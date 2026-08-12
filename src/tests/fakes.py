"""In-memory test doubles for EvidenceStore/GEEClient/WeatherClient/IMDClient.
Real infrastructure (Postgres+PostGIS, GEE credentials) isn't available in
CI/dev sandboxes per quickstart.md's Prerequisites — these let contract and
integration tests exercise the actual routing/pipeline/model logic without
it. Production code paths (evidence_store.py, gee_client.py, weather.py)
are untouched; only test wiring uses these."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from evidence_intelligence.ingestion.gee_client import ImageryComposite, SarComposite
from evidence_intelligence.store.evidence_store import retention_expiry_date
from evidence_intelligence.store.schema import (
    DamageAssessmentComponentResult,
    EvidencePackage,
    EvidenceRequest,
    PackageTier,
    PerilType,
    RequestStatus,
    SatelliteAnalysisResult,
    WeatherCorrelationResult,
)

_counter = {"n": 0}


def _next_id(prefix: str) -> str:
    _counter["n"] += 1
    return f"{prefix}-TEST-{_counter['n']:06d}"


class FakeEvidenceStore:
    """Same public method signatures as EvidenceStore, backed by dicts."""

    def __init__(self):
        self.requests: dict[str, EvidenceRequest] = {}
        self.satellite_results: dict[str, list[SatelliteAnalysisResult]] = {}
        self.component_results: dict[str, list[DamageAssessmentComponentResult]] = {}
        self.weather_results: dict[str, list[WeatherCorrelationResult]] = {}
        self.packages: dict[str, list[EvidencePackage]] = {}

    def create_request(
        self,
        geometry: str,
        event_date: date,
        peril_type: PerilType,
        external_reference_id: str | None = None,
    ) -> EvidenceRequest:
        request = EvidenceRequest(
            request_id=_next_id("EIM"),
            geometry=geometry,
            event_date=event_date,
            peril_type=peril_type,
            external_reference_id=external_reference_id,
            status=RequestStatus.RECEIVED,
            requested_at=datetime.utcnow(),
        )
        self.requests[request.request_id] = request
        self.satellite_results[request.request_id] = []
        self.component_results[request.request_id] = []
        self.weather_results[request.request_id] = []
        self.packages[request.request_id] = []
        return request

    def get_request(self, request_id: str) -> EvidenceRequest | None:
        return self.requests.get(request_id)

    def set_status(self, request_id: str, status: RequestStatus) -> None:
        request = self.requests[request_id]
        request.status = status
        if status == RequestStatus.COMPLETE:
            request.completed_at = datetime.utcnow()

    def add_satellite_result(self, request_id: str, **kwargs) -> SatelliteAnalysisResult:
        result = SatelliteAnalysisResult(result_id=_next_id("SAT"), request_id=request_id, **kwargs)
        self.satellite_results[request_id].append(result)
        return result

    def list_satellite_results(self, request_id: str) -> list[SatelliteAnalysisResult]:
        return self.satellite_results.get(request_id, [])

    def add_component_result(
        self, request_id: str, **kwargs
    ) -> DamageAssessmentComponentResult:
        result = DamageAssessmentComponentResult(
            result_id=_next_id("MDL"), request_id=request_id, **kwargs
        )
        self.component_results[request_id].append(result)
        return result

    def list_component_results(self, request_id: str) -> list[DamageAssessmentComponentResult]:
        return self.component_results.get(request_id, [])

    def get_component_result(self, request_id: str, component) -> Any:
        matches = [
            r for r in self.component_results.get(request_id, []) if r.component == component
        ]
        return matches[-1] if matches else None

    def add_weather_result(self, request_id: str, **kwargs) -> WeatherCorrelationResult:
        result = WeatherCorrelationResult(result_id=_next_id("WX"), request_id=request_id, **kwargs)
        self.weather_results[request_id].append(result)
        return result

    def list_weather_results(self, request_id: str) -> list[WeatherCorrelationResult]:
        return self.weather_results.get(request_id, [])

    def add_package(
        self,
        request_id: str,
        package_tier: PackageTier,
        pdf_uri: str,
        json_uri: str,
        map_uris: list[str],
        methodology_version: str,
        checksum: str,
        generated_at: datetime | None = None,
    ) -> EvidencePackage:
        generated_at = generated_at or datetime.utcnow()
        package = EvidencePackage(
            package_id=_next_id("PKG"),
            request_id=request_id,
            package_tier=package_tier,
            pdf_uri=pdf_uri,
            json_uri=json_uri,
            map_uris=map_uris,
            methodology_version=methodology_version,
            checksum=checksum,
            generated_at=generated_at,
            retention_expiry_date=retention_expiry_date(generated_at.date()),
        )
        self.packages[request_id].append(package)
        return package

    def latest_package(self, request_id: str) -> EvidencePackage | None:
        packages = self.packages.get(request_id, [])
        return max(packages, key=lambda p: p.generated_at) if packages else None

    def list_packages(self, request_id: str) -> list[EvidencePackage]:
        return self.packages.get(request_id, [])


class FakeGEEClient:
    """Deterministic imagery fixture, keyed by scenario name. Distinguishes
    the pre-event vs. post-event `optical_composite` call by comparing the
    window's `end` date against `event_date` (the pre-event window always
    ends the day before; the post-event window always starts on or after it)."""

    def __init__(self, scenario: str = "healthy", event_date: date | None = None):
        self.scenario = scenario
        self.event_date = event_date or date(2026, 6, 15)
        self.pre_event_ndvi = 0.75
        self.post_event_ndvi = 0.30

    FLOOD_SCENARIOS = ("flood", "flood_single_pol")

    def optical_composite(self, geometry, start, end):
        if self.scenario in ("no_imagery", *self.FLOOD_SCENARIOS):
            # The flood scenarios simulate the monsoon cloud-cover case:
            # post-event optical is blocked, forcing the SAR substitution path.
            if self.scenario in self.FLOOD_SCENARIOS and end < self.event_date:
                pass  # pre-event window still has usable optical
            else:
                return None
        index_value = self.pre_event_ndvi if end < self.event_date else self.post_event_ndvi
        return ImageryComposite(
            source_dataset="Sentinel-2 SR Harmonized (fake)",
            source_version="fake-v1",
            acquisition_date=end,
            index_value=index_value,
        )

    def sar_composite(self, geometry, pre_event_end, post_event_start, post_event_end):
        if self.scenario not in ("flood", "flood_single_pol"):
            return None
        return SarComposite(
            source_dataset="Sentinel-1 GRD (fake)",
            source_version="fake-v1",
            acquisition_date=post_event_end,
            vv_drop_db=5.0,
            # "flood_single_pol" simulates acquisitions that carried VV only,
            # so the VH-derived DSI indicator and cross-pol feature must stay
            # absent rather than falling back to the VV measurement.
            vh_drop_db=None if self.scenario == "flood_single_pol" else 8.0,
            # A *populated* FeatureCollection, matching what
            # `reduceToVectors().getInfo()` actually returns once `vv_drop_db`
            # clears the flood threshold. The previous empty collection was an
            # internally inconsistent fixture — "flood detected, zero flooded
            # pixels" — and an empty collection is the one shape that never
            # exercises the FeatureCollection-to-geometry conversion the real
            # pipeline needs (tasks.md T0-13).
            flood_extent_geojson={
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"label": 1},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [77.0, 20.0],
                                    [77.005, 20.0],
                                    [77.005, 20.005],
                                    [77.0, 20.005],
                                    [77.0, 20.0],
                                ]
                            ],
                        },
                    }
                ],
            },
        )

    def historical_composite(self, geometry, start, end, years=5):
        if self.scenario == "no_history":
            return []
        return [
            ImageryComposite(
                source_dataset="Sentinel-2 SR Harmonized (fake)",
                source_version="fake-v1",
                acquisition_date=end,
                index_value=0.7,
            )
            for _ in range(years)
        ]


class FakeWeatherClient:
    def precipitation(self, geometry, start, end):
        return 45.0

    def near_real_time_precipitation(self, geometry, start, end):
        return 12.0

    def reanalysis_temperature(self, geometry, start, end):
        return 24.0

    def soil_moisture(self, geometry, start, end):
        return 0.3


class FakeIMDClient:
    def station_record(self, geometry, start, end):
        return None
