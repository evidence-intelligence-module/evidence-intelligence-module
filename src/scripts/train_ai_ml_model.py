"""Trains the AI/ML damage model (evidence_intelligence.models.ai_ml) against
labeled data and saves it for the running service to load via
AI_ML_MODEL_PATH. See GUIDE.md "Training the AI/ML Model" for the full
walkthrough. No labeled data ships in this repo, and sourcing it is out of
scope for this module (documents/constitution.md §9.2) — it is supplied by
whoever operates the deployment. What this module does require is that the
supplier's declaration of where the labels came from is recorded with the
artifact, via --label-provenance, since it reaches every evidence package.

Usage:
    python scripts/train_ai_ml_model.py \
        --data path/to/labeled.csv \
        --output models/ai_ml_v1.joblib \
        --label-provenance "insurer pilot survey, Maharashtra 2025-26, non-CCE"

CSV format: one header row, one column per name in ai_ml.FEATURE_NAMES, plus
a `damage_fraction` column (the verified outcome, in [0, 1]) as the label.
Extra columns are ignored.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evidence_intelligence.models.ai_ml import FEATURE_NAMES, AiMlModel  # noqa: E402

LABEL_COLUMN = "damage_fraction"


def load_csv(path: Path) -> tuple[np.ndarray, np.ndarray]:
    features: list[list[float]] = []
    labels: list[float] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        available = reader.fieldnames or []
        missing = [name for name in [*FEATURE_NAMES, LABEL_COLUMN] if name not in available]
        if missing:
            raise ValueError(f"{path} is missing required column(s): {missing}")
        for row in reader:
            features.append([float(row[name]) for name in FEATURE_NAMES])
            labels.append(float(row[LABEL_COLUMN]))
    if len(features) < 10:
        raise ValueError(
            f"only {len(features)} labeled rows found in {path} — too few to train "
            "and hold out a meaningful validation split"
        )
    return np.array(features), np.array(labels)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="Path to labeled CSV")
    parser.add_argument("--output", type=Path, required=True, help="Path to save the trained model")
    parser.add_argument("--test-size", type=float, default=0.2, help="Held-out validation fraction")
    parser.add_argument(
        "--random-state", type=int, default=42, help="Split seed, for a reproducible split"
    )
    parser.add_argument(
        "--label-provenance",
        required=True,
        help=(
            "Where these labels came from, as stated by whoever supplied them "
            '(e.g. "insurer pilot survey, Maharashtra 2025-26, non-CCE"). Required, '
            "unverified, and reported in every evidence package this model produces. "
            "Pass 'unknown' if the supplier did not say — constitution.md §9.2 puts "
            "sourcing out of scope, not disclosure."
        ),
    )
    args = parser.parse_args()

    features, labels = load_csv(args.data)
    x_train, x_val, y_train, y_val = train_test_split(
        features, labels, test_size=args.test_size, random_state=args.random_state
    )

    model = AiMlModel()
    model.fit(x_train, y_train)
    metrics = model.evaluate(x_val, y_val)
    model.save(args.output, label_provenance=args.label_provenance)

    print(f"Trained on {len(x_train)} rows, validated on {len(x_val)} held-out rows.")
    print(f"MAE={metrics['mae']:.4f}  RMSE={metrics['rmse']:.4f}  NRMSE={metrics['nrmse']:.4f}")
    print(f"Saved to {args.output}")
    print(f"Label provenance recorded: {args.label_provenance}")
    print(f"Point the running service at it: export AI_ML_MODEL_PATH={args.output}")


if __name__ == "__main__":
    main()
