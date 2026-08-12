"""Integration test: peril=flood with unusable optical imagery substitutes
SAR flood-extent analysis rather than falling back to weather-only
(spec.md User Story 3, acceptance scenario 2; FR-006)."""

from datetime import date

from evidence_intelligence.pipeline import run_pipeline
from evidence_intelligence.store.schema import PackageTier, PerilType, RequestStatus
from tests.conftest import SAMPLE_GEOMETRY
from tests.fakes import FakeGEEClient, FakeIMDClient, FakeWeatherClient


def test_flood_peril_with_no_optical_substitutes_sar(
    fake_store, test_settings, tmp_path, monkeypatch
):
    monkeypatch.setenv("EVIDENCE_STORE_LOCAL_ROOT", str(tmp_path))
    from evidence_intelligence.packaging.report_generator import LocalObjectStorage

    event_date = date(2026, 7, 20)
    request = fake_store.create_request(
        geometry=str(SAMPLE_GEOMETRY), event_date=event_date, peril_type=PerilType.FLOOD
    )

    gee_client = FakeGEEClient(scenario="flood", event_date=event_date)
    run_pipeline(
        request.request_id,
        SAMPLE_GEOMETRY,
        event_date,
        PerilType.FLOOD,
        fake_store,
        test_settings,
        gee_client=gee_client,
        weather_client=FakeWeatherClient(),
        imd_client=FakeIMDClient(),
        storage=LocalObjectStorage(test_settings.evidence_store_bucket),
    )

    request_state = fake_store.get_request(request.request_id)
    assert request_state.status == RequestStatus.COMPLETE  # not INSUFFICIENT_DATA

    satellite_results = fake_store.list_satellite_results(request.request_id)
    assert satellite_results
    assert satellite_results[0].flood_extent_geometry is not None

    package = fake_store.latest_package(request.request_id)
    assert package.package_tier == PackageTier.COMPLETE
