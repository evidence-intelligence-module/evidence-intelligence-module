"""Unit tests for pipeline._load_ai_ml_model: the wiring between
AI_ML_MODEL_PATH (config.py) and the trained-model artifact (ai_ml.py)."""

import numpy as np
import pytest

from evidence_intelligence.config import DEFAULT_DAMAGE_CLASSIFICATION_BANDS, Settings
from evidence_intelligence.models.ai_ml import FEATURE_NAMES, AiMlModel
from evidence_intelligence.pipeline import _ai_ml_model_cache, _load_ai_ml_model


@pytest.fixture(autouse=True)
def _clear_cache():
    _ai_ml_model_cache.clear()
    yield
    _ai_ml_model_cache.clear()


def _settings(ai_ml_model_path=None) -> Settings:
    return Settings(
        gee_service_account_credentials=None,
        gee_service_account_email=None,
        database_url="sqlite:///:memory:",
        evidence_store_bucket="test-bucket",
        causation_low_confidence_threshold=None,
        csm_high_scrutiny_enabled=False,
        ai_ml_model_path=ai_ml_model_path,
        minimum_valid_pixel_fraction=None,
        damage_classification_bands=DEFAULT_DAMAGE_CLASSIFICATION_BANDS,
    )


def test_no_path_configured_returns_untrained_model():
    model = _load_ai_ml_model(_settings(ai_ml_model_path=None))
    result = model.predict({"ndvi_deviation": 0.3}, harvest_index=0.4)
    assert result.confidence_or_accuracy["status"] == "untrained_placeholder"


def test_configured_path_loads_trained_model(tmp_path):
    rng = np.random.RandomState(0)
    trained = AiMlModel()
    trained.fit(rng.rand(30, len(FEATURE_NAMES)), rng.rand(30))
    trained.evaluate(rng.rand(10, len(FEATURE_NAMES)), rng.rand(10))
    save_path = tmp_path / "model.joblib"
    trained.save(save_path, label_provenance="test fixture labels, synthetic")

    model = _load_ai_ml_model(_settings(ai_ml_model_path=str(save_path)))
    result = model.predict({name: 0.1 for name in FEATURE_NAMES}, harvest_index=0.4)
    assert result.confidence_or_accuracy["status"] == "trained"


def test_missing_file_falls_back_to_untrained_not_crash(tmp_path):
    model = _load_ai_ml_model(_settings(ai_ml_model_path=str(tmp_path / "does-not-exist.joblib")))
    result = model.predict({"ndvi_deviation": 0.3}, harvest_index=0.4)
    assert result.confidence_or_accuracy["status"] == "untrained_placeholder"


def test_model_is_cached_across_calls(tmp_path):
    rng = np.random.RandomState(0)
    trained = AiMlModel()
    trained.fit(rng.rand(30, len(FEATURE_NAMES)), rng.rand(30))
    save_path = tmp_path / "model.joblib"
    trained.save(save_path, label_provenance="test fixture labels, synthetic")

    settings = _settings(ai_ml_model_path=str(save_path))
    first = _load_ai_ml_model(settings)
    second = _load_ai_ml_model(settings)
    assert first is second
