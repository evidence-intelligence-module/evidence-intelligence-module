# Evidence Intelligence Module Constitution
<!-- Distilled for Spec Kit from the canonical source of truth: documents/initiatives/evidence-intelligence-module/Constitution.md. That document controls in case of conflict; amend it first, then sync this file. -->

## Core Principles

### I. Reproducible, Versioned Evidence
Every evidence artifact must be re-derivable: the same source imagery and parameters must yield the same result. Source dataset name, version, and acquisition timestamp are recorded with every output. The methodology (thresholds, models, regression coefficients) used to produce a given package is pinned and recorded so it can be explained and re-derived years later, even after the methodology has since changed.

### II. Event-Causal, Independently Verifiable
Every evidence package ties to a specific location, a specific claimed event date, and a specific peril type — generic regional monitoring is not evidence for an individual claim. An insurer, auditor, or court must be able to trace any figure back to a named, dated, publicly identifiable satellite/weather data source. Every evidence-generation claim in project documentation must cite a named public dataset or a specific section of `YESTECH_Manual_2023.md` — never invented figures or citations.

### III. Legally Admissible by Construction (NON-NEGOTIABLE)
Packaging must satisfy Indian Evidence Act, 1872 §65B (electronic record admissibility): source attribution, processing methodology, accuracy statement, and chain of custody are mandatory fields on every output, not optional extras.

### IV. No CCE, No Standalone Prediction (NON-NEGOTIABLE)
This module does not ingest, validate, or dispute Crop Cutting Experiment data, does not implement CCE-blended yield determination, and never claims to replace CCE — it may produce a yield-loss *estimate* as supporting evidence only, clearly labeled as such. It reacts to a reported/claimed loss event; it does not run continuous proactive predictive alerting. These boundaries may only be relaxed by an explicit, recorded amendment to the canonical Constitution — never inferred from a single feature request.

### V. Standalone Interface, No Privileged Caller
The module exposes a generic evidence-request contract (location, event date, peril type, optional external reference ID) and has no dependency on any specific claim-intimation channel's internal schema, message bus, or tooling. A voice-agent system, web portal, CSC-assisted workflow, or insurer's own claims system all integrate the same way; none is assumed or privileged. The module owns its own data model and does not read from or write to another initiative's tables, topics, or tool definitions. (A prior voice-assisted claim-intimation initiative was deliberately deleted from this repo for this reason — see `documents/initiatives/evidence-intelligence-module/notes/brainstorm-auth.md` — its absence is not an oversight.)

## Additional Constraints

**YES-TECH alignment posture:** align with `YESTECH_Manual_2023.md`'s modeling rigor and evidentiary discipline (five-model-family ensemble structure, disclosed hyperparameters and MAE/RMSE/NRMSE reporting, documented SOPs/versioning, entropy-weighted composite scoring, wall-to-wall per-field coverage) without adopting its governance or CCE-blending machinery (no CCE+modelled-yield blending formula, no MITR/TIP empanelment or Tripartite Agreements, no claim that this module's output is Threshold-Yield-grade).

**Data retention:** evidence artifacts (source imagery references, derived rasters, weather correlation results, generated reports) are retained for 10 years from generation, per IRDAI's *Minimum Information Required for Investigation and Inspection Regulations, 2020*. Raw source data may be referenced rather than duplicated where the source (e.g., Google Earth Engine, CHIRPS) guarantees long-term public archival access; derived analysis products and final reports are always retained directly.

**Repo state:** `crop-insurance/code/` is currently empty — no implementation exists yet. Documentation is the current deliverable; treat `documents/initiatives/evidence-intelligence-module/` (README → Constitution → HLD → Modeling-Approach → Evidence-Flow-Spec) as the required reading order before planning implementation work.

## Development Workflow

Cross-document references use `File.md §N — Section Title` or a markdown link, naming sections by actual heading text so references survive renumbering. This is a documentation-only repo today — there's no build/test/run step; correctness means internal consistency (cross-references resolve, no contradicted boundaries) and factual accuracy against cited sources. Read `documents/initiatives/evidence-intelligence-module/notes/brainstorm-auth.md` before assuming something is "missing" — it's the running decision log for why prior material was deliberately removed.

## Governance

This Constitution may be amended only by an explicit, recorded decision — never silently superseded by a later document that merely contradicts it. Any proposal to integrate this module more tightly with a specific intimation channel (relaxing Principle V), add predictive alerting (relaxing Principle IV), or touch CCE data (relaxing Principle IV) must amend the canonical Constitution first, with rationale stated, before implementation. `HLD.md` and `Evidence-Flow-Spec.md` implement this Constitution; where they appear to conflict with it, the canonical document controls. This file is a Spec-Kit-facing distillation kept in sync with it, not an independent authority.

**Version**: 1.0.0 | **Ratified**: 2026-08-12 | **Last Amended**: 2026-08-12
