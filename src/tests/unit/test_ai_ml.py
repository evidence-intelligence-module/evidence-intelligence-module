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


def test_trained_but_unevaluated_model_reports_null_metrics_not_fabricated():
    """A model that's been fit() but not yet evaluate()'d is genuinely
    'trained', but has no real accuracy figures yet — still never fabricated."""
    import numpy as np

    from evidence_intelligence.models.ai_ml import FEATURE_NAMES

    model = AiMlModel()
    features = np.random.RandomState(0).rand(20, len(FEATURE_NAMES))
    labels = np.random.RandomState(1).rand(20)
    model.fit(features, labels)

    result = model.predict({name: 0.1 for name in FEATURE_NAMES}, harvest_index=0.4)
    assert result.confidence_or_accuracy["status"] == "trained"
    assert result.confidence_or_accuracy["mae"] is None


def test_evaluate_records_real_metrics_from_held_out_data():
    import numpy as np

    from evidence_intelligence.models.ai_ml import FEATURE_NAMES

    rng = np.random.RandomState(0)
    train_features, train_labels = rng.rand(50, len(FEATURE_NAMES)), rng.rand(50)
    val_features, val_labels = rng.rand(10, len(FEATURE_NAMES)), rng.rand(10)

    model = AiMlModel()
    model.fit(train_features, train_labels)
    metrics = model.evaluate(val_features, val_labels)

    assert metrics["mae"] >= 0
    assert metrics["rmse"] >= 0
    assert metrics["nrmse"] is None or metrics["nrmse"] >= 0

    result = model.predict({name: 0.1 for name in FEATURE_NAMES}, harvest_index=0.4)
    assert result.confidence_or_accuracy["mae"] == metrics["mae"]


def test_evaluate_before_fit_raises():
    import numpy as np
    import pytest

    from evidence_intelligence.models.ai_ml import FEATURE_NAMES

    model = AiMlModel()
    with pytest.raises(RuntimeError):
        model.evaluate(np.zeros((5, len(FEATURE_NAMES))), np.zeros(5))


def test_save_untrained_model_raises(tmp_path):
    import pytest

    model = AiMlModel()
    with pytest.raises(RuntimeError):
        model.save(tmp_path / "model.joblib", label_provenance="test fixture labels, synthetic")


def test_save_and_load_round_trip_preserves_predictions(tmp_path):
    import numpy as np

    from evidence_intelligence.models.ai_ml import FEATURE_NAMES

    rng = np.random.RandomState(0)
    model = AiMlModel()
    model.fit(rng.rand(50, len(FEATURE_NAMES)), rng.rand(50))
    model.evaluate(rng.rand(10, len(FEATURE_NAMES)), rng.rand(10))

    save_path = tmp_path / "model.joblib"
    model.save(save_path, label_provenance="test fixture labels, synthetic")
    loaded = AiMlModel.load(save_path)

    feature_vector = {name: 0.3 for name in FEATURE_NAMES}
    original_result = model.predict(feature_vector, harvest_index=0.4)
    loaded_result = loaded.predict(feature_vector, harvest_index=0.4)

    assert loaded_result.damage_fraction == original_result.damage_fraction
    assert loaded_result.confidence_or_accuracy["status"] == "trained"
    assert (
        loaded_result.confidence_or_accuracy["mae"]
        == original_result.confidence_or_accuracy["mae"]
    )


def test_save_requires_label_provenance(tmp_path):
    """Sourcing training data is out of scope (constitution.md §9.2), so the
    module cannot verify where labels came from — which is exactly why it must
    refuse to persist an artifact that does not say. A calibrated accuracy
    figure in a §65B package with no statement about the data behind it is the
    outcome this guards against."""
    import numpy as np
    import pytest

    from evidence_intelligence.models.ai_ml import FEATURE_NAMES

    rng = np.random.RandomState(0)
    model = AiMlModel()
    model.fit(rng.rand(50, len(FEATURE_NAMES)), rng.rand(50))

    for empty in ("", "   "):
        with pytest.raises(ValueError, match="label_provenance is required"):
            model.save(tmp_path / "model.joblib", label_provenance=empty)

    assert not (tmp_path / "model.joblib").exists()


def test_label_provenance_round_trips_into_every_prediction(tmp_path):
    """It has to reach `confidence_or_accuracy`, because that dict is what the
    pipeline copies into the package's accuracy statement. Recorded in the
    artifact but absent from the prediction would disclose nothing."""
    import numpy as np

    from evidence_intelligence.models.ai_ml import FEATURE_NAMES

    rng = np.random.RandomState(0)
    model = AiMlModel()
    model.fit(rng.rand(50, len(FEATURE_NAMES)), rng.rand(50))
    model.evaluate(rng.rand(10, len(FEATURE_NAMES)), rng.rand(10))

    save_path = tmp_path / "model.joblib"
    model.save(save_path, label_provenance="  insurer pilot survey, Maharashtra, non-CCE  ")
    loaded = AiMlModel.load(save_path)

    result = loaded.predict({name: 0.3 for name in FEATURE_NAMES}, harvest_index=0.4)
    assert (
        result.confidence_or_accuracy["label_provenance"]
        == "insurer pilot survey, Maharashtra, non-CCE"
    )


def test_untrained_model_reports_no_label_provenance():
    """The untrained placeholder has no training data, so it must not claim a
    provenance for one. This also keeps the untrained path — the one every
    golden fixture exercises — byte-identical to before the field existed."""
    result = AiMlModel().predict({"ndvi_deviation": 0.4}, harvest_index=0.4)

    assert result.confidence_or_accuracy["status"] == "untrained_placeholder"
    assert "label_provenance" not in result.confidence_or_accuracy


def test_load_of_artifact_without_provenance_says_so(tmp_path):
    """Artifacts saved before the field was mandatory still load — and report
    'not recorded' rather than an empty string, because a blank provenance
    reads as one that was declared and left empty."""
    import joblib
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor

    from evidence_intelligence.models.ai_ml import (
        FEATURE_NAMES,
        HYPERPARAMETERS,
        METHODOLOGY_VERSION,
    )

    rng = np.random.RandomState(0)
    legacy = RandomForestRegressor(**HYPERPARAMETERS)
    legacy.fit(rng.rand(50, len(FEATURE_NAMES)), rng.rand(50))

    save_path = tmp_path / "legacy.joblib"
    joblib.dump(
        {
            "model": legacy,
            "validation_metrics": {"mae": 0.1, "rmse": 0.2, "nrmse": 0.3},
            "feature_names": FEATURE_NAMES,
            "methodology_version": METHODOLOGY_VERSION,
        },
        save_path,
    )

    result = AiMlModel.load(save_path).predict(
        {name: 0.3 for name in FEATURE_NAMES}, harvest_index=0.4
    )
    assert result.confidence_or_accuracy["label_provenance"] == "not recorded"


def test_load_rejects_mismatched_feature_names(tmp_path, monkeypatch):
    import numpy as np
    import pytest

    from evidence_intelligence.models import ai_ml as ai_ml_module

    rng = np.random.RandomState(0)
    model = AiMlModel()
    model.fit(rng.rand(20, len(ai_ml_module.FEATURE_NAMES)), rng.rand(20))
    save_path = tmp_path / "model.joblib"
    model.save(save_path, label_provenance="test fixture labels, synthetic")

    monkeypatch.setattr(ai_ml_module, "FEATURE_NAMES", ["a_completely_different_feature_set"])
    with pytest.raises(ValueError):
        ai_ml_module.AiMlModel.load(save_path)
