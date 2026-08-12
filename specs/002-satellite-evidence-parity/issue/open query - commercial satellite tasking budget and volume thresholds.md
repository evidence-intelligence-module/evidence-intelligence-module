# Open Query: Commercial satellite tasking budget and volume thresholds

**Plan/Tasks**: [../plan.md](../plan.md) Scale/Scope, [../research.md](../research.md) §5
**Status**: Deferred — not blocking Phase 0/1 design or `/speckit-tasks`; matters once implementation reaches the commercial-tasking client (`ingestion/commercial_tasking_client.py`)

## The question

This roadmap's enhanced-tier sourcing (spec.md FR-002, FR-013) includes commercial, paid-per-scene or subscription satellite sources — tasked VHR optical (Planet SkySat, Maxar WorldView Legion, Airbus Pléiades Neo) and commercial SAR (ICEYE, Capella, Umbra) — alongside the free/open baseline. No source document states a budget ceiling, per-claim cost threshold, or expected request volume that would determine:

1. Whether commercial tasking is authorized at all in the near-term rollout, or deferred entirely to a later phase.
2. If authorized, which claim characteristics (claim value, confidence tier already reached with free sources, peril type, region) justify the cost of tasking a commercial source for a given request.
3. What volume of tasked requests per season/district is financially sustainable, which affects whether the Satellite Source Registry's commercial tier should be always-considered or opt-in per deployment.

## What was checked

`documents/research/Satellite-Parity-Global-Precedent-Research.md` §2.1/§2.2 documents indicative per-scene/tasking costs for reference (e.g., WorldView Legion "~$1,200+/scene") but these are vendor list-price data points, not a budget decision for this project. No document in `documents/` or `specs/001-evidence-generation-pipeline/` addresses commercial data spend — `001`'s own equivalent open question (`specs/001-evidence-generation-pipeline/issue/open query - expected request volume and concurrency target.md`) covers infrastructure concurrency, not data-sourcing budget, and doesn't resolve this either.

## Options

| Option | Description |
|---|---|
| A. No commercial tasking in near-term rollout | Enhanced tier limited to free/open sources only (Sentinel-1 SAR, PlanetScope subscription if budget allows, ISRO Resourcesat/EOS-04, open foundation models). Simplest, zero incremental per-request cost, but caps how far monsoon/small-field capture-quality gains can go (research §2.1/§2.2 ceiling). |
| B. Budget-gated commercial tasking for a defined claim-value/confidence tier | Commercial VHR/SAR authorized only when a claim exceeds a value threshold and/or the free-source-only confidence tier resolves to `LOW` — closest to how CbM's yellow-tier escalation works, but requires the threshold values this query is asking for. |
| C. Defer the whole question to the Pilot & Validation roadmap phase | Run near-term rollout on free sources only; use pilot-phase real claim data (`documents/README.md` §8) to empirically justify a commercial-tasking budget before committing one. |

## Recommendation

Not resolved unilaterally here. Leaning toward A/C as the safer default for the near-term phase (`plan.md`/`research.md` §5 already assume this — the Satellite Source Registry and commercial tasking client are designed so a `false`/unauthorized default requires no code change later), with B as the natural target once a budget figure exists. Per Constitution §8-equivalent governance (canonical `documents/Constitution.md` §8), this needs an explicit, recorded decision from whoever owns delivery-planning budget, not an inference from vendor list prices.

## Resolution

Open. Recorded here rather than assumed either way, mirroring how `specs/001-evidence-generation-pipeline/issue/` tracks its own deferred, consequential questions rather than letting them sit only in chat history.
