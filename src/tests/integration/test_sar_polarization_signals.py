"""Integration tests for the SAR polarization signals
(`specs/002-satellite-evidence-parity/tasks.md` T0-15).

`modeling-approach.md` §6's DSI indicator table names cross-polarized **VH**
backscatter deviation as the structural-damage signal, and §3's Component 2
feature table names the VH/VV cross-pol ratio. The pipeline was feeding the
VH indicator a **VV** measurement — the flood detector's polarization, which
measures surface water rather than canopy structure. These tests pin the
distinction: VH drives the structural signals, VV drives flood extent, and
where VH wasn't acquired the VH-derived signals stay absent."""

from datetime import date

from evidence_intelligence.models.ai_ml import FEATURE_NAMES
from evidence_intelligence.packaging.report_generator import LocalObjectStorage
from evidence_intelligence.pipeline import _cross_pol_ratio_deviation, run_pipeline
from evidence_intelligence.store.schema import ModelComponent, PerilType
from tests.conftest import SAMPLE_GEOMETRY
from tests.fakes import FakeGEEClient, FakeIMDClient, FakeWeatherClient

EVENT_DATE = date(2026, 7, 20)


def _run(scenario: str, fake_store, test_settings, tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_STORE_LOCAL_ROOT", str(tmp_path))
    request = fake_store.create_request(
        geometry=str(SAMPLE_GEOMETRY), event_date=EVENT_DATE, peril_type=PerilType.FLOOD
    )
    run_pipeline(
        request.request_id,
        SAMPLE_GEOMETRY,
        EVENT_DATE,
        PerilType.FLOOD,
        fake_store,
        test_settings,
        gee_client=FakeGEEClient(scenario=scenario, event_date=EVENT_DATE),
        weather_client=FakeWeatherClient(),
        imd_client=FakeIMDClient(),
        storage=LocalObjectStorage(test_settings.evidence_store_bucket),
    )
    return request.request_id


def _ai_ml_features(fake_store, request_id) -> list[str]:
    result = fake_store.get_component_result(request_id, ModelComponent.AI_ML)
    return result.confidence_or_accuracy.get("features_supplied", [])


def test_cross_pol_feature_is_supplied_when_both_polarizations_were_measured(
    fake_store, test_settings, tmp_path, monkeypatch
):
    request_id = _run("flood", fake_store, test_settings, tmp_path, monkeypatch)
    assert "vh_vv_backscatter_deviation" in _ai_ml_features(fake_store, request_id)


def test_cross_pol_feature_is_absent_when_only_vv_was_acquired(
    fake_store, test_settings, tmp_path, monkeypatch
):
    """Single-polarization acquisitions must not produce a cross-pol ratio —
    there is no second polarization to take a ratio against."""
    request_id = _run("flood_single_pol", fake_store, test_settings, tmp_path, monkeypatch)
    assert "vh_vv_backscatter_deviation" not in _ai_ml_features(fake_store, request_id)


def _captured_dsi_indicators(monkeypatch) -> dict:
    """Captures what the pipeline hands `dsi.compute`.

    Asserted at the call boundary rather than through the DSI score, because
    with no SAR history to normalize against, `_min_max_normalize` returns a
    neutral 0.5 for the indicator whatever its value — so the score itself
    cannot distinguish a VH measurement from a VV one."""
    from evidence_intelligence.models import dsi

    captured: dict = {}
    original = dsi.compute

    def _spy(current_indicators, historical_indicators):
        captured.update(current_indicators)
        return original(current_indicators, historical_indicators)

    monkeypatch.setattr(dsi, "compute", _spy)
    return captured


def test_dsi_structural_indicator_receives_vh_not_vv(
    fake_store, test_settings, tmp_path, monkeypatch
):
    """The substitution this test exists to prevent: `sar_vh_backscatter_
    deviation` must carry the cross-polarized measurement, not the flood
    detector's co-polarized one. The fake reports VH 8.0 dB / VV 5.0 dB
    precisely so the two are distinguishable."""
    indicators = _captured_dsi_indicators(monkeypatch)
    _run("flood", fake_store, test_settings, tmp_path, monkeypatch)

    assert indicators["sar_vh_backscatter_deviation"] == 8.0  # VH, not VV's 5.0


def test_dsi_structural_indicator_is_absent_when_only_vv_was_acquired(
    fake_store, test_settings, tmp_path, monkeypatch
):
    indicators = _captured_dsi_indicators(monkeypatch)
    _run("flood_single_pol", fake_store, test_settings, tmp_path, monkeypatch)

    assert "sar_vh_backscatter_deviation" not in indicators


def test_dsi_still_scores_without_a_vh_measurement(
    fake_store, test_settings, tmp_path, monkeypatch
):
    """An absent VH indicator degrades the DSI to its remaining indicators
    rather than failing the request or substituting the VV measurement."""
    request_id = _run("flood_single_pol", fake_store, test_settings, tmp_path, monkeypatch)
    dsi_result = fake_store.get_component_result(request_id, ModelComponent.DSI)
    assert dsi_result is not None
    assert 0.0 <= dsi_result.point_estimate <= 1.0


def test_cross_pol_ratio_reduces_to_the_difference_of_the_two_drops():
    """In dB a ratio is a difference, so the change in (VH − VV) across the
    event equals `vh_drop − vv_drop` — no third measurement needed."""

    class _Sar:
        vh_drop_db = 8.0
        vv_drop_db = 5.0

    assert _cross_pol_ratio_deviation(_Sar()) == 3.0


def test_cross_pol_ratio_is_absent_when_either_polarization_is_missing():
    class _VvOnly:
        vh_drop_db = None
        vv_drop_db = 5.0

    class _VhOnly:
        vh_drop_db = 8.0
        vv_drop_db = None

    assert _cross_pol_ratio_deviation(_VvOnly()) is None
    assert _cross_pol_ratio_deviation(_VhOnly()) is None


def test_cross_pol_feature_name_matches_the_declared_feature_set():
    """Guards against the feature being populated under a name Component 2
    would silently ignore."""
    assert "vh_vv_backscatter_deviation" in FEATURE_NAMES
