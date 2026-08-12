# Phase 0 Research: Satellite Evidence Parity Roadmap

Resolves the technical choices flagged in `plan.md`'s Technical Context. Every decision below traces to a specific finding in [`documents/research/Satellite-Parity-Global-Precedent-Research.md`](../../documents/research/Satellite-Parity-Global-Precedent-Research.md) (§ references below) rather than to an invented figure, per `CLAUDE.md`'s no-invented-figures convention.

## 1. First foundation-model integration target

**Decision**: Presto (NASA Harvest).

**Rationale**: Purpose-built for exactly this module's existing input shape — per-pixel timeseries over Sentinel-1 SAR + Sentinel-2 optical + weather + DEM (research §4.1) — so integration is additive, not a re-architecture. MIT-licensed, weights openly downloadable, and already production-proven as the backbone of ESA's live WorldCereal system (research §4.3), which de-risks "research-only, never actually production-usable" failure mode flagged against several alternatives. Small enough for cheap per-field inference, consistent with the Performance Goals in `plan.md` (no GPU/specialized-compute requirement introduced).

**Alternatives considered**:
- *Clay Foundation Model* — rejected as the *first* target (not ruled out long-term): natively fuses SAR+optical+Landsat+NAIP in one embedding space, which is attractive, but at 632M parameters it's a heavier integration than Presto for a first additive step; a natural Phase-2 candidate once Presto integration is validated.
- *Prithvi-EO-2.0* — rejected as the first target: Apache-2.0 and production-ready, but optical-only (HLS), so it wouldn't cover the SAR side of the existing feature set without a second model; kept as the safest large-backbone fallback if Presto proves insufficient.
- *AlphaEarth Foundations* — rejected: only the *output embeddings* are open (CC-BY-4.0), not the model itself, making it a data dependency on Google infrastructure rather than an offline open-weight model (research §4.1) — inconsistent with this module's existing GEE-adjacent-but-source-agnostic posture.
- *SatMAE* — rejected: license not clearly asserted in the source repository as of this research pass (research §4.1) — do not depend on an unconfirmed-license model in a production evidence pipeline.

## 2. Cloud-penetrating / enhanced-resolution source priority

**Decision**: Sentinel-1 SAR (already in the `001` baseline) becomes the default fallback the moment optical is unusable for a request's analysis window; Planet PlanetScope (daily, ~3–4m, moderate commercial cost) is the default enhanced-tier optical source for small-field cases; commercial SAR (ICEYE first) and tasked VHR (SkySat/Maxar/Pléiades Neo) are budget-gated, request-level options, not always-on.

**Rationale**: Research §3 documents 90–92% July–August cloud cover in monsoon-affected regions — exactly the window most claimed hailstorm/flood/cloudburst events fall in — making SAR-first fallback load-bearing, not optional, for this module's core use case. Research §2.1 shows PlanetScope's daily revisit and 3–4m resolution measurably improves classification on India's median ~0.16 ha field size, at a moderate, subscription-based (not per-scene-tasked) cost — a reasonable default-on enhanced tier. Sub-meter tasked sources (SkySat, WorldView Legion, Pléiades Neo) and commercial SAR (ICEYE/Capella/Umbra) carry meaningfully higher per-request cost (research §2.1/§2.2: "$1,200+/scene" for WorldView Legion tasking) and are better suited to budget-gated, high-value-claim use — resolved as an open scope item, §5 below.

**Alternatives considered**:
- *Optical-only, wait for the next clear pass* — rejected: this is the status quo `001` already has via the baseline pipeline's graceful degradation to a weather-only preliminary package; it's retained as the ultimate fallback (`plan.md` Constraints), but doesn't close the gap this feature exists to close.
- *Commercial SAR always-on for every request* — rejected: no source document or research finding supports the cost being justified for every request regardless of claim value or confidence need; reserved as budget-gated per FR-002/FR-013.
- *ISRO Resourcesat-2A LISS-4 as the default enhanced optical tier instead of Planet* — not rejected, but sequenced second: free/sovereign and a real 5.8m option (research §2.3), but 5-day revisit is coarser than PlanetScope's daily cadence and civilian tasking availability for Cartosat-3's finer resolution is unclear from public documentation — a good budget-free fallback within the Satellite Source Registry, not the default.

## 3. Independent crop-type/calendar cross-check source

**Decision**: WorldCereal (ESA), accessed via the Copernicus Data Space Ecosystem / openEO.

**Rationale**: Open-source, production-live (2025), global 10m crop type/irrigation/calendar maps, built on Presto embeddings + CatBoost (research §4.3) — reuses the same foundation-model family chosen in §1 above rather than introducing an unrelated dependency, and is already a proven, actively maintained production system rather than a research artifact.

**Alternatives considered**:
- *Build a custom crop-type classifier* — rejected: WorldCereal already solves this problem at production quality for the relevant crop set; duplicating it would add maintenance burden with no accuracy benefit research surfaced.
- *CropNet* — rejected: US county-level, license unconfirmed, not transferable to India's PMFBY context (research §4.3) — reference-only value.

## 4. Confidence tier structure

**Decision**: Three tiers — High / Medium / Low — computed as a deterministic function of the existing per-component and ensemble confidence figures (`Modeling-Approach.md` §5, §7), with the Low tier carrying a mandatory non-equivalence-to-CCE statement and optional-evidence guidance text.

**Rationale**: Every credible global precedent reviewed uses a small, named tier set with an explicit lowest-tier fallback path rather than a raw score or a binary pass/fail (research §1.10, citing EU CAP Check-by-Monitoring's green/yellow/red as the clearest regulatory precedent). Three tiers is the minimum needed to distinguish "trust this," "this needs more evidence," and "this is genuinely uncertain" — matching CbM's structure without inventing a finer-grained scheme no reviewed precedent uses.

**Alternatives considered**:
- *Binary Pass/Fail* — rejected: collapses the "needs supplementary evidence but isn't necessarily wrong" case that CbM's yellow tier exists specifically to capture (research §1.1); would lose exactly the signal that makes tiered confidence trustworthy per every precedent found.
- *A five-or-more-tier scheme* — rejected: no reviewed precedent uses more than three tiers for this kind of decision-facing output; added granularity would not be traceable to any sourced justification.
- *Numeric score only (status quo)* — rejected as the sole output (the underlying numeric confidence is retained, not removed): research §5 point 1 is explicit that this module's existing confidence figures are the right foundation, but a raw score is not decision-usable for a non-technical reviewer per spec.md SC-003.

## 5. Commercial satellite tasking budget / scale

**Decision**: Not resolved here — explicitly deferred.

**Rationale**: No source document states a tasking budget, per-claim cost ceiling, or volume threshold for commercial VHR/SAR sourcing. Inventing one would violate `CLAUDE.md`'s no-invented-figures convention, the same reasoning `001-evidence-generation-pipeline/research.md` §4 applied to its own concurrency/scale question. Phase 1 design below (data model, contracts) does not depend on this number — the Satellite Source Registry and commercial tasking client are designed to accept a budget/authorization decision as configuration, not as a hardcoded assumption, so resolving this later doesn't require a design change. Full reasoning: [`issue/open query - commercial satellite tasking budget and volume thresholds.md`](./issue/open%20query%20-%20commercial%20satellite%20tasking%20budget%20and%20volume%20thresholds.md).

**Alternatives considered**: N/A — no candidate figures exist in any source document to weigh against each other.

## Output

All technical choices flagged in `plan.md`'s Technical Context are resolved above, except commercial tasking budget/scale, which is deliberately left open and tracked as an issue rather than guessed. This does not block Phase 1 — the data model and contracts are budget-agnostic, treating "was a commercial source available/authorized for this request" as a per-request input rather than a fixed constant.
