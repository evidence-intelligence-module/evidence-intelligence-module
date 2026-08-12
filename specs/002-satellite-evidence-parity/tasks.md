---

description: "Task list for Satellite Evidence Parity Roadmap implementation"
---

# Tasks: Satellite Evidence Parity Roadmap

**Input**: Design documents from `/specs/002-satellite-evidence-parity/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/evidence-request-api-extensions.md, quickstart.md — all present

**Tests**: Included. `plan.md`'s project structure extends `001`'s existing `tests/{contract,integration,unit}` convention, and `quickstart.md`'s scenarios map 1:1 to the tasks below, matching how `001-evidence-generation-pipeline/tasks.md` handled the same decision.

**Organization**: Tasks are grouped by user story (from `spec.md`) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)

## Path Conventions

Single project (per `plan.md` Structure Decision, extending `001`): `src/evidence_intelligence/` for source, `src/tests/` for tests. This feature adds new modules within `001`'s existing subpackages rather than a new tree.

## A note on scope not covered elsewhere in this repo's docs

PyTorch is used below to run Presto inference (`research.md` §1 names Presto but not a runtime) — a routine implementation choice, not a domain-specific figure, so it doesn't warrant an `issue/` entry, matching how `001-evidence-generation-pipeline/tasks.md` treated its own FastAPI choice.

**Update (2026-08-12): commercial satellite tasking is resolved, not open.** `issue/open query - commercial satellite tasking budget and volume thresholds.md` is decided — Option A, free-only for this rollout. `T037` below still implements `commercial_tasking_client.py` as a disabled-by-default stub (`COMMERCIAL_TASKING_ENABLED=false`), but it now lives in Polish rather than the User Story 1 critical path, since building a paid-tasking client with no authorized budget isn't near-term work. The free enhanced tier for User Story 1 runs on Sentinel-1 SAR (existing) plus ISRO's Resourcesat-2A LISS-4/EOS-04 via a new Bhoonidhi client (T009) — not PlanetScope, which is commercial and deferred alongside the rest (see `research.md` §2's correction note).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add this feature's dependencies and module skeletons on top of the already-running `001` service

- [ ] T001 Add new dependencies to `src/pyproject.toml`: `torch` (Presto inference, research.md §1), `openeo` (WorldCereal/Copernicus Data Space client, research.md §3), `requests` (Bhoonidhi API client), `boto3` (ECOSTRESS AWS Open Data Registry access, research.md §6.2)
- [ ] T002 [P] Create module skeletons with `__init__.py` exports: `src/evidence_intelligence/ingestion/source_registry.py`, `src/evidence_intelligence/ingestion/bhoonidhi_client.py`, `src/evidence_intelligence/ingestion/commercial_tasking_client.py`, `src/evidence_intelligence/ingestion/crop_calendar_crosscheck.py`, `src/evidence_intelligence/models/foundation_features.py`, `src/evidence_intelligence/models/confidence_tier.py`, `src/evidence_intelligence/models/thermal_stress.py`, `src/evidence_intelligence/models/red_edge_indices.py`, `src/evidence_intelligence/models/field_boundary_assist.py`
- [ ] T003 [P] Add new environment/config entries (`PRESTO_MODEL_PATH`, `WORLDCEREAL_ENDPOINT`, `BHOONIDHI_API_KEY`, `ECOSTRESS_AWS_REGION`, `COMMERCIAL_TASKING_ENABLED` default `false`) in `src/evidence_intelligence/config.py` — no Planet/Maxar/ICEYE credentials configured by default per the free-only decision (`issue/`, resolved)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema and persistence extensions that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Extend database schema per `data-model.md`: new columns on `satellite_analysis_results` (`source_class`, `access_model`, `considered_not_used`), `evidence_packages` (`confidence_tier`, `confidence_tier_guidance`, `cce_non_equivalence_statement`), and `model_component_results` (`red_edge_index_type`, `red_edge_index_value`); new tables `foundation_model_feature_sets`, `crop_calendar_cross_checks`, `supplementary_evidence_attachments`, `thermal_stress_signals` — as SQLAlchemy models + Alembic migration in `src/evidence_intelligence/store/schema.py`
- [ ] T005 [P] Extend `EvidenceStore` persistence layer for all new/extended entities, enforcing the non-null provenance/tier constraints from `data-model.md` (including `cce_non_equivalence_statement = true` when `confidence_tier = LOW`, and non-null provenance on `thermal_stress_signals` rows even when `pass_available = false`) in `src/evidence_intelligence/store/evidence_store.py`

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Trustworthy Evidence During Monsoon Cloud Cover (Priority: P1) 🎯 MVP

**Goal**: Prioritize cloud-penetrating SAR and, where in scope, higher-resolution sources so monsoon-season and small-field claims produce a usable evidence package instead of going dark from sensor blindness.

**Independent Test**: Submit a request for a field/event-date window with full optical cloud cover; verify the resulting package sources SAR (and any authorized enhanced source) rather than reporting insufficient data solely due to cloud cover (`quickstart.md` Scenario 1).

### Tests for User Story 1

- [ ] T006 [P] [US1] Unit test for source-selection priority logic (cloud-cover-aware SAR fallback, small-field resolution threshold) in `src/tests/unit/test_source_registry.py`
- [ ] T007 [P] [US1] Integration test for `quickstart.md` Scenario 1 (cloud-covered window → SAR-sourced package, graceful degradation when no enhanced source available) in `src/tests/integration/test_monsoon_sar_fallback.py`

### Implementation for User Story 1

- [ ] T008 [P] [US1] Implement Satellite Source Registry (catalog of baseline + enhanced sources with resolution, revisit cadence, sensor type, access model) in `src/evidence_intelligence/ingestion/source_registry.py` per `research.md` §2
- [ ] T009 [P] [US1] Implement Bhoonidhi client for ISRO's free sovereign sources (Resourcesat-2A LISS-4, EOS-04/RISAT-1A) — not covered by `gee_client.py` — in `src/evidence_intelligence/ingestion/bhoonidhi_client.py` per `research.md` §6.3 (depends on T001, T003)
- [ ] T010 [US1] Extend Imagery Ingestion to consult `source_registry` for SAR-priority/enhanced-source selection based on cloud-cover availability and field-size threshold, falling back to the `001` baseline pipeline when no enhanced source is available in `src/evidence_intelligence/ingestion/imagery.py` (depends on T008, T009)
- [ ] T011 [US1] Record `source_class`/`access_model`/`considered_not_used` provenance on every `SatelliteAnalysisResult` row, including sources evaluated but not used, in `src/evidence_intelligence/ingestion/imagery.py` (depends on T004, T010)
- [ ] T012 [US1] Surface `sources_used`/`sources_considered_not_used` in the evidence package per `contracts/evidence-request-api-extensions.md` in `src/evidence_intelligence/packaging/report_generator.py` (depends on T011)

**Checkpoint**: User Story 1 fully functional and independently testable — this is the MVP.

---

## Phase 4: User Story 2 - Tiered Confidence With an Explicit Fallback Path (Priority: P2)

**Goal**: Classify every evidence package into a plain-language confidence tier (High/Medium/Low), derived from existing ensemble confidence, with an explicit non-equivalence-to-CCE statement and optional supplementary-evidence attachment for the lowest tier.

**Independent Test**: Generate packages across a range of underlying confidence scores and verify each resolves to the correct tier label with tier-appropriate guidance text and, for the lowest tier, a non-equivalence statement (`quickstart.md` Scenario 2).

### Tests for User Story 2

- [ ] T013 [P] [US2] Contract test for `confidence_tier`/`confidence_tier_guidance`/`cce_non_equivalence_statement` fields against `contracts/evidence-request-api-extensions.md` in `src/tests/contract/test_confidence_tier.py`
- [ ] T014 [P] [US2] Contract test for `POST /evidence-requests/{request_id}/supplementary-evidence` against `contracts/evidence-request-api-extensions.md` in `src/tests/contract/test_supplementary_evidence_post.py`
- [ ] T015 [P] [US2] Integration test for `quickstart.md` Scenario 2 (high/low confidence tiers, non-equivalence statement, supplementary-evidence attachment) in `src/tests/integration/test_confidence_tier_fallback.py`

### Implementation for User Story 2

- [ ] T016 [P] [US2] Implement Confidence Tier classifier (derives HIGH/MEDIUM/LOW from existing per-component/ensemble confidence per `Modeling-Approach.md` §5, §7) in `src/evidence_intelligence/models/confidence_tier.py` per `research.md` §4
- [ ] T017 [US2] Wire confidence tier, guidance text, and `cce_non_equivalence_statement` into `EvidencePackage` generation, enforcing the non-equivalence statement whenever tier is `LOW`, in `src/evidence_intelligence/packaging/report_generator.py` (depends on T016, T004)
- [ ] T018 [US2] Implement `POST /evidence-requests/{request_id}/supplementary-evidence` endpoint (accepts opaque `attachment_type`/`uri`/`caller_supplied_metadata`, never validated against a specific channel schema) in `src/evidence_intelligence/api/routes.py` (depends on T004, T005)
- [ ] T019 [US2] Add validation/error handling for the supplementary-evidence endpoint (`400` on missing `attachment_type`/`uri`, `404` on unknown `request_id`) in `src/evidence_intelligence/api/routes.py` (depends on T018)

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Foundation-Model-Augmented Damage & Yield-Loss Accuracy (Priority: P3)

**Goal**: Add open geospatial foundation-model embeddings (Presto) as an additive, disclosed feature source for Component 2, falling back to the existing hand-crafted feature set when unavailable.

**Independent Test**: Train/evaluate Component 2 with and without the added embeddings on the same held-out split and compare MAE/RMSE/NRMSE; disable the embedding source and confirm the pipeline still completes using the existing feature set (`quickstart.md` Scenario 3).

### Tests for User Story 3

- [ ] T020 [P] [US3] Unit test for foundation-model feature extraction and fallback behavior (missing/invalid `PRESTO_MODEL_PATH`) in `src/tests/unit/test_foundation_features.py`
- [ ] T021 [P] [US3] Integration test for `quickstart.md` Scenario 3 (train with/without embeddings, compare validation metrics; fallback disclosure when source unavailable) in `src/tests/integration/test_foundation_model_augmentation.py`

### Implementation for User Story 3

- [ ] T022 [P] [US3] Implement foundation-model feature extraction (Presto embedding inference, versioned per Constitution Principle I) in `src/evidence_intelligence/models/foundation_features.py` per `research.md` §1 (depends on T001)
- [ ] T023 [US3] Extend the AI/ML Damage & Yield-Loss Model to accept foundation-model embeddings as an additive feature source alongside its existing hand-crafted features, falling back to the existing feature set alone when the embedding source is unavailable, in `src/evidence_intelligence/models/ai_ml.py` (depends on T022)
- [ ] T024 [US3] Record `FoundationModelFeatureSet` (`model_name`/`model_version`/`status`) per request in `src/evidence_intelligence/pipeline.py` (depends on T004, T023)
- [ ] T025 [US3] Surface `foundation_model_features` disclosure in the evidence package per `contracts/evidence-request-api-extensions.md` in `src/evidence_intelligence/packaging/report_generator.py` (depends on T024)

**Checkpoint**: User Stories 1, 2, and 3 all work independently.

---

## Phase 6: User Story 4 - Independent Crop-Type and Calendar Cross-Check (Priority: P4)

**Goal**: Independently verify a claim's declared crop type/calendar against an open crop-type mapping product (WorldCereal), flagging — not silently resolving — discrepancies.

**Independent Test**: Submit claims with matching and mismatching declared/observed crop type or calendar and verify the discrepancy flag is raised only for genuine mismatches (`quickstart.md` Scenario 4).

### Tests for User Story 4

- [ ] T026 [P] [US4] Integration test for `quickstart.md` Scenario 4 (matching and mismatching crop-type/calendar cases) in `src/tests/integration/test_crop_calendar_crosscheck.py`

### Implementation for User Story 4

- [ ] T027 [P] [US4] Implement WorldCereal-based crop-type/calendar cross-check client (via `openeo`/Copernicus Data Space Ecosystem) in `src/evidence_intelligence/ingestion/crop_calendar_crosscheck.py` per `research.md` §3 (depends on T001)
- [ ] T028 [US4] Wire the cross-check into pipeline orchestration, persisting `CropCalendarCrossCheck` with `discrepancy_flag` in `src/evidence_intelligence/pipeline.py` (depends on T004, T027)
- [ ] T029 [US4] Surface `crop_calendar_cross_check` in the evidence package per `contracts/evidence-request-api-extensions.md` in `src/evidence_intelligence/packaging/report_generator.py` (depends on T028)

**Checkpoint**: All four original user stories independently functional.

---

## Phase 7: User Story 5 - Thermal and Red-Edge Stress Signals for Drought and Heatwave Claims (Priority: P5)

**Goal**: Formalize dedicated red-edge vegetation indices (NDRE) and add NASA ECOSTRESS canopy-temperature data as an additive water-stress signal, scoped to `drought`/`heatwave` requests, where the pipeline currently has no thermal signal at all.

**Independent Test**: Submit drought/heatwave claims and verify the package includes named red-edge indices and, where an ECOSTRESS pass is available, a thermal water-stress signal; verify graceful fallback when no pass is available (`quickstart.md` Scenario 6).

### Tests for User Story 5

- [ ] T030 [P] [US5] Unit test for red-edge index computation (NDRE from Sentinel-2 red-edge bands) in `src/tests/unit/test_red_edge_indices.py`
- [ ] T031 [P] [US5] Unit test for ECOSTRESS ingestion and pass-availability fallback (`pass_available: false` case) in `src/tests/unit/test_thermal_stress.py`
- [ ] T032 [P] [US5] Integration test for `quickstart.md` Scenario 6 (red-edge + thermal signal present, ECOSTRESS-unavailable fallback, non-drought/heatwave peril scoping) in `src/tests/integration/test_thermal_red_edge_signals.py`

### Implementation for User Story 5

- [ ] T033 [P] [US5] Implement red-edge index computation (NDRE, with Chlorophyll Index Red-Edge/MTCI as disclosed alternatives), replacing the generic "red-edge index" placeholder, in `src/evidence_intelligence/models/red_edge_indices.py` per `research.md` §6.1
- [ ] T034 [P] [US5] Implement ECOSTRESS canopy-temperature ingestion (AWS Open Data Registry, `boto3`), scoped to `drought`/`heatwave` peril types, in `src/evidence_intelligence/models/thermal_stress.py` per `research.md` §6.2 (depends on T001)
- [ ] T035 [US5] Wire red-edge index and `ThermalStressSignal` computation into pipeline orchestration, persisting both (with `pass_available = false` recorded rather than skipped when no ECOSTRESS pass exists) in `src/evidence_intelligence/pipeline.py` (depends on T004, T033, T034)
- [ ] T036 [US5] Surface `red_edge_index`/`thermal_stress_signal` in the evidence package per `contracts/evidence-request-api-extensions.md` in `src/evidence_intelligence/packaging/report_generator.py` (depends on T035)

**Checkpoint**: All five user stories independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories, plus deferred/lower-priority work

- [ ] T037 [P] Implement commercial tasking client (isolated, vendor-agnostic interface for Planet/Maxar/ICEYE-class tasking requests), gated off by default via `COMMERCIAL_TASKING_ENABLED`, in `src/evidence_intelligence/ingestion/commercial_tasking_client.py` per `research.md` §5 — **deferred, not part of any near-term critical path** per the free-only decision (`issue/`, resolved); retained as a disabled stub so a future budget decision needs only a config change
- [ ] T038 [P] Implement optional field/damage-boundary segmentation assist (FR-014, SHOULD-priority; human-in-the-loop only, given the documented SAM2 remote-sensing domain gap, `documents/research/Satellite-Parity-Global-Precedent-Research.md` §4.2) in `src/evidence_intelligence/models/field_boundary_assist.py`
- [ ] T039 [P] Add unit tests for graceful-degradation edge cases (no enhanced source available, foundation-model source deprecated, SAR/optical disagreement surfaced rather than silently resolved, ECOSTRESS unavailable) in `src/tests/unit/test_graceful_degradation.py`
- [ ] T040 [P] Update `GUIDE.md` with operational instructions for the new capabilities (source registry configuration, Bhoonidhi setup, confidence-tier interpretation, foundation-model training, thermal/red-edge signals, commercial-tasking gating)
- [ ] T041 Run `quickstart.md` validation across all 6 scenarios end-to-end against a deployed instance

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately once `001` is running
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - Can proceed in parallel (if staffed) or sequentially in priority order (P1 → P2 → P3 → P4 → P5)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories in this feature
- **User Story 2 (P2)**: No dependencies on other stories — confidence-tier computation reads existing `001` ensemble confidence, not US1's new sources
- **User Story 3 (P3)**: No dependencies on other stories — Component 2 augmentation is independent of source selection and confidence tiering
- **User Story 4 (P4)**: No dependencies on other stories
- **User Story 5 (P5)**: No dependencies on other stories — red-edge/thermal signals are independent of source selection (US1), confidence tiering (US2), foundation-model features (US3), and crop cross-check (US4)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Registry/client modules before pipeline wiring
- Pipeline wiring before package-generator surfacing
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- T004/T005 in Foundational are sequential (schema before persistence layer built on it)
- Once Foundational completes, all five user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- T037/T038/T039/T040 in Polish can all run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch tests for User Story 1 together:
Task: "Unit test for source-selection priority logic in src/tests/unit/test_source_registry.py"
Task: "Integration test for quickstart.md Scenario 1 in src/tests/integration/test_monsoon_sar_fallback.py"

# Launch independent implementation modules for User Story 1 together:
Task: "Implement Satellite Source Registry in src/evidence_intelligence/ingestion/source_registry.py"
Task: "Implement Bhoonidhi client in src/evidence_intelligence/ingestion/bhoonidhi_client.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run `quickstart.md` Scenario 1 independently
5. Deploy/demo if ready — this alone closes the largest capture-quality gap identified in `documents/research/Satellite-Parity-Global-Precedent-Research.md`

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Validate independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Validate independently → Deploy/Demo
4. Add User Story 3 → Validate independently → Deploy/Demo
5. Add User Story 4 → Validate independently → Deploy/Demo
6. Add User Story 5 → Validate independently → Deploy/Demo
7. Each story adds value without breaking previous stories or `001`'s existing behavior

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Commercial tasking (T037) ships gated off by default (`COMMERCIAL_TASKING_ENABLED=false`), decided (not just deferred) free-only for this rollout per `issue/open query - commercial satellite tasking budget and volume thresholds.md` — does not block any user story
- ECOSTRESS's irregular revisit means `pass_available = false` is an expected, normal outcome for User Story 5, not an error condition — tests (T031, T032) must cover it as a first-class case, not an edge case
- Every task in this file is additive to `001-evidence-generation-pipeline`'s existing implementation; none replace or remove existing `001` behavior
