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

## New: ThermalStressSignal (`thermal_stress_signals`)

| Field | Type | Notes |
|---|---|---|
| `signal_id` | string, PK | |
| `request_id` | FK → EvidenceRequest | |
| `source_dataset`, `source_version` | string, string | e.g. ECOSTRESS L2 LSTE, collection version (research.md §6.2) |
| `land_surface_temperature`, `historical_baseline`, `deviation` | float, float, float | Canopy-temperature deviation from the field's own historical baseline, mirroring the deviation-from-baseline pattern `WeatherCorrelationResult` (`001`) and the DSI (`Modeling-Approach.md` §6) already use |
| `overpass_local_solar_time` | time, nullable | **Added 2026-08-13 (spec.md FR-023).** Local solar time of the acquisition. Required for the deviation above to mean anything: land surface temperature swings through the day, and ECOSTRESS is deliberately non-sun-synchronous (that irregular sampling is the point of the mission), so a deviation taken against a baseline observed at a different time of day measures the diurnal cycle rather than crop stress. `null` only where `pass_available = false` |
| `baseline_overpass_window` | string, nullable | The local-solar-time window the `historical_baseline` was drawn from, so a reader can check that observation and baseline are time-comparable rather than having to assume it |
| `pass_available` | boolean | `false` when no usable ECOSTRESS pass existed within the analysis window — row still persisted so "we checked and none was available" is distinguishable from "we never checked" |

**Validation rules**: A row is generated for every `drought`/`heatwave` peril-type request (spec.md FR-016) — `pass_available = false` rows carry null measurement fields but non-null provenance fields, so the attempt itself is always auditable. Never generated for other peril types (scope per FR-016). Where `pass_available = true`, `overpass_local_solar_time` is required, and `deviation` MUST be computed only against baseline observations within `baseline_overpass_window` (spec.md FR-023).

**Known spatial constraint, disclosed rather than designed around**: ECOSTRESS resolves to ~70 m, so one pixel covers roughly 0.49 ha against the ~0.16 ha median Indian field size this roadmap targets elsewhere (`research.md` §2) — a worse mixed-pixel ratio than the 10–30 m problem User Story 1 exists to address. The signal is therefore a field-neighbourhood measurement, not a per-field one, and packages MUST present it as such. A relative anomaly against surrounding pixels carries more information here than an absolute per-field temperature, since the mixing affects observation and baseline alike.

## Extension: DamageAssessmentComponentResult (`model_component_results`) — red-edge disclosure

New column, added to the table `001` already defines:

| Field | Type | Notes |
|---|---|---|
| `red_edge_index_type`, `red_edge_index_value` | string, float | Nullable — populated on the `AI_ML` component row whenever Sentinel-2 red-edge bands were available (spec.md FR-015); `red_edge_index_type` names the specific index used (e.g. `NDRE`), never left as a generic unnamed value |

**Validation rules**: When populated, `red_edge_index_type` must name a specific, disclosed index — mirrors the same "no generic/undisclosed feature" discipline `001`'s `component_inputs` field already enforces.

## Entity Relationships (additions to `001`'s diagram)

```
EvidenceRequest (1) ──< (0..*) FoundationModelFeatureSet        [one attempt per request; USED or FALLBACK_NOT_USED]
EvidenceRequest (1) ──< (0..1) CropCalendarCrossCheck            [only when a declared crop type exists to compare]
EvidenceRequest (1) ──< (0..*) SupplementaryEvidenceAttachment   [optional, channel-agnostic, any confidence tier]
EvidenceRequest (1) ──< (0..1) ThermalStressSignal               [only for drought/heatwave peril_type; pass_available may be false]
EvidencePackage  (1) ── confidence_tier, confidence_tier_guidance, cce_non_equivalence_statement   [new columns, not a new table]
SatelliteAnalysisResult (1) ── source_class, access_model, considered_not_used                     [new columns, not a new table]
DamageAssessmentComponentResult (1) ── red_edge_index_type, red_edge_index_value                   [new columns on AI_ML row, not a new table]
```

No entity added or extended here references CCE data, and no new table leaves this module's own schema to reference another initiative's tables (Constitution §4/§5) — same boundary `001`'s data model already enforces, unchanged by this extension.
