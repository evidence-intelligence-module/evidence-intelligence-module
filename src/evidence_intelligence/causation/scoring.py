"""Causation Analysis Engine (Evidence-Flow-Spec.md §5). Weighted score
(0-100) across temporal, spatial, magnitude, and physiological alignment
between the reported weather event and the observed damage (spec.md FR-015).

Also implements FR-024's low-confidence labeling: a request with a
configurable, currently-unset threshold (see
specs/001-evidence-generation-pipeline/issue/open query - causation
confidence low-confidence threshold (FR-024).md) is still always delivered —
this module never suppresses or rejects a package regardless of score."""

from __future__ import annotations

from dataclasses import dataclass

from evidence_intelligence.store.schema import PerilType

TEMPORAL_WEIGHT = 0.30
SPATIAL_WEIGHT = 0.25
MAGNITUDE_WEIGHT = 0.25
PHYSIOLOGICAL_WEIGHT = 0.20


@dataclass
class CausationScoreResult:
    score: int  # 0-100
    temporal_alignment: float
    spatial_alignment: float
    magnitude_correlation: float
    physiological_plausibility: float
    low_confidence: bool


def _temporal_alignment(days_between_event_and_ndvi_drop: int) -> float:
    """Evidence-Flow-Spec.md §5: NDVI drop within 7 days = 100%; 7-14 days =
    70%; >14 days = 30%."""
    if days_between_event_and_ndvi_drop <= 7:
        return 100.0
    if days_between_event_and_ndvi_drop <= 14:
        return 70.0
    return 30.0


def _spatial_alignment(distance_km_to_weather_anomaly: float) -> float:
    """Weather anomaly covers the geometry = 100%; within 5km = 80%; within
    10km = 50%; otherwise 0%."""
    if distance_km_to_weather_anomaly <= 0:
        return 100.0
    if distance_km_to_weather_anomaly <= 5:
        return 80.0
    if distance_km_to_weather_anomaly <= 10:
        return 50.0
    return 0.0


def _magnitude_correlation(
    normalized_weather_anomaly: float, normalized_ndvi_drop: float
) -> float:
    """Larger weather anomaly should correlate with larger NDVI drop — scored
    as how close the two normalized magnitudes are to each other."""
    normalized_weather_anomaly = max(0.0, min(1.0, normalized_weather_anomaly))
    normalized_ndvi_drop = max(0.0, min(1.0, normalized_ndvi_drop))
    return 100.0 * (1.0 - abs(normalized_weather_anomaly - normalized_ndvi_drop))


def _physiological_plausibility(
    peril_type: PerilType, phenology_flag: str | None
) -> float:
    """Whether the peril is capable of producing the observed damage pattern
    at the crop's inferred growth stage. `peril_type = other` runs the
    generic pass without this heuristic (Evidence-Flow-Spec.md §2)."""
    if not peril_type.runs_peril_specific_causation_heuristics:
        return 50.0  # generic pass — neither supports nor contradicts plausibility
    return 40.0 if phenology_flag else 90.0


def score(
    days_between_event_and_ndvi_drop: int,
    distance_km_to_weather_anomaly: float,
    normalized_weather_anomaly: float,
    normalized_ndvi_drop: float,
    peril_type: PerilType,
    phenology_flag: str | None,
    low_confidence_threshold: int | None,
) -> CausationScoreResult:
    temporal = _temporal_alignment(days_between_event_and_ndvi_drop)
    spatial = _spatial_alignment(distance_km_to_weather_anomaly)
    magnitude = _magnitude_correlation(normalized_weather_anomaly, normalized_ndvi_drop)
    physiological = _physiological_plausibility(peril_type, phenology_flag)

    weighted = (
        temporal * TEMPORAL_WEIGHT
        + spatial * SPATIAL_WEIGHT
        + magnitude * MAGNITUDE_WEIGHT
        + physiological * PHYSIOLOGICAL_WEIGHT
    )
    final_score = round(weighted)

    low_confidence = (
        low_confidence_threshold is not None and final_score < low_confidence_threshold
    )

    return CausationScoreResult(
        score=final_score,
        temporal_alignment=temporal,
        spatial_alignment=spatial,
        magnitude_correlation=magnitude,
        physiological_plausibility=physiological,
        low_confidence=low_confidence,
    )
