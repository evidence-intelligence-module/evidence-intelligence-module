"""Characterization-fixture harness (tasks.md T0R-01).

Records the full observable output of `run_pipeline` for a fixed set of
scenarios, so that every later step of the Phase 0.4 decomposition can be
checked against "did any number change?" rather than against hope.

These snapshots capture behaviour **as it is today, including the parts known
to be wrong** — see `pipeline-decomposition-design.md` §8.1. They are a
change-detector, not a correctness oracle. Each scenario therefore carries a
label:

- `pinned`      — any diff is a regression; the refactor must not move these.
- `known-wrong` — expected to change, naming the task that changes it and why.

Regenerate with `python scripts/record_golden_fixtures.py` after a task that
is *supposed* to flip a `known-wrong` fixture, and review the diff as part of
that task rather than as a separate cleanup.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from evidence_intelligence.config import DEFAULT_DAMAGE_CLASSIFICATION_BANDS, Settings
from evidence_intelligence.packaging.report_generator import LocalObjectStorage
from evidence_intelligence.pipeline import run_pipeline
from evidence_intelligence.store.schema import PerilType
from tests.fakes import FakeEvidenceStore, FakeGEEClient, FakeIMDClient, FakeWeatherClient

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "golden"

SAMPLE_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[[77.0, 20.0], [77.01, 20.0], [77.01, 20.01], [77.0, 20.01], [77.0, 20.0]]],
}

EVENT_DATE = date(2026, 6, 15)

PINNED = "pinned"
KNOWN_WRONG = "known-wrong"


@dataclass(frozen=True)
class Scenario:
    name: str
    gee_scenario: str
    peril_type: PerilType
    label: str
    reason: str
    csm_enabled: bool = False
    valid_pixel_fraction: float | None = 0.95
    minimum_valid_pixel_fraction: float | None = None


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        name="healthy_hailstorm",
        gee_scenario="healthy",
        peril_type=PerilType.HAILSTORM,
        label=PINNED,
        reason="The main COMPLETE path: pre/post optical pair, all components run. "
        "Nothing in Phase 0.4 may change this output.",
    ),
    Scenario(
        name="flood_sar_substitution",
        gee_scenario="flood",
        peril_type=PerilType.FLOOD,
        label=PINNED,
        reason="Post-event optical unusable, SAR substitutes. Exercises the path where "
        "Component 1 is absent from the ensemble and NDVI-derived signals stay absent.",
    ),
    Scenario(
        name="flood_single_polarization",
        gee_scenario="flood_single_pol",
        peril_type=PerilType.FLOOD,
        label=PINNED,
        reason="VH absent (T0-15): the cross-pol feature and the VH DSI indicator must "
        "stay absent rather than falling back to the VV measurement.",
    ),
    Scenario(
        name="csm_high_scrutiny_enabled",
        gee_scenario="healthy",
        peril_type=PerilType.HAILSTORM,
        label=PINNED,
        reason="The only coverage of the Component 3 path. T0R-04 moves this gating from "
        "an inline conditional into registry construction; the output must not move with it.",
    ),
    Scenario(
        name="partial_cloud_coverage",
        gee_scenario="healthy",
        peril_type=PerilType.HAILSTORM,
        label=PINNED,
        reason="Low valid_pixel_fraction with the usability gate set (T0-07), so the "
        "coverage disclosure and the gating decision are both captured.",
        valid_pixel_fraction=0.35,
        minimum_valid_pixel_fraction=0.5,
    ),
    Scenario(
        name="varied_historical_archive",
        gee_scenario="varied_history",
        peril_type=PerilType.HAILSTORM,
        label=PINNED,
        reason="The only scenario where the DSI's min-max normalization has a real range "
        "to work against — every other archive is five identical values, so `hi == lo` "
        "and normalization returns the 0.5 midpoint whatever the weights are. Without "
        "this, no fixture can tell a working DSI from a collapsed one, and T0R-05's gate "
        "would be vacuous. Also pins the quantity mismatch described in T0R-05's note: "
        "the archive holds absolute NDVI index values while the current indicator is a "
        "deviation, so the normalized result clips rather than ranking.",
    ),
    Scenario(
        name="no_imagery_weather_only",
        gee_scenario="no_imagery",
        peril_type=PerilType.DROUGHT,
        label=KNOWN_WRONG,
        reason="T0R-06 unifies the two package paths, so this WEATHER_ONLY_PRELIMINARY "
        "package gains the evidence-inputs manifest and the coverage statement it lacks "
        "today. It must NOT gain the Harvest Index / damage-band statements, which "
        "describe figures this tier does not contain.",
    ),
    Scenario(
        name="no_historical_archive",
        gee_scenario="no_history",
        peril_type=PerilType.HAILSTORM,
        label=KNOWN_WRONG,
        reason="T0R-05: with no archive for any indicator, _entropy_weights currently "
        "falls back to uniform 1/6 over six 0.5 midpoints, producing a confident-looking "
        "dsi_score of 0.5 from no historical evidence at all. After the fix no indicator "
        "contributes and the score becomes null.",
    ),
)


def _settings(scenario: Scenario) -> Settings:
    return Settings(
        gee_service_account_credentials=None,
        gee_service_account_email=None,
        database_url="sqlite:///:memory:",
        evidence_store_bucket="golden-fixtures",
        causation_low_confidence_threshold=None,
        csm_high_scrutiny_enabled=scenario.csm_enabled,
        ai_ml_model_path=None,
        minimum_valid_pixel_fraction=scenario.minimum_valid_pixel_fraction,
        damage_classification_bands=DEFAULT_DAMAGE_CLASSIFICATION_BANDS,
    )


def _round(value):
    """Stabilise float formatting across platforms without hiding real drift.

    10 decimal places is far below any figure this pipeline reports and far
    above the noise floor of the arithmetic involved, so a diff at this
    precision is a real change, not a rounding artifact.
    """
    if isinstance(value, float):
        return round(value, 10)
    if isinstance(value, dict):
        return {k: _round(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_round(v) for v in value]
    return value


def _normalize_package_json(content: dict) -> dict:
    """Strip the fields that vary per run rather than per behaviour.

    `request_id` comes from a global counter (so it depends on test ordering),
    `generated_at` from the wall clock, and `checksum` is a hash over both — so
    all three change on every run without anything having changed.
    """
    normalized = dict(content)
    normalized["request_id"] = "<request-id>"
    normalized["generated_at"] = "<timestamp>"
    return _round(normalized)


def run_scenario(scenario: Scenario, tmp_root: Path) -> dict:
    """Run the pipeline once and return its full observable output."""
    import os

    os.environ["EVIDENCE_STORE_LOCAL_ROOT"] = str(tmp_root)

    store = FakeEvidenceStore()
    settings = _settings(scenario)
    request = store.create_request(
        geometry=str(SAMPLE_GEOMETRY),
        event_date=EVENT_DATE,
        peril_type=scenario.peril_type,
    )

    run_pipeline(
        request.request_id,
        SAMPLE_GEOMETRY,
        EVENT_DATE,
        scenario.peril_type,
        store,
        settings,
        gee_client=FakeGEEClient(
            scenario=scenario.gee_scenario,
            event_date=EVENT_DATE,
            valid_pixel_fraction=scenario.valid_pixel_fraction,
        ),
        weather_client=FakeWeatherClient(),
        imd_client=FakeIMDClient(),
        storage=LocalObjectStorage(settings.evidence_store_bucket),
    )

    package = store.latest_package(request.request_id)
    package_json = None
    if package is not None:
        package_json = _normalize_package_json(
            json.loads(Path(package.json_uri.replace("file://", "")).read_text())
        )

    return {
        "_label": scenario.label,
        "_label_reason": scenario.reason,
        "request_status": store.get_request(request.request_id).status.value,
        "package_tier": package.package_tier.value if package else None,
        "package_json": package_json,
        "component_results": [
            {
                "component": r.component.value,
                "methodology_version": r.methodology_version,
                "point_estimate": _round(r.point_estimate),
                "damage_classification": r.damage_classification,
                "affected_area_ha": _round(r.affected_area_ha),
                "confidence_or_accuracy": _round(r.confidence_or_accuracy),
            }
            for r in store.list_component_results(request.request_id)
        ],
        "satellite_results": [
            {
                "source_dataset": r.source_dataset,
                "source_version": r.source_version,
                "acquisition_date": str(r.acquisition_date),
                "pre_event_index_value": _round(r.pre_event_index_value),
                "post_event_index_value": _round(r.post_event_index_value),
                "flood_extent_geometry": r.flood_extent_geometry,
            }
            for r in store.list_satellite_results(request.request_id)
        ],
        "weather_results": [
            {
                "source_dataset": r.source_dataset,
                "source_version": r.source_version,
                "observed_value": _round(r.observed_value),
                "historical_baseline": _round(r.historical_baseline),
                "anomaly_score": _round(r.anomaly_score),
                "causation_confidence_score": r.causation_confidence_score,
            }
            for r in store.list_weather_results(request.request_id)
        ],
    }


def fixture_path(scenario: Scenario) -> Path:
    return FIXTURE_DIR / f"{scenario.name}.json"


def load_fixture(scenario: Scenario) -> dict:
    return json.loads(fixture_path(scenario).read_text(encoding="utf-8"))


def write_fixture(scenario: Scenario, snapshot: dict) -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    fixture_path(scenario).write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


__all__ = [
    "KNOWN_WRONG",
    "PINNED",
    "SCENARIOS",
    "Scenario",
    "fixture_path",
    "load_fixture",
    "replace",
    "run_scenario",
    "write_fixture",
]
