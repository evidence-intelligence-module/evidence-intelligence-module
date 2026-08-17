# Component 2 Data Workspace

This directory is the staging area for AI/ML training data used by Component 2.

The intended flow is:

1. Put a raw supplier dataset in `raw/`
2. Create or edit a mapping JSON in `mappings/`
3. Normalize the raw dataset into canonical labels:

```bash
python scripts/prepare_ai_ml_labels.py \
  --raw data/component2/raw/pbi_india.csv \
  --mapping data/component2/mappings/pbi_india.template.json \
  --output data/component2/labels/pbi_india_labels.csv
```

4. Produce a feature table keyed by the same `sample_id` in `features/`
5. Join labels + features into the exact training shape expected by the model:

```bash
python scripts/assemble_ai_ml_training_data.py \
  --labels data/component2/labels/pbi_india_labels.csv \
  --features data/component2/features/pbi_india_features.csv \
  --output data/component2/training/pbi_india_training.csv
```

6. Train the model:

```bash
python scripts/train_ai_ml_model.py \
  --data data/component2/training/pbi_india_training.csv \
  --output models/ai_ml_pbi_india.joblib \
  --label-provenance "IFPRI PBI India 2016-17, non-CCE"
```

`prepare_ai_ml_labels.py` supports three ways to derive `damage_fraction`:

- direct `damage_fraction` column from the supplier
- `observed_yield` + `expected_yield`
- `observed_damage_score` + `damage_score_scale_max`

Templates included here are starting points only. The exact raw column names
must be updated to match the files you acquire.
