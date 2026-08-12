# Phase 1 Data Model: Satellite Evidence Parity Roadmap

**Extends [`001-evidence-generation-pipeline/data-model.md`](../001-evidence-generation-pipeline/data-model.md) — not an independent schema.** Tables/fields not mentioned here are unchanged from `001`. Where this document adds columns to an existing `001` table, the addition is additive and nullable/defaulted so existing `001` rows and code remain valid without migration-time backfill logic beyond a default.

## Extension: SatelliteAnalysisResult (`satellite_analysis_results`)

New columns, added to the table `001` already defines:

| Field | Type | Notes |
|---|---|---|
| `source_class` | enum | `BASELINE` (Sentinel-1/2, Landsat, MODIS — the existing `001` sources) \| `ENHANCED` (higher-resolution optical, commercial SAR, ISRO sovereign sources beyond the `001` baseline) |
| `access_model` | enum | `FREE` \| `COMMERCIAL_TASKED` |
| `considered_not_used` | boolean, default `false` | `true` when a commercial/enhanced source was evaluated for this request but not used (e.g., budget-gated, unauthorized, or unnecessary because a baseline source sufficed) — required so provenance records the *decision*, not just the outcome (spec.md FR-013, Edge Cases) |

**Validation rules**: `source_class` and `access_model` are required on every row, including `considered_not_used = true` rows — a commercial source that was evaluated but skipped still gets a row, not a silent omission (spec.md Edge Cases: "MUST record that a commercial source was considered but not used").

## New: FoundationModelFeatureSet (`foundation_model_feature_sets`)

| Field | Type | Notes |
|---|---|---|
| `feature_set_id` | string, PK | |
| `request_id` | FK → EvidenceRequest | |
| `model_name` | string | e.g. `presto` (research.md §1) |
| `model_version` | string | Pinned per Constitution Principle I |
| `embedding_reference` | structured reference | Points to the stored embedding output, mirroring `model_component_results.component_inputs`'s reference pattern from `001` |
| `status` | enum | `USED` \| `FALLBACK_NOT_USED` — set to `FALLBACK_NOT_USED` when the embedding source was unavailable and Component 2 ran on its existing hand-crafted feature set alone (spec.md FR-008) |

**Validation rules**: A row exists for every request regardless of `status`, so "did we attempt foundation-model augmentation, and did it work" is always answerable from the record, not just inferable from Component 2's feature list. `model_name`/`model_version` are required even on `FALLBACK_NOT_USED` rows (recording which version was *attempted*).

## New: ConfidenceTier — extension of EvidencePackage (`evidence_packages`)

New columns, added to the table `001` already defines:

| Field | Type | Notes |
|---|---|---|
| `confidence_tier` | enum | `HIGH` \| `MEDIUM` \| `LOW` — derived from `model_component_results` (`ENSEMBLE` row, `001`) per research.md §4; never independently overridden |
| `confidence_tier_guidance` | string, nullable | Populated only for `MEDIUM`/`LOW` — plain-language statement of what could improve confidence (spec.md FR-005); `null` for `HIGH` |
| `cce_non_equivalence_statement` | boolean, must be `true` when `confidence_tier = LOW` | Enforces spec.md FR-005/FR-012 at the schema level — a `LOW`-tier package cannot be persisted without this flag set |

**Validation rules**: `confidence_tier` is required on every package, at every tier, including `WEATHER_ONLY_PRELIMINARY` packages inherited from `001` (a preliminary package still gets a tier, typically `LOW`, since it's generated with reduced input availability). `cce_non_equivalence_statement` is enforced `true` whenever `confidence_tier = LOW` — this is spec.md FR-005 written as a data constraint, not just a narrative convention, so it can't be silently dropped by a future code change without the write failing.

## New: CropCalendarCrossCheck (`crop_calendar_cross_checks`)

| Field | Type | Notes |
|---|---|---|
| `check_id` | string, PK | |
| `request_id` | FK → EvidenceRequest | |
| `source_dataset`, `source_version` | string, string | e.g. WorldCereal v2 (research.md §3) |
| `declared_crop_type` | string, nullable | From the claim, if provided at request time |
| `observed_crop_type` | string | Independently derived from the cross-check source |
| `declared_calendar_window`, `observed_calendar_window` | date range, date range, nullable | Sowing/harvest window comparison |
| `discrepancy_flag` | boolean | `true` when declared and observed materially disagree |

**Validation rules**: A row is generated for every request where a declared crop type is available to compare against (spec.md User Story 4); `discrepancy_flag` is a first-class, always-computed field — the module MUST NOT silently reconcile a mismatch into the observed value (spec.md FR-010).

## New: SupplementaryEvidenceAttachment (`supplementary_evidence_attachments`)

| Field | Type | Notes |
|---|---|---|
| `attachment_id` | string, PK | |
| `request_id` | FK → EvidenceRequest | |
| `attachment_type` | enum | `PHOTO` \| `OTHER` |
| `uri` | string | Object storage reference |
| `submitted_at` | timestamp | |
| `caller_supplied_metadata` | opaque JSON, nullable | Never validated or interpreted against any specific channel's schema — mirrors `external_reference_id`'s opacity in `001`'s `EvidenceRequest` (Constitution §5) |

**Validation rules**: Attachable to a request at any confidence tier, but only surfaced as tier-improvement guidance for `MEDIUM`/`LOW` packages (`evidence_packages.confidence_tier_guidance`). The module never requires this table to be populated — it exists purely as an optional channel-agnostic input (spec.md FR-006).

## Entity Relationships (additions to `001`'s diagram)

```
EvidenceRequest (1) ──< (0..*) FoundationModelFeatureSet        [one attempt per request; USED or FALLBACK_NOT_USED]
EvidenceRequest (1) ──< (0..1) CropCalendarCrossCheck            [only when a declared crop type exists to compare]
EvidenceRequest (1) ──< (0..*) SupplementaryEvidenceAttachment   [optional, channel-agnostic, any confidence tier]
EvidencePackage  (1) ── confidence_tier, confidence_tier_guidance, cce_non_equivalence_statement   [new columns, not a new table]
SatelliteAnalysisResult (1) ── source_class, access_model, considered_not_used                     [new columns, not a new table]
```

No entity added or extended here references CCE data, and no new table leaves this module's own schema to reference another initiative's tables (Constitution §4/§5) — same boundary `001`'s data model already enforces, unchanged by this extension.
