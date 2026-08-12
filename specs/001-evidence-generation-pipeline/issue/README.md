# Open Queries — Evidence Generation Pipeline

Questions that genuinely have no answer in `documents/` or `YESTECH_Manual_2023.md`, surfaced during `/speckit-specify`, `/speckit-plan`, and post-implementation review rather than guessed at.

**Status vocabulary** (same in `specs/002-satellite-evidence-parity/issue/`):

- **Open** — no answer yet. Blocks whatever the last column names.
- **Narrowed** — part of the question turned out to have an unambiguous right answer and was fixed; the part needing a decision is still live.
- **Reframed** — the question was valid but asked in the wrong order; the file records what actually blocks first.
- **Provisional default** — a default was adopted so work could proceed, chosen because it required no unsourced figure. Reversible; the residual question is named in the file.
- **Resolved** — decided and recorded. Kept in this directory for the audit trail, not because it's still live.

All four below are Open, and each is *deferred* — the shipped code states its behavioural contract without asserting the unsourced figure, so none blocks `001` today. A cross-tracker re-assessment on 2026-08-13 changed how three of them are framed, without resolving any. Filenames start `open query - ` as a naming convention, not a status; several are linked by path from `spec.md`, `data-model.md`, `research.md`, and `tasks.md`, so they aren't renamed when their status changes.

| Status | File | Surfaced during | Blocks / what it gates |
|---|---|---|---|
| **Open — root** | [`open query - AI-ML training data source and CCE-label question.md`](./open%20query%20-%20AI-ML%20training%20data%20source%20and%20CCE-label%20question.md) | post-implementation review | `tasks.md` T017. **Re-assessed 2026-08-13 as the root of both trackers**: it gates `002`'s User Story 3, SC-001/SC-002 and its mirror query, the second half of `002`'s SAR query, this tracker's causation threshold, and any later numeric calibration of `002`'s confidence tiers. Every numeric-threshold question in this repo terminates here. If one decision gets made, make this one |
| **Open — reframed** 2026-08-13 | [`open query - CSM high-scrutiny trigger criteria (FR-011).md`](./open%20query%20-%20CSM%20high-scrutiny%20trigger%20criteria%20%28FR-011%29.md) | `/speckit-specify` | `spec.md` FR-011, `tasks.md` T038. The trigger question is real but is **not** what blocks Component 3 — `csm_assimilation.run()` is a placeholder that echoes its input, so enabling the tier would manufacture corroboration in the ensemble. Implement the component first; the trigger is downstream. Keep the tier disabled |
| **Open — narrowed** 2026-08-13 | [`open query - causation confidence low-confidence threshold (FR-024).md`](./open%20query%20-%20causation%20confidence%20low-confidence%20threshold%20%28FR-024%29.md) | `/speckit-specify` | `spec.md` FR-024, `tasks.md` T039. Cannot be calibrated by data availability alone: 55 of the score's 100 points are hardcoded at the call site, so the distribution is degenerate. Needs `002`'s `T0-06` first, then labels. `002`'s rule-table default for confidence tiers is a candidate template here |
| **Open — narrowed** 2026-08-13 | [`open query - expected request volume and concurrency target.md`](./open%20query%20-%20expected%20request%20volume%20and%20concurrency%20target.md) | `/speckit-plan` | `plan.md` Scale/Scope, `research.md` §4. Narrowed to **capacity sizing only** — the durability/architecture half (`002` `T05-06`) is justified on correctness alone and should not wait on a volume figure |

None of these were invented — each file documents what was checked (usually `YESTECH_Manual_2023.md`) and why no sourced answer exists, per this repo's convention against unsourced figures (`CLAUDE.md` Working conventions).
