"""Contract test for POST /evidence-requests (contracts/evidence-request-api.md)."""

from tests.conftest import SAMPLE_GEOMETRY


def test_valid_request_returns_202_with_request_id_and_in_progress(client):
    response = client.post(
        "/evidence-requests",
        json={
            "geometry": SAMPLE_GEOMETRY,
            "event_date": "2026-06-15",
            "peril_type": "hailstorm",
            "external_reference_id": "caller-ref-123",
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["request_id"]
    assert body["status"] == "IN_PROGRESS"
    assert "estimated_completion" in body


def test_external_reference_id_is_optional(client):
    response = client.post(
        "/evidence-requests",
        json={"geometry": SAMPLE_GEOMETRY, "event_date": "2026-06-15", "peril_type": "drought"},
    )
    assert response.status_code == 202


def test_missing_geometry_returns_422(client):
    response = client.post(
        "/evidence-requests", json={"event_date": "2026-06-15", "peril_type": "drought"}
    )
    assert response.status_code == 422


def test_invalid_geometry_returns_422(client):
    response = client.post(
        "/evidence-requests",
        json={
            "geometry": {"type": "Polygon", "coordinates": "not-a-coordinate-list"},
            "event_date": "2026-06-15",
            "peril_type": "drought",
        },
    )
    assert response.status_code == 422


def test_invalid_peril_type_returns_422(client):
    response = client.post(
        "/evidence-requests",
        json={
            "geometry": SAMPLE_GEOMETRY,
            "event_date": "2026-06-15",
            "peril_type": "not-a-real-peril",
        },
    )
    assert response.status_code == 422


def test_response_never_includes_caller_internal_schema_fields(client):
    """FR-002: no caller-internal claim ID, farmer ID, or policy schema is
    required or accepted — only the generic contract fields."""
    response = client.post(
        "/evidence-requests",
        json={
            "geometry": SAMPLE_GEOMETRY,
            "event_date": "2026-06-15",
            "peril_type": "flood",
            "external_reference_id": "opaque-key",
            "claim_id": "should-be-ignored",
            "farmer_id": "should-be-ignored",
        },
    )
    assert response.status_code == 202
    assert "claim_id" not in response.json()
    assert "farmer_id" not in response.json()
