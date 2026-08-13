# Open Query: the RUE semi-physical model is applied to part of a season, which its source manual says it cannot be

**Spec/Plan/Tasks**: [`documents/modeling-approach.md`](../../../documents/modeling-approach.md) §2, [`documents/standards/yestech_manual_2023.md`](../../../documents/standards/yestech_manual_2023.md) §4.1.1.2 and Appendix 1, [`../tasks.md`](../tasks.md) `T05-08`/`T05-09` — `src/evidence_intelligence/models/semi_physical.py`, `pipeline.py`
**Status**: **Open.** Surfaced 2026-08-13 while researching the Phase 0.4 findings. Unlike the other entries in this tracker, the resolution is a **`documents/` change** — it is a claim this repo makes about its own method, not a missing figure.

Blocks: any statement that Component 1 implements "the same physical chain" as YES-TECH's RUE model. Does **not** block Phase 0.4, `T0R-03`…`T0R-08`, or any Phase 1–8 story.

## The question

`modeling-approach.md` §2 says this module "uses the **same physical chain**" as the YES-TECH RUE model, applied to a pre-event versus post-event comparison.

`yestech_manual_2023.md` §4.1.1.2 says:

> "**The model cannot be applied for part of the season because constant RUE is applicable only when the entire crop-growing season is considered.** Moderate resolution (10-30m) NDVI and LSWI datasets **throughout the crop season** are to be used."

A pre/post event window is part of a season. So either the claim in §2 needs reframing, or Component 1 needs rebuilding as a seasonal integration. The two documents currently disagree, and §2 is the one making the stronger claim.

This is not a defect with an unambiguous right answer, which is why it is here rather than in `tasks.md`: both resolutions are legitimate, and choosing between them is a scope decision about how much modelling rigor this module commits to.

## What was checked

**The manual's constraint is explicit and unqualified.** §4.1.1.2 gives the reason (constant RUE is a whole-season approximation), not merely a preference. Appendix 1 reinforces it: biomass is `RUE_max × Σ (from Sowing to Harvest) of (PAR × fAPAR × WS × TS)`, and "Tstress is estimated **at each time step**".

**The implementation is a single-point evaluation, twice.** `semi_physical.run` computes `_biomass(...)` once for pre-event inputs and once for post-event inputs. There is no summation and no time step. `modeling-approach.md` §2's own formula carries the `Σ`, so the code diverges from this repo's spec as well as from the manual.

**Four of §2's five terms are not implemented as specified** (verified 2026-08-13):

| §2 specifies | Implemented |
|---|---|
| `Σ` from sowing to the analysis date | Single-point evaluation, twice |
| `PAR = Daily Surface Insolation × 0.48` | Constant `18.0` MJ; the `0.48` factor is absent entirely |
| `LSWI = (NIR − SWIR) / (NIR + SWIR)` | NDVI substituted — SWIR is never requested from GEE |
| fAPAR from MODIS / Sentinel-3 OLCI | Linear approximation from NDVI (already disclosed, `FR-019`) |
| Daily Tmin/Tmax | One value, passed identically as both pre- and post-event |

**Consequence: every non-NDVI term cancels.** Because insolation is a constant and the same temperature is passed to both sides, both terms divide out of `(expected − observed) / expected`. Verified directly:

```
temp= 25.0  damage=0.8011248594        insolation=18.0  damage=0.8011248594
temp= 12.0  damage=0.8011248594        insolation= 5.0  damage=0.8011248594
temp= 38.0  damage=0.8011248594        insolation=40.0  damage=0.8011248594
temp=  5.0  damage=0.0   <- below temp_min: both sides zero, guard returns 0.0
```

So Component 1 reduces to a closed-form function of pre/post NDVI:
`damage = 1 − (fAPAR_post · WS_post) / (fAPAR_pre · WS_pre)`, where both `fAPAR` and `LSWI` are themselves derived from NDVI.

**Why that matters beyond tidiness.** `ensemble.semi_physical_weight` returns `calibration_confidence`, which is **0.85** when inputs are in range, against untrained Component 2's **0.15**. So roughly 85% of the ensemble's weight rests on a deterministic NDVI transform, and `ensemble.combine`'s confidence-weighted average reads its agreement with Component 2 (also NDVI-fed) as corroboration. This is the hazard [`models/csm_assimilation.py`](../../../src/evidence_intelligence/models/csm_assimilation.py)'s docstring already warns about for Component 3 — "adding a component that restates another's input manufactures corroboration in a figure that ends up in a legal evidence package" — occurring between Components 1 and 2, in shipped code, at 0.85 weight.

**The temperature stress function also diverges from the manual.** Appendix 1 gives
`Tstress = (T−Tmin)(T−Tmax) / [(T−Tmin)(T−Tmax) − (T−Topt)²]`; `_temperature_stress_scalar` uses a piecewise-linear ramp. §2's wording ("a bounded function of observed temperature relative to the crop's minimum, optimum, and maximum thresholds") is loose enough that the code does not contradict §2 — but it does diverge from the manual, and `CLAUDE.md` commits this module to matching or exceeding the manual's rigor. Note this is **not** the cause of the cancellation: with the same temperature on both sides, any functional form cancels.

**Nothing in `documents/research/` addresses this.** The white paper and the parity precedent research discuss sourcing and resolution, not RUE applicability windows.

## Options

| Option | Description |
|---|---|
| **A. Reframe §2 honestly** | Keep the two-point comparison; drop the "same physical chain" claim; state that constant-RUE seasonal integration is deliberately not attempted, why (no sowing-date input, no insolation feed), and that Component 1 is therefore an NDVI-derived biomass-ratio heuristic rather than the manual's RUE model. Cheapest, and squarely inside this repo's existing disclose-don't-invent posture. Does not make the ensemble-weight problem go away — pair with a weight cap. |
| **B. Rebuild as a seasonal integration** | Matches the manual. Needs the per-field index time series `T05-05` already produces, plus a real insolation feed and a sowing-date input. The largest option, and the only one that makes §2's claim true as written. |
| **C. Retire Component 1** | If it is a deterministic NDVI transform, it may be contributing manufactured corroboration rather than independent evidence. Most honest reading of the finding; leaves the ensemble as Component 2 alone, which is currently untrained — so this trades a misleading figure for a much weaker one. |
| **D. Close the input gaps first, then re-assess** | Land `T05-08` (real LSWI from SWIR) and `T05-09` (distinct pre/post temperature). Both are cheap and unambiguously correct regardless of how this query resolves, and they make Component 1 stop being purely NDVI-driven. Then decide between A and B with a component that actually has independent inputs. |

## Recommendation

**D, then A.** `T05-08` and `T05-09` are correct work under every option — LSWI and per-window temperature are named in §2, computable from data already ingested, and needed by B as much as by A. Landing them first removes the degeneracy that makes this query urgent, and converts the remaining decision from "is Component 1 evidence at all?" into the narrower "does §2 overclaim?".

Then **A** rather than B, unless the seasonal integration is wanted for its own sake: B's prerequisites (sowing date per field, an insolation feed) are larger than the accuracy they would buy for a *damage-detection* comparison, which is a different problem from the *absolute yield estimation* the manual's constraint is written about. Worth stating explicitly in §2 if A is chosen: the manual's prohibition concerns absolute-yield estimation with a constant RUE, and a ratio between two evaluations is not obviously subject to the same constraint — but that argument has to be **made in the document**, not left implicit in code, because right now §2 claims the method rather than arguing the adaptation.

**Not recommended: C**, at least not before D. Retiring a component because its inputs were never wired is the wrong order of operations.

## Interim, regardless of resolution

Component 1's `calibration_confidence` of **0.85** is not defensible while it is a pure NDVI transform, because that figure is what tells the ensemble how much independent corroboration the component provides. Capping it, or disclosing the degeneracy in the package's accuracy statement, is correct under every option above and needs no decision from this query.
