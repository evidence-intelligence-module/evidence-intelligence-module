# Contract Extension: Evidence Request Interface

**Extends [`001-evidence-generation-pipeline/contracts/evidence-request-api.md`](../../001-evidence-generation-pipeline/contracts/evidence-request-api.md) — not a new interface.** Every endpoint from `001`'s contract is unchanged; this document only adds new response fields to the existing `GET /evidence-requests/{request_id}` payload and one new endpoint. Same rule applies: no caller-specific variant, no privileged caller (Constitution §5) — this extension is exercised identically regardless of which system submitted the original request.

## Extension: `GET /evidence-requests/{request_id}` response

The `package` object in the `COMPLETE` and `INSUFFICIENT_DATA` responses (`001` contract) gains these fields:

```json
{
  "request_id": "EIM-2026-0810-000472",
  "status": "COMPLETE",
  "package": {
    "pdf_uri": "...",
    "json_uri": "...",
    "map_uris": ["..."],
    "methodology_version": "v1.2.0",
    "causation_confidence_score": 94,
    "confidence_tier": "HIGH",
    "confidence_tier_guidance": null,
    "sources_used": [
      { "name": "Sentinel-1 SAR", "source_class": "BASELINE", "access_model": "FREE" },
      { "name": "Resourcesat-2A LISS-4", "source_class": "ENHANCED", "access_model": "FREE" }
    ],
    "sources_considered_not_used": [],
    "foundation_model_features": { "model_name": "presto", "model_version": "v1.0", "status": "USED" },
    "crop_calendar_cross_check": { "discrepancy_flag": false },
    "red_edge_index": { "type": "NDRE", "value": 0.42 },
    "thermal_stress_signal": null
  }
}
```

**Drought/heatwave example** (`peril_type: "drought"`, ECOSTRESS pass available):

```json
{
  "package": {
    "red_edge_index": { "type": "NDRE", "value": 0.18 },
    "thermal_stress_signal": {
      "source_dataset": "ECOSTRESS L2 LSTE",
      "deviation_from_baseline_celsius": 4.7,
      "pass_available": true
    }
  }
}
```

**Low-confidence example** (`confidence_tier: "LOW"`):

```json
{
  "package": {
    "confidence_tier": "LOW",
    "confidence_tier_guidance": "Confidence limited by persistent cloud cover and no available enhanced-resolution source for this field. Supplementary evidence (e.g., a geotagged photo) may improve confidence if available. This package is not equivalent to a Crop Cutting Experiment (CCE)-based ground-truth determination.",
    "cce_non_equivalence_statement": true
  }
}
```

| New field | Notes |
|---|---|
| `confidence_tier` | `HIGH` \| `MEDIUM` \| `LOW` — always present, every tier, every package including `WEATHER_ONLY_PRELIMINARY` (data-model.md) |
| `confidence_tier_guidance` | `null` for `HIGH`; plain-language text for `MEDIUM`/`LOW` (spec.md FR-005) |
| `sources_used` / `sources_considered_not_used` | Full provenance list, including commercial sources evaluated but not used (spec.md FR-013) |
| `foundation_model_features` | `status: "USED"` or `"FALLBACK_NOT_USED"` — always present (spec.md FR-007/FR-008) |
| `crop_calendar_cross_check` | Present only when a declared crop type existed to compare against (data-model.md) |
| `red_edge_index` | `null` when Sentinel-2 red-edge bands were unavailable; otherwise names the specific index used (never a generic/undisclosed value) — spec.md FR-015 |
| `thermal_stress_signal` | `null` for non-drought/heatwave peril types, or when no ECOSTRESS pass was available within the analysis window (`pass_available: false` case is recorded internally per data-model.md but surfaced here simply as `null` — the reviewer doesn't need to distinguish "not applicable" from "not available" at the API layer) — spec.md FR-016/FR-017 |

**This is a strictly additive change** — a caller written against `001`'s contract alone continues to work unmodified; these are new fields on the same response shape, not a new response shape.

## New: `POST /evidence-requests/{request_id}/supplementary-evidence`

Attach optional, channel-agnostic supplementary evidence (e.g., a geotagged photo) to an existing request (spec.md FR-006, User Story 2).

**Request body**:
```json
{
  "attachment_type": "PHOTO",
  "uri": "s3://.../submitted-photo.jpg",
  "caller_supplied_metadata": { "any": "opaque JSON, never validated or interpreted" }
}
```

| Field | Required | Notes |
|---|---|---|
| `attachment_type` | Yes | `PHOTO` \| `OTHER` |
| `uri` | Yes | Reference to the already-stored evidence object; this endpoint does not accept raw file uploads |
| `caller_supplied_metadata` | No | Opaque, exactly like `external_reference_id` in `001`'s `POST /evidence-requests` — never validated against any specific channel's schema (Constitution §5) |

**Response — `201 Created`**:
```json
{
  "attachment_id": "SEA-2026-0810-000091",
  "request_id": "EIM-2026-0810-000472",
  "status": "ATTACHED"
}
```

**Response — `404 Not Found`**: `request_id` does not exist.

**Response — `400 Bad Request`**: `attachment_type` or `uri` missing/malformed.

**This endpoint accepts an attachment at any confidence tier and at any request status** — it does not require the request to be `INSUFFICIENT_DATA` or `LOW`-tier, since a caller may reasonably submit supplementary evidence proactively. It does not trigger re-processing on its own; if a deployment wants attaching evidence to trigger re-evaluation, that is a separate, not-yet-specified capability, not implied by this endpoint.

## Notes for implementers

- No field or endpoint in this extension accepts or returns a caller's internal claim ID, farmer ID, or policy schema — matching `001`'s existing boundary.
- No field or endpoint in this extension reads from or writes to CCE data of any kind (Constitution §4) — `crop_calendar_cross_check` compares against an open crop-type mapping product (WorldCereal, research.md §3), never CCE.
- `sources_considered_not_used` existing as an empty array is a valid, common response (most requests won't need to consider a commercial source) — its presence is mandatory, not its non-emptiness.
