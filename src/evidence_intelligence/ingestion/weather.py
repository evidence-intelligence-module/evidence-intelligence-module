"""Weather Correlation Engine (HLD §3). CHIRPS/ERA5-Land/GPM IMERG/SMAP via
GEE, corroborated by IMD AWS station data where available
(Evidence-Flow-Spec.md §5 steps 1-3)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta

import ee
import httpx

from evidence_intelligence.dates import shift_years

CHIRPS_DAILY = "UCSB-CHG/CHIRPS/DAILY"
ERA5_LAND_DAILY = "ECMWF/ERA5_LAND/DAILY_AGGR"
GPM_IMERG = "NASA/GPM_L3/IMERG_V07"
SMAP_L3 = "NASA/SMAP/SPL4SMGP/007"

EVENT_WINDOW_DAYS_BEFORE = 7
EVENT_WINDOW_DAYS_AFTER = 3
HISTORICAL_BASELINE_YEARS = 5

# ERA5-Land distributes 2m air temperature in kelvin. Converting at this
# boundary — where the source's unit is known — rather than at the call site
# keeps every downstream consumer working in the celsius its parameter names
# already claim (tasks.md T0-01).
KELVIN_TO_CELSIUS_OFFSET = 273.15


@dataclass
class WeatherObservation:
    source_dataset: str
    source_version: str
    observed_value: float | None
    historical_baseline: float | None
    anomaly_score: float | None


@dataclass
class WeatherIngestionResult:
    precipitation: WeatherObservation
    near_real_time_precipitation: WeatherObservation | None
    reanalysis: WeatherObservation
    soil_moisture: WeatherObservation
    station_corroboration: dict | None


class WeatherClient:
    def __init__(self, auto_init: bool = True):
        if auto_init:
            from evidence_intelligence.ingestion.gee_client import _ensure_initialized

            _ensure_initialized()

    def _window_mean(
        self, collection_id: str, band: str, geometry: dict, start: date, end: date
    ) -> float | None:
        region = ee.Geometry(geometry)
        collection = (
            ee.ImageCollection(collection_id)
            .filterBounds(region)
            .filterDate(str(start), str(end))
            .select(band)
        )
        if collection.size().getInfo() == 0:
            return None
        image = collection.mean()
        stats = image.reduceRegion(reducer=ee.Reducer.mean(), geometry=region, scale=5000)
        values = stats.getInfo()
        if not values:
            return None
        value = next(iter(values.values()))
        return float(value) if value is not None else None

    def precipitation(self, geometry: dict, start: date, end: date) -> float | None:
        return self._window_mean(CHIRPS_DAILY, "precipitation", geometry, start, end)

    def near_real_time_precipitation(
        self, geometry: dict, start: date, end: date
    ) -> float | None:
        return self._window_mean(GPM_IMERG, "precipitationCal", geometry, start, end)

    def reanalysis_temperature(self, geometry: dict, start: date, end: date) -> float | None:
        """Mean 2m air temperature over the window, **in celsius**.

        ERA5-Land serves this band in kelvin; the conversion happens here so
        callers (`models/semi_physical.py`'s `*_temp_c` parameters, the
        `temperature_anomaly` feature) receive the unit they document.
        Returning kelvin put every real reading above `CropParameters.
        temp_max_c`, which zeroed Component 1's biomass on every request while
        still reporting high calibration confidence (tasks.md T0-01)."""
        kelvin = self._window_mean(ERA5_LAND_DAILY, "temperature_2m", geometry, start, end)
        if kelvin is None:
            return None
        return kelvin - KELVIN_TO_CELSIUS_OFFSET

    def soil_moisture(self, geometry: dict, start: date, end: date) -> float | None:
        return self._window_mean(SMAP_L3, "sm_surface", geometry, start, end)


class IMDClient:
    """Official weather-station records, used to corroborate gridded
    sources, never to substitute them (Evidence-Flow-Spec.md §5 step 3)."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or os.environ.get("IMD_AWS_API_BASE_URL")

    def station_record(
        self, geometry: dict, start: date, end: date
    ) -> dict | None:
        if not self.base_url:
            return None
        try:
            response = httpx.get(
                f"{self.base_url}/station-data",
                params={
                    "lat": geometry.get("coordinates", [[None]])[0][0][1]
                    if geometry.get("type") == "Polygon"
                    else geometry.get("coordinates", [None, None])[1],
                    "lon": geometry.get("coordinates", [[None]])[0][0][0]
                    if geometry.get("type") == "Polygon"
                    else geometry.get("coordinates", [None, None])[0],
                    "start": str(start),
                    "end": str(end),
                },
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return None


def _anomaly_score(
    observed: float | None, baseline: float | None, relative: bool = True
) -> float | None:
    """Deviation of `observed` from `baseline`.

    `relative=True` (precipitation, soil moisture) expresses it as a fraction
    of the baseline, which is how a rainfall anomaly is conventionally read.
    `relative=False` (temperature) returns the absolute deviation in the
    source's own unit — a temperature baseline near 0 °C would otherwise make
    the relative form diverge, and a temperature anomaly is conventionally
    stated in degrees rather than as a ratio."""
    if observed is None or baseline is None:
        return None
    if not relative:
        return observed - baseline
    if baseline == 0:
        return None
    return (observed - baseline) / abs(baseline)


def _observe(
    fetch,
    geometry: dict,
    window_start: date,
    window_end: date,
    source_dataset: str,
    source_version: str,
    relative_anomaly: bool = True,
) -> WeatherObservation:
    """Event-window observation plus a same-calendar-window baseline over the
    previous `HISTORICAL_BASELINE_YEARS`, and the anomaly between them.

    Every gridded source gets the same treatment — previously only
    precipitation carried a baseline, so `temperature_anomaly` and
    `soil_moisture_deviation` had nothing to be computed from and were
    hardcoded to 0.0 at the pipeline's feature vector despite the underlying
    data already being fetched (tasks.md T0-03)."""
    observed = fetch(geometry, window_start, window_end)
    baseline_values = [
        fetch(
            geometry,
            shift_years(window_start, -offset),
            shift_years(window_end, -offset),
        )
        for offset in range(1, HISTORICAL_BASELINE_YEARS + 1)
    ]
    baseline_values = [v for v in baseline_values if v is not None]
    baseline = sum(baseline_values) / len(baseline_values) if baseline_values else None

    return WeatherObservation(
        source_dataset=source_dataset,
        source_version=source_version,
        observed_value=observed,
        historical_baseline=baseline,
        anomaly_score=_anomaly_score(observed, baseline, relative=relative_anomaly),
    )


def ingest_weather(
    weather_client: WeatherClient,
    imd_client: IMDClient,
    geometry: dict,
    event_date: date,
    peril_type_is_cloudburst_or_hailstorm: bool,
) -> WeatherIngestionResult:
    """FR-008/FR-009: event-window weather data plus a multi-year historical
    baseline for the same calendar window, corroborated by IMD AWS where
    available."""
    window_start = event_date - timedelta(days=EVENT_WINDOW_DAYS_BEFORE)
    window_end = event_date + timedelta(days=EVENT_WINDOW_DAYS_AFTER)

    precipitation = _observe(
        weather_client.precipitation,
        geometry,
        window_start,
        window_end,
        source_dataset="CHIRPS Daily",
        source_version=CHIRPS_DAILY,
    )

    near_real_time = None
    if peril_type_is_cloudburst_or_hailstorm:
        nrt_value = weather_client.near_real_time_precipitation(
            geometry, window_start, window_end
        )
        near_real_time = WeatherObservation(
            source_dataset="GPM IMERG",
            source_version=GPM_IMERG,
            observed_value=nrt_value,
            historical_baseline=None,
            anomaly_score=None,
        )

    reanalysis = _observe(
        weather_client.reanalysis_temperature,
        geometry,
        window_start,
        window_end,
        source_dataset="ERA5-Land Daily Aggregated",
        source_version=ERA5_LAND_DAILY,
        relative_anomaly=False,  # degrees celsius deviation, not a ratio
    )

    soil_moisture = _observe(
        weather_client.soil_moisture,
        geometry,
        window_start,
        window_end,
        source_dataset="SMAP L4",
        source_version=SMAP_L3,
    )

    station_record = imd_client.station_record(geometry, window_start, window_end)

    return WeatherIngestionResult(
        precipitation=precipitation,
        near_real_time_precipitation=near_real_time,
        reanalysis=reanalysis,
        soil_moisture=soil_moisture,
        station_corroboration=station_record,
    )
