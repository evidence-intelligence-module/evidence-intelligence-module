"""Component 2 — AI/ML Damage & Yield-Loss Model (Modeling-Approach.md §3).
Random Forest over the documented multi-source feature set, with mandatory
hyperparameter and MAE/RMSE/NRMSE disclosure (Constitution §2.2).

No labeled training data ships in this repo, so a freshly constructed
`AiMlModel()` is untrained: `predict()` still returns a point estimate (a
disclosed, documented fallback formula), but `confidence_or_accuracy`
honestly reports 'untrained_placeholder' rather than a fabricated
MAE/RMSE/NRMSE figure — inventing an accuracy number here would violate the
same no-invented-figures rule that governs the docs (CLAUDE.md Working
Conventions), and this figure ends up in a legal evidence package
(Constitution §2.2/§2.3).

Training workflow (see README.md "Training the AI/ML Model" for the full
walkthrough and scripts/train_ai_ml_model.py for a runnable entry point):
`fit()` on labeled training data -> `evaluate()` against a disjoint held-out
set to record real MAE/RMSE/NRMSE -> `save()` to a path -> point
`AI_ML_MODEL_PATH` at it so the running service loads it via `load()`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
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
        self._validation_metrics: dict[str, float] = {}

    def fit(self, features: np.ndarray, damage_fraction_labels: np.ndarray) -> None:
        """Trains against labeled data — `features` must be ordered per
        `FEATURE_NAMES` and must NOT include any rows also passed to
        `evaluate()`, or the resulting MAE/RMSE/NRMSE would be measuring the
        model against data it already memorized, not real accuracy."""
        self._model.fit(features, damage_fraction_labels)
        self._is_trained = True
        self._validation_metrics = {}

    def evaluate(
        self, features: np.ndarray, damage_fraction_labels: np.ndarray
    ) -> dict[str, float]:
        """Computes MAE/RMSE/NRMSE against a held-out set disjoint from
        `fit()`'s training data, and records them for `predict()` to report.
        Never call `predict()` and expect real numbers without calling this
        first — an untrained-but-fit model reports `mae`/`rmse`/`nrmse` as
        `None`, never a fabricated figure (Constitution §2.2)."""
        if not self._is_trained:
            raise RuntimeError("cannot evaluate an untrained AiMlModel — call fit() first")
        predictions = self._model.predict(features)
        errors = predictions - damage_fraction_labels
        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(errors**2)))
        label_range = float(damage_fraction_labels.max() - damage_fraction_labels.min())
        nrmse = rmse / label_range if label_range > 0 else None
        metrics = {"mae": mae, "rmse": rmse, "nrmse": nrmse}
        self._validation_metrics = metrics
        return metrics

    def save(self, path: str | Path) -> None:
        """Persists the trained model + its disclosed validation metrics.
        Raises if called on an untrained instance — there's nothing honest
        to disclose from an untrained model, so it shouldn't be saved as if
        it were a real artifact."""
        if not self._is_trained:
            raise RuntimeError("cannot save an untrained AiMlModel — call fit() first")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "model": self._model,
                "validation_metrics": self._validation_metrics,
                "feature_names": FEATURE_NAMES,
                "methodology_version": METHODOLOGY_VERSION,
            },
            path,
        )

    @classmethod
    def load(cls, path: str | Path) -> AiMlModel:
        """Loads a model saved by `save()`. Refuses to load an artifact
        trained against a different `FEATURE_NAMES` order or a different
        `METHODOLOGY_VERSION` — silently predicting from mismatched features
        would produce a wrong, unlabeled-as-such result (Constitution §2.1)."""
        payload = joblib.load(path)
        if payload.get("feature_names") != FEATURE_NAMES:
            raise ValueError(
                f"model at {path} was trained against a different feature order; "
                "retrain against the current FEATURE_NAMES before loading"
            )
        if payload.get("methodology_version") != METHODOLOGY_VERSION:
            raise ValueError(
                f"model at {path} was trained under methodology_version "
                f"{payload.get('methodology_version')!r}, current code is "
                f"{METHODOLOGY_VERSION!r} — retrain or bump the saved artifact's version"
            )
        instance = cls()
        instance._model = payload["model"]
        instance._validation_metrics = payload["validation_metrics"]
        instance._is_trained = True
        return instance

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
