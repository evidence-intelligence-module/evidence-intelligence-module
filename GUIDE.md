# Guide

Configuration, running the service, training the AI/ML model, and the current open
issues — the operational how-to for this repo, consolidated in one place. For orientation
(what this is, why it exists, the hard boundaries) see [`documents/README.md`](documents/README.md).
For machine/tooling setup of Spec Kit itself (not this application), see [`SETUP.md`](SETUP.md).

## Configure

### Prerequisites

| Tool | Needed for |
|---|---|
| [Claude Code](https://claude.com/claude-code) | The `/speckit-*` and other skills in `.claude/skills/` only run inside it |
| Git | Cloning, obviously |
| PowerShell 7+ (`pwsh`) | This repo was initialized with `--script ps`, so `.specify/scripts/powershell/*.ps1` are the active automation scripts the `/speckit-*` skills call |

Verify these are present and match what the repo expects:

```
uvx --from git+https://github.com/github/spec-kit.git@v0.16.2 specify check
```

### Set up the Python environment

```bash
cd src
uv venv .venv
uv pip install -e ".[dev]" --python .venv
```

### Set environment variables

The service needs three things to run for real — none are provisioned in this repo:

| Variable | What it's for |
|---|---|
| `GEE_SERVICE_ACCOUNT_CREDENTIALS` | Path to a Google Earth Engine service account key — satellite/weather ingestion |
| `DATABASE_URL` | A PostgreSQL+PostGIS connection string — `docker-compose up -d` in `src/` starts one locally |
| `EVIDENCE_STORE_BUCKET` | Object storage bucket name for generated packages (falls back to local disk in dev — see `LocalObjectStorage`) |

Without these, the service still runs and its test suite still passes (tests inject fakes for GEE/weather/storage), but real evidence requests will fail at the ingestion step.

## Running the App

### Run the tests

```bash
.venv/Scripts/python -m pytest tests/
```

46 tests (unit/contract/integration) — all pass without any of the above configured.

### Run the service

```bash
.venv/Scripts/python -m uvicorn evidence_intelligence.api:app --reload
```

### Submit an evidence request

```bash
curl -X POST http://localhost:8000/evidence-requests \
  -H "Content-Type: application/json" \
  -d '{
    "geometry": {"type": "Polygon", "coordinates": [[[77.0,20.0],[77.01,20.0],[77.01,20.01],[77.0,20.01],[77.0,20.0]]]},
    "event_date": "2026-08-08",
    "peril_type": "hailstorm",
    "external_reference_id": "your-own-correlation-key"
  }'
# -> {"request_id": "EIM-...", "status": "IN_PROGRESS", "estimated_completion": "..."}

curl http://localhost:8000/evidence-requests/EIM-...
# -> {"request_id": "EIM-...", "status": "COMPLETE", "package": {...}}
```

`peril_type` is one of `hailstorm`, `flood`, `drought`, `cyclone`, `unseasonal_rain`, `frost`, `heatwave`, `pest_disease_weather_induced`, `landslide`, `cloudburst`, `other`. Full request/response shapes, including the weather-only-preliminary and 404 cases: [`contracts/evidence-request-api.md`](specs/001-evidence-generation-pipeline/contracts/evidence-request-api.md).

## Training the AI/ML Model

The AI/ML damage model (`evidence_intelligence/models/ai_ml.py`, modeling-approach.md §3) ships **untrained** by default — no labeled data exists in this repo (see the open question below), so it falls back to a disclosed placeholder formula and every prediction honestly reports `confidence_or_accuracy.status == "untrained_placeholder"` rather than a fabricated MAE/RMSE/NRMSE.

Once real labeled data exists, training it and putting it into production is a three-step, verified-working loop:

**1. Prepare labeled data as a CSV.** One row per historical claim, one column per name in `ai_ml.FEATURE_NAMES` (satellite/weather/radar deviations — see the file for the exact list), plus a `damage_fraction` column (the verified outcome, `0`–`1`) as the label. See the [open question on where this data comes from](specs/001-evidence-generation-pipeline/issue/open%20query%20-%20AI-ML%20training%20data%20source%20and%20CCE-label%20question.md) — this isn't solved yet, deliberately.

**2. Train and evaluate:**
```bash
cd src
.venv/Scripts/python scripts/train_ai_ml_model.py --data path/to/labeled.csv --output models/ai_ml_v1.joblib
# Trained on 48 rows, validated on 12 held-out rows.
# MAE=0.0272  RMSE=0.0327  NRMSE=0.2797
# Saved to models/ai_ml_v1.joblib
```
The script holds out a validation split (`--test-size`, default 20%) the model never trains on, and reports MAE/RMSE/NRMSE computed against that held-out set — never a number the model has already seen, and never fabricated if training data is too thin (`evaluate()` requires `fit()` to have run first, `save()` refuses to persist an untrained model).

**3. Point the running service at it:**
```bash
export AI_ML_MODEL_PATH=models/ai_ml_v1.joblib
```
`config.py` reads this at startup; `pipeline.py` loads and caches the model once per process (`_load_ai_ml_model`). From then on, every evidence package's `confidence_or_accuracy.status` reads `"trained"` with real MAE/RMSE/NRMSE instead of the placeholder. If the path is unset, missing, or the saved model was trained against a different feature set or methodology version, the service logs it and falls back to the untrained placeholder rather than crashing or silently mispredicting.

## Open Issues

These questions have no sourced answer in `documents/` or `yestech_manual_2023.md` and are deliberately deferred rather than guessed at. Full detail (what was checked, what task/FR each blocks) lives in each feature's own `issue/README.md`.

**Evidence Generation Pipeline** — [`specs/001-evidence-generation-pipeline/issue/README.md`](specs/001-evidence-generation-pipeline/issue/README.md):

- **Open — split & narrowed** — AI/ML training data source and CCE-label question. The model ships transparently untrained today (see "Training the AI/ML Model" above). Split on 2026-08-13 once "labels" turned out to be three separate datasets: **per-field damage magnitude** stays here and is the only one the Constitution §4 CCE decision governs; **claim outcomes** are work rather than a decision (`002` `TV-01`/`TV-02`); **reference-product accuracy** is a literature lookup tracked in `002`'s crop cross-check query. Recommendation moved harder toward non-CCE sources — training on CCE outcomes makes CCE the model's target variable, which is the equivalence §4 forbids, just routed through a regression.
- **Open — reframed** — CSM high-scrutiny trigger criteria (FR-011). The trigger is not what blocks Component 3: `csm_assimilation.run()` is a placeholder that echoes its input, so enabling the tier would add false corroboration to a confidence-weighted ensemble. **Leave `CSM_HIGH_SCRUTINY_ENABLED` off** until the component is genuinely implemented.
- **Open — narrowed** — Causation confidence low-confidence threshold (FR-024). Cannot be calibrated until `002`'s `T0-06` lands; 55 of the score's 100 points are currently hardcoded, so there is no distribution to calibrate against.
- **Open — narrowed** — Expected request volume and concurrency target. Now capacity sizing only; the durability/architecture half is settled on other grounds (`002` `T05-06`).
- **Open — live in shipped code** — Damage classification band thresholds. `_classify`'s 0.1/0.33/0.66 appear nowhere in `documents/`, and YES-TECH defines no transferable severity banding — so a categorical label in a §65B package rests on invented figures. Disclosure fix is `002` `T0-17`.
- **Open — live in shipped code** — Harvest Index source and per-crop resolution. A flat `0.4` for every crop, against `modeling-approach.md` §2's commitment to per-variety values "clearly labeled as a modeling assumption". Scales every yield-loss figure. Disclosure fix is `002` `T0-18`; per-crop resolution needs a request-contract field, to be decided with `002`'s User Story 4.

**Satellite Evidence Parity Roadmap** — [`specs/002-satellite-evidence-parity/issue/README.md`](specs/002-satellite-evidence-parity/issue/README.md):

- **Open** — What the parity claim is validated against (SC-002, US3): the `002`-side view of `001`'s root label question above. Resolve there.
- **Narrowed** ×2 — SAR damage semantics for non-flood perils (FR-001): polarization half fixed as a defect (T0-15), magnitude-calibration half moved to the label question. Live: whether SAR is reached for non-flood perils — decidable now, and separating it means US1 no longer waits on the label decision.
- **Split** — Supplementary evidence re-evaluation and package supersession (FR-006): package lineage was a defect → `T0-16`. Live: whether attaching evidence re-evaluates anything.
- **Provisional default** — Confidence tier threshold values (FR-004): tier assigned by a rule table over the evidence-inputs manifest, needing no unsourced cut point. No longer blocks `T016`.
- **Provisional default** — Crop cross-check harm posture (FR-010): three-state `outcome` + mandatory framing adopted. Open: the accuracy floor, and whether to ship User Story 4 at all.
- **Provisional default** — Personal data in caller-supplied attachment metadata (FR-006): `caller_supplied_metadata` dropped (nothing read it), `uri` constrained. Open: reconciling the 10-year retention floor with DPDP obligations, which is a `documents/` change.
- **Resolved** 2026-08-12 — Commercial satellite tasking budget: free-only for this rollout; retained for its rationale.

Each tracker's `README.md` carries the same Open / Narrowed / Resolved status per entry. The `open query - ` filename prefix is a naming convention, not a status — files aren't renamed when they close, because `spec.md`/`plan.md`/`tasks.md` link them by path.

Separately, [`specs/002-satellite-evidence-parity/tasks.md`](specs/002-satellite-evidence-parity/tasks.md) carries four pre-feature task groups that are **not** open questions and are blocked by none of the above: **Phase 0** base-pipeline corrections (defects with unambiguous right answers; several block the rest of `002` from being measurable at all), **Phase 0.4** pipeline decomposition (see [`pipeline-decomposition-design.md`](specs/002-satellite-evidence-parity/pipeline-decomposition-design.md) — restructures `pipeline.py` so an absent input cannot be read as a measured value without a test failing, and corrects a fifth defect of that class in the Damage Severity Index), **Phase 0.5** evidence-processing improvements, and **Phase 0.6** label capture and label-free validation.

One item there is time-sensitive rather than merely useful: **`TV-01` (claim-outcome capture) must land before the Pilot & Validation phase.** There is no outcome field on `EvidenceRequest` and no outcome endpoint in the contract today, so the module generates evidence and discards the only training labels it will ever get for free. If the pilot runs first, its labels are lost and the label question is exactly as open afterwards.
