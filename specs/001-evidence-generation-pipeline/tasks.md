---
description: "Task list for Evidence Generation Pipeline implementation"
---

# Tasks: Evidence Generation Pipeline

**Input**: Design documents from `/specs/001-evidence-generation-pipeline/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/evidence-request-api.md, quickstart.md — all present

**Tests**: Included. `plan.md`'s project structure already commits to `tests/{contract,integration,unit}`, and `quickstart.md`'s "Automated test mapping" table specifies exactly which tests validate each user story — tasks below implement that mapping.

**Organization**: Tasks are grouped by user story (from `spec.md`) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Single project (per `plan.md` Structure Decision): `crop-insurance/code/evidence_intelligence/` for source, `crop-insurance/code/tests/` for tests.

## A note on scope not covered elsewhere in this repo's docs

Building this pipeline requires an HTTP framework to serve `contracts/evidence-request-api.md`; no existing document names one (unlike storage/testing, which `research.md` already resolved). **FastAPI** is used below — a routine implementation choice (pairs naturally with the Pydantic-shaped JSON contracts already defined, and with `pytest` per `research.md` §2), not a domain-specific figure, so it doesn't warrant an `issue/` entry the way FR-011/FR-024 did.

Two items remain genuinely open from `spec.md`/`plan.md` and are called out inline below rather than blocking: the CSM assimilation trigger (FR-011) and the low-confidence numeric threshold (FR-024). Both are implemented as configurable/gated rather than hard-coded, so MVP delivery isn't blocked on a business-policy decision.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project skeleton per `plan.md` Project Structure: `crop-insurance/code/evidence_intelligence/{api,ingestion,models,causation,packaging,store}/` and `crop-insurance/code/tests/{contract,integration,unit}/`, each with `__init__.py`
- [X] T002 Initialize Python 3.11 project in `crop-insurance/code/pyproject.toml` with dependencies: `earthengine-api`, `fastapi`, `uvicorn`, `sqlalchemy`, `psycopg2`/`asyncpg`, `scikit-learn`, `reportlab`, `folium`, `matplotlib`, `pytest` (per `research.md`)
- [X] T003 [P] Configure linting/formatting (ruff, black) in `crop-insurance/code/pyproject.toml`
- [X] T004 [P] Add local dev PostgreSQL+PostGIS via `crop-insurance/code/docker-compose.yml` (per `research.md` §1)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Implement database schema for all five `data-model.md` entities (`evidence_requests`, `satellite_analysis_results`, `model_component_results`, `weather_correlation_results`, `evidence_packages`) as SQLAlchemy models + Alembic migration in `crop-insurance/code/evidence_intelligence/store/schema.py`
- [X] T006 [P] Implement `EvidenceStore` persistence layer (create/read/update for all five entities, enforcing the non-null provenance fields from `data-model.md`) in `crop-insurance/code/evidence_intelligence/store/evidence_store.py`
- [X] T007 [P] Implement shared GEE client wrapper (auth via `GEE_SERVICE_ACCOUNT_CREDENTIALS`, query helpers) in `crop-insurance/code/evidence_intelligence/ingestion/gee_client.py`
- [X] T008 Implement FastAPI app skeleton and router registration in `crop-insurance/code/evidence_intelligence/api/__init__.py`
- [X] T009 [P] Implement structured logging and error-handling middleware in `crop-insurance/code/evidence_intelligence/api/middleware.py`
- [X] T010 [P] Implement environment/config loader (`GEE_SERVICE_ACCOUNT_CREDENTIALS`, `DATABASE_URL`, `EVIDENCE_STORE_BUCKET`) in `crop-insurance/code/evidence_intelligence/config.py`

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Generate a Complete Evidence Package for a Reported Loss (Priority: P1) MVP

**Goal**: Given a valid evidence request, run the full pipeline and return a complete, audit-ready evidence package.

**Independent Test**: Submit a request with a geometry/date/peril having available satellite and weather coverage; verify a complete package with damage assessment, yield-loss estimate, causation confidence, and all mandatory admissibility fields is returned (`quickstart.md` Scenario 1).

### Tests for User Story 1

- [X] T011 [P] [US1] Contract test for `POST /evidence-requests` against `contracts/evidence-request-api.md` in `crop-insurance/code/tests/contract/test_evidence_requests_post.py`
- [X] T012 [P] [US1] Contract test for `GET /evidence-requests/{request_id}` (complete-package shape) against `contracts/evidence-request-api.md` in `crop-insurance/code/tests/contract/test_evidence_requests_get.py`
- [X] T013 [P] [US1] Integration test for `quickstart.md` Scenario 1 (submit → poll → complete package, including reproducibility re-run) in `crop-insurance/code/tests/integration/test_complete_package.py`

### Implementation for User Story 1

- [X] T014 [P] [US1] Implement Imagery Ingestion (pre-event 30-day window, post-event 7-15 day window, 5-year historical baseline; phenology/crop-calendar sanity check) in `crop-insurance/code/evidence_intelligence/ingestion/imagery.py` per `Evidence-Flow-Spec.md` §3
- [X] T015 [P] [US1] Implement Weather Correlation Engine (CHIRPS/ERA5-Land/GPM/SMAP query + historical baseline + IMD AWS corroboration) in `crop-insurance/code/evidence_intelligence/ingestion/weather.py` per `Evidence-Flow-Spec.md` §5 steps 1-3
- [X] T016 [P] [US1] Implement Semi-Physical Damage Model (RUE-chain biomass estimate) in `crop-insurance/code/evidence_intelligence/models/semi_physical.py` per `Modeling-Approach.md` §2
- [X] T017 [P] [US1] Implement AI/ML Damage & Yield-Loss Model (RF/DNN over documented feature set, with MAE/RMSE/NRMSE disclosure) in `crop-insurance/code/evidence_intelligence/models/ai_ml.py` per `Modeling-Approach.md` §3
- [X] T018 [US1] Implement Ensemble Blending Engine (weighted by each component's own validation confidence) in `crop-insurance/code/evidence_intelligence/models/ensemble.py` (depends on T016, T017)
- [X] T019 [US1] Implement Damage Severity Index Engine (entropy-weighted, Min-Max normalized) in `crop-insurance/code/evidence_intelligence/models/dsi.py` per `Modeling-Approach.md` §6 (depends on T014, T015)
- [X] T020 [US1] Implement Causation Analysis Engine (temporal/spatial/magnitude/physiological weighted scoring) in `crop-insurance/code/evidence_intelligence/causation/scoring.py` per `Evidence-Flow-Spec.md` §5 (depends on T014, T015)
- [X] T021 [US1] Implement Report/Package Generator (PDF via ReportLab, JSON, GeoTIFF/PNG maps via Folium/Matplotlib, with mandatory §65B fields: source attribution, methodology, accuracy statement, chain of custody, checksum) in `crop-insurance/code/evidence_intelligence/packaging/report_generator.py` per `HLD.md` §6 (depends on T018, T019, T020)
- [X] T022 [US1] Implement `POST /evidence-requests` endpoint (validate input, persist `EvidenceRequest`, return `request_id` synchronously, enqueue pipeline) in `crop-insurance/code/evidence_intelligence/api/routes.py` (depends on T006, T008)
- [X] T023 [US1] Implement `GET /evidence-requests/{request_id}` endpoint (status + completed package retrieval) in `crop-insurance/code/evidence_intelligence/api/routes.py` (depends on T006, T008)
- [X] T024 [US1] Wire end-to-end pipeline orchestration (request → ingestion → models → causation → ensemble/DSI → packaging → store) in `crop-insurance/code/evidence_intelligence/pipeline.py` (depends on T014-T021)
- [X] T025 [US1] Add request validation and `400` error handling per `contracts/evidence-request-api.md` in `crop-insurance/code/evidence_intelligence/api/routes.py` (depends on T022)

**Checkpoint**: User Story 1 fully functional and independently testable — this is the MVP.

---

## Phase 4: User Story 2 - Track Progress of an In-Flight Evidence Request (Priority: P2)

**Goal**: Requesters can retrieve a request ID immediately and check status while the pipeline runs.

**Independent Test**: Submit a request, confirm immediate `request_id` + in-progress status, confirm status reflects progress before completion and the completed package after (`quickstart.md` Scenario 2).

### Tests for User Story 2

- [X] T026 [P] [US2] Contract test confirming `POST /evidence-requests` returns synchronously with `status: IN_PROGRESS` before analysis finishes, in `crop-insurance/code/tests/contract/test_status_immediate.py`
- [X] T027 [P] [US2] Integration test for `quickstart.md` Scenario 2 (poll before and after completion) in `crop-insurance/code/tests/integration/test_status_polling.py`

### Implementation for User Story 2

- [X] T028 [US2] Persist `EvidenceRequest.status` transitions (`RECEIVED` → `IN_PROGRESS` → `COMPLETE`) synchronously at each pipeline stage in `crop-insurance/code/evidence_intelligence/pipeline.py` (depends on T024)
- [X] T029 [US2] Add `estimated_completion` calculation to `GET /evidence-requests/{request_id}` in `crop-insurance/code/evidence_intelligence/api/routes.py` (depends on T023)

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Receive Usable Evidence When Satellite Imagery Is Unavailable (Priority: P3)

**Goal**: When no usable imagery exists, deliver a weather-only preliminary package rather than failing; substitute SAR for flood-compatible perils; handle missing historical baselines without fabricating data.

**Independent Test**: Submit a request for a window with no usable imagery; verify a weather-only preliminary package is delivered and the request stays open for later completion (`quickstart.md` Scenario 3).

### Tests for User Story 3

- [X] T030 [P] [US3] Integration test for `quickstart.md` Scenario 3 (no imagery, non-flood peril → weather-only preliminary, later superseded by complete package) in `crop-insurance/code/tests/integration/test_insufficient_data_fallback.py`
- [X] T031 [P] [US3] Integration test for SAR flood-substitution path (peril=flood or optical unusable) in `crop-insurance/code/tests/integration/test_sar_flood_fallback.py`

### Implementation for User Story 3

- [X] T032 [US3] Implement no-usable-imagery detection and `INSUFFICIENT_DATA` status transition in `crop-insurance/code/evidence_intelligence/ingestion/imagery.py` (depends on T014)
- [X] T033 [US3] Implement Sentinel-1 SAR flood-extent substitution (VV backscatter, <-15dB threshold, >3dB drop) in `crop-insurance/code/evidence_intelligence/ingestion/imagery.py` per `Evidence-Flow-Spec.md` §4 step 3 (depends on T014)
- [X] T034 [US3] Implement weather-only preliminary package generation (`package_tier=WEATHER_ONLY_PRELIMINARY`, retained alongside a later complete package per `data-model.md`) in `crop-insurance/code/evidence_intelligence/packaging/report_generator.py` (depends on T021)
- [X] T035 [US3] Implement backoff-retry and `INSUFFICIENT_DATA` → `COMPLETE` re-queue logic once imagery becomes available in `crop-insurance/code/evidence_intelligence/pipeline.py` (depends on T024, T032)
- [X] T036 [US3] Implement no-historical-baseline fallback (proceed from pre/post comparison alone; explicit "anomaly-vs-history scoring omitted" note in the package, never a fabricated baseline) in `crop-insurance/code/evidence_intelligence/ingestion/imagery.py` and `crop-insurance/code/evidence_intelligence/packaging/report_generator.py` (depends on T014, T021)

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories, plus the two deliberately-deferred spec items

- [X] T037 [P] Unit tests for each model component (semi-physical, AI/ML, ensemble, DSI, causation scoring) in `crop-insurance/code/tests/unit/`
- [X] T038 [P] Implement CSM Assimilation Engine (WOFOST/InfoCrop, Indian-calibrated) in `crop-insurance/code/evidence_intelligence/models/csm_assimilation.py` per `Modeling-Approach.md` §4, gated behind a configurable high-scrutiny trigger defaulting to **disabled** — trigger criteria not yet defined, see `issue/open query - CSM high-scrutiny trigger criteria (FR-011).md`
- [X] T039 [P] Implement low-confidence labeling on `WeatherCorrelationResult.causation_confidence_score` using a configurable threshold (unset by default — package is never auto-rejected regardless) in `crop-insurance/code/evidence_intelligence/causation/scoring.py`, referencing `issue/open query - causation confidence low-confidence threshold (FR-024).md`
- [X] T040 [P] Implement 10-year `retention_expiry_date` calculation and retention-tracking on package creation in `crop-insurance/code/evidence_intelligence/store/evidence_store.py` per Constitution §7
- [X] T041 Run `quickstart.md` end-to-end against a local environment and confirm all three scenarios pass — validated via automated integration tests (tests/integration/) using injected fakes for GEE/weather/IMD, since real credentials/Postgres+PostGIS aren't provisioned in this environment (quickstart.md Prerequisites); app startup and route registration independently verified live via TestClient
- [X] T042 Manual review: confirm no CCE-related field/table exists anywhere in `crop-insurance/code/evidence_intelligence/`, and no endpoint or model accepts a caller-internal schema, per Constitution §4/§5 — grep-verified clean (see completion report)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational; T028/T029 build on the pipeline/endpoint T024/T023 introduced in Phase 3, so in practice follows US1
- **User Story 3 (Phase 5)**: Depends on Foundational; T032-T036 extend imagery/pipeline/packaging modules T014/T021/T024 introduced in Phase 3, so in practice follows US1
- **Polish (Phase 6)**: Depends on all three user stories being complete

### Parallel Opportunities

- T003, T004 (Setup) in parallel
- T006, T007, T009, T010 (Foundational) in parallel once T005/T008 land
- T011-T013 (US1 tests) in parallel; T014-T017 (US1 models/ingestion) in parallel
- T026-T027 (US2 tests) in parallel
- T030-T031 (US3 tests) in parallel
- T037-T040 (Polish) in parallel

---

## Parallel Example: User Story 1

```bash
# Tests together:
Task: "Contract test for POST /evidence-requests in crop-insurance/code/tests/contract/test_evidence_requests_post.py"
Task: "Contract test for GET /evidence-requests/{request_id} in crop-insurance/code/tests/contract/test_evidence_requests_get.py"
Task: "Integration test for quickstart.md Scenario 1 in crop-insurance/code/tests/integration/test_complete_package.py"

# Ingestion + models together:
Task: "Implement Imagery Ingestion in crop-insurance/code/evidence_intelligence/ingestion/imagery.py"
Task: "Implement Weather Correlation Engine in crop-insurance/code/evidence_intelligence/ingestion/weather.py"
Task: "Implement Semi-Physical Damage Model in crop-insurance/code/evidence_intelligence/models/semi_physical.py"
Task: "Implement AI/ML Damage & Yield-Loss Model in crop-insurance/code/evidence_intelligence/models/ai_ml.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup → Phase 2 Foundational (blocking) → Phase 3 US1
2. **STOP and VALIDATE**: run `quickstart.md` Scenario 1 against the deployed service
3. This is the smallest slice that delivers the module's core value (spec.md §Why this priority)

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → validate Scenario 1 → MVP
3. US2 → validate Scenario 2 (adds status-tracking UX on top of US1's pipeline)
4. US3 → validate Scenario 3 (adds resilience on top of US1's pipeline)
5. Polish → CSM tier and low-confidence labeling remain explicitly gated/deferred per the two open issues; everything else hardens what's already working

## Notes

- [P] tasks touch different files with no unmet dependency
- FR-011 (CSM trigger) and FR-024 (confidence threshold) are intentionally not hard-coded anywhere above — see T038/T039 and the two `issue/` files
- Commit after each task or logical group
- Verify tests fail before implementing them (if following TDD)
