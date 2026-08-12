"""Regression tests for the Phase 0 base-pipeline corrections
(`specs/002-satellite-evidence-parity/tasks.md` T0-01 – T0-04, T0-12).

Each of these covers a path where the pipeline previously substituted a
default for an unmeasured input and reported the result as measured. The
shared property under test is that *absent stays absent*: an input the module
could not observe must never become a number in an evidence package."""

from __future__ import annotations

from datetime import date

import pytest

from evidence_intelligence.dates import shift_years
from evidence_intelligence.ingestion.weather import _anomaly_score, _observe
from evidence_intelligence.models.ai_ml import FEATURE_NAMES, _placeholder_estimate
from evidence_intelligence.models.semi_physical import (
    TEMPERATURE_UNIT_SANITY_RANGE_C,
    CropParameters,
    run,
)

# -- T0-12: leap-day-safe historical windows ----------------------------------


def test_shift_years_clamps_leap_day_to_28_february():
    assert shift_years(date(2024, 2, 29), -1) == date(2023, 2, 28)


def test_shift_years_preserves_leap_day_when_target_year_is_leap():
    assert shift_years(date(2024, 2, 29), -4) == date(2020, 2, 29)


def test_shift_years_leaves_ordinary_dates_untouched():
    assert shift_years(date(2026, 6, 15), -5) == date(2021, 6, 15)


# -- T0-01: temperature unit sanity -------------------------------------------


def test_kelvin_temperature_degrades_calibration_confidence():
    """A kelvin reading (~300) exceeds every crop temperature bound, so the
    model correctly produces zero biomass — but it must not report the 0.85
    confidence it reserves for plausible inputs, because the zero came from a
    unit error rather than from an observed heatwave."""
    result = run(
        pre_event_insolation_mj=18.0,
        pre_event_fapar=0.6,
        pre_event_lswi=0.3,
        pre_event_temp_c=298.15,
        post_event_insolation_mj=18.0,
        post_event_fapar=0.6,
        post_event_lswi=0.3,
        post_event_temp_c=298.15,
    )
    assert result.calibration_confidence == 0.5
    assert any("outside the range any celsius reading" in w for w in result.input_warnings)


def test_genuine_heatwave_above_crop_max_is_not_flagged_as_a_unit_error():
    """45 °C is beyond `CropParameters.temp_max_c` and legitimately zeroes
    biomass. It is a real reading, so it must carry no unit warning and keep
    full calibration confidence — the distinction the sanity range exists for."""
    params = CropParameters()
    assert params.temp_max_c < 45.0 < TEMPERATURE_UNIT_SANITY_RANGE_C[1]
    result = run(
        pre_event_insolation_mj=18.0,
        pre_event_fapar=0.6,
        pre_event_lswi=0.3,
        pre_event_temp_c=25.0,
        post_event_insolation_mj=18.0,
        post_event_fapar=0.6,
        post_event_lswi=0.3,
        post_event_temp_c=45.0,
    )
    assert result.input_warnings == []
    assert result.calibration_confidence == 0.85


# -- T0-03: every gridded source carries a baseline and an anomaly ------------


def _fetch_stub(values: dict[int, float]):
    """Returns a `_observe`-compatible fetch keyed by the window's end year."""

    def fetch(geometry, start, end):
        return values.get(end.year)

    return fetch


def test_observe_computes_baseline_and_relative_anomaly():
    observation = _observe(
        _fetch_stub({2026: 90.0, 2025: 45.0, 2024: 45.0, 2023: 45.0, 2022: 45.0, 2021: 45.0}),
        geometry={},
        window_start=date(2026, 6, 8),
        window_end=date(2026, 6, 18),
        source_dataset="stub",
        source_version="stub-v1",
    )
    assert observation.historical_baseline == 45.0
    assert observation.anomaly_score == 1.0  # 90 is +100% against a 45 baseline


def test_observe_uses_absolute_deviation_for_temperature():
    observation = _observe(
        _fetch_stub({2026: 31.0, 2025: 25.0, 2024: 25.0, 2023: 25.0, 2022: 25.0, 2021: 25.0}),
        geometry={},
        window_start=date(2026, 6, 8),
        window_end=date(2026, 6, 18),
        source_dataset="stub",
        source_version="stub-v1",
        relative_anomaly=False,
    )
    assert observation.anomaly_score == 6.0  # degrees, not a ratio


def test_observe_reports_no_anomaly_when_no_history_exists():
    observation = _observe(
        _fetch_stub({2026: 90.0}),
        geometry={},
        window_start=date(2026, 6, 8),
        window_end=date(2026, 6, 18),
        source_dataset="stub",
        source_version="stub-v1",
    )
    assert observation.observed_value == 90.0
    assert observation.historical_baseline is None
    assert observation.anomaly_score is None


def test_relative_anomaly_against_a_zero_baseline_is_absent_not_zero():
    assert _anomaly_score(5.0, 0.0, relative=True) is None


def test_absolute_anomaly_against_a_zero_baseline_is_valid():
    """0 °C is a real baseline, so the absolute form must still produce a
    deviation where the relative form cannot."""
    assert _anomaly_score(5.0, 0.0, relative=False) == 5.0


# -- T0-04: the fallback estimate reflects what was measured ------------------


def test_placeholder_estimate_ignores_features_that_were_never_supplied():
    """The same measured deviations must produce the same estimate regardless
    of how many other features the pipeline happens not to populate."""
    supplied = {"ndvi_deviation": 0.4, "rainfall_anomaly": 0.8}
    padded = dict.fromkeys(FEATURE_NAMES, 0.0) | supplied

    assert _placeholder_estimate(supplied) > _placeholder_estimate(padded)
    assert _placeholder_estimate(supplied) == pytest.approx(0.3)  # mean(0.4, 0.8) / 2


def test_placeholder_estimate_with_no_measured_features_is_zero():
    assert _placeholder_estimate({}) == 0.0


def test_placeholder_estimate_ignores_unknown_feature_names():
    assert _placeholder_estimate({"ndvi_deviation": 0.4, "not_a_feature": 99.0}) == 0.2
