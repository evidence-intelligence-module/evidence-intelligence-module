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
    "package_version": 1,
    "package_status": "CURRENT",
    "supersedes_package_id": null,
    "causation_confidence_score": 94,
    "confidence_tier": "HIGH",
    "confidence_tier_guidance": null,
    "sources_used": [
      { "name": "Sentinel-1 SAR", "source_class": "BASELINE", "access_model": "FREE" },
      { "name": "Resourcesat-2A LISS-4", "source_class": "ENHANCED", "access_model": "FREE" }
    ],
    "sources_considered_not_used": [],
    "foundation_model_features": { "model_name": "presto", "model_version": "v1.0", "status": "USED" },
    "crop_calendar_cross_check": {
      "outcome": "CONSISTENT",
      "source_dataset": "WorldCereal",
      "source_version": "v2"
    },
    "red_edge_index": { "type": "NDRE", "value": 0.42 },
    "thermal_stress_signal": null
  }
}
```

**Superseded package example** — a request re-processed once imagery became available (`001`'s `retry_insufficient_data`). The earlier package remains retrievable by its own `package_id`; this endpoint returns the current one:

```json
{
  "package": {
    "package_version": 2,
    "package_status": "CURRENT",
    "supersedes_package_id": "PKG-2026-0810-000133",
    "confidence_tier": "HIGH"
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
      "overpass_local_solar_time": "13:42",
      "baseline_overpass_window": "12:00-15:00",
      "pass_available": true
    }
  }
}
```

**Crop-type discrepancy example** — the framing fields below are mandatory whenever `outcome` is `DISCREPANT`, never optional:

```json
{
  "package": {
    "crop_calendar_cross_check": {
      "outcome": "DISCREPANT",
      "declared_crop_type": "wheat",
      "observed_crop_type": "rice",
      "source_dataset": "WorldCereal",
      "source_version": "v2",
      "reference_accuracy": 0.79,
      "pure_pixel_count": 14,
      "note": "This is a data-consistency observation, not a fraud determination. It did not alter the damage estimate in this package."
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
| `crop_calendar_cross_check` | Present only when a declared crop type existed to compare against (data-model.md). `outcome` is `CONSISTENT` \| `INCONCLUSIVE` \| `DISCREPANT` — **not a boolean.** `INCONCLUSIVE` covers "the reference product has no class for this field" and "too few pure pixels to judge", which a boolean flag could only have represented as a mismatch. A `DISCREPANT` outcome MUST carry `reference_accuracy`, `pure_pixel_count`, and the not-a-fraud-determination note |
| `red_edge_index` | `null` when Sentinel-2 red-edge bands were unavailable; otherwise names the specific index used (never a generic/undisclosed value) — spec.md FR-015 |
| `thermal_stress_signal` | `null` **only** for non-drought/heatwave peril types, where a thermal signal was never applicable. Where it *was* applicable but no ECOSTRESS pass fell in the window, the object is present with `"pass_available": false` and null measurements — "we looked and there was nothing" is a different statement from "this doesn't apply", and `data-model.md` persists that distinction precisely so it can be read back. An earlier version of this contract surfaced both as `null` on the grounds that a reviewer needn't distinguish them; that traded away an auditable fact for a marginal simplification, against Constitution Principle I/II. When present with `pass_available: true`, `overpass_local_solar_time` and `baseline_overpass_window` are required alongside the deviation (spec.md FR-023) |
| `package_version` / `package_status` / `supersedes_package_id` | Lineage for regenerated packages (data-model.md, `tasks.md` T0-16). `package_status` is `CURRENT` \| `SUPERSEDED`; this endpoint always returns the `CURRENT` one. A superseded package is never deleted or mutated and stays retrievable by its own `package_id` — it was issued as a §65B artifact and may already have been acted on |

**This is a strictly additive change** — a caller written against `001`'s contract alone continues to work unmodified; these are new fields on the same response shape, not a new response shape.

## New: `POST /evidence-requests/{request_id}/supplementary-evidence`

Attach optional, channel-agnostic supplementary evidence (e.g., a geotagged photo) to an existing request (spec.md FR-006, User Story 2).

**Request body**:
```json
{
  "attachment_type": "PHOTO",
  "uri": "s3://evidence-store/.../submitted-photo.jpg"
}
```

| Field | Required | Notes |
|---|---|---|
| `attachment_type` | Yes | `PHOTO` \| `OTHER` |
| `uri` | Yes | Reference to the already-stored evidence object; this endpoint does not accept raw file uploads. Restricted to the module's own object store or a configured allowlist, and **never dereferenced by the module** — an unconstrained caller-supplied URI that anything downstream fetches is a server-side request forgery vector and a route to reading objects the caller cannot otherwise reach through this service |

**`caller_supplied_metadata` was removed 2026-08-13** ([`issue/open query - personal data in caller-supplied attachment metadata (FR-006).md`](../issue/open%20query%20-%20personal%20data%20in%20caller-supplied%20attachment%20metadata%20%28FR-006%29.md)). It was an unvalidated opaque JSON field that nothing in this design read — a write-only personal-data ingress into a store with a ten-year retention floor, which callers would predictably have filled with farmer identifiers, importing exactly the data Constitution §5's boundary exists to keep out. `external_reference_id` on the original request already covers the legitimate correlation need with the same opacity and a bounded shape. Removing a field with no reader costs no capability, which is why this needed no trade-off decision.

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

## New: `POST /evidence-requests/{request_id}/outcome`

Record what actually happened to the claim this request produced evidence for (`tasks.md` `TV-01`). Added 2026-08-13.

**Why this exists**: every evidence package eventually pairs with a settled claim, and that pairing is the only training and calibration data this module will ever get for free. Without this endpoint the module generates evidence and discards it — so the label question stays permanently open, and the Pilot & Validation phase (`documents/README.md` §8) would run against real claims and keep none of the labels it generates.

**Request body**:
```json
{
  "outcome": "UPHELD",
  "assessed_loss_fraction": 0.42,
  "recorded_at": "2026-11-04"
}
```

| Field | Required | Notes |
|---|---|---|
| `outcome` | Yes | `UPHELD` \| `PARTIALLY_UPHELD` \| `REJECTED` \| `WITHDRAWN` \| `UNKNOWN`. A small closed enum — deliberately not the caller's own claim-status vocabulary |
| `assessed_loss_fraction` | No | The independently assessed loss in [0,1], where the caller has one. This is the damage-magnitude label Component 2 needs; the enum above is the coarser signal that calibrates confidence tiers and the causation threshold |
| `recorded_at` | No | When the outcome was determined. Defaults to receipt time |

**Response — `201 Created`**, `404` for an unknown `request_id`, `400` for an outcome outside the enum.

**Constraints this endpoint holds to**:

- **No caller schema, no personal data** (Constitution §5, and the same minimal-PII posture as the attachment endpoint above). It accepts a closed enum and a number — never a claim ID, policy field, surveyor identity, or farmer identifier. A caller correlates via `external_reference_id` on the original request, as everywhere else.
- **It does not alter any issued package.** Recording an outcome never re-runs the pipeline, never changes a `confidence_tier`, and never supersedes a package. It is write-only observation, kept strictly separate from evidence generation so that recording what happened cannot retroactively shape what the module said would happen.
- **It carries no CCE data** (Constitution §4). `assessed_loss_fraction` is whatever the caller independently assessed; whether *CCE-derived* outcomes may be supplied here is the open question in [`001`'s label query](../../001-evidence-generation-pipeline/issue/open%20query%20-%20AI-ML%20training%20data%20source%20and%20CCE-label%20question.md) and is **not** decided by this contract. The endpoint's existence does not presume that answer — it works identically for pilot-survey and insurer-assessed outcomes.

## Notes for implementers

- No field or endpoint in this extension accepts or returns a caller's internal claim ID, farmer ID, or policy schema — matching `001`'s existing boundary.
- No field or endpoint in this extension reads from or writes to CCE data of any kind (Constitution §4) — `crop_calendar_cross_check` compares against an open crop-type mapping product (WorldCereal, research.md §3), never CCE.
- `sources_considered_not_used` existing as an empty array is a valid, common response (most requests won't need to consider a commercial source) — its presence is mandatory, not its non-emptiness. Note that with commercial tasking disabled by configuration (FR-019) it is *always* empty, which records nothing; the useful record in that state is the policy itself ("commercial tier disabled by configuration"), not a per-request empty list.
- **On "strictly additive"**: the claim above is about `001`'s contract, and it still holds — a caller written against `001` alone is unaffected by everything here. Within this extension, `caller_supplied_metadata` was removed and `crop_calendar_cross_check.discrepancy_flag` became a three-state `outcome` on 2026-08-13. Neither had shipped, so no caller existed to break; both are recorded rather than silently swapped so that anyone who read an earlier draft knows the shape changed and why.

## Changelog

| Date | Change |
|---|---|
| 2026-08-13 | Removed `caller_supplied_metadata` (personal-data ingress with no reader). Constrained `uri` and asserted non-dereference. `discrepancy_flag` boolean → three-state `outcome` with mandatory framing fields. Added package lineage (`package_version`, `package_status`, `supersedes_package_id`). Added `overpass_local_solar_time`/`baseline_overpass_window` to the thermal signal. `thermal_stress_signal` now distinguishes "not applicable" (`null`) from "checked, unavailable" (`pass_available: false`). Added `POST /evidence-requests/{request_id}/outcome` |
