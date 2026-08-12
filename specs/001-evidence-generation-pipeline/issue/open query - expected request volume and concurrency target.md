# Open Query: expected request volume / concurrency target

**Plan**: [../plan.md](../plan.md) — Technical Context, Scale/Scope
**Status**: Deferred to task-sizing / infra planning — not a plan-blocking gate failure

## The question

No document in this repo (`README.md`, `constitution.md`, `hld.md`, `modeling-approach.md`, `evidence-flow-spec.md`) states an expected number of evidence requests per day/season, a target number of concurrent in-flight requests, or a claims-volume figure to size against. `hld.md` §8's Non-Functional Requirements cover latency and availability qualitatively but not volume.

## Why it matters

Phase 1 design (data model, API contract) is scale-agnostic and doesn't need this number. It will matter once `/speckit-tasks` or implementation starts making concrete infrastructure decisions — compute sizing, GEE quota planning (GEE has request-rate limits even on free/government tiers), database connection pooling, object storage throughput.

## Recommendation

Don't invent a figure — India's PMFBY processes claims at national scale, so any guessed number would be either meaningless or misleadingly precise. This should come from whoever owns rollout planning (which districts, what phase, per the Roadmap Pointer in `README.md` §8: Foundation → Advanced analysis → Packaging & delivery → Pilot & validation) — a pilot-phase volume estimate is very different from a national-rollout one, and the Roadmap already implies this is meant to be answered in phases, not upfront.

## Narrowed 2026-08-13 — the architecture decision no longer waits on this

A cross-tracker evaluation on 2026-08-13 separated two things this query had bundled: *what shape* the load takes, and *how much* of it there is. The second still needs a number. The first no longer does.

**Load shape, now known well enough to design against.** `002`'s `spec.md` gained an edge case describing the correlated-catastrophe pattern: a real regional event produces many requests over one district simultaneously, and the same cloud cover or source outage degrades all of them at once. So the load is bursty and spatially correlated with a shared failure mode — not the uniform arrival rate an average-requests-per-day figure would imply. That is a design input, and it points the same way regardless of the eventual number.

**What follows without a number.** `002` `tasks.md` `T05-06` (durable job runner with queue, retry, and restart survival) is justified on correctness alone: evidence generation currently runs in a FastAPI `BackgroundTasks` in-process, so a restart loses the request, and `retry_insufficient_data` exists but is scheduled by nothing. `002` then adds four external dependencies to that path. None of that reasoning needs a volume target.

**What still needs one**: instance counts, queue-depth alarms, GEE quota planning, and load-test targets. Genuinely capacity questions, genuinely unanswerable without the figure.

## Resolution

Recorded in `research.md` as an explicit open item. Phase 1 artifacts (data-model.md, contracts/) are written to not depend on a specific scale figure. Revisit before any task that involves capacity planning, load testing targets, or infrastructure sizing.

**Update 2026-08-13**: narrowed to *capacity sizing only*. The durability/architecture half is decided on other grounds (`T05-06`) and should not wait on this.
