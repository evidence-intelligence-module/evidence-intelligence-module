# Open Query: AI/ML training data source, and whether historical CCE outcomes may be used as offline training labels

**Plan/Tasks**: [../plan.md](../plan.md), [../tasks.md](../tasks.md) T017 — `src/evidence_intelligence/models/ai_ml.py`
**Status**: **Open — root dependency of this repo's open-query tree** (re-assessed 2026-08-13). Still not blocking `001` today (the model ships transparently untrained), but every other numeric-threshold question across both features terminates here. If one decision gets made, make this one.

## What this gates (added 2026-08-13)

A cross-tracker evaluation on 2026-08-13 found this query sitting underneath most of the others, which none of the individual files stated:

| Downstream | How it depends on this |
|---|---|
| `002` [`what the parity claim is validated against`](../../002-satellite-evidence-parity/issue/open%20query%20-%20what%20the%20parity%20claim%20is%20validated%20against%20%28SC-002%2C%20US3%29.md) | Same decision, viewed from `002`. Resolve together; **this file is authoritative** |
| `002` User Story 3, SC-001, SC-002 | Cannot be evaluated without a labeled held-out split |
| `002` [`SAR damage semantics`](../../002-satellite-evidence-parity/issue/open%20query%20-%20SAR%20damage%20semantics%20for%20non-flood%20perils%20%28FR-001%29.md), second half | "What magnitude of VH drop constitutes damage" is a calibration question, not a physics one |
| [`causation confidence low-confidence threshold (FR-024)`](./open%20query%20-%20causation%20confidence%20low-confidence%20threshold%20%28FR-024%29.md) | Its own resolution defers to "empirical calibration against real claim outcomes" — which is this data |
| `002` [`confidence tier threshold values (FR-004)`](../../002-satellite-evidence-parity/issue/open%20query%20-%20confidence%20tier%20threshold%20values%20%28FR-004%29.md) | Its provisional rule-table default ships without labels, but any later numeric calibration of tier boundaries needs them |

The practical consequence: the two `002` gates previously described as "most urgent" are both downstream of this one.

## The question

`ai_ml.py` (Modeling-Approach.md §3, Component 2) currently ships **untrained**: no labeled `(feature vector → verified damage outcome)` pairs exist anywhere in this repo or its source documents, so `predict()` uses a disclosed placeholder formula and `confidence_or_accuracy` honestly reports `"untrained_placeholder"` rather than a fabricated MAE/RMSE/NRMSE (Constitution §2.2, and the same no-invented-figures rule `CLAUDE.md` applies to documentation).

Two questions, not one:
1. Where does real labeled training data come from at all?
2. Specifically: can **historical, already-settled CCE-verified yield-loss outcomes** be used purely as *offline training labels* to calibrate this model — never re-ingested at runtime, never blended into any live evidence-generation request — without that counting as the CCE ingestion/blending Constitution §4 prohibits?

## What was checked

`Constitution.md` §4: *"Does not ingest, validate, or dispute Crop Cutting Experiment data... Does not implement the YES-TECH blended-yield formula... or claim to replace CCE."* This reads naturally as governing the module's **live, per-request behavior** — what a running evidence-generation call is allowed to touch. It does not explicitly address whether CCE data may be used **historically and offline**, purely to calibrate a model that itself never touches CCE at runtime. No document (`Constitution.md`, `HLD.md`, `Modeling-Approach.md`) resolves this either way — it's a genuine gap, not a settled "no."

`documents/README.md` §8 Roadmap already names the intended path: **"Pilot & validation — run against real claims in a small number of districts, validate outputs against ground truth, calibrate thresholds before wider rollout."** That phase hasn't started; it's the most direct route to real labels regardless of the CCE question below.

## Options

| Option | Description |
|---|---|
| A. Historical CCE outcomes as offline labels only | Most readily available Indian ground-truth source for yield-loss outcomes; never touches CCE at runtime. Risks *appearing* to contradict Constitution §4's spirit unless explicitly clarified as compliant by whoever owns that boundary. |
| B. Non-CCE ground truth only | Insurer-run pilot surveys, independent field verification, published academic NDVI-yield-loss research datasets. Cleanly avoids any CCE entanglement; likely slower to reach sufficient scale. |
| C. Defer to the roadmap's own Pilot & validation phase | Run the pilot first, derive labels from its independent verification, and only revisit the CCE question if pilot-scale data proves insufficient. |

## Recommendation

Not resolved unilaterally here. Leaning toward B/C as the safer default — it matches the roadmap's own intended sequencing and avoids any appearance of CCE dependency without an explicit decision — but Option A shouldn't be ruled out either, since the underlying Constitution §4 text may not have been written with offline-training-label use in mind at all. Per Constitution §8, this needs an explicit, recorded decision from whoever owns that boundary (with rationale, if Option A is chosen) before implementation, not an inference from silence.

## Resolution

Open. Recorded here rather than assumed either way. Surfaced during a post-implementation status discussion, not during `/speckit-specify`/`/speckit-plan` like FR-011/FR-024 — added to the `issue/` tracker on request for the same reason: don't let an unresolved, consequential question sit only in chat history.

**Update (2026-08-13)**: this is no longer only a future question. `specs/002-satellite-evidence-parity/` was written assuming it was already answered — its User Story 3 (foundation-model embeddings) is evaluated by "training/evaluating Component 2 with and without the added embeddings on the same held-out validation split", its SC-002 is stated as an MAE/RMSE/NRMSE improvement, and its `quickstart.md` lists a trained model at `AI_ML_MODEL_PATH` as a *prerequisite*. None of that is satisfiable while this query is open, and `002`'s central "parity" claim has no measurement without it either. Tracked from `002`'s side in [`../../002-satellite-evidence-parity/issue/open query - what the parity claim is validated against (SC-002, US3).md`](../../002-satellite-evidence-parity/issue/open%20query%20-%20what%20the%20parity%20claim%20is%20validated%20against%20%28SC-002%2C%20US3%29.md). The recommendation there: whichever option is chosen, `002`'s User Story 3 should not be implemented at P3.

**Update**: the plumbing this question was blocking on is no longer missing. `AiMlModel.fit()`/`evaluate()`/`save()`/`load()`, `scripts/train_ai_ml_model.py`, and `AI_ML_MODEL_PATH` wiring in `pipeline.py` now exist and are tested end-to-end (`tests/unit/test_ai_ml.py`, `tests/unit/test_pipeline_ai_ml_loading.py`) — see GUIDE.md "Training the AI/ML Model". What remains open is **only** the data question above: where labeled `(feature vector → verified damage outcome)` pairs come from, and whether historical CCE outcomes may be used as offline labels. Once that's answered, training is a two-command operation, not a code change.
