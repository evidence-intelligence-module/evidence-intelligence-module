# Implementation Plan: Satellite Evidence Parity Roadmap

**Branch**: `002-satellite-evidence-parity` | **Date**: 2026-08-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-satellite-evidence-parity/spec.md`

**Extends**: [`specs/001-evidence-generation-pipeline/`](../001-evidence-generation-pipeline/) — this is a second feature against the same running service, not a new service. It extends the existing data model (`../001-evidence-generation-pipeline/data-model.md`), API contract (`../001-evidence-generation-pipeline/contracts/evidence-request-api.md`), and `Modeling-Approach.md` Component 2, rather than redesigning them. Where this plan doesn't override 001's decisions, 001's decisions still apply.

**Grounded in**: [`documents/research/Satellite-Parity-Global-Precedent-Research.md`](../../documents/research/Satellite-Parity-Global-Precedent-Research.md) — every source-selection and confidence-tiering decision below traces to a cited finding there, not to an invented figure.

## Summary

Extends the existing evidence-generation pipeline with five additive capabilities, in priority order: (1) source-selection logic that prioritizes cloud-penetrating SAR and, where in scope, higher-resolution optical/SAR sources over the current 10–30m optical-only baseline, so monsoon-season and small-field claims don't go dark from sensor blindness; (2) a plain-language confidence tier (High/Medium/Low) attached to every evidence package, mirroring the tiered-confidence-plus-fallback pattern every reviewed global precedent uses, derived from — not replacing — the existing ensemble confidence figure; (3) an additive open-foundation-model embedding feature source (Presto first) feeding the existing AI/ML damage model (Component 2) alongside its current hand-crafted features; (4) an independent crop-type/calendar cross-check against an open crop-type mapping product, flagging discrepancies rather than resolving them silently; (5) dedicated red-edge vegetation indices and NASA ECOSTRESS canopy-temperature data as additive stress signals specifically for drought and heatwave claims, where the pipeline currently has no thermal signal at all. No new service, no new external interface shape beyond additive fields/endpoints on the existing Evidence Request Interface, and no change to the Constitution §4 no-CCE boundary.

**Decision update (2026-08-12)**: commercial satellite tasking (VHR optical, commercial SAR) is **not** part of the near-term rollout — decided free-only (`issue/open query - commercial satellite tasking budget and volume thresholds.md`, Resolution). Enhanced-tier sourcing for this rollout is limited to the existing GEE-hosted baseline plus ISRO's free sovereign sources (Resourcesat-2A LISS-4, EOS-04/RISAT-1A) accessed via a separate Bhoonidhi client — GEE does not host ISRO's own satellite data (confirmed directly against Earth Engine's Data Catalog, which lists NASA/USGS/ESA-primary datasets only). `commercial_tasking_client.py` remains in the design as a disabled-by-default stub, not deleted, so a future budget decision needs only a config change.

## Technical Context

**Language/Version**: Python 3.11 — unchanged from `001-evidence-generation-pipeline/plan.md`; every new dependency below has a mature Python 3.11-compatible client.

**Primary Dependencies**: Existing (`001` plan) — GEE Python API, scikit-learn/DNN framework, WOFOST/InfoCrop, Matplotlib/Folium, ReportLab. **New**: a PyTorch runtime to load and run Presto (open, MIT-licensed, small ViT-style pixel-timeseries transformer — research §4.1) for foundation-model embeddings; an openEO/Copernicus Data Space Ecosystem client for WorldCereal-based crop-type cross-checking (research §4.3); a Bhoonidhi API client for ISRO's free sovereign sources (Resourcesat-2A LISS-4, EOS-04/RISAT-1A — not available via GEE, see Summary decision update); an AWS Open Data Registry client (`boto3` or plain HTTPS, no vendor-specific SDK needed) for NASA ECOSTRESS canopy-temperature data. Vendor tasking API clients for commercial enhanced-tier sources (Planet/Maxar/Airbus/ICEYE/Capella) are designed-for but **not implemented in this rollout** — isolated behind the Satellite Source Registry and gated off per the free-only decision above, so no commercial vendor SDK is hard-baked into the core pipeline (preserves the module's own standalone-by-design ethos, Constitution §5, applied internally as well as externally).

**Storage**: Extends the existing PostgreSQL + PostGIS store (`001` plan) — new columns and tables only (data-model.md below); no new storage engine.

**Testing**: pytest — unchanged from `001`.

**Target Platform**: Unchanged — Linux containers on cloud compute. Presto inference is lightweight (research §4.1: "small enough for cheap per-field inference") — no GPU or specialized-compute requirement is introduced by this plan.

**Project Type**: Single backend service (extension of the existing service — no new project, no frontend).

**Performance Goals**: Must not regress the existing targets (`001` plan: weather-only preliminary within minutes; full package within the relevant imagery revisit window). Source-selection logic (capability 1) and the confidence-tier computation (capability 2) run on the request's synchronous path and must add negligible latency; foundation-model inference (capability 3) and the crop-calendar cross-check (capability 4) are additive analysis steps within the existing full-package timing budget, not on any new faster path.

**Constraints**: All constraints from `001-evidence-generation-pipeline/plan.md` carry forward unchanged (reproducibility, never-fail-silently, mandatory provenance, 10-year retention, no CCE, no proactive alerting, no privileged caller). New in this plan: enhanced sources and foundation-model features MUST be additive/optional — the pipeline MUST produce a complete evidence package using only the existing `001` baseline if no enhanced source or foundation-model feature is available for a given request (spec.md FR-003, FR-008); commercial/tasked source usage MUST be recorded whether or not it was actually used (spec.md FR-013); discrepancy flags (capability 4) MUST be surfaced, never silently resolved (spec.md FR-010).

**Scale/Scope**: Commercial (paid/tasked) satellite source budget and per-region/per-season volume thresholds — **resolved 2026-08-12**: none authorized for this rollout (Option A, free-only), so this no longer gates Scale/Scope; commercial tasking is simply out of scope until revisited (see [`issue/open query - commercial satellite tasking budget and volume thresholds.md`](./issue/open%20query%20-%20commercial%20satellite%20tasking%20budget%20and%20volume%20thresholds.md), Resolution). Request-volume/concurrency targets remain unresolved for the same reason `001`'s own equivalent question is open — not invented here either.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Constitution principle | Gate | Status |
|---|---|---|
| I. Reproducible, Versioned Evidence | Every new signal (source selection, foundation-model feature, cross-check) carries a pinned version/provenance; identical inputs + version → identical output | **PASS** — `foundation_model_feature_sets.model_version`, `satellite_analysis_results.source_class`/`access_model`, and `crop_calendar_cross_checks.source_dataset`/`source_version` (data-model.md) all carry this; confidence-tier computation is a pure function of already-versioned component/ensemble outputs, adding no unversioned input |
| II. Event-Causal, Independently Verifiable | Every new source/signal traces to a specific request and to a named, dated public or commercial source | **PASS** — new tables all FK to `evidence_requests`; `satellite_analysis_results` extension records source name, resolution class, and acquisition date for every source considered, not just the one used |
| III. Legally Admissible by Construction (NON-NEGOTIABLE) | §65B fields remain mandatory on every output; new fields (confidence tier, discrepancy flags) are additive to, not replacements for, existing mandatory fields | **PASS** — `evidence_packages.confidence_tier` and its guidance text are additive columns; the existing attribution/methodology/accuracy/chain-of-custody fields from `001-evidence-generation-pipeline/data-model.md` are untouched |
| IV. No CCE, No Standalone Prediction (NON-NEGOTIABLE) | No CCE ingestion/blending anywhere in this plan; every new capability is reactive to an existing request | **PASS** — no entity in data-model.md below references CCE data; the crop-calendar cross-check (capability 4) compares against an open crop-type mapping product, never CCE; the lowest confidence tier explicitly states non-equivalence to CCE (spec.md FR-005), reinforcing rather than relaxing this boundary |
| V. Standalone Interface, No Privileged Caller | New endpoint/fields remain generic; no caller-specific schema is introduced | **PASS** — the new Supplementary Evidence Attachment endpoint (contracts/) accepts an opaque attachment with no assumption about which intimation channel produced it, matching the existing `external_reference_id` pattern in `001`'s contract |

No violations — Complexity Tracking table below is empty.

**Post-decision re-check (2026-08-12, free-only + User Story 5 added)**: the free-only decision removes a dependency, not adds one — no new gate exposure. User Story 5 (red-edge/ECOSTRESS) introduces one new entity (`ThermalStressSignal`, data-model.md) which, like every other entity in this design, FKs only to `evidence_requests` and carries mandatory source/version provenance — same Principle I/II pattern as everything else here. All five gates re-confirmed **PASS**.

**Post-Phase-1 re-check** (2026-08-12, after `data-model.md`/`contracts/`/`quickstart.md` were written): all five gates above still hold against the actual design artifacts. `data-model.md`'s new/extended entities add no CCE-related table or foreign key (Principle IV); every new table carries mandatory provenance fields matching the non-nullable pattern `001` already established (Principle I/II); the new contract endpoint follows the identical opaque/generic pattern as the existing `POST /evidence-requests` (Principle V). No new violations introduced during design. Gate re-confirmed **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/002-satellite-evidence-parity/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command) — extends 001's data-model.md
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command) — extends 001's contract
├── checklists/          # Spec quality checklist (/speckit-specify command)
├── issue/                # Open queries deferred from spec/plan (commercial tasking budget)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/evidence_intelligence/
├── api/
│   └── routes.py                     # MODIFIED — new supplementary-evidence endpoint (contracts/)
├── ingestion/
│   ├── imagery.py                    # MODIFIED — consults source_registry.py for SAR-priority/enhanced-source selection
│   ├── gee_client.py                 # UNCHANGED — remains the client for existing baseline (Sentinel/Landsat/MODIS) sources
│   ├── source_registry.py            # NEW — Satellite Source Registry: catalog + selection logic (FR-001, FR-002, FR-003, FR-013)
│   ├── bhoonidhi_client.py           # NEW — ISRO free sovereign sources (Resourcesat-2A LISS-4, EOS-04); not covered by gee_client.py
│   ├── commercial_tasking_client.py  # NEW, INACTIVE — isolated stub for tasked VHR/commercial SAR, disabled by free-only decision (FR-002, FR-013); not on the near-term critical path
│   └── crop_calendar_crosscheck.py   # NEW — WorldCereal-based crop-type/calendar cross-check (FR-010)
├── models/
│   ├── ai_ml.py                      # MODIFIED — accepts foundation-model embeddings as an additive feature source (FR-007, FR-008)
│   ├── foundation_features.py        # NEW — Presto embedding extraction, versioned (FR-007, FR-008)
│   ├── confidence_tier.py            # NEW — derives High/Medium/Low tier from existing ensemble confidence (FR-004, FR-005)
│   ├── thermal_stress.py             # NEW — ECOSTRESS canopy-temperature ingestion + water-stress signal for drought/heatwave (FR-016, FR-017)
│   ├── red_edge_indices.py           # NEW — formalized NDRE/CIred-edge/MTCI computation, replacing the generic "red-edge index" placeholder (FR-015)
│   └── field_boundary_assist.py      # NEW, SHOULD-priority — human-in-the-loop segmentation assist (FR-014)
├── packaging/
│   └── report_generator.py           # MODIFIED — surfaces confidence tier, source provenance, discrepancy flags, non-equivalence statement, thermal/red-edge signals
└── store/
    └── schema.py                      # MODIFIED — new columns/tables per data-model.md

src/tests/
├── contract/              # New: validates api/ against contracts/ extension
├── integration/           # New: end-to-end per spec.md User Stories 1-5
└── unit/                  # New: source_registry, confidence_tier, foundation_features, crop_calendar_crosscheck, thermal_stress, red_edge_indices
```

**Structure Decision**: Single project (Option 1), same as `001` — this is an extension of the existing service, not a new one. Every new module is additive within the existing `ingestion/`, `models/`, `packaging/` subpackages so each stays independently testable, matching the module's existing per-component structure; nothing here introduces a second service, a frontend, or a new top-level source tree.

## Complexity Tracking

*No Constitution Check violations — table intentionally empty.*
