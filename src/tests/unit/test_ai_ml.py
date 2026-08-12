from evidence_intelligence.models.ai_ml import AiMlModel


def test_untrained_model_discloses_placeholder_status_not_fabricated_accuracy():
    """Constitution §2.2 / CLAUDE.md: never invent a figure — an untrained
    model must say so, not present a fake MAE/RMSE/NRMSE."""
    model = AiMlModel()
    result = model.predict({"ndvi_deviation": 0.3}, harvest_index=0.4)
    assert result.confidence_or_accuracy["status"] == "untrained_placeholder"
    assert result.confidence_or_accuracy["mae"] is None
    assert result.confidence_or_accuracy["rmse"] is None
    assert result.confidence_or_accuracy["nrmse"] is None


def test_prediction_is_deterministic_for_reproducibility():
    """FR-021/SC-005: same inputs must yield the same output."""
    model = AiMlModel()
    feature_vector = {"ndvi_deviation": 0.4, "rainfall_anomaly": -0.6}
    result_1 = model.predict(feature_vector, harvest_index=0.4)
    result_2 = model.predict(feature_vector, harvest_index=0.4)
    assert result_1.damage_fraction == result_2.damage_fraction


def test_damage_fraction_bounded_zero_one():
    model = AiMlModel()
    result = model.predict({name: 999.0 for name in ["ndvi_deviation"]}, harvest_index=0.4)
    assert 0.0 <= result.damage_fraction <= 1.0


def test_yield_loss_fraction_scaled_by_harvest_index():
    model = AiMlModel()
    result = model.predict({"ndvi_deviation": 0.5}, harvest_index=0.5)
    assert result.yield_loss_fraction == result.damage_fraction * 0.5


def test_trained_model_reports_supplied_validation_metrics():
    import numpy as np

    from evidence_intelligence.models.ai_ml import FEATURE_NAMES

    model = AiMlModel()
    features = np.random.RandomState(0).rand(20, len(FEATURE_NAMES))
    labels = np.random.RandomState(1).rand(20)
    model.fit(features, labels, validation_metrics={"mae": 0.05, "rmse": 0.08, "nrmse": 0.12})

    result = model.predict({name: 0.1 for name in FEATURE_NAMES}, harvest_index=0.4)
    assert result.confidence_or_accuracy["status"] == "trained"
    assert result.confidence_or_accuracy["nrmse"] == 0.12
