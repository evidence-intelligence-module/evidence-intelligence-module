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

## Blocked on a code fix, not only on data (added 2026-08-13)

The Recommendation above defers to "empirical calibration against real claim outcomes." A cross-tracker evaluation on 2026-08-13 found a nearer obstacle that the original filing did not have visibility on: **the score being thresholded barely varies today.**

`pipeline.py` calls `causation_scoring.score` with `days_between_event_and_ndvi_drop=1` and `distance_km_to_weather_anomaly=0.0` hardcoded at the call site. Those feed the temporal and spatial terms, worth 30% and 25% respectively, so both return their maximum on every request — 55 of the 100 available points are a constant. The remaining 45 come from magnitude correlation and physiological plausibility, and the latter is itself near-binary (90 or 40, on the phenology flag).

Calibrating a threshold against that distribution would measure the hardcoding, not the evidence. So the sequence is:

1. **`002` `tasks.md` T0-06** — compute the temporal and spatial terms from observed data (break-point date of the index time series; actual distance from the geometry to the weather anomaly).
2. **Then** the label/ground-truth question ([`AI-ML training data source`](./open%20query%20-%20AI-ML%20training%20data%20source%20and%20CCE-label%20question.md)), which supplies the outcomes to calibrate against.
3. **Then** this threshold.

This does not change the recommendation — deferring was and remains right. It records why the deferral cannot be lifted by data availability alone.

## Related

The `002` [`confidence tier threshold values (FR-004)`](../../002-satellite-evidence-parity/issue/open%20query%20-%20confidence%20tier%20threshold%20values%20%28FR-004%29.md) query is the same question in a different place: an unsourceable numeric cut on a confidence-shaped score. That one adopted a provisional rule-table default on 2026-08-13 — expressing the decision as individually-defensible rules over observable input facts rather than as a cut point. If that framing holds up in practice, it is the natural template here too, and would let FR-024 ship a defensible behaviour without waiting on steps 1–3 above.

## Resolution

Recorded in `spec.md` Assumptions as an open item pending empirical calibration. FR-024 is worded to state the behavioral contract (package still delivered, clearly labeled) without asserting a specific, unsourced number.
