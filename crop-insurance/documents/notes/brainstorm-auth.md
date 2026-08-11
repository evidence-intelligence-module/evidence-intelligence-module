# Brainstorm Log — Evidence Intelligence Module

**Purpose:** Running decision log for scoping and designing the satellite + weather evidence-collection initiative. Captures what was researched, what was decided, and why — so the reasoning behind `initiatives/evidence-intelligence-module/` doesn't have to be reverse-engineered later.

---

## 1. Starting point

Two new white papers landed in `documents/documentation/`:

- **Evidence-Collection-Generation-White-Paper.md** — proposes a satellite+weather "Evidence Intelligence Module" (Google Earth Engine, Sentinel-1/2, CHIRPS, ERA5, SMAP, MODIS) to generate reproducible, auditable evidence for crop-damage/yield claims. Core thesis: most legitimate PMFBY claim failures are an *evidence poverty* problem, not fraud — missed 72h deadlines, no pre-event crop-health baseline, CCE sampling only 4 plots per Insurance Unit, sparse weather stations, no proven causation link between a weather event and the damage.
- **Document-Lapse-Report-White-Paper.md** — an audit of the *existing* voice-agent claim-intimation docs. Found real defects: WhatsApp strips EXIF GPS/timestamp metadata from photos unless sent as a "Document" attachment, which breaks the evidence-validation pipeline as currently specified (CRITICAL, unresolved); retention stated as 5 years where IRDAI mandates 10; a 12-week vs. 14-week timeline conflict across docs; missing TTS engine spec; missing cross-references.

Goal stated by the user: turn heterogeneous satellite, weather, CCE, and field observations into reproducible, spatially explicit, auditable technical evidence supporting crop-damage/yield assessments submitted to insurers/government. **CCE is explicitly out of scope for now** — only satellite + weather evidence to support farmer claim intimation.

Standards reference: `YESTECH_Manual_2023.md` (the actual DA&FW/MNCFC government manual governing technology-based yield estimation under PMFBY).

## 2. Research findings (3 parallel deep-dives)

**`baseline/` (platform-wide docs):** All four files predate the voice-agent initiative but remain broadly authoritative. `baseline/HLD.md` already anticipates a "Weather, satellite, and scheme reference sources" adapter in its integration layer — a ready seam for future work. `baseline/Roadmap-Region_India.md` contains the ancestral satellite/YES-TECH/CCE market background that the new white paper now supersedes with much more technical depth. No conflicts found.

**`initiatives/voice-agent-claim-intimation/current-design/` (the voice-agent spec):** `HLD.md` §9 "Explicit Boundaries" states the architecture **excludes "satellite assessment"** — a direct textual conflict with the new initiative. `Evidence-Collection-Spec.md` defines a WhatsApp-photo EXIF-GPS pipeline that is technically broken per the lapse report. `Business-Justification.md` excludes "calamity prediction," which sits ambiguously close to the white paper's "proactive event detection" feature. Retention stated as 5 years in two places.

**`notes/`, `reference-plan/`, root `README.md`:** `reference-plan/` holds unique implementation detail (MCP server table, tool contracts, phased rollout) not duplicated in `current-design/` — not redundant. Root `README.md` does not reference the `documentation/` folder at all — a real navigation gap, unrelated to any initiative's internal scope.

**Conclusion:** nothing in the repo is *purely* redundant. A blind "delete redundant files" pass would not have been justified by the evidence.

## 3. Scope discussion — how the module relates to the voice-agent initiative

Initial framing (mine) proposed integrating the new module directly with the voice-agent's existing `claim_evidence` table, Kafka topics (`evidence.upload.received`, `evidence.validation.completed`), and MCP tools (`request_evidence`, `create_evidence_link`), and directly editing `current-design/HLD.md` §9 to resolve the boundary contradiction plus the 5yr→10yr retention line elsewhere in that initiative.

User pushback, across several rounds: the voice-agent initiative is **out of scope for this work**. Final, confirmed decision:

> The Evidence Intelligence Module is a **fully standalone initiative**. It has its own data model, its own document set, and no dependency on, reference to, or edit of anything inside `initiatives/voice-agent-claim-intimation/` — not the schema, not the topics, not the tools, not even the `§9` boundary line. It still conceptually supports "claim intimation" as a business goal, but exposes a generic, consumer-agnostic evidence-request/output contract rather than assuming any specific intimation channel's internals.

Practical effect: the module is architected only against `baseline/` platform concepts (the already-anticipated integration seam), the two white papers, and `YESTECH_Manual_2023.md` as a standards reference. It does not inherit voice-agent's 5-year retention bug — since it's a new design, retention is stated correctly (10 years, IRDAI) from the start, no "fix" needed.

Also confirmed separately: `baseline/Roadmap-Region_India.md` stays untouched (no trim); the WhatsApp-EXIF (R1) and retention (R2) lapse-report fixes remain the voice-agent initiative's own follow-up work, not bundled here.

One further correction: the original `notes/Original-Inclusion-Notes.md` / `Original-Exclusion-Notes.md` scope-capture files are **not used as a reference or source of truth** for this module's boundaries. This module's in/out-of-scope lines are derived fresh from the two white papers, the YES-TECH manual, and direct instruction in this conversation — not from those older notes.

## 4. What got built as a result

- `initiatives/evidence-intelligence-module/Constitution.md` — principles and boundaries (evidence generation vs. prediction, evidence vs. CCE/yield-blending, standalone-interface principle, YES-TECH alignment posture, 10-year retention).
- `initiatives/evidence-intelligence-module/HLD.md` — architecture: own data model, own interface contract, own tech stack — no dependency on voice-agent internals.
- `initiatives/evidence-intelligence-module/Evidence-Flow-Spec.md` — in-depth pipeline flow (imagery acquisition → damage detection → weather causation → yield-loss estimate → report packaging), with a generic trigger contract rather than a voice-call-specific one.
- `initiatives/evidence-intelligence-module/README.md` — top-level orientation document: end-to-end flow plus an explicit "what this fixes" section framed against the *systemic* evidence gap described in the white paper, not against any other initiative's internal bugs.
- `documents/README.md` — one small additive edit: added the missing `documentation/` folder and the new initiative to the navigation tree and reading order. No existing content changed.

## 5. What was explicitly not done (round 1)

- No edits inside `initiatives/voice-agent-claim-intimation/` (including its own `§9` contradiction — left as that initiative's own future fix).
- No edits to `baseline/Roadmap-Region_India.md` or `baseline/HLD.md`.
- No file deletions anywhere.
- No bundling of the R1 (WhatsApp EXIF) or R2 (retention) lapse-report fixes.
- `notes/Original-Inclusion-Notes.md` / `Original-Exclusion-Notes.md` left untouched and unreferenced.

---

## 6. Round 2 — tech-stack upgrade + repo scrap

Two follow-up questions from the user, arriving together:

1. **Was the tech stack actually grounded in YES-TECH?** No. Round 1's `HLD.md`/`Evidence-Flow-Spec.md` used a single NDVI-difference threshold table plus one generic regression as the entire damage/yield-loss engine. Re-reading `YESTECH_Manual_2023.md` past line 2000 — Appendix 1, which round 1 never reached — showed the manual mandates five real modeling approaches, each with genuine technical depth and disclosure requirements:
   - **Semi-physical (RUE) model**: biomass = PAR × fAPAR × RUE × water/temperature stress scalars → yield via Harvest Index.
   - **AI/ML models** (RF, DNN): a named feature set (Table 8: vegetation indices, SAR backscatter, IMD weather, fAPAR/LAI, soil texture, SRTM, SMAP) with mandatory hyperparameter disclosure and MAE/RMSE/NRMSE accuracy reporting.
   - **Crop Simulation Models** (DSSAT, APSIM, InfoCrop, ORYZA, WOFOST): process-based, calibrated genetic coefficients, can assimilate remote-sensing state variables.
   - **Ensemble models**: weighted-average/stacking of ML + CSM outputs.
   - **Crop Health Factor (CHF)**: an entropy-weighted, Min-Max-normalized composite index, blended 70/30 with CCE yield deviation.

   Instruction: the module should **at least match this rigor, and be more robust** — not just "reproducible in spirit," which is what round 1 delivered.

2. **Scrap "everything else."** Confirmed explicitly, twice (the second time after I flagged the apparent tension with round 1's "edit `§9` directly" answer, which the user resolved by saying voice-agent scope should be removed entirely, then here going further): delete `baseline/`, all of `initiatives/voice-agent-claim-intimation/`, `documentation/Document-Lapse-Report-White-Paper.md`, and the two original scope-capture notes. Keep only: `YESTECH_Manual_2023.md` (repo root), `evidence-intelligence-module/` itself, `documentation/Evidence-Collection-Generation-White-Paper.md` (the module's own source research), and this log.

   No salvage pass was needed before deleting the lapse report — the one fact worth keeping from it (IRDAI's 10-year retention mandate) was already independently stated in `Constitution.md` §7 in round 1, sourced from the actual regulation, not from that white paper.

### What got built/changed as a result

- **Deleted**: `baseline/` (4 files), `initiatives/voice-agent-claim-intimation/` (8 files across `current-design/` and `reference-plan/`), `documentation/Document-Lapse-Report-White-Paper.md`, `notes/Original-Inclusion-Notes.md` + `Original-Exclusion-Notes.md`.
- **New**: `evidence-intelligence-module/Modeling-Approach.md` — the science/methodology document. Names five components mirroring YES-TECH's structure (semi-physical damage model, AI/ML damage & yield-loss models, optional CSM assimilation, ensemble blending, a CHF-inspired Damage Severity Index) but applied to per-field damage/evidence scoring rather than IU-level CCE-blended yield.
- **The "more robust" argument, concretely**: this module always ensembles multiple components per request rather than a state committing to one model for a whole season; it operates per-field rather than per-IU; it reacts within hours/days of a claimed event via near-real-time sources rather than working to a seasonal report cadence; and full provenance/versioning is a constitutional (not merely procedural) requirement.
- **Updated**: `HLD.md` (component breakdown, data model, tech stack extended for the multi-model pipeline), `Evidence-Flow-Spec.md` (damage-detection and yield-loss steps rewritten around the five components), `Constitution.md` §6 (YES-TECH alignment posture stated concretely rather than "in spirit"), both `README.md` files (module-level reading order, and the root nav rewritten around the now much smaller tree).

### What's still explicitly not done

- Still no CCE ingestion, no CCE-blending formula, no MITR/TIP governance adoption — the Constitution §4 boundary is unchanged; only the *rigor* of the non-CCE modeling components increased.
- Still no standalone predictive alerting (Constitution §3 unchanged).
