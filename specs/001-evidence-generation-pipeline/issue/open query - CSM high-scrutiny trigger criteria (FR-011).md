# Open Query: CSM high-scrutiny trigger criteria (FR-011)

**Spec**: [../spec.md](../spec.md) — FR-011
**Status**: **Reframed 2026-08-13** — the trigger criteria below is a real question, but it is not what currently blocks Component 3. See "Reframing" first.

## Reframing (2026-08-13): the trigger is not the blocker

A cross-tracker evaluation on 2026-08-13 checked this query against the code and found it asks the wrong question first.

`models/csm_assimilation.py`'s `run()` is a placeholder. It returns `clip(damage_signal, 0, 1)` at a fixed `calibration_confidence` of 0.4 — no WOFOST, no InfoCrop, no assimilated LAI or soil-moisture state, which is the entire substance of `Modeling-Approach.md` §4. At the `pipeline.py` call site, `damage_signal` is `ndvi_drop`, the same quantity that drives Component 2's feature vector.

So enabling the tier today would add a component that **re-reports an existing component's input as though it were an independent third estimate**. `models/ensemble.py` combines contributions by confidence-weighted average, which treats agreement between components as corroboration — so the effect is not a harmless no-op, it is manufactured corroboration in a figure that ends up in a legal evidence package. The 0.4 confidence limits the magnitude; it does not change the kind.

The module's own header docstring asserted the opposite — *"This module is a real, callable implementation; only the decision of when to call it is unresolved"* — while `run()`'s docstring two lines below called itself a placeholder. That contradiction invited exactly the wrong action (flipping `CSM_HIGH_SCRUTINY_ENABLED` on the belief that only policy was missing) and was corrected on 2026-08-13.

**Therefore**: the blocking item for Component 3 is *implementing* it — wiring a calibrated crop simulation model per `Modeling-Approach.md` §4. The trigger-criteria question below stays open and stays valid, but it is downstream of that work, not ahead of it, and there is no value in resolving it first.

## The original question (still open, now correctly sequenced)

`HLD.md` §3 and `Evidence-Flow-Spec.md` §4 both name a "high-scrutiny"/"high-value" tier of requests that additionally runs the CSM (crop-simulation-model) assimilation component, on top of the semi-physical and AI/ML models that run for every request. Neither document defines what makes a request "high-scrutiny."

## What was checked

Searched `YESTECH_Manual_2023.md` for a transferable precedent. The closest analog is not a per-claim escalation rule — it's a district/season-level statistical-audit rule: "at least 10 CCEs per IU covering 5–10% of IUs" get deeper ground-truth verification each season, plus a graded weightage table tied to how many CCEs a district records (Table 4). That mechanism is explicitly CCE-based, which this module is barred from touching (Constitution §4), so it doesn't transfer directly to a per-request trigger.

## Options considered (presented to user 2026-08-12)

| Option | Description |
|---|---|
| Claim value threshold | Requests above a defined estimated-loss/sum-insured amount get the CSM tier |
| Always run CSM | Drop the gate; run CSM assimilation on every request alongside the other two model families |
| Caller-flagged | Requester can flag a request as high-scrutiny at submission (e.g. insurer's own escalation/audit flag) |
| Defer to planning | Leave as an open, explicitly-flagged assumption rather than inventing a number/rule now |

User response: asked for a recommendation rather than picking directly ("what should be the right approach").

## Recommendation

No existing document defines this, and it reads as a product/business policy decision (what counts as high enough value or risk to warrant the more expensive CSM tier) rather than a technical constant derivable from the current spec set. Recommend deferring to whoever owns claim/product policy, to be resolved concretely during `/speckit-plan` rather than guessed here — consistent with not inventing figures/criteria the source documents don't support (`CLAUDE.md` working conventions).

## Resolution

Recorded in `spec.md` Assumptions as an open item pending a planning-phase decision. FR-011 is worded to state the behavioral contract (CSM runs for requests meeting defined criteria) without asserting a specific, unsourced criterion.

**Update 2026-08-13**: reframed, not resolved. The trigger question is correctly deferred and remains a product/business-policy call — but it sits behind the implementation of Component 3 itself, which the original filing treated as done. The tier stays disabled by default; that default is now load-bearing for a second reason (avoiding false corroboration in the ensemble), not only because the trigger is undefined. The misleading module docstring was corrected the same day. Note that the "Always run CSM" option in the table above would be actively harmful in the component's current state, and should not be selected until Component 3 is genuinely implemented.
