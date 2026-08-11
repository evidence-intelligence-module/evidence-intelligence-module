# Open Query: causation-confidence "low-confidence" numeric threshold (FR-024)

**Spec**: [../spec.md](../spec.md) — FR-024
**Status**: Deferred to planning — not a spec-blocking [NEEDS CLARIFICATION] marker

## The question

`Evidence-Flow-Spec.md` §8 states that when "causation confidence [is] below a low-confidence threshold," the package is still delivered but clearly labeled with the low score. The causation confidence score itself is 0–100 (§5, weighted combination of temporal/spatial/magnitude/physiological alignment), but no document states what numeric value counts as "low."

## What was checked

Searched `YESTECH_Manual_2023.md` for a transferable numeric precedent. It mandates *disclosing* model accuracy metrics (RMSE, NRMSE, MAPE, correlation coefficient — §4.1.4.2, §5.2.2.4) but never sets a numeric pass/fail threshold for any of them. YES-TECH has no concept equivalent to a "causation confidence score" — that scoring mechanism is this module's own invention (Evidence-Flow-Spec.md §5), and even that document deliberately left the threshold unstated. There is no sourced number to pull from.

## Options considered (presented to user 2026-08-12)

| Option | Description |
|---|---|
| 50 | Midpoint of the 0–100 scale — common default for a scored metric |
| 70 | Stricter bar — only fairly strong alignment across all four factors counts as non-low-confidence |
| Defer to planning | Leave open; calibrate against real claims data rather than guess now |

User response: asked to explore what YES-TECH suggests more broadly rather than picking a number directly.

## Recommendation

No citable precedent exists in YES-TECH or this module's own prior documentation for this figure — inventing one now would violate this repo's convention against un-sourced figures (`CLAUDE.md` working conventions: "don't invent figures or citations"). The number is inherently something that needs empirical calibration against real claim outcomes (does a score of 50 actually correlate with claims that turn out contested/wrong more often than a score of 70?), which isn't available at spec time. Recommend deferring to `/speckit-plan` / a calibration pass once real or representative claims data exists.

## Resolution

Recorded in `spec.md` Assumptions as an open item pending empirical calibration. FR-024 is worded to state the behavioral contract (package still delivered, clearly labeled) without asserting a specific, unsourced number.
