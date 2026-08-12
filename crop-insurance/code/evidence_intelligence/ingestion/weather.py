"""Weather Correlation Engine (HLD §3). CHIRPS/ERA5-Land/GPM IMERG/SMAP via
GEE, corroborated by IMD AWS station data where available
(Evidence-Flow-Spec.md §5 steps 1-3)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta

import ee
import httpx

CHIRPS_DAILY = "UCSB-CHG/CHIRPS/DAILY"
ERA5_LAND_DAILY = "ECMWF/ERA5_LAND/DAILY_AGGR"
GPM_IMERG = "NASA/GPM_L3/IMERG_V07"
SMAP_L3 = "NASA/SMAP/SPL4SMGP/007"

EVENT_WINDOW_DAYS_BEFORE = 7
EVENT_WINDOW_DAYS_AFTER = 3
HISTORICAL_BASELINE_YEARS = 5


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
        return self._window_mean(
            ERA5_LAND_DAILY, "temperature_2m", geometry, start, end
        )

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


def _anomaly_score(observed: float | None, baseline: float | None) -> float | None:
    if observed is None or baseline is None or baseline == 0:
        return None
    return (observed - baseline) / abs(baseline)


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

    precip_observed = weather_client.precipitation(geometry, window_start, window_end)
    precip_baseline_values = [
        weather_client.precipitation(
            geometry,
            window_start.replace(year=window_start.year - offset),
            window_end.replace(year=window_end.year - offset),
        )
        for offset in range(1, HISTORICAL_BASELINE_YEARS + 1)
    ]
    precip_baseline_values = [v for v in precip_baseline_values if v is not None]
    precip_baseline = (
        sum(precip_baseline_values) / len(precip_baseline_values)
        if precip_baseline_values
        else None
    )

    precipitation = WeatherObservation(
        source_dataset="CHIRPS Daily",
        source_version=CHIRPS_DAILY,
        observed_value=precip_observed,
        historical_baseline=precip_baseline,
        anomaly_score=_anomaly_score(precip_observed, precip_baseline),
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

    temp_observed = weather_client.reanalysis_temperature(geometry, window_start, window_end)
    reanalysis = WeatherObservation(
        source_dataset="ERA5-Land Daily Aggregated",
        source_version=ERA5_LAND_DAILY,
        observed_value=temp_observed,
        historical_baseline=None,
        anomaly_score=None,
    )

    soil_moisture_value = weather_client.soil_moisture(geometry, window_start, window_end)
    soil_moisture = WeatherObservation(
        source_dataset="SMAP L4",
        source_version=SMAP_L3,
        observed_value=soil_moisture_value,
        historical_baseline=None,
        anomaly_score=None,
    )

    station_record = imd_client.station_record(geometry, window_start, window_end)

    return WeatherIngestionResult(
        precipitation=precipitation,
        near_real_time_precipitation=near_real_time,
        reanalysis=reanalysis,
        soil_moisture=soil_moisture,
        station_corroboration=station_record,
    )
