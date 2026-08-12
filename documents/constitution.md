# Evidence Intelligence Module — Constitution

**Status:** Foundational — governs all design and implementation decisions for this initiative.
**Applies to:** this repo's single active initiative, the Evidence Intelligence Module (see `documents/README.md` / `CLAUDE.md`).

---

## 1. Purpose & Scope Statement

The Evidence Intelligence Module turns heterogeneous satellite and weather observations into reproducible, spatially explicit, auditable technical evidence that supports crop-damage and yield-loss assessments submitted to insurers and government authorities under PMFBY/RWBCIS.

It exists to close the **evidence gap**, not the *fraud* gap: the working assumption, backed by forum analysis, CAG findings, and court rulings, is that most claim failures happen because genuinely damaged farmers cannot produce adequate proof — not because claims are false. This module produces that proof independently of what a farmer's phone or a manual surveyor can capture.

**In scope now:** automated generation of satellite-derived and weather-derived evidence artifacts (pre/post-event crop-health imagery, damage classification, causation analysis, yield-loss estimate, packaged report) triggered by a reported crop-loss event.

**Out of scope now:** everything listed under Section 4 (CCE), Section 3 (prediction), and any specific claim-intimation channel's internal implementation (Section 5).

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
