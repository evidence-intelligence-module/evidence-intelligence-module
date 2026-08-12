"""Contract test for GET /evidence-requests/{request_id} (contracts/evidence-request-api.md)."""

from datetime import date, datetime

from evidence_intelligence.store.schema import PackageTier, PerilType, RequestStatus
from tests.conftest import SAMPLE_GEOMETRY


def test_unknown_request_id_returns_404(client):
    response = client.get("/evidence-requests/does-not-exist")
    assert response.status_code == 404


def test_in_progress_request_returns_status_without_package(client, fake_store):
    request = fake_store.create_request(
        geometry=str(SAMPLE_GEOMETRY), event_date=date(2026, 6, 15), peril_type=PerilType.DROUGHT
    )
    response = client.get(f"/evidence-requests/{request.request_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "RECEIVED"
    assert body.get("package") is None


def test_complete_request_returns_full_package_shape(client, fake_store):
    request = fake_store.create_request(
        geometry=str(SAMPLE_GEOMETRY), event_date=date(2026, 6, 15), peril_type=PerilType.HAILSTORM
    )
    fake_store.add_weather_result(
        request_id=request.request_id,
        source_dataset="CHIRPS Daily",
        source_version="fake",
        observed_value=50.0,
        historical_baseline=20.0,
        anomaly_score=1.5,
        causation_confidence_score=94,
    )
    fake_store.add_package(
        request_id=request.request_id,
        package_tier=PackageTier.COMPLETE,
        pdf_uri="file:///tmp/report.pdf",
        json_uri="file:///tmp/package.json",
        map_uris=[],
        methodology_version="v1.0.0",
        checksum="deadbeef",
        generated_at=datetime.utcnow(),
    )
    fake_store.set_status(request.request_id, RequestStatus.COMPLETE)

    response = client.get(f"/evidence-requests/{request.request_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETE"
    assert body["package"]["pdf_uri"] == "file:///tmp/report.pdf"
    assert body["package"]["json_uri"] == "file:///tmp/package.json"
    assert body["package"]["methodology_version"] == "v1.0.0"
    assert body["package"]["causation_confidence_score"] == 94
    assert body["package"]["note"] is None


def test_insufficient_data_request_returns_weather_only_note(client, fake_store):
    request = fake_store.create_request(
        geometry=str(SAMPLE_GEOMETRY), event_date=date(2026, 6, 15), peril_type=PerilType.DROUGHT
    )
    fake_store.add_package(
        request_id=request.request_id,
        package_tier=PackageTier.WEATHER_ONLY_PRELIMINARY,
        pdf_uri="file:///tmp/report.pdf",
        json_uri="file:///tmp/package.json",
        map_uris=[],
        methodology_version="v1.0.0",
        checksum="deadbeef",
        generated_at=datetime.utcnow(),
    )
    fake_store.set_status(request.request_id, RequestStatus.INSUFFICIENT_DATA)

    response = client.get(f"/evidence-requests/{request.request_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "INSUFFICIENT_DATA"
    assert "preliminary" in body["package"]["note"].lower()
    assert body["estimated_completion"] is not None
