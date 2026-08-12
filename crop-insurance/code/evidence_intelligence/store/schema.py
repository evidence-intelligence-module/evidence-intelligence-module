"""SQLAlchemy schema for the five data-model.md entities. Field names and
shapes are taken as given from HLD.md §4 / data-model.md; not an independent
design."""

import enum
import uuid
from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class PerilType(str, enum.Enum):
    HAILSTORM = "hailstorm"
    FLOOD = "flood"
    DROUGHT = "drought"
    CYCLONE = "cyclone"
    UNSEASONAL_RAIN = "unseasonal_rain"
    FROST = "frost"
    HEATWAVE = "heatwave"
    PEST_DISEASE_WEATHER_INDUCED = "pest_disease_weather_induced"
    LANDSLIDE = "landslide"
    CLOUDBURST = "cloudburst"
    OTHER = "other"

    @property
    def is_flood_compatible(self) -> bool:
        """Whether SAR substitutes for optical imagery when this peril's
        window has unusable optical coverage (FR-006, Evidence-Flow-Spec.md
        §4 step 3)."""
        return self is PerilType.FLOOD

    @property
    def runs_peril_specific_causation_heuristics(self) -> bool:
        """FR-015/Evidence-Flow-Spec.md §2: 'other' or ambiguous perils skip
        peril-specific causation heuristics but still run the generic pass."""
        return self is not PerilType.OTHER


class RequestStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    FAILED = "FAILED"


class ModelComponent(str, enum.Enum):
    SEMI_PHYSICAL = "SEMI_PHYSICAL"
    AI_ML = "AI_ML"
    CSM_ASSIMILATION = "CSM_ASSIMILATION"
    ENSEMBLE = "ENSEMBLE"
    DSI = "DSI"


class PackageTier(str, enum.Enum):
    WEATHER_ONLY_PRELIMINARY = "WEATHER_ONLY_PRELIMINARY"
    COMPLETE = "COMPLETE"


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class EvidenceRequest(Base):
    __tablename__ = "evidence_requests"

    request_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: _new_id("EIM")
    )
    geometry: Mapped[str] = mapped_column(Geometry(geometry_type="GEOMETRY", srid=4326))
    event_date: Mapped[date] = mapped_column(Date)
    peril_type: Mapped[PerilType] = mapped_column(Enum(PerilType))
    external_reference_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus), default=RequestStatus.RECEIVED
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    satellite_results: Mapped[list["SatelliteAnalysisResult"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )
    component_results: Mapped[list["DamageAssessmentComponentResult"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )
    weather_results: Mapped[list["WeatherCorrelationResult"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )
    packages: Mapped[list["EvidencePackage"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )


class SatelliteAnalysisResult(Base):
    __tablename__ = "satellite_analysis_results"

    result_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: _new_id("SAT")
    )
    request_id: Mapped[str] = mapped_column(ForeignKey("evidence_requests.request_id"))
    source_dataset: Mapped[str] = mapped_column(String)
    source_version: Mapped[str] = mapped_column(String)
    acquisition_date: Mapped[date] = mapped_column(Date)
    pre_event_index_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    post_event_index_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    index_type: Mapped[str] = mapped_column(String, default="NDVI")
    flood_extent_geometry: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True
    )

    request: Mapped[EvidenceRequest] = relationship(back_populates="satellite_results")


class DamageAssessmentComponentResult(Base):
    __tablename__ = "model_component_results"

    result_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: _new_id("MDL")
    )
    request_id: Mapped[str] = mapped_column(ForeignKey("evidence_requests.request_id"))
    component: Mapped[ModelComponent] = mapped_column(Enum(ModelComponent))
    methodology_version: Mapped[str] = mapped_column(String)
    point_estimate: Mapped[float] = mapped_column(Float)
    confidence_or_accuracy: Mapped[dict] = mapped_column(JSON)
    damage_classification: Mapped[str | None] = mapped_column(String, nullable=True)
    affected_area_ha: Mapped[float | None] = mapped_column(Float, nullable=True)
    component_inputs: Mapped[dict] = mapped_column(JSON, default=dict)

    request: Mapped[EvidenceRequest] = relationship(back_populates="component_results")


class WeatherCorrelationResult(Base):
    __tablename__ = "weather_correlation_results"

    result_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: _new_id("WX")
    )
    request_id: Mapped[str] = mapped_column(ForeignKey("evidence_requests.request_id"))
    source_dataset: Mapped[str] = mapped_column(String)
    source_version: Mapped[str] = mapped_column(String)
    observed_value: Mapped[float] = mapped_column(Float)
    historical_baseline: Mapped[float | None] = mapped_column(Float, nullable=True)
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    causation_confidence_score: Mapped[int] = mapped_column(Integer)

    request: Mapped[EvidenceRequest] = relationship(back_populates="weather_results")


class EvidencePackage(Base):
    __tablename__ = "evidence_packages"

    package_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: _new_id("PKG")
    )
    request_id: Mapped[str] = mapped_column(ForeignKey("evidence_requests.request_id"))
    package_tier: Mapped[PackageTier] = mapped_column(Enum(PackageTier))
    pdf_uri: Mapped[str] = mapped_column(String)
    json_uri: Mapped[str] = mapped_column(String)
    map_uris: Mapped[list[str]] = mapped_column(JSON, default=list)
    methodology_version: Mapped[str] = mapped_column(String)
    checksum: Mapped[str] = mapped_column(String)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    retention_expiry_date: Mapped[date] = mapped_column(Date)

    request: Mapped[EvidenceRequest] = relationship(back_populates="packages")
