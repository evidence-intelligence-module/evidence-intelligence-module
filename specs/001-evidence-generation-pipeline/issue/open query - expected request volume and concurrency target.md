# Open Query: expected request volume / concurrency target

**Plan**: [../plan.md](../plan.md) — Technical Context, Scale/Scope
**Status**: Deferred to task-sizing / infra planning — not a plan-blocking gate failure

## The question

No document in this repo (`README.md`, `Constitution.md`, `HLD.md`, `Modeling-Approach.md`, `Evidence-Flow-Spec.md`) states an expected number of evidence requests per day/season, a target number of concurrent in-flight requests, or a claims-volume figure to size against. `HLD.md` §8's Non-Functional Requirements cover latency and availability qualitatively but not volume.

## Why it matters

Phase 1 design (data model, API contract) is scale-agnostic and doesn't need this number. It will matter once `/speckit-tasks` or implementation starts making concrete infrastructure decisions — compute sizing, GEE quota planning (GEE has request-rate limits even on free/government tiers), database connection pooling, object storage throughput.

## Recommendation

Don't invent a figure — India's PMFBY processes claims at national scale, so any guessed number would be either meaningless or misleadingly precise. This should come from whoever owns rollout planning (which districts, what phase, per the Roadmap Pointer in `README.md` §8: Foundation → Advanced analysis → Packaging & delivery → Pilot & validation) — a pilot-phase volume estimate is very different from a national-rollout one, and the Roadmap already implies this is meant to be answered in phases, not upfront.

## Resolution

Recorded in `research.md` as an explicit open item. Phase 1 artifacts (data-model.md, contracts/) are written to not depend on a specific scale figure. Revisit before any task that involves capacity planning, load testing targets, or infrastructure sizing.
