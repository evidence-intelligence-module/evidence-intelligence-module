"""Component 4 — Ensemble Blending Engine (modeling-approach.md §5). Always
combines every component that ran for a request, weighted by each one's own
validation confidence — recomputed per request, never a fixed a-priori split
(spec.md FR-013)."""

from __future__ import annotations

from dataclasses import dataclass

METHODOLOGY_VERSION = "ensemble-v1"

# Deliberately low: the AI/ML model's placeholder fallback is not a calibrated
# prediction (see models/ai_ml.py) and must not be weighted as if it were.
UNTRAINED_PLACEHOLDER_WEIGHT = 0.15


@dataclass
class ComponentContribution:
    component: str
    damage_fraction: float
    weight: float


@dataclass
class EnsembleResult:
    damage_fraction: float
    combined_confidence: float
    contributions: list[ComponentContribution]


def semi_physical_weight(calibration_confidence: float) -> float:
    return calibration_confidence


def ai_ml_weight(confidence_or_accuracy: dict) -> float:
    if confidence_or_accuracy.get("status") == "trained":
        nrmse = confidence_or_accuracy.get("nrmse")
        if nrmse is not None:
            return max(0.05, 1.0 - min(nrmse, 1.0))
        return 0.5
    return UNTRAINED_PLACEHOLDER_WEIGHT


def combine(contributions: list[ComponentContribution]) -> EnsembleResult:
    """Weighted average by each component's own confidence — a request with
    only low-confidence components still produces a result, just with a low
    combined_confidence (never suppressed, spec.md FR-024's sibling principle
    for the damage estimate itself)."""
    if not contributions:
        raise ValueError("ensemble requires at least one component contribution")

    total_weight = sum(c.weight for c in contributions)
    if total_weight <= 0:
        damage_fraction = sum(c.damage_fraction for c in contributions) / len(contributions)
        combined_confidence = 0.0
    else:
        damage_fraction = (
            sum(c.damage_fraction * c.weight for c in contributions) / total_weight
        )
        combined_confidence = total_weight / len(contributions)

    return EnsembleResult(
        damage_fraction=damage_fraction,
        combined_confidence=min(1.0, combined_confidence),
        contributions=contributions,
    )
