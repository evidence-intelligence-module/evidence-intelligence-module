from evidence_intelligence.causation.scoring import score
from evidence_intelligence.store.schema import PerilType


def test_perfect_alignment_scores_high():
    result = score(
        days_between_event_and_ndvi_drop=2,
        distance_km_to_weather_anomaly=0.0,
        normalized_weather_anomaly=0.8,
        normalized_ndvi_drop=0.8,
        peril_type=PerilType.HAILSTORM,
        phenology_flag=None,
        low_confidence_threshold=None,
    )
    assert result.score >= 90


def test_poor_alignment_scores_low():
    result = score(
        days_between_event_and_ndvi_drop=30,
        distance_km_to_weather_anomaly=20.0,
        normalized_weather_anomaly=0.1,
        normalized_ndvi_drop=0.9,
        peril_type=PerilType.HAILSTORM,
        phenology_flag="crop calendar mismatch",
        low_confidence_threshold=None,
    )
    assert result.score < 40


def test_score_never_suppresses_result_below_threshold():
    """FR-024: package still delivered, just labeled — never rejected."""
    result = score(
        days_between_event_and_ndvi_drop=30,
        distance_km_to_weather_anomaly=20.0,
        normalized_weather_anomaly=0.1,
        normalized_ndvi_drop=0.9,
        peril_type=PerilType.HAILSTORM,
        phenology_flag=None,
        low_confidence_threshold=50,
    )
    assert result.low_confidence is True
    assert isinstance(result.score, int)


def test_no_threshold_configured_never_flags_low_confidence():
    """Threshold is unset by default (issue FR-024) — never auto-labels."""
    result = score(
        days_between_event_and_ndvi_drop=30,
        distance_km_to_weather_anomaly=20.0,
        normalized_weather_anomaly=0.1,
        normalized_ndvi_drop=0.9,
        peril_type=PerilType.HAILSTORM,
        phenology_flag=None,
        low_confidence_threshold=None,
    )
    assert result.low_confidence is False


def test_other_peril_uses_generic_neutral_plausibility():
    result = score(
        days_between_event_and_ndvi_drop=5,
        distance_km_to_weather_anomaly=0.0,
        normalized_weather_anomaly=0.5,
        normalized_ndvi_drop=0.5,
        peril_type=PerilType.OTHER,
        phenology_flag=None,
        low_confidence_threshold=None,
    )
    assert result.physiological_plausibility == 50.0


def test_score_is_bounded_zero_to_hundred():
    result = score(
        days_between_event_and_ndvi_drop=100,
        distance_km_to_weather_anomaly=100.0,
        normalized_weather_anomaly=0.0,
        normalized_ndvi_drop=1.0,
        peril_type=PerilType.DROUGHT,
        phenology_flag="mismatch",
        low_confidence_threshold=None,
    )
    assert 0 <= result.score <= 100
