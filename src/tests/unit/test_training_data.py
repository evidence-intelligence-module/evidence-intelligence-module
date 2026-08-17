from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from evidence_intelligence.models.ai_ml import FEATURE_NAMES
from evidence_intelligence.training_data import (
    CANONICAL_LABEL_FIELDS,
    assemble_training_csv,
    normalize_label_csv,
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_normalize_label_csv_derives_damage_fraction_from_yield(tmp_path):
    raw = tmp_path / "raw.csv"
    raw.write_text(
        "plot_id,state,observed,expected,lat,lon\n"
        "A-1,Haryana,2.0,4.0,29.1,76.3\n",
        encoding="utf-8",
    )
    mapping = tmp_path / "mapping.json"
    mapping.write_text(
        json.dumps(
            {
                "source_dataset": "test dataset",
                "label_provenance": "test dataset, non-CCE",
                "sample_id_prefix": "test",
                "columns": {
                    "sample_id": "plot_id",
                    "state": "state",
                    "observed_yield": "observed",
                    "expected_yield": "expected",
                    "latitude": "lat",
                    "longitude": "lon",
                },
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "labels.csv"

    rows_written = normalize_label_csv(raw, mapping, output)

    assert rows_written == 1
    rows = _read_csv(output)
    assert rows[0]["sample_id"] == "A-1"
    assert rows[0]["state"] == "Haryana"
    assert rows[0]["damage_fraction"] == "0.500000"
    assert rows[0]["label_provenance"] == "test dataset, non-CCE"
    assert list(rows[0].keys()) == CANONICAL_LABEL_FIELDS


def test_normalize_label_csv_derives_damage_fraction_from_score(tmp_path):
    raw = tmp_path / "raw.csv"
    raw.write_text("score\n3\n", encoding="utf-8")
    mapping = tmp_path / "mapping.json"
    mapping.write_text(
        json.dumps(
            {
                "source_dataset": "test dataset",
                "label_provenance": "test dataset, non-CCE",
                "sample_id_prefix": "score",
                "damage_score_scale_max": 5,
                "columns": {"observed_damage_score": "score"},
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "labels.csv"

    normalize_label_csv(raw, mapping, output)

    rows = _read_csv(output)
    assert rows[0]["sample_id"] == "score-1"
    assert rows[0]["damage_fraction"] == "0.600000"


def test_assemble_training_csv_requires_feature_row_for_every_label(tmp_path):
    labels = tmp_path / "labels.csv"
    labels.write_text(
        "sample_id,damage_fraction,source_dataset,label_provenance\n"
        "A-1,0.5,test,test labels\n",
        encoding="utf-8",
    )
    features = tmp_path / "features.csv"
    features.write_text("sample_id\n", encoding="utf-8")

    with pytest.raises(ValueError, match="exists in labels but not in features"):
        assemble_training_csv(labels, features, tmp_path / "training.csv")


def test_assemble_training_csv_joins_labels_and_features(tmp_path):
    labels = tmp_path / "labels.csv"
    labels.write_text(
        "sample_id,damage_fraction,source_dataset,label_provenance\n"
        "A-1,0.5,test,test labels\n",
        encoding="utf-8",
    )
    features = tmp_path / "features.csv"
    feature_header = ",".join(["sample_id", *FEATURE_NAMES])
    feature_values = ",".join(["A-1", *(["0.1"] * len(FEATURE_NAMES))])
    features.write_text(f"{feature_header}\n{feature_values}\n", encoding="utf-8")
    output = tmp_path / "training.csv"

    rows_written = assemble_training_csv(labels, features, output)

    assert rows_written == 1
    rows = _read_csv(output)
    assert rows[0]["damage_fraction"] == "0.5"
    assert rows[0]["sample_id"] == "A-1"
    assert rows[0]["source_dataset"] == "test"
    assert rows[0]["label_provenance"] == "test labels"
    for feature_name in FEATURE_NAMES:
        assert rows[0][feature_name] == "0.1"


def test_assemble_training_csv_can_fill_missing_features(tmp_path):
    labels = tmp_path / "labels.csv"
    labels.write_text(
        "sample_id,damage_fraction,source_dataset,label_provenance\n"
        "A-1,0.5,test,test labels\n",
        encoding="utf-8",
    )
    features = tmp_path / "features.csv"
    features.write_text("sample_id,ndvi_deviation\nA-1,0.2\n", encoding="utf-8")
    output = tmp_path / "training.csv"

    assemble_training_csv(labels, features, output, fill_missing_features=0.0)

    rows = _read_csv(output)
    assert rows[0]["ndvi_deviation"] == "0.2"
    assert rows[0]["evi_deviation"] == "0.0"
