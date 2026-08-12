"""Integration test for quickstart.md Scenario 3: no imagery, non-flood
peril -> weather-only preliminary package, later superseded by a complete
package once imagery becomes available (spec.md User Story 3, FR-022)."""

from datetime import date

from evidence_intelligence.pipeline import run_pipeline
from evidence_intelligence.store.schema import PackageTier, PerilType, RequestStatus
from tests.conftest import SAMPLE_GEOMETRY
from tests.fakes import FakeGEEClient, FakeIMDClient, FakeWeatherClient


def test_no_imagery_non_flood_peril_delivers_weather_only_preliminary(
    fake_store, test_settings, tmp_path, monkeypatch
):
    monkeypatch.setenv("EVIDENCE_STORE_LOCAL_ROOT", str(tmp_path))
    from evidence_intelligence.packaging.report_generator import LocalObjectStorage

    event_date = date(2026, 6, 15)
    request = fake_store.create_request(
        geometry=str(SAMPLE_GEOMETRY), event_date=event_date, peril_type=PerilType.DROUGHT
    )

    run_pipeline(
        request.request_id,
        SAMPLE_GEOMETRY,
        event_date,
        PerilType.DROUGHT,
        fake_store,
        test_settings,
        gee_client=FakeGEEClient(scenario="no_imagery", event_date=event_date),
        weather_client=FakeWeatherClient(),
        imd_client=FakeIMDClient(),
        storage=LocalObjectStorage(test_settings.evidence_store_bucket),
    )

    assert fake_store.get_request(request.request_id).status == RequestStatus.INSUFFICIENT_DATA
    package = fake_store.latest_package(request.request_id)
    assert package is not None
    assert package.package_tier == PackageTier.WEATHER_ONLY_PRELIMINARY
    # Still fully admissible even in the degraded path (FR-017-FR-020).
    assert package.pdf_uri and package.json_uri and package.checksum


def test_request_remains_open_for_later_completion(
    fake_store, test_settings, tmp_path, monkeypatch
):
    """Once imagery becomes available, retry_insufficient_data completes
    the request and a second (COMPLETE) package is added — the preliminary
    one is retained, not overwritten (data-model.md)."""
    monkeypatch.setenv("EVIDENCE_STORE_LOCAL_ROOT", str(tmp_path))
    from evidence_intelligence.packaging.report_generator import LocalObjectStorage
    from evidence_intelligence.pipeline import retry_insufficient_data

    event_date = date(2026, 6, 15)
    request = fake_store.create_request(
        geometry=str(SAMPLE_GEOMETRY), event_date=event_date, peril_type=PerilType.DROUGHT
    )
    run_pipeline(
        request.request_id,
        SAMPLE_GEOMETRY,
        event_date,
        PerilType.DROUGHT,
        fake_store,
        test_settings,
        gee_client=FakeGEEClient(scenario="no_imagery", event_date=event_date),
        weather_client=FakeWeatherClient(),
        imd_client=FakeIMDClient(),
        storage=LocalObjectStorage(test_settings.evidence_store_bucket),
    )
    assert len(fake_store.list_packages(request.request_id)) == 1

    completed = retry_insufficient_data(
        request.request_id,
        SAMPLE_GEOMETRY,
        event_date,
        PerilType.DROUGHT,
        fake_store,
        test_settings,
        gee_client=FakeGEEClient(scenario="healthy", event_date=event_date),
        weather_client=FakeWeatherClient(),
        imd_client=FakeIMDClient(),
        storage=LocalObjectStorage(test_settings.evidence_store_bucket),
    )
    assert completed is True
    assert fake_store.get_request(request.request_id).status == RequestStatus.COMPLETE

    packages = fake_store.list_packages(request.request_id)
    assert len(packages) == 2
    tiers = {p.package_tier for p in packages}
    assert PackageTier.WEATHER_ONLY_PRELIMINARY in tiers
    assert PackageTier.COMPLETE in tiers
