"""Helpers for turning external label sources into Component 2 training CSVs.

Two-step flow:
1. Normalize a supplier/raw CSV into a canonical label file.
2. Join that canonical label file to a feature CSV containing the declared
   Component 2 feature columns, producing the exact training format expected by
   scripts/train_ai_ml_model.py.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from evidence_intelligence.models.ai_ml import FEATURE_NAMES

CANONICAL_LABEL_FIELDS = [
    "sample_id",
    "source_dataset",
    "source_record_id",
    "crop_type",
    "state",
    "district",
    "season",
    "event_date",
    "latitude",
    "longitude",
    "observed_yield",
    "expected_yield",
    "observed_damage_score",
    "payout_triggered",
    "damage_fraction",
    "label_provenance",
]


@dataclass(frozen=True)
class LabelMapping:
    source_dataset: str
    label_provenance: str
    columns: dict[str, str]
    sample_id_prefix: str = "sample"
    damage_score_scale_max: float | None = None


def load_label_mapping(path: Path) -> LabelMapping:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return LabelMapping(
        source_dataset=payload["source_dataset"],
        label_provenance=payload["label_provenance"],
        columns=payload.get("columns", {}),
        sample_id_prefix=payload.get("sample_id_prefix", "sample"),
        damage_score_scale_max=payload.get("damage_score_scale_max"),
    )


def normalize_label_csv(raw_csv: Path, mapping_json: Path, output_csv: Path) -> int:
    mapping = load_label_mapping(mapping_json)
    with open(raw_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        normalized = [normalize_label_row(row, mapping, idx) for idx, row in enumerate(reader, 1)]
    write_csv(output_csv, CANONICAL_LABEL_FIELDS, normalized)
    return len(normalized)


def normalize_label_row(row: dict[str, str], mapping: LabelMapping, row_number: int) -> dict[str, str]:
    sample_id = mapped_value(row, mapping, "sample_id") or f"{mapping.sample_id_prefix}-{row_number}"
    normalized = {
        "sample_id": sample_id,
        "source_dataset": mapping.source_dataset,
        "source_record_id": mapped_value(row, mapping, "source_record_id"),
        "crop_type": mapped_value(row, mapping, "crop_type"),
        "state": mapped_value(row, mapping, "state"),
        "district": mapped_value(row, mapping, "district"),
        "season": mapped_value(row, mapping, "season"),
        "event_date": mapped_value(row, mapping, "event_date"),
        "latitude": mapped_value(row, mapping, "latitude"),
        "longitude": mapped_value(row, mapping, "longitude"),
        "observed_yield": mapped_value(row, mapping, "observed_yield"),
        "expected_yield": mapped_value(row, mapping, "expected_yield"),
        "observed_damage_score": mapped_value(row, mapping, "observed_damage_score"),
        "payout_triggered": normalize_bool(mapped_value(row, mapping, "payout_triggered")),
        "damage_fraction": derive_damage_fraction(row, mapping),
        "label_provenance": mapping.label_provenance,
    }
    return normalized


def mapped_value(row: dict[str, str], mapping: LabelMapping, field_name: str) -> str:
    column_name = mapping.columns.get(field_name)
    if not column_name:
        return ""
    return (row.get(column_name) or "").strip()


def derive_damage_fraction(row: dict[str, str], mapping: LabelMapping) -> str:
    direct = mapped_value(row, mapping, "damage_fraction")
    if direct:
        return f"{clip_zero_one(float(direct)):.6f}"

    observed_yield = mapped_value(row, mapping, "observed_yield")
    expected_yield = mapped_value(row, mapping, "expected_yield")
    if observed_yield and expected_yield:
        expected = float(expected_yield)
        observed = float(observed_yield)
        if expected <= 0:
            raise ValueError("expected_yield must be > 0 when deriving damage_fraction from yield")
        return f"{clip_zero_one((expected - observed) / expected):.6f}"

    observed_damage_score = mapped_value(row, mapping, "observed_damage_score")
    if observed_damage_score:
        if mapping.damage_score_scale_max is None or mapping.damage_score_scale_max <= 0:
            raise ValueError(
                "damage_score_scale_max must be set in the mapping when deriving "
                "damage_fraction from observed_damage_score"
            )
        return f"{clip_zero_one(float(observed_damage_score) / mapping.damage_score_scale_max):.6f}"

    raise ValueError(
        "could not derive damage_fraction: provide a direct damage_fraction column, "
        "or observed_yield + expected_yield, or observed_damage_score + damage_score_scale_max"
    )


def normalize_bool(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in {"", "na", "n/a", "null", "none"}:
        return ""
    if lowered in {"1", "true", "t", "yes", "y"}:
        return "true"
    if lowered in {"0", "false", "f", "no", "n"}:
        return "false"
    return value.strip()


def assemble_training_csv(
    labels_csv: Path,
    features_csv: Path,
    output_csv: Path,
    *,
    fill_missing_features: float | None = None,
) -> int:
    labels = load_csv_by_key(labels_csv, "sample_id")
    features = load_csv_by_key(features_csv, "sample_id")

    rows: list[dict[str, str]] = []
    for sample_id, label_row in labels.items():
        feature_row = features.get(sample_id)
        if feature_row is None:
            raise ValueError(f"sample_id {sample_id!r} exists in labels but not in features")
        rows.append(
            build_training_row(
                sample_id,
                label_row,
                feature_row,
                fill_missing_features=fill_missing_features,
            )
        )

    fieldnames = [
        *FEATURE_NAMES,
        "damage_fraction",
        "sample_id",
        "source_dataset",
        "label_provenance",
    ]
    write_csv(output_csv, fieldnames, rows)
    return len(rows)


def build_training_row(
    sample_id: str,
    label_row: dict[str, str],
    feature_row: dict[str, str],
    *,
    fill_missing_features: float | None,
) -> dict[str, str]:
    training_row: dict[str, str] = {}
    for feature_name in FEATURE_NAMES:
        value = (feature_row.get(feature_name) or "").strip()
        if not value:
            if fill_missing_features is None:
                raise ValueError(
                    f"sample_id {sample_id!r} is missing required feature {feature_name!r}"
                )
            value = str(fill_missing_features)
        training_row[feature_name] = value

    damage_fraction = (label_row.get("damage_fraction") or "").strip()
    if not damage_fraction:
        raise ValueError(f"sample_id {sample_id!r} is missing damage_fraction in labels file")
    training_row["damage_fraction"] = damage_fraction
    training_row["sample_id"] = sample_id
    training_row["source_dataset"] = (label_row.get("source_dataset") or "").strip()
    training_row["label_provenance"] = (label_row.get("label_provenance") or "").strip()
    return training_row


def load_csv_by_key(path: Path, key_field: str) -> dict[str, dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            key = (row.get(key_field) or "").strip()
            if not key:
                raise ValueError(f"{path} contains a row without {key_field!r}")
            if key in rows:
                raise ValueError(f"{path} contains duplicate {key_field!r} value {key!r}")
            rows[key] = row
        return rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def clip_zero_one(value: float) -> float:
    return max(0.0, min(1.0, value))
