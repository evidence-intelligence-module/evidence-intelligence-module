# Open Query: does attaching supplementary evidence re-evaluate a package, and how are superseded evidence packages versioned

**Spec/Plan/Tasks**: [../spec.md](../spec.md) User Story 2, FR-006, [../contracts/evidence-request-api-extensions.md](../contracts/evidence-request-api-extensions.md), [../tasks.md](../tasks.md) T018 — `src/evidence_intelligence/api/routes.py`
**Status**: **Split 2026-08-13.** This file bundled a decision with a defect:

- **Package lineage (Option D) — a defect, moved out.** `retry_insufficient_data` already produces a second `EvidencePackage` today, in shipped `001` code, with no `supersedes`, no version and no status recording the relationship — under a ten-year retention floor and §65B chain-of-custody requirements. There is no judgement call in "an evidence artifact that replaces another should say so." Moved to `tasks.md` `T0-16` and `data-model.md`; it applies whether or not any option below is chosen.
- **Whether attaching evidence re-evaluates anything (Options A/B/C) — the genuine decision, still open.** Unchanged below.

Does not block `T018`'s endpoint, but the guidance text `T017` writes into low-tier packages promises something no specified capability delivers — which is what Option A would fix in a sentence.

## The question

User Story 2 says a low-tier package "clearly states what additional evidence would help resolve the case further", and FR-006 adds an endpoint for attaching that evidence. `contracts/evidence-request-api-extensions.md` then states the endpoint "does not trigger re-processing on its own; if a deployment wants attaching evidence to trigger re-evaluation, that is a separate, not-yet-specified capability".

So as specified, the reviewer reads "supplementary evidence may improve confidence", attaches a photo, and nothing changes. Two questions:

1. **Should attaching evidence re-evaluate the package?** If not, what should the low-tier guidance text actually say?
2. **If a package is ever regenerated, what is the relationship between the old and new one?**

## What was checked

**The loop is genuinely open, not merely unimplemented.** `data-model.md` gives `supplementary_evidence_attachments` no path into any model, index, or confidence figure. No component in `modeling-approach.md` accepts a photo as an input, and no FR asks one to. So even a deployment that wanted re-evaluation would have nothing to re-evaluate *with* — the attachment is stored, surfaced, and otherwise inert. This is a defensible design (a human reviewer reads the photo themselves), but then the guidance text should say that, not imply the module will act on it.

**Package supersession is already ambiguous in `001`, before `002` adds to it.** `pipeline.py`'s `retry_insufficient_data` re-runs the full pipeline and calls `store.add_package` again, producing a second `EvidencePackage` row for the same request. `store/evidence_store.py` deliberately "never overwrites a component/package row in place", and `api/routes.py` returns `store.latest_package(...)`, describing the earlier one as "superseded". But `schema.py`'s `EvidencePackage` has no `supersedes`, no sequence number, and no status — "superseded" exists in prose and in an ordering, not in the data.

**This matters more for `002` than for `001`.** Every package carries a checksum, mandatory §65B fields, and a 10-year retention expiry (Constitution §7). Once `002` attaches a `confidence_tier` to it, a regenerated package can differ from its predecessor on the single field a reviewer is most likely to have relied on — a claim could be actioned on a `LOW`-tier package that later becomes `HIGH`, or the reverse. An evidence artifact that can silently change its headline conclusion, with no explicit lineage between versions, is weak exactly where §65B admissibility is strongest: chain of custody.

**Nothing schedules the retry.** `retry_insufficient_data` exists and is tested, but no scheduler, queue, or cron calls it anywhere in `src/`. So today the supersession path is reachable only if something external drives it.

## Options

| Option | Description |
|---|---|
| A. No re-evaluation; fix the guidance text | State plainly that supplementary evidence is stored and surfaced for the reviewer's own judgement and does not change the module's figures. Cheapest and most honest given nothing consumes an attachment today. |
| B. Attachment triggers re-run of the unchanged pipeline | Re-runs source acquisition (which may now find a clear optical pass), producing a genuinely updated package. The attachment itself still doesn't enter any model — the improvement comes from time having passed, which is worth being explicit about rather than letting the reviewer credit their photo. |
| C. Attachment becomes a modeled input | A geotagged photo as an actual evidence component with its own confidence contribution. Largest change by far; needs its own modeling section in `modeling-approach.md` and is arguably a different feature. |
| D. Explicit package lineage, independent of the above | Add `supersedes` / `version` / `status` to `EvidencePackage` so every regeneration states which artifact it replaces and why. Needed under B and C, and worth having under A too, because `retry_insufficient_data` already regenerates packages. |

## Recommendation

Not resolved unilaterally here.

Leaning A + D for this rollout: say what actually happens rather than implying an action the module cannot take, and give packages explicit lineage regardless, since `001` can already produce two packages for one request today with nothing recording the relationship between them. D is small, is required by any of B or C later, and closes a real §65B chain-of-custody gap that exists right now.

B is the natural next step once a durable job runner exists (nothing schedules retries today). C should not be folded into `002` — it is a new evidence component, not an extension of the confidence-tier story.

## Resolution

Open. Surfaced during a full-scope re-evaluation of `002` on 2026-08-13.
