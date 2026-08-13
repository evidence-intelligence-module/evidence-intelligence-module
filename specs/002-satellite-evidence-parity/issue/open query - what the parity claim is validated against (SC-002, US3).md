# Open Query: what ground truth the "parity" claim and User Story 3's accuracy improvement are measured against

> **CLOSED 2026-08-13** with [`001`'s label query](../../001-evidence-generation-pipeline/issue/open%20query%20-%20AI-ML%20training%20data%20source%20and%20CCE-label%20question.md), which this file mirrored. Label sourcing is out of scope per `constitution.md` §9.2; the parity claim is validated against whatever labeled held-out split the external supplier provides, on the module's existing MAE/RMSE/NRMSE reporting.

**Spec/Plan/Tasks**: [../spec.md](../spec.md) User Story 3, SC-001, SC-002, [../quickstart.md](../quickstart.md) Scenario 3, [../tasks.md](../tasks.md) T020–T025
**Upstream**: the same underlying question as [`001`'s AI/ML training-data query](../../001-evidence-generation-pipeline/issue/open%20query%20-%20AI-ML%20training%20data%20source%20and%20CCE-label%20question.md), which is still Open. This entry records that `002` now *depends* on it rather than merely being adjacent to it.
**Status**: Open — blocks User Story 3 (T020–T025) and makes SC-001/SC-002 unmeasurable as written.

## The question

`002` is titled a **parity** roadmap: pushing satellite-only evidence "as close as technically achievable to CCE-level verification confidence". Two of its success criteria are stated as measured improvements:

- **SC-002**: damage-classification accuracy "measured as MAE/RMSE/NRMSE against the same held-out validation methodology already in use — improves measurably versus the 10–30m-only baseline".
- **SC-001**: the proportion of monsoon-season requests resolved with a usable package "increases measurably over the current optical-only baseline".

Both presuppose a validation set. So does User Story 3's Independent Test ("training/evaluating Component 2 with and without the added embeddings on the same held-out validation split") and `quickstart.md` Scenario 3 ("run `scripts/train_ai_ml_model.py` twice on the same labeled dataset").

**No such dataset exists in this repo or in any document it references.**

## What was checked

**`001` already recorded this, and it is still open.** Its issue file states plainly that "no labeled `(feature vector → verified damage outcome)` pairs exist anywhere in this repo or its source documents", which is why `models/ai_ml.py` ships untrained and reports `"untrained_placeholder"` rather than a fabricated MAE/RMSE/NRMSE. That file's own Update notes the *plumbing* is complete — `fit()`/`evaluate()`/`save()`/`load()`, `scripts/train_ai_ml_model.py`, `AI_ML_MODEL_PATH` — and that only the data question remains. `002` was written as though the data question were already answered.

**`002`'s prerequisites assume it away.** `quickstart.md`'s Prerequisites require "`AI_ML_MODEL_PATH` pointing at a trained Component 2 model" as a starting condition for Scenario 3. That is not a prerequisite that can currently be satisfied.

**The dependency runs the wrong way round for User Story 3.** Presto produces an embedding; an embedding is only useful to a *trained* downstream model. Adding embedding dimensions to a model with zero labels changes nothing measurable, and on a small pilot-scale label set, adding a large embedding to a `RandomForestRegressor` with `max_features="sqrt"` and `min_samples_leaf=5` is more likely to degrade held-out accuracy than improve it. So US3 at P3 is sequenced ahead of the thing that determines whether it can work at all.

**"Parity" is unfalsifiable without this.** Every precedent `documents/research/satellite-parity-global-precedent-research.md` reviews — EU CAP Check-by-Monitoring, IBLI, ACRE Africa, ARC, RIICE — validated against *something*, and that validation is what made each of them credible. A roadmap that narrows the gap to CCE-level confidence but admits no measurement of the gap cannot demonstrate that it did so. `spec.md`'s Assumptions correctly disclaim literal parity; they do not address how any degree of approach to it would be evidenced.

**Constitution §4's scope is genuinely ambiguous here, and should not be inferred either way.** §4 prohibits ingesting, validating, or disputing CCE plot data and implementing the blended-yield formula. `001`'s issue file already observes this "reads naturally as governing the module's live, per-request behaviour" and does not explicitly address historical, offline use purely as calibration or validation labels. That remains the single highest-leverage unresolved question in the repo, and per Constitution §8 it needs an explicit recorded decision, not an inference from silence.

## Options

Same three options `001`'s issue file lays out, with their `002` consequences added:

| Option | Description | Consequence for `002` |
|---|---|---|
| A. Historical CCE outcomes as offline labels only | Most readily available Indian ground truth; never touched at runtime. Needs an explicit §8 decision that this is compatible with §4's intent. | US3 becomes measurable, and "parity" becomes a claim that can be tested against the very thing parity is defined relative to. |
| B. Non-CCE ground truth only | Insurer pilot surveys, independent field verification, published NDVI-yield-loss research datasets. Cleanly avoids CCE entanglement; slower to reach scale. | US3 becomes measurable once the pilot reaches scale; SC-002's baseline comparison has to wait for it. |
| C. Defer to the Pilot & Validation phase | `documents/README.md` §8's own sequencing. | US3, SC-001 and SC-002 must be re-sequenced *after* the pilot, not shipped as P3 of this roadmap. |

## Recommendation

Not resolved unilaterally here — it belongs to whoever owns the Constitution §4 boundary.

Independent of which option is chosen, one thing follows for `002` immediately: **User Story 3 should not be implemented at P3.** Under B or C it cannot be evaluated until pilot data exists; under A it should follow the labeling decision, not precede it. The work that would make US3 pay off later — populating the features Component 2 already declares but never receives, and moving to per-field time series rather than two-point differencing — is independent of the label question and can proceed now.

SC-001 is separable and salvageable: "proportion of requests resolved with a usable package" needs no yield labels, only a defensible definition of *usable* (see the confidence-tier query in this directory).

## Resolution

Open. Surfaced during a full-scope re-evaluation of `002` on 2026-08-13. Recorded here in addition to `001`'s entry because the dependency direction changed: what was a deferred future question for `001` is a live blocker for `002`.
