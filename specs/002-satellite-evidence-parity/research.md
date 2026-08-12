# Phase 0 Research: Satellite Evidence Parity Roadmap

Resolves the technical choices flagged in `plan.md`'s Technical Context. Every decision below traces to a specific finding in [`documents/research/satellite-parity-global-precedent-research.md`](../../documents/research/satellite-parity-global-precedent-research.md) (§ references below) rather than to an invented figure, per `CLAUDE.md`'s no-invented-figures convention.

## 1. First foundation-model integration target

**Decision**: Presto (NASA Harvest).

**Rationale**: Purpose-built for exactly this module's existing input shape — per-pixel timeseries over Sentinel-1 SAR + Sentinel-2 optical + weather + DEM (research §4.1) — so integration is additive, not a re-architecture. MIT-licensed, weights openly downloadable, and already production-proven as the backbone of ESA's live WorldCereal system (research §4.3), which de-risks "research-only, never actually production-usable" failure mode flagged against several alternatives. Small enough for cheap per-field inference, consistent with the Performance Goals in `plan.md` (no GPU/specialized-compute requirement introduced).

**Alternatives considered**:
- *Clay Foundation Model* — rejected as the *first* target (not ruled out long-term): natively fuses SAR+optical+Landsat+NAIP in one embedding space, which is attractive, but at 632M parameters it's a heavier integration than Presto for a first additive step; a natural Phase-2 candidate once Presto integration is validated.
- *Prithvi-EO-2.0* — rejected as the first target: Apache-2.0 and production-ready, but optical-only (HLS), so it wouldn't cover the SAR side of the existing feature set without a second model; kept as the safest large-backbone fallback if Presto proves insufficient.
- *AlphaEarth Foundations* — rejected: only the *output embeddings* are open (CC-BY-4.0), not the model itself, making it a data dependency on Google infrastructure rather than an offline open-weight model (research §4.1) — inconsistent with this module's existing GEE-adjacent-but-source-agnostic posture.
- *SatMAE* — rejected: license not clearly asserted in the source repository as of this research pass (research §4.1) — do not depend on an unconfirmed-license model in a production evidence pipeline.

## 2. Cloud-penetrating / enhanced-resolution source priority

**Decision (corrected 2026-08-12 — see note below)**: Sentinel-1 SAR (already in the `001` baseline) becomes the default fallback the moment optical is unusable for a request's analysis window; ISRO Resourcesat-2A LISS-4 (free, via the new Bhoonidhi client, §6.3) is the default enhanced-resolution optical tier for small-field cases; EOS-04/RISAT-1A is a free sovereign SAR backup. **Planet PlanetScope, commercial SAR (ICEYE/Capella/Umbra), and tasked VHR (SkySat/WorldView Legion/Pléiades Neo) are all deferred under the free-only decision (§5)** — every one of them is a paid/commercial source per the licensing breakdown this research surfaced (8 of 13 enhanced-tier sources researched are commercial), so none belong in the near-term default tier.

**Correction note**: the original version of this decision (pre-2026-08-12) treated PlanetScope as a "default-on" source despite it being commercial/subscription-based — an inconsistency surfaced when the commercial-licensing breakdown was produced and the free-only decision was made explicit. PlanetScope was moved into the deferred/commercial bucket alongside the sources it was previously distinguished from, rather than left as an unexplained exception to the free-only rule.

**Rationale**: Research §3 documents 90–92% July–August cloud cover in monsoon-affected regions — exactly the window most claimed hailstorm/flood/cloudburst events fall in — making SAR-first fallback load-bearing, not optional, for this module's core use case; this holds regardless of the commercial-tasking decision, since Sentinel-1 is free. Research §2.3 documents LISS-4's free 5.8m/5-day resolution as a real, if partial, improvement over the 10–30m baseline for India's ~0.16 ha median field size — coarser and slower than PlanetScope's 3–4m/daily, but $0, consistent with §5's decision. Every sub-3m or sub-daily option researched (PlanetScope, SkySat, WorldView Legion, Pléiades Neo, ICEYE, Capella, Umbra) is commercial and therefore out of scope for this rollout.

**Alternatives considered**:
- *Optical-only, wait for the next clear pass* — rejected: this is the status quo `001` already has via the baseline pipeline's graceful degradation to a weather-only preliminary package; it's retained as the ultimate fallback (`plan.md` Constraints), but doesn't close the gap this feature exists to close.
- *PlanetScope as a default-on exception to the free-only rule* — rejected (see correction note above): no principled basis for treating one commercial source as "default" while gating the rest; consistency requires treating all 8 commercial sources identically until a budget decision changes that.
- *Cartosat-3 as a free high-resolution option* — not adopted: civilian agri-insurance tasking availability is unclear from public documentation (research §2.3), and its status as a strategic/government asset makes "free" a weaker claim than for LISS-4/EOS-04, which have established civilian access via Bhoonidhi.

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

**Decision (resolved 2026-08-12): Option A — no commercial tasking in the near-term rollout.** Enhanced-tier sourcing is free-only: existing GEE baseline + ISRO sovereign sources (Resourcesat-2A LISS-4, EOS-04) via a new Bhoonidhi client (§6.3 below). `commercial_tasking_client.py` remains an inactive, disabled-by-default stub.

**Rationale**: No source document ever stated a tasking budget, per-claim cost ceiling, or volume threshold, and inventing one would have violated `CLAUDE.md`'s no-invented-figures convention. Rather than block on that missing figure, the decision was made to run free-only for the near-term rollout and revisit once real budget or Pilot & Validation data exists — the same logic the issue file's Option A/C recommendation laid out. The Satellite Source Registry and commercial tasking client were already designed to accept a budget/authorization decision as configuration, not a hardcoded assumption, so this decision required no design change, only a scope reduction for this rollout.

**Alternatives considered**: Option B (budget-gated by claim value/confidence tier) — the natural target once a real budget figure exists, but not chosen now since no threshold value exists to gate on. Option C (defer to Pilot & Validation) — functionally the same near-term behavior as Option A, folded into the same decision rather than tracked as a separate path.

## 6. User Story 5 additions (added 2026-08-12, scope-completeness pass)

### 6.1 Red-edge index formalization

**Decision**: Compute NDRE (Normalized Difference Red-Edge) as the primary formalized index, with Chlorophyll Index Red-Edge and MTCI as secondary/disclosed alternatives, replacing the generic "red-edge index" placeholder in `Modeling-Approach.md` §3's Component 2 feature table.

**Rationale**: `documents/research/satellite-parity-global-precedent-research.md` §2.5a/§2.5a-quantitative documents NDRE detecting nitrogen deficiency 1–2 weeks earlier than NDVI and resisting NDVI's saturation in dense canopy, with sourced R²=0.74–0.94 (nitrogen/chlorophyll) against Sentinel-2's existing red-edge bands (705/740/783nm) — no new data source required, purely a feature-engineering formalization.

**Alternatives considered**: Leaving "red-edge index" generic (status quo) — rejected, since naming and disclosing the specific index is required for the same Constitution Principle I/II provenance discipline every other feature in this module already follows.

### 6.2 ECOSTRESS thermal integration

**Decision**: Ingest NASA ECOSTRESS canopy-temperature data (5 thermal bands, 8–12.5µm, 70m resolution, 1–5 day irregular revisit, free via AWS Open Data Registry) as an additive water-stress signal, scoped to `drought` and `heatwave` peril-type requests.

**Rationale**: Research §2.5a identified this as filling a real gap — no thermal signal exists anywhere in the current feature set, and this module's own peril-type list names `drought`/`heatwave` explicitly. ECOSTRESS measures water stress via evapotranspiration/thermal response, a genuinely different physical principle than reflectance spectroscopy, so it's additive information, not a duplicate of red-edge/NDVI signals.

**Alternatives considered**: Landsat 8/9 TIRS thermal band — rejected as primary choice; Landsat's ~16-day single-satellite revisit is coarser than ECOSTRESS's 1–5 day cadence and Landsat wasn't purpose-built for plant water-stress measurement the way ECOSTRESS is. Not ruled out as a future secondary/fallback thermal source.

### 6.3 ISRO sovereign source access: separate Bhoonidhi client, not folded into GEE

**Decision**: Build a dedicated `bhoonidhi_client.py` for Resourcesat-2A LISS-4 and EOS-04/RISAT-1A, separate from the existing `gee_client.py`.

**Rationale**: Directly checked Google Earth Engine's Data Catalog — it lists NASA/USGS/ESA-primary public datasets (Landsat, MODIS, Sentinel, etc.) with no ISRO/Resourcesat/EOS-series entries found. ISRO's sovereign data is distributed through its own Bhoonidhi/Bhuvan platform, not GEE, so the free-only decision (§5) requires two ingestion clients for its two free-enhanced-tier sources, not one. This was surfaced during the free-only decision discussion and is recorded here rather than left as an incorrect assumption in the design.

**Alternatives considered**: Assuming GEE covers ISRO sources — rejected after direct verification; would have produced a design that silently failed to actually reach the free sources it claimed to use.

## Output

All technical choices flagged in `plan.md`'s Technical Context are resolved above. Commercial tasking budget/scale, previously deferred, is now resolved (§5) — free-only for this rollout. Request-volume/concurrency targets remain open for the same reason `001`'s equivalent question is open — not invented here either, and not blocking Phase 1 design, which is scale-agnostic.
