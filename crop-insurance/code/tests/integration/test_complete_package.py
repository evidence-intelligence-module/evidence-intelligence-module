"""Integration test for quickstart.md Scenario 1: submit -> poll -> complete
package, including the reproducibility re-run (spec.md FR-021, SC-005)."""

from datetime import date

from evidence_intelligence.pipeline import run_pipeline
from evidence_intelligence.store.schema import ModelComponent, PackageTier, PerilType, RequestStatus
from tests.conftest import SAMPLE_GEOMETRY
from tests.fakes import FakeGEEClient, FakeIMDClient, FakeWeatherClient


def _run(fake_store, test_settings, tmp_path, monkeypatch, event_date=date(2026, 6, 15)):
    monkeypatch.setenv("EVIDENCE_STORE_LOCAL_ROOT", str(tmp_path))
    from evidence_intelligence.packaging.report_generator import LocalObjectStorage

    request = fake_store.create_request(
        geometry=str(SAMPLE_GEOMETRY), event_date=event_date, peril_type=PerilType.HAILSTORM
    )
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
    return request.request_id


def test_complete_package_has_all_mandatory_fields(
    fake_store, test_settings, tmp_path, monkeypatch
):
    request_id = _run(fake_store, test_settings, tmp_path, monkeypatch)

    request = fake_store.get_request(request_id)
    assert request.status == RequestStatus.COMPLETE

    package = fake_store.latest_package(request_id)
    assert package is not None
    assert package.package_tier == PackageTier.COMPLETE
    assert package.pdf_uri and package.json_uri
    assert package.methodology_version
    assert package.checksum
    assert package.retention_expiry_date.year == package.generated_at.year + 10

    satellite_results = fake_store.list_satellite_results(request_id)
    assert satellite_results
    for result in satellite_results:
        assert result.source_dataset
        assert result.source_version
        assert result.acquisition_date

    component_results = fake_store.list_component_results(request_id)
    components = {r.component for r in component_results}
    assert ModelComponent.SEMI_PHYSICAL in components
    assert ModelComponent.AI_ML in components
    assert ModelComponent.ENSEMBLE in components
    assert ModelComponent.DSI in components

    weather_results = fake_store.list_weather_results(request_id)
    assert weather_results
    assert 0 <= weather_results[-1].causation_confidence_score <= 100


def test_every_component_result_is_independently_recorded(
    fake_store, test_settings, tmp_path, monkeypatch
):
    """FR-012: no component's result overwrites another's."""
    request_id = _run(fake_store, test_settings, tmp_path, monkeypatch)
    component_results = fake_store.list_component_results(request_id)
    assert len({r.result_id for r in component_results}) == len(component_results)
    versions = {r.component: r.methodology_version for r in component_results}
    assert len(versions) == len(component_results)


def test_rerunning_identical_request_is_reproducible(
    fake_store, test_settings, tmp_path, monkeypatch
):
    """FR-021/SC-005: same request + same methodology version -> same result."""
    request_id_1 = _run(fake_store, test_settings, tmp_path, monkeypatch)
    request_id_2 = _run(fake_store, test_settings, tmp_path, monkeypatch)

    ensemble_1 = fake_store.get_component_result(request_id_1, ModelComponent.ENSEMBLE)
    ensemble_2 = fake_store.get_component_result(request_id_2, ModelComponent.ENSEMBLE)
    assert ensemble_1.point_estimate == ensemble_2.point_estimate
    assert ensemble_1.methodology_version == ensemble_2.methodology_version

    dsi_1 = fake_store.get_component_result(request_id_1, ModelComponent.DSI)
    dsi_2 = fake_store.get_component_result(request_id_2, ModelComponent.DSI)
    assert dsi_1.point_estimate == dsi_2.point_estimate


def test_package_labels_estimates_as_supporting_evidence(
    fake_store, test_settings, tmp_path, monkeypatch
):
    """FR-026/SC-008: ensemble yield-loss estimate and DSI must be labeled
    as supporting evidence, never authoritative."""
    import json
    from pathlib import Path

    request_id = _run(fake_store, test_settings, tmp_path, monkeypatch)
    package = fake_store.latest_package(request_id)
    content = json.loads(Path(package.json_uri.replace("file://", "")).read_text())
    assert content["yield_loss_estimate"]["label"] == "supporting_evidence_not_authoritative"
    assert content["damage_severity_index"]["label"] == "supporting_evidence_not_authoritative"
    assert "not an authoritative" in content["disclaimer"].lower()
