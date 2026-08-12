"""Contract test: POST /evidence-requests returns synchronously with
status=IN_PROGRESS before analysis finishes (spec.md FR-003, SC-001)."""

from evidence_intelligence.store.schema import RequestStatus
from tests.conftest import SAMPLE_GEOMETRY


def test_response_returns_even_if_background_pipeline_fails(client, fake_store, monkeypatch):
    """If the response depended on the pipeline finishing, a pipeline
    failure would surface as a 5xx here. It doesn't — proving the response
    is genuinely decoupled from pipeline execution, not just labeled as
    such. The request is marked FAILED rather than left stuck IN_PROGRESS."""

    def _broken_pipeline(*args, **kwargs):
        raise RuntimeError("simulated pipeline failure")

    monkeypatch.setattr("evidence_intelligence.pipeline.run_pipeline", _broken_pipeline)

    response = client.post(
        "/evidence-requests",
        json={"geometry": SAMPLE_GEOMETRY, "event_date": "2026-06-15", "peril_type": "hailstorm"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "IN_PROGRESS"

    request = fake_store.get_request(body["request_id"])
    assert request.status == RequestStatus.FAILED


def test_request_id_is_unique_per_submission(client, monkeypatch):
    monkeypatch.setattr(
        "evidence_intelligence.pipeline.run_pipeline", lambda *a, **k: None
    )
    ids = set()
    for _ in range(3):
        response = client.post(
            "/evidence-requests",
            json={"geometry": SAMPLE_GEOMETRY, "event_date": "2026-06-15", "peril_type": "drought"},
        )
        ids.add(response.json()["request_id"])
    assert len(ids) == 3
