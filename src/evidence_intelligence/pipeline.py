"""End-to-end pipeline orchestration: request -> ingestion -> models ->
causation -> ensemble/DSI -> packaging -> store (HLD §2 sequence diagram).

Known limitation, disclosed in every package's accuracy statement: fAPAR and
insolation are approximated from NDVI via a published linear relationship
(fAPAR ≈ clip(1.24×NDVI − 0.168, 0, 1)) rather than a dedicated fAPAR product,
since a wired MODIS/Sentinel-3 OLIC fAPAR feed is not yet integrated
(modeling-approach.md §2 names MODIS/Sentinel-3 OLCI as the intended source)."""

from __future__ import annotations

import logging
from datetime import date, datetime

from evidence_intelligence.causation import scoring as causation_scoring
from evidence_intelligence.config import Settings
from evidence_intelligence.geometry import to_ewkt
from evidence_intelligence.ingestion.gee_client import GEEClient
from evidence_intelligence.ingestion.imagery import ingest_imagery
from evidence_intelligence.ingestion.weather import IMDClient, WeatherClient, ingest_weather
from evidence_intelligence.manifest import EvidenceInputsManifest, InputOutcome
from evidence_intelligence.models import ai_ml, dsi, ensemble, semi_physical
from evidence_intelligence.observation import (
    FAPAR_DEVIATION,
    LSWI_DEVIATION,
    NDVI_DEVIATION,
    POST_EVENT_FAPAR,
    POST_EVENT_INSOLATION_MJ,
    POST_EVENT_LSWI,
    POST_EVENT_TEMP_C,
    PRE_EVENT_FAPAR,
    PRE_EVENT_INSOLATION_MJ,
    PRE_EVENT_LSWI,
    PRE_EVENT_TEMP_C,
    RAINFALL_ANOMALY,
    SAR_VH_BACKSCATTER_DEVIATION,
    SOIL_MOISTURE_DEVIATION,
    TEMPERATURE_ANOMALY,
    VH_VV_BACKSCATTER_DEVIATION,
    WEATHER_ANOMALY_MAGNITUDE,
    observe,
)
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


def _build_manifest(imagery, weather, ai_ml_result, semi_physical_result, settings):
    """Record every evidence input attempted for this request (T0-09)."""
    manifest = EvidenceInputsManifest()

    for name, composite in (
        ("optical_pre_event", imagery.pre_event),
        ("optical_post_event", imagery.post_event),
    ):
        if composite is None:
            manifest.record(name, InputOutcome.UNAVAILABLE, "no usable composite in window")
        else:
            fraction = composite.valid_pixel_fraction
            # Half the field is a reporting boundary for the manifest's
            # coarse USED/DEGRADED label only — it gates nothing. What decides
            # usability is `minimum_valid_pixel_fraction`, which stays unset
            # until a deployment sources a value (T0-07).
            partial = fraction is not None and fraction < 0.5
            manifest.record(
                name,
                InputOutcome.DEGRADED if partial else InputOutcome.USED,
                f"{composite.source_dataset}"
                + (f", {fraction:.0%} cloud-free coverage" if fraction is not None else ""),
            )

    if imagery.sar is not None:
        manifest.record(
            "sar_backscatter",
            InputOutcome.DEGRADED if imagery.post_event is None else InputOutcome.USED,
            "substituted for unusable post-event optical"
            if imagery.post_event is None
            else "supplementary to optical",
        )
    else:
        manifest.record(
            "sar_backscatter", InputOutcome.NOT_APPLICABLE, "not a flood-compatible peril"
        )

    manifest.record(
        "historical_baseline",
        InputOutcome.USED if imagery.historical else InputOutcome.UNAVAILABLE,
        f"{len(imagery.historical)} prior season(s)",
    )

    for name, observation in (
        ("weather_precipitation", weather.precipitation),
        ("weather_temperature", weather.reanalysis),
        ("weather_soil_moisture", weather.soil_moisture),
    ):
        manifest.record(
            name,
            InputOutcome.USED if observation.anomaly_score is not None else InputOutcome.DEGRADED,
            observation.source_dataset
            + ("" if observation.anomaly_score is not None else ", no baseline to compare against"),
        )

    manifest.record(
        "imd_station_corroboration",
        InputOutcome.USED if weather.station_corroboration else InputOutcome.UNAVAILABLE,
        None if weather.station_corroboration else "no station record returned",
    )

    manifest.record(
        "model_semi_physical",
        InputOutcome.USED if semi_physical_result is not None else InputOutcome.UNAVAILABLE,
        None if semi_physical_result is not None else "requires a pre/post optical pair",
    )

    trained = ai_ml_result.confidence_or_accuracy.get("status") == "trained"
    manifest.record(
        "model_ai_ml",
        InputOutcome.USED if trained else InputOutcome.DEGRADED,
        None if trained else "untrained placeholder formula, not a calibrated prediction",
    )

    manifest.record(
        "model_csm_assimilation",
        InputOutcome.USED if settings.csm_high_scrutiny_enabled else InputOutcome.NOT_APPLICABLE,
        None if settings.csm_high_scrutiny_enabled else "advanced tier disabled",
    )

    return manifest


def _assumed_harvest_index() -> float:
    """The single Harvest Index applied to every crop (tasks.md T0-18).

    Read from `CropParameters` rather than repeated as a literal so Component 1
    and Component 2 cannot drift apart — they previously carried the same 0.4
    in two unconnected places.

    `modeling-approach.md` §2 commits to Harvest Index being "sourced from
    published crop-variety reference values and regional agronomic literature,
    clearly labeled as a modeling assumption". Neither half held: one constant
    was applied to wheat, paddy, cotton and everything else, and no package
    said so. Per-crop resolution is not a lookup away either — the Evidence
    Request Interface carries no crop-type field to look one up *from*, which
    is the open part (see specs/001-evidence-generation-pipeline/issue/
    "harvest index source and per-crop resolution"). This function closes the
    labelling half only."""
    return semi_physical.CropParameters().harvest_index


def _modeling_assumption_statements(bands: tuple[float, float, float]) -> list[str]:
    """Assumptions that shape reported figures but aren't derived from this
    request's own data — stated in the package rather than left in the code.

    Both were live in shipped output before T0-17/T0-18: a yield-loss figure
    scaled by an un-crop-specific constant, and a severity word produced by
    cut points that appear in no source document. A reader can discount a
    disclosed assumption; an undisclosed one just looks like a measurement."""
    return [
        f"Yield loss = damage fraction × Harvest Index, using an assumed "
        f"Harvest Index of {_assumed_harvest_index()} applied uniformly to all crops. "
        "This is a modeling assumption, not a crop-specific published value — the "
        "evidence request carries no crop type to select one by (modeling-approach.md §2).",
        f"Damage classification bands (negligible < {bands[0]} ≤ minor < {bands[1]} "
        f"≤ moderate < {bands[2]} ≤ severe) are a presentational convention configured "
        "for this deployment, not a sourced standard. The underlying damage fraction and "
        "its confidence are the figures to weigh.",
    ]


def _coverage_statement(imagery) -> str:
    """How much of the field was actually seen, for the accuracy statement.

    A reader of an evidence package needs this to weigh every index-derived
    figure in it: an NDVI drop measured over 12% of a field is a different
    claim from the same drop measured over 95% of it, and before T0-07 the
    package could not tell them apart (Constitution Principle I/II)."""
    parts = []
    for label, composite in (("pre-event", imagery.pre_event), ("post-event", imagery.post_event)):
        if composite is None:
            parts.append(f"{label}: no usable optical composite")
        elif composite.valid_pixel_fraction is None:
            parts.append(f"{label}: coverage not measured")
        else:
            parts.append(f"{label}: {composite.valid_pixel_fraction:.0%} of field")
    return (
        "Cloud/shadow-free coverage of the submitted geometry, after per-pixel "
        f"masking — {'; '.join(parts)}."
    )


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

    imagery = ingest_imagery(
        gee_client,
        geometry,
        event_date,
        peril_type,
        minimum_valid_pixel_fraction=settings.minimum_valid_pixel_fraction,
    )

    weather = ingest_weather(
        weather_client,
        imd_client,
        geometry,
        event_date,
        peril_type_is_cloudburst_or_hailstorm=peril_type in CLOUDBURST_HAILSTORM_PERILS,
    )
    # Every derived signal for this request, in one place (tasks.md T0R-02).
    # Nothing below re-derives "was this measured?" from the raw bundles.
    obs = observe(imagery, weather)

    causation_low_confidence_threshold = settings.causation_low_confidence_threshold
    weather_anomaly_normalized = obs.value(WEATHER_ANOMALY_MAGNITUDE)

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
        # Earth Engine's reduceToVectors returns a GeoJSON FeatureCollection,
        # which PostGIS rejects outright — `str()` of it was never a storable
        # value, and this path runs only when SAR actually detects flooding
        # (tasks.md T0-13). Normalised to EWKT; a FeatureCollection with no
        # features stores NULL rather than an empty geometry.
        flood_extent_geometry=(
            to_ewkt(imagery.sar.flood_extent_geojson) if imagery.sar else None
        ),
    )

    # Deliberately still read from the bundle, not from `obs`: this counts
    # historical *composites*, while `obs.history(NDVI_DEVIATION)` counts those
    # with a usable index value. They differ when a composite returns no value,
    # and T0R-02 is a lift, not a correction — see T0R-05's note.
    has_historical_baseline = len(imagery.historical) > 0

    # -- Optical-derived signals, where an optical pair actually exists -----
    # When SAR substituted for post-event optical (flood/cloud-cover case)
    # there is no NDVI-equivalent post-event value. Every NDVI-derived signal
    # stays absent in that case rather than defaulting to 0, which previously
    # made the apparent NDVI drop equal the whole pre-event NDVI — i.e.
    # synthesized a maximum-damage reading out of missing data, in the
    # claimant's favour, and reported it as measured (tasks.md T0-02).
    # `observe()` now owns that rule; here it is only read.
    ndvi_drop = obs.value(NDVI_DEVIATION)
    optical_pair_available = obs.is_present(NDVI_DEVIATION)

    contributions: list[ensemble.ComponentContribution] = []

    # -- Semi-physical model (Component 1) --------------------------------
    # Runs only with a real pre/post optical pair — its RUE chain is entirely
    # fAPAR/LSWI-driven, so without one it has no input to model and must be
    # absent from the ensemble rather than contribute a fabricated estimate.
    semi_physical_result = None
    if optical_pair_available:
        semi_physical_result = semi_physical.run(
            pre_event_insolation_mj=obs.value(PRE_EVENT_INSOLATION_MJ),
            pre_event_fapar=obs.value(PRE_EVENT_FAPAR),
            pre_event_lswi=obs.value(PRE_EVENT_LSWI),
            pre_event_temp_c=obs.value(PRE_EVENT_TEMP_C),
            post_event_insolation_mj=obs.value(POST_EVENT_INSOLATION_MJ),
            post_event_fapar=obs.value(POST_EVENT_FAPAR),
            post_event_lswi=obs.value(POST_EVENT_LSWI),
            post_event_temp_c=obs.value(POST_EVENT_TEMP_C),
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
    feature_vector = obs.present(
        (
            NDVI_DEVIATION,
            FAPAR_DEVIATION,
            RAINFALL_ANOMALY,
            TEMPERATURE_ANOMALY,
            SOIL_MOISTURE_DEVIATION,
            VH_VV_BACKSCATTER_DEVIATION,
        )
    )

    ai_ml_result = ai_ml_model.predict(feature_vector, harvest_index=_assumed_harvest_index())
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
        damage_classification=_classify(
            ensemble_result.damage_fraction, settings.damage_classification_bands
        ),
        affected_area_ha=None,
    )

    # -- Damage Severity Index (Component 5) --------------------------------
    # Indicators the pipeline cannot currently measure are omitted, not passed
    # as 0.0 — `dsi.compute` already treats an absent indicator as neutral
    # (0.5 normalized), whereas 0.0 asserts a measured zero deviation.
    # `lswi_deviation` in particular was being fed the NDVI drop, a different
    # physical quantity (tasks.md T0-03), and `sar_vh_backscatter_deviation`
    # the VV drop (T0-15). `observe()` owns both distinctions now.
    dsi_indicators = obs.present(
        (
            WEATHER_ANOMALY_MAGNITUDE,
            NDVI_DEVIATION,
            FAPAR_DEVIATION,
            SAR_VH_BACKSCATTER_DEVIATION,
            LSWI_DEVIATION,
        )
    )
    # `or []` preserves `dsi.compute`'s current contract, which cannot tell an
    # absent archive from a zero-variance one. That conflation is the defect
    # T0R-05 fixes; T0R-02 only moves where the archives come from.
    dsi_historical = {
        name: list(obs.history(name) or [])
        for name in dsi.INDICATOR_DIRECTIONS
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
        # Both unmeasured, and passing them as such rather than as 1 / 0.0 is
        # the point: those literals scored 100 each, i.e. 55 of the 100 points
        # were a constant on every request (tasks.md T0-06). The temporal term
        # needs a break-point date (T05-05); the spatial term needs the
        # anomaly's footprint, which nothing computes.
        days_between_event_and_ndvi_drop=None,
        distance_km_to_weather_anomaly=None,
        normalized_weather_anomaly=weather_anomaly_normalized,
        # No optical pair means no observed damage magnitude to correlate the
        # weather anomaly against. Previously scored as a measured 0.0, which
        # read as *perfect* correlation whenever the anomaly was also near zero.
        normalized_ndvi_drop=min(1.0, ndvi_drop / 0.5) if ndvi_drop is not None else None,
        peril_type=peril_type,
        phenology_flag=obs.phenology_flag,
        phenology_checked=True,
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
    if causation_result.score is None:
        notes.append(
            "Causation confidence was not computed: none of the four alignment terms "
            f"could be measured ({'; '.join(causation_result.excluded.values())}). "
            "The damage and yield-loss figures in this package do not depend on it."
        )
    elif causation_result.excluded:
        notes.append(
            f"Causation confidence ({causation_result.score}) was computed from "
            f"{len(causation_result.contributing)} of 4 alignment terms, reweighted over "
            "those measured. Terms not measured: "
            + "; ".join(f"{name} ({reason})" for name, reason in causation_result.excluded.items())
            + "."
        )
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
        _coverage_statement(imagery),
        *_modeling_assumption_statements(settings.damage_classification_bands),
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
        causation_terms_contributing=causation_result.contributing,
        causation_terms_excluded=causation_result.excluded,
        ensemble_damage_fraction=ensemble_result.damage_fraction,
        ensemble_combined_confidence=ensemble_result.combined_confidence,
        dsi_score=dsi_result.score,
        damage_classification=_classify(
            ensemble_result.damage_fraction, settings.damage_classification_bands
        ),
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
                # T0-10: window mean alone understates a single-day extreme,
                # which is the whole signal for cloudburst and hailstorm claims.
                "window_total_mm": weather.precipitation_total_mm,
                "max_daily_mm": weather.precipitation_max_daily_mm,
            },
            *(
                [
                    {
                        "source_dataset": "IMD AWS station record",
                        "source_version": "imd-aws",
                        "acquisition_date": str(event_date),
                        # T0-10: this was fetched and discarded, leaving
                        # evidence-flow-spec.md §5's "corroborated by IMD AWS"
                        # claim unbacked by anything in the package.
                        "corroboration": weather.station_corroboration,
                    }
                ]
                if weather.station_corroboration
                else []
            ),
        ],
        accuracy_statement=accuracy_statement,
        notes=notes,
        evidence_inputs=_build_manifest(
            imagery, weather, ai_ml_result, semi_physical_result, settings
        ).as_list(),
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
        days_between_event_and_ndvi_drop=None,
        distance_km_to_weather_anomaly=None,
        normalized_weather_anomaly=weather_anomaly_normalized,
        normalized_ndvi_drop=None,
        peril_type=peril_type,
        phenology_flag=None,
        # There is no imagery on this tier, so the phenology check never ran.
        # Passing it as "checked, nothing wrong" scored 90 of a possible 100
        # on the tier with the weakest evidence in the system.
        phenology_checked=False,
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
        causation_terms_contributing=causation_result.contributing,
        causation_terms_excluded=causation_result.excluded,
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


DAMAGE_CLASSIFICATION_LABELS = ("negligible", "minor", "moderate", "severe")


def _classify(damage_fraction: float, bands: tuple[float, float, float]) -> str:
    """Map a damage fraction to one of four labels.

    The cut points are configuration, not a standard (tasks.md T0-17). They
    appear nowhere in `documents/`, and `yestech_manual_2023.md` defines no
    transferable severity vocabulary this module could adopt — so a field at
    0.34 reading as "moderate" while one at 0.32 reads as "minor" rests on
    nothing sourced. Every package now discloses that, because a categorical
    label is the one output a reviewer cannot weigh for themselves: a fraction
    invites judgement, a word substitutes for it."""
    for threshold, label in zip(bands, DAMAGE_CLASSIFICATION_LABELS, strict=False):
        if damage_fraction < threshold:
            return label
    return DAMAGE_CLASSIFICATION_LABELS[-1]


def retry_insufficient_data(
    request_id: str,
    geometry: dict,
    event_date: date,
    peril_type: PerilType,
    store: EvidenceStore,
    settings: Settings,
    **clients,
) -> bool:
    """evidence-flow-spec.md §8: re-processed on a backoff schedule once
    imagery becomes available. Returns True if it completed this attempt."""
    request = store.get_request(request_id)
    if request is None or request.status != RequestStatus.INSUFFICIENT_DATA:
        return False

    gee_client = clients.get("gee_client") or GEEClient()
    imagery = ingest_imagery(
        gee_client,
        geometry,
        event_date,
        peril_type,
        minimum_valid_pixel_fraction=settings.minimum_valid_pixel_fraction,
    )
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
