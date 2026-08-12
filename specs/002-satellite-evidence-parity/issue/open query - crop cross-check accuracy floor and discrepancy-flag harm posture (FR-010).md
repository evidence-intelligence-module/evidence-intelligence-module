# Open Query: what accuracy floor justifies raising a crop-type discrepancy flag against an individual claim, and how must that flag be framed

**Spec/Plan/Tasks**: [../spec.md](../spec.md) User Story 4, FR-010, [../data-model.md](../data-model.md) `crop_calendar_cross_checks`, [../tasks.md](../tasks.md) T027–T029 — `src/evidence_intelligence/ingestion/crop_calendar_crosscheck.py`
**Status**: Open — should block T028/T029. This is the only capability in `002` whose failure mode harms an identifiable individual rather than degrading an estimate.

## The question

FR-010 requires the module to "flag — not silently resolve — any material mismatch against the claim's declared crop or date", comparing against WorldCereal. `data-model.md` implements this as a boolean `discrepancy_flag`.

Three questions this leaves unanswered:

1. **What accuracy does the reference product need for that flag to be fair** at the level of one farmer's claim, rather than at the population level where crop-type maps are normally validated?
2. **What happens when the declared crop is outside the reference product's class set** — is that a discrepancy, or is it no answer at all?
3. **How must the flag be framed in the package**, given that a reader will reasonably interpret it as a fraud signal?

## What was checked

**No accuracy figure for this use is sourced anywhere.** `research.md` §3 and `documents/research/Satellite-Parity-Global-Precedent-Research.md` §4.3 establish WorldCereal as open, production-live, global, 10 m, and Presto-backed. Neither states a per-parcel accuracy for Indian smallholdings, and a global product's headline accuracy is a population statistic — it does not license a per-individual inference. This module's own research repeatedly flags mixed-pixel effects at India's median field size as a first-order problem for 10 m data; that same problem applies to a 10 m crop-type classification, and more severely, because classification errors are discrete rather than a blurred value.

**The data model has no "no answer" state.** `crop_calendar_cross_checks.observed_crop_type` is non-nullable and `discrepancy_flag` is a boolean. If the field's actual crop is not in the reference product's class set, there is no representable outcome other than reporting *some* observed crop and flagging a mismatch. That converts "the reference product does not cover this crop" into "the farmer's declaration disagrees with satellite evidence" — a false accusation produced by schema shape, not by evidence. WorldCereal's class set is cereal- and maize-centred and does not span the full range of crops insured under PMFBY, so this is the common case for a large share of Indian claims, not an edge case.

**The spec says the flag is corroboration only, but nothing enforces it.** `spec.md`'s Assumptions state the cross-check "is understood as a corroboration/discrepancy-flagging signal only — it does not feed a yield-blending formula". That constrains the *pipeline*. It does not constrain the *reader*: `contracts/evidence-request-api-extensions.md` surfaces `crop_calendar_cross_check.discrepancy_flag` as a bare boolean with no accuracy figure, no confidence, and no statement of what it does and does not mean. Every other satellite-derived figure in this module carries mandatory provenance and an accuracy statement under Constitution Principle I/II; this one does not, and it is the one most likely to be read as an accusation.

**Constitution §4 is adjacent but does not cover this.** The no-CCE boundary is respected — the comparison is against an open crop-type map, never CCE. What §4 does not address is the module producing an adverse individual finding about a claimant from a source whose accuracy at that granularity is unestablished.

## Options

| Option | Description |
|---|---|
| A. Three-state outcome | Replace the boolean with `CONSISTENT` / `INCONCLUSIVE` / `DISCREPANT`, where a declared crop outside the reference class set, or a field below a minimum pure-pixel count, resolves to `INCONCLUSIVE` and never to `DISCREPANT`. Removes the schema-induced false-accusation path. |
| B. Accuracy floor as a gate | Do not raise `DISCREPANT` unless the reference product publishes a per-class accuracy for the relevant crop and region above a stated floor; below it, report `INCONCLUSIVE`. Requires deciding the floor — itself unsourced today. |
| C. Mandatory framing in the package | Any discrepancy carries the reference dataset, version, its own accuracy figure for that crop/region, and an explicit statement that it is not a fraud determination and did not alter the damage estimate. Composable with A and B. |
| D. Drop User Story 4 | The cross-check is P4, corroborative only, and is the lowest-value/highest-harm item in the roadmap. Dropping it costs the roadmap little. |

## Recommendation

Not resolved unilaterally here — the harm posture is a decision for whoever owns the boundary, per Constitution §8.

Leaning A + C as a minimum bar if User Story 4 proceeds at all: a three-state outcome and mandatory framing are cheap and remove the two mechanisms by which this feature can produce a false adverse finding. B is the principled addition but needs a sourced floor that does not exist yet. D deserves genuine consideration: this is the only capability in the roadmap that can hurt a claimant if it is wrong, and it is also the one the roadmap values least.

Whatever is decided, `data-model.md`'s boolean should not be implemented as-is.

## Resolution

Open. Surfaced during a full-scope re-evaluation of `002` on 2026-08-13.
