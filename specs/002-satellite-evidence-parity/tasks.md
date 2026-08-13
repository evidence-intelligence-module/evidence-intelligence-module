---

description: "Task list for Satellite Evidence Parity Roadmap implementation"
---

# Tasks: Satellite Evidence Parity Roadmap

**Input**: Design documents from `/specs/002-satellite-evidence-parity/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/evidence-request-api-extensions.md, quickstart.md — all present

**Tests**: Included. `plan.md`'s project structure extends `001`'s existing `tests/{contract,integration,unit}` convention, and `quickstart.md`'s scenarios map 1:1 to the tasks below, matching how `001-evidence-generation-pipeline/tasks.md` handled the same decision.

**Organization**: Tasks are grouped by user story (from `spec.md`) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- **`T0-NN`**: Phase 0 base-pipeline corrections, added 2026-08-13 (see below). Numbered separately from the `TNNN` series so the original task numbering stays stable.
- **`T05-NN`**: Phase 0.5 evidence-processing improvements. **`TV-NN`**: Phase 0.6 label capture and label-free validation. Distinct prefixes so `T0-06` and the Phase 0.6 tasks can't be confused.
- **`T0R-NN`**: Phase 0.4 pipeline decomposition (`R` for refactor), added 2026-08-13. Kept distinct from `T0-NN` because these restructure code rather than correct a wrong figure — the two want different review standards, and conflating them in one sequence hides which commits changed an output.

## Path Conventions

Single project (per `plan.md` Structure Decision, extending `001`): `src/evidence_intelligence/` for source, `src/tests/` for tests. This feature adds new modules within `001`'s existing subpackages rather than a new tree.

## A note on scope not covered elsewhere in this repo's docs

PyTorch is used below to run Presto inference (`research.md` §1 names Presto but not a runtime) — a routine implementation choice, not a domain-specific figure, so it doesn't warrant an `issue/` entry, matching how `001-evidence-generation-pipeline/tasks.md` treated its own FastAPI choice.

**Update (2026-08-12): commercial satellite tasking is resolved, not open.** `issue/open query - commercial satellite tasking budget and volume thresholds.md` is decided — Option A, free-only for this rollout. `T037` below still implements `commercial_tasking_client.py` as a disabled-by-default stub (`COMMERCIAL_TASKING_ENABLED=false`), but it now lives in Polish rather than the User Story 1 critical path, since building a paid-tasking client with no authorized budget isn't near-term work. The free enhanced tier for User Story 1 runs on Sentinel-1 SAR (existing) plus ISRO's Resourcesat-2A LISS-4/EOS-04 via a new Bhoonidhi client (T009) — not PlanetScope, which is commercial and deferred alongside the rest (see `research.md` §2's correction note).

---

## Phase 0: Base-Pipeline Corrections (BLOCKING — added 2026-08-13)

**Purpose**: `002` was planned as an extension of a working measurement pipeline. A full re-evaluation of this feature's artifacts against the running code in `src/` on 2026-08-13 found that several of the figures `002` builds on are currently constant, hardcoded, or synthesized. Every one of these is a defect with an unambiguous right answer — they are **not** open queries, and are tracked here rather than in [`issue/`](./issue/README.md).

**Why this blocks the rest of this feature**, concretely:

- `models/ensemble.py`'s `combined_confidence` evaluates to exactly **0.50 on every request** in the shipped configuration (`total_weight / len(contributions)`, with Component 1 always at 0.85 and untrained Component 2 always at 0.15). FR-004 derives the entire confidence tier from that figure — so User Story 2 assigns one tier to 100% of packages, SC-003 is vacuous, SC-005 has nothing to track, and `quickstart.md` Scenario 2 cannot pass.
- `pipeline.py` passes ERA5-Land `temperature_2m` (Kelvin) into `semi_physical.run`'s `*_temp_c` parameters. Every real reading exceeds `CropParameters.temp_max_c` (40), so `_temperature_stress_scalar` returns 0.0, expected biomass is 0, and Component 1 reports `damage_fraction = 0.0` — with `calibration_confidence` still at 0.85, because it only range-checks fAPAR. The ensemble is therefore `0.15 × placeholder`, which `_classify` rounds to **"negligible" on effectively every request**.
- 55 of the causation score's 100 points come from `days_between_event_and_ndvi_drop=1` and `distance_km_to_weather_anomaly=0.0`, both hardcoded at the call site. The figure printed in every §65B package as "causation confidence" is a fixed 55 plus a small variable remainder.

Until these hold, `002`'s new sources, embeddings and tiers change the provenance of the answer without changing the answer.

**CRITICAL**: `T0-01` … `T0-05` block Phase 2 onward. `T0-06` … `T0-11` are strongly recommended before User Story 1, since they determine whether new sources improve anything measurable.

### Correctness (blocking)

- [x] T0-01 Convert ERA5-Land `temperature_2m` from Kelvin to Celsius at the ingestion boundary, and add a plausibility guard so an out-of-range temperature degrades `calibration_confidence` instead of silently zeroing biomass, in `src/evidence_intelligence/ingestion/weather.py` and `src/evidence_intelligence/models/semi_physical.py`
- [x] T0-02 Stop synthesizing NDVI-derived features when post-event optical is absent — represent them as absent rather than `0.0`, and exclude Component 1 from the ensemble when its inputs are unavailable, rather than contributing a fabricated maximum-damage signal, in `src/evidence_intelligence/pipeline.py`
- [x] T0-03 Stop populating `lswi_deviation` with the NDVI drop (a different physical quantity), and populate the features already ingested and discarded — ERA5 temperature anomaly against a computed baseline, SMAP soil-moisture deviation — in `src/evidence_intelligence/pipeline.py` and `src/evidence_intelligence/ingestion/weather.py`
- [x] T0-04 Fix `_placeholder_estimate` to average over the features actually supplied rather than all 17 declared ones (11 of which are currently constant zeros, diluting every estimate toward zero), and preserve the sign convention its docstring asserts, in `src/evidence_intelligence/models/ai_ml.py`
- [x] T0-15 Measure Sentinel-1 **VH** alongside VV so `modeling-approach.md` §6's `sar_vh_backscatter_deviation` indicator carries the cross-polarized canopy-structure measurement it names, rather than the co-polarized flood detector's VV. Populates `vh_vv_backscatter_deviation` (Component 2's declared cross-pol feature) as `vh_drop − vv_drop`, since a dB ratio is a difference; both signals stay absent where the acquisitions were single-polarization, in `src/evidence_intelligence/ingestion/gee_client.py` and `pipeline.py`
- [ ] T0-16 Add package lineage — `supersedes_package_id`, `package_version`, `package_status` on `evidence_packages`, set transactionally when a package replaces another (`data-model.md`). `retry_insufficient_data` already writes a second package today with nothing recording the relationship, under a 10-year retention floor and §65B chain-of-custody requirements; once `002` attaches a `confidence_tier` a regenerated package can change the headline conclusion an insurer already acted on. Surfaced by splitting [`issue/open query - supplementary evidence re-evaluation and package supersession (FR-006).md`](./issue/open%20query%20-%20supplementary%20evidence%20re-evaluation%20and%20package%20supersession%20%28FR-006%29.md) — the lineage half was a defect, not a decision. **Fold into `T004`**, in `src/evidence_intelligence/store/schema.py` and `evidence_store.py`
- [ ] T0-05 Replace the constant `combined_confidence` with a figure that varies with real input availability — **gated on** [`issue/open query - confidence tier threshold values (FR-004).md`](./issue/open%20query%20-%20confidence%20tier%20threshold%20values%20%28FR-004%29.md), since what it should be computed over is the same question as what the tier should be computed over — in `src/evidence_intelligence/models/ensemble.py`

### Evidence quality (strongly recommended before User Story 1)

- [ ] T0-06 Compute the causation engine's temporal and spatial terms from observed data (break-point date of the index time series; actual distance from the geometry to the weather anomaly) instead of passing hardcoded `1` and `0.0` at the call site, in `src/evidence_intelligence/pipeline.py` and `src/evidence_intelligence/causation/scoring.py`
- [x] T0-07 Add per-pixel cloud and cloud-shadow masking (SCL/QA60 or s2cloudless) and report a per-geometry `valid_pixel_fraction`, replacing the scene-level `CLOUDY_PIXEL_PERCENTAGE < 20` filter that lets a scene 19% cloudy be 100% cloudy over a 0.16 ha field, in `src/evidence_intelligence/ingestion/gee_client.py`
- [ ] T0-08 Restructure `SatelliteAnalysisResult` to one row per source considered, not one row per request (today only the post-event source is persisted; pre-event and the five historical composites are dropped) — prerequisite for FR-009 and for `contracts/`'s `sources_used[]`/`sources_considered_not_used[]` arrays, in `src/evidence_intelligence/store/schema.py` and `pipeline.py`. **Fold into T004** rather than migrating twice
- [x] T0-09 Add a per-request evidence-inputs manifest recording every source and signal attempted, its outcome, and the reason on failure — the natural input to the confidence tier, and what a §65B chain-of-custody argument needs as one retrievable statement rather than spread across `considered_not_used` / `status` / `pass_available` / the cross-check `outcome` in four tables
- [x] T0-10 [P] Carry event-window precipitation as sum and 1-day maximum alongside the current 10-day mean (a `collection.mean()` over the window averages a cloudburst into insignificance — for the perils this module names as highest-value), and record the already-fetched IMD station corroboration in package provenance instead of discarding it, in `src/evidence_intelligence/ingestion/weather.py`
- [x] T0-11 [P] Filter Sentinel-1 by `relativeOrbitNumber_start` and `orbitProperties_pass` so pre/post backscatter comparisons use matching viewing geometry, in `src/evidence_intelligence/ingestion/gee_client.py`

### Known smaller defects (fix opportunistically)

- [x] T0-17 [P] **Disclose the damage-classification banding** — move `pipeline.py::_classify`'s `0.1`/`0.33`/`0.66` cut points into config and state in every package that the `negligible`/`minor`/`moderate`/`severe` banding is a presentational convention, not a sourced standard. The thresholds appear nowhere in `documents/` and `yestech_manual_2023.md` defines no transferable severity vocabulary — so a categorical label in a §65B output currently rests on invented figures, and a field at 0.34 reads as "moderate" while one at 0.32 reads as "minor" on no stated basis. The disclosure half needs no decision; which bands are *right* is [`001`'s damage classification band query](../001-evidence-generation-pipeline/issue/open%20query%20-%20damage%20classification%20band%20thresholds.md)
- [x] T0-18 [P] **Disclose the Harvest Index assumption** — surface the value used, and that it is a single un-crop-specific constant, in every package's accuracy statement. `modeling-approach.md` §2 commits to Harvest Index being "sourced from published crop-variety reference values … clearly labeled as a modeling assumption"; `pipeline.py` passes a flat `harvest_index=0.4` for every crop and labels nothing, so a documented commitment is unmet in the artifact where it matters. Yield loss is `damage_fraction × harvest_index`, so this scales the headline figure on every claim. Per-crop resolution needs a request-contract decision — [`001`'s harvest index query](../001-evidence-generation-pipeline/issue/open%20query%20-%20harvest%20index%20source%20and%20per-crop%20resolution.md), which should be decided jointly with User Story 4's crop-type input since both need the same field
- [x] T0-12 [P] `.replace(year=…)` on arbitrary window dates raises on 29 February in `ingestion/gee_client.py` (`historical_composite`) and `ingestion/weather.py` — `store/evidence_store.py`'s `retention_expiry_date` already guards this exact case and is the pattern to follow
- [x] T0-13 [P] **Done 2026-08-13, verified against real PostGIS 3.4 (postgis/postgis:16-3.4).** The suspicion was half wrong and half worse than stated.
  - **`api/routes.py`'s `str(body.geometry)` was NOT broken.** GeoAlchemy2 emits `ST_GeomFromEWKT(...)`, whose parser falls through to GeoJSON and accepts a bare geometry — even as a Python dict `repr()` with single quotes. It worked by the parser's leniency, not by design.
  - **`pipeline.py`'s `str(imagery.sar.flood_extent_geojson)` always failed**: `psycopg.errors.InternalError_: invalid GeoJson representation`. Earth Engine's `reduceToVectors().getInfo()` returns a GeoJSON **FeatureCollection**, which is a container, not a geometry — PostGIS rejects it for both populated and empty collections.
  - **Severity comes from when it fires.** `gee_client.sar_composite` sets `flood_extent_geojson` only when `vv_drop` clears `SENTINEL1_FLOOD_DROP_THRESHOLD_DB` — i.e. *only when flooding is detected*. `run_pipeline_background` catches the exception and marks the request `FAILED`. So the pipeline crashed precisely when it had succeeded at detecting a flood, for the peril and cloud-cover case this module exists to evidence.
  - **Why no test caught it**: every test injects `FakeEvidenceStore`, which stores any string and never reaches PostGIS. `test_sar_flood_fallback` asserted `flood_extent_geometry is not None` and passed throughout. The fake also returned an *empty* FeatureCollection while reporting `vv_drop_db=5.0` — an internally inconsistent "flood detected, zero flooded pixels" fixture, now corrected to a populated collection.
  - **Fix**: new `src/evidence_intelligence/geometry.py::to_ewkt` normalises geometry / `Feature` / `FeatureCollection` to `SRID=4326;WKT`, dissolving multi-feature collections with `unary_union` (one row holds one geometry; a flood extent is naturally multi-part) and returning `None` for an empty collection so "no flood pixels" stores `NULL` rather than a zero-area extent that would later read as measured. Both call sites — `routes.py` and `pipeline.py` — now go through it, so the stored form is explicit rather than dependent on parser leniency. Covered by `src/tests/unit/test_geometry_ewkt.py` (9 tests, no live DB needed).
- [x] T0-14 [P] Remove the dead `notes = list(imagery.historical) and [] or [...]` expression in `pipeline.py`, immediately overwritten by the `if not has_historical_baseline` block below it

**Checkpoint**: the pipeline produces figures that vary with the evidence. Phases 1–8 below are measurable from here.

---

## Phase 0.4: Pipeline Decomposition (added 2026-08-13)

**Design**: [`pipeline-decomposition-design.md`](./pipeline-decomposition-design.md) — read it before starting; the tasks below are its migration table and nothing more.

**Purpose**: Phase 0 fixed four defects of one shape — an input that was never measured being read as a measured value (`T0-02` NDVI→`0.0`, `T0-03` LSWI→the NDVI drop, `T0-04` 11 of 17 features→`0.0`, and a fifth found on 2026-08-13, below). Each was fixed at its call site with a conditional and a comment. The discipline that prevents the class is currently a convention repeated at six call sites in a 761-line `pipeline.py`, enforced by nothing. This phase makes it a property of a type.

**The fifth defect, not previously tracked**: `models/dsi.py` handles a missing historical archive two ways at once — `_min_max_normalize` returns the FR-023 `0.5` midpoint, while `_entropy_weights` returns weight `0.0`, which nullifies it. `pipeline.py` passes `[]` for five of six historical arrays, so all weight lands on `ndvi_deviation` and **the DSI score equals the normalised NDVI deviation** — a single-indicator figure presented as a six-indicator composite, with nothing in the package saying so. `weather_anomaly_magnitude`, the one indicator the pipeline reliably populates, is among those zeroed. `test_dsi.py`'s only weight assertion uses fully-populated archives, the opposite of what the pipeline passes, so the suite cannot see it.

**Sequencing** (does not follow section order — read this):

- Land **before `T0-08`**, which restructures exactly the write path `T0R-07` centralises into `_persist`. Landing `T0-08` first builds that logic twice.
- Land **before `T05-02`**, which afterwards becomes a single `obs.record(...)` call, into a DSI that reports `crop_condition_variability` as contributing rather than silently zero-weighting it.
- `T0-06` is independent and can proceed in parallel.

**Not blocking** Phases 1–8 in the way Phase 0 is: the pipeline already produces varying figures. What this buys is that the next defect of the same class is caught by a test rather than by re-reading the pipeline.

- [x] T0R-01 **Done 2026-08-13.** 8 fixtures recorded (6 `pinned`, 2 `known-wrong`) in `src/tests/fixtures/golden/`, with `tests/golden.py`, `tests/integration/test_golden_fixtures.py`, `scripts/record_golden_fixtures.py`, and a `README.md` covering the labels. Suite 117 → 135, ruff clean.
  - **The harness needed a scenario the fixtures did not have.** Every pre-existing scenario's historical archive is five identical values (`FakeGEEClient.historical_composite` returned `0.7` five times), so `hi == lo` in `_min_max_normalize` and it returns the `0.5` midpoint *whatever the entropy weights are*. `dsi_score` was `0.5` in every scenario from three unrelated causes — which is why the weight collapse survived: no test could distinguish a working DSI from a collapsed one. Added a `varied_history` fake scenario and a `varied_historical_archive` fixture so `T0R-05`'s gate is not vacuous.
  - **Second defect found and pinned, not fixed** — see `T0R-05`'s note below.
  - Scope as specified: full JSON package snapshots per scenario, each labelled `pinned` (any diff is a regression) or `known-wrong` (expected to flip, naming the task that flips it). Capture current behaviour including its known-wrong parts — a change-detector, not a correctness oracle.
- [x] T0R-02 **Done 2026-08-13.** `observation.py` added (`Observation`/`Absent`/`FieldObservations`/`ObservationBuilder`/`observe`); `pipeline.py` builds it once and reads every derived signal from it. All 8 golden fixtures byte-identical. Suite 135 → 145, ruff clean, `pipeline.py` 761 → 722 lines.
  - **Two substitutions preserved rather than corrected**, because this task's gate is byte-identical output. Both are now stated in the signal's `source` provenance instead of buried in an expression, which is what makes them fixable under a task that owns the fixture they will flip: (a) `FALLBACK_TEMPERATURE_C = 25.0` stands in when ERA5-Land returns no reading, so Component 1 reports `calibration_confidence` 0.85 on a temperature nobody measured; (b) `abs(anomaly_score or 0.0)` turns an uncomputable precipitation anomaly into a measured zero that reaches both the DSI and the causation score — the exact shape of `T0-02`/`T0-03`. Neither is covered by any current fixture (the fakes always return readings), so both need a scenario before they can be flipped safely.
  - `has_historical_baseline` deliberately still counts historical *composites* from the bundle rather than archive entries from `obs`; the two differ when a composite returns no index value, and correcting that is not a lift.
  - Scope as specified: add `src/evidence_intelligence/observation.py` with `Observation`/`Absent`/`FieldObservations`, and have `pipeline.py` build and read it. Absence carries a reason; the sole scalar accessor returns `float | None`; there is deliberately no `get(name, default)` and no `__getitem__`, since `pyproject.toml` runs ruff `E`/`F`/`I`/`UP` with no type checker and the API shape is therefore the enforcement. Absorbs `_ndvi_to_fapar`, `_insolation_proxy_mj`, `_cross_pol_ratio_deviation`, `ndvi_drop`, `fapar_deviation`, `weather_anomaly_normalized`, `optical_pair_available`, `FALLBACK_TEMPERATURE_C`. Gate: all `pinned` fixtures byte-identical
- [ ] T0R-03 Add the three structural tests: **import-graph** (no module under `models/`, `causation/`, `packaging/` imports `ingestion` or `store`), **absence-propagation** (parametrized over every consumer — signal `Absent` ⇒ output `None`/excluded, never a number; this is the test that would have caught all five defects), **manifest-agreement** (every consumed signal appears `USED`; every `Absent` appears with its reason). Expected to fail initially for consumers still reading raw bundles — that failure is `T0R-04`'s specification
- [ ] T0R-04 Add `src/evidence_intelligence/models/registry.py` with the `DamageEstimator` protocol (`component`, `methodology_version`, `estimate(obs) -> Estimate | NotRun`) and a separate `Trainable` protocol satisfied by `AiMlEstimator` alone — trainability becomes a declared capability rather than a special case in orchestration, referenced only by `scripts/train_ai_ml_model.py`. Three thin adapters wrap the existing `semi_physical`/`ai_ml`/`csm_assimilation` modules without touching their science. `csm_high_scrutiny_enabled` gating moves into registry construction so the loop carries no conditionals. `ensemble.semi_physical_weight`/`ai_ml_weight` move onto their estimators (the `0.15` untrained cap is a statement about Component 2's confidence, not blending policy), leaving `ensemble.combine` purely mechanical. **Per-component `methodology_version` and the `ModelComponent` enum are unchanged** — §65B re-derivability depends on them staying distinct. Gate: `pinned` fixtures identical
- [ ] T0R-05 Fix the DSI inconsistency above: partition indicators into `contributing` (non-empty archive) and `excluded` (name → reason); compute entropy weights and the weighted sum over contributing only; return `score: float | None`. **FR-023 is untouched** — `normalized_indicators` still reports the `0.5` midpoint for every indicator. Disclose `contributing`/`excluded` in the package, since `report_generator.py` currently prints a bare `Damage Severity Index: {score}`. All three `test_dsi.py` tests pass unchanged (they assert on `normalized_indicators`, never on weights under an empty archive), and today's score is numerically identical since weight already collapsed to `ndvi_deviation = 1.0`. One `known-wrong` fixture flips: no archive for any indicator now yields `None` rather than a confident-looking `0.5`
  - **Note, found by `T0R-01`, not yet scoped into any task**: the archive `pipeline.py` passes for `ndvi_deviation` is `historical_ndvi` — a list of **absolute NDVI index values** — while the current indicator is a **deviation**. The two are different quantities, exactly the `T0-03` mismatch in a different place. The `varied_historical_archive` fixture pins the consequence: normalizing a 0.45 NDVI drop against a 0.62–0.81 index range clips below the floor, so the package reports a **Damage Severity Index of 0.0 for a field that lost 0.45 NDVI**. Fixing this needs a source of historical *deviations* (each prior season's drop against its own baseline), which is data work adjacent to `T05-03`/`T05-05` rather than part of this refactor — decide where it lands before closing Phase 0.4
- [ ] T0R-06 Add `src/evidence_intelligence/packaging/assembly.py` building `PackageContent` for **both** tiers, and delete `_deliver_weather_only_preliminary` — a near-duplicate 60-line second path whose divergence is why the preliminary tier carries no `evidence_inputs` manifest today. Preliminary packages gain the manifest and the coverage statement; they do **not** gain the Harvest Index / damage-band statements, which describe figures that tier does not contain — a disclosure on an absent figure is noise, and noise trains readers to skip disclosures. Gate: preliminary `known-wrong` fixtures flip, complete stay `pinned`
- [ ] T0R-07 Introduce `PipelineRecord` (satellite row, weather row, component rows, `PackageContent`, tier, terminal status) and a single `_persist`, the only function that calls `store.add_*`; stages become pure. Writes now batch at the end rather than landing incrementally, so a mid-run crash leaves no rows where today it leaves an orphaned satellite/weather row with no package — `run_pipeline_background` marks `FAILED` either way, and for a §65B record "no run" is a cleaner artifact than "a run that describes inputs but produced no evidence". `set_status(IN_PROGRESS)` stays outside the batch. Gate: `pinned` identical, write order asserted
- [ ] T0R-08 Delete the helpers left dead by `T0R-02`/`T0R-04`/`T0R-06` from `pipeline.py`. Gate: ruff clean, all 117 existing tests plus the new structural tests pass, `pipeline.py` ~120 lines

**Checkpoint**: absent inputs cannot be read as measured values without a test failing, and `pipeline.py` is orchestration only.

---

## Phase 0.5: Evidence-Processing Improvements (added 2026-08-13)

**Purpose**: work on the imagery *already ingested* that improves evidence quality more, per unit of effort, than acquiring new sources does. The same 2026-08-13 re-evaluation that produced Phase 0 found that this roadmap reaches for new sensors (User Story 1) and new model features (User Story 3) before extracting what the existing Sentinel-2/Sentinel-1 archive already supports. These tasks cost no new data licence, no new vendor integration, and no labeled training set — which is what makes them worth sequencing ahead of the stories that do.

**Not blocking**, unlike Phase 0. But `T05-01` and `T05-02` directly determine whether User Story 1's enhanced sourcing has anything measurable to improve on, and `T05-04` is the strongest single move toward this feature's stated parity goal.

- [ ] T05-01 [P] Mask boundary pixels before reducing a geometry: negative-buffer the field by one pixel of the selected source and/or weight by each pixel's contained fraction, so a per-field index value comes from pixels actually inside the field. India's ~0.16 ha median field size means boundary pixels dominate an unbuffered 10 m reduction — this addresses the mixed-pixel problem User Story 1 buys resolution to solve, on data already in hand, in `src/evidence_intelligence/ingestion/gee_client.py`
- [ ] T05-02 [P] Replace `_reduce_mean`'s single mean with a distribution over the field (p10/p50/p90 plus coefficient of variation), so "half the field is destroyed" is distinguishable from "the whole field is mildly stressed" — currently indistinguishable, since both reduce to the same mean. Also populates `crop_condition_variability`, a `modeling-approach.md` §6 DSI indicator that has never been computed, in `src/evidence_intelligence/ingestion/gee_client.py` and `pipeline.py`
- [ ] T05-03 [P] Make the historical baseline robust to prior loss years: use a median or trimmed mean over the archive rather than a mean, and record which seasons contributed (`spec.md` Edge Cases, added 2026-08-13). A 5-year mean that includes damaged seasons encodes damage as normal and suppresses the very anomaly the module is looking for, in `src/evidence_intelligence/ingestion/gee_client.py` and `ingestion/weather.py`
- [ ] T05-04 Add a spatial control comparison: score the field's index change against the contemporaneous distribution of statistically similar neighbouring fields (same crop where known, same agro-climatic zone, same acquisition), rather than only against its own history. "This field declined while comparable neighbouring fields under the same weather did not" is a materially stronger causal argument than "this field declined", it is computable from imagery already ingested, and it attacks the causation weakness `T0-06` only partly addresses. Closest analogue to what the Check-by-Monitoring precedent in `documents/research/satellite-parity-global-precedent-research.md` actually does
- [ ] T05-05 Move Component 2's input from two-point pre/post differencing to a per-field index time series compared against its own multi-year phenological curve. Yields a break-point *date* (the observable `T0-06`'s temporal causation term needs, rather than the hardcoded `1`), is robust to a single bad composite, and produces the pixel-timeseries shape Presto consumes natively — so it de-risks User Story 3 rather than competing with it
- [ ] T05-06 [P] Replace the in-process `BackgroundTasks` execution with a durable job runner (queue + retry + restart survival), and schedule `retry_insufficient_data`, which exists and is tested but is called by nothing. `002` adds four external dependencies (Bhoonidhi, openEO/WorldCereal, ECOSTRESS via S3, Presto inference) to a path that currently loses a request on any process restart — each new source is otherwise a new way to lose one, and SC-001's latency target is unverifiable without it, in `src/evidence_intelligence/api/routes.py`
- [ ] T05-07 [P] Replace deprecated `datetime.utcnow()` with timezone-aware `datetime.now(UTC)` across `api/routes.py`, `pipeline.py`, `store/schema.py`, and `tests/fakes.py` — currently ~2,400 deprecation warnings per test run, and removed in a future Python

**Checkpoint**: the existing archive is fully exploited. User Story 1's new sources now have a real baseline to improve on.

---

## Phase 0.6: Label Capture & Label-Free Validation (added 2026-08-13)

**Purpose**: end the situation where the module has no way to learn from its own operation, and start measuring the things that *can* be measured without ground truth.

Splitting [`001`'s label query](../001-evidence-generation-pipeline/issue/open%20query%20-%20AI-ML%20training%20data%20source%20and%20CCE-label%20question.md) three ways showed that only one of the three label types it carried — per-field damage magnitude — actually needs the Constitution §4 decision. Claim outcomes are a byproduct of running the system, and several useful validations need no labels at all. None of the tasks below waits on any open query.

**The sequencing point that matters**: `TV-01` must land **before** the Pilot & Validation phase (`documents/README.md` §8), not after. Otherwise the pilot runs against real claims, generates hundreds of packages, discards every outcome, and the label question is exactly as open a year later. Today there is no outcome field on `EvidenceRequest` and no outcome endpoint in the contract, so the module produces evidence and throws away the only labels it will ever get for free.

### Label capture

- [ ] TV-01 Record claim outcomes: a `claim_outcomes` table FK'd to `evidence_requests` (outcome category, optional assessed loss fraction, assessment source, recorded-at) plus a `POST /evidence-requests/{request_id}/outcome` endpoint. **Channel-agnostic per Constitution §5** — accepts a small closed enum describing what happened to the claim, never a caller's claim schema, policy fields, or farmer identifiers; same opacity discipline as `external_reference_id`, and the same minimal-personal-data posture adopted for supplementary-evidence attachments. Does not re-run the pipeline or alter any issued package
- [ ] TV-01a **Constitution §4 gate on the outcome endpoint** — `assessment_source` mandatory whenever `assessed_loss_fraction` is supplied, validated against an `AUTHORIZED_OUTCOME_SOURCES` allowlist, `422` and **no write** when the source is unauthorised. `CCE_DERIVED` is an explicit enum member absent from the default allowlist. **Must ship with TV-01, not after it**: this endpoint is deliberately sequenced ahead of the §4 decision, so without the gate it is an ungated ingress for exactly the data that decision governs — arriving unlabelled, since a caller with no `CCE_DERIVED` option to declare would simply send `INSURER_ASSESSED`. Config entry in `src/evidence_intelligence/config.py`, validation in `api/routes.py`
- [ ] TV-02 Export a training set from captured outcomes in `scripts/train_ai_ml_model.py`'s existing CSV format (one column per `FEATURE_NAMES` plus `damage_fraction`), joining each request's recorded feature vector to its outcome. Closes the loop: once `TV-01` has run long enough, training becomes the two-command operation `001`'s issue file already describes, with no new code. Requires the per-request feature vector to be persisted — check `model_component_results.component_inputs` covers it before assuming

### Validation that needs no labels

- [ ] TV-03 [P] **Negative controls / specificity harness**: run the pipeline over fields with no claimed event and measure the rate at which it reports damage. If unaffected fields score like claimed ones, something is wrong — and this is measurable with no ground truth, since the only input needed is fields nobody claimed on. Directly tests the cloud-over-field failure mode `T0-07` addresses, and would have caught the fabricated-signal defects Phase 0 fixed
- [ ] TV-04 [P] **Reproducibility check**: same request, re-run later, yields an identical package (modulo timestamps). Constitution Principle I asserts this and nothing verifies it — and it is *not* obviously true today, since GEE composites are medians over windows whose contents can change as collections are reprocessed
- [ ] TV-05 [P] **Ablation harness**: measure whether adding or removing a feature changes the output at all. Cannot show a feature is *better* without labels, but "changes nothing" is decisive and cheap — and it is the honest, available version of what User Story 3's independent test is trying to do while `D2` is open

**Checkpoint**: operating the module now generates labels instead of discarding them, and its false-positive rate, reproducibility, and feature sensitivity are measurable today rather than after the pilot.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add this feature's dependencies and module skeletons on top of the already-running `001` service

- [ ] T001 Add new dependencies to `src/pyproject.toml`: `torch` (Presto inference, research.md §1), `openeo` (WorldCereal/Copernicus Data Space client, research.md §3), `requests` (Bhoonidhi API client), `boto3` (ECOSTRESS AWS Open Data Registry access, research.md §6.2)
- [ ] T002 [P] Create module skeletons with `__init__.py` exports: `src/evidence_intelligence/ingestion/source_registry.py`, `src/evidence_intelligence/ingestion/bhoonidhi_client.py`, `src/evidence_intelligence/ingestion/commercial_tasking_client.py`, `src/evidence_intelligence/ingestion/crop_calendar_crosscheck.py`, `src/evidence_intelligence/models/foundation_features.py`, `src/evidence_intelligence/models/confidence_tier.py`, `src/evidence_intelligence/models/thermal_stress.py`, `src/evidence_intelligence/models/red_edge_indices.py`, `src/evidence_intelligence/models/field_boundary_assist.py`
- [ ] T003 [P] Add new environment/config entries (`PRESTO_MODEL_PATH`, `WORLDCEREAL_ENDPOINT`, `BHOONIDHI_API_KEY`, `ECOSTRESS_AWS_REGION`, `COMMERCIAL_TASKING_ENABLED` default `false`) in `src/evidence_intelligence/config.py` — no Planet/Maxar/ICEYE credentials configured by default per the free-only decision (`issue/`, resolved)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema and persistence extensions that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Extend database schema per `data-model.md`: new columns on `satellite_analysis_results` (`source_class`, `access_model`, `considered_not_used`), `evidence_packages` (`confidence_tier`, `confidence_tier_guidance`, `cce_non_equivalence_statement`), and `model_component_results` (`red_edge_index_type`, `red_edge_index_value`); new tables `foundation_model_feature_sets`, `crop_calendar_cross_checks`, `supplementary_evidence_attachments`, `thermal_stress_signals` — as SQLAlchemy models + Alembic migration in `src/evidence_intelligence/store/schema.py`. **Fold in `T0-08` (per-source satellite rows) and `T0-16` (package lineage) so the schema migrates once.** Note three `data-model.md` changes made 2026-08-13 after this task was written: `crop_calendar_cross_checks` carries a three-state `outcome` enum rather than a boolean `discrepancy_flag` (plus `reference_accuracy`/`pure_pixel_count`); `supplementary_evidence_attachments` has no `caller_supplied_metadata` column; `thermal_stress_signals` carries `overpass_local_solar_time`/`baseline_overpass_window`
- [ ] T005 [P] Extend `EvidenceStore` persistence layer for all new/extended entities, enforcing the non-null provenance/tier constraints from `data-model.md` (including `cce_non_equivalence_statement = true` when `confidence_tier = LOW`, and non-null provenance on `thermal_stress_signals` rows even when `pass_available = false`) in `src/evidence_intelligence/store/evidence_store.py`

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Trustworthy Evidence During Monsoon Cloud Cover (Priority: P1)

> **Sequencing note (2026-08-13)**: this was the MVP. It is now 2nd in the Wave 3 order — gated on **D3**, and preceded by `T05-01`/`T05-02` so its new sources have a baseline worth beating. Still the larger capture-quality win; just not the shortest path to a demonstrable one.

**Goal**: Prioritize cloud-penetrating SAR and, where in scope, higher-resolution sources so monsoon-season and small-field claims produce a usable evidence package instead of going dark from sensor blindness.

**Independent Test**: Submit a request for a field/event-date window with full optical cloud cover; verify the resulting package sources SAR (and any authorized enhanced source) rather than reporting insufficient data solely due to cloud cover (`quickstart.md` Scenario 1).

### Tests for User Story 1

- [ ] T006 [P] [US1] Unit test for source-selection priority logic (cloud-cover-aware SAR fallback, small-field resolution threshold) in `src/tests/unit/test_source_registry.py`
- [ ] T007 [P] [US1] Integration test for `quickstart.md` Scenario 1 (cloud-covered window → SAR-sourced package, graceful degradation when no enhanced source available) in `src/tests/integration/test_monsoon_sar_fallback.py`

### Implementation for User Story 1

- [ ] T008 [P] [US1] Implement Satellite Source Registry (catalog of baseline + enhanced sources with resolution, revisit cadence, sensor type, access model) in `src/evidence_intelligence/ingestion/source_registry.py` per `research.md` §2
- [ ] T009 [P] [US1] Implement Bhoonidhi client for ISRO's free sovereign sources (Resourcesat-2A LISS-4, EOS-04/RISAT-1A) — not covered by `gee_client.py` — in `src/evidence_intelligence/ingestion/bhoonidhi_client.py` per `research.md` §6.3 (depends on T001, T003)
- [ ] T010 [US1] Extend Imagery Ingestion to consult `source_registry` for SAR-priority/enhanced-source selection based on cloud-cover availability and field-size threshold, falling back to the `001` baseline pipeline when no enhanced source is available in `src/evidence_intelligence/ingestion/imagery.py` (depends on T008, T009)
- [ ] T011 [US1] Record `source_class`/`access_model`/`considered_not_used` provenance on every `SatelliteAnalysisResult` row, including sources evaluated but not used, in `src/evidence_intelligence/ingestion/imagery.py` (depends on T004, T010)
- [ ] T012 [US1] Surface `sources_used`/`sources_considered_not_used` in the evidence package per `contracts/evidence-request-api-extensions.md` in `src/evidence_intelligence/packaging/report_generator.py` (depends on T011)
- [ ] T042 [US1] **Declare each registry source's spectral bands, and refuse to compute an index the selected source cannot support** (FR-021) — in `src/evidence_intelligence/ingestion/source_registry.py` and `imagery.py` (depends on T008, T010). Not hypothetical: the free enhanced tier this rollout depends on, Resourcesat-2A LISS-4, carries green/red/NIR only — no SWIR, no red-edge — so selecting it for resolution silently removes the bands LSWI, NDWI and NDRE are computed from. Without this check the pipeline would emit an index under its established name from bands that cannot produce it. A source that improves resolution while dropping bands is a partial substitute, and selection must treat it as one, falling back per FR-003
- [ ] T043 [US1] **Record the producing sensor per index value, and never present cross-sensor values as directly comparable without a documented harmonization** (FR-020) — in `src/evidence_intelligence/ingestion/imagery.py` and `packaging/report_generator.py` (depends on T011, T042). Where no harmonization exists for a sensor pair, either confine the comparison to one sensor or disclose it as cross-sensor and unharmonized. Bites hardest on the pre/post comparison that is this module's core measurement: a Sentinel-2 pre-event value differenced against a LISS-4 or Landsat post-event value is not a like-for-like change, and reporting it as one would put an artefact of sensor difference into an evidence package as observed crop damage

**Checkpoint**: User Story 1 fully functional and independently testable — this is the MVP.

---

## Phase 4: User Story 2 - Tiered Confidence With an Explicit Fallback Path (Priority: P2) 🎯 MVP

> **Sequencing note (2026-08-13)**: now 1st in the Wave 3 order and the MVP. Gated only on **D1**, where the other stories each wait on a decision *and* on preparatory work — and a plain-language tier is what makes every other figure in the package usable by a non-technical reviewer.

**Goal**: Classify every evidence package into a plain-language confidence tier (High/Medium/Low), derived from existing ensemble confidence, with an explicit non-equivalence-to-CCE statement and optional supplementary-evidence attachment for the lowest tier.

**Independent Test**: Generate packages across a range of underlying confidence scores and verify each resolves to the correct tier label with tier-appropriate guidance text and, for the lowest tier, a non-equivalence statement (`quickstart.md` Scenario 2).

### Tests for User Story 2

- [ ] T013 [P] [US2] Contract test for `confidence_tier`/`confidence_tier_guidance`/`cce_non_equivalence_statement` fields against `contracts/evidence-request-api-extensions.md` in `src/tests/contract/test_confidence_tier.py`
- [ ] T014 [P] [US2] Contract test for `POST /evidence-requests/{request_id}/supplementary-evidence` against `contracts/evidence-request-api-extensions.md` in `src/tests/contract/test_supplementary_evidence_post.py`
- [ ] T015 [P] [US2] Integration test for `quickstart.md` Scenario 2 (high/low confidence tiers, non-equivalence statement, supplementary-evidence attachment) in `src/tests/integration/test_confidence_tier_fallback.py`

### Implementation for User Story 2

- [ ] T016 [P] [US2] Implement Confidence Tier classifier (derives HIGH/MEDIUM/LOW from existing per-component/ensemble confidence per `modeling-approach.md` §5, §7) in `src/evidence_intelligence/models/confidence_tier.py` per `research.md` §4
- [ ] T017 [US2] Wire confidence tier, guidance text, and `cce_non_equivalence_statement` into `EvidencePackage` generation, enforcing the non-equivalence statement whenever tier is `LOW`, in `src/evidence_intelligence/packaging/report_generator.py` (depends on T016, T004)
- [ ] T018 [US2] Implement `POST /evidence-requests/{request_id}/supplementary-evidence` endpoint (accepts `attachment_type` and `uri` only, never validated against a specific channel schema) in `src/evidence_intelligence/api/routes.py` (depends on T004, T005). **`caller_supplied_metadata` was removed 2026-08-13** — do not reintroduce it; it was an unread personal-data ingress (`issue/`, provisional default). `uri` is restricted to the module's own object store or a configured allowlist and is never dereferenced
- [ ] T019 [US2] Add validation/error handling for the supplementary-evidence endpoint (`400` on missing `attachment_type`/`uri`, `404` on unknown `request_id`) in `src/evidence_intelligence/api/routes.py` (depends on T018)

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Foundation-Model-Augmented Damage & Yield-Loss Accuracy (Priority: P3)

**Goal**: Add open geospatial foundation-model embeddings (Presto) as an additive, disclosed feature source for Component 2, falling back to the existing hand-crafted feature set when unavailable.

**Independent Test**: Train/evaluate Component 2 with and without the added embeddings on the same held-out split and compare MAE/RMSE/NRMSE; disable the embedding source and confirm the pipeline still completes using the existing feature set (`quickstart.md` Scenario 3).

### Tests for User Story 3

- [ ] T020 [P] [US3] Unit test for foundation-model feature extraction and fallback behavior (missing/invalid `PRESTO_MODEL_PATH`) in `src/tests/unit/test_foundation_features.py`
- [ ] T021 [P] [US3] Integration test for `quickstart.md` Scenario 3 (train with/without embeddings, compare validation metrics; fallback disclosure when source unavailable) in `src/tests/integration/test_foundation_model_augmentation.py`

### Implementation for User Story 3

- [ ] T022 [P] [US3] Implement foundation-model feature extraction (Presto embedding inference, versioned per Constitution Principle I) in `src/evidence_intelligence/models/foundation_features.py` per `research.md` §1 (depends on T001)
- [ ] T023 [US3] Extend the AI/ML Damage & Yield-Loss Model to accept foundation-model embeddings as an additive feature source alongside its existing hand-crafted features, falling back to the existing feature set alone when the embedding source is unavailable, in `src/evidence_intelligence/models/ai_ml.py` (depends on T022)
- [ ] T024 [US3] Record `FoundationModelFeatureSet` (`model_name`/`model_version`/`status`) per request in `src/evidence_intelligence/pipeline.py` (depends on T004, T023)
- [ ] T025 [US3] Surface `foundation_model_features` disclosure in the evidence package per `contracts/evidence-request-api-extensions.md` in `src/evidence_intelligence/packaging/report_generator.py` (depends on T024)

**Checkpoint**: User Stories 1, 2, and 3 all work independently.

---

## Phase 6: User Story 4 - Independent Crop-Type and Calendar Cross-Check (Priority: P4)

**Goal**: Independently verify a claim's declared crop type/calendar against an open crop-type mapping product (WorldCereal), flagging — not silently resolving — discrepancies.

**Independent Test**: Submit claims with matching and mismatching declared/observed crop type or calendar and verify the discrepancy flag is raised only for genuine mismatches (`quickstart.md` Scenario 4).

### Tests for User Story 4

- [ ] T026 [P] [US4] Integration test for `quickstart.md` Scenario 4 (matching and mismatching crop-type/calendar cases) in `src/tests/integration/test_crop_calendar_crosscheck.py`

### Implementation for User Story 4

- [ ] T027 [P] [US4] Implement WorldCereal-based crop-type/calendar cross-check client (via `openeo`/Copernicus Data Space Ecosystem) in `src/evidence_intelligence/ingestion/crop_calendar_crosscheck.py` per `research.md` §3 (depends on T001)
- [ ] T028 [US4] Wire the cross-check into pipeline orchestration, persisting `CropCalendarCrossCheck` with its three-state `outcome` (`CONSISTENT`/`INCONCLUSIVE`/`DISCREPANT`) plus `reference_accuracy` and `pure_pixel_count`, in `src/evidence_intelligence/pipeline.py` (depends on T004, T027). `DISCREPANT` MUST be unreachable when the reference product has no class covering the field, when pure-pixel count is below the configured minimum, or when accuracy is unestablished for that crop/region — those resolve to `INCONCLUSIVE` (`data-model.md`, and the provisional default in `issue/`)
- [ ] T029 [US4] Surface `crop_calendar_cross_check` in the evidence package per `contracts/evidence-request-api-extensions.md` in `src/evidence_intelligence/packaging/report_generator.py` (depends on T028)

**Checkpoint**: All four original user stories independently functional.

---

## Phase 7: User Story 5 - Thermal and Red-Edge Stress Signals for Drought and Heatwave Claims (Priority: P5)

**Goal**: Formalize dedicated red-edge vegetation indices (NDRE) and add NASA ECOSTRESS canopy-temperature data as an additive water-stress signal, scoped to `drought`/`heatwave` requests, where the pipeline currently has no thermal signal at all.

**Independent Test**: Submit drought/heatwave claims and verify the package includes named red-edge indices and, where an ECOSTRESS pass is available, a thermal water-stress signal; verify graceful fallback when no pass is available (`quickstart.md` Scenario 6).

### Tests for User Story 5

- [ ] T030 [P] [US5] Unit test for red-edge index computation (NDRE from Sentinel-2 red-edge bands) in `src/tests/unit/test_red_edge_indices.py`
- [ ] T031 [P] [US5] Unit test for ECOSTRESS ingestion and pass-availability fallback (`pass_available: false` case) in `src/tests/unit/test_thermal_stress.py`
- [ ] T032 [P] [US5] Integration test for `quickstart.md` Scenario 6 (red-edge + thermal signal present, ECOSTRESS-unavailable fallback, non-drought/heatwave peril scoping) in `src/tests/integration/test_thermal_red_edge_signals.py`

### Implementation for User Story 5

- [ ] T033 [P] [US5] Implement red-edge index computation (NDRE, with Chlorophyll Index Red-Edge/MTCI as disclosed alternatives), replacing the generic "red-edge index" placeholder, in `src/evidence_intelligence/models/red_edge_indices.py` per `research.md` §6.1
- [ ] T034 [P] [US5] Implement ECOSTRESS canopy-temperature ingestion (AWS Open Data Registry, `boto3`), scoped to `drought`/`heatwave` peril types, in `src/evidence_intelligence/models/thermal_stress.py` per `research.md` §6.2 (depends on T001)
- [ ] T035 [US5] Wire red-edge index and `ThermalStressSignal` computation into pipeline orchestration, persisting both (with `pass_available = false` recorded rather than skipped when no ECOSTRESS pass exists) in `src/evidence_intelligence/pipeline.py` (depends on T004, T033, T034)
- [ ] T036 [US5] Surface `red_edge_index`/`thermal_stress_signal` in the evidence package per `contracts/evidence-request-api-extensions.md` in `src/evidence_intelligence/packaging/report_generator.py` (depends on T035)
- [ ] T044 [US5] **Record each ECOSTRESS pass's local solar time and compare only against time-matched baseline observations** (FR-023) — populate `overpass_local_solar_time`/`baseline_overpass_window`, and reject or widen a baseline whose overpass times don't match, in `src/evidence_intelligence/models/thermal_stress.py` (depends on T004, T034). `T004` adds the columns but nothing currently computes or enforces the constraint, so the signal could ship with the fields unpopulated and the deviation still wrong. ECOSTRESS is non-sun-synchronous by design — that irregular sampling is the point of the mission — so a deviation taken across mismatched overpass times measures the diurnal temperature cycle rather than crop water stress, and would be irreproducible in Constitution Principle I's sense

**Checkpoint**: All five user stories independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories, plus deferred/lower-priority work

- [ ] T037 [P] Implement commercial tasking client (isolated, vendor-agnostic interface for Planet/Maxar/ICEYE-class tasking requests), gated off by default via `COMMERCIAL_TASKING_ENABLED`, in `src/evidence_intelligence/ingestion/commercial_tasking_client.py` per `research.md` §5 — **deferred, not part of any near-term critical path** per the free-only decision (`issue/`, resolved); retained as a disabled stub so a future budget decision needs only a config change
- [ ] T038 [P] Implement optional field/damage-boundary segmentation assist (FR-014, SHOULD-priority; human-in-the-loop only, given the documented SAM2 remote-sensing domain gap, `documents/research/satellite-parity-global-precedent-research.md` §4.2) in `src/evidence_intelligence/models/field_boundary_assist.py`
- [ ] T039 [P] Add unit tests for graceful-degradation edge cases (no enhanced source available, foundation-model source deprecated, SAR/optical disagreement surfaced rather than silently resolved, ECOSTRESS unavailable) in `src/tests/unit/test_graceful_degradation.py`
- [ ] T040 [P] Update `GUIDE.md` with operational instructions for the new capabilities (source registry configuration, Bhoonidhi setup, confidence-tier interpretation, foundation-model training, thermal/red-edge signals, commercial-tasking gating)
- [ ] T045 [P] **Report the lowest-tier rate stratified by field-size band, agro-climatic zone and season** (SC-007), not only as an aggregate. Both drivers of a low tier — small fields and monsoon cloud cover — correlate with the smallholder population this module exists to serve, so an aggregate figure can hold steady while the tier systematically disadvantages that group. The stratification is what makes that visible; SC-007 asserts the measurement, not a target value for it (depends on T017)
- [ ] T041 Run `quickstart.md` validation across all 7 scenarios end-to-end against a deployed instance

---

## Delivery Sequence (added 2026-08-13)

The phases above are grouped by *what* they change. This section is the ordering across them — three waves, ordered by dependency rather than by priority label, plus the decisions that gate each.

### Gates — decisions, not code

Three entries in [`issue/`](./issue/README.md) block work below. None can be resolved by inference from existing documents, which is why they're tracked rather than implemented.

| Gate | Decision | Unblocks |
|---|---|---|
| **D1** | How the confidence tier is defined ([`confidence tier threshold values`](./issue/open%20query%20-%20confidence%20tier%20threshold%20values%20%28FR-004%29.md)) | `T0-05`, `T016`, User Story 2 in full. **Most urgent** — the longest dependency chain runs through it |
| **D2** | Where validation labels come from ([`what the parity claim is validated against`](./issue/open%20query%20-%20what%20the%20parity%20claim%20is%20validated%20against%20%28SC-002%2C%20US3%29.md)) | User Story 3 (`T020`–`T025`), SC-001, SC-002 — and any measurable meaning for "parity" |
| **D3** | Whether SAR is reached for non-flood perils ([`SAR damage semantics`](./issue/open%20query%20-%20SAR%20damage%20semantics%20for%20non-flood%20perils%20%28FR-001%29.md)) | `T010` and User Story 1's stated value; without it US1 ships better provenance on the same coverage |

Three further decisions are filed but off the critical path: crop cross-check harm posture (before US4), package supersession (before US2's guidance text ships), and attachment metadata handling (before `T018`).

### Wave 1 — make the instrument measure (Phase 0, blocking)

`T0-13` first: it's cheap and it tests the premise everything else rests on, that `001` actually runs. Then `T0-07` → `T0-09` on the critical path. `T0-10`, `T0-11` in parallel. `T0-05` waits on **D1**. `T0-06` splits — its spatial term is independent, its temporal term wants the break-point date `T05-05` produces, so either split the task or sequence that half after Wave 2.

**Exit criterion**: two requests with materially different evidence quality produce materially different confidence figures. They currently cannot — `combined_confidence` is a constant 0.50.

### Wave 2 — extract what the archive already holds (Phase 0.5, not blocking)

`T05-06` leads: every Wave 3 story adds an external dependency to an execution path that loses requests on restart. `T05-01`/`T05-02` before US1, so its new sources have a real baseline to beat. `T05-04` is the highest-leverage item in the whole roadmap. `T05-03`, `T05-07` anytime.

**Exit criterion**: a partially-damaged field is distinguishable from a uniformly-stressed one in the package. Today both reduce to the same mean.

### Wave 3 — the feature stories, reordered

Phases 1 and 2 run first and unchanged. The story order below differs from `spec.md`'s P1–P5, which were assigned before the base-pipeline state was known:

| Order | Story | Moved because | Gate |
|---|---|---|---|
| 1st | **US2** — confidence tiers (`T013`–`T019`) | Was P2. Tiering makes every other output legible to a reviewer, and it's the only story whose value depends on neither new sources nor labels | D1 |
| 2nd | **US1** — SAR-priority sourcing (`T006`–`T012`) | Was P1. Still high value, but `T05-01`/`T05-02` should land first, and D3 decides whether it reaches its headline hailstorm/cloudburst cases at all | D3 |
| 3rd | **US5** — thermal + red-edge (`T030`–`T036`) | Was P5. Genuinely independent of every other story, so it moves up freely. Ship with FR-023's overpass-time handling, not without it | — |
| 4th | **US3** — foundation-model features (`T020`–`T025`) | Was P3. Cannot be evaluated without labels; adding embedding dimensions to a model with none changes nothing measurable. Follows D2 and `T05-05` | D2 |
| 5th | **US4** — crop cross-check (`T026`–`T029`) | Was P4, stays last. The only capability whose failure mode harms an identifiable individual, and the roadmap values it least — a poor trade to ship early | Harm posture |

**Exit criterion**: `quickstart.md` Scenarios 1–6, as already written.

### Critical path

```
D1 ──→ T0-07 ──→ T0-09 ──→ T0-05 ──→ US2
       (cloud     (evidence   (real      (tiers in
        masking)   manifest)   confidence) every package)
```

Everything else parallelises around this. `T0-07` does not strictly wait on D1 and should start immediately — it's the one item on the chain that is unambiguously correct work however D1 resolves.

### Start here

1. **Raise D1** — longest chain behind it, needs no engineering input to decide
2. `T0-13` — verify PostGIS
3. `T0-07` — cloud masking, regardless of D1
4. `T05-07` — deprecation cleanup, as filler

Then `T0-09` once coverage figures exist to put in a manifest; `T0-10`/`T0-11` in parallel; `T05-06` before any external dependency lands; and raise **D2**/**D3** in time not to stall Waves 2 and 3.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Base-Pipeline Corrections (Phase 0)**: No dependencies. `T0-01`–`T0-05` BLOCK Phase 2 onward; `T0-06`–`T0-11` should land before User Story 1. `T0-05` is itself gated on the confidence-tier query in [`issue/`](./issue/README.md)
- **Evidence-Processing Improvements (Phase 0.5)**: Not blocking, but `T05-01`/`T05-02` should precede User Story 1 (they determine what its new sources are improving *on*), and `T05-05` should precede User Story 3 (it produces the timeseries shape Presto consumes). `T05-06` should precede any user story that adds an external dependency — i.e. all of them
- **Label Capture & Label-Free Validation (Phase 0.6)**: No dependencies on anything in this feature, and blocked by no open query. `TV-01` must precede the Pilot & Validation phase or the pilot's labels are lost. `TV-03`–`TV-05` can run as soon as Phase 0's correctness fixes land — running them earlier measures the defects rather than the module
- **Setup (Phase 1)**: No dependencies — can start immediately once `001` is running; can run in parallel with Phase 0
- **Foundational (Phase 2)**: Depends on Setup **and on Phase 0's blocking tasks** — BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - Can proceed in parallel (if staffed) or sequentially — sequential order is the Wave 3 order above (US2 → US1 → US5 → US3 → US4), not the original P1–P5 labels
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

No user story depends on another user story — that remains true, and is what makes them independently testable. What the 2026-08-13 sequencing review added is that several depend on things *outside* this feature's story set: a gate decision, a Phase 0 correction, or a Phase 0.5 improvement. Those are what reorder them.

- **User Story 1 (P1)**: No story dependencies. Depends on **D3** for its headline cases, and on `T05-01`/`T05-02` for a baseline worth improving on
- **User Story 2 (P2)**: No story dependencies — confidence-tier computation reads existing `001` ensemble confidence, not US1's new sources. Depends on **D1**, and on `T0-05` for that confidence figure to vary at all
- **User Story 3 (P3)**: No story dependencies — Component 2 augmentation is independent of source selection and confidence tiering. Depends on **D2** (no labeled validation set exists) and benefits from `T05-05`
- **User Story 4 (P4)**: No story dependencies. Depends on the crop cross-check harm-posture decision
- **User Story 5 (P5)**: No story dependencies — red-edge/thermal signals are independent of source selection (US1), confidence tiering (US2), foundation-model features (US3), and crop cross-check (US4). No gate; ship with FR-023's overpass-time handling

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Registry/client modules before pipeline wiring
- Pipeline wiring before package-generator surfacing
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- T004/T005 in Foundational are sequential (schema before persistence layer built on it)
- Once Foundational completes, all five user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- T037/T038/T039/T040 in Polish can all run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch tests for User Story 1 together:
Task: "Unit test for source-selection priority logic in src/tests/unit/test_source_registry.py"
Task: "Integration test for quickstart.md Scenario 1 in src/tests/integration/test_monsoon_sar_fallback.py"

# Launch independent implementation modules for User Story 1 together:
Task: "Implement Satellite Source Registry in src/evidence_intelligence/ingestion/source_registry.py"
Task: "Implement Bhoonidhi client in src/evidence_intelligence/ingestion/bhoonidhi_client.py"
```

---

## Implementation Strategy

**Superseded 2026-08-13 by the Delivery Sequence section above**, which supplies the ordering these two strategies originally carried. Both are kept below because their *shape* still holds — ship one story, validate it standalone, deploy, repeat — only the entry conditions and the story order changed. Where they disagree with the Delivery Sequence, the Delivery Sequence wins.

### MVP First — now User Story 2, not User Story 1

1. Resolve **D1** (confidence tier definition) — nothing in US2 is implementable without it
2. Complete Wave 1's blocking tasks (`T0-05`, `T0-07`, `T0-08`, `T0-09`) — without them the pipeline reports "negligible" damage at a constant confidence of 0.50 on every request, and no later phase is measurable
3. Complete Phase 1: Setup
4. Complete Phase 2: Foundational (CRITICAL — blocks all stories; fold `T0-08` into `T004`)
5. Complete Phase 4: User Story 2
6. **STOP and VALIDATE**: run `quickstart.md` Scenario 2 independently
7. Deploy/demo if ready

The MVP moved from US1 to US2 because US1's value is gated on **D3** and on Wave 2's baseline work, while US2's is gated only on D1 — and because a tier is what makes every other figure in the package usable by a non-technical reviewer. US1 remains the larger capture-quality win; it is simply not the shortest path to a demonstrable one.

### Incremental Delivery

1. Wave 1 blocking tasks + Setup + Foundational → foundation ready, figures vary with the evidence
2. Add User Story 2 → validate independently → deploy/demo (MVP)
3. Add Wave 2's `T05-01`/`T05-02`/`T05-06` → the archive is properly exploited and the run path is durable
4. Add User Story 1 → validate independently → deploy/demo
5. Add User Story 5 → validate independently → deploy/demo
6. Add `T05-05`, then User Story 3 once **D2** lands → validate → deploy/demo
7. Add User Story 4 once the harm-posture decision lands → validate → deploy/demo
8. Each story still adds value without breaking previous stories or `001`'s existing behavior

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Commercial tasking (T037) ships gated off by default (`COMMERCIAL_TASKING_ENABLED=false`), decided (not just deferred) free-only for this rollout per `issue/open query - commercial satellite tasking budget and volume thresholds.md` — does not block any user story
- ECOSTRESS's irregular revisit means `pass_available = false` is an expected, normal outcome for User Story 5, not an error condition — tests (T031, T032) must cover it as a first-class case, not an edge case
- Every task in this file is additive to `001-evidence-generation-pipeline`'s existing implementation; none replace or remove existing `001` behavior
