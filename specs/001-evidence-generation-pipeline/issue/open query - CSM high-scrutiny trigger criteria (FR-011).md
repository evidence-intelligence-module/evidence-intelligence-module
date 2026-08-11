# Open Query: CSM high-scrutiny trigger criteria (FR-011)

**Spec**: [../spec.md](../spec.md) — FR-011
**Status**: Deferred to planning — not a spec-blocking [NEEDS CLARIFICATION] marker

## The question

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
