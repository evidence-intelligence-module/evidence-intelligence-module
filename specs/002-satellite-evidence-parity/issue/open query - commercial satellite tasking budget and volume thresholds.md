# Open Query: Commercial satellite tasking budget and volume thresholds

**Plan/Tasks**: [../plan.md](../plan.md) Scale/Scope, [../research.md](../research.md) §5
**Status**: **Resolved 2026-08-12 — Option A.** No longer blocking; recorded below for audit trail.

## The question

This roadmap's enhanced-tier sourcing (spec.md FR-002, FR-013) includes commercial, paid-per-scene or subscription satellite sources — tasked VHR optical (Planet SkySat, Maxar WorldView Legion, Airbus Pléiades Neo) and commercial SAR (ICEYE, Capella, Umbra) — alongside the free/open baseline. No source document states a budget ceiling, per-claim cost threshold, or expected request volume that would determine:

1. Whether commercial tasking is authorized at all in the near-term rollout, or deferred entirely to a later phase.
2. If authorized, which claim characteristics (claim value, confidence tier already reached with free sources, peril type, region) justify the cost of tasking a commercial source for a given request.
3. What volume of tasked requests per season/district is financially sustainable, which affects whether the Satellite Source Registry's commercial tier should be always-considered or opt-in per deployment.

## What was checked

`documents/research/satellite-parity-global-precedent-research.md` §2.1/§2.2 documents indicative per-scene/tasking costs for reference (e.g., WorldView Legion "~$1,200+/scene") but these are vendor list-price data points, not a budget decision for this project. No document in `documents/` or `specs/001-evidence-generation-pipeline/` addresses commercial data spend — `001`'s own equivalent open question (`specs/001-evidence-generation-pipeline/issue/open query - expected request volume and concurrency target.md`) covers infrastructure concurrency, not data-sourcing budget, and doesn't resolve this either.

## Options

| Option | Description |
|---|---|
| A. No commercial tasking in near-term rollout **(chosen)** | Enhanced tier limited to free/open sources only (Sentinel-1 SAR, ISRO Resourcesat-2A LISS-4/EOS-04 via Bhoonidhi, open foundation models). PlanetScope is also commercial/subscription-based, so it's deferred alongside the others, not treated as an exception. Simplest, zero incremental per-request cost, but caps how far monsoon/small-field capture-quality gains can go (research §2.1/§2.2 ceiling). |
| B. Budget-gated commercial tasking for a defined claim-value/confidence tier | Commercial VHR/SAR authorized only when a claim exceeds a value threshold and/or the free-source-only confidence tier resolves to `LOW` — closest to how CbM's yellow-tier escalation works, but requires the threshold values this query is asking for. |
| C. Defer the whole question to the Pilot & Validation roadmap phase | Run near-term rollout on free sources only; use pilot-phase real claim data (`documents/README.md` §8) to empirically justify a commercial-tasking budget before committing one. |

## Recommendation

Not resolved unilaterally here. Leaning toward A/C as the safer default for the near-term phase (`plan.md`/`research.md` §5 already assume this — the Satellite Source Registry and commercial tasking client are designed so a `false`/unauthorized default requires no code change later), with B as the natural target once a budget figure exists. Per Constitution §8-equivalent governance (canonical `documents/Constitution.md` §8), this needs an explicit, recorded decision from whoever owns delivery-planning budget, not an inference from vendor list prices.

## Resolution

**Decided 2026-08-12: Option A — no commercial satellite tasking in the near-term rollout.** Enhanced-tier sourcing is limited to free/open sources: the existing GEE-hosted baseline (Sentinel-1/2, Landsat, MODIS, CHIRPS, ERA5-Land, IMD, SMAP, SRTM, INSAT-3D) plus ISRO's free sovereign sources (Resourcesat-2A LISS-4, EOS-04/RISAT-1A). `commercial_tasking_client.py` (`tasks.md` T009) is retained in the design as an isolated, disabled-by-default module (`COMMERCIAL_TASKING_ENABLED=false`) rather than removed, so a future budget decision requires only a config/authorization change, not new architecture — but it moves out of the MVP critical path (see `tasks.md` update). Revisit via Option B or C once real budget or Pilot & Validation data exists.

**Access-path clarification, prompted by the decision discussion**: GEE is the primary access layer, but it does **not** host ISRO's own sovereign satellite data — confirmed by checking Google's Earth Engine Data Catalog directly, which lists NASA/USGS/ESA-primary public datasets (Landsat, MODIS, Sentinel, etc.) with no ISRO/Resourcesat/EOS-series entries. Resourcesat-2A LISS-4 and EOS-04 therefore still require a **separate** Bhoonidhi/Bhuvan API integration (`research.md` §2 already noted this access path; this just makes explicit that it is not folded into the existing `gee_client.py`). This does not change the free-only decision — both channels are $0 — it only means the free enhanced tier needs two ingestion clients (GEE for the baseline it already covers, a new Bhoonidhi client for the ISRO sovereign sources), not one.
