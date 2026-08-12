"""Component 5 — Damage Severity Index (modeling-approach.md §6).
Entropy-weighted, Min-Max-normalized composite computed per field against
its own historical archive — never blended with CCE data (Constitution §4)."""

from __future__ import annotations

import math
from dataclasses import dataclass

METHODOLOGY_VERSION = "dsi-entropy-v1"

# modeling-approach.md §6 Table — name -> "does a higher value mean more damage?"
INDICATOR_DIRECTIONS: dict[str, bool] = {
    "ndvi_deviation": True,
    "lswi_deviation": True,
    "sar_vh_backscatter_deviation": True,
    "fapar_deviation": True,
    "crop_condition_variability": False,  # negative relationship — inverted below
    "weather_anomaly_magnitude": True,
}


@dataclass
class DsiResult:
    score: float
    entropy_weights: dict[str, float]
    normalized_indicators: dict[str, float]


def _min_max_normalize(value: float, historical_values: list[float], positive: bool) -> float:
    if not historical_values:
        return 0.5  # no history — see FR-023 fallback handled by the caller upstream
    lo, hi = min(historical_values), max(historical_values)
    if hi == lo:
        return 0.5
    normalized = (value - lo) / (hi - lo)
    normalized = max(0.0, min(1.0, normalized))
    return normalized if positive else 1.0 - normalized


def _entropy_weights(historical_matrix: dict[str, list[float]]) -> dict[str, float]:
    """Standard entropy-weighting method (modeling-approach.md §6, mirroring
    YES-TECH's CHF Appendix 1 §5.4): indicators that vary more informatively
    across the historical archive receive proportionally more weight."""
    names = list(historical_matrix.keys())
    n = len(next(iter(historical_matrix.values()), []))
    if n == 0:
        return {name: 1.0 / len(names) for name in names}

    entropies: dict[str, float] = {}
    for name in names:
        values = historical_matrix[name]
        total = sum(abs(v) for v in values)
        if total == 0:
            entropies[name] = 1.0
            continue
        proportions = [abs(v) / total for v in values]
        e = -sum(p * math.log(p) for p in proportions if p > 0) / math.log(n) if n > 1 else 0.0
        entropies[name] = e

    diversities = {name: 1.0 - e for name, e in entropies.items()}
    total_diversity = sum(diversities.values())
    if total_diversity == 0:
        return {name: 1.0 / len(names) for name in names}
    return {name: d / total_diversity for name, d in diversities.items()}


def compute(
    current_indicators: dict[str, float],
    historical_indicators: dict[str, list[float]],
) -> DsiResult:
    """FR-014: composite damage severity score normalized against the
    field's own historical archive rather than a group/regional average."""
    normalized = {
        name: _min_max_normalize(
            current_indicators.get(name, 0.0),
            historical_indicators.get(name, []),
            INDICATOR_DIRECTIONS.get(name, True),
        )
        for name in INDICATOR_DIRECTIONS
    }
    weights = _entropy_weights(
        {name: historical_indicators.get(name, []) for name in INDICATOR_DIRECTIONS}
    )
    score = sum(weights[name] * normalized[name] for name in INDICATOR_DIRECTIONS)

    return DsiResult(score=score, entropy_weights=weights, normalized_indicators=normalized)
