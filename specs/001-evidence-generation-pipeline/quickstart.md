# Quickstart: Validating the Evidence Generation Pipeline

Runnable validation scenarios proving the feature works end-to-end, one per user story in `spec.md`. Full request/response shapes are in `contracts/evidence-request-api.md`; full schema is in `data-model.md` — not repeated here.

## Prerequisites

- Python 3.11
- A Google Earth Engine service account with API access (satellite/weather ingestion depends on it — HLD §7)
- PostgreSQL with the PostGIS extension, reachable via connection string (`research.md` §1)
- Object storage (S3-compatible) reachable for package/imagery-derivative storage (HLD §7)
- `pytest` installed (`research.md` §2)

## Setup

```bash
pip install -e .
export GEE_SERVICE_ACCOUNT_CREDENTIALS=/path/to/credentials.json
export DATABASE_URL=postgresql://.../evidence_intelligence
export EVIDENCE_STORE_BUCKET=s3://...
# Apply schema from data-model.md (migration tooling is an implementation-phase decision, not fixed here)
alembic upgrade head   # or equivalent, once the migration tool is chosen in tasks.md
uvicorn evidence_intelligence.api:app --reload
```

## Scenario 1 — Generate a Complete Evidence Package (User Story 1, P1)

**Goal**: prove the full pipeline runs end-to-end for a normal case (imagery and weather both available).

1. `POST /evidence-requests` with a known geometry, an `event_date` with available Sentinel-2 coverage, and `peril_type: "hailstorm"` (contracts/evidence-request-api.md).
2. **Expect**: `202 Accepted` with a `request_id` and `status: "IN_PROGRESS"`, returned without waiting for analysis (FR-003).
3. Poll `GET /evidence-requests/{request_id}` until `status: "COMPLETE"`.
4. **Expect**: response includes a `package` with `pdf_uri`, `json_uri`, `map_uris`, a `methodology_version`, and a `causation_confidence_score`.
5. Inspect the underlying rows (`data-model.md`): confirm `SEMI_PHYSICAL` and `AI_ML` rows exist in `model_component_results`, an `ENSEMBLE` row and a `DSI` row were derived from them, and a `weather_correlation_results` row has a `causation_confidence_score` between 0–100.
6. **Expect**: every `satellite_analysis_results` and `weather_correlation_results` row has non-null `source_dataset`/`source_version`/`acquisition_date` (FR-017) — spot-check this before calling the scenario passed.
7. Re-submit the identical request. **Expect**: an identical result, given the methodology version hasn't changed (FR-021, SC-005).

## Scenario 2 — Track an In-Flight Request (User Story 2, P2)

**Goal**: prove status tracking works independently of full completion.

1. `POST /evidence-requests` as in Scenario 1.
2. Immediately `GET /evidence-requests/{request_id}` (before analysis would plausibly finish).
3. **Expect**: `status: "IN_PROGRESS"`, not an error and not a stale/missing response (FR-004, SC-001).
4. Poll again after completion. **Expect**: `status: "COMPLETE"` with the full `package`.

## Scenario 3 — Graceful Degradation When Imagery Is Unavailable (User Story 3, P3)

**Goal**: prove the module never fails silently when satellite imagery can't be acquired.

1. `POST /evidence-requests` with a geometry/`event_date` window known to have no usable optical imagery and `peril_type` set to something **not** flood-compatible (e.g. `"drought"`), so SAR does not substitute.
2. Poll until settled.
3. **Expect**: `status: "INSUFFICIENT_DATA"`, with a `package` present (`package_tier: WEATHER_ONLY_PRELIMINARY` in `data-model.md`) rather than a `4xx`/`5xx` failure or an empty response (FR-022, SC-007).
4. Confirm in `evidence_packages` that the preliminary package row is retained (not deleted) once imagery later becomes available and a second, `COMPLETE`-tier package row is generated for the same `request_id` (`data-model.md` — Multiple packages per request).

## Automated test mapping

| Scenario above | Test location (plan.md project structure) |
|---|---|
| 1 | `tests/integration/` (full pipeline) + `tests/contract/` (API shape against `contracts/evidence-request-api.md`) |
| 2 | `tests/contract/` (status endpoint shape) |
| 3 | `tests/integration/` (fallback path) |
| Individual component correctness (semi-physical, AI/ML, ensemble, DSI, causation scoring) | `tests/unit/`, per component — not covered by the scenarios above, which are end-to-end |

Full task breakdown for building these belongs to `/speckit-tasks`, not this document.
