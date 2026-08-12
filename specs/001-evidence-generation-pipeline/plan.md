# Implementation Plan: Evidence Generation Pipeline

**Branch**: `001-evidence-generation-pipeline` | **Date**: 2026-08-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-evidence-generation-pipeline/spec.md`

**Implements**: [`documents/hld.md`](../../documents/hld.md) — that document is the architectural source of truth; this plan and its Phase 0/1 artifacts (`research.md`, `data-model.md`, `contracts/`) translate it into an executable build, they do not redesign it.

## Summary

A standalone backend service that accepts a generic evidence-request (field geometry, event date, peril type, optional external reference ID), acquires satellite imagery and weather data for the event window, runs three independent damage/yield-loss assessment approaches (semi-physical, AI/ML, and — for high-scrutiny requests — crop-simulation assimilation) plus a causation-confidence scorer, blends the results into an ensemble estimate and a Damage Severity Index, and assembles everything into a §65B-admissible evidence package (PDF + JSON + maps). Built as a Python service on top of Google Earth Engine, following the architecture already fixed in `hld.md` — this plan implements that architecture, it does not redesign it.

## Technical Context

**Language/Version**: Python 3.11 — matches every dependency below (GEE Python API, scikit-learn, ReportLab); no other language appears anywhere in `hld.md` §7.

**Primary Dependencies**: Google Earth Engine Python API (satellite/weather data access); scikit-learn (Random Forest) and/or a DNN framework (AI/ML damage model, modeling-approach.md §3); WOFOST or InfoCrop, Indian-calibrated (CSM assimilation, advanced tier, modeling-approach.md §4); Matplotlib/Folium (GIS map generation); ReportLab (PDF report generation).

**Storage**: S3-compatible object storage for evidence packages and imagery derivatives (HLD §7, explicit). A relational store is required for the structured data model (`evidence_requests`, `satellite_analysis_results`, `model_component_results`, `weather_correlation_results`, `evidence_packages` — HLD §4) but no specific engine is named in existing docs — resolved in [research.md](./research.md).

**Testing**: Not specified in existing docs — resolved in [research.md](./research.md).

**Target Platform**: Cloud-based compute (HLD §7 — "Compute: Cloud-based; GEE handles heavy satellite compute server-side; ML/CSM components run on standard cloud compute"); Linux containers assumed as the reasonable default for cloud-based Python services — resolved in [research.md](./research.md).

**Project Type**: Single backend service (no frontend in scope — this module's only interface is the generic Evidence Request Interface, HLD §5). Maps to the "Single project" structure below.

**Performance Goals**: Weather-only preliminary result within minutes of request submission; full satellite-inclusive package within the relevant imagery revisit window (HLD §8, spec.md SC-002/SC-003). No numeric throughput/concurrency target exists in any source document — not invented here.

**Constraints**: Reproducibility — identical request + unchanged methodology version MUST yield an identical result (Constitution §2.1, spec.md FR-021). Never fail silently — degrade to a weather-only preliminary package rather than error out when imagery is unavailable (HLD §8, spec.md FR-022). Every output carries source attribution, pinned methodology version, accuracy statement, and chain of custody (Constitution §2.4, spec.md FR-017–FR-020). 10-year retention from generation (Constitution §7, spec.md FR-029). No CCE ingestion or CCE-blending at any stage (Constitution §4, spec.md FR-025–FR-026). No proactive/predictive alerting — every run is reactive to a submitted request (Constitution §3, spec.md FR-027). No privileged caller — one generic contract for every requester (Constitution §5, spec.md FR-028).

**Scale/Scope**: Not specified in any source document (no concurrent-request or claims-volume target exists yet) — flagged as an open item in [research.md](./research.md) rather than assumed.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Constitution principle | Gate | Status |
|---|---|---|
| I. Reproducible, Versioned Evidence | Every model component and package carries a pinned `methodology_version`; identical inputs + version → identical output | **PASS** — `model_component_results.methodology_version` and `evidence_packages.methodology_version` (data-model.md) carry this; no design element recomputes without recording its version |
| II. Event-Causal, Independently Verifiable | Every package traces to a specific geometry/date/peril and to named, dated public sources | **PASS** — `evidence_requests` scopes every run to one geometry/date/peril; `satellite_analysis_results`/`weather_correlation_results` carry `source_dataset`/`source_version`/`acquisition_date` |
| III. Legally Admissible by Construction (NON-NEGOTIABLE) | §65B fields (attribution, methodology, accuracy, chain of custody) mandatory on every output | **PASS** — `evidence_packages` schema (data-model.md) makes these required fields, not optional; Report/Package Generator component cannot emit a package without them |
| IV. No CCE, No Standalone Prediction (NON-NEGOTIABLE) | No CCE ingestion/blending; no proactive alerting; pipeline only runs on an inbound request | **PASS** — data model has no CCE-related entity or foreign key; the only trigger in this design is the Evidence Request Interface receiving a request (contracts/evidence-request-api.md) |
| V. Standalone Interface, No Privileged Caller | One generic request/response contract; module owns its own schema | **PASS** — contracts/evidence-request-api.md defines the sole external interface; `external_reference_id` is opaque and never interpreted; no caller-specific schema exists anywhere in the design |

No violations — Complexity Tracking table below is empty.

**Post-Phase-1 re-check** (2026-08-12, after `data-model.md`/`contracts/`/`quickstart.md` were written): all five gates above still hold against the actual design artifacts, not just the intent — `data-model.md`'s Entity Relationships section has no CCE-related entity and no foreign key leaving this module's schema (Principle IV/V); every table in `data-model.md` carries the provenance/methodology-version fields Principle I/II/III require as non-nullable; `contracts/evidence-request-api.md` defines exactly one interface with no caller-specific variant (Principle V). No new violations introduced during design. Gate re-confirmed **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/001-evidence-generation-pipeline/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
├── issue/                # Open queries deferred from spec (FR-011, FR-024)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/evidence_intelligence/
├── api/                  # Evidence Request Interface (HLD §3) — request intake, status/result retrieval
├── ingestion/
│   ├── imagery.py        # Imagery Ingestion (HLD §3) — pre/post-event + historical baseline via GEE
│   └── weather.py        # Weather Correlation Engine (HLD §3) — CHIRPS/ERA5/GPM/SMAP + IMD AWS corroboration
├── models/
│   ├── semi_physical.py  # Component 1 — modeling-approach.md §2
│   ├── ai_ml.py          # Component 2 — modeling-approach.md §3
│   ├── csm_assimilation.py # Component 3 (advanced tier) — modeling-approach.md §4
│   ├── ensemble.py       # Component 4 — modeling-approach.md §5
│   └── dsi.py             # Component 5 (Damage Severity Index) — modeling-approach.md §6
├── causation/
│   └── scoring.py         # Causation Analysis Engine — evidence-flow-spec.md §5
├── packaging/
│   └── report_generator.py # Report/Package Generator (HLD §3, §6) — PDF/JSON/maps + §65B fields
└── store/
    └── evidence_store.py   # Evidence Store (HLD §4 data model) — persistence + retention

src/tests/
├── contract/              # Validates api/ against contracts/evidence-request-api.md
├── integration/           # End-to-end: request → package, per spec.md User Stories 1-3
└── unit/                  # Per-component tests (models/, causation/, packaging/)
```

**Structure Decision**: Single project (Option 1). This module has one external interface (the Evidence Request Interface) and no frontend — HLD §3's component table maps directly onto the package layout above, one subpackage per component so each stays independently testable per the module's own design principle (Constitution §5 / HLD §1: standalone, consumer-agnostic).

## Complexity Tracking

*No Constitution Check violations — table intentionally empty.*
