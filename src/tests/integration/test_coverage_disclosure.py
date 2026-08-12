"""Coverage must reach the evidence package, not just the pipeline (T0-07).

Constitution Principle I/II require every figure in a package to be traceable
and independently weighable. An NDVI drop measured over 12% of a field is a
different claim from the same drop measured over 95% of it — so the package
has to say which it is, or a reviewer cannot weigh anything derived from it."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from evidence_intelligence.packaging.report_generator import LocalObjectStorage
from evidence_intelligence.pipeline import run_pipeline
from evidence_intelligence.store.schema import PerilType
from tests.conftest import SAMPLE_GEOMETRY
from tests.fakes import FakeGEEClient, FakeIMDClient, FakeWeatherClient

EVENT_DATE = date(2026, 6, 15)


def _package_json(fake_store, test_settings, tmp_path, monkeypatch, **gee_kwargs) -> dict:
    monkeypatch.setenv("EVIDENCE_STORE_LOCAL_ROOT", str(tmp_path))
    request = fake_store.create_request(
        geometry=str(SAMPLE_GEOMETRY), event_date=EVENT_DATE, peril_type=PerilType.HAILSTORM
    )
    run_pipeline(
        request.request_id,
        SAMPLE_GEOMETRY,
        EVENT_DATE,
        PerilType.HAILSTORM,
        fake_store,
        test_settings,
        gee_client=FakeGEEClient(event_date=EVENT_DATE, **gee_kwargs),
        weather_client=FakeWeatherClient(),
        imd_client=FakeIMDClient(),
        storage=LocalObjectStorage(test_settings.evidence_store_bucket),
    )
    package = fake_store.latest_package(request.request_id)
    return json.loads(Path(package.json_uri.removeprefix("file://")).read_text(encoding="utf-8"))


def test_package_states_how_much_of_the_field_was_seen(
    fake_store, test_settings, tmp_path, monkeypatch
):
    record = _package_json(
        fake_store, test_settings, tmp_path, monkeypatch, valid_pixel_fraction=0.95
    )
    coverage = [s for s in record["accuracy_statement"] if "coverage" in s.lower()]
    assert coverage, "package must disclose cloud/shadow-free coverage"
    assert "95% of field" in coverage[0]


def test_poor_coverage_is_visible_in_the_package_not_hidden(
    fake_store, test_settings, tmp_path, monkeypatch
):
    """A barely-observed field still produces a package — evidence is never
    silently suppressed — but the package says so, which is the whole point."""
    record = _package_json(
        fake_store, test_settings, tmp_path, monkeypatch, valid_pixel_fraction=0.12
    )
    coverage = [s for s in record["accuracy_statement"] if "coverage" in s.lower()][0]
    assert "12% of field" in coverage


def test_unmeasured_coverage_is_labelled_as_unmeasured(
    fake_store, test_settings, tmp_path, monkeypatch
):
    record = _package_json(
        fake_store, test_settings, tmp_path, monkeypatch, valid_pixel_fraction=None
    )
    coverage = [s for s in record["accuracy_statement"] if "coverage" in s.lower()][0]
    assert "not measured" in coverage
