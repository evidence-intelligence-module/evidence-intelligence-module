"""Causation Analysis Engine (evidence-flow-spec.md §5). Weighted score
(0-100) across temporal, spatial, magnitude, and physiological alignment
between the reported weather event and the observed damage (spec.md FR-015).

**Terms that cannot be measured are excluded, not scored zero (tasks.md T0-06).**
Each term returns `float | None`; the weighted score renormalizes over whichever
terms were actually measured, and is `None` when none were. This is the same
rule `observation.py` applies to signals and `dsi.py` to indicators — an input
nobody measured must not become a number.

Before this, every term had a value on every path, and all four were fabricated
on the weather-only path: `days_between=1` and `distance_km=0.0` were hardcoded
at the call site (100 each), an unmeasured NDVI drop was passed as a measured
`0.0` into a formula that rewards *closeness* to the weather anomaly (100 when
the anomaly was also near zero), and `phenology_flag=None` was read as "checked
and passed" (90) rather than "never checked". A request with **no satellite
imagery at all** therefore scored **98/100**, while a request with a full
optical pair scored 76 — the more damage observed, the lower the confidence,
because a real NDVI drop diverged from a weather anomaly that was near zero.

Also implements FR-024's low-confidence labeling: a request with a
configurable, currently-unset threshold (see
specs/001-evidence-generation-pipeline/issue/open query - causation
confidence low-confidence threshold (FR-024).md) is still always delivered —
this module never suppresses or rejects a package regardless of score."""

from __future__ import annotations

from dataclasses import dataclass, field

from evidence_intelligence.store.schema import PerilType

TEMPORAL_WEIGHT = 0.30
SPATIAL_WEIGHT = 0.25
MAGNITUDE_WEIGHT = 0.25
PHYSIOLOGICAL_WEIGHT = 0.20

TEMPORAL = "temporal_alignment"
SPATIAL = "spatial_alignment"
MAGNITUDE = "magnitude_correlation"
PHYSIOLOGICAL = "physiological_plausibility"

TERM_WEIGHTS = {
    TEMPORAL: TEMPORAL_WEIGHT,
    SPATIAL: SPATIAL_WEIGHT,
    MAGNITUDE: MAGNITUDE_WEIGHT,
    PHYSIOLOGICAL: PHYSIOLOGICAL_WEIGHT,
}


@dataclass
class CausationScoreResult:
    score: int | None
    """`None` when no term could be measured — there is no causation to score
    without at least one measured alignment. Never fabricated to keep a number
    in the package."""

    temporal_alignment: float | None
    spatial_alignment: float | None
    magnitude_correlation: float | None
    physiological_plausibility: float | None
    low_confidence: bool
    contributing: list[str] = field(default_factory=list)
    excluded: dict[str, str] = field(default_factory=dict)
    """Term name -> why it could not be measured. Goes into the package: a
    reader has to be able to tell a 60 computed from four terms from a 60
    computed from one."""


def _temporal_alignment(days_between_event_and_ndvi_drop: int | None) -> float | None:
    """evidence-flow-spec.md §5: NDVI drop within 7 days = 100%; 7-14 days =
    70%; >14 days = 30%.

    `None` when the date of the drop is unknown. With only a pre- and a
    post-event composite, the drop is known to have happened *somewhere between
    the two acquisitions* and no more precisely — a break-point date needs the
    per-field time series `T05-05` produces."""
    if days_between_event_and_ndvi_drop is None:
        return None
    if days_between_event_and_ndvi_drop <= 7:
        return 100.0
    if days_between_event_and_ndvi_drop <= 14:
        return 70.0
    return 30.0


def _spatial_alignment(distance_km_to_weather_anomaly: float | None) -> float | None:
    """Weather anomaly covers the geometry = 100%; within 5km = 80%; within
    10km = 50%; otherwise 0%.

    `None` when the anomaly's spatial footprint was never computed. Note this
    term is currently unmeasurable by construction rather than by accident:
    gridded weather is sampled *at the field*, so "distance from the field to
    the reading" is definitionally zero and says nothing about whether the
    field sits inside the anomaly's extent, which is what the term asks."""
    if distance_km_to_weather_anomaly is None:
        return None
    if distance_km_to_weather_anomaly <= 0:
        return 100.0
    if distance_km_to_weather_anomaly <= 5:
        return 80.0
    if distance_km_to_weather_anomaly <= 10:
        return 50.0
    return 0.0


def _magnitude_correlation(
    normalized_weather_anomaly: float | None, normalized_ndvi_drop: float | None
) -> float | None:
    """Larger weather anomaly should correlate with larger NDVI drop — scored
    as how close the two normalized magnitudes are to each other.

    `None` unless **both** were measured. Scoring an unmeasured drop as `0.0`
    made the term report perfect correlation whenever the weather anomaly was
    also near zero, which is how a request with no imagery reached 98/100."""
    if normalized_weather_anomaly is None or normalized_ndvi_drop is None:
        return None
    normalized_weather_anomaly = max(0.0, min(1.0, normalized_weather_anomaly))
    normalized_ndvi_drop = max(0.0, min(1.0, normalized_ndvi_drop))
    return 100.0 * (1.0 - abs(normalized_weather_anomaly - normalized_ndvi_drop))


def _physiological_plausibility(
    peril_type: PerilType, phenology_flag: str | None, phenology_checked: bool
) -> float | None:
    """Whether the peril is capable of producing the observed damage pattern
    at the crop's inferred growth stage. `peril_type = other` runs the
    generic pass without this heuristic (evidence-flow-spec.md §2).

    `None` when the check never ran. `phenology_flag=None` previously meant
    both "checked, nothing wrong" and "no imagery existed to check against",
    and both scored 90 — a near-ceiling result for a check that never
    happened, on the tier with the weakest evidence."""
    if not peril_type.runs_peril_specific_causation_heuristics:
        return 50.0  # generic pass — neither supports nor contradicts plausibility
    if not phenology_checked:
        return None
    return 40.0 if phenology_flag else 90.0


def score(
    days_between_event_and_ndvi_drop: int | None,
    distance_km_to_weather_anomaly: float | None,
    normalized_weather_anomaly: float | None,
    normalized_ndvi_drop: float | None,
    peril_type: PerilType,
    phenology_flag: str | None,
    low_confidence_threshold: int | None,
    phenology_checked: bool = True,
) -> CausationScoreResult:
    terms: dict[str, float | None] = {
        TEMPORAL: _temporal_alignment(days_between_event_and_ndvi_drop),
        SPATIAL: _spatial_alignment(distance_km_to_weather_anomaly),
        MAGNITUDE: _magnitude_correlation(normalized_weather_anomaly, normalized_ndvi_drop),
        PHYSIOLOGICAL: _physiological_plausibility(
            peril_type, phenology_flag, phenology_checked
        ),
    }

    excluded = {
        TEMPORAL: "no break-point date — the drop's timing is unknown between acquisitions",
        SPATIAL: "the weather anomaly's spatial footprint was not computed",
        MAGNITUDE: "requires both a measured weather anomaly and a measured NDVI drop",
        PHYSIOLOGICAL: "no imagery to infer a growth stage from, so the check never ran",
    }
    contributing = [name for name, value in terms.items() if value is not None]
    excluded = {name: reason for name, reason in excluded.items() if terms[name] is None}

    total_weight = sum(TERM_WEIGHTS[name] for name in contributing)
    if total_weight <= 0:
        final_score = None
    else:
        # Renormalized over measured terms only. Without this an excluded term
        # would still consume its share of the 100 points and drag the score
        # down in proportion to what could not be measured, which is the same
        # error as scoring it zero, one step removed.
        final_score = round(
            sum(terms[name] * TERM_WEIGHTS[name] for name in contributing) / total_weight
        )

    low_confidence = (
        low_confidence_threshold is not None
        and final_score is not None
        and final_score < low_confidence_threshold
    )

    return CausationScoreResult(
        score=final_score,
        temporal_alignment=terms[TEMPORAL],
        spatial_alignment=terms[SPATIAL],
        magnitude_correlation=terms[MAGNITUDE],
        physiological_plausibility=terms[PHYSIOLOGICAL],
        low_confidence=low_confidence,
        contributing=contributing,
        excluded=excluded,
    )
