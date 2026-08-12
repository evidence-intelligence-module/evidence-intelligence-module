"""Evidence Request Interface endpoints (contracts/evidence-request-api.md).
The sole external interface (Constitution §5) — no caller-specific schema,
no privileged caller (FR-002, FR-028)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, field_validator
from shapely.geometry import shape

from evidence_intelligence.api.dependencies import get_settings, get_store
from evidence_intelligence.config import Settings
from evidence_intelligence.geometry import to_ewkt
from evidence_intelligence.pipeline import run_pipeline_background
from evidence_intelligence.store.evidence_store import EvidenceStore
from evidence_intelligence.store.schema import PerilType, RequestStatus

router = APIRouter()

# Operational estimates only — not an evidentiary figure, so not subject to
# the "don't invent figures" sourcing rule (CLAUDE.md) that governs domain claims.
ESTIMATED_COMPLETION_NORMAL = timedelta(minutes=10)
ESTIMATED_COMPLETION_RETRY_BACKOFF = timedelta(hours=24)


class EvidenceRequestIn(BaseModel):
    geometry: dict
    event_date: date
    peril_type: PerilType
    external_reference_id: str | None = None

    @field_validator("geometry")
    @classmethod
    def _validate_geometry(cls, value: dict) -> dict:
        try:
            shape(value)
        except Exception as exc:
            raise ValueError(f"invalid GeoJSON geometry: {exc}") from exc
        return value


class EvidenceRequestAccepted(BaseModel):
    request_id: str
    status: Literal["IN_PROGRESS"]
    estimated_completion: str


class PackageOut(BaseModel):
    pdf_uri: str
    json_uri: str
    map_uris: list[str]
    methodology_version: str
    causation_confidence_score: int | None = None
    note: str | None = None


class EvidenceRequestStatusOut(BaseModel):
    request_id: str
    status: str
    estimated_completion: str | None = None
    package: PackageOut | None = None


@router.post("/evidence-requests", response_model=EvidenceRequestAccepted, status_code=202)
def create_evidence_request(
    body: EvidenceRequestIn,
    background_tasks: BackgroundTasks,
    store: EvidenceStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> EvidenceRequestAccepted:
    """FR-001/FR-002/FR-003: accepts only the generic contract fields and
    returns a request identifier immediately, before analysis completes —
    the pipeline runs in the background, after the response is sent."""
    request = store.create_request(
        # EWKT, not `str(dict)`. The bare-GeoJSON form happened to parse —
        # `ST_GeomFromEWKT` is lenient about geometries — but relying on that
        # leniency is what hid the FeatureCollection failure elsewhere
        # (tasks.md T0-13). Stored form is now explicit at both call sites.
        geometry=to_ewkt(body.geometry),
        event_date=body.event_date,
        peril_type=body.peril_type,
        external_reference_id=body.external_reference_id,
    )

    background_tasks.add_task(
        run_pipeline_background,
        request.request_id,
        body.geometry,
        body.event_date,
        body.peril_type,
        store,
        settings,
    )

    return EvidenceRequestAccepted(
        request_id=request.request_id,
        status="IN_PROGRESS",
        estimated_completion=(datetime.utcnow() + ESTIMATED_COMPLETION_NORMAL).isoformat(),
    )


@router.get("/evidence-requests/{request_id}", response_model=EvidenceRequestStatusOut)
def get_evidence_request(
    request_id: str, store: EvidenceStore = Depends(get_store)
) -> EvidenceRequestStatusOut:
    """FR-004: current status, or the completed/preliminary package once
    ready. A superseded WEATHER_ONLY_PRELIMINARY package remains separately
    retrievable by its own package_id (data-model.md), but this endpoint
    always returns the most recent package for the request."""
    request = store.get_request(request_id)
    if request is None:
        raise HTTPException(status_code=404, detail=f"no such request: {request_id}")

    if request.status in (RequestStatus.RECEIVED, RequestStatus.IN_PROGRESS):
        return EvidenceRequestStatusOut(
            request_id=request_id,
            status=request.status.value,
            estimated_completion=(
                datetime.utcnow() + ESTIMATED_COMPLETION_NORMAL
            ).isoformat(),
        )

    package = store.latest_package(request_id)
    if package is None:
        return EvidenceRequestStatusOut(request_id=request_id, status=request.status.value)

    weather_results = store.list_weather_results(request_id)
    causation_score = weather_results[-1].causation_confidence_score if weather_results else None

    package_out = PackageOut(
        pdf_uri=package.pdf_uri,
        json_uri=package.json_uri,
        map_uris=package.map_uris,
        methodology_version=package.methodology_version,
        causation_confidence_score=causation_score,
        note=(
            "Weather-only preliminary package — satellite imagery unavailable at "
            "generation time; will be superseded by a complete package once imagery "
            "is available."
            if package.package_tier.value == "WEATHER_ONLY_PRELIMINARY"
            else None
        ),
    )

    return EvidenceRequestStatusOut(
        request_id=request_id,
        status=request.status.value,
        estimated_completion=(
            (datetime.utcnow() + ESTIMATED_COMPLETION_RETRY_BACKOFF).isoformat()
            if request.status == RequestStatus.INSUFFICIENT_DATA
            else None
        ),
        package=package_out,
    )
