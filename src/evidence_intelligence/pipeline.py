"""End-to-end pipeline orchestration: request -> ingestion -> models ->
causation -> ensemble/DSI -> packaging -> store (HLD §2 sequence diagram).

Known limitation, disclosed in every package's accuracy statement: fAPAR and
insolation are approximated from NDVI via a published linear relationship
(fAPAR ≈ clip(1.24×NDVI − 0.168, 0, 1)) rather than a dedicated fAPAR product,
since a wired MODIS/Sentinel-3 OLIC fAPAR feed is not yet integrated
(Modeling-Approach.md §2 names MODIS/Sentinel-3 OLCI as the intended source)."""

from __future__ import annotations

import logging
from datetime import date, datetime

from evidence_intelligence.causation import scoring as causation_scoring
from evidence_intelligence.config import Settings
from evidence_intelligence.ingestion.gee_client import GEEClient
from evidence_intelligence.ingestion.imagery import ingest_imagery
from evidence_intelligence.ingestion.weather import IMDClient, WeatherClient, ingest_weather
from evidence_intelligence.models import ai_ml, dsi, ensemble, semi_physical
from evidence_intelligence.packaging.report_generator import (
    LocalObjectStorage,
    PackageContent,
    generate_package,
)
from evidence_intelligence.store.evidence_store import EvidenceStore
from evidence_intelligence.store.schema import ModelComponent, PackageTier, PerilType, RequestStatus

CLOUDBURST_HAILSTORM_PERILS = {PerilType.CLOUDBURST, PerilType.HAILSTORM}

logger = logging.getLogger("evidence_intelligence")

_ai_ml_model_cache: dict[str, ai_ml.AiMlModel] = {}


def _load_ai_ml_model(settings: Settings) -> ai_ml.AiMlModel:
    """Loads the trained model at `settings.ai_ml_model_path` (see
    scripts/train_ai_ml_model.py) if one is configured, caching it per path
    for the life of the process. Falls back to an untrained instance —
    logged, not silent — if no path is set or the load fails, so a bad
    config degrades to the disclosed placeholder rather than crashing every
    request."""
    path = settings.ai_ml_model_path
    if path is None:
        return ai_ml.AiMlModel()
    if path not in _ai_ml_model_cache:
        try:
            _ai_ml_model_cache[path] = ai_ml.AiMlModel.load(path)
            logger.info("ai_ml_model_loaded path=%s", path)
        except Exception:
            logger.exception("ai_ml_model_load_failed path=%s falling back to untrained", path)
            _ai_ml_model_cache[path] = ai_ml.AiMlModel()
    return _ai_ml_model_cache[path]


def _ndvi_to_fapar(ndvi: float | None) -> float | None:
    """`None` in, `None` out — an absent NDVI has no fAPAR, and substituting
    0.0 made "we could not see the field" indistinguishable from "the field
    has no green vegetation left", i.e. total damage (tasks.md T0-02)."""
    if ndvi is None:
        return None
    return max(0.0, min(1.0, 1.24 * ndvi - 0.168))


def _insolation_proxy_mj() -> float:
    """No dedicated insolation feed wired yet — a fixed regional-average
    proxy, disclosed as a known limitation (FR-019)."""
    return 18.0


# Used only when ERA5-Land returns no reading for the window at all. Kept as an
# explicit `is None` check rather than `or`, since 0 °C is a valid temperature
# that `or` would silently replace with this default.
FALLBACK_TEMPERATURE_C = 25.0


def _cross_pol_ratio_deviation(sar) -> float | None:
    """`vh_vv_backscatter_deviation` (Modeling-Approach.md §3's Component 2
    feature table) — how much the cross-polarized ratio changed over the event.

    In dB the ratio is a difference, so the change in (VH − VV) between the
    pre- and post-event composites reduces exactly to `vh_drop − vv_drop`; no
    additional acquisition is needed beyond the two `sar_composite` already
    measures. Positive means VH fell further than VV — canopy volume
    scattering lost relative to surface return — matching the
    positive-to-damage direction the rest of the feature set uses.

    `None` unless both polarizations were measured; the feature is omitted
    rather than defaulted in that case."""
    if sar.vh_drop_db is None or sar.vv_drop_db is None:
        return None
    return sar.vh_drop_db - sar.vv_drop_db


def run_pipeline(
    request_id: str,
    geometry: dict,
    event_date: date,
    peril_type: PerilType,
    store: EvidenceStore,
    settings: Settings,
    gee_client: GEEClient | None = None,
    weather_client: WeatherClient | None = None,
    imd_client: IMDClient | None = None,
    ai_ml_model: ai_ml.AiMlModel | None = None,
    storage: LocalObjectStorage | None = None,
) -> None:
    gee_client = gee_client or GEEClient()
    weather_client = weather_client or WeatherClient()
    imd_client = imd_client or IMDClient()
    ai_ml_model = ai_ml_model or _load_ai_ml_model(settings)
    storage = storage or LocalObjectStorage(settings.evidence_store_bucket)

    store.set_status(request_id, RequestStatus.IN_PROGRESS)

    imagery = ingest_imagery(gee_client, geometry, event_date, peril_type)

    weather = ingest_weather(
        weather_client,
        imd_client,
        geometry,
        event_date,
        peril_type_is_cloudburst_or_hailstorm=peril_type in CLOUDBURST_HAILSTORM_PERILS,
    )
    causation_low_confidence_threshold = settings.causation_low_confidence_threshold
    weather_anomaly_normalized = min(
        1.0, abs(weather.precipitation.anomaly_score or 0.0)
    )

    if not imagery.usable:
        # FR-022: no usable imagery and not flood-compatible (SAR did not
        # substitute either) — deliver a weather-only preliminary package
        # rather than failing outright, and stay open for a later complete run.
        _deliver_weather_only_preliminary(
            request_id, weather, weather_anomaly_normalized, peril_type, store, settings, storage
        )
        store.set_status(request_id, RequestStatus.INSUFFICIENT_DATA)
        return

    # SAR substitutes for, rather than supplements, post-event optical when
    # it was unusable (imagery.usable can be True via post_event OR sar) —
    # SAR has no NDVI-equivalent index value, only a backscatter drop.
    post_event_source = imagery.post_event or imagery.sar
    store.add_satellite_result(
        request_id=request_id,
        source_dataset=post_event_source.source_dataset,
        source_version=post_event_source.source_version,
        acquisition_date=post_event_source.acquisition_date,
        pre_event_index_value=imagery.pre_event.index_value if imagery.pre_event else None,
        post_event_index_value=imagery.post_event.index_value if imagery.post_event else None,
        flood_extent_geometry=(
            str(imagery.sar.flood_extent_geojson)
            if imagery.sar and imagery.sar.flood_extent_geojson
            else None
        ),
    )

    has_historical_baseline = len(imagery.historical) > 0

    # -- Optical-derived signals, where an optical pair actually exists -----
    # When SAR substituted for post-event optical (flood/cloud-cover case)
    # there is no NDVI-equivalent post-event value. Every NDVI-derived signal
    # below stays absent in that case rather than defaulting to 0, which
    # previously made the apparent NDVI drop equal the whole pre-event NDVI —
    # i.e. synthesized a maximum-damage reading out of missing data, in the
    # claimant's favour, and reported it as measured (tasks.md T0-02).
    pre_ndvi = imagery.pre_event.index_value if imagery.pre_event else None
    post_ndvi = imagery.post_event.index_value if imagery.post_event else None
    pre_fapar = _ndvi_to_fapar(pre_ndvi)
    post_fapar = _ndvi_to_fapar(post_ndvi)
    optical_pair_available = pre_ndvi is not None and post_ndvi is not None

    ndvi_drop = max(0.0, pre_ndvi - post_ndvi) if optical_pair_available else None
    fapar_deviation = (
        pre_fapar - post_fapar if pre_fapar is not None and post_fapar is not None else None
    )
    observed_temp_c = (
        weather.reanalysis.observed_value
        if weather.reanalysis.observed_value is not None
        else FALLBACK_TEMPERATURE_C
    )

    contributions: list[ensemble.ComponentContribution] = []

    # -- Semi-physical model (Component 1) --------------------------------
    # Runs only with a real pre/post optical pair — its RUE chain is entirely
    # fAPAR/LSWI-driven, so without one it has no input to model and must be
    # absent from the ensemble rather than contribute a fabricated estimate.
    semi_physical_result = None
    if optical_pair_available:
        semi_physical_result = semi_physical.run(
            pre_event_insolation_mj=_insolation_proxy_mj(),
            pre_event_fapar=pre_fapar,
            pre_event_lswi=pre_ndvi,
            pre_event_temp_c=observed_temp_c,
            post_event_insolation_mj=_insolation_proxy_mj(),
            post_event_fapar=post_fapar,
            post_event_lswi=post_ndvi,
            post_event_temp_c=observed_temp_c,
        )
        store.add_component_result(
            request_id=request_id,
            component=ModelComponent.SEMI_PHYSICAL,
            methodology_version=semi_physical.METHODOLOGY_VERSION,
            point_estimate=semi_physical_result.damage_fraction,
            confidence_or_accuracy={
                "calibration_confidence": semi_physical_result.calibration_confidence,
                "input_warnings": semi_physical_result.input_warnings,
            },
        )
        contributions.append(
            ensemble.ComponentContribution(
                component="SEMI_PHYSICAL",
                damage_fraction=semi_physical_result.damage_fraction,
                weight=ensemble.semi_physical_weight(
                    semi_physical_result.calibration_confidence
                ),
            )
        )

    # -- AI/ML model (Component 2) -----------------------------------------
    # Only features that were actually measured are passed. A feature the
    # pipeline cannot compute is omitted, never defaulted to 0.0 — the model's
    # 0.0 means "no deviation observed", which is a claim about the field, not
    # about our coverage of it (tasks.md T0-03).
    feature_vector: dict[str, float] = {}
    if ndvi_drop is not None:
        feature_vector["ndvi_deviation"] = ndvi_drop
    if fapar_deviation is not None:
        feature_vector["fapar_deviation"] = fapar_deviation
    if weather.precipitation.anomaly_score is not None:
        feature_vector["rainfall_anomaly"] = weather.precipitation.anomaly_score
    if weather.reanalysis.anomaly_score is not None:
        feature_vector["temperature_anomaly"] = weather.reanalysis.anomaly_score
    if weather.soil_moisture.anomaly_score is not None:
        feature_vector["soil_moisture_deviation"] = weather.soil_moisture.anomaly_score
    if imagery.sar is not None:
        cross_pol = _cross_pol_ratio_deviation(imagery.sar)
        if cross_pol is not None:
            feature_vector["vh_vv_backscatter_deviation"] = cross_pol

    ai_ml_result = ai_ml_model.predict(feature_vector, harvest_index=0.4)
    store.add_component_result(
        request_id=request_id,
        component=ModelComponent.AI_ML,
        methodology_version=ai_ml.METHODOLOGY_VERSION,
        point_estimate=ai_ml_result.damage_fraction,
        confidence_or_accuracy=ai_ml_result.confidence_or_accuracy,
    )

    contributions.append(
        ensemble.ComponentContribution(
            component="AI_ML",
            damage_fraction=ai_ml_result.damage_fraction,
            weight=ensemble.ai_ml_weight(ai_ml_result.confidence_or_accuracy),
        )
    )

    # -- CSM assimilation (Component 3, advanced tier) ----------------------
    if settings.csm_high_scrutiny_enabled and ndvi_drop is not None:
        from evidence_intelligence.models import csm_assimilation

        csm_result = csm_assimilation.run(
            geometry=geometry,
            damage_signal=ndvi_drop,
        )
        store.add_component_result(
            request_id=request_id,
            component=ModelComponent.CSM_ASSIMILATION,
            methodology_version=csm_assimilation.METHODOLOGY_VERSION,
            point_estimate=csm_result.damage_fraction,
            confidence_or_accuracy={"calibration_confidence": csm_result.calibration_confidence},
        )
        contributions.append(
            ensemble.ComponentContribution(
                component="CSM_ASSIMILATION",
                damage_fraction=csm_result.damage_fraction,
                weight=csm_result.calibration_confidence,
            )
        )

    # -- Ensemble (Component 4) ---------------------------------------------
    ensemble_result = ensemble.combine(contributions)
    store.add_component_result(
        request_id=request_id,
        component=ModelComponent.ENSEMBLE,
        methodology_version=ensemble.METHODOLOGY_VERSION,
        point_estimate=ensemble_result.damage_fraction,
        confidence_or_accuracy={"combined_confidence": ensemble_result.combined_confidence},
        damage_classification=_classify(ensemble_result.damage_fraction),
        affected_area_ha=None,
    )

    # -- Damage Severity Index (Component 5) --------------------------------
    historical_ndvi = [c.index_value for c in imagery.historical if c.index_value is not None]
    # Indicators the pipeline cannot currently measure are omitted, not passed
    # as 0.0 — `dsi.compute` already treats an absent indicator as neutral
    # (0.5 normalized), whereas 0.0 asserts a measured zero deviation.
    # `lswi_deviation` in particular was being fed the NDVI drop, a different
    # physical quantity, in both this dict and the Component 2 feature vector
    # (tasks.md T0-03). No LSWI source is wired yet, so it stays absent.
    dsi_indicators: dict[str, float] = {
        "weather_anomaly_magnitude": weather_anomaly_normalized,
    }
    if ndvi_drop is not None:
        dsi_indicators["ndvi_deviation"] = ndvi_drop
    if fapar_deviation is not None:
        dsi_indicators["fapar_deviation"] = fapar_deviation
    if imagery.sar is not None and imagery.sar.vh_drop_db is not None:
        # Modeling-Approach.md §6's indicator is cross-polarized VH, which
        # tracks canopy volume scattering. VV — the flood detector's
        # polarization — was standing in for it, which reported a surface-water
        # measurement as a crop-structure one. Absent VH now leaves the
        # indicator absent (tasks.md T0-15).
        dsi_indicators["sar_vh_backscatter_deviation"] = imagery.sar.vh_drop_db
    dsi_historical = {
        "ndvi_deviation": historical_ndvi,
        "lswi_deviation": [],
        "sar_vh_backscatter_deviation": [],
        "fapar_deviation": [],
        "crop_condition_variability": [],
        "weather_anomaly_magnitude": [],
    }
    dsi_result = dsi.compute(dsi_indicators, dsi_historical)
    store.add_component_result(
        request_id=request_id,
        component=ModelComponent.DSI,
        methodology_version=dsi.METHODOLOGY_VERSION,
        point_estimate=dsi_result.score,
        confidence_or_accuracy={"entropy_weights": dsi_result.entropy_weights},
    )

    # -- Causation analysis ---------------------------------------------------
    causation_result = causation_scoring.score(
        days_between_event_and_ndvi_drop=1,
        distance_km_to_weather_anomaly=0.0,
        normalized_weather_anomaly=weather_anomaly_normalized,
        # No optical pair means no observed damage magnitude to correlate the
        # weather anomaly against — scored as 0 (uncorroborated), not as a
        # synthesized drop.
        normalized_ndvi_drop=min(1.0, ndvi_drop / 0.5) if ndvi_drop is not None else 0.0,
        peril_type=peril_type,
        phenology_flag=imagery.phenology_flag,
        low_confidence_threshold=causation_low_confidence_threshold,
    )
    store.add_weather_result(
        request_id=request_id,
        source_dataset=weather.precipitation.source_dataset,
        source_version=weather.precipitation.source_version,
        observed_value=weather.precipitation.observed_value or 0.0,
        historical_baseline=weather.precipitation.historical_baseline,
        anomaly_score=weather.precipitation.anomaly_score,
        causation_confidence_score=causation_result.score,
    )

    # -- Package assembly -----------------------------------------------------
    notes: list[str] = []
    if not has_historical_baseline:
        notes.append(
            "No historical baseline was available for this geometry; "
            "anomaly-vs-history scoring was omitted (FR-023)."
        )
    if imagery.phenology_flag:
        notes.append(imagery.phenology_flag)
    if causation_result.low_confidence:
        notes.append(
            f"Causation confidence ({causation_result.score}) is below the configured "
            "low-confidence threshold. This package is still delivered in full."
        )

    supplied_features = ai_ml_result.confidence_or_accuracy.get("features_supplied") or []
    accuracy_statement = [
        "fAPAR and insolation are approximated from NDVI via a published linear "
        "relationship, not a dedicated fAPAR product (known limitation).",
        f"AI/ML model status: {ai_ml_result.confidence_or_accuracy.get('status')}.",
        f"Component 2 features measured for this request: "
        f"{', '.join(supplied_features) if supplied_features else 'none'} "
        f"({len(supplied_features)} of {len(ai_ml.FEATURE_NAMES)} declared). "
        "Features that could not be measured were omitted rather than defaulted.",
    ]
    if imagery.post_event is None and imagery.sar is not None:
        accuracy_statement.append(
            "Post-event optical imagery was unusable; Sentinel-1 SAR substituted for "
            "flood-extent detection. No NDVI-equivalent post-event value exists from "
            "SAR, so the semi-physical model (Component 1) and all NDVI-derived "
            "signals were omitted from this package rather than estimated from a "
            "substituted value — the damage estimate here rests on the SAR flood "
            "extent and the weather correlation alone."
        )
    if semi_physical_result is not None and semi_physical_result.input_warnings:
        accuracy_statement.extend(
            f"Semi-physical model input warning: {warning}."
            for warning in semi_physical_result.input_warnings
        )

    package_content = PackageContent(
        request_id=request_id,
        package_tier=PackageTier.COMPLETE.value,
        methodology_version="v1.0.0",
        generated_at=datetime.utcnow(),
        causation_confidence_score=causation_result.score,
        ensemble_damage_fraction=ensemble_result.damage_fraction,
        ensemble_combined_confidence=ensemble_result.combined_confidence,
        dsi_score=dsi_result.score,
        damage_classification=_classify(ensemble_result.damage_fraction),
        affected_area_ha=None,
        source_attribution=[
            {
                "source_dataset": post_event_source.source_dataset,
                "source_version": post_event_source.source_version,
                "acquisition_date": str(post_event_source.acquisition_date),
            },
            {
                "source_dataset": weather.precipitation.source_dataset,
                "source_version": weather.precipitation.source_version,
                "acquisition_date": str(event_date),
            },
        ],
        accuracy_statement=accuracy_statement,
        notes=notes,
    )
    package_fields = generate_package(package_content, storage)
    store.add_package(
        request_id=request_id,
        package_tier=PackageTier.COMPLETE,
        methodology_version="v1.0.0",
        **package_fields,
    )

    store.set_status(request_id, RequestStatus.COMPLETE)


def _deliver_weather_only_preliminary(
    request_id: str,
    weather,
    weather_anomaly_normalized: float,
    peril_type: PerilType,
    store: EvidenceStore,
    settings: Settings,
    storage: LocalObjectStorage,
) -> None:
    """FR-022: weather-only preliminary package when no usable satellite
    imagery exists — never a bare failure."""
    causation_result = causation_scoring.score(
        days_between_event_and_ndvi_drop=1,
        distance_km_to_weather_anomaly=0.0,
        normalized_weather_anomaly=weather_anomaly_normalized,
        normalized_ndvi_drop=0.0,
        peril_type=peril_type,
        phenology_flag=None,
        low_confidence_threshold=settings.causation_low_confidence_threshold,
    )
    store.add_weather_result(
        request_id=request_id,
        source_dataset=weather.precipitation.source_dataset,
        source_version=weather.precipitation.source_version,
        observed_value=weather.precipitation.observed_value or 0.0,
        historical_baseline=weather.precipitation.historical_baseline,
        anomaly_score=weather.precipitation.anomaly_score,
        causation_confidence_score=causation_result.score,
    )

    package_content = PackageContent(
        request_id=request_id,
        package_tier=PackageTier.WEATHER_ONLY_PRELIMINARY.value,
        methodology_version="v1.0.0",
        generated_at=datetime.utcnow(),
        causation_confidence_score=causation_result.score,
        ensemble_damage_fraction=None,
        ensemble_combined_confidence=None,
        dsi_score=None,
        damage_classification=None,
        affected_area_ha=None,
        source_attribution=[
            {
                "source_dataset": weather.precipitation.source_dataset,
                "source_version": weather.precipitation.source_version,
                "acquisition_date": "n/a",
            }
        ],
        accuracy_statement=[
            "No usable satellite imagery was available for this request's window; "
            "this package is weather-only and preliminary. It will be superseded by "
            "a complete package once imagery becomes available (FR-022)."
        ],
        notes=["Weather-only preliminary package."],
    )
    package_fields = generate_package(package_content, storage)
    store.add_package(
        request_id=request_id,
        package_tier=PackageTier.WEATHER_ONLY_PRELIMINARY,
        methodology_version="v1.0.0",
        **package_fields,
    )


def _classify(damage_fraction: float) -> str:
    if damage_fraction < 0.1:
        return "negligible"
    if damage_fraction < 0.33:
        return "minor"
    if damage_fraction < 0.66:
        return "moderate"
    return "severe"


def retry_insufficient_data(
    request_id: str,
    geometry: dict,
    event_date: date,
    peril_type: PerilType,
    store: EvidenceStore,
    settings: Settings,
    **clients,
) -> bool:
    """Evidence-Flow-Spec.md §8: re-processed on a backoff schedule once
    imagery becomes available. Returns True if it completed this attempt."""
    request = store.get_request(request_id)
    if request is None or request.status != RequestStatus.INSUFFICIENT_DATA:
        return False

    gee_client = clients.get("gee_client") or GEEClient()
    imagery = ingest_imagery(gee_client, geometry, event_date, peril_type)
    if not imagery.usable:
        return False

    run_pipeline(
        request_id,
        geometry,
        event_date,
        peril_type,
        store,
        settings,
        gee_client=gee_client,
        weather_client=clients.get("weather_client"),
        imd_client=clients.get("imd_client"),
        ai_ml_model=clients.get("ai_ml_model"),
        storage=clients.get("storage"),
    )
    return True


def run_pipeline_background(
    request_id: str,
    geometry: dict,
    event_date: date,
    peril_type: PerilType,
    store: EvidenceStore,
    settings: Settings,
) -> None:
    """Entry point for FastAPI's BackgroundTasks. Wraps `run_pipeline` so an
    unhandled exception (a transient GEE/weather-API failure, a bug) can't
    propagate out of the background task and crash the ASGI response cycle —
    it's caught, logged, and the request is marked FAILED instead, extending
    the same 'never fail silently' principle behind FR-022 to failures
    outside the specific imagery-unavailable case that FR-022 covers."""
    try:
        run_pipeline(request_id, geometry, event_date, peril_type, store, settings)
    except Exception:
        logger.exception("pipeline_failed request_id=%s", request_id)
        try:
            store.set_status(request_id, RequestStatus.FAILED)
        except Exception:
            logger.exception("failed_to_mark_request_failed request_id=%s", request_id)
