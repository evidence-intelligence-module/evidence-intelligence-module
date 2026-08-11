# Phase 1 Data Model: Evidence Generation Pipeline

Elaborates the schema already fixed in `HLD.md` §4 with validation rules and state transitions needed for implementation. Field names and table shapes are taken as given from `HLD.md` — this document adds the behavioral rules the spec (`spec.md`) and flow spec (`Evidence-Flow-Spec.md`) require but the HLD's table listing didn't spell out.

## EvidenceRequest (`evidence_requests`)

| Field | Type | Notes |
|---|---|---|
| `request_id` | string, PK | Format `EIM-YYYY-MMDD-NNNNNN` (per HLD §5 example) |
| `geometry` | GeoJSON Polygon or Point | As submitted by requester |
| `event_date` | date | Claimed/reported event date |
| `peril_type` | enum | `hailstorm` \| `flood` \| `drought` \| `cyclone` \| `unseasonal_rain` \| `frost` \| `heatwave` \| `pest_disease_weather_induced` \| `landslide` \| `cloudburst` \| `other` (Evidence-Flow-Spec.md §2 — fixed list) |
| `external_reference_id` | string, nullable | Opaque; never validated or interpreted (spec.md FR-002) |
| `status` | enum | `RECEIVED` → `IN_PROGRESS` → `COMPLETE` \| `INSUFFICIENT_DATA` \| `FAILED` |
| `requested_at` | timestamp | Set on creation |
| `completed_at` | timestamp, nullable | Set when status reaches `COMPLETE` |

**Validation rules**:
- `geometry`, `event_date`, `peril_type` are required; `external_reference_id` is optional and opaque (FR-001, FR-002).
- `peril_type = other` or unrecognized: pipeline still runs the generic damage-detection + weather-anomaly pass but skips peril-specific causation heuristics (Evidence-Flow-Spec.md §2).

**State transitions**:
```
RECEIVED --(pipeline starts)--> IN_PROGRESS
IN_PROGRESS --(all steps complete)--> COMPLETE
IN_PROGRESS --(no usable imagery, non-flood-compatible peril)--> INSUFFICIENT_DATA
INSUFFICIENT_DATA --(imagery becomes available, re-processed)--> COMPLETE
IN_PROGRESS --(unrecoverable error)--> FAILED
```
`INSUFFICIENT_DATA` is not terminal — Evidence-Flow-Spec.md §8 requires re-queuing once imagery becomes available (FR-022).

## SatelliteAnalysisResult (`satellite_analysis_results`)

| Field | Type | Notes |
|---|---|---|
| `result_id` | string, PK | |
| `request_id` | FK → EvidenceRequest | |
| `source_dataset`, `source_version`, `acquisition_date` | string, string, date | Mandatory provenance (Constitution §2.2, FR-017) |
| `pre_event_index_value`, `post_event_index_value`, `index_type` | float, float, string | e.g. NDVI |
| `flood_extent_geometry` | GeoJSON, nullable | Populated only when SAR flood mapping ran (FR-006) |

**Validation rules**: `source_dataset`/`source_version`/`acquisition_date` are required on every row — a row cannot be persisted without provenance (this is the field-level enforcement of Constitution §2.2/§2.5). `flood_extent_geometry` is non-null only when `peril_type = flood` or optical imagery was unusable and SAR substituted (FR-006).

## DamageAssessmentComponentResult (`model_component_results`)

| Field | Type | Notes |
|---|---|---|
| `result_id` | string, PK | |
| `request_id` | FK → EvidenceRequest | |
| `component` | enum | `SEMI_PHYSICAL` \| `AI_ML` \| `CSM_ASSIMILATION` \| `ENSEMBLE` \| `DSI` |
| `methodology_version` | string | Pinned independently per component (FR-018, FR-021) |
| `point_estimate` | float | Damage/yield-loss estimate, or DSI score for the `DSI` row |
| `confidence_or_accuracy` | float / structured | R²/NRMSE for `AI_ML`; calibration confidence for `SEMI_PHYSICAL`/`CSM_ASSIMILATION`; combined confidence for `ENSEMBLE`; entropy-weight summary for `DSI` |
| `damage_classification`, `affected_area_ha` | string, float, nullable | Populated only on the `ENSEMBLE` row — the reconciled, reportable figures |
| `component_inputs` | structured reference | Points to the specific feature values/datasets used (Modeling-Approach.md §7) |

**Validation rules**:
- One row per `(request_id, component)` — a later component's result MUST NOT overwrite an earlier row (FR-012). Re-running produces a new row set, not an in-place update, to preserve the audit trail.
- `SEMI_PHYSICAL` and `AI_ML` rows exist for every request (FR-010). A `CSM_ASSIMILATION` row exists only for requests meeting the high-scrutiny criteria — **criteria not yet defined**, see `issue/open query - CSM high-scrutiny trigger criteria (FR-011).md`; until resolved, this field's presence/absence is a design placeholder, not a working trigger.
- `ENSEMBLE` row is derived only after all contributing component rows exist for the request (FR-013).
- `DSI` row is computed independently of `ENSEMBLE` — both are evidence components, neither supersedes the other (Modeling-Approach.md §6, FR-014).

## WeatherCorrelationResult (`weather_correlation_results`)

| Field | Type | Notes |
|---|---|---|
| `result_id` | string, PK | |
| `request_id` | FK → EvidenceRequest | |
| `source_dataset`, `source_version` | string, string | e.g. CHIRPS v2.0, ERA5-Land |
| `observed_value`, `historical_baseline`, `anomaly_score` | float, float, float | |
| `causation_confidence_score` | integer, 0–100 | Weighted combination per Evidence-Flow-Spec.md §5 (temporal 30%, spatial 25%, magnitude 25%, physiological 20%) |

**Validation rules**: `causation_confidence_score` is always computed and always persisted, even when below the low-confidence threshold — the package is still delivered, clearly labeled (FR-024; numeric threshold **not yet defined**, see `issue/open query - causation confidence low-confidence threshold (FR-024).md`).

## EvidencePackage (`evidence_packages`)

| Field | Type | Notes |
|---|---|---|
| `package_id` | string, PK | |
| `request_id` | FK → EvidenceRequest | |
| `package_tier` | enum | `WEATHER_ONLY_PRELIMINARY` \| `COMPLETE` — see note below |
| `pdf_uri`, `json_uri`, `map_uris` | string, string, string[] | Object storage references |
| `methodology_version` | string | Pins the exact combination of component versions used (Constitution §2.2) |
| `checksum` | string | Integrity verification (FR-020) |
| `generated_at` | timestamp | |
| `retention_expiry_date` | date | `generated_at` + 10 years (Constitution §7, FR-029) |

**Validation rules**:
- `pdf_uri`/`json_uri`/`methodology_version`/`checksum` are required — a package cannot be generated without them (this is the field-level enforcement of Constitution §2.4 / spec.md FR-017–FR-020).
- **Multiple packages per request are allowed and none are deleted or overwritten**: when imagery is unavailable, a `WEATHER_ONLY_PRELIMINARY` package is delivered first (FR-022); once imagery arrives, a `COMPLETE` package is generated as a *new* row, not a mutation of the preliminary one. This preserves the reproducibility/auditability principle — an earlier preliminary package that was already delivered to a requester must remain independently verifiable even after a fuller package supersedes it as the operative evidence.

## Entity Relationships

```
EvidenceRequest (1) ──< (0..*) SatelliteAnalysisResult
EvidenceRequest (1) ──< (2..5) DamageAssessmentComponentResult   [SEMI_PHYSICAL + AI_ML always; CSM_ASSIMILATION conditional; ENSEMBLE + DSI derived]
EvidenceRequest (1) ──< (0..*) WeatherCorrelationResult
EvidenceRequest (1) ──< (1..*) EvidencePackage                   [preliminary then complete, both retained]
```

No entity in this data model references any table, topic, or schema outside this module (Constitution §5) — there is deliberately no CCE-related entity anywhere in this design (Constitution §4).
