# Open Queries — Evidence Generation Pipeline

Questions that genuinely have no answer in `documents/` or `YESTECH_Manual_2023.md`, surfaced during `/speckit-specify` and `/speckit-plan` rather than guessed at. Each is deferred, not blocking — see the referenced task/FR for how it's handled in the meantime.

| File | Surfaced during | Blocks |
|---|---|---|
| [`open query - CSM high-scrutiny trigger criteria (FR-011).md`](./open%20query%20-%20CSM%20high-scrutiny%20trigger%20criteria%20%28FR-011%29.md) | `/speckit-specify` | `spec.md` FR-011, `tasks.md` T038 — CSM assimilation tier is implemented but gated off by default until this is resolved |
| [`open query - causation confidence low-confidence threshold (FR-024).md`](./open%20query%20-%20causation%20confidence%20low-confidence%20threshold%20%28FR-024%29.md) | `/speckit-specify` | `spec.md` FR-024, `tasks.md` T039 — low-confidence labeling uses a configurable, currently-unset threshold |
| [`open query - expected request volume and concurrency target.md`](./open%20query%20-%20expected%20request%20volume%20and%20concurrency%20target.md) | `/speckit-plan` | `plan.md` Scale/Scope, `research.md` §4 — doesn't block Phase 0/1 design, matters at infra-sizing time |

None of these were invented — each file documents what was checked (usually `YESTECH_Manual_2023.md`) and why no sourced answer exists, per this repo's convention against unsourced figures (`CLAUDE.md` Working conventions).
