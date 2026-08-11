# Contract: Evidence Request Interface

The sole external interface this module exposes (Constitution §5, HLD §5). Every caller — voice-agent system, web portal, CSC workflow, insurer's own claims system — integrates through this contract and no other; there is no privileged caller and no caller-specific variant.

## POST /evidence-requests

Submit a new evidence request. Returns immediately (FR-003) — does not block until analysis completes.

**Request body**:
```json
{
  "geometry": { "type": "Polygon", "coordinates": [ ... ] },
  "event_date": "2026-08-08",
  "peril_type": "hailstorm",
  "external_reference_id": "opaque-caller-key (optional)"
}
```

| Field | Required | Notes |
|---|---|---|
| `geometry` | Yes | GeoJSON `Polygon` or `Point` — the field boundary or representative point |
| `event_date` | Yes | ISO 8601 date — the claimed/reported event date |
| `peril_type` | Yes | One of the fixed enum in `data-model.md` (`EvidenceRequest.peril_type`) |
| `external_reference_id` | No | Opaque string; never validated, interpreted, or required to match any schema (FR-002) |

**Response — `202 Accepted`**:
```json
{
  "request_id": "EIM-2026-0810-000472",
  "status": "IN_PROGRESS",
  "estimated_completion": "2026-08-10T18:00:00+05:30"
}
```

**Response — `400 Bad Request`**: `geometry`, `event_date`, or `peril_type` missing or malformed. Body: `{ "error": "...", "field": "..." }`.

**This endpoint never returns a caller-specific error shape or requires a caller-specific auth scheme beyond whatever generic access control the deployment adds** — the contract itself has no notion of "which system is calling" (Constitution §5).

## GET /evidence-requests/{request_id}

Retrieve current status, or the completed package once ready (FR-004, User Story 2).

**Response — `200 OK`, in progress**:
```json
{
  "request_id": "EIM-2026-0810-000472",
  "status": "IN_PROGRESS",
  "estimated_completion": "2026-08-10T18:00:00+05:30"
}
```

**Response — `200 OK`, complete**:
```json
{
  "request_id": "EIM-2026-0810-000472",
  "status": "COMPLETE",
  "package": {
    "pdf_uri": "...",
    "json_uri": "...",
    "map_uris": ["..."],
    "methodology_version": "v1.2.0",
    "causation_confidence_score": 94
  }
}
```

**Response — `200 OK`, insufficient data (weather-only preliminary delivered)**:
```json
{
  "request_id": "EIM-2026-0810-000472",
  "status": "INSUFFICIENT_DATA",
  "package": {
    "pdf_uri": "...",
    "json_uri": "...",
    "map_uris": [],
    "methodology_version": "v1.2.0",
    "note": "Weather-only preliminary package — satellite imagery unavailable at time of generation; will be superseded by a complete package once imagery is available."
  }
}
```
Per `data-model.md`, this preliminary package is retained even after a later `COMPLETE` package is generated for the same request — a second `GET` after supersession returns the `COMPLETE` package as current, but the preliminary one remains independently retrievable by its own `package_id` for audit purposes.

**Response — `404 Not Found`**: `request_id` does not exist.

**Status polling and/or a webhook callback are both acceptable integration patterns** (HLD §5) — this contract defines the polling shape; a webhook, if a deployment adds one, delivers the same `package` object shown above as its payload rather than a different shape.

## Notes for implementers

- No endpoint in this contract accepts or returns a caller's internal claim ID, farmer ID, or policy schema — only `external_reference_id`, opaque (FR-002).
- No endpoint in this contract reads from or writes to CCE data of any kind (Constitution §4).
- This module never initiates a request — every row in `evidence_requests` originates from a `POST` here; there is no scheduled/proactive trigger anywhere in this contract (Constitution §3, FR-027).
