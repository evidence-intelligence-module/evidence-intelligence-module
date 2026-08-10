# Crop Insurance Claim Intimation — Landscape Research & Phase 1 Roadmap (India)

*Prepared August 2026*

---

## 1. Pre-Plan Overview — Region: India

Crop insurance in India runs mostly under one umbrella scheme (**PMFBY**) plus a parallel weather-index scheme (**RWBCIS**) and a few smaller/state-specific programs. Claim *intimation* — the farmer reporting a loss so an assessment can start — is the single biggest failure point in the whole chain. The 72-hour intimation window is strict, and most claim rejections trace back to missed or incomplete intimation rather than the loss itself.

Two structurally different claim mechanics exist, and any product/roadmap has to design for both:

- **Farmer-initiated claims** — farmer must actively report within 72 hours (localized calamity, post-harvest loss, prevented sowing).
- **System-triggered claims** — no farmer action needed; payout is computed automatically from Crop Cutting Experiments (CCE) or weather-station/satellite data covering an entire notified area.

---

## 2. Claim Types in India

### A. "Single" / Individual Claims (farmer-triggered, farm-level assessment)
Assessed at the individual insured farm, not the village.

| Type | Trigger | Intimation window | Assessment method |
|---|---|---|---|
| **Localized calamity claim** | Hailstorm, landslide, inundation, cloudburst, natural fire (isolated, not a widespread event) | 72 hours from occurrence | On-farm inspection / satellite + physical verification |
| **Post-harvest loss claim** | Damage to cut & spread crop within 14 days of harvest, from cyclone/unseasonal rain (only for crops where "dry in field" is allowed) | 72 hours from occurrence | Individual farm assessment |
| **Prevented / failed sowing claim** | Farmer unable to sow the notified crop due to adverse weather before the sowing window closes | 72 hours from end of the sowing window | Area-level verification, but intimation is farmer-initiated |

### B. "Group" / Area-Approach Claims (automatic, no individual intimation)
<cite index="21-1">Loss assessment due to natural risks is conducted on an area approach basis</cite>, with the **Insurance Unit** typically set at village/village-panchayat level for major crops.

| Type | Trigger | Farmer intimation needed? | Assessment method |
|---|---|---|---|
| **Widespread/yield-shortfall claim** | Drought, flood, cyclone causing area-wide yield loss | No — <cite index="16-1">widespread yield loss claims are processed after crop-cutting results, no individual intimation needed</cite> | Crop Cutting Experiments (CCE) compare actual vs. threshold yield for the whole insurance unit; every insured farmer in that unit is paid automatically |
| **Mid-season adversity / on-account payment** | Severe adverse conditions (extended dry spell, floods) partway through the season, likely to reduce yield >50% | No individual intimation; state government/insurer declares it for the notified area | Rapid assessment triggers an interim (on-account) payout of up to 25% of likely claim, adjusted at final settlement |

### C. Additional India-Specific Claim Variants
- **Weather-index claims (under RWBCIS)** — payout triggered purely by weather-station data (rainfall, temperature, humidity, wind) crossing a pre-defined threshold; no yield measurement or farm visit at all. This is the fastest-settling and least intimation-dependent claim type in India.
- **Perennial/horticulture crop claims (e.g., Coconut Palm Insurance Scheme)** — per-tree/per-plant assessment rather than per-hectare yield.
- **State-specific claim mechanisms** — a few states (e.g., Bihar's State Crop Assistance scheme, Karnataka's Raitha Suraksha) run their own compensation schemes outside PMFBY/RWBCIS, each with its own intimation and disbursal process; <cite index="34-1">Andhra Pradesh, West Bengal and Bihar had decided to exit the scheme citing high costs and the need to customise it based on geographical diversities</cite>.

---

## 3. Organizations That Provide/Process Claims

**Implementing insurers (empanelled by the Dept. of Agriculture & Farmers Welfare):**
<cite index="24-1">Agriculture Insurance Company of India (AIC) and empanelled private insurers: ICICI-Lombard, HDFC-ERGO, IFFCO-Tokio, Cholamandalam MS, Bajaj Allianz, Reliance General, Future Generali, Tata-AIG, SBI General, and Universal Sompo General Insurance</cite>. States select from this empanelled list <cite index="24-1">based on the lowest weighted premium quoted for all notified crops within a cluster of districts</cite>.

**Newer specialist agri-insurer:** Kshema General Insurance — a digital-first, satellite/remote-sensing-led crop insurer built specifically around fast claim intimation and settlement.

**Other stakeholders in the claim chain:**
- State Agriculture/Revenue Department district officials (receive intimation, run CCEs)
- Banks / PACS / Common Service Centres (CSCs) — intimation channels, especially for loanee farmers
- National Crop Insurance Portal (pmfby.gov.in) and the Crop Insurance mobile app — official digital intimation channel
- IRDAI — regulator overseeing insurer conduct and claim conduct rules

---

## 4. Government Schemes Supporting the Process

| Scheme | Role |
|---|---|
| **PMFBY (Pradhan Mantri Fasal Bima Yojana)**, since 2016 | Flagship scheme; <cite index="7-1">administered through the National Crop Insurance Portal and implemented by empanelled insurance companies</cite>; subsidised premium (2% Kharif / 1.5% Rabi / 5% commercial-horticulture), rest paid by Centre+State |
| **RWBCIS (Restructured Weather Based Crop Insurance Scheme)**, since 2016 | <cite index="30-1">Mitigates farmer hardship from anticipated crop loss due to adverse weather — rainfall, temperature, wind, humidity</cite>, run in parallel to PMFBY in states that opt for index-based cover |
| **WINDS (Weather Information Network Data Systems)** | Infrastructure layer — <cite index="20-1">a network of automatic weather stations and rain gauges at revenue-village level, installed to improve weather data accuracy for RWBCIS and PMFBY loss assessment</cite> |
| **YES-TECH** | <cite index="23-1">AI-assisted remote sensing used alongside CCEs and WINDS for yield estimation, reducing human error</cite> in area-approach claims |
| **Coconut Palm Insurance Scheme (CPIS)** | Perennial-crop scheme for coconut cultivators, separate claim/assessment logic |
| **State-specific compensation schemes** | Run outside PMFBY by states that opted out (Bihar, West Bengal historically; Andhra Pradesh also exited citing cost/customisation needs) |

Scale: <cite index="20-1">PMFBY has enrolled over 57 crore farmer-applications and paid out claims worth more than ₹1.5 lakh crore since launch</cite>, making it <cite index="20-1">the world's largest crop insurance scheme by farmer enrollment</cite>.

---

## 5. Current Companies Helping with Claim Intimation — Landscape Scan

| Company | Model | Relevance to intimation |
|---|---|---|
| **Kshema General Insurance** | Full-stack digital agri-insurer (satellite + AI underwriting) | In-app claim intimation, geo-tagged photo upload, <cite index="15-1">24×7 satellite monitoring for accurate loss assessment and quick claim settlement</cite>; claims paid <cite index="10-1">within 48 hrs of intimation</cite> in cited cases |
| **SatSure** | Earth-observation (EO) data & analytics provider to insurers | <cite index="18-1">Helps insurers use EO data for yield forecasts, claim validation, and risk modeling</cite> — B2B infrastructure layer, not farmer-facing |
| **GramCover** | Insurance distribution/advisory for rural India | Distribution and awareness layer; <cite index="12-1">founded to increase penetration of formal financial products and cushion farmers against sudden financial losses</cite>; helps farmers navigate intimation via agent network |
| **Skymet** | Weather risk data & agri-analytics | Weather-index data provider feeding RWBCIS-style automatic claims |
| **CropIn, DhanyaSeva and similar agri-data platforms** | Farm-level data collection (polygon mapping, crop health) | Feed intimation/assessment pipelines used by insurers and government bodies |
| **Empanelled traditional insurers' own apps/portals** (SBI General, HDFC ERGO, ICICI Lombard, IFFCO-Tokio, Universal Sompo, etc.) | In-house claim portals + toll-free numbers | Primary official channel; <cite index="3-1">USGI provides a claim portal that can be used for claim intimation</cite>, and most insurers offer app/toll-free/email routes |

---

## 6. Gap Analysis — Current Claim Intimation Process

1. **72-hour window is unforgiving and poorly enforced-for-awareness.** <cite index="7-1">Missing the 72-hour intimation window can result in claim rejection regardless of actual loss</cite> — yet awareness of the exact rule (what counts as "occurrence," how to prove timing) is low among smallholders.
2. **Channel fragmentation.** A farmer can intimate via <cite index="9-1">PMFBY portal, Crop Insurance App, CSC/bank branch, district Agri/Revenue office, or the insurer's helpline</cite> — five+ parallel channels with no single source of truth for the farmer or unified status tracking.
3. **Confusion between claim types.** Farmers often don't know whether their loss needs individual intimation (localized/post-harvest/prevented-sowing) or is auto-settled via CCE (widespread yield loss) — leading to either missed intimation for claims that needed it, or wasted effort intimating claims that didn't.
4. **Documentation burden at the point of maximum stress.** Geo-tagged photos, policy number, land records, and sowing proof are all needed *immediately after a calamity*, when connectivity, literacy, and access are often worst.
5. **Assessment delay and disputed CCE data.** Even after intimation, on-ground CCE/loss-assessor deployment can lag, and mistrust of yield data (especially where WINDS station coverage is thin) drives grievances.
6. **Language and digital literacy gaps.** Most official portals/helplines are only partially multilingual; only newer entrants (e.g., Kshema, <cite index="15-1">available in 10+ regional languages</cite>) have closed this meaningfully.
7. **Weak feedback loop on claim status.** Farmers frequently cannot tell what stage their claim is at (intimated → assessor assigned → CCE done → approved → paid), causing repeat calls/grievances and eroding trust in the scheme.
8. **State-scheme fragmentation.** States that exited PMFBY run entirely separate intimation/compensation logic, so any pan-India tool needs a state-scheme-aware routing layer, not a single PMFBY-only assumption.
9. **Underused automatic-trigger potential.** RWBCIS/weather-index and YES-TECH/WINDS infrastructure could remove intimation entirely for more claim types than it currently does — this is a policy/technology opportunity, not just a UX one.

---

## 7. Phase 1 Roadmap

**Goal for Phase 1:** Build a reliable, farmer-first claim intimation layer that reduces missed windows and channel confusion — without yet trying to replace the underlying assessment/settlement systems (CCE, WINDS, insurer back-ends).

| Workstream | Key activities | Output |
|---|---|---|
| **1. Scheme & rule mapping** | Codify PMFBY, RWBCIS, and top 3–5 state-scheme rules: claim type definitions, intimation windows, required documents, eligible crops/states | A structured, machine-readable rules engine ("does this loss need intimation, and by when") |
| **2. Farmer-facing intimation flow** | Single guided flow: identify claim type → collect geo-tagged evidence/photos → auto-fill policy/Aadhaar-linked details → submit to correct channel(s) simultaneously (portal + insurer + bank) | Multilingual intimation form/app flow with offline-first capture (photo/GPS cached, synced when connectivity returns) |
| **3. Deadline & reminder system** | Countdown from loss-event date/discovery date per claim type; SMS/WhatsApp/IVR reminders in regional languages | Automated 72-hour compliance nudges, reducing missed-window rejections |
| **4. Status transparency** | Pull/display claim stage (intimated → assessor assigned → CCE/assessment done → approved → paid) from insurer/portal wherever an API or scrape-safe source exists | Farmer-facing status tracker, reducing repeat-call grievance load |
| **5. Pilot & validation** | Select 2–3 districts across 2 states (one PMFBY-heavy, one with a state-specific scheme) covering both individual and area-approach claim types | Pilot data on: time-to-intimate, % within 72-hr window, farmer comprehension of claim type, drop-off points |
| **6. Partnership scoping** | Early conversations with AIC + 1–2 empanelled private insurers, plus a data partner (SatSure/WINDS-linked) for assessment-side visibility | MoUs/pilot agreements; access to claim-status data feeds where available |

**Suggested Phase 1 duration:** 10–12 weeks (rules mapping + flow build in parallel for weeks 1–5, pilot in weeks 6–10, review and gap-closure in weeks 11–12).

**Explicitly out of scope for Phase 1** (flag for Phase 2+): CCE-data integration/dispute resolution tooling, direct insurer claim-payment integration, expansion beyond the pilot states, and building an independent weather-index trigger layer.

---

### Sources
Research drawn from PMFBY operational guidelines (pmfby.gov.in), IRDAI RWBCIS documentation, insurer claim-process pages (SBI General, IFFCO-Tokio, Universal Sompo, HDFC ERGO, Bajaj Finserv, Kshema), and current news/analysis (August 2026).
