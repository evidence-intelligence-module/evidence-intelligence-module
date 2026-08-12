from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from evidence_intelligence.api import create_app
from evidence_intelligence.api.dependencies import get_settings, get_store
from evidence_intelligence.config import Settings
from tests.fakes import FakeEvidenceStore

SAMPLE_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[[77.0, 20.0], [77.01, 20.0], [77.01, 20.01], [77.0, 20.01], [77.0, 20.0]]],
}


@pytest.fixture
def fake_store() -> FakeEvidenceStore:
    return FakeEvidenceStore()


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        gee_service_account_credentials=None,
        gee_service_account_email=None,
        database_url="sqlite:///:memory:",
        evidence_store_bucket="test-bucket",
        causation_low_confidence_threshold=None,
        csm_high_scrutiny_enabled=False,
        ai_ml_model_path=None,
    )


@pytest.fixture
def client(fake_store, test_settings) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_store] = lambda: fake_store
    app.dependency_overrides[get_settings] = lambda: test_settings
    return TestClient(app)
