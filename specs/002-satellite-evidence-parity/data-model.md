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
| `supersedes_package_id` | FK → EvidencePackage, nullable | **Added 2026-08-13 (`tasks.md` T0-16).** The package this one replaces, if any |
| `package_version` | integer, default `1` | Monotonic per request |
| `package_status` | enum | `CURRENT` \| `SUPERSEDED` |

**Package lineage (added 2026-08-13)**: `001`'s `retry_insufficient_data` already writes a second `EvidencePackage` for a request once imagery becomes available, and `api/routes.py` describes the earlier one as "superseded" — but nothing in the schema records that relationship, so supersession exists only as an ordering by `generated_at`. Under a ten-year retention floor and §65B chain-of-custody requirements, and once `002` attaches a `confidence_tier` that a regenerated package can *change*, an artifact that silently replaces another is a real gap: a claim can be actioned on a `LOW`-tier package that later becomes `HIGH`, with no record tying the two together. Writing a new package MUST set the previous one's `package_status` to `SUPERSEDED` and the new one's `supersedes_package_id` to its `package_id`, in one transaction. Superseded packages are never deleted or mutated — `001`'s never-overwrite-in-place rule is unchanged.

**Validation rules**: `confidence_tier` is required on every package, at every tier, including `WEATHER_ONLY_PRELIMINARY` packages inherited from `001` (a preliminary package still gets a tier, typically `LOW`, since it's generated with reduced input availability). `cce_non_equivalence_statement` is enforced `true` whenever `confidence_tier = LOW` — this is spec.md FR-005 written as a data constraint, not just a narrative convention, so it can't be silently dropped by a future code change without the write failing.

## New: CropCalendarCrossCheck (`crop_calendar_cross_checks`)

| Field | Type | Notes |
|---|---|---|
| `check_id` | string, PK | |
| `request_id` | FK → EvidenceRequest | |
| `source_dataset`, `source_version` | string, string | e.g. WorldCereal v2 (research.md §3) |
| `declared_crop_type` | string, nullable | From the claim, if provided at request time |
| `observed_crop_type` | string, **nullable** | Independently derived from the cross-check source. `null` where the reference product has no class covering this field |
| `declared_calendar_window`, `observed_calendar_window` | date range, date range, nullable | Sowing/harvest window comparison |
| `outcome` | enum | **Replaces the original boolean `discrepancy_flag`, 2026-08-13.** `CONSISTENT` \| `INCONCLUSIVE` \| `DISCREPANT` |
| `reference_accuracy`, `pure_pixel_count` | float nullable, integer | The reference product's published accuracy for this crop/region, and how many pixels fell wholly inside the geometry — the two facts that determine whether `DISCREPANT` is defensible for this request |

**Validation rules**: A row is generated for every request where a declared crop type is available to compare against (spec.md User Story 4). The outcome is always computed — the module MUST NOT silently reconcile a mismatch into the observed value (spec.md FR-010).

**Why this is an enum and not a boolean** (changed 2026-08-13, per [`issue/open query - crop cross-check accuracy floor and discrepancy-flag harm posture (FR-010).md`](./issue/open%20query%20-%20crop%20cross-check%20accuracy%20floor%20and%20discrepancy-flag%20harm%20posture%20%28FR-010%29.md)): with a non-nullable `observed_crop_type` and a boolean flag, a crop outside the reference product's class set has no representable outcome except "mismatch" — turning "the reference product does not cover this crop" into an adverse finding against a named claimant. WorldCereal's class set does not span the crops insured under PMFBY, so that is the common case, not an edge case. `INCONCLUSIVE` is required whenever `observed_crop_type` is `null`, or `pure_pixel_count` is below the configured minimum, or `reference_accuracy` is unestablished for that crop/region; `DISCREPANT` MUST NOT be reachable in any of those states.

A `DISCREPANT` outcome MUST be surfaced with `source_dataset`, `source_version`, `reference_accuracy`, an explicit statement that it is not a fraud determination, and a statement that it did not alter the damage estimate — the same provenance discipline Constitution Principle I/II requires of every other satellite-derived figure, which this output was the one exception to.

## New: SupplementaryEvidenceAttachment (`supplementary_evidence_attachments`)

| Field | Type | Notes |
|---|---|---|
| `attachment_id` | string, PK | |
| `request_id` | FK → EvidenceRequest | |
| `attachment_type` | enum | `PHOTO` \| `OTHER` |
| `uri` | string | Object storage reference, restricted to the module's own store or a configured allowlist. Never dereferenced by the module |
| `submitted_at` | timestamp | |

**Validation rules**: Attachable to a request at any confidence tier, but only surfaced as tier-improvement guidance for `MEDIUM`/`LOW` packages (`evidence_packages.confidence_tier_guidance`). The module never requires this table to be populated — it exists purely as an optional channel-agnostic input (spec.md FR-006).

**`caller_supplied_metadata` removed 2026-08-13**, per [`issue/open query - personal data in caller-supplied attachment metadata (FR-006).md`](./issue/open%20query%20-%20personal%20data%20in%20caller-supplied%20attachment%20metadata%20%28FR-006%29.md). It was an unvalidated opaque JSON field with no reader anywhere in this design — callers would predictably have placed farmer identifiers in it, importing personal data into a store with a ten-year retention floor, which is precisely what Constitution §5's boundary exists to prevent. `external_reference_id` on `EvidenceRequest` already covers the legitimate correlation need with the same opacity and a bounded shape. Removing a field nothing reads costs no capability.

**On `uri`**: the endpoint takes a reference to an already-stored object, not an upload. That the module never fetches it is a security property worth asserting in the contract rather than leaving as an accident of the current implementation — an unconstrained caller-supplied URI that anything downstream dereferences is a server-side request forgery vector.

## New: ClaimOutcome (`claim_outcomes`)

Added 2026-08-13 for `tasks.md` `TV-01`. What actually happened to the claim this request produced evidence for.

| Field | Type | Notes |
|---|---|---|
| `outcome_id` | string, PK | |
| `request_id` | FK → EvidenceRequest | |
| `outcome` | enum | `UPHELD` \| `PARTIALLY_UPHELD` \| `REJECTED` \| `WITHDRAWN` \| `UNKNOWN` — a small closed set, deliberately not the caller's own claim-status vocabulary (Constitution §5) |
| `assessed_loss_fraction` | float, nullable | Independently assessed loss in [0,1] where the caller has one. This is the damage-magnitude label Component 2 needs; `outcome` above is the coarser signal that calibrates confidence tiers and the causation threshold |
| `assessment_source` | enum, **required whenever `assessed_loss_fraction` is present** | `PILOT_SURVEY` \| `INSURER_ASSESSED` \| `REMOTE_REVIEW` \| `CCE_DERIVED` \| `OTHER`. Names where the loss figure came from, so the §4 boundary is enforceable rather than assumed |
| `recorded_at` | date | When the outcome was determined; defaults to receipt time |
| `received_at` | timestamp | When the module was told |

**Why this table exists**: every evidence package eventually pairs with a settled claim, and that pairing is the only training and calibration data this module gets for free. Without it, operating the module generates evidence and discards its own labels — which is why [`001`'s label query](../001-evidence-generation-pipeline/issue/open%20query%20-%20AI-ML%20training%20data%20source%20and%20CCE-label%20question.md) would otherwise stay open indefinitely. It must exist **before** the Pilot & Validation phase (`documents/README.md` §8), or the pilot's labels are lost.

**Validation rules**: At most one current outcome per request; a corrected outcome is a new row, never an update in place, matching the never-overwrite discipline `001`'s store already applies to component results and packages. Writing a row **never** re-runs the pipeline, alters a `confidence_tier`, or supersedes a package — recording what happened must not retroactively shape what the module said would happen, so the write path is strictly one-directional.

**Boundaries**: carries no claim ID, policy field, surveyor identity, or farmer identifier (Constitution §5 — callers correlate via `external_reference_id` as everywhere else).

**The Constitution §4 gate (added 2026-08-13)**: `assessed_loss_fraction` is the one field on this table that could carry a CCE-derived figure, and `TV-01` is deliberately sequenced *before* the §4 decision is made — so without a gate, building it opens an ingress for exactly the data whose permissibility is the repo's oldest open question, arriving unlabelled and unnoticed.

`assessment_source` closes that. Writes are accepted only when the declared source appears in the configured `AUTHORIZED_OUTCOME_SOURCES` allowlist; anything else is rejected, not silently stored. `CCE_DERIVED` is an explicit enum member **and is absent from the default allowlist** — naming it is what makes the boundary enforceable. Omitting it would not prevent CCE-derived figures arriving; it would only guarantee they arrived mislabelled as `INSURER_ASSESSED`, which is strictly worse than rejecting them.

This encodes the §4 boundary as a runtime constraint rather than a convention, and does **not** decide the open question — resolving [`001`'s label query](../001-evidence-generation-pipeline/issue/open%20query%20-%20AI-ML%20training%20data%20source%20and%20CCE-label%20question.md) in favour of offline CCE labels would be a one-line config change, with the decision recorded per Constitution §8 rather than inferred from the schema.

## New: ThermalStressSignal (`thermal_stress_signals`)

| Field | Type | Notes |
|---|---|---|
| `signal_id` | string, PK | |
| `request_id` | FK → EvidenceRequest | |
| `source_dataset`, `source_version` | string, string | e.g. ECOSTRESS L2 LSTE, collection version (research.md §6.2) |
| `land_surface_temperature`, `historical_baseline`, `deviation` | float, float, float | Canopy-temperature deviation from the field's own historical baseline, mirroring the deviation-from-baseline pattern `WeatherCorrelationResult` (`001`) and the DSI (`modeling-approach.md` §6) already use |
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
EvidenceRequest (1) ──< (0..*) ClaimOutcome                      [optional, write-only; a correction is a new row, never an update]
EvidencePackage  (1) ── confidence_tier, confidence_tier_guidance, cce_non_equivalence_statement   [new columns, not a new table]
SatelliteAnalysisResult (1) ── source_class, access_model, considered_not_used                     [new columns, not a new table]
DamageAssessmentComponentResult (1) ── red_edge_index_type, red_edge_index_value                   [new columns on AI_ML row, not a new table]
```

No entity added or extended here references CCE data, and no new table leaves this module's own schema to reference another initiative's tables (Constitution §4/§5) — same boundary `001`'s data model already enforces, unchanged by this extension.
