"""Characterization-fixture harness (tasks.md T0R-01).

Records the full observable output of `run_pipeline` for a fixed set of
scenarios, so that every later step of the Phase 0.4 decomposition can be
checked against "did any number change?" rather than against hope.

These snapshots capture behaviour **as it is today, including the parts known
to be wrong** — see `pipeline-decomposition-design.md` §8.1. They are a
change-detector, not a correctness oracle.

**Labels are per-field, not per-fixture.** The first version of this harness
labelled whole scenarios `pinned`/`known-wrong`, which was wrong in a way worth
recording: every fixture's `causation_confidence_score` is fabricated (see
`known_wrong` below), so labelling a scenario `pinned` because its *damage*
figures were trusted also pinned a causation figure that is false. A snapshot
is a mixture of trustworthy and untrustworthy values, and the label has to be
able to say which is which.

So: **every recorded value is pinned unless it appears in the scenario's
`known_wrong` map**, which names the task that will change it and why. Any diff
outside that map is a regression. A diff inside it is the named task doing its
job — re-record with `python scripts/record_golden_fixtures.py` *as part of that
task*, and review the diff in that task's commit.

Re-recording to make a red suite go green defeats the entire purpose.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
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

# Fabricated on every path, so every scenario inherits it (see T0-06). Kept as a
# shared constant rather than repeated per scenario, because the day it stops
# being true it must stop being true everywhere at once.
CAUSATION_KNOWN_WRONG = {
    "package_json.causation_confidence_score": (
        "T0-06: 55 of the 100 points are hardcoded at the call site "
        "(days_between=1 -> temporal 100, distance_km=0.0 -> spatial 100). The "
        "magnitude term additionally scores an unmeasured NDVI drop as a "
        "measured 0.0, and phenology_flag=None is read as 'checked and passed' "
        "(90) rather than 'never checked'. Net effect: a request with no "
        "imagery at all scores 98/100, higher than one with a full optical pair."
    ),
    "weather_results[0].causation_confidence_score": (
        "T0-06: same figure, as persisted. See the package_json entry."
    ),
}


@dataclass(frozen=True)
class Scenario:
    name: str
    gee_scenario: str
    peril_type: PerilType
    purpose: str
    """What this scenario exists to cover — why it is in the set at all."""

    known_wrong: Mapping[str, str] = field(default_factory=dict)
    """Dotted paths into the snapshot whose recorded value is known to be wrong,
    mapped to the task that will change it and why. Everything not listed here
    is pinned: a diff outside this map is a regression."""

    csm_enabled: bool = False
    valid_pixel_fraction: float | None = 0.95
    minimum_valid_pixel_fraction: float | None = None


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        name="healthy_hailstorm",
        gee_scenario="healthy",
        peril_type=PerilType.HAILSTORM,
        purpose="The main COMPLETE path: pre/post optical pair, all components run.",
        known_wrong=dict(CAUSATION_KNOWN_WRONG),
    ),
    Scenario(
        name="flood_sar_substitution",
        gee_scenario="flood",
        peril_type=PerilType.FLOOD,
        purpose="Post-event optical unusable, SAR substitutes; Component 1 absent from "
        "the ensemble and NDVI-derived signals stay absent.",
        known_wrong=dict(CAUSATION_KNOWN_WRONG),
    ),
    Scenario(
        name="flood_single_polarization",
        gee_scenario="flood_single_pol",
        peril_type=PerilType.FLOOD,
        purpose="VH absent (T0-15): the cross-pol feature and the VH DSI indicator must "
        "stay absent rather than falling back to the VV measurement.",
        known_wrong=dict(CAUSATION_KNOWN_WRONG),
    ),
    Scenario(
        name="csm_high_scrutiny_enabled",
        gee_scenario="healthy",
        peril_type=PerilType.HAILSTORM,
        purpose="The only coverage of the Component 3 path. T0R-04 moves this gating "
        "from an inline conditional into registry construction.",
        csm_enabled=True,
        known_wrong=dict(CAUSATION_KNOWN_WRONG),
    ),
    Scenario(
        name="partial_cloud_coverage",
        gee_scenario="healthy",
        peril_type=PerilType.HAILSTORM,
        purpose="Low valid_pixel_fraction with the usability gate set (T0-07), so the "
        "coverage disclosure and the gating decision are both captured.",
        valid_pixel_fraction=0.35,
        minimum_valid_pixel_fraction=0.5,
        known_wrong={
            **CAUSATION_KNOWN_WRONG,
            "package_json.evidence_inputs": (
                "T0R-06: the WEATHER_ONLY_PRELIMINARY path builds its package through a "
                "duplicate assembly path that never passes the evidence-inputs manifest, "
                "so this records [] where a manifest belongs."
            ),
        },
    ),
    Scenario(
        name="varied_historical_archive",
        gee_scenario="varied_history",
        peril_type=PerilType.HAILSTORM,
        purpose="The only scenario where the DSI's min-max normalization has a real "
        "range to work against — every other archive is five identical values, so "
        "hi == lo and normalization returns the 0.5 midpoint whatever the weights are. "
        "Without this, no fixture can tell a working DSI from a collapsed one.",
        known_wrong={
            **CAUSATION_KNOWN_WRONG,
            "package_json.damage_severity_index.value": (
                "T05-10: the archive holds absolute NDVI index values while the "
                "indicator is a deviation. Normalizing a 0.45 drop against a 0.62-0.81 "
                "index range clips below the floor, so this records DSI 0.0 for a field "
                "that lost 0.45 NDVI — and it errs against the claimant."
            ),
        },
    ),
    Scenario(
        name="no_imagery_weather_only",
        gee_scenario="no_imagery",
        peril_type=PerilType.DROUGHT,
        purpose="No usable imagery of any kind: the WEATHER_ONLY_PRELIMINARY tier.",
        known_wrong={
            **CAUSATION_KNOWN_WRONG,
            "package_json.evidence_inputs": (
                "T0R-06: as partial_cloud_coverage — the duplicate preliminary assembly "
                "path never passes the manifest."
            ),
        },
    ),
    Scenario(
        name="no_historical_archive",
        gee_scenario="no_history",
        peril_type=PerilType.HAILSTORM,
        purpose="No historical archive for any indicator.",
        known_wrong={
            **CAUSATION_KNOWN_WRONG,
            "package_json.damage_severity_index.value": (
                "T0R-05: with no archive at all, _entropy_weights falls back to uniform "
                "1/6 over six 0.5 midpoints, producing a confident-looking 0.5 from no "
                "historical evidence whatsoever. After the fix no indicator contributes "
                "and the score becomes null."
            ),
        },
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
        "_purpose": scenario.purpose,
        "_known_wrong": dict(scenario.known_wrong),
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


_MISSING = object()


def resolve_path(snapshot: dict, path: str):
    """Resolve a dotted path like `weather_results[0].causation_confidence_score`.

    Returns `_MISSING` when any step does not exist, which is what lets the test
    suite catch a `known_wrong` entry that has gone stale — an excuse for a
    fabricated value must stop existing when the value does.
    """
    current = snapshot
    for step in path.split("."):
        name, _, index = step.partition("[")
        if name:
            if not isinstance(current, dict) or name not in current:
                return _MISSING
            current = current[name]
        if index:
            position = int(index.rstrip("]"))
            if not isinstance(current, list) or position >= len(current):
                return _MISSING
            current = current[position]
    return current


def path_exists(snapshot: dict, path: str) -> bool:
    return resolve_path(snapshot, path) is not _MISSING


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
    "CAUSATION_KNOWN_WRONG",
    "SCENARIOS",
    "Scenario",
    "fixture_path",
    "resolve_path",
    "load_fixture",
    "replace",
    "run_scenario",
    "write_fixture",
]
