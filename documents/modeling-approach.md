# Evidence Intelligence Module — Modeling Approach

**Governed by:** [constitution.md](./constitution.md). **Implements:** [hld.md](./hld.md) §3 (Component Breakdown). This document is the science/methodology reference — it plays the same role for this module that Section 4 and Appendix 1 of [`yestech_manual_2023.md`](./standards/yestech_manual_2023.md) play for YES-TECH: it names each modeling component, its inputs, its method, and its validation standard.

---

## 1. Design Philosophy

`yestech_manual_2023.md` — the DA&FW/MNCFC manual governing technology-based yield estimation under PMFBY — mandates five documented modeling approaches (semi-physical, AI/ML, crop simulation, ensemble, and a parametric composite index) for area-level yield estimation blended with CCE. This module targets the same technical rigor, applied to a different problem: **per-field damage/evidence scoring for an individual claimed loss event**, not IU-level yield determination for indemnity calculation.

Concretely, this means: every component below has a real analogue in YES-TECH's own methodology — same families of models, same class of input data, same discipline around documenting hyperparameters and reporting accuracy — but re-purposed to answer "what happened to this field, and how confident are we" rather than "what is this Insurance Unit's yield this season."

Constitution §4 still governs: none of this feeds a CCE-blending formula, and no component's output is presented as an authoritative yield determination. See §9.

## 2. Component 1 — Semi-Physical Damage Model

**YES-TECH analogue:** the Radiation Use Efficiency (RUE) model (YES-TECH Manual §4.1.1, Appendix 1 §1).

**Adaptation:** YES-TECH uses the RUE chain to estimate absolute seasonal yield. This module uses the same physical chain to estimate an **expected** biomass trajectory for the submitted field, then compares it against the **observed** post-event trajectory — the deviation is the damage signal, which is more physically grounded than a raw NDVI-difference threshold.

**Method:**
- Biomass = RUE_max × Σ (from sowing to the analysis date) of (PAR × fAPAR × Water Stress × Temperature Stress)
- PAR (photosynthetically active radiation) = Daily Surface Insolation × 0.48
- Water Stress Scalar = (1 + LSWI) / (1 + LSWI_max), where LSWI = (NIR − SWIR) / (NIR + SWIR)
- Temperature Stress is a bounded function of observed temperature relative to the crop's minimum, optimum, and maximum temperature thresholds
- Yield = Biomass × Harvest Index; Harvest Index = Economic Yield / Biological Yield

**Inputs** (YES-TECH Table 7, sourced via GEE rather than direct agency feeds where equivalent):

| Data / Product | Source dataset |
|---|---|
| Daily insolation (PAR) | INSAT-3D (via MOSDAC) or equivalent GEE-hosted solar radiation product |
| fAPAR | MODIS / Sentinel-3 OLCI (8-day composite) |
| Surface reflectance, NDVI, LSWI | Sentinel-2 MSI (10–20m), Landsat 8/9 OLI (30m) |
| Crop mask / sowing date | Sentinel-1 SAR + Sentinel-2/Landsat, classified per field |
| Daily Tmin/Tmax | IMD gridded (0.5°) or ERA5-Land |

**Deliberate divergence from YES-TECH here:** YES-TECH derives Harvest Index from historical **CCE** biomass/grain-yield data (Table 7, row 6). This module does not use CCE data (Constitution §4) — Harvest Index is instead sourced from published crop-variety reference values and regional agronomic literature, clearly labeled as a modeling assumption rather than a locally-measured constant. This is a genuine accuracy trade-off versus YES-TECH's own approach, disclosed explicitly rather than silently substituted.

## 3. Component 2 — AI/ML Damage & Yield-Loss Models

**YES-TECH analogue:** AI/ML models — Random Forest, Deep Neural Networks (YES-TECH Manual §4.1.2, Appendix 1 §2).

**Method:** Supervised models (Random Forest and/or a neural network) trained to predict damage severity and yield-loss percentage from a documented feature set, following the same disclosure discipline YES-TECH mandates for its own AI/ML approach.

**Feature set** (mirrors YES-TECH Table 8):

| Category | Features | Source |
|---|---|---|
| Satellite vegetation | NDVI, EVI, red-edge index | Sentinel-2, Landsat, MODIS |
| Satellite wetness | NDWI, LSWI | Sentinel-2, Landsat |
| Radar | VH/VV backscatter, RVI | Sentinel-1 |
| Meteorological | Rainfall, rainy-day count, dry/wet-spell length, temperature, growing degree days, heat/cold wave flags | IMD, CHIRPS, ERA5 |
| Biophysical | fAPAR, LAI | MODIS, Sentinel-2/3 |
| Edaphic | Soil texture/depth, DEM, soil moisture | NBSSLUP-equivalent soil reference, SRTM, SMAP |

**Mandatory disclosure per trained model version** (matching YES-TECH §2.3):
- For neural network models: architecture, activation function, learning algorithm, learning rate, loss function, regularization criteria, training epochs, batch size.
- For tree-based models: number of trees, features considered per split, split-selection criteria, minimum leaf size.
- For every model version: accuracy reported as MAE, RMSE, and NRMSE against a held-out validation set, with the calibration/validation split documented.

Feature selection follows the same multicollinearity-check and crop-calendar-aware discipline YES-TECH requires (§2.3) — features are only included if they carry information about the specific field's growing period, not generic regional signal.

## 4. Component 3 — Crop Simulation Model Assimilation (Advanced Tier)

**YES-TECH analogue:** Crop Simulation Models — DSSAT, APSIM, InfoCrop, ORYZA, WOFOST (YES-TECH Manual §4.1.3, Appendix 1 §3).

**Adaptation:** YES-TECH treats CSM-based estimation as a full standalone approach a state can select. This module treats it as an **advanced-tier cross-validation step**, run for high-value or high-scrutiny claims rather than every request — genuinely exceeding YES-TECH's baseline by making the most rigorous component available as a strengthening layer rather than requiring a state to commit to it exclusively for an entire season.

**Method:** A calibrated crop simulation model (WOFOST or InfoCrop, for which published Indian-conditions calibrations exist) is run with locally available weather, soil, and crop-management inputs, then remote-sensing-derived state variables (LAI, soil moisture) are assimilated to update the model's internal state — the same assimilation pattern YES-TECH describes in §3.3 of Appendix 1. The CSM's yield/biomass estimate is compared against Components 1 and 2 as an independent check.

**Inputs** (YES-TECH Table 9): IMD daily weather (current + 7-year history), soil physical/chemical properties by layer, crop-management data (fertilizer, seed rate, irrigation — sourced from published agronomic references where field-level data isn't available), crop-specific genetic coefficients (literature-calibrated), and remote-sensing LAI/soil moisture for assimilation.

Calibration and validation follow YES-TECH §3.5: genetic coefficients are checked against the crop's known biological range, not fitted freely.

## 5. Component 4 — Ensemble Blending

**YES-TECH analogue:** Ensemble models — model averaging, voting, and stacking of ML + CSM outputs (YES-TECH Manual §4.1.4, Appendix 1 §4).

**This is where "more robust than YES-TECH" is concrete, not aspirational:** YES-TECH treats ensembling as *one of five choices* a state selects for an entire season. This module **always** ensembles Components 1–2 (and Component 3, where the advanced tier applies) for every single request, weighted by each component's own reported confidence/accuracy rather than a fixed a-priori split. A request is never answered by a single unvalidated model.

**Method:** Weighted averaging or stacking (consistent with YES-TECH's own recommended techniques), with weights derived from each component's validation-set accuracy (Component 2) or calibration quality (Components 1 and 3) rather than a fixed ratio. The ensemble output carries its own combined confidence figure, not just a point estimate.

## 6. Component 5 — Damage Severity Index (DSI)

**YES-TECH analogue:** Crop Health Factor (CHF) — an entropy-weighted, Min-Max-normalized composite index (YES-TECH Manual §4.1.5, Appendix 1 §5).

**Adaptation:** YES-TECH computes CHF per homogeneous group of ≥4 contiguous Insurance Units, then blends it 70/30 with CCE-yield deviation for area-level loss assessment. This module computes an analogous composite index — the **Damage Severity Index** — per submitted field geometry, normalized against that field's own multi-year historical distribution rather than a peer-IU group, and used purely as a transparent evidence score, never blended with CCE data.

**Input indicators** (mirroring YES-TECH Table 10, re-scoped to damage rather than health):

| Indicator | Relationship to DSI |
|---|---|
| Post-event NDVI deviation from pre-event/historical baseline | Positive (larger negative deviation → higher DSI) |
| Post-event LSWI deviation (moisture stress) | Positive |
| SAR VH backscatter deviation (structural/flood damage) | Positive |
| Integrated FAPAR deviation over the affected window | Positive |
| Crop condition variability (coefficient of variation of NDVI/LSWI within the field) | Negative — high internal variability reduces confidence that the whole field is uniformly affected |
| Weather anomaly magnitude (rainfall/temperature deviation for the event window) | Positive |

**Method:**
1. Normalize each indicator to [0,1] via Min-Max scaling, using the field's own historical archive as the reference range (direction-aware: indicators with a positive relationship to damage use `(x − min) / (max − min)`; the one negative-relationship indicator, crop condition variability, uses the inverted form).
2. Compute an entropy-based weight for each indicator from its distribution across the historical archive — indicators that vary more informatively across past seasons receive proportionally more weight, following the same entropy-weighting logic YES-TECH applies to CHF (Appendix 1 §5.4), rather than assigning weights by fixed rule.
3. DSI = Σ (weight_j × normalized_indicator_j).

**Explicitly not done:** no stratification into peer-IU groups (this module operates per-field, not per-IU-group — see the robustness comparison in §8), and no blending with CCE-yield deviation (Constitution §4). DSI is reported alongside, not instead of, the Component 4 ensemble yield-loss estimate — they answer different questions (severity score vs. yield-loss percentage) and are both included in the evidence package.

## 7. Validation & Accuracy Standards

Every component's outputs, on every request, carry:
- The `methodology_version` that produced them (Constitution §2).
- For Components 2 and 3: the model/calibration version's own validation-set accuracy (MAE/RMSE/NRMSE for Component 2; genetic-coefficient plausibility bounds for Component 3), matching YES-TECH §2.3/§3.5's own bar for statistical rigor.
- For Component 4: the ensemble's combined confidence, derived from its inputs' individual accuracy figures.
- For Component 5: the entropy weights used, so the DSI computation is fully reproducible from the same historical archive.

## 8. What's More Robust Than YES-TECH

| Dimension | YES-TECH | This Module |
|---|---|---|
| Granularity | Insurance Unit (Gram-Panchayat-level group) | Per submitted field geometry |
| Model selection | A state selects **one** of five approaches for an entire season | **Always** ensembles multiple components per individual request |
| Cadence | Seasonal — Inception/Mid-Season/End-of-Season reports | Near-real-time — hours to days after a claimed event, using sub-daily sources (GPM IMERG) where relevant |
| Advanced cross-validation (CSM assimilation) | Optional, selected in place of other approaches | Included as a standard advanced-tier strengthening layer alongside the others, not a replacement for them |
| Provenance/versioning | Procedural — SOP submission and MITR review cycle | Constitutional requirement baked into every single output (Constitution §2) |
| Output purpose | Yield determination, blended with CCE for indemnity | Evidence + a clearly labeled estimate supporting a claim — never an indemnity determination itself |

## 9. Explicit Boundaries

This document does not authorize CCE ingestion, CCE-blending, or MITR/TIP-style governance — see [constitution.md](./constitution.md) §4 and §6. Increasing modeling rigor here does not change what the outputs are used for.
