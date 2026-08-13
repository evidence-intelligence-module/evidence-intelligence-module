# Evidence Intelligence Module — Constitution

**Status:** Foundational — governs all design and implementation decisions for this initiative.
**Applies to:** this repo's single active initiative, the Evidence Intelligence Module (see `documents/README.md` / `CLAUDE.md`).

---

## 1. Purpose & Scope Statement

The Evidence Intelligence Module turns heterogeneous satellite and weather observations into reproducible, spatially explicit, auditable technical evidence that supports crop-damage and yield-loss assessments submitted to insurers and government authorities under PMFBY/RWBCIS.

It exists to close the **evidence gap**, not the *fraud* gap: the working assumption, backed by forum analysis, CAG findings, and court rulings, is that most claim failures happen because genuinely damaged farmers cannot produce adequate proof — not because claims are false. This module produces that proof independently of what a farmer's phone or a manual surveyor can capture.

**In scope now:** automated generation of satellite-derived and weather-derived evidence artifacts (pre/post-event crop-health imagery, damage classification, causation analysis, yield-loss estimate, packaged report) triggered by a reported crop-loss event.

**Out of scope:** the full boundary set is enumerated in [Section 9](#9-scope-boundaries) — including the three this document states in their own right (Section 3, prediction; Section 4, CCE; Section 5, any specific claim-intimation channel's internal implementation).

## 2. Non-Negotiables

Every evidence artifact this module produces must be:

1. **Reproducible** — re-running the same analysis against the same source imagery and parameters must yield the same result. Source dataset name, version, and acquisition timestamp are recorded with every output.
2. **Versioned** — the methodology (thresholds, models, regression coefficients) used to produce a given evidence package is pinned and recorded, so a package generated today can be explained and re-derived a year from now even if the methodology has since changed.
3. **Causally linked to a specific event** — every evidence package ties to a specific location, a specific claimed event date, and a specific peril type. Generic regional monitoring is not evidence for an individual claim.
4. **Legally admissible** — packaged to satisfy Indian Evidence Act, 1872 §65B (electronic record admissibility): source attribution, processing methodology, accuracy statement, and chain of custody are mandatory fields on every output, not optional extras.
5. **Independently verifiable** — an insurer, auditor, or court must be able to trace any figure in a report back to a named, dated, publicly identifiable satellite/weather data source.

## 3. Boundary — Evidence Generation vs. Prediction

This module reacts to a reported (or independently detected) loss **event**; it does not run a standalone predictive/early-warning program.

- **In scope:** given an event (location, date, peril type), generate evidence for *that* event — including checking recent satellite/weather data around the event date to corroborate or contradict what was reported.
- **Out of scope, for now:** continuous proactive scanning that pushes alerts to farmers or insurers before any loss is reported ("we detected a hailstorm signature in your district, did you suffer damage?"). This is a legitimate future capability the white paper describes, but it is a distinct product decision (consent, false-positive handling, notification channel ownership) that has not been made. Building it now would smuggle a second initiative's scope into this one.

## 4. Boundary — Evidence vs. CCE / Yield-Blending

Crop Cutting Experiments and the CCE-based yield-determination process are **explicitly excluded**. This module:

- Does **not** ingest, validate, or dispute CCE plot data.
- Does **not** implement the YES-TECH blended-yield formula (CCE weight + modelled weight) or claim to replace CCE.
- **Does** produce a yield-loss *estimate* as one evidence component (via NDVI-yield regression) — but this is presented as supporting evidence, not an authoritative determination, and is clearly labeled as such in every output.

If a future initiative decides to feed this module's outputs into a CCE-blending workflow, that is a deliberate, separately-scoped decision — not something this module assumes or half-implements.

## 5. Boundary — Standalone Interface Principle

This module does not assume, depend on, or reference any specific claim-intimation channel's internal data model, message bus, or tooling.

- It exposes a **generic evidence-request contract**: given a location (geometry), an event date, a peril type, and an optional external reference ID, it returns an evidence package (or a status while one is being generated).
- Any consumer — a voice-agent system, a web portal, a CSC-assisted workflow, an insurer's own claims system — integrates the same way, through that contract. None of them is a privileged or assumed caller.
- This module owns its own data model (Section 4 of `hld.md`). It does not read from or write to another initiative's tables, topics, or tool definitions.

## 6. YES-TECH Alignment Posture

[`yestech_manual_2023.md`](./standards/yestech_manual_2023.md) is the government's own standard for technology-based yield estimation under PMFBY. This module aligns with its **modeling rigor and evidentiary discipline** without adopting its **governance or CCE-blending machinery** — and, per direct instruction, is designed to at least match that rigor and exceed it where practical.

**Adopted as a concrete design pattern, not just in spirit** (full detail in [modeling-approach.md](./modeling-approach.md)):
- The same five-model-family structure YES-TECH mandates — a semi-physical (RUE-based) model, AI/ML models with disclosed hyperparameters and MAE/RMSE/NRMSE accuracy reporting, crop simulation model assimilation, ensemble blending, and an entropy-weighted composite index — re-purposed for per-field damage/evidence scoring rather than IU-level yield determination.
- Reproducibility and methodology documentation as a hard requirement for every model/output (YES-TECH mandates SOPs, model versioning, and documented accuracy per Section 4–6 and Appendix 1 of the manual).
- Transparent, auditable conversion of a satellite-observed anomaly into a severity/loss estimate — the Damage Severity Index (modeling-approach.md §6) plays the same structural role as YES-TECH's Crop Health Factor (entropy-weighted, Min-Max normalized), without the CCE-blending step.
- Preference for wall-to-wall, per-field coverage over sparse sampling or IU-group aggregation, consistent with YES-TECH's own critique of CCE's statistical inadequacy — and going further than YES-TECH's own IU-level granularity.
- Ensembling as the **default** behavior for every request, rather than a single model family selected once per season — see modeling-approach.md §8 for the full robustness comparison.

**Not adopted:**
- The CCE + modelled-yield blending formula and its mandated weightages.
- MITR/TIP empanelment, Tripartite Agreements, or YES-TECH's dispute-resolution governance — those apply to the formal YES-TECH program and its yield-determination authority, not to this evidence-support module.
- Any claim that this module's yield-loss estimate or Damage Severity Index is a Threshold-Yield-grade figure suitable for indemnity calculation.

## 7. Data & Retention Principles

- Evidence artifacts (source imagery references, derived rasters, weather correlation results, generated reports) are retained for **10 years** from the date of generation, consistent with IRDAI's *Minimum Information Required for Investigation and Inspection Regulations, 2020*.
- This is stated as a first-class design principle from the outset — not a retrofit — because this module is new and inherits no prior 5-year assumption from any other initiative's documentation.
- Raw satellite/weather source data is referenced by dataset name, version, and acquisition date rather than duplicated wholesale where the source (e.g., Google Earth Engine, CHIRPS) already guarantees long-term public archival access; derived analysis products and final reports are always retained directly.

## 8. Governance & Amendment

- This Constitution may be amended only by an explicit, recorded decision — not silently superseded by a later document that merely contradicts it.
- Any proposal to integrate this module more tightly with a specific intimation channel (relaxing Section 5), to add predictive alerting (relaxing Section 3), or to touch CCE data (relaxing Section 4) must amend this document first, with the rationale stated, before implementation.
- `hld.md` and `evidence-flow-spec.md` in this same folder implement this Constitution; where they appear to conflict with it, this document controls.

## 9. Scope Boundaries

**The module owns the transformation, not the supply chain at either end.** Labeled data arrives; an evidence package leaves. Who produces the one and who consumes the other are outside this module.

Every boundary below is **permanent**. Crossing one requires a Section 8 amendment — an explicit, recorded decision with rationale, made before implementation, not inferred from silence. There is deliberately no "for now" tier: Section 8 asks only for a written decision and a reason, which is what anyone should produce before adding fraud scoring or a second country in any case.

Rationale, alternatives considered, and the prune this section triggered are recorded in [`notes/2026-08-13-scope-boundaries-design.md`](notes/2026-08-13-scope-boundaries-design.md). That file explains this section; it does not govern.

### 9.1 Data minimisation

The module accepts exactly `geometry`, `event_date`, `peril_type`, and an opaque `external_reference_id`, and **never widens that surface**.

This is stated as minimisation rather than as an absence of personal data, deliberately. A field boundary plus an event date plus a peril type identifies a specific farm, so this module processes personal data today, inherently, as a condition of doing its job. Personal-data *processing* is acknowledged; personal-data *accumulation* is barred.

Reconciling Section 7's ten-year retention floor with the DPDP Act, 2023's purpose-limitation and erasure obligations remains unaddressed by this document and is not resolved by this section.

### 9.2 Upstream — how inputs are produced

| Out of scope | What it means |
|---|---|
| Training-label sourcing, curation, annotation | A supplier delivers labeled data in the documented feature contract. Its origin is recorded as *declared*, never verified. No annotation tooling, no labeling pipeline |
| Ground-truth survey operations | Field visits, agronomist networks, plot sampling |
| Commercial satellite procurement | Vendor contracts, tasking budgets, licence negotiation |
| Hosting or mirroring source archives | Section 7 references sources rather than copying them; this module is not a tile server or an imagery archive |
| Owning master reference data | Crop calendars, crop-type maps, agro-climatic zone definitions — consumed as published products, never authored. Consuming such a product remains fully in scope |
| Field boundary derivation and land records | Geometry arrives with the request; cadastral and land-title systems are separate |
| Sensor operations | Ingesting an image someone else captured is in scope; flying drones or deploying ground sensors is not |

### 9.3 Downstream — what happens to the package

| Out of scope | What it means |
|---|---|
| The consuming service | See Section 5 |
| Claim adjudication and settlement | This module evidences; it never decides |
| Indemnity and payout computation | Sum insured, threshold yield, premium, deductible |
| Delivery and notification | The package is retrieved from a URI. An optional callback announces that a package exists; that is a readiness notification, not delivery |
| Farmer- or surveyor-facing UI | No app, no review screen, no override workflow |
| Dashboards, BI, portfolio analytics | |
| Dispute filing, certification, representation | This module produces §65B-admissible *content*. A §65B certificate is signed by a legal person; software does not issue one |
| Human override of an issued figure | Packages are append-only. Disagreement is recorded downstream, never as an edit to an issued package |

### 9.4 Lateral — adjacent uses of the same data

| Out of scope | What it means |
|---|---|
| Predictive / early-warning alerting | See Section 3 |
| CCE ingestion, validation, blending | See Section 4 |
| Fraud detection, claimant risk scoring | Section 1 is explicit that this module closes the evidence gap, not the fraud gap. It may report that data *contradicts* a claim — Section 3 provides for corroborating or contradicting what was reported — but it must never score a claimant |
| Underwriting, risk rating, premium pricing | The same archive used in the opposite direction; it would make this an actuarial tool |
| Parametric / index-insurance trigger computation | Computing a payout trigger is acting as a determination authority, which Section 4 exists to prevent |
| Agronomic advisory | Irrigation, pesticide, or harvest-timing recommendations |
| Yield forecasting for markets or procurement | |
| Continuous monitoring without a claimed event | Section 3 in new clothing, and it breaks Section 2.3's requirement that every package tie to a specific event. This governs *issuing evidence*: running the pipeline over unclaimed fields as an internal specificity check produces no package and is in scope |
| Other insurance lines and other geographies | PMFBY/RWBCIS, India. Not livestock, property, or health lines; not other countries |

### 9.5 Platform — what this module is not, as software

| Out of scope | What it means |
|---|---|
| ML platform services | Feature store, experiment tracker, model registry, serving mesh. This module ships a training entry point, a saved model artifact, and a feature contract |
| SaaS product surface | Tenancy, billing, metering, subscriptions |
| Deployment and infrastructure | Infrastructure-as-code, orchestration, CI/CD, secrets management, autoscaling |
| Authentication and identity | A gateway concern. The service assumes an authenticated caller and issues no identities |
