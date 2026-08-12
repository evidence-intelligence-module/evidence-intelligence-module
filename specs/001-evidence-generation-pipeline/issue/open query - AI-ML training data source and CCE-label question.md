# Open Query: AI/ML training data source, and whether historical CCE outcomes may be used as offline training labels

**Plan/Tasks**: [../plan.md](../plan.md), [../tasks.md](../tasks.md) T017 — `src/evidence_intelligence/models/ai_ml.py`
**Status**: Deferred — not blocking today (the model already ships transparently untrained), but blocks any future move to actually train/calibrate it

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
