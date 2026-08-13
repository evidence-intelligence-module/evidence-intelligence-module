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
      { "name": "Sentinel-1 SAR", "source_class": "BASELINE" },
      { "name": "Resourcesat-2A LISS-4", "source_class": "ENHANCED" }
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
| `sources_used` / `sources_considered_not_used` | Full provenance list, including enhanced sources evaluated but not used (spec.md FR-013). The `access_model` field was removed 2026-08-13 with the commercial tier (`constitution.md` §9.2) — every source is free or sovereign |
| `foundation_model_features` | `status: "USED"` or `"FALLBACK_NOT_USED"` — always present (spec.md FR-007/FR-008) |
| `crop_calendar_cross_check` | Present only when a declared crop type existed to compare against (data-model.md). `outcome` is `CONSISTENT` \| `INCONCLUSIVE` \| `DISCREPANT` — **not a boolean.** `INCONCLUSIVE` covers "the reference product has no class for this field" and "too few pure pixels to judge", which a boolean flag could only have represented as a mismatch. A `DISCREPANT` outcome MUST carry `reference_accuracy`, `pure_pixel_count`, and the not-a-fraud-determination note |
| `red_edge_index` | `null` when Sentinel-2 red-edge bands were unavailable; otherwise names the specific index used (never a generic/undisclosed value) — spec.md FR-015 |
| `thermal_stress_signal` | `null` **only** for non-drought/heatwave peril types, where a thermal signal was never applicable. Where it *was* applicable but no ECOSTRESS pass fell in the window, the object is present with `"pass_available": false` and null measurements — "we looked and there was nothing" is a different statement from "this doesn't apply", and `data-model.md` persists that distinction precisely so it can be read back. An earlier version of this contract surfaced both as `null` on the grounds that a reviewer needn't distinguish them; that traded away an auditable fact for a marginal simplification, against Constitution Principle I/II. When present with `pass_available: true`, `overpass_local_solar_time` and `baseline_overpass_window` are required alongside the deviation (spec.md FR-023) |
| `package_version` / `package_status` / `supersedes_package_id` | Lineage for regenerated packages (data-model.md, `tasks.md` T0-16). `package_status` is `CURRENT` \| `SUPERSEDED`; this endpoint always returns the `CURRENT` one. A superseded package is never deleted or mutated and stays retrievable by its own `package_id` — it was issued as a §65B artifact and may already have been acted on |

**This is a strictly additive change** — a caller written against `001`'s contract alone continues to work unmodified; these are new fields on the same response shape, not a new response shape.

## ~~New: `POST /evidence-requests/{request_id}/supplementary-evidence`~~ — removed 2026-08-13

Out of scope per `constitution.md` §9.1 (data minimisation), with spec.md FR-006. A geotagged photograph is personal data about an identifiable individual, arriving from outside, into a store with a ten-year retention floor. The earlier fix — dropping `caller_supplied_metadata` — bounded what could arrive through the field; the boundary closes the surface entirely.

## ~~New: `POST /evidence-requests/{request_id}/outcome`~~ — removed 2026-08-13

Out of scope per `constitution.md` §9.2 (training-label sourcing) and §9.1, with spec.md FR-024 and `tasks.md` `TV-01`. Labeled data arrives from an external supplier; the module does not capture, store, or export it.

The `assessment_source` allowlist on this endpoint was the Constitution §4 gate, refusing `CCE_DERIVED` figures at ingress. With no ingress, that gate has nothing to guard. Its purpose survives in a weaker but honest form: `label_provenance` on the saved model artifact, recording what a supplier *declared* about their labels' origin — a declaration the module cannot verify and does not claim to.

**The request surface is therefore unchanged from `001`'s**: `geometry`, `event_date`, `peril_type`, `external_reference_id`. This extension adds response fields only.

## Notes for implementers

- No field or endpoint in this extension accepts or returns a caller's internal claim ID, farmer ID, or policy schema — matching `001`'s existing boundary.
- No field or endpoint in this extension reads from or writes to CCE data of any kind (Constitution §4) — `crop_calendar_cross_check` compares against an open crop-type mapping product (WorldCereal, research.md §3), never CCE.
- `sources_considered_not_used` existing as an empty array is a valid, common response — its presence is mandatory, not its non-emptiness. Since 2026-08-13 it records only free and sovereign enhanced sources: a Bhoonidhi LISS-4 scene evaluated and skipped because the baseline sufficed is a real entry, whereas the commercial tier that would previously have populated it no longer exists (`constitution.md` §9.2).
- **On "strictly additive"**: the claim above is about `001`'s contract, and it still holds — a caller written against `001` alone is unaffected by everything here. Within this extension, the supplementary-evidence and outcome endpoints were removed entirely, `access_model` was dropped, and `crop_calendar_cross_check.discrepancy_flag` became a three-state `outcome`, all on 2026-08-13. Neither had shipped, so no caller existed to break; both are recorded rather than silently swapped so that anyone who read an earlier draft knows the shape changed and why.

## Changelog

| Date | Change |
|---|---|
| 2026-08-13 | Removed `caller_supplied_metadata` (personal-data ingress with no reader). Constrained `uri` and asserted non-dereference. `discrepancy_flag` boolean → three-state `outcome` with mandatory framing fields. Added package lineage (`package_version`, `package_status`, `supersedes_package_id`). Added `overpass_local_solar_time`/`baseline_overpass_window` to the thermal signal. `thermal_stress_signal` now distinguishes "not applicable" (`null`) from "checked, unavailable" (`pass_available: false`). Added `POST /evidence-requests/{request_id}/outcome` |
| 2026-08-13 | Removed `POST .../supplementary-evidence` and `POST .../outcome` entirely, and dropped `access_model`, per `constitution.md` §9. The request surface returns to `001`'s four fields; this extension is response-only |
