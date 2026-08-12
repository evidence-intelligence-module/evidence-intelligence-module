"""Shared Google Earth Engine client wrapper (HLD §7). Every ingestion
module goes through this rather than calling `ee` directly, so imagery.py
and weather.py stay testable without a live GEE connection (swap in a fake
implementing the same methods)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta

import ee

SENTINEL2_SR = "COPERNICUS/S2_SR_HARMONIZED"
LANDSAT89_SR = "LANDSAT/LC09/C02/T1_L2"
SENTINEL1_GRD = "COPERNICUS/S1_GRD"
SENTINEL2_CLOUD_FILTER_PCT = 20


@dataclass
class ImageryComposite:
    source_dataset: str
    source_version: str
    acquisition_date: date
    index_value: float | None
    index_type: str = "NDVI"
    usable: bool = True


@dataclass
class SarComposite:
    source_dataset: str
    source_version: str
    acquisition_date: date
    vv_drop_db: float | None
    flood_extent_geojson: dict | None


_initialized = False


def _ensure_initialized() -> None:
    global _initialized
    if _initialized:
        return
    credentials_path = os.environ.get("GEE_SERVICE_ACCOUNT_CREDENTIALS")
    if not credentials_path:
        raise RuntimeError(
            "GEE_SERVICE_ACCOUNT_CREDENTIALS is not set — required to initialize the "
            "Earth Engine client (see SETUP.md / quickstart.md prerequisites)."
        )
    service_account = os.environ.get("GEE_SERVICE_ACCOUNT_EMAIL", "")
    credentials = ee.ServiceAccountCredentials(service_account, credentials_path)
    ee.Initialize(credentials)
    _initialized = True


class GEEClient:
    """Thin wrapper over the `ee` Python API. Methods return plain
    dataclasses, not `ee` objects, so callers never need to reason about
    server-side vs. client-side evaluation."""

    def __init__(self, auto_init: bool = True):
        if auto_init:
            _ensure_initialized()

    def optical_composite(
        self, geometry: dict, window_start: date, window_end: date
    ) -> ImageryComposite | None:
        """NDVI composite from Sentinel-2 (primary) falling back to Landsat
        8/9 if no cloud-free Sentinel-2 image exists in the window
        (Evidence-Flow-Spec.md §3)."""
        region = ee.Geometry(geometry)
        collection = (
            ee.ImageCollection(SENTINEL2_SR)
            .filterBounds(region)
            .filterDate(str(window_start), str(window_end))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", SENTINEL2_CLOUD_FILTER_PCT))
        )
        if collection.size().getInfo() > 0:
            image = collection.median()
            ndvi = image.normalizedDifference(["B8", "B4"])
            value = self._reduce_mean(ndvi, region)
            return ImageryComposite(
                source_dataset="Sentinel-2 SR Harmonized",
                source_version=SENTINEL2_SR,
                acquisition_date=window_end,
                index_value=value,
            )

        landsat = (
            ee.ImageCollection(LANDSAT89_SR).filterBounds(region).filterDate(
                str(window_start), str(window_end)
            )
        )
        if landsat.size().getInfo() > 0:
            image = landsat.median()
            ndvi = image.normalizedDifference(["SR_B5", "SR_B4"])
            value = self._reduce_mean(ndvi, region)
            return ImageryComposite(
                source_dataset="Landsat 8/9 Collection 2 Level-2",
                source_version=LANDSAT89_SR,
                acquisition_date=window_end,
                index_value=value,
            )

        return None

    def sar_composite(
        self, geometry: dict, pre_event_end: date, post_event_start: date, post_event_end: date
    ) -> SarComposite | None:
        """Sentinel-1 VV backscatter change detection for flood extent
        (Evidence-Flow-Spec.md §4 step 3): threshold <-15dB with a >3dB drop
        from the pre-event baseline."""
        region = ee.Geometry(geometry)
        pre = (
            ee.ImageCollection(SENTINEL1_GRD)
            .filterBounds(region)
            .filterDate(str(pre_event_end - timedelta(days=30)), str(pre_event_end))
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .select("VV")
            .median()
        )
        post = (
            ee.ImageCollection(SENTINEL1_GRD)
            .filterBounds(region)
            .filterDate(str(post_event_start), str(post_event_end))
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .select("VV")
            .median()
        )
        drop = self._reduce_mean(pre.subtract(post), region)
        if drop is None:
            return None

        flood_mask = post.lt(-15).And(pre.subtract(post).gt(3))
        vectors = flood_mask.selfMask().reduceToVectors(geometry=region, scale=10)
        flood_geojson = vectors.getInfo() if drop > 3 else None
        return SarComposite(
            source_dataset="Sentinel-1 GRD",
            source_version=SENTINEL1_GRD,
            acquisition_date=post_event_end,
            vv_drop_db=drop,
            flood_extent_geojson=flood_geojson,
        )

    def historical_composite(
        self, geometry: dict, seasonal_window_start: date, seasonal_window_end: date, years: int = 5
    ) -> list[ImageryComposite]:
        """5-year historical archive over the same seasonal window, for
        anomaly-vs-history scoring (Evidence-Flow-Spec.md §3)."""
        composites: list[ImageryComposite] = []
        for offset in range(1, years + 1):
            start = seasonal_window_start.replace(year=seasonal_window_start.year - offset)
            end = seasonal_window_end.replace(year=seasonal_window_end.year - offset)
            composite = self.optical_composite(geometry, start, end)
            if composite is not None:
                composites.append(composite)
        return composites

    @staticmethod
    def _reduce_mean(image: ee.Image, region: ee.Geometry) -> float | None:
        stats = image.reduceRegion(reducer=ee.Reducer.mean(), geometry=region, scale=10)
        values = stats.getInfo()
        if not values:
            return None
        value = next(iter(values.values()))
        return float(value) if value is not None else None
