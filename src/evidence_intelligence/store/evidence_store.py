"""Persistence layer (HLD §3 'Evidence Store'). Enforces the retention
principle (Constitution §7 / spec.md FR-029) at package-creation time and
never overwrites a component/package row in place (spec.md FR-012,
data-model.md 'Multiple packages per request')."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from evidence_intelligence.store.schema import (
    DamageAssessmentComponentResult,
    EvidencePackage,
    EvidenceRequest,
    ModelComponent,
    PackageTier,
    PerilType,
    RequestStatus,
    SatelliteAnalysisResult,
    WeatherCorrelationResult,
)

RETENTION_YEARS = 10


def retention_expiry_date(generated_at: date) -> date:
    """Constitution §7: retained for 10 years from generation."""
    try:
        return generated_at.replace(year=generated_at.year + RETENTION_YEARS)
    except ValueError:
        # generated_at is Feb 29 on a leap year; +10 years lands on a non-leap year.
        return generated_at.replace(month=2, day=28, year=generated_at.year + RETENTION_YEARS)


class EvidenceStore:
    def __init__(self, session: Session):
        self.session = session

    # -- EvidenceRequest -------------------------------------------------

    def create_request(
        self,
        geometry: str,
        event_date: date,
        peril_type: PerilType,
        external_reference_id: str | None = None,
    ) -> EvidenceRequest:
        request = EvidenceRequest(
            geometry=geometry,
            event_date=event_date,
            peril_type=peril_type,
            external_reference_id=external_reference_id,
            status=RequestStatus.RECEIVED,
        )
        self.session.add(request)
        self.session.commit()
        self.session.refresh(request)
        return request

    def get_request(self, request_id: str) -> EvidenceRequest | None:
        return self.session.get(EvidenceRequest, request_id)

    def set_status(self, request_id: str, status: RequestStatus) -> None:
        request = self.session.get(EvidenceRequest, request_id)
        if request is None:
            raise KeyError(f"no such request: {request_id}")
        request.status = status
        if status == RequestStatus.COMPLETE:
            request.completed_at = datetime.utcnow()
        self.session.commit()

    # -- SatelliteAnalysisResult ------------------------------------------

    def add_satellite_result(
        self,
        request_id: str,
        source_dataset: str,
        source_version: str,
        acquisition_date: date,
        pre_event_index_value: float | None,
        post_event_index_value: float | None,
        index_type: str = "NDVI",
        flood_extent_geometry: str | None = None,
    ) -> SatelliteAnalysisResult:
        result = SatelliteAnalysisResult(
            request_id=request_id,
            source_dataset=source_dataset,
            source_version=source_version,
            acquisition_date=acquisition_date,
            pre_event_index_value=pre_event_index_value,
            post_event_index_value=post_event_index_value,
            index_type=index_type,
            flood_extent_geometry=flood_extent_geometry,
        )
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        return result

    def list_satellite_results(self, request_id: str) -> list[SatelliteAnalysisResult]:
        stmt = select(SatelliteAnalysisResult).where(
            SatelliteAnalysisResult.request_id == request_id
        )
        return list(self.session.scalars(stmt))

    # -- DamageAssessmentComponentResult -----------------------------------

    def add_component_result(
        self,
        request_id: str,
        component: ModelComponent,
        methodology_version: str,
        point_estimate: float,
        confidence_or_accuracy: dict[str, Any],
        damage_classification: str | None = None,
        affected_area_ha: float | None = None,
        component_inputs: dict[str, Any] | None = None,
    ) -> DamageAssessmentComponentResult:
        """spec.md FR-012: a later component's result MUST NOT overwrite an
        earlier row — always inserts a new row, never updates in place."""
        result = DamageAssessmentComponentResult(
            request_id=request_id,
            component=component,
            methodology_version=methodology_version,
            point_estimate=point_estimate,
            confidence_or_accuracy=confidence_or_accuracy,
            damage_classification=damage_classification,
            affected_area_ha=affected_area_ha,
            component_inputs=component_inputs or {},
        )
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        return result

    def list_component_results(
        self, request_id: str
    ) -> list[DamageAssessmentComponentResult]:
        stmt = select(DamageAssessmentComponentResult).where(
            DamageAssessmentComponentResult.request_id == request_id
        )
        return list(self.session.scalars(stmt))

    def get_component_result(
        self, request_id: str, component: ModelComponent
    ) -> DamageAssessmentComponentResult | None:
        stmt = (
            select(DamageAssessmentComponentResult)
            .where(
                DamageAssessmentComponentResult.request_id == request_id,
                DamageAssessmentComponentResult.component == component,
            )
            .order_by(DamageAssessmentComponentResult.result_id.desc())
        )
        return self.session.scalars(stmt).first()

    # -- WeatherCorrelationResult ------------------------------------------

    def add_weather_result(
        self,
        request_id: str,
        source_dataset: str,
        source_version: str,
        observed_value: float,
        historical_baseline: float | None,
        anomaly_score: float | None,
        causation_confidence_score: int,
    ) -> WeatherCorrelationResult:
        result = WeatherCorrelationResult(
            request_id=request_id,
            source_dataset=source_dataset,
            source_version=source_version,
            observed_value=observed_value,
            historical_baseline=historical_baseline,
            anomaly_score=anomaly_score,
            causation_confidence_score=causation_confidence_score,
        )
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        return result

    def list_weather_results(self, request_id: str) -> list[WeatherCorrelationResult]:
        stmt = select(WeatherCorrelationResult).where(
            WeatherCorrelationResult.request_id == request_id
        )
        return list(self.session.scalars(stmt))

    # -- EvidencePackage -----------------------------------------------------

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
        """data-model.md: multiple packages per request are allowed and none
        are deleted or overwritten — a WEATHER_ONLY_PRELIMINARY package is
        never mutated into COMPLETE, a new row is added instead (FR-022)."""
        generated_at = generated_at or datetime.utcnow()
        package = EvidencePackage(
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
        self.session.add(package)
        self.session.commit()
        self.session.refresh(package)
        return package

    def latest_package(self, request_id: str) -> EvidencePackage | None:
        stmt = (
            select(EvidencePackage)
            .where(EvidencePackage.request_id == request_id)
            .order_by(EvidencePackage.generated_at.desc())
        )
        return self.session.scalars(stmt).first()

    def list_packages(self, request_id: str) -> list[EvidencePackage]:
        stmt = select(EvidencePackage).where(EvidencePackage.request_id == request_id)
        return list(self.session.scalars(stmt))
