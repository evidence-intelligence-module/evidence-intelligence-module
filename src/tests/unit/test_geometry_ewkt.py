"""Regression tests for GeoJSON -> EWKT normalisation (tasks.md T0-13).

The defect these pin down: `pipeline.py` stored `str(...)` of Earth Engine's
`reduceToVectors().getInfo()`, a GeoJSON **FeatureCollection**, into a
`Geometry(srid=4326)` column. PostGIS rejects that with
`invalid GeoJson representation` — a FeatureCollection is a container, not a
geometry.

Two things made it invisible:

1. It fires *only* on success. `gee_client.sar_composite` sets
   `flood_extent_geojson` to a FeatureCollection only when `vv_drop` exceeds
   the flood threshold, so the insert failed exactly when SAR had detected a
   flood — and `run_pipeline_background` then marked the request `FAILED`.
2. Every existing test injects `FakeEvidenceStore`, which stores whatever
   string it is handed and never reaches PostGIS. `test_sar_flood_fallback`
   even asserts `flood_extent_geometry is not None` and passed throughout.

These tests therefore assert on the *value's storable form* rather than on a
successful write, so they hold without a live database."""

from __future__ import annotations

import pytest
from shapely import wkt

from evidence_intelligence.geometry import to_ewkt

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[77.0, 20.0], [77.01, 20.0], [77.01, 20.01], [77.0, 20.01], [77.0, 20.0]]],
}
ADJACENT = {
    "type": "Polygon",
    "coordinates": [[[77.01, 20.0], [77.02, 20.0], [77.02, 20.01], [77.01, 20.01], [77.01, 20.0]]],
}


def _feature(geometry: dict) -> dict:
    return {"type": "Feature", "geometry": geometry, "properties": {"label": 1}}


def _is_storable(value: str) -> bool:
    """EWKT that PostGIS's `ST_GeomFromEWKT` will accept: an `SRID=n;` prefix
    followed by a WKT body the same parser PostGIS uses can read."""
    if not value.startswith("SRID="):
        return False
    prefix, _, body = value.partition(";")
    int(prefix.removeprefix("SRID="))
    wkt.loads(body)
    return True


# -- the case that was actually broken ---------------------------------------


def test_populated_feature_collection_becomes_storable_ewkt():
    """The real flood-detected payload. `str()` of this was never storable."""
    collection = {"type": "FeatureCollection", "features": [_feature(POLYGON)]}
    result = to_ewkt(collection)
    assert _is_storable(result)
    assert result.startswith("SRID=4326;")


def test_raw_str_of_a_feature_collection_is_not_storable():
    """Pins down why the old code failed, so the regression can't quietly
    return: a FeatureCollection's WKT-parse fails outright."""
    collection = {"type": "FeatureCollection", "features": [_feature(POLYGON)]}
    with pytest.raises(Exception):
        wkt.loads(str(collection))


def test_multiple_features_are_dissolved_into_one_geometry():
    """`reduceToVectors` emits one feature per contiguous flooded patch; the
    evidence claim is about their union, and the column holds one geometry."""
    collection = {"type": "FeatureCollection", "features": [_feature(POLYGON), _feature(ADJACENT)]}
    geometry = wkt.loads(to_ewkt(collection).partition(";")[2])
    assert geometry.area == pytest.approx(
        wkt.loads(to_ewkt(POLYGON).partition(";")[2]).area
        + wkt.loads(to_ewkt(ADJACENT).partition(";")[2]).area
    )


# -- absence must stay absent ------------------------------------------------


def test_empty_feature_collection_is_none_not_an_empty_geometry():
    """"SAR ran and found no flood pixels" is an absence. Storing an empty
    geometry would later read as a measured zero-area flood extent."""
    assert to_ewkt({"type": "FeatureCollection", "features": []}) is None


def test_none_passes_through():
    assert to_ewkt(None) is None


# -- the shapes that already worked, now explicit rather than incidental -----


def test_bare_geometry_becomes_storable_ewkt():
    result = to_ewkt(POLYGON)
    assert _is_storable(result)
    assert "POLYGON" in result


def test_single_feature_becomes_storable_ewkt():
    assert _is_storable(to_ewkt(_feature(POLYGON)))


def test_srid_is_overridable_but_defaults_to_4326():
    assert to_ewkt(POLYGON).startswith("SRID=4326;")
    assert to_ewkt(POLYGON, srid=3857).startswith("SRID=3857;")
