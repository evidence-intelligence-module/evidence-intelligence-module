"""Normalize an external label dataset into the canonical Component 2 label CSV.

The raw supplier dataset can carry any column names; a small JSON mapping file
declares which raw columns correspond to canonical fields. The output of this
script is not yet trainable by itself: it is a label table keyed by `sample_id`
that can later be joined to a feature table produced from satellite/weather
processing.

Usage:
    python scripts/prepare_ai_ml_labels.py \
        --raw data/raw/pbi_india.csv \
        --mapping data/component2/mappings/pbi_india.template.json \
        --output data/component2/labels/pbi_india_labels.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evidence_intelligence.training_data import normalize_label_csv  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True, help="Path to the raw supplier CSV")
    parser.add_argument(
        "--mapping",
        type=Path,
        required=True,
        help="JSON field-mapping file describing how to derive canonical labels",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path for the canonical label CSV keyed by sample_id",
    )
    args = parser.parse_args()

    rows = normalize_label_csv(args.raw, args.mapping, args.output)
    print(f"Wrote {rows} normalized label row(s) to {args.output}")


if __name__ == "__main__":
    main()
