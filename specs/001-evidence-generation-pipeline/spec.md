# Feature Specification: Evidence Generation Pipeline

**Feature Branch**: `[001-evidence-generation-pipeline]`

**Created**: 2026-08-12

**Status**: Draft

**Input**: User description: "Build the full evidence-generation pipeline for the Evidence Intelligence Module: given a crop-loss evidence request (field geometry, claimed event date, peril type, optional external reference ID), the system acquires pre-event and post-event satellite imagery (optical Sentinel-2/Landsat, with Sentinel-1 SAR for flood/cloud-cover cases) and correlates it with weather data (CHIRPS, ERA5-Land, GPM IMERG, SMAP, corroborated by IMD AWS where available) for the event window. It runs multi-model damage detection (a semi-physical RUE-based model, AI/ML models, and CSM assimilation for high-scrutiny claims), scores causation confidence (temporal, spatial, magnitude, and physiological alignment between the weather event and observed damage), blends the model outputs into an ensemble yield-loss estimate and a Damage Severity Index, and assembles everything into a legally admissible evidence package (PDF + JSON + GIS maps) satisfying Indian Evidence Act §65B — with mandatory source attribution, methodology versioning, accuracy statements, and chain of custody on every output. The requester receives a request ID immediately and polls for or is notified of the completed package. Every output must be reproducible (same request + same methodology version → same result) and must degrade gracefully (e.g. to a weather-only preliminary package) rather than fail silently when satellite imagery is unavailable. Out of scope: ingesting or validating Crop Cutting Experiment data, CCE-blended yield determination, standalone/proactive predictive alerting before a loss is reported, and any dependency on a specific claim-intimation channel's internal data model — this module only exposes and consumes its own generic evidence-request contract."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate a Complete Evidence Package for a Reported Loss (Priority: P1)

A requester (any claim-intimation channel — voice, web, CSC-assisted, or an insurer's own system) submits an evidence request for a crop-loss event: a field geometry, the claimed event date, and the peril type. The system independently gathers satellite and weather evidence for that specific field and date, runs multiple independent damage-assessment approaches, and returns a complete, audit-ready evidence package the requester can attach to the claim record.

**Why this priority**: This is the entire reason the module exists — closing the evidence gap for a specific claimed loss. Without this flow, nothing else in the module has value.

**Independent Test**: Submit a request with a valid geometry, event date, and peril type for a field with available satellite and weather coverage; verify a complete evidence package is returned containing a damage assessment, a yield-loss estimate, a causation confidence score, and all mandatory admissibility fields.

**Acceptance Scenarios**:

1. **Given** a valid geometry, event date, and peril type with satellite imagery and weather data available for that window, **When** the request is submitted, **Then** the system returns a complete evidence package containing pre/post-event imagery analysis, a weather-event correlation, a causation confidence score, an ensemble yield-loss estimate, a Damage Severity Index, and the mandatory source-attribution, methodology, accuracy, and chain-of-custody fields.
2. **Given** a completed evidence package, **When** the same request is re-submitted against the same pinned methodology version, **Then** the system returns an identical result.
3. **Given** a completed evidence package, **When** any figure in the report is inspected, **Then** it can be traced to a named, dated, publicly identifiable source dataset.

---

### User Story 2 - Track Progress of an In-Flight Evidence Request (Priority: P2)

While an evidence package is being generated, the requester needs to know the request has been received and be able to check its progress, since full satellite-inclusive analysis is not instantaneous.

**Why this priority**: Supports the core flow's usability — without it, requesters cannot distinguish "still working" from "lost request," but the module still produces correct evidence without this feature.

**Independent Test**: Submit a request and confirm a request ID is returned immediately; check status before completion and confirm it reflects an in-progress state; check again after completion and confirm it reflects the completed package.

**Acceptance Scenarios**:

1. **Given** a newly submitted request, **When** the requester checks status immediately after submission, **Then** the system returns a request ID and an in-progress status without waiting for analysis to finish.
2. **Given** a request that is still being processed, **When** the requester checks status, **Then** the system reports current progress state rather than an error or a stale response.
3. **Given** a request whose evidence package is ready, **When** the requester checks status, **Then** the system returns the completed package.

---

### User Story 3 - Receive Usable Evidence When Satellite Imagery Is Unavailable (Priority: P3)

Cloud cover, imagery revisit timing, or source outages can mean no usable satellite image exists yet for the requested window. Rather than the request failing outright, the requester still receives a preliminary, clearly labeled weather-only package, with the full package delivered once imagery becomes available.

**Why this priority**: Protects the module's core reliability promise (never fail silently) for a condition that will occur routinely, especially during monsoon season — but it is a resilience behavior layered on top of User Story 1, not the primary value.

**Independent Test**: Submit a request for a geometry/date window with no usable optical or SAR imagery available; verify a weather-only preliminary package is delivered rather than a failure, and that the request remains open for completion once imagery becomes available.

**Acceptance Scenarios**:

1. **Given** no cloud-free optical imagery is available in the post-event window and the peril is not flood-compatible (so SAR does not substitute), **When** the request is processed, **Then** the system marks the request as insufficient for a full package, delivers a weather-only preliminary package, and continues to seek imagery for a full package.
2. **Given** the peril is flood-compatible and optical imagery is unusable, **When** the request is processed, **Then** the system substitutes SAR-based flood-extent analysis rather than falling back to weather-only.
3. **Given** imagery later becomes available for a request previously delivered as weather-only, **When** the system re-processes the request, **Then** it delivers an updated, complete package.

---

### Edge Cases

- What happens when no historical (multi-year) baseline exists for a geometry (e.g., first season of coverage for that area)? The system proceeds using pre/post-event comparison alone and explicitly states in the package that anomaly-vs-history scoring was omitted, rather than fabricating a baseline.
- How does the system handle a causation confidence score that falls below the defined low-confidence threshold? The package is still delivered, clearly labeled with the low score; the system does not suppress or auto-reject it — the decision of what to do with a low-confidence package belongs to the requester.
- How does the system handle a `peril_type` of "other" or one that is ambiguous? It still runs the generic damage-detection and weather-anomaly pass but skips peril-specific causation heuristics.
- What happens when the underlying satellite or weather data source is unavailable at request time (rather than simply lacking imagery for the window)? The request remains in progress and is retried on a backoff schedule, with the estimated completion time updated accordingly, rather than failing.
- What happens when the pre-event imagery suggests no crop was plausibly standing before the claimed event (phenology/crop-calendar mismatch)? The inconsistency is flagged in the package rather than blocking evidence generation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept an evidence-generation request consisting of a field geometry, a claimed event date, a peril type, and an optional external reference ID.
- **FR-002**: System MUST NOT require or accept any caller-internal claim ID, farmer ID, or policy schema as part of the request — only its own generic fields (Constitution §5, HLD §2).
- **FR-003**: System MUST return a request identifier immediately upon submission, before analysis completes.
- **FR-004**: System MUST allow the requester to retrieve the current status of a submitted request (at minimum: received, in progress, complete, insufficient data, or failed).
- **FR-005**: System MUST acquire pre-event satellite imagery for the requested geometry from a window ending before the claimed event date, and post-event imagery from a window starting at the claimed event date.
- **FR-006**: System MUST substitute radar-based (all-weather) imagery for optical imagery when the peril is flood-compatible and optical imagery is unusable due to cloud cover. For non-flood-compatible perils, unusable optical imagery falls through to the weather-only preliminary path (FR-022) rather than attempting radar substitution — radar flood-extent detection is not a meaningful signal for perils like drought or heatwave.
- **FR-007**: System MUST acquire a multi-year historical baseline of imagery for the same geometry and equivalent seasonal window, to support anomaly detection against the field's own history.
- **FR-008**: System MUST acquire weather data for a window spanning several days before through several days after the claimed event date, and a corresponding multi-year historical baseline for the same calendar window and geometry.
- **FR-009**: System MUST corroborate gridded weather analysis against an official station-level record where one is available for the geometry.
- **FR-010**: System MUST run at least two independently-derived damage/yield-loss assessment approaches (a semi-physical model and an AI/ML model) against the same imagery and weather inputs for every request.
- **FR-011**: System MUST run an additional, higher-fidelity crop-simulation-based assessment approach for requests that meet defined high-scrutiny criteria (criteria not yet set — see Assumptions).
- **FR-012**: System MUST record each damage-assessment approach's own output, methodology version, and confidence/accuracy independently, such that no approach's result overwrites another's.
- **FR-013**: System MUST combine the independent damage-assessment outputs into a single reconciled ensemble yield-loss estimate, weighting each approach's contribution by that approach's own validation confidence, recomputed for every request rather than fixed once per season.
- **FR-014**: System MUST compute a composite damage severity score for the field, normalized against that field's own historical archive rather than a group/regional average.
- **FR-015**: System MUST score causation confidence for every request as a function of temporal alignment, spatial alignment, magnitude correlation, and physiological plausibility between the reported weather event and the observed damage.
- **FR-016**: System MUST assemble every completed request into an evidence package containing a human-readable report, a machine-readable structured record, and supporting maps.
- **FR-017**: Every evidence package MUST state, for every satellite image and weather data point it relies on, the source dataset name, version, and acquisition date/time.
- **FR-018**: Every evidence package MUST state the processing methodology used, including the pinned methodology version, so the package's meaning remains explainable even after methodology is later recalibrated.
- **FR-019**: Every evidence package MUST include an accuracy statement disclosing known limitations of the analysis (e.g., imagery gaps, model accuracy figures).
- **FR-020**: Every evidence package MUST include a chain-of-custody record, a generation timestamp, and an integrity checksum.
- **FR-021**: Re-running an identical request against an unchanged methodology version MUST produce an identical result.
- **FR-022**: When no usable satellite imagery is available within the required window and the peril is not flood-compatible, system MUST deliver a weather-only preliminary package rather than failing the request outright, and MUST continue seeking imagery to complete the package.
- **FR-023**: When no historical baseline exists for a geometry, system MUST proceed using pre/post-event comparison alone and MUST explicitly state in the package that anomaly-vs-history scoring was omitted.
- **FR-024**: When causation confidence falls below a defined low-confidence threshold (numeric value not yet set — see Assumptions), system MUST still deliver the package, clearly labeled with the low score, rather than suppressing or auto-rejecting it.
- **FR-025**: System MUST NOT ingest, validate, or otherwise depend on Crop Cutting Experiment data at any stage of evidence generation.
- **FR-026**: System MUST NOT implement a CCE-blended yield-determination formula, and MUST label its yield-loss estimate and Damage Severity Index as supporting evidence — never as an authoritative or indemnity-grade determination.
- **FR-027**: System MUST only generate evidence in reaction to a reported/claimed loss event — it MUST NOT initiate evidence generation proactively or push unsolicited alerts.
- **FR-028**: System MUST accept requests through the same generic contract regardless of which caller submits them, with no caller receiving a privileged interface or access to another caller's requests.
- **FR-029**: System MUST retain evidence packages and their supporting analysis results for 10 years from the date of generation.

### Key Entities *(include if feature involves data)*

- **Evidence Request**: A single request for evidence tied to one geometry, one claimed event date, and one peril type; carries a status through its lifecycle and an optional opaque caller reference ID.
- **Satellite Analysis Result**: The imagery-derived output for a request — pre-event and post-event index values, source dataset/version/acquisition date, and (when applicable) flood-extent geometry.
- **Damage Assessment Component Result**: One independently-recorded output from a single damage-assessment approach (semi-physical, AI/ML, crop-simulation, ensemble, or severity-index) run against a request, each with its own methodology version and confidence/accuracy figure.
- **Weather Correlation Result**: The weather-derived output for a request — observed value, historical baseline, anomaly score, source dataset/version, and causation confidence score.
- **Evidence Package**: The final assembled output for a completed request — report, structured record, maps, pinned methodology version, checksum, and retention expiry date.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Requesters receive a request identifier immediately (synchronously) upon submitting an evidence request, without waiting for analysis to complete.
- **SC-002**: A weather-only preliminary result is available within minutes of request submission when satellite imagery is not yet available.
- **SC-003**: A full satellite-inclusive evidence package is available within the imagery revisit window relevant to the request's location.
- **SC-004**: 100% of delivered evidence packages include source attribution, pinned methodology version, an accuracy statement, and a chain-of-custody record — zero packages missing any mandatory admissibility field.
- **SC-005**: Re-running an identical request against an unchanged methodology version reproduces the same result 100% of the time.
- **SC-006**: Every figure in every delivered evidence package traces to a named, dated, publicly identifiable data source, with zero fabricated or unattributed figures.
- **SC-007**: When satellite imagery is unavailable for a request, the requester still receives a preliminary package rather than an outright failure in 100% of such cases.
- **SC-008**: 100% of evidence packages clearly and separately label the ensemble yield-loss estimate and the Damage Severity Index as supporting evidence, distinguishable from an authoritative/indemnity-grade determination.

## Assumptions

- Satellite imagery is sourced as optical (primary) with radar-based imagery as the all-weather/flood-compatible substitute; weather data is sourced as gridded precipitation, temperature/wind/humidity reanalysis, near-real-time precipitation, and soil moisture, corroborated by official station-level records where available — per the existing architecture in `hld.md` §7. This spec does not re-decide those source choices.
- Supported peril types are the fixed set already defined in `evidence-flow-spec.md` §2 (hailstorm, flood, drought, cyclone, unseasonal rain, frost, heatwave, weather-induced pest/disease, landslide, cloudburst, other); "other" or ambiguous perils run the generic pass without peril-specific causation heuristics.
- Evidence packages and their supporting analysis results are retained for 10 years from generation, per `constitution.md` §7 and the underlying IRDAI regulation — not a new decision made by this spec.
- Status polling and/or a webhook-style notification are both acceptable ways for a requester to learn a package is complete; neither is mandatory for the requester to implement (`hld.md` §5).
- This spec covers the evidence-generation pipeline itself; it does not cover any specific claim-intimation channel's UI/UX, nor CCE data, nor predictive/proactive alerting — all excluded per `constitution.md` §3–§5.
- **Open — FR-011 CSM "high-scrutiny" trigger criteria**: not defined by any existing document; no transferable numeric precedent exists in `yestech_manual_2023.md` (its closest analog, 5–10% IU-level CCE sampling, is a district/season audit mechanism this module can't use since it's CCE-based). Reads as a product/business policy decision, not a technical constant — to be set during `/speckit-plan`, not invented here. Tracked in [`issue/open query - CSM high-scrutiny trigger criteria (FR-011).md`](./issue/open%20query%20-%20CSM%20high-scrutiny%20trigger%20criteria%20%28FR-011%29.md).
- **Open — FR-024 causation-confidence "low-confidence" numeric threshold**: not defined by any existing document; `yestech_manual_2023.md` mandates disclosing accuracy metrics but never sets numeric acceptance thresholds, so no figure can be sourced from it. Needs empirical calibration against real claims data rather than a guess now — to be resolved during `/speckit-plan`. Tracked in [`issue/open query - causation confidence low-confidence threshold (FR-024).md`](./issue/open%20query%20-%20causation%20confidence%20low-confidence%20threshold%20%28FR-024%29.md).
