# Open Query: AI/ML training data source, and whether historical CCE outcomes may be used as offline training labels

> **CLOSED 2026-08-13 — resolved by scope decision, not by answering it.** Training-label *sourcing* is out of scope per `constitution.md` §9.2: labeled data arrives from an external supplier and this repo neither produces, procures, nor verifies it. The Constitution §4 question this file carried — whether historical CCE outcomes may serve as offline labels — is therefore no longer this module's to decide; a supplier's labels may or may not be CCE-derived, and the module records only what the supplier *declares* via `label_provenance` on the saved model artifact. Retained for its reasoning, particularly the target-variable and sampling-error objections, which remain the strongest argument against CCE labels wherever that decision is now made. See [`documents/notes/2026-08-13-scope-boundaries-design.md`](../../../documents/notes/2026-08-13-scope-boundaries-design.md).

**Plan/Tasks**: [../plan.md](../plan.md), [../tasks.md](../tasks.md) T017 — `src/evidence_intelligence/models/ai_ml.py`
**Status**: **Split and narrowed 2026-08-13.** Now scoped to **one** thing: per-field damage/yield-loss magnitude labels for Component 2, and whether historical CCE outcomes may supply them. Still not blocking `001` today (the model ships transparently untrained). Still the hardest of the three, but no longer the root of everything — two of the three label types it used to carry don't need this decision at all.

## Split (2026-08-13): "labels" was three different datasets

This file originally asked one question — "where does labeled training data come from?" — for everything downstream. A re-assessment found it was carrying three unrelated datasets of very different difficulty, and that bundling them made several downstream items look blocked on the CCE decision when they are not:

| Label type | What it actually is | Where it now lives |
|---|---|---|
| **(a) Damage magnitude** — per field, `damage_fraction` in [0,1] | The verified outcome Component 2 regresses against | **This file.** The genuinely hard one, and the only one the Constitution §4 question governs |
| **(b) Claim outcomes** — was a package's conclusion upheld or overturned? | A binary/ordinal record per settled claim. Calibrates the causation threshold and any numeric confidence-tier component | **Work, not a decision** → `002` `tasks.md` `TV-01`/`TV-02`. Self-generating from operating the system; no CCE involvement |
| **(c) Reference-product accuracy** — WorldCereal's published per-class accuracy for a crop and region | A literature lookup, not fieldwork | Already tracked as the open accuracy-floor item in `002`'s [`crop cross-check accuracy floor`](../../002-satellite-evidence-parity/issue/open%20query%20-%20crop%20cross-check%20accuracy%20floor%20and%20discrepancy-flag%20harm%20posture%20%28FR-010%29.md) |

**(b) is the one that changes the picture.** Every evidence package eventually pairs with a settled claim, so the label source for threshold calibration is a byproduct of running the module — provided somebody records it. Today nothing does: there is no outcome field on `EvidenceRequest` and no outcome endpoint in the contract, so the system generates evidence and discards the only labels it will ever produce for free. `TV-01` fixes that, and it needs no decision from anyone.

The sequencing consequence is direct: **build outcome capture before the Pilot & Validation phase, not after.** Otherwise the pilot runs against real claims, produces hundreds of packages, throws away every label, and this query is exactly as open a year later.

## What this file still gates (narrowed)

| Downstream | How it depends on (a) specifically |
|---|---|
| `002` [`what the parity claim is validated against`](../../002-satellite-evidence-parity/issue/open%20query%20-%20what%20the%20parity%20claim%20is%20validated%20against%20%28SC-002%2C%20US3%29.md) | Same decision, viewed from `002`. Resolve together; **this file is authoritative** |
| `002` User Story 3, SC-002 | Cannot be evaluated without a labeled held-out split of magnitude outcomes |
| `002` [`SAR damage semantics`](../../002-satellite-evidence-parity/issue/open%20query%20-%20SAR%20damage%20semantics%20for%20non-flood%20perils%20%28FR-001%29.md), second half | "What magnitude of VH drop constitutes damage" is a calibration question against (a) |

No longer gated by this file: SC-001 (needs no labels — only a defensible definition of *usable*), the [`causation threshold`](./open%20query%20-%20causation%20confidence%20low-confidence%20threshold%20%28FR-024%29.md) and confidence-tier calibration (both want **(b)**, not (a)), and the crop cross-check accuracy floor (wants **(c)**).

## The argument against Option A, stated properly (added 2026-08-13)

The Options table below describes Option A's risk as *appearing* to contradict §4. Two stronger objections belong on the record before anyone decides:

1. **CCE would become the model's target variable.** Train Component 2 on CCE outcomes and the model is, by construction, an estimator of what CCE would have said — which is the equivalence §4 forbids, routed through a regression rather than through the blended-yield formula. Every package would then be a CCE prediction carrying a disclaimer that it isn't one.
2. **CCE's sampling error lands where it hurts most.** CCE samples a handful of plots per Insurance Unit. Used as labels at *per-field* granularity — the granularity this module exists to provide — that error is largest exactly where it would be applied, so the model would partly be learning the sampling noise.

**A caution on the apparent shortcut**: published district-level yield statistics look like a clean non-CCE external check, but in India the General Crop Estimation Survey's yield figures are themselves largely CCE-derived. Validating against them is using CCE at one remove. Worth knowing before it gets adopted as the "neutral" option, because it isn't one.

This does not close the decision — per Constitution §8 it remains the boundary owner's call — but it should be made against the strongest version of the case, not the mildest.

## The question

`ai_ml.py` (modeling-approach.md §3, Component 2) currently ships **untrained**: no labeled `(feature vector → verified damage outcome)` pairs exist anywhere in this repo or its source documents, so `predict()` uses a disclosed placeholder formula and `confidence_or_accuracy` honestly reports `"untrained_placeholder"` rather than a fabricated MAE/RMSE/NRMSE (Constitution §2.2, and the same no-invented-figures rule `CLAUDE.md` applies to documentation).

Two questions, not one:
1. Where does real labeled training data come from at all?
2. Specifically: can **historical, already-settled CCE-verified yield-loss outcomes** be used purely as *offline training labels* to calibrate this model — never re-ingested at runtime, never blended into any live evidence-generation request — without that counting as the CCE ingestion/blending Constitution §4 prohibits?

## What was checked

`constitution.md` §4: *"Does not ingest, validate, or dispute Crop Cutting Experiment data... Does not implement the YES-TECH blended-yield formula... or claim to replace CCE."* This reads naturally as governing the module's **live, per-request behavior** — what a running evidence-generation call is allowed to touch. It does not explicitly address whether CCE data may be used **historically and offline**, purely to calibrate a model that itself never touches CCE at runtime. No document (`constitution.md`, `hld.md`, `modeling-approach.md`) resolves this either way — it's a genuine gap, not a settled "no."

`documents/README.md` §8 Roadmap already names the intended path: **"Pilot & validation — run against real claims in a small number of districts, validate outputs against ground truth, calibrate thresholds before wider rollout."** That phase hasn't started; it's the most direct route to real labels regardless of the CCE question below.

## Options

| Option | Description |
|---|---|
| A. Historical CCE outcomes as offline labels only | Most readily available Indian ground-truth source for yield-loss outcomes; never touches CCE at runtime. Risks *appearing* to contradict Constitution §4's spirit unless explicitly clarified as compliant by whoever owns that boundary. |
| B. Non-CCE ground truth only | Insurer-run pilot surveys, independent field verification, published academic NDVI-yield-loss research datasets. Cleanly avoids any CCE entanglement; likely slower to reach sufficient scale. |
| C. Defer to the roadmap's own Pilot & validation phase | Run the pilot first, derive labels from its independent verification, and only revisit the CCE question if pilot-scale data proves insufficient. |

## Recommendation

**Updated 2026-08-13**: leaning B/C considerably harder than the original wording below, on the two arguments in "The argument against Option A, stated properly" above — the target-variable objection in particular is a reason of principle, not of appearance. Option A should not be ruled out by inference from silence either, but if chosen it needs an explicit §8 decision recording that both objections were considered.

Independent of which option is chosen, three things should proceed now and are not blocked by it: outcome capture (`TV-01`/`TV-02`), the label-free validations (`TV-03`–`TV-05`), and SC-001, which needs no labels at all.

*Original wording, retained:* Not resolved unilaterally here. Leaning toward B/C as the safer default — it matches the roadmap's own intended sequencing and avoids any appearance of CCE dependency without an explicit decision — but Option A shouldn't be ruled out either, since the underlying Constitution §4 text may not have been written with offline-training-label use in mind at all. Per Constitution §8, this needs an explicit, recorded decision from whoever owns that boundary (with rationale, if Option A is chosen) before implementation, not an inference from silence.

## Resolution

Open. Recorded here rather than assumed either way. Surfaced during a post-implementation status discussion, not during `/speckit-specify`/`/speckit-plan` like FR-011/FR-024 — added to the `issue/` tracker on request for the same reason: don't let an unresolved, consequential question sit only in chat history.

**Update (2026-08-13)**: this is no longer only a future question. `specs/002-satellite-evidence-parity/` was written assuming it was already answered — its User Story 3 (foundation-model embeddings) is evaluated by "training/evaluating Component 2 with and without the added embeddings on the same held-out validation split", its SC-002 is stated as an MAE/RMSE/NRMSE improvement, and its `quickstart.md` lists a trained model at `AI_ML_MODEL_PATH` as a *prerequisite*. None of that is satisfiable while this query is open, and `002`'s central "parity" claim has no measurement without it either. Tracked from `002`'s side in [`../../002-satellite-evidence-parity/issue/open query - what the parity claim is validated against (SC-002, US3).md`](../../002-satellite-evidence-parity/issue/open%20query%20-%20what%20the%20parity%20claim%20is%20validated%20against%20%28SC-002%2C%20US3%29.md). The recommendation there: whichever option is chosen, `002`'s User Story 3 should not be implemented at P3.

**Update**: the plumbing this question was blocking on is no longer missing. `AiMlModel.fit()`/`evaluate()`/`save()`/`load()`, `scripts/train_ai_ml_model.py`, and `AI_ML_MODEL_PATH` wiring in `pipeline.py` now exist and are tested end-to-end (`tests/unit/test_ai_ml.py`, `tests/unit/test_pipeline_ai_ml_loading.py`) — see GUIDE.md "Training the AI/ML Model". What remains open is **only** the data question above: where labeled `(feature vector → verified damage outcome)` pairs come from, and whether historical CCE outcomes may be used as offline labels. Once that's answered, training is a two-command operation, not a code change.
