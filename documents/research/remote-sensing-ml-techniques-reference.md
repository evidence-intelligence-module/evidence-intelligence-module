# Remote-Sensing & ML Techniques — Evaluated from an External Platform Pitch

**Status:** Reference only — not a design spec.
**Source:** Extracted and rewritten from an external SaaS platform pitch ("ML-Powered Remote Sensing Platform for Crop Insurance Claim Verification", v1.0, August 2026) that was evaluated against this repo's active initiative and found to conflict with it on scope.

---

## 1. Why This Document Exists

A third-party pitch document proposed a general-purpose, multi-tenant SaaS platform for satellite-based crop insurance evidence. It was evaluated against [`constitution.md`](../constitution.md) and found to conflict with all three of its hard boundaries:

- It defaults to a **configurable CCE-blending ratio** (Constitution §4 excludes CCE entirely).
- It runs **continuous proactive anomaly scanning with auto-notification** to stakeholders before any loss is reported (Constitution §3 excludes standalone predictive alerting).
- It is architected as its **own end-to-end SaaS product** — tenants, dashboards, pricing tiers, claim pipeline — rather than a component behind a generic evidence-request contract (Constitution §5).

The pitch itself — tenancy model, pricing, roadmap, staffing, financial projections, and YES-TECH "compliance" framing built around CCE blending — was rejected and is not reproduced here. See `notes/decision-log.md` for the full decision record.

What survived: a set of **remote-sensing and ML techniques** that are technically sound, don't depend on CCE data or proactive alerting, and improve on gaps in this module's own [`modeling-approach.md`](../modeling-approach.md) and [`evidence-flow-spec.md`](../evidence-flow-spec.md). Those are captured below as reference material — evaluate and adopt deliberately, the same way any other research input is used; nothing here is pre-approved for implementation.

## 2. Satellite Data Ingestion Reference

| Satellite | Sensor | Resolution | Revisit | Key Products | Access |
|-----------|--------|-----------|---------|-------------|--------|
| Sentinel-1 | C-band SAR | 20m | 6 days | VV/VH backscatter, coherence | Copernicus Open Access |
| Sentinel-2 | MSI | 10-20m | 5 days | 13 spectral bands, L2A reflectance | Copernicus Open Access |
| Landsat 8/9 | OLI/TIRS | 30m | 8 days (combined) | Surface reflectance, thermal | USGS EarthExplorer |
| MODIS | Terra/Aqua | 250-500m | 1-2 days | NDVI, fAPAR, LAI, surface reflectance | NASA EARTHDATA |
| Planet | PlanetScope | 3-5m | Daily | 8-band surface reflectance | Commercial API |
| INSAT-3D | Imager/Sounder | 1-4km | 30 min | Insolation, cloud, SST | MOSDAC |
| SMAP | L-band radiometer | 9-36km | 2-3 days | Soil moisture | NASA |

Our module already draws on most of these via Google Earth Engine ([hld.md](../hld.md) §7); this table is kept as a consolidated spec/resolution/revisit reference.

## 3. Processing Pipeline Techniques

These address a real gap: our current pipeline ([evidence-flow-spec.md](../evidence-flow-spec.md) §3) falls back from Sentinel-2 to Landsat on cloud cover without stating how the two are made comparable, and falls back to SAR-only or `INSUFFICIENT_DATA` on persistent cloud cover without trying to fill the optical gap first.

- **Cross-sensor harmonization (HLS methodology):** align Sentinel-2 and Landsat 8/9 surface-reflectance products radiometrically before treating them as interchangeable inputs to the same NDVI/LSWI time series.
- **Cloud/shadow masking:** Sentinel-2's Scene Classification Layer (SCL) plus a supplementary CNN-based cloud/shadow detector for edge cases the SCL band misses.
- **Spatiotemporal fusion (STARFM/ESTARFM):** fuse Sentinel-2 (10m, 5-day revisit) with MODIS (250m, daily) to synthesize daily 10m imagery — a way to fill optical gaps during a claim's event window instead of falling straight back to SAR or a low-confidence path.
- **SAR-optical co-registration:** explicit co-registration of Sentinel-1 VV/VH backscatter with the Sentinel-2 optical stack before combining them as multi-source model inputs.

## 4. ML Modeling Techniques

Candidates for strengthening the five components in [modeling-approach.md](../modeling-approach.md) — none of these require CCE-derived labels or change what the outputs are used for.

- **Foundation-model crop segmentation:** a pretrained multi-temporal foundation model (e.g. Prithvi-EO-2.0-style backbone) with a CNN+GRU/LSTM temporal head, or a Segment-Anything-style adapter, for the per-field crop mask / sowing-date classification that Modeling-Approach §2 currently leaves as an unspecified input to the semi-physical model.
- **Physics-informed neural network (PINN):** embeds the RUE-chain equations (Modeling-Approach §2) as constraints in a neural network's loss function — a genuine fusion of the semi-physical and AI/ML components (§2 and §3) rather than two independent models reconciled only at the ensemble stage.
- **Transformer-based temporal modeling:** temporal attention over the multi-source time series (satellite indices + weather + soil moisture) as an alternative/addition to the RF/DNN models in Modeling-Approach §3, for capturing longer-range seasonal dependencies.
- **Per-prediction uncertainty (quantile regression / Monte Carlo dropout):** Modeling-Approach §3 currently reports only model-level accuracy (MAE/RMSE/NRMSE); this would give each individual request's estimate its own confidence interval, not just the model's aggregate accuracy figure.

## 5. Damage-Scoring Technique

Modeling-Approach §6 (Damage Severity Index) currently uses Min-Max normalization with entropy-derived weights only. An **isolation-forest + Z-score ensemble** anomaly score, computed per indicator against the field's own historical archive, is a stronger per-indicator anomaly measure — and can be computed inside the existing event-triggered flow ([evidence-flow-spec.md](../evidence-flow-spec.md) §4/§6) rather than requiring the continuous proactive scanning the source pitch wrapped it in. The technique is separable from that wrapper; only the wrapper was rejected.

## 6. Evidence Integrity Idea

**Blockchain hash-anchoring:** the source pitch anchors each evidence document's hash on a low-cost chain (e.g. Polygon) in addition to storing a checksum. Our `evidence_packages` table ([hld.md](../hld.md) §4) already records a `checksum`; anchoring that hash externally would strengthen the §65B chain-of-custody requirement (Constitution §2 item 4) without any change to module scope.

## 7. Technical Risk Notes Worth Keeping

Stripped of the SaaS-specific risks (regulatory acceptance of a technology-only platform, tenant data isolation, pricing-tier availability):

- **Cloud-cover gaps:** SAR provides all-weather observation; STARFM-style fusion (§3 above) fills optical gaps; MODIS daily coverage as a further fallback.
- **Model accuracy variance across agro-climatic zones:** region-specific fine-tuning and transfer learning from data-rich to data-sparse regions, with continuous per-region accuracy monitoring.
- **Adversarial manipulation (false claims):** multi-source cross-validation (optical + SAR + weather) and historical-baseline comparison make a single fabricated or cherry-picked signal harder to pass off as genuine damage.

## 8. What Was Deliberately Not Kept

For traceability, the following were evaluated and rejected — not overlooked:

- CCE-blending ratio / "technology-only where regulatory environment permits" framing (Constitution §4).
- Continuous proactive anomaly scanning with automatic stakeholder notification; the parametric auto-trigger that generates and sends a claim document without a reported event (Constitution §3).
- Multi-tenant SaaS architecture, role-based dashboards, API surface, pricing tiers (Constitution §5 — standalone-interface principle, not a product).
- Implementation roadmap, team/staffing plan, financial projections — business planning, not technical content, and specific to a platform this repo isn't building.
- Training-data sourcing from CCE ground truth / CROPIC labels for the crop classifier — this module cannot use CCE-derived labels (Constitution §4); if a labeled-training-data source is needed for a future foundation-model fine-tune, it must come from a non-CCE source, which is an open question for whoever picks up §4 of this document, not something resolved here.

## References

- YES-TECH Manual 2023, Department of Agriculture & Farmers Welfare, Ministry of Agriculture & Farmers Welfare, Government of India
- [Improved early-stage crop classification using fusion-based ML with Sentinel-2A and Landsat 8-9](https://link.springer.com/article/10.1007/s10661-025-14420-9)
- [Benchmarking Geospatial Foundation Models for Agriculture Applications](https://arxiv.org/html/2606.29664v1)
- [Sentinel-2 for Crop Yield Estimation: A Systematic Review](https://arxiv.org/pdf/2603.23779)
- [Satellite Data and AI: The Shift to Data-Driven Agriculture Insurance — Planet](https://www.planet.com/pulse/satellite-data-and-ai-the-shift-to-data-driven-agriculture-insurance/)
- [Seeing Risk from Space: How EO Satellites Power Modern Crop Insurance](https://spaceinsider.tech/2025/10/11/seeing-risk-from-space-how-eo-satellites-power-modern-crop-insurance/)
- [Can YES-TECH Technology in PMFBY Provide Accurate Crop Assessments — Global Agriculture](https://www.global-agriculture.com/india-region/can-yes-tech-technology-in-pmfby-provide-accurate-crop-assessments/)
- [Can Technology Fix India's Crop Insurance? — Down To Earth](https://www.downtoearth.org.in/agriculture/can-technology-make-indias-crop-insurance-payouts-more-accurate)
- [AI in Parametric Insurance: 7 Ways It Works (2026)](https://insurnest.com/blog/ai-in-parametric-insurance/)
- [AgriFM: Multi-source Temporal Remote Sensing Foundation Model for Agriculture Mapping](https://arxiv.org/pdf/2505.21357)
- [Deep Learning for Crop Mapping Using Multi-Temporal Sentinel-2 with CNN-RNN](https://doi.org/10.3390/rs17183207)
