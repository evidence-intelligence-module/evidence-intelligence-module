# Open Query: what damage fractions separate "negligible", "minor", "moderate" and "severe"

**Spec/Code**: [../spec.md](../spec.md) FR-014, `hld.md` §4 (`damage_classification` on the `ENSEMBLE` row) — `src/evidence_intelligence/pipeline.py::_classify`
**Status**: **Open — an unsourced figure currently reaching a §65B output.** Unlike this tracker's other threshold queries, this one is not deferred behind an absent mechanism: the numbers are live in shipped code today and appear in every evidence package.

## The question

`pipeline.py::_classify` maps the ensemble damage fraction to one of four labels:

```python
if damage_fraction < 0.1:   return "negligible"
if damage_fraction < 0.33:  return "minor"
if damage_fraction < 0.66:  return "moderate"
return "severe"
```

`0.1`, `0.33` and `0.66` decide which word a claims reviewer reads. Where do they come from?

## What was checked

**Nowhere in this repo.** A search across all of `documents/` returns zero occurrences of `0.33`, `0.66`, `33%` or `66%`. `hld.md` §4 lists `damage_classification` as a field on the `ENSEMBLE` row and `documents/readme.md` describes "pixel-level damage classification with a computed affected area", but no document defines the bands or the label set.

**`yestech_manual_2023.md` has no transferable precedent.** Searched for severity/category/grade banding: every hit is incidental ("moderate resolution imaging spectro-radiometer", "moderate spatial and temporal scales"). YES-TECH reports yield and health *figures* and mandates disclosing model accuracy; it does not define a four-band damage-severity vocabulary this module could adopt.

**So the thresholds were invented**, in exactly the sense `CLAUDE.md`'s working conventions prohibit — and this is the most exposed instance in the codebase, because the output is a categorical label in a legally-admissible package rather than a number a reader can weigh for themselves. A field at 0.34 damage is reported as "moderate" and one at 0.32 as "minor" on no stated basis, and the distinction is not recoverable from the package.

**This is not the FR-024 situation.** That threshold ships unset and simply doesn't label anything until a value is supplied. A classification band cannot be unset the same way — `damage_classification` is a populated field on every `ENSEMBLE` row, so *some* mapping has to exist. The mechanism can't be deferred; only its justification and its disclosure can be fixed.

## Options

| Option | Description |
|---|---|
| A. Configurable bands + explicit disclosure | Keep the current values as a labelled provisional default, move them to config, and state in every package that the banding is a presentational convention rather than a sourced standard. Cheapest honest fix; the numbers stay arbitrary but stop being presented as authoritative. |
| B. Source them from PMFBY/scheme practice | If the scheme, an insurer, or a state SOP already defines loss-severity bands for claims handling, adopt those — the labels would then mean something to the reviewer reading them. Requires someone with access to that practice; nothing in this repo supplies it. |
| C. Drop the categorical label entirely | Report the damage fraction and its confidence, and let the consumer band it. Removes the invented figure completely, at the cost of a field `hld.md` §4 currently specifies. |
| D. Calibrate against outcomes | Derive bands from settled-claim outcomes once `002`'s `TV-01` capture supplies them — which band actually predicts a contested or upheld claim. The only option that makes the numbers *mean* something, and the slowest. |

## Recommendation

Not resolved unilaterally here.

**A now, B or D later.** The current bands are load-bearing in shipped code and cannot simply be removed, so the immediate priority is that the package stop presenting an arbitrary mapping as though it were a standard — a reviewer who knows the banding is a presentational convention can discount it; one who doesn't cannot. That is a same-day change and needs no decision from anyone.

B is the right long-term answer if such bands exist in scheme practice, since a label only helps if it matches what the reader already uses. C deserves genuine consideration — the module's own framing is that it produces evidence rather than determinations, and a categorical severity label is closer to a determination than the underlying fraction is.

## Resolution

Open. Surfaced 2026-08-13 during a sweep for hardcoded values, after Phase 0's fixes had removed the fabricated *inputs* — this is the same failure class one layer further down the pipeline, in the outputs.
