# Satellite-Only Evidence Parity — Global Precedent & Technology Research

**Purpose:** internal source research, commissioned to ground a roadmap for pushing this module's satellite+weather evidence generation as close as technically achievable to Crop Cutting Experiment (CCE) — level verification confidence, without ingesting CCE data or any ground-crew inspection (Constitution §4 remains in force — this research informs *satellite-side* capability, it does not revisit the no-CCE boundary). Feeds [`specs/002-satellite-evidence-parity/`](../../specs/002-satellite-evidence-parity/).

**Status:** Research/reference, like [`Evidence-Collection-Generation-White-Paper.md`](Evidence-Collection-Generation-White-Paper.md) and [`Remote-Sensing-ML-Techniques-Reference.md`](Remote-Sensing-ML-Techniques-Reference.md) — optional depth, not required reading, and not itself a design spec.

**Method note:** compiled from three parallel web-research passes (August 2026). Every claim below is sourced; where a source didn't specify a figure, it was omitted rather than estimated, per this repo's no-invented-figures convention (`CLAUDE.md` Working Conventions). Vendor marketing claims are explicitly flagged as unverified where found.

---

## 1. Prior Art: Satellite-Based Verification Reducing Reliance on Manual Ground-Truthing

### 1.1 EU CAP "Checks by Monitoring" (CbM) — strongest regulatory precedent

**What it replaced:** on-the-spot physical farm inspections for CAP area-based subsidy compliance (Integrated Administration and Control System), via Commission Implementing Regulation (EU) 2018/746 amending Reg. 809/2014 Art. 40a.

**Data/method:** Sentinel-1 SAR (6-day revisit, 5m) + Sentinel-2 optical (5-day revisit, 10m) time series per declared parcel, checking declared land use/activity against observed markers (e.g., mowing, ploughing events). Can cover up to 100% of applications continuously through a season vs. the historical ~1–5% physically inspected sample.

**Outcome tiering and fallback — the key design pattern:** each parcel resolves to **green** (compliant), **red** (non-compliant), or **yellow** (inconclusive from imagery alone). Yellow triggers farmer-submitted geotagged photos, then physical on-the-spot check if still unresolved. Small parcels (<0.5 ha), extensive grazing, and greenhouse cultivation are explicitly flagged as hard to resolve remotely (European Court of Auditors Special Report 04/2020).

**Tolerated error / scale:** Commission-set tolerances of ≤5% false-red and 10–20% false-green. Field-inspection rates fell to 0.1–1.0% of monitored parcels among CbM adopters (2019 data), though adoption was partial — 15 of 66 paying agencies across 5 member states, citing conformity-clearance uncertainty and expertise gaps. May 2024 simplification reforms and Dec 2025 Council measures expanded reliance on satellite/geotagged-photo evidence, cutting required on-farm visits up to 50% where automated monitoring is used.

Sources: [ESA — Sentinels modernise CAP](https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinels_modernise_Europe_s_agricultural_policy) · [ECA Special Report 04/2020](https://op.europa.eu/webpub/eca/special-reports/new-tech-in-agri-monitoring-4-2020/en/) · [JRC CbM docs](https://jrc-cbm.readthedocs.io/en/latest/dias4cbm_intro.html) · [EU Commission, Sept 2025](https://agriculture.ec.europa.eu/media/news/satellite-tech-and-smart-data-take-root-europes-farming-future-2025-09-19_en) · [Council, Dec 2025](https://www.consilium.europa.eu/en/press/press-releases/2025/12/18/council-signs-off-simplification-of-common-agricultural-policy/)

### 1.2 ACRE Africa (Kenya, Rwanda, Tanzania, Zambia, Nigeria)

Weather/satellite-rainfall index products replace individual loss adjustment for smallholders with area/index triggers tied to M-Pesa payout. ~1.7M contracts, ~8.5M beneficiaries. **Index insurance, not satellite-only damage verification** — substitutes an area-level proxy for individual ground-truthing, accepting basis risk as the trade-off for zero-inspection-cost delivery.

Sources: [IDRC](https://idrc-crdi.ca/en/research-in-action/satellite-and-cellphone-imagery-scale-climate-smart-crop-insurance-kenya) · [Index Insurance Forum](https://www.indexinsuranceforum.org/project/acresyngenta-foundation-sustainable-agriculture-kenya-rwanda-tanzania)

### 1.3 IBLI — Index-Based Livestock Insurance (N. Kenya, Ethiopia)

Satellite NDVI (10–16 day composites) statistically correlated with historical community-level livestock mortality; payout triggers automatically above a threshold (~15% predicted mortality) — entirely ground-inspection-free by design, chosen specifically because NDVI is "objectively, cost-effectively measured and non-human-manipulable." Run by ILRI since 2011.

Sources: [ILRI — IBLI](https://ibli.ilri.org/) · [FAO STI Portal](https://sti-portal.fao.org/innovations/index-based-livestock-insurance-ibli)

### 1.4 African Risk Capacity (ARC) / Africa RiskView

Satellite rainfall estimates feed FAO's Water Requirements Satisfaction Index (WRSI), overlaid with population-vulnerability data — national-level sovereign drought parametric insurance, no farm-level ground-truthing at all since payouts go to governments. Active since 2014, up to $30M coverage/country/season for 1-in-5-year+ droughts.

Sources: [ARC methodology](https://arc.int/news/africa-riskview-methodology) · [ARC — How ARC Works](https://www.arc.int/how-arc-works)

### 1.5 USA — USDA RMA

Landsat ("forensic remote sensing," ~600 scenes/year) used for **fraud/anomaly investigation on top of** existing claims, not as a replacement for licensed loss adjusters. NASA Harvest partners on research (Virginia Tech) and a NASA-funded RF-CLASS system supports flood-loss crop assessment, but no evidence found of RMA shifting to satellite-only adjustment as primary methodology. No verifiable evidence of an operational Descartes Labs–RMA integration.

Sources: [NASA Science — Landsat fraud detection](https://science.nasa.gov/missions/landsat/saving-millions-in-government-dollars-landsat-helps-fight-crop-insurance-fraud/) · [NASA — RF-CLASS](https://appliedsciences.nasa.gov/what-we-do/projects/remote-sensing-based-flood-crop-loss-assessment-service-system-rf-class) · [Virginia Tech — NASA Harvest](https://news.vt.edu/articles/2024/01/cals_nasa.html)

### 1.6 China

Only pilot/academic evidence found: Chinese Academy of Agricultural Sciences + PICC (Shandong) applied satellite yield-estimation to regional soybean revenue insurance. No evidence of a national program comparable to YES-TECH or CbM — treat as emerging, not precedent.

Source: [Smart Agriculture journal](https://www.smartag.net.cn/EN/10.12133/j.smartag.2020.2.3.202006-SA002)

### 1.7 RIICE (IRRI-led, South/Southeast Asia — includes an India deployment)

SAR time series + the ORYZA crop-growth model map rice area/phenology and estimate yield; public-private partnership (sarmap, IRRI, Swiss Re, Swiss/German development cooperation, since 2011). Rice-area mapping validated ~90% across diverse ecosystems; yield-simulation accuracy 86–91% district level, 82–97% block level.

**India precedent:** Tamil Nadu Agricultural University + IRRI used RIICE outputs under PMFBY's prevented/failed-sowing provision, triggering claims in 529 villages (prevented sowing) and 821 villages (total crop failure) faster than conventional assessment — a real India example of satellite-triggered payout bypassing individual field verification, though scoped narrowly to sowing-failure/total-loss triggers, not general yield-loss quantification.

Sources: [sarmap — RIICE](https://www.sarmap.ch/index.php/product-services/riice/) · [ASEAN AgriFood — India](https://asean-agrifood.org/press-release-satellite-technology-expedites-insurance-payouts-in-indias-crop-insurance-programme/) · [ISPRS Archives](https://isprs-archives.copernicus.org/articles/XLII-3-W6/239/2019/)

### 1.8 Private/parametric agtech (Arbol, Planet+AXA Climate)

**Arbol**: fully parametric (PRISM, CPC, ERA5 triggers), explicitly "no adjuster, no dispute" — payout is a direct index function, sidestepping individual damage verification rather than approximating it. **Planet + AXA Climate**: Planet's satellite-derived Soil Water Content variable drives automated drought-insurance triggers, live in Brazil since 2023, expanding globally; Planet also partners with ZEP-RE for Horn of Africa drought insurance. Both are index/parametric designs (accept basis risk by design), structurally different from attempting satellite-only *replication* of individual ground-truth-quality loss assessment.

Sources: [Arbol — Agriculture](https://www.arbol.io/solutions/agriculture) · [Planet — AXA Climate](https://www.planet.com/pulse/axa-climate-leverages-planetary-variables-for-drought-insurance-through-extended-strategic-partnership/)

### 1.9 India — YES-TECH itself (baseline for comparison)

Confirmed blended, not satellite-only: 30% satellite / 70% CCE nationally mandated. A 2021 MNCFC technical report titled "Replacing CCE-yield estimates with modelled-yield estimates" signals the *stated direction of travel* toward reduced CCE dependence — but no verified figures put satellite-only estimation at CCE-equivalent confidence. This remains an open research question per MNCFC's own framing, not a solved one.

Sources: [PMFBY — Replacing CCE-yield with modelled-yield (2021)](https://pmfby.gov.in/compendium/Technology/2021%20-%20Replacing%20CCE-yield%20with%20modelled%20yield-Technical%20Report.pdf) · [PMFBY — YES-TECH](https://pmfby.gov.in/yestech/)

### 1.10 Cross-cutting pattern

Every program that achieved credible ground-truth-free (or ground-truth-reduced) verification did so via **either** (a) a tiered confidence system with an explicit fallback path (CbM), **or** (b) an area/population-level index that accepts basis risk instead of individual-farm truth (IBLI, ARC, ACRE, Arbol). No program claims satellite-only verification at individual-farm granularity matching CCE-equivalent confidence without one of those two compromises. This module already has the architectural bones for pattern (a) — see §5.

---

## 2. Satellite Data Providers & Platforms Beyond the Current Baseline

Current baseline (`Modeling-Approach.md`): Sentinel-1/2, Landsat 8/9, MODIS/Sentinel-3 OLCI, CHIRPS, ERA5-Land, IMD gridded, SMAP, SRTM, INSAT-3D — mostly via GEE.

### 2.1 Very-high-resolution commercial optical

| Provider | Resolution | Revisit | Notes |
|---|---|---|---|
| Planet PlanetScope | 3–4 m native | Daily | 200+ Dove/SuperDove cubesats; documented to improve classification on sub-600 m² Indian plots |
| Planet SkySat | 0.5 m orthorectified | Up to 10×/day (tasked) | Fine enough to visually confirm lodging/localized flooding/hail streaks within a single small plot |
| Maxar WorldView Legion | ~0.34 m pan-class | Up to 15×/day over populated areas | Commercial tasking, ~$1,200+/scene |
| Airbus Pléiades Neo | 0.3 m pan / 1.2 m MS | 2×/day anywhere | 14 km swath, tasking-based |

India's average field size is ~0.16 ha (many districts <0.7 ha) — smaller than a single 10–30 m pixel footprint in many cases, and coarse sensors produce omission-dominated errors on small fields (one study: 472 false negatives vs. 35 false positives on tiny fields). Sub-3 m sources are the only class of source that can resolve *sub-field* damage patterns, at the cost of paid tasking and narrow swaths unsuitable for blanket district-wide coverage.

### 2.2 Commercial SAR constellations

| Provider | Resolution | Revisit | Notes |
|---|---|---|---|
| ICEYE | 16–25 cm spotlight | ~20 hrs mean at equator | ~18 operational satellites (60+ launched cumulatively); dedicated flood-extent/windstorm damage products for insurance |
| Capella Space | 25 cm spotlight / sub-m strip-map | — | 36-satellite target constellation (Acadia generation) |
| Umbra | Down to 0.15 m GSD | — | Highest-resolution commercial SAR available to approved users |

Cloud/day-night independence is the whole value proposition: during monsoon-timed hail/flood/cloudburst events, tasked commercial SAR is often the *only* source imageable within hours, versus Sentinel-1's coarser free revisit.

### 2.3 ISRO / Indian sovereign sources

| Source | Resolution | Revisit | Notes |
|---|---|---|---|
| Resourcesat-2A LISS-4 | 5.8 m | 5-day | India-native alternative to Sentinel-2/Landsat |
| Resourcesat-2A LISS-3 / AWiFS | 23.5 m / 56 m | — | |
| Cartosat-3 | 0.25 m pan / 1.13 m MS / 12 m hyperspectral | — | Resolution rivals Maxar/Airbus; civilian agri-insurance tasking availability unclear from public documentation |
| EOS-04 (RISAT-1A) | C-band SAR, all-weather | 25-day nominal, 12-day inner cycle (ScanSAR) | Far coarser cadence than commercial X-band SAR, but free/sovereign |

Access: **Bhuvan** (NRSC geoportal, visualization + free thematic products) and **Bhoonidhi** (ISRO's open-data hub, archive since 1986, also redistributes Sentinel/Landsat regionally). Value is sovereignty and zero cost, not superior temporal/spatial performance over commercial options.

### 2.4 Open aggregation platforms (complementing GEE)

**Copernicus Data Space Ecosystem** (ESA's official full/free/open Sentinel gateway, direct API/bulk access), **NASA Earthdata/EOSDIS** (full NASA EO catalog), **USGS EarthExplorer** (Landsat archive since 1972 — best for long historical baselines). USGS and ESA actively collaborate to keep both jointly free and open.

### 2.5 Hyperspectral

**EnMAP** (DLR) / **PRISMA** (ASI): 30 m resolution, ~30 km swath, ~200+ narrow bands (420–2450 nm). Enable biochemical retrieval (canopy nitrogen, water-stress absorption features) beyond broadband indices, complementary to Sentinel-2 in fusion studies — but 30 m resolution, narrow swath, and non-daily tasking make them impractical as a standalone per-field source on sub-hectare plots; better as a research/calibration layer.

**Pixxel Firefly** (India-based startup): 5 m, ~24-hr revisit, 135+ bands — a meaningful resolution jump over EnMAP/PRISMA and India-domiciled. *Flagged: vendor claims (e.g., "detects crop disease three weeks early") are marketing, not independently validated at operational scale — worth tracking, not yet evidence-grade.*

### 2.6 The ceiling — what no satellite source reliably captures

Sub-canopy conditions (root-zone waterlogging duration, soil-level damage), pre-visible-symptom pest/disease onset, grain quality/moisture, and actual harvested yield. All satellite signals are *correlates* of biomass/stress, not direct yield measurements — published defoliation-detection accuracy tops out around 81–85%. This is the structural gap CCE physically closes by cutting and weighing crop; no combination of remote-sensing sources eliminates it, only narrows it. This ceiling is why §1.10's pattern (a)/(b) compromise is structural, not a temporary technology gap.

---

## 3. Physical Factors Affecting Satellite Data Capture Quality

- **Monsoon cloud cover**: optical revisit is frequently unusable during Kharif season — documented 90–92% cloud cover in July–August in monsoon-affected regions left 23–25% of surface water area unmappable by optical alone, driving the need for SAR-optical fusion.
- **Revisit vs. resolution trade-off / latency**: free 10–30 m sensors offer better cadence than most VHR optical, but neither guarantees a *usable* (cloud-free) pass near a claimed event; commercial tasking narrows this at cost. Event-to-usable-image latency is the operational bottleneck the industry is actively engineering around, not a solved problem.
- **SAR-specific factors**: speckle noise (inherent to coherent imaging) requires filtering; temporal decorrelation is severe over vegetation (sub-wavelength leaf/branch movement decorrelates the signal between passes); incidence angle changes sensitivity by polarization and crop stage; side-looking geometry causes layover/foreshortening. Powerful for change/flood detection, noisier for fine classification than optical.
- **Mixed-pixel effects**: Indian field sizes averaging ~0.16 ha routinely fall below a single 10–30 m pixel, degrading classification and change detection — a fundamental ceiling for the existing baseline sensors, relieved only by ≤5 m sources.
- **Atmospheric correction**: essential for multi-temporal comparison; documented satellite-vs-ground reflectance discrepancies of 39–97% pre-correction, with residual uncertainty up to ~10% in vegetation indices even post-correction.
- **Sun-angle/BRDF effects**: reflectance varies with sun-sensor-target geometry independent of actual crop condition; normalization (Ross-Li/Walthall BRDF models) is required or apparent "change" can be a geometry artifact.
- **Cross-sensor harmonization**: combining Landsat, Sentinel-2, and commercial sources requires bandpass adjustment, BRDF normalization, co-registration (NASA's HLS product formalizes this); sensor calibration drift over an operational lifetime (flagged for Landsat-8) requires ongoing monitoring.
- **Data latency**: "near-real-time" claims processing is an active industry goal contingent on priority tasking agreements — implying baseline (non-tasked) latency remains a real constraint.

Sources: [SkySat docs](https://docs.planet.com/data/imagery/skysat/) · [orbitalradar.com](https://orbitalradar.com/satellites/operator/planet-labs) · [ICEYE eoPortal](https://www.eoportal.org/satellite-missions/iceye-constellation) · [ICEYE vs Capella](https://spacenexus.us/compare/iceye-vs-capella-space) · [Resourcesat-2 eoPortal](https://www.eoportal.org/satellite-missions/resourcesat-2) · [EOS-04](https://en.wikipedia.org/wiki/EOS-04) · [Cartosat-3 eoPortal](https://www.eoportal.org/satellite-missions/cartosat-3) · [Copernicus Data Space](https://dataspace.copernicus.eu/) · [Bhoonidhi](https://bhoonidhi.nrsc.gov.in/) · [EnMAP/PRISMA fusion](https://www.tandfonline.com/doi/abs/10.1080/01431161.2026.2612849) · [Pixxel eoPortal](https://www.eoportal.org/satellite-missions/pixxel) · [Telangana field mapping](https://arxiv.org/pdf/2507.05189) · [Radar vs optical, India](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11760589/) · [SAR temporal decorrelation](https://www.sciencedirect.com/science/article/pii/S0034425722003169) · [Atmospheric correction](https://nhess.copernicus.org/articles/10/89/2010/) · [BRDF normalization](https://ieeexplore.ieee.org/document/1221801/) · [HLS](https://ntrs.nasa.gov/api/citations/20190028663/downloads/20190028663.pdf) · [WorldView Legion](https://www.eoportal.org/satellite-missions/worldview-legion) · [Crop loss ML](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0251952) · [Seeing Risk from Space](https://spaceinsider.tech/2025/10/11/seeing-risk-from-space-how-eo-satellites-power-modern-crop-insurance/)

---

## 4. Open/Open-Weight AI Models

### 4.1 Geospatial foundation models

| Model | Org | License | Modality | Status |
|---|---|---|---|---|
| **Prithvi-EO-2.0** (300M/600M) | NASA/IBM/Jülich | Apache-2.0, weights on HF | Optical (HLS) | Production-ready, actively maintained |
| **Clay v1.5** (632M) | Clay Foundation/Development Seed | Apache-2.0 | Multi-sensor: S1 SAR + S2 + Landsat + NAIP | Production-ready, actively maintained |
| **Presto** | NASA Harvest | MIT | Per-pixel timeseries: S1+S2+weather+DEM+ERA5 | Production-proven — backbone of ESA WorldCereal (§4.3) |
| **SSL4EO-S12** | TUM/DLR | Apache-2.0 (code), CC-BY-4.0 (weights) | S1+S2 pretraining | Actively maintained (v1.1, 2025) |
| SatMAE | Stanford | License unconfirmed | Temporal + multispectral | Research reference, less actively maintained — verify license before use |
| AlphaEarth Foundations | Google DeepMind | CC-BY-4.0 (**output embeddings only** — model weights not open) | 10m annual global embeddings | Active, but a data dependency on Google infra, not an offline open-weight model |
| FarmVibes.AI | Microsoft | MIT | Workflow/orchestration platform, not a pretrained model | Reference architecture only |

**Fit for this module:** Presto is the strongest direct fit — purpose-built for exactly the S1+S2+weather-timeseries setup already assembled for Component 2, small enough for cheap per-field inference, and already proven in production (WorldCereal). Clay's native SAR+optical fusion is a strong candidate to replace the hand-engineered fusion currently needed between the RF/NN (Component 2) and RUE model (Component 1). Prithvi is the safest large-scale Apache-2.0 fallback if a bigger backbone is needed.

### 4.2 Segmentation for field/damage boundary delineation

**SAM2** (Meta, Apache-2.0, weights open) has a documented domain gap on remote-sensing imagery (color/texture/scale mismatch) — unreliable zero-shot on field boundaries. **RSPrompter** (Apache-2.0, SAM+MMDetection with RS-specific prompts) is research-grade, needs training on labeled RS data, no off-the-shelf field-boundary checkpoint. Current best use: human-in-the-loop assist (prompt-driven correction of a submitted field polygon, or a damage-extent polygon from a few clicks) rather than a fully automated model — would improve per-field normalization feeding the Damage Severity Index, but needs a thin fine-tuning/prompting layer.

### 4.3 Crop type / damage / flood mapping

**WorldCereal** (ESA) — open-source, production-live (2025) on Copernicus Data Space/openEO, built on Presto embeddings + CatBoost, global 10m crop type/irrigation/calendar maps. Directly usable to independently cross-check crop type and sowing/harvest windows per claimed field. **Sentinel-1 SAR flood mapping (UN-SPIDER Recommended Practice)** — fully open notebook toolkit, deterministic JRC-derived change-detection/thresholding algorithm, no license friction, mature and humanitarian-mapping-proven — usable today as a dedicated inundation evidence sub-module. **CropNet** (KDD 2024) — US county-level, license unconfirmed, not directly transferable to India; reference/benchmark only.

### 4.4 Yield/damage-specific prediction architectures

No mature, open, India-relevant, pretrained NDVI-to-yield-loss model was found. **MMST-ViT** (ICCV 2023, open code) is a usable *architecture donor* (spatiotemporal transformer) but needs full retraining on Indian PMFBY/weather data — not a drop-in model. This category is the least mature of the four; the realistic near-term path is **feature-level augmentation** (Presto/Clay/Prithvi embeddings feeding the existing RF/NN ensemble) rather than wholesale model replacement.

### 4.5 Maturity summary

- **Production-ready, permissive license, weights downloadable:** Prithvi-EO-2.0, Clay, Presto, SSL4EO-S12, WorldCereal, UN-SPIDER SAR flood toolkit, SAM2 core.
- **Open output, closed model:** AlphaEarth Foundations.
- **Research-stage, needs adaptation:** SatMAE (license unconfirmed), RSPrompter, RS-adapted SAM2 variants, MMST-ViT, CropNet (license unconfirmed).
- **Toolkit, not a model:** FarmVibes.AI.

---

## 5. Synthesis — Implications for This Module's Roadmap

1. **The ceiling is structural, not a technology gap to be closed by better satellites.** §1.10 and §2.6 agree: every credible precedent either tiers confidence with a fallback, or trades individual-farm truth for an area-level index. This module already produces per-component confidence figures and an ensemble confidence (`Modeling-Approach.md` §5, §7) — the CbM green/yellow/red pattern is a natural extension of that, not a new architecture.
2. **Cloud-blind optical during monsoon is the single biggest capture-quality risk** (§3) for exactly the events (hailstorm, flood, cloudburst) this module exists to evidence — reinforcing that SAR (existing Sentinel-1, or tasked commercial SAR for speed) is not optional, it's load-bearing for the monsoon damage cases that matter most.
3. **Resolution, not just spectral capability, is the concrete lever for closing distance to CCE-level per-field confidence** given India's ~0.16 ha average field size — sub-5 m sources (Planet, Pixxel, ISRO Resourcesat LISS-4, tasked commercial VHR) address a real, specific mixed-pixel failure mode that the current 10–30 m baseline has.
4. **The open-model landscape offers a low-risk augmentation path, not a rebuild.** Presto/Clay/Prithvi embeddings can feed Component 2 as an additive feature source alongside (not instead of) the existing hand-crafted NDVI/EVI/SAR feature set, preserving the disclosure discipline `Modeling-Approach.md` §3 already commits to.
5. **RIICE's India deployment is the most directly relevant precedent** — same country, same PMFBY program, satellite-triggered payout without individual field verification, but narrowly scoped to sowing-failure/total-loss. It's evidence the regulatory environment already tolerates satellite-only triggers for a *subset* of claim types, which is a useful wedge for where a satellite-only-confidence-sufficient tier could start.
