# Feature Specification: Satellite Evidence Parity Roadmap

**Feature Branch**: `002-satellite-evidence-parity`

**Created**: 2026-08-12

**Status**: Draft

**Input**: User description: "Satellite Evidence Parity Roadmap — a roadmap for pushing this module's satellite+weather-only evidence generation as close as technically achievable to Crop Cutting Experiment (CCE)-level verification confidence, without ever ingesting CCE data (Constitution §4 remains in force unchanged). Grounded in `documents/research/Satellite-Parity-Global-Precedent-Research.md`: prior country/program precedent (EU CAP Check-by-Monitoring, IBLI, ACRE Africa, ARC, RIICE's India PMFBY deployment), additional satellite providers (very-high-res commercial optical, commercial SAR, ISRO sovereign sources, hyperspectral), physical capture-quality factors (monsoon cloud cover, SAR speckle/decorrelation, mixed-pixel effects on India's small field sizes, atmospheric/BRDF correction, cross-sensor harmonization, latency), and open geospatial foundation models (Presto, Clay, Prithvi-EO-2.0, WorldCereal, SAM2, UN-SPIDER SAR flood toolkit) as additive feature sources for the existing Component 2 model. Defines a phased plan for higher-resolution/SAR-priority sourcing, foundation-model feature augmentation, and a tiered confidence/fallback output pattern, while explicitly not overpromising literal CCE-equivalence."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trustworthy Evidence During Monsoon Cloud Cover (Priority: P1)

A claims reviewer requests evidence for a hailstorm/flood/cloudburst claim filed during Kharif season, when the field has been under persistent cloud cover for the entire pre/post-event window. Today, the optical-only portions of the pipeline may have nothing usable to work from during exactly the events this module exists to evidence. The module must prioritize cloud-penetrating (SAR) sources and, where the case warrants it, higher-resolution options, so the reviewer still receives a usable, evidence-backed package rather than a blank or defaulted-low-confidence result caused purely by sensor blindness rather than genuine analytical uncertainty.

**Why this priority**: This is the single largest capture-quality risk identified in research (documented 90–92% July–August cloud cover in monsoon-affected regions), and it hits precisely the peril types — hailstorm, flood, cloudburst — this module is built to evidence. Without this, every other improvement is built on a foundation that goes dark during the highest-value events.

**Independent Test**: Can be fully tested by submitting a claim with a known cloud-covered event window and verifying the resulting evidence package sources SAR (and, where in scope, tasked higher-resolution imagery) rather than reporting "no usable satellite pass" — delivering value on its own even before any other story in this roadmap ships.

**Acceptance Scenarios**:

1. **Given** a claimed event date where optical imagery is unavailable due to cloud cover for the entire analysis window, **When** the evidence request is processed, **Then** the package is generated using SAR-sourced evidence and clearly states which source class was used and why.
2. **Given** a small field (at or below India's median field size) where existing 10–30m sources produce mixed-pixel ambiguity, **When** a higher-resolution source is available and in scope for that request, **Then** the package uses it and records the resolution/source used.
3. **Given** no cloud-penetrating or higher-resolution source is available or affordable for a given request, **When** the evidence request is processed, **Then** the module falls back to the existing baseline pipeline (Sentinel/Landsat/MODIS) without failing the request.

---

### User Story 2 - Tiered Confidence With an Explicit Fallback Path (Priority: P2)

An insurer, auditor, or claims reviewer receives an evidence package and needs to know, at a glance, how much weight the package's conclusions can bear — without having to interpret a raw numeric confidence score themselves. The module classifies every package into a small number of confidence tiers (mirroring the pattern every credible global precedent uses to make satellite-only verification trustworthy — see `documents/research/Satellite-Parity-Global-Precedent-Research.md` §1.10) and, for the lowest tier, clearly states what additional evidence would help resolve the case further, without assuming any specific channel is available to collect it.

**Why this priority**: Research across every reviewed precedent (EU CAP Check-by-Monitoring's green/yellow/red, IBLI/ARC's accepted basis risk) found that credible ground-truth-free verification always pairs with an explicit tier + fallback pattern, never a single opaque confidence number. This module already computes per-component and ensemble confidence (`documents/Modeling-Approach.md` §5, §7) — this story is the natural, low-risk extension of existing capability into a decision-usable output, not new architecture.

**Independent Test**: Can be fully tested by generating evidence packages across a range of underlying confidence scores and verifying each resolves to the correct tier label with tier-appropriate guidance text, independent of any satellite-source changes from User Story 1.

**Acceptance Scenarios**:

1. **Given** an evidence package with high underlying ensemble confidence, **When** the package is generated, **Then** it is labeled with the highest confidence tier and no further-evidence guidance is shown.
2. **Given** an evidence package with low underlying ensemble confidence, **When** the package is generated, **Then** it is labeled with the lowest confidence tier, explicitly states that it is not equivalent to CCE-based ground truth, and surfaces that supplementary evidence could improve confidence — without naming or requiring any specific claim-intimation channel.
3. **Given** any confidence tier, **When** a reviewer inspects the package, **Then** the tier label is a plain-language classification, not a bare number, and traces back to the specific component/ensemble confidence figures that produced it.

---

### User Story 3 - Foundation-Model-Augmented Damage & Yield-Loss Accuracy (Priority: P3)

A model maintainer wants Component 2 (the AI/ML damage & yield-loss model, `documents/Modeling-Approach.md` §3) to benefit from modern pretrained geospatial representations rather than hand-crafted vegetation indices alone, without abandoning the disclosure discipline the module already commits to. Open, permissively-licensed foundation-model embeddings (starting with Presto, given its production track record as the backbone of ESA's WorldCereal system and its native fit with the module's existing Sentinel-1/2 + weather timeseries inputs) are added as an additional, disclosed feature source alongside — not instead of — the existing NDVI/EVI/SAR feature set.

**Why this priority**: This is an accuracy improvement to an already-functioning component, not a capability that's currently missing entirely (unlike Stories 1–2) — valuable, but appropriately sequenced after the sourcing and confidence-communication gaps that affect every request.

**Independent Test**: Can be fully tested by training/evaluating Component 2 with and without the added embeddings on the same held-out validation split and comparing reported MAE/RMSE/NRMSE, independent of Stories 1 and 2.

**Acceptance Scenarios**:

1. **Given** a documented feature set that includes foundation-model embeddings, **When** a model version is trained and evaluated, **Then** the evidence package's mandatory disclosure (model architecture, feature set, validation accuracy) names the embedding source and its version, per existing Constitution Principle I requirements.
2. **Given** the foundation-model embedding source is unavailable or fails at inference time, **When** an evidence request is processed, **Then** Component 2 falls back to its existing hand-crafted feature set rather than failing the request.

---

### User Story 4 - Independent Crop-Type and Calendar Cross-Check (Priority: P4)

A claims reviewer wants an independent, satellite-derived signal confirming that the crop type and sowing/growth stage implied by the claim actually matches what the imagery shows for that field — catching cases where the declared crop or timeline is inconsistent with observed conditions, using an open crop-type mapping product rather than any ground-truth source.

**Why this priority**: This is a corroboration/discrepancy-flagging enhancement that strengthens trust in existing evidence rather than closing a sourcing or communication gap — most valuable once Stories 1–3 are in place and evidence packages are already reliable enough for a discrepancy flag to be meaningful.

**Independent Test**: Can be fully tested by submitting claims with known crop-type/date mismatches against an independent reference dataset and verifying the module flags the discrepancy rather than silently ignoring or silently resolving it.

**Acceptance Scenarios**:

1. **Given** a claim's declared crop type matches the independently observed crop type for that field and period, **When** the evidence package is generated, **Then** no discrepancy flag is raised.
2. **Given** a mismatch between declared and independently observed crop type or growth stage, **When** the evidence package is generated, **Then** the package includes an explicit, clearly labeled discrepancy flag rather than silently adjusting or suppressing the result.

---

### User Story 5 - Thermal and Red-Edge Stress Signals for Drought and Heatwave Claims (Priority: P5)

A claims reviewer handling a drought or heatwave claim needs stress evidence beyond generic greenness (NDVI), since water stress and heat stress often manifest as a canopy-temperature or chlorophyll/nitrogen signal before they show up as a broad vegetation-index decline. Today the pipeline has a generic, undisclosed "red-edge index" placeholder and no thermal signal at all. This story formalizes dedicated red-edge indices (e.g. NDRE) and adds NASA ECOSTRESS canopy-temperature data as an additive water-stress signal, scoped specifically to `drought` and `heatwave` requests.

**Why this priority**: An accuracy/coverage improvement for two specific peril types, sequenced after the stories that affect every request (sourcing, confidence tiering, foundation-model augmentation, crop cross-check). Depends on no other story in this feature.

**Independent Test**: Submit drought and heatwave claims and verify the evidence package includes named, disclosed red-edge indices, and — where an ECOSTRESS pass is available within the analysis window — a canopy-temperature-derived water-stress signal; verify graceful fallback when no ECOSTRESS pass is available.

**Acceptance Scenarios**:

1. **Given** a drought or heatwave claim where Sentinel-2 red-edge bands are available, **When** the evidence package is generated, **Then** it includes a named, disclosed red-edge index (at minimum NDRE) distinct from the existing generic vegetation index, with source/version provenance.
2. **Given** an ECOSTRESS pass is available within the claim's analysis window, **When** the evidence package is generated, **Then** it includes a canopy-temperature-derived water-stress signal alongside the existing vegetation/SAR signals.
3. **Given** no ECOSTRESS pass is available within the analysis window (its 1–5 day revisit is irregular, not sun-synchronous), **When** the evidence package is generated, **Then** the pipeline falls back to red-edge and existing baseline signals without failing the request.

---

### Edge Cases

- What happens when neither SAR nor any higher-resolution source is available within the request's latency window (e.g., a genuine gap in coverage over a given field)? The module MUST fall back to the existing baseline pipeline and MUST NOT block or fail the evidence request solely because an enhanced source was unavailable.
- What happens when SAR and optical/VHR signals disagree (e.g., SAR indicates flooding but the next cloud-free optical pass shows no visible damage)? The disagreement itself is evidence-relevant and MUST be surfaced in the package rather than silently resolved by picking one source.
- What happens when a request would require paid/tasked commercial imagery (VHR optical or commercial SAR) and tasking budget or authorization is not available for that request? The module MUST fall back to free/open sources and MUST record that a commercial source was considered but not used, rather than silently omitting the consideration.
- What happens when a foundation-model embedding source (Story 3) is deprecated, changes its output format, or becomes unavailable? Evidence generation MUST continue using the existing hand-crafted feature set, and the change in feature-source availability MUST be reflected in the methodology version per Constitution Principle I.
- What happens when ECOSTRESS's irregular revisit doesn't produce a pass within a drought/heatwave claim's analysis window? The module MUST fall back to red-edge and existing baseline signals and MUST NOT fail the request solely because thermal coverage was unavailable — this is expected, disclosed per-package data availability, not a pipeline failure.
- What happens when even the best available combination of sources cannot resolve a case above the lowest confidence tier (the structural ceiling documented in research §2.6 — sub-canopy conditions, actual harvested yield, pre-symptom pest/disease onset)? The package MUST be delivered at the lowest tier with an explicit statement of what remains unresolved, and MUST NOT claim or imply CCE-equivalent confidence regardless of how much sourcing/modeling effort was applied.

### Edge Cases — coverage and geometry (added 2026-08-13)

- What happens when the field is *partially* visible — some valid pixels, but not enough for a confident reading? Coverage is not binary. The module MUST record the proportion of the geometry that was actually observable for each source and window, and MUST reflect it in the confidence tier, rather than treating any non-empty composite as full coverage.
- What happens when the submitted geometry is smaller than a single pixel of the selected source, or is a sliver whose pixels are all boundary pixels? The module MUST record that no pure pixel was available and MUST NOT report a per-field index value as if it were measured on that field alone.
- What happens when the submitted geometry contains non-crop land (a road, a homestead, a water body)? Those pixels bias every index computed over the geometry. The module MUST either exclude them or disclose that the geometry was used unmasked.
- What happens when the claimed event date falls outside any plausible crop calendar for that field — a claim against a fallow field? The existing phenology check flags this today but does not affect any output figure. The flag MUST reach the confidence tier rather than sitting only in the notes.
- What happens when two requests are submitted over overlapping geometries, or the same geometry is claimed twice in one season? The module MUST NOT silently produce independent, potentially contradictory packages with no record that they describe the same ground.
- What happens when the geometry submitted is not the claimant's field — a polygon drawn over a genuinely damaged neighbouring field? The module cannot verify land tenure and MUST NOT imply that it has; the package MUST state that the geometry is caller-asserted.

### Edge Cases — sources, history, and package lifetime (added 2026-08-13)

- What happens when an enhanced source offers higher resolution but a narrower spectral band set than the baseline it replaces (e.g. a source with no SWIR or red-edge bands)? Resolution and spectral coverage trade against each other. The module MUST NOT compute an index under its established name from bands that do not support it, and MUST fall back per FR-003 rather than silently substituting a different index.
- What happens when the field's multi-year historical baseline includes seasons that were themselves loss years? The baseline then encodes damage as normal, suppressing the anomaly. The module MUST use a baseline statistic robust to this and MUST disclose which historical seasons contributed.
- What happens when the claimed event predates the archive of every available source, or the geometry falls outside a source's coverage or latitude band? This is distinct from a transient gap and MUST be reported as a structural coverage limit, not as a retryable insufficient-data state.
- What happens when a data source is reprocessed, re-versioned, or retired *after* a package citing it was issued? Constitution Principle I's reproducibility claim ("the same request re-run later yields the same result") does not survive this on a version string alone. The module MUST record enough to distinguish "the method changed" from "the underlying data changed."
- What happens when many requests arrive for one district at once, as they will during any real regional catastrophe? This is both a load condition and a correlated-failure condition — the same cloud cover or source outage affects every request in the batch simultaneously.
- What happens when a package delivered at the lowest confidence tier is later superseded by a higher-tier package, after the insurer has already acted on the first? Both packages are §65B artifacts under a 10-year retention rule. The relationship between them MUST be explicit in the record, not inferable only from timestamps.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The module MUST select satellite source priority per request based on data availability within the request's analysis window, preferring cloud-penetrating (SAR) sources when optical sources are unusable due to cloud cover.
- **FR-002**: The module MUST support ingestion of higher-resolution (sub-10m) optical and/or commercial SAR sources as an additional evidence tier for requests where the existing 10–30m baseline is structurally insufficient (small field size or monsoon-season cloud cover), where such a source is available and in scope.
- **FR-003**: The module MUST degrade gracefully to the existing baseline pipeline (Sentinel-1/2, Landsat, MODIS) when an enhanced source is unavailable, unaffordable, or not yet integrated for a given region or season, without failing the evidence request.
- **FR-004**: The module MUST compute and report a small number of plain-language confidence tiers per evidence package, derived from and traceable to the existing per-component and ensemble confidence figures (`documents/Modeling-Approach.md` §5, §7).
- **FR-005**: For the lowest confidence tier, the module MUST explicitly state that the package is not equivalent to CCE-based ground truth, consistent with Constitution §4's no-CCE-equivalence-claim boundary.
- **FR-006**: The module MUST support an optional interface for attaching supplementary evidence (e.g., a geotagged photo) to a package, without depending on or assuming any specific claim-intimation channel's schema (Constitution §5).
- **FR-007**: The module MUST support integration of open, permissively-licensed geospatial foundation-model embeddings as an additive feature source for the AI/ML damage & yield-loss model (Component 2), disclosed with the same rigor as its existing hand-crafted features (`documents/Modeling-Approach.md` §3).
- **FR-008**: Foundation-model embeddings MUST be additive only — the module MUST NOT remove or bypass the existing disclosed Component 2 feature set, and MUST continue functioning using that existing feature set if an embedding source becomes unavailable.
- **FR-009**: Every evidence package MUST document which satellite sources (including whether free/open or commercial-tasked) were used to produce it, including source name, resolution, and acquisition date, per Constitution Principle I/II.
- **FR-010**: The module MUST support an independent crop-type and sowing/growth-calendar cross-check against an open crop-type mapping product, and MUST flag — not silently resolve — any material mismatch against the claim's declared crop or date.
- **FR-011**: The module MUST NOT ingest, validate, or reference Crop Cutting Experiment data at any point within this roadmap's scope; Constitution §4 remains unchanged and unaffected by any story in this feature.
- **FR-012**: The module MUST NOT present any output, at any confidence tier or with any combination of enhanced sources, as a replacement for or equivalent to CCE-based yield determination.
- **FR-013**: The module MUST record, per evidence package, whether a commercial (paid/tasked) source was considered and whether it was used, as part of the package's provenance trail.
- **FR-014**: The module SHOULD support human-in-the-loop, segmentation-model-assisted refinement of a submitted field or damage-extent polygon, as an assistive step rather than a fully automated replacement for the submitted field geometry.
- **FR-015**: The module MUST compute and disclose a named red-edge vegetation index (at minimum NDRE), replacing the undisclosed generic "red-edge index" placeholder, for every request where Sentinel-2 red-edge bands are available.
- **FR-016**: The module MUST support ingestion of NASA ECOSTRESS canopy-temperature data as an additive water-stress signal, scoped to `drought` and `heatwave` peril-type requests, where a usable pass exists within the analysis window.
- **FR-017**: The module MUST fall back to red-edge and existing baseline vegetation signals when no ECOSTRESS pass is available within the analysis window, without failing the request.
- **FR-018**: Every red-edge index and ECOSTRESS-derived signal included in a package MUST carry source/version provenance, per the same discipline Constitution Principle I/II requires of every other satellite-derived figure in this module.
- **FR-019**: Commercial satellite tasking (paid VHR optical, commercial SAR) is **not authorized** for this rollout — the Satellite Source Registry's commercial tier remains disabled by default; enhanced-tier sourcing is limited to free/open sources (existing baseline plus ISRO sovereign sources via a dedicated access client, since these are not available through the existing GEE integration).

The following four were added on 2026-08-13. FR-020–FR-022 close capture-quality factors this spec's own Input paragraph names — cross-sensor harmonization, mixed-pixel effects on India's small field sizes, atmospheric/BRDF correction, SAR speckle/decorrelation — which had no requirement behind them; FR-023 closes a reproducibility gap in the thermal signal added by User Story 5.

- **FR-020**: Where a single evidence package draws index values from more than one sensor, the module MUST record which sensor produced each value, and MUST NOT present values from different sensors as directly comparable unless a documented harmonization was applied. Where no harmonization exists for a given sensor pair, the module MUST either confine the comparison to one sensor or disclose it as cross-sensor and unharmonized.
- **FR-021**: Every source in the Satellite Source Registry MUST declare the spectral bands it provides, and the module MUST NOT compute a named index from a source lacking the bands that index requires. A source that improves spatial resolution while removing bands the baseline provided is a partial substitute, not a replacement, and MUST be treated as such in source selection (FR-001, FR-003).
- **FR-022**: SAR change detection MUST compare acquisitions of matching viewing geometry — same relative orbit and same pass direction — since backscatter varies systematically with incidence angle independently of any ground change. Any speckle filtering or terrain correction applied MUST be disclosed with the resulting figure, per the same discipline FR-018 requires of every other satellite-derived value.
- **FR-023**: Every thermal (canopy-temperature) measurement MUST record the acquisition's local solar time, and MUST be compared only against baseline observations at a comparable local solar time. Land surface temperature varies strongly through the day, and ECOSTRESS's ISS orbit is deliberately non-sun-synchronous, so a deviation computed across mismatched overpass times is not reproducible in the sense Constitution Principle I requires.

### Key Entities

- **Confidence Tier**: A plain-language classification (e.g., High / Medium / Low) attached to an evidence package, derived from existing component/ensemble confidence figures, with tier-specific guidance text and, for the lowest tier, an explicit non-equivalence-to-CCE statement.
- **Satellite Source Registry**: The catalog of satellite sources available to the module — baseline (Sentinel-1/2, Landsat, MODIS) and enhanced (higher-resolution optical, commercial SAR, sovereign ISRO sources) — each with resolution, revisit cadence, sensor type, and access model (free vs. commercial), used to select sources per request.
- **Foundation Model Feature Set**: A versioned set of embeddings from an integrated open geospatial foundation model, recorded per Constitution Principle I and used additively alongside the existing Component 2 feature set.
- **Cross-Validation Signal**: The result (consistent / discrepant) of comparing a claim's declared crop type and calendar against an independent, satellite-derived crop-type mapping product.
- **Supplementary Evidence Attachment**: An optional, channel-agnostic evidence item (e.g., a geotagged photo) that can be associated with a package to help resolve a low-confidence case, without coupling the module to any specific intimation channel.
- **Thermal Stress Signal**: A canopy-temperature-derived water-stress measurement (land surface temperature/evapotranspiration deviation from baseline), sourced from NASA ECOSTRESS, associated with a request, present only for `drought`/`heatwave` peril-type requests where a usable pass existed within the analysis window.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For claims filed under monsoon-season cloud-cover conditions, the proportion of requests resolved with a usable (non-"insufficient-data") evidence package increases measurably over the current optical-only baseline, without exceeding the existing evidence-generation latency target.
- **SC-002**: For fields at or below India's median field size, damage-classification accuracy (measured as MAE/RMSE/NRMSE against the same held-out validation methodology already in use) improves measurably versus the 10–30m-only baseline.
- **SC-003**: 100% of evidence packages include a plain-language confidence tier that a non-technical claims reviewer can act on without interpreting a raw numeric score.
- **SC-004**: 0% of evidence packages, across all confidence tiers and all source combinations, present output as equivalent to or a replacement for CCE-based determination (verified via package-content audit).
- **SC-005**: The proportion of claims resolving to the lowest confidence tier is tracked and reported as a visible baseline metric, so later roadmap phases have a concrete number to measure improvement against.
- **SC-006**: For drought and heatwave claims specifically, the evidence package includes a dedicated stress signal (red-edge and/or thermal) distinct from the generic vegetation-index baseline, whenever a usable red-edge or ECOSTRESS source exists for the claim window.
- **SC-007** (added 2026-08-13): The lowest-tier rate from SC-005 is reported **stratified** by field-size band, agro-climatic zone, and season — not only as a single aggregate. Both drivers of a low tier, small fields and monsoon cloud cover, correlate with the smallholder population this module exists to serve, so an aggregate figure can stay flat while the tier systematically disadvantages that group. Stratified reporting is what makes that visible; this criterion asserts the measurement, not a target value for it.

## Assumptions

- "As close as technically achievable to CCE-level verification confidence" is interpreted as narrowing the gap via the tiered-confidence-plus-best-available-source pattern that every reviewed global precedent uses (`documents/research/Satellite-Parity-Global-Precedent-Research.md` §1.10, §5) — not achieving literal parity. No reviewed program achieves CCE-equivalent confidence at individual-field granularity without either a tiered fallback or an area-level index trade-off, so this roadmap does not claim to be the exception.
- **Decided (2026-08-12), no longer an assumption**: commercial (paid/tasked) satellite sources — very-high-resolution optical and commercial SAR — are **not authorized** for this rollout (FR-019). The near-term rollout uses free/open sources only (existing Sentinel/Landsat/MODIS baseline, ISRO sovereign sources via a dedicated Bhoonidhi client, and open foundation-model embeddings). Commercial tasking remains designed-for but inactive, revisited only once a real budget decision is made (`issue/open query - commercial satellite tasking budget and volume thresholds.md`).
- ECOSTRESS's canopy-temperature revisit (1–5 days, irregular, ISS-mounted rather than sun-synchronous) means Thermal Stress Signal availability varies per request and cannot be guaranteed the way baseline Sentinel sources can — this is disclosed as a per-package data-availability fact (FR-017), not treated as a pipeline failure.
- Presto is assumed as the first foundation-model integration target (Story 3) given its production track record as ESA WorldCereal's backbone and its native fit with the module's existing Sentinel-1/2 + weather timeseries inputs; final model selection remains subject to technical evaluation during `/speckit-plan`.
- This roadmap extends the already-implemented pipeline in `specs/001-evidence-generation-pipeline/` (specifically Component 2 and the ensemble/confidence layer of `documents/Modeling-Approach.md`) rather than building new evidence-generation infrastructure from scratch.
- Empirical validation of confidence-tier thresholds and any accuracy claims arising from this roadmap is assumed to occur during the existing Pilot & Validation roadmap phase (`documents/README.md` §8), not resolved unilaterally by this spec.
- The independent crop-type cross-check (Story 4) is understood as a corroboration/discrepancy-flagging signal only — it does not feed a yield-blending formula and is not a step toward any CCE-equivalent function, consistent with Constitution §4.
