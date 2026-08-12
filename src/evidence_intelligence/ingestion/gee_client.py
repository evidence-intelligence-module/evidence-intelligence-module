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

# Scene Classification Layer values that make a Sentinel-2 pixel unusable for
# vegetation analysis: 0 no-data, 1 saturated/defective, 2 cast shadow,
# 3 cloud shadow, 8 cloud medium probability, 9 cloud high probability,
# 10 thin cirrus, 11 snow/ice. Retained: 4 vegetation, 5 not-vegetated,
# 6 water (a flooded field is a real observation, not an artefact),
# 7 unclassified.
SENTINEL2_INVALID_SCL_CLASSES = [0, 1, 2, 3, 8, 9, 10, 11]

# Landsat C2 L2 QA_PIXEL bits: 0 fill, 1 dilated cloud, 2 cirrus, 3 cloud,
# 4 cloud shadow, 5 snow.
LANDSAT_QA_INVALID_BITS = [0, 1, 2, 3, 4, 5]

# A *performance* prefilter only, not a correctness gate — it exists to avoid
# compositing scenes that cannot contribute any clear pixel, and is deliberately
# loose. Correctness is decided per pixel below (tasks.md T0-07). An operational
# efficiency knob rather than an evidentiary figure, so it is not subject to the
# no-invented-figures rule that governs domain thresholds (CLAUDE.md), the same
# treatment `api/routes.py` gives its completion-time estimates.
SENTINEL2_SCENE_PREFILTER_PCT = 95

# evidence-flow-spec.md §4 step 3: standing water reads below -15dB in VV with
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
    valid_pixel_fraction: float | None = None
    """Fraction of the submitted geometry seen cloud- and shadow-free at least
    once in the window, after per-pixel masking (tasks.md T0-07).

    This is the figure that distinguishes "the field is damaged" from "we could
    not see the field". Scene-level cloud percentage cannot: a scene 19% cloudy
    overall can be entirely clouded over one 0.16 ha field, while a scene 60%
    cloudy can be perfectly clear over it. Cloud over vegetation depresses NDVI,
    so an unmasked composite reports that indistinguishably from crop loss."""


@dataclass
class SarComposite:
    """Backscatter change over the event window, per polarization.

    Both drops are `pre − post` in dB, so a positive value means backscatter
    fell — matching the positive-to-damage direction `modeling-approach.md` §6's
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

    @staticmethod
    def _sentinel2_valid_mask(image: ee.Image) -> ee.Image:
        """Per-pixel validity from the Scene Classification Layer."""
        return image.select("SCL").remap(
            SENTINEL2_INVALID_SCL_CLASSES,
            [0] * len(SENTINEL2_INVALID_SCL_CLASSES),
            1,
        )

    @staticmethod
    def _landsat_valid_mask(image: ee.Image) -> ee.Image:
        """Per-pixel validity from the Collection 2 QA_PIXEL bitmask."""
        qa = image.select("QA_PIXEL")
        mask = ee.Image.constant(1)
        for bit in LANDSAT_QA_INVALID_BITS:
            mask = mask.And(qa.bitwiseAnd(1 << bit).eq(0))
        return mask

    def _valid_pixel_fraction(
        self, masked: ee.ImageCollection, band: str, region: ee.Geometry, scale: int
    ) -> float | None:
        """Fraction of `region` seen unmasked at least once in the window.

        `count()` is per pixel across the collection, so a field clouded on one
        pass but clear on another counts as seen. `unmask(0)` is load-bearing:
        GEE reducers skip masked pixels entirely, so without it the mean would
        be taken over only the surviving pixels and would always return 1.0 —
        reporting perfect coverage precisely when coverage was worst."""
        seen = masked.select(band).count().gt(0).unmask(0)
        return self._reduce_mean(seen, region, scale=scale)

    def optical_composite(
        self, geometry: dict, window_start: date, window_end: date
    ) -> ImageryComposite | None:
        """NDVI composite from Sentinel-2 (primary) falling back to Landsat
        8/9 (evidence-flow-spec.md §3), cloud- and shadow-masked per pixel.

        Masking is applied before compositing, so cloudy pixels never enter the
        median. Previously any scene passing a 20% *scene-level* cloud filter
        contributed all of its pixels — including those directly over the field
        — and cloud over vegetation depresses NDVI, so the composite reported
        obscured ground indistinguishably from crop loss (tasks.md T0-07).
        Every composite now carries `valid_pixel_fraction` so a caller can tell
        a real index value from one computed over almost nothing."""
        region = ee.Geometry(geometry)
        collection = (
            ee.ImageCollection(SENTINEL2_SR)
            .filterBounds(region)
            .filterDate(str(window_start), str(window_end))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", SENTINEL2_SCENE_PREFILTER_PCT))
        )
        if collection.size().getInfo() > 0:
            masked = collection.map(
                lambda image: image.updateMask(self._sentinel2_valid_mask(image))
            )
            ndvi = masked.median().normalizedDifference(["B8", "B4"])
            return ImageryComposite(
                source_dataset="Sentinel-2 SR Harmonized",
                source_version=SENTINEL2_SR,
                acquisition_date=window_end,
                index_value=self._reduce_mean(ndvi, region),
                valid_pixel_fraction=self._valid_pixel_fraction(masked, "B8", region, scale=10),
            )

        landsat = (
            ee.ImageCollection(LANDSAT89_SR).filterBounds(region).filterDate(
                str(window_start), str(window_end)
            )
        )
        if landsat.size().getInfo() > 0:
            masked = landsat.map(lambda image: image.updateMask(self._landsat_valid_mask(image)))
            ndvi = masked.median().normalizedDifference(["SR_B5", "SR_B4"])
            return ImageryComposite(
                source_dataset="Landsat 8/9 Collection 2 Level-2",
                source_version=LANDSAT89_SR,
                acquisition_date=window_end,
                index_value=self._reduce_mean(ndvi, region),
                valid_pixel_fraction=self._valid_pixel_fraction(masked, "SR_B5", region, scale=30),
            )

        return None

    def _s1_median(
        self,
        region: ee.Geometry,
        window_start: date,
        window_end: date,
        polarization: str,
        orbit_pass: str | None = None,
        relative_orbit: int | None = None,
    ) -> ee.Image:
        """Median backscatter composite for one polarization over a window,
        optionally pinned to a single viewing geometry.

        Filtering on `transmitterReceiverPolarisation` is what makes the VH
        signal honest: Sentinel-1 IW is usually dual-pol VV+VH over land, but
        not in every acquisition plan or every region. Where VH wasn't
        acquired the collection is empty, the composite carries no bands, and
        `_reduce_mean` returns `None` — so the caller leaves the VH-derived
        signals absent instead of substituting VV, which measures a different
        physical process.

        `orbit_pass`/`relative_orbit` pin pre- and post-event composites to
        matching acquisition geometry (tasks.md T0-11)."""
        collection = (
            ee.ImageCollection(SENTINEL1_GRD)
            .filterBounds(region)
            .filterDate(str(window_start), str(window_end))
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", polarization))
        )
        if orbit_pass is not None:
            collection = collection.filter(ee.Filter.eq("orbitProperties_pass", orbit_pass))
        if relative_orbit is not None:
            collection = collection.filter(
                ee.Filter.eq("relativeOrbitNumber_start", relative_orbit)
            )
        return collection.select(polarization).median()

    @staticmethod
    def _dominant_orbit(collection: ee.ImageCollection) -> tuple[str, int] | None:
        """The pass direction and relative orbit of the most recent acquisition
        in `collection`, or `None` when it is empty (tasks.md T0-11).

        Used to pin the pre- and post-event composites to one viewing geometry.
        Sentinel-1 backscatter varies systematically with incidence angle and
        look direction, so differencing an ascending pre-event composite
        against a descending post-event one mixes a real ground change with a
        geometry change — a well-known false-positive source in SAR change
        detection, and one that produces exactly the >3 dB drop this module
        reads as flooding."""
        recent = collection.sort("system:time_start", False).first()
        info = ee.Algorithms.If(collection.size().gt(0), recent, None).getInfo()
        if not info:
            return None
        properties = info.get("properties", {})
        orbit_pass = properties.get("orbitProperties_pass")
        relative_orbit = properties.get("relativeOrbitNumber_start")
        if orbit_pass is None or relative_orbit is None:
            return None
        return orbit_pass, relative_orbit

    def sar_composite(
        self, geometry: dict, pre_event_end: date, post_event_start: date, post_event_end: date
    ) -> SarComposite | None:
        """Sentinel-1 backscatter change over the event window, in both
        polarizations — two different measurements from the same acquisitions,
        because they answer different questions:

        - **VV** drives flood-extent detection (evidence-flow-spec.md §4
          step 3). Standing water is a specular reflector, so co-polarized
          backscatter collapses over it.
        - **VH** drives the structural-damage signal (`modeling-approach.md` §6's
          DSI indicator table, "SAR VH backscatter deviation"). Cross-polarized
          return comes from volume scattering within the canopy, so it tracks
          crop structure rather than surface conditions.

        A missing VH acquisition yields `vh_drop_db=None` rather than falling
        back to VV. Returns `None` overall only when VV itself is unavailable,
        since flood extent is the signal this method is called for today.

        Both windows are pinned to the post-event acquisition's viewing
        geometry (tasks.md T0-11) so the difference measures ground change
        rather than look-angle change."""
        region = ee.Geometry(geometry)
        pre_start = pre_event_end - timedelta(days=SENTINEL1_PRE_EVENT_WINDOW_DAYS)

        # Pin to the post-event pass's geometry: it is the acquisition that
        # must exist for this analysis to mean anything, so it dictates which
        # pre-event pass is comparable to it rather than the reverse.
        post_collection = (
            ee.ImageCollection(SENTINEL1_GRD)
            .filterBounds(region)
            .filterDate(str(post_event_start), str(post_event_end))
            .filter(ee.Filter.eq("instrumentMode", "IW"))
        )
        orbit = self._dominant_orbit(post_collection)
        orbit_pass, relative_orbit = orbit if orbit else (None, None)

        def median(start: date, end: date, polarization: str) -> ee.Image:
            return self._s1_median(
                region, start, end, polarization, orbit_pass, relative_orbit
            )

        pre_vv = median(pre_start, pre_event_end, "VV")
        post_vv = median(post_event_start, post_event_end, "VV")
        vv_drop = self._reduce_mean(pre_vv.subtract(post_vv), region)
        if vv_drop is None:
            return None

        pre_vh = median(pre_start, pre_event_end, "VH")
        post_vh = median(post_event_start, post_event_end, "VH")
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
        anomaly-vs-history scoring (evidence-flow-spec.md §3)."""
        composites: list[ImageryComposite] = []
        for offset in range(1, years + 1):
            start = shift_years(seasonal_window_start, -offset)
            end = shift_years(seasonal_window_end, -offset)
            composite = self.optical_composite(geometry, start, end)
            if composite is not None:
                composites.append(composite)
        return composites

    @staticmethod
    def _reduce_mean(image: ee.Image, region: ee.Geometry, scale: int = 10) -> float | None:
        stats = image.reduceRegion(reducer=ee.Reducer.mean(), geometry=region, scale=scale)
        values = stats.getInfo()
        if not values:
            return None
        value = next(iter(values.values()))
        return float(value) if value is not None else None
