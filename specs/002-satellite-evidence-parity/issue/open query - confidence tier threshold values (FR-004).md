# Open Query: what threshold values separate the HIGH / MEDIUM / LOW confidence tiers, and what are they computed over

**Spec/Plan/Tasks**: [../spec.md](../spec.md) FR-004/FR-005, [../research.md](../research.md) §4, [../tasks.md](../tasks.md) T016 — `src/evidence_intelligence/models/confidence_tier.py`
**Status**: **Provisional default adopted 2026-08-13 (Option B + C) — no longer blocking `T016`.** Reversible; recorded rather than assumed. See "Provisional default" below.

## Provisional default (2026-08-13)

A re-assessment on 2026-08-13 concluded this was over-classified as blocking. Option B needs no unsourced figure — that was the point of proposing it — so it can be adopted as a documented default now and revised when evidence justifies it, exactly as `001` handled FR-024's threshold (ship the mechanism, leave the number unset) and as this feature handled commercial tasking (decide a reversible default rather than block).

**Adopted**: the tier is assigned by a rule table over the per-request evidence-inputs manifest (`tasks.md` `T0-09`), not by a cut point on a float. Each rule states an observable fact about the inputs and the ceiling it imposes:

| Rule — observable input fact | Tier ceiling |
|---|---|
| No valid post-event pixels over the geometry | `LOW` |
| Post-event optical unavailable; SAR substituted | `MEDIUM` |
| No historical baseline available for the geometry | `MEDIUM` |
| Component 2 running on its untrained placeholder | `MEDIUM` |
| Phenology check flagged (no plausible standing crop pre-event) | `MEDIUM` |
| Package is `WEATHER_ONLY_PRELIMINARY` | `LOW` |
| No rule triggered | `HIGH` |

The tier is the lowest ceiling any triggered rule imposes. Every assignment therefore traces to a stated, checkable fact rather than to a threshold nobody can source — which is also what makes it defensible in a forum hearing, where "the field was not visible on any post-event pass" is an argument and "confidence was 0.63" is not.

**What remains open**: whether to add a numeric component once `T0-05` makes ensemble confidence vary and the Pilot phase supplies calibration data. Per Option C, any such value ships configurable and unset by default. The table above is a starting point, not a finding — the rules were chosen because each is individually defensible, not because their combination has been validated against outcomes.

**Consequences for the spec**: FR-004 currently reads as though the tier derives from confidence *figures*. Adopting this default means it derives from the evidence-inputs manifest, of which the confidence figures are one input. FR-004's wording should be reconciled at the next spec pass, and `T016` depends on `T0-09` rather than only on `T0-05`.

## The question

`research.md` §4 decides *three tiers* (High/Medium/Low) and says they are "computed as a deterministic function of the existing per-component and ensemble confidence figures." It does not say what that function is, and no cut points appear anywhere in `documents/`, `yestech_manual_2023.md`, or `documents/research/satellite-parity-global-precedent-research.md`.

Two questions, not one:

1. **What are the cut points?** "Ensemble combined confidence ≥ 0.8 is HIGH" is not derivable from anything sourced — picking a number here would be exactly the invented figure `CLAUDE.md`'s working conventions prohibit, and it would land in a §65B evidence package as if it meant something.
2. **What should the tier be computed *over*?** FR-004 ties it to model confidence only. That may be the wrong variable — see "What was checked" below.

## What was checked

**The sourced precedent doesn't carry thresholds.** Research §1.10 establishes *that* every credible precedent uses a small tier set with an explicit lowest-tier fallback (EU CAP Check-by-Monitoring's green/yellow/red is the clearest). It does not publish CbM's own cut points, and CbM's traffic-light decision rule is a function of parcel-level monitoring outcomes under a different regulatory scheme, not of an ensemble confidence score — so it justifies the *shape* of the output, not any number.

**The variable FR-004 names is currently a constant.** `models/ensemble.py` computes `combined_confidence = total_weight / len(contributions)`. With Component 2 shipping untrained (`ai_ml_weight` → `UNTRAINED_PLACEHOLDER_WEIGHT` = 0.15) and Component 1's `calibration_confidence` always resolving to 0.85 (it only range-checks fAPAR, which `pipeline.py` clips to [0,1] before passing), that expression evaluates to exactly **0.50 on every request** in the shipped configuration. Any threshold placed on it puts 100% of packages in one tier, which makes SC-003 vacuous and SC-005 unmeasurable, and `quickstart.md` Scenario 2 ("submit one expected-high and one expected-low request") cannot pass as written.

**Model confidence is not the same thing as evidence quality.** What a claims reviewer needs from a tier is whether the *evidence* is strong: was the field actually visible through cloud, was a historical baseline available, did SAR substitute for optical, how many of Component 2's 17 declared features were real rather than defaulted, how large is the field relative to the pixel, was causation actually computed. Two packages can carry the same ensemble confidence with completely different answers to those questions. Nothing in FR-004 lets the tier see any of it.

## Options

| Option | Description |
|---|---|
| A. Numeric cut points on ensemble confidence | Simplest reading of FR-004 as written. Requires inventing two numbers with no source, and — until the constant-confidence defect above is fixed — assigns every package to one tier. Not recommended on its own. |
| B. Rule table over an evidence-completeness record | Tier is assigned by a small set of individually justifiable rules ("no valid post-event pixels over the geometry ⇒ LOW"; "post-event optical unavailable and SAR substituted ⇒ at most MEDIUM"; "no historical baseline ⇒ at most MEDIUM"). Each rule is defensible in a forum hearing on its own terms; no unsourced numeric cut is required. Depends on a per-request evidence-inputs manifest existing. |
| C. Configurable, unset by default | Mirrors exactly how `001` handled the same problem for FR-024's causation low-confidence threshold: ship the mechanism, leave the value unset in config, label tiers only once a real value is supplied. Composable with A or B. |
| D. Defer entirely to Pilot & Validation | `documents/README.md` §8's Pilot phase is the only place a calibrated cut point could legitimately come from. Matches `spec.md`'s own Assumptions ("Empirical validation of confidence-tier thresholds ... is assumed to occur during the existing Pilot & Validation roadmap phase"). |

## Recommendation

Not resolved unilaterally here. Leaning B + C: express the tier as a rule table over an explicit evidence-completeness record rather than a cut on a single float, and keep any numeric component configurable-and-unset until the Pilot phase supplies a calibrated value (the FR-024 precedent). B has the property that matters most for this module's purpose — every tier assignment traces to a stated, checkable fact about the inputs, not to a threshold nobody can source.

Whichever option is chosen, the constant-`combined_confidence` defect must be fixed first, or the tier is decorative regardless of how it is defined.

## Resolution

Open. Surfaced during a full-scope re-evaluation of `002` on 2026-08-13, not during `/speckit-plan` — recorded here rather than left in chat history, the same reason `001`'s AI/ML training-label query was added to its tracker.
