# Open Query: where per-crop Harvest Index values come from, and whether the request contract needs a crop type to look one up

**Spec/Code**: `modeling-approach.md` §2 (Component 1), [../contracts/evidence-request-api.md](../contracts/evidence-request-api.md) — `src/evidence_intelligence/pipeline.py` (`harvest_index=0.4`), `models/semi_physical.py::CropParameters`
**Status**: **Open — the shipped code contradicts a documented commitment.** Not blocking today, but every yield-loss estimate the module has ever produced is affected.

## The question

`modeling-approach.md` §2 makes an explicit, deliberate commitment about this constant:

> YES-TECH derives Harvest Index from historical **CCE** biomass/grain-yield data (Table 7, row 6). This module does not use CCE data (Constitution §4) — Harvest Index is instead sourced from published crop-variety reference values and regional agronomic literature, **clearly labeled as a modeling assumption** rather than a locally-measured constant.

The code does neither half of that. `pipeline.py` passes a flat `harvest_index=0.4` to Component 2 for every request, and `CropParameters.harvest_index` defaults to the same `0.4` for Component 1. Wheat, paddy, cotton, pulses and everything else get one number, and no package labels it as an assumption.

Yield loss is reported as `damage_fraction × harvest_index`, so this constant scales the module's headline figure on every claim.

## What was checked

**There is nothing to look a per-crop value up *from*.** The Evidence Request Interface takes a geometry, an event date, a peril type, and an optional external reference ID (`contracts/evidence-request-api.md`, Constitution §5). **Crop type is not a field.** So the flat default is not merely an unfinished lookup — the contract carries no input that would let a lookup happen. Resolving this properly means deciding whether the request contract grows a crop-type field, or whether the crop is derived some other way.

**`CropParameters` is honest about being a placeholder; the call site is not.** `semi_physical.py`'s docstring says "Placeholder defaults — a real deployment populates this from an agronomic reference table per crop/region", which is a fair disclosure. But `pipeline.py`'s `harvest_index=0.4` literal carries no such marker, and neither reaches the evidence package. §2's promise of "clearly labeled as a modeling assumption" is unmet in the artifact where it matters.

**`002` already needs a crop type for a different reason.** User Story 4's crop-type cross-check compares a *declared* crop against an observed one, and `data-model.md`'s `crop_calendar_cross_checks.declared_crop_type` is nullable "from the claim, if provided at request time" — implying a field that the `001` contract does not currently define. Whatever is decided here should be decided together with that, or the two features will grow separate crop-type inputs.

**Constitution §4 constrains the answer.** The obvious source for Indian per-crop Harvest Index — historical CCE biomass/grain ratios — is the one §2 explicitly rules out and routes around. So this query is adjacent to, but narrower than, the [AI/ML label question](./open%20query%20-%20AI-ML%20training%20data%20source%20and%20CCE-label%20question.md): published agronomic literature is a legitimate non-CCE source here in a way it is not for per-field damage labels.

## Options

| Option | Description |
|---|---|
| A. Disclose the flat default now | Surface the Harvest Index used, and the fact that it is a single un-crop-specific assumption, in every package's accuracy statement. Does not improve the estimate; makes it honest, and satisfies §2's "clearly labeled" half. Same-day change, no decision required. |
| B. Add crop type to the request contract | An optional crop-type field, used to select a published per-variety Harvest Index from a reference table. Directly serves `002`'s User Story 4 as well. Needs a Constitution §5 check — it is a generic agronomic input, not a caller-specific schema, so it appears compatible, but that should be confirmed rather than assumed. |
| C. Derive crop type from satellite data | Use the same open crop-type product `002`'s cross-check relies on (WorldCereal) to infer the crop, and select the Harvest Index from that. No contract change — but it inherits that product's accuracy limits, which `002`'s own crop cross-check query flags as unestablished for Indian smallholdings. |
| D. Report biomass damage only | Drop the yield conversion and report the damage fraction, leaving Harvest Index out of the module entirely. `constitution.md` §4 permits a yield-loss estimate but does not require one. |

## Recommendation

Not resolved unilaterally here.

**A immediately, regardless of what else is chosen** — the gap between §2's stated commitment and the shipped behaviour is a disclosure failure, and closing it needs no decision.

Then **B**, and decided jointly with `002`'s crop-type cross-check rather than separately, since both need the same input and neither currently has it. C is a fallback where no declared crop exists, but should not be the primary path while the reference product's per-parcel accuracy is unestablished. D is cleaner than it first appears and worth a moment's consideration — the module's framing is evidence rather than determination, and a yield-loss figure resting on a flat assumed constant may be claiming more than it can support.

## Resolution

Open. Surfaced 2026-08-13 during a sweep for hardcoded values.
