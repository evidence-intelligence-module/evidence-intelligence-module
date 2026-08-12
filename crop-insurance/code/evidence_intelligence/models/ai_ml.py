"""Component 2 — AI/ML Damage & Yield-Loss Model (Modeling-Approach.md §3).
Random Forest over the documented multi-source feature set, with mandatory
hyperparameter and MAE/RMSE/NRMSE disclosure (Constitution §2.2).

No labeled training data exists in this repo yet, so this ships untrained:
`predict()` still returns a point estimate (a disclosed, documented fallback
formula), but `confidence_or_accuracy` honestly reports 'untrained_placeholder'
rather than a fabricated MAE/RMSE/NRMSE figure — inventing an accuracy number
here would violate the same no-invented-figures rule that governs the docs
(CLAUDE.md Working Conventions), and this figure ends up in a legal evidence
package (Constitution §2.2/§2.3)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import RandomForestRegressor

METHODOLOGY_VERSION = "ai-ml-rf-v1"

# Modeling-Approach.md §3 Table — fixed feature order for reproducibility (FR-021).
FEATURE_NAMES: list[str] = [
    "ndvi_deviation",
    "evi_deviation",
    "red_edge_index",
    "ndwi_deviation",
    "lswi_deviation",
    "vh_vv_backscatter_deviation",
    "rvi",
    "rainfall_anomaly",
    "rainy_day_count",
    "dry_spell_length",
    "wet_spell_length",
    "temperature_anomaly",
    "growing_degree_days",
    "heat_cold_wave_flag",
    "fapar_deviation",
    "lai_deviation",
    "soil_moisture_deviation",
]

# Disclosed per Modeling-Approach.md §3's mandated disclosure discipline
# (matching YES-TECH §2.3): number of trees, features per split, min leaf size.
HYPERPARAMETERS = {
    "n_estimators": 200,
    "max_features": "sqrt",
    "min_samples_leaf": 5,
    "random_state": 42,  # fixed for reproducibility (FR-021, Constitution §2.1)
}


@dataclass
class AiMlResult:
    damage_fraction: float
    yield_loss_fraction: float
    confidence_or_accuracy: dict = field(default_factory=dict)


class AiMlModel:
    def __init__(self):
        self._model = RandomForestRegressor(**HYPERPARAMETERS)
        self._is_trained = False
        self._validation_metrics: dict[str, float] | None = None

    def fit(
        self, features: np.ndarray, damage_fraction_labels: np.ndarray, validation_metrics: dict
    ) -> None:
        """Trains against labeled data (out of scope until real, ground-truthed
        training data exists) and records the caller-supplied validation-set
        MAE/RMSE/NRMSE — never computed by fabrication."""
        self._model.fit(features, damage_fraction_labels)
        self._is_trained = True
        self._validation_metrics = validation_metrics

    def predict(self, feature_vector: dict[str, float], harvest_index: float) -> AiMlResult:
        ordered = np.array([[feature_vector.get(name, 0.0) for name in FEATURE_NAMES]])

        if self._is_trained:
            damage_fraction = float(np.clip(self._model.predict(ordered)[0], 0.0, 1.0))
            accuracy = {
                "status": "trained",
                "mae": self._validation_metrics.get("mae"),
                "rmse": self._validation_metrics.get("rmse"),
                "nrmse": self._validation_metrics.get("nrmse"),
            }
        else:
            damage_fraction = _placeholder_estimate(ordered[0])
            accuracy = {
                "status": "untrained_placeholder",
                "mae": None,
                "rmse": None,
                "nrmse": None,
                "note": (
                    "No labeled training data available yet; this is a disclosed "
                    "fallback formula, not a calibrated model prediction."
                ),
            }

        return AiMlResult(
            damage_fraction=damage_fraction,
            yield_loss_fraction=damage_fraction * harvest_index,
            confidence_or_accuracy=accuracy,
        )


def _placeholder_estimate(feature_row: np.ndarray) -> float:
    """Disclosed, deterministic fallback: mean of the deviation/anomaly
    features (all designed to be signed, positive = more damage-consistent),
    clipped to [0, 1]. Not a trained prediction — see `confidence_or_accuracy`."""
    return float(np.clip(np.mean(np.abs(feature_row)) / 2.0, 0.0, 1.0))
