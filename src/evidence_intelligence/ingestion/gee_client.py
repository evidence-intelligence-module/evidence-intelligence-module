"""Shared Google Earth Engine client wrapper (HLD §7). Every ingestion
module goes through this rather than calling `ee` directly, so imagery.py
and weather.py stay testable without a live GEE connection (swap in a fake
implementing the same methods)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta

import ee

from evidence_intelligence.dates import shift_years

SENTINEL2_SR = "COPERNICUS/S2_SR_HARMONIZED"
LANDSAT89_SR = "LANDSAT/LC09/C02/T1_L2"
SENTINEL1_GRD = "COPERNICUS/S1_GRD"
SENTINEL2_CLOUD_FILTER_PCT = 20

# Evidence-Flow-Spec.md §4 step 3: standing water reads below -15dB in VV with
# a >3dB drop from the pre-event baseline.
SENTINEL1_FLOOD_VV_THRESHOLD_DB = -15
SENTINEL1_FLOOD_DROP_THRESHOLD_DB = 3
SENTINEL1_PRE_EVENT_WINDOW_DAYS = 30


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
    """Backscatter change over the event window, per polarization.

    Both drops are `pre − post` in dB, so a positive value means backscatter
    fell — matching the positive-to-damage direction `Modeling-Approach.md` §6's
    DSI indicator table uses. `vh_drop_db` is `None` where the acquisitions
    covering this geometry were single-polarization (see `_s1_median`)."""

    source_dataset: str
    source_version: str
    acquisition_date: date
    vv_drop_db: float | None
    vh_drop_db: float | None
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
            "Earth Engine client (see GUIDE.md / quickstart.md prerequisites)."
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

    def _s1_median(
        self, region: ee.Geometry, window_start: date, window_end: date, polarization: str
    ) -> ee.Image:
        """Median backscatter composite for one polarization over a window.

        Filtering on `transmitterReceiverPolarisation` is what makes the VH
        signal honest: Sentinel-1 IW is usually dual-pol VV+VH over land, but
        not in every acquisition plan or every region. Where VH wasn't
        acquired the collection is empty, the composite carries no bands, and
        `_reduce_mean` returns `None` — so the caller leaves the VH-derived
        signals absent instead of substituting VV, which measures a different
        physical process."""
        return (
            ee.ImageCollection(SENTINEL1_GRD)
            .filterBounds(region)
            .filterDate(str(window_start), str(window_end))
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", polarization))
            .select(polarization)
            .median()
        )

    def sar_composite(
        self, geometry: dict, pre_event_end: date, post_event_start: date, post_event_end: date
    ) -> SarComposite | None:
        """Sentinel-1 backscatter change over the event window, in both
        polarizations — two different measurements from the same acquisitions,
        because they answer different questions:

        - **VV** drives flood-extent detection (Evidence-Flow-Spec.md §4
          step 3). Standing water is a specular reflector, so co-polarized
          backscatter collapses over it.
        - **VH** drives the structural-damage signal (`Modeling-Approach.md` §6's
          DSI indicator table, "SAR VH backscatter deviation"). Cross-polarized
          return comes from volume scattering within the canopy, so it tracks
          crop structure rather than surface conditions.

        A missing VH acquisition yields `vh_drop_db=None` rather than falling
        back to VV. Returns `None` overall only when VV itself is unavailable,
        since flood extent is the signal this method is called for today."""
        region = ee.Geometry(geometry)
        pre_start = pre_event_end - timedelta(days=SENTINEL1_PRE_EVENT_WINDOW_DAYS)

        pre_vv = self._s1_median(region, pre_start, pre_event_end, "VV")
        post_vv = self._s1_median(region, post_event_start, post_event_end, "VV")
        vv_drop = self._reduce_mean(pre_vv.subtract(post_vv), region)
        if vv_drop is None:
            return None

        pre_vh = self._s1_median(region, pre_start, pre_event_end, "VH")
        post_vh = self._s1_median(region, post_event_start, post_event_end, "VH")
        vh_drop = self._reduce_mean(pre_vh.subtract(post_vh), region)

        flood_mask = post_vv.lt(SENTINEL1_FLOOD_VV_THRESHOLD_DB).And(
            pre_vv.subtract(post_vv).gt(SENTINEL1_FLOOD_DROP_THRESHOLD_DB)
        )
        vectors = flood_mask.selfMask().reduceToVectors(geometry=region, scale=10)
        flood_geojson = (
            vectors.getInfo() if vv_drop > SENTINEL1_FLOOD_DROP_THRESHOLD_DB else None
        )
        return SarComposite(
            source_dataset="Sentinel-1 GRD",
            source_version=SENTINEL1_GRD,
            acquisition_date=post_event_end,
            vv_drop_db=vv_drop,
            vh_drop_db=vh_drop,
            flood_extent_geojson=flood_geojson,
        )

    def historical_composite(
        self, geometry: dict, seasonal_window_start: date, seasonal_window_end: date, years: int = 5
    ) -> list[ImageryComposite]:
        """5-year historical archive over the same seasonal window, for
        anomaly-vs-history scoring (Evidence-Flow-Spec.md §3)."""
        composites: list[ImageryComposite] = []
        for offset in range(1, years + 1):
            start = shift_years(seasonal_window_start, -offset)
            end = shift_years(seasonal_window_end, -offset)
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
