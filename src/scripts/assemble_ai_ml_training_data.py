"""Join canonical labels to a Component 2 feature table.

The output is the exact CSV shape expected by scripts/train_ai_ml_model.py:
all declared FEATURE_NAMES plus `damage_fraction`. A few metadata columns are
also preserved; train_ai_ml_model.py ignores extra columns.

Usage:
    python scripts/assemble_ai_ml_training_data.py \
        --labels data/component2/labels/pbi_india_labels.csv \
        --features data/component2/features/pbi_india_features.csv \
        --output data/component2/training/pbi_india_training.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evidence_intelligence.training_data import assemble_training_csv  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, required=True, help="Canonical label CSV")
    parser.add_argument(
        "--features",
        type=Path,
        required=True,
        help="Feature CSV keyed by sample_id with one column per Component 2 feature",
    )
    parser.add_argument("--output", type=Path, required=True, help="Model-ready training CSV")
    parser.add_argument(
        "--fill-missing-features",
        type=float,
        default=None,
        help="Optional fallback value to use instead of erroring on a missing feature",
    )
    args = parser.parse_args()

    rows = assemble_training_csv(
        args.labels,
        args.features,
        args.output,
        fill_missing_features=args.fill_missing_features,
    )
    print(f"Wrote {rows} training row(s) to {args.output}")


if __name__ == "__main__":
    main()
