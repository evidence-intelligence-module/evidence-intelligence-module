"""Normalisation of GeoJSON values into the EWKT form PostGIS columns accept.

Every `Geometry(srid=4326)` column in `store/schema.py` is written through
GeoAlchemy2, which wraps the bound value in `ST_GeomFromEWKT(...)`. That
function accepts WKT, EWKT, and — leniently — a bare GeoJSON *geometry*. It
does **not** accept a GeoJSON `Feature` or `FeatureCollection`, which are
containers rather than geometries: PostGIS rejects them with
`invalid GeoJson representation`.

That distinction bit exactly once, and expensively (tasks.md T0-13):

- `api/routes.py` stored `str(body.geometry)` — a bare geometry, so
  `ST_GeomFromEWKT` parsed it and the path worked by luck rather than design.
- `pipeline.py` stored `str(imagery.sar.flood_extent_geojson)`, which comes
  from Earth Engine's `reduceToVectors().getInfo()` and is a
  **FeatureCollection**. That insert always failed.

The second path is reached only when `gee_client.sar_composite` actually
detects flooding (`vv_drop` above the flood threshold), and an unhandled
exception there leaves `run_pipeline_background` marking the request `FAILED`
— so the pipeline broke precisely when it had succeeded at finding a flood,
for the peril and cloud-cover case the module exists to evidence. Every test
missed it because the fakes never touch PostGIS.

Routing both call sites through `to_ewkt` makes the stored form explicit
rather than incidental, so neither depends on how forgiving the parser
happens to be."""

from __future__ import annotations

from shapely.geometry import shape
from shapely.ops import unary_union

DEFAULT_SRID = 4326


def to_ewkt(value: dict | None, srid: int = DEFAULT_SRID) -> str | None:
    """A GeoJSON geometry, `Feature`, or `FeatureCollection` as `SRID=n;WKT`.

    Returns `None` for `None`, and for a `FeatureCollection` carrying no
    features — "SAR ran and found no flood pixels" is an absence, and belongs
    in the column as `NULL` rather than as an empty geometry that later reads
    as a measured zero-area extent.

    Multiple features are dissolved into a single geometry with
    `unary_union`, since the column holds one geometry per row and a flood
    extent is naturally multi-part: `reduceToVectors` returns one feature per
    contiguous patch of flooded pixels, and the evidence claim is about their
    union, not about any one patch."""
    if value is None:
        return None

    geometry = _extract_geometry(value)
    if geometry is None or geometry.is_empty:
        return None

    return f"SRID={srid};{geometry.wkt}"


def _extract_geometry(value: dict):
    """The single shapely geometry a GeoJSON value denotes, or `None`."""
    geojson_type = value.get("type")

    if geojson_type == "FeatureCollection":
        geometries = [
            shape(feature["geometry"])
            for feature in value.get("features") or []
            if feature.get("geometry")
        ]
        if not geometries:
            return None
        return unary_union(geometries)

    if geojson_type == "Feature":
        return shape(value["geometry"]) if value.get("geometry") else None

    return shape(value)
