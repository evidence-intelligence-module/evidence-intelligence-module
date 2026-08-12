"""The evidence-inputs manifest reaches the package (tasks.md T0-09).

Its purpose is a §65B chain-of-custody statement a reviewer can read in one
place: what was attempted, what came of it, and — critically — the difference
between "we looked and there was nothing" and "this never applied". Before
this, that answer was spread across four tables and could not be stated at
all. It is also the record the confidence tier's rule table reads from
(`issue/open query - confidence tier threshold values (FR-004).md`)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from evidence_intelligence.manifest import (
    EvidenceInputsManifest,
    InputOutcome,
)
from evidence_intelligence.packaging.report_generator import LocalObjectStorage
from evidence_intelligence.pipeline import run_pipeline
from evidence_intelligence.store.schema import PerilType
from tests.conftest import SAMPLE_GEOMETRY
from tests.fakes import FakeGEEClient, FakeIMDClient, FakeWeatherClient

EVENT_DATE = date(2026, 6, 15)


def _inputs(fake_store, test_settings, tmp_path, monkeypatch, scenario, peril) -> dict[str, dict]:
    monkeypatch.setenv("EVIDENCE_STORE_LOCAL_ROOT", str(tmp_path))
    request = fake_store.create_request(
        geometry=str(SAMPLE_GEOMETRY), event_date=EVENT_DATE, peril_type=peril
    )
    run_pipeline(
        request.request_id,
        SAMPLE_GEOMETRY,
        EVENT_DATE,
        peril,
        fake_store,
        test_settings,
        gee_client=FakeGEEClient(scenario=scenario, event_date=EVENT_DATE),
        weather_client=FakeWeatherClient(),
        imd_client=FakeIMDClient(),
        storage=LocalObjectStorage(test_settings.evidence_store_bucket),
    )
    package = fake_store.latest_package(request.request_id)
    record = json.loads(Path(package.json_uri.removeprefix("file://")).read_text(encoding="utf-8"))
    return {entry["input"]: entry for entry in record["evidence_inputs"]}


def test_package_carries_a_manifest_of_every_attempted_input(
    fake_store, test_settings, tmp_path, monkeypatch
):
    inputs = _inputs(
        fake_store, test_settings, tmp_path, monkeypatch, "healthy", PerilType.HAILSTORM
    )
    for expected in (
        "optical_pre_event",
        "optical_post_event",
        "sar_backscatter",
        "historical_baseline",
        "weather_precipitation",
        "imd_station_corroboration",
        "model_semi_physical",
        "model_ai_ml",
        "model_csm_assimilation",
    ):
        assert expected in inputs, f"{expected} missing from manifest"


def test_untrained_model_is_recorded_as_degraded_not_used(
    fake_store, test_settings, tmp_path, monkeypatch
):
    """Component 2 ships untrained. A package resting on a placeholder formula
    must say so in the record, not merely in a nested accuracy field."""
    inputs = _inputs(
        fake_store, test_settings, tmp_path, monkeypatch, "healthy", PerilType.HAILSTORM
    )
    assert inputs["model_ai_ml"]["outcome"] == InputOutcome.DEGRADED.value
    assert "untrained" in inputs["model_ai_ml"]["detail"]


def test_sar_substitution_is_recorded_as_degraded(
    fake_store, test_settings, tmp_path, monkeypatch
):
    """SAR standing in for unusable post-event optical is weaker evidence than
    having both, and the manifest is where that shows."""
    inputs = _inputs(fake_store, test_settings, tmp_path, monkeypatch, "flood", PerilType.FLOOD)
    assert inputs["sar_backscatter"]["outcome"] == InputOutcome.DEGRADED.value
    assert inputs["optical_post_event"]["outcome"] == InputOutcome.UNAVAILABLE.value
    assert inputs["model_semi_physical"]["outcome"] == InputOutcome.UNAVAILABLE.value


def test_inapplicable_is_distinguished_from_unavailable(
    fake_store, test_settings, tmp_path, monkeypatch
):
    """The distinction the manifest exists for. SAR is not attempted for a
    hailstorm — that is not a gap in the evidence — whereas the disabled CSM
    tier and a missing IMD record are different statements again."""
    inputs = _inputs(
        fake_store, test_settings, tmp_path, monkeypatch, "healthy", PerilType.HAILSTORM
    )
    assert inputs["sar_backscatter"]["outcome"] == InputOutcome.NOT_APPLICABLE.value
    assert inputs["model_csm_assimilation"]["outcome"] == InputOutcome.NOT_APPLICABLE.value
    assert inputs["imd_station_corroboration"]["outcome"] == InputOutcome.UNAVAILABLE.value


def test_missing_history_is_recorded_as_unavailable(
    fake_store, test_settings, tmp_path, monkeypatch
):
    inputs = _inputs(
        fake_store, test_settings, tmp_path, monkeypatch, "no_history", PerilType.HAILSTORM
    )
    assert inputs["historical_baseline"]["outcome"] == InputOutcome.UNAVAILABLE.value


# -- the manifest structure itself -------------------------------------------


def test_any_degraded_or_missing_ignores_not_applicable():
    """NOT_APPLICABLE must not read as a shortfall — otherwise every non-flood
    claim would look degraded merely for not needing SAR."""
    manifest = EvidenceInputsManifest()
    manifest.record("a", InputOutcome.USED)
    manifest.record("b", InputOutcome.NOT_APPLICABLE)
    assert manifest.any_degraded_or_missing() is False

    manifest.record("c", InputOutcome.DEGRADED)
    assert manifest.any_degraded_or_missing() is True
