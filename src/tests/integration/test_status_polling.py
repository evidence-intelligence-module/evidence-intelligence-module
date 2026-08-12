"""Integration test for quickstart.md Scenario 2: poll before and after
pipeline completion (spec.md User Story 2)."""

from datetime import date

from evidence_intelligence.pipeline import run_pipeline
from evidence_intelligence.store.schema import PerilType, RequestStatus
from tests.conftest import SAMPLE_GEOMETRY
from tests.fakes import FakeGEEClient, FakeIMDClient, FakeWeatherClient


def test_poll_before_and_after_completion(client, fake_store, test_settings, tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_STORE_LOCAL_ROOT", str(tmp_path))
    from evidence_intelligence.packaging.report_generator import LocalObjectStorage

    event_date = date(2026, 6, 15)
    request = fake_store.create_request(
        geometry=str(SAMPLE_GEOMETRY), event_date=event_date, peril_type=PerilType.HAILSTORM
    )

    before_response = client.get(f"/evidence-requests/{request.request_id}")
    assert before_response.status_code == 200
    before_body = before_response.json()
    assert before_body["status"] == "RECEIVED"
    assert before_body.get("package") is None

    run_pipeline(
        request.request_id,
        SAMPLE_GEOMETRY,
        event_date,
        PerilType.HAILSTORM,
        fake_store,
        test_settings,
        gee_client=FakeGEEClient(scenario="healthy", event_date=event_date),
        weather_client=FakeWeatherClient(),
        imd_client=FakeIMDClient(),
        storage=LocalObjectStorage(test_settings.evidence_store_bucket),
    )

    after_response = client.get(f"/evidence-requests/{request.request_id}")
    assert after_response.status_code == 200
    after_body = after_response.json()
    assert after_body["status"] == "COMPLETE"
    assert after_body["package"] is not None
    assert fake_store.get_request(request.request_id).status == RequestStatus.COMPLETE
