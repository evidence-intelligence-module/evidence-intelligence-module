from evidence_intelligence.models.dsi import compute


def test_dsi_score_bounded_zero_one():
    current = {
        "ndvi_deviation": 0.4,
        "lswi_deviation": 0.2,
        "sar_vh_backscatter_deviation": 3.0,
        "fapar_deviation": 0.3,
        "crop_condition_variability": 0.1,
        "weather_anomaly_magnitude": 0.6,
    }
    historical = {
        "ndvi_deviation": [0.0, 0.1, 0.2, 0.3, 0.5],
        "lswi_deviation": [0.0, 0.1, 0.15, 0.2, 0.25],
        "sar_vh_backscatter_deviation": [0.0, 1.0, 2.0, 3.0, 4.0],
        "fapar_deviation": [0.0, 0.1, 0.2, 0.3, 0.4],
        "crop_condition_variability": [0.0, 0.05, 0.1, 0.15, 0.2],
        "weather_anomaly_magnitude": [0.0, 0.2, 0.4, 0.6, 0.8],
    }
    result = compute(current, historical)
    assert 0.0 <= result.score <= 1.0
    assert abs(sum(result.entropy_weights.values()) - 1.0) < 1e-9


def test_no_historical_archive_falls_back_to_midpoint_normalization():
    """FR-023: no fabricated baseline — indicators default to the 0.5
    midpoint rather than a made-up historical range."""
    current = {"ndvi_deviation": 0.9}
    historical = {"ndvi_deviation": []}
    result = compute(current, {**historical, **{k: [] for k in [
        "lswi_deviation", "sar_vh_backscatter_deviation", "fapar_deviation",
        "crop_condition_variability", "weather_anomaly_magnitude",
    ]}})
    assert result.normalized_indicators["ndvi_deviation"] == 0.5


def test_negative_relationship_indicator_is_inverted():
    current = {"crop_condition_variability": 1.0}
    historical = {"crop_condition_variability": [0.0, 0.5, 1.0]}
    filler = {k: [] for k in [
        "ndvi_deviation", "lswi_deviation", "sar_vh_backscatter_deviation",
        "fapar_deviation", "weather_anomaly_magnitude",
    ]}
    result = compute(current, {**historical, **filler})
    # Highest variability -> normalized toward 0 (lower confidence of uniform damage).
    assert result.normalized_indicators["crop_condition_variability"] == 0.0
