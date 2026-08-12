# Quickstart: Validating the Satellite Evidence Parity Roadmap

Validation scenarios proving each user story (`spec.md`) works end-to-end, on top of an already-running `001-evidence-generation-pipeline` service. Not a full test suite — see `tasks.md` for that; this is the runnable proof that the feature does what the spec says.

## Prerequisites

- The `001-evidence-generation-pipeline` service running per its own `quickstart.md`/`GUIDE.md`.
- `AI_ML_MODEL_PATH` pointing at a trained Component 2 model (`GUIDE.md` "Training the AI/ML Model") — foundation-model feature augmentation (Scenario 3) is evaluated against this.
- `BHOONIDHI_API_KEY` for ISRO's free Resourcesat-2A LISS-4/EOS-04 access (`research.md` §6.3) — Scenario 1 can be validated with Sentinel-1 SAR alone if this isn't configured, since SAR is the load-bearing default, not the enhanced tier. No commercial (Planet/Maxar/ICEYE) credentials are needed or used anywhere in this quickstart — commercial tasking is deferred (`issue/`, resolved 2026-08-12).

## Scenario 1 — Monsoon cloud cover fallback (User Story 1)

1. Submit an evidence request (`POST /evidence-requests`) for a field and event date where the pre/post-event window is known to be fully cloud-covered (verifiable independently via any Sentinel-2 cloud-mask product for that date/AOI).
2. Poll `GET /evidence-requests/{request_id}` until `status: COMPLETE` or `INSUFFICIENT_DATA`.
3. **Expected**: `package.sources_used` includes a SAR source (Sentinel-1 baseline, or EOS-04 if Bhoonidhi is configured); the package is not `INSUFFICIENT_DATA` solely due to cloud cover, per spec.md Acceptance Scenario 1.1.

## Scenario 2 — Confidence tier and non-equivalence statement (User Story 2)

1. Submit two requests: one expected to score high on existing ensemble confidence (clear, well-covered field/event), one expected to score low (sparse data, ambiguous signal).
2. Retrieve both completed packages.
3. **Expected**: the first returns `confidence_tier: "HIGH"` with `confidence_tier_guidance: null`; the second returns `confidence_tier: "LOW"` with non-null guidance text and `cce_non_equivalence_statement: true`, per spec.md Acceptance Scenarios 2.1/2.2.
4. Attach supplementary evidence to the low-confidence request via `POST /evidence-requests/{request_id}/supplementary-evidence` and confirm `201 Created` with no requirement to specify which intimation channel originated it.

## Scenario 3 — Foundation-model feature augmentation (User Story 3)

1. Run `scripts/train_ai_ml_model.py` twice on the same labeled dataset: once with foundation-model embeddings enabled, once without.
2. Compare the reported MAE/RMSE/NRMSE on the same held-out validation split (per `GUIDE.md`'s existing training output format).
3. **Expected**: both runs report real, non-fabricated held-out metrics (never a fabricated number if the delta is negligible); the evidence package generated afterward discloses `foundation_model_features.model_name`/`model_version` per spec.md Acceptance Scenario 3.1.
4. Temporarily disable the foundation-model source (e.g., point `PRESTO_MODEL_PATH` at a nonexistent path) and resubmit a request.
5. **Expected**: the request still completes; `package.foundation_model_features.status: "FALLBACK_NOT_USED"`, per spec.md Acceptance Scenario 3.2.

## Scenario 4 — Crop-type/calendar discrepancy flagging (User Story 4)

1. Submit a request with a declared crop type known to mismatch the field's actual crop (e.g., declare "wheat" for a field independently known to be under paddy for that season).
2. **Expected**: `package.crop_calendar_cross_check.discrepancy_flag: true`, and the package's declared/observed values are both retained (not silently reconciled), per spec.md Acceptance Scenario 4.2.
3. Repeat with a matching declared/observed crop type.
4. **Expected**: `discrepancy_flag: false`, no flag raised, per spec.md Acceptance Scenario 4.1.

## Scenario 5 — Graceful degradation (Edge Cases)

1. Submit a request for a field/date where no enhanced source (SAR, VHR, or commercial) is available or authorized.
2. **Expected**: the request still completes using only the `001` baseline pipeline; `package.sources_considered_not_used` may be non-empty (recording that a commercial source was evaluated and skipped), but the request is never failed solely because an enhanced source was unavailable, per spec.md Edge Cases.

## Scenario 6 — Thermal/red-edge stress signals for drought and heatwave claims (User Story 5)

1. Submit a request with `peril_type: "drought"` or `"heatwave"` for a field/date where Sentinel-2 red-edge bands and an ECOSTRESS pass are both available within the analysis window.
2. **Expected**: `package.red_edge_index` names a specific index (e.g. `NDRE`, not a generic value) and `package.thermal_stress_signal` is populated with a non-null deviation figure, per spec.md Acceptance Scenarios 5.1/5.2.
3. Repeat for a date/location where no ECOSTRESS pass fell within the window (its 1–5 day revisit is irregular).
4. **Expected**: the request still completes; `package.thermal_stress_signal` is `null`, `package.red_edge_index` is still populated if red-edge bands were available, per spec.md Acceptance Scenario 5.3.
5. Repeat for a non-drought/heatwave peril type (e.g. `hailstorm`).
6. **Expected**: `package.thermal_stress_signal` is `null` — this field is scoped to drought/heatwave only (spec.md FR-016), not populated or attempted for other peril types.

## Out of scope for this quickstart

Field/damage-boundary segmentation assist (FR-014, SHOULD-priority) has no dedicated scenario here — it's a human-in-the-loop UI capability, not an automated pipeline behavior, and is validated via its own tooling once implemented, not via this API-level quickstart.
