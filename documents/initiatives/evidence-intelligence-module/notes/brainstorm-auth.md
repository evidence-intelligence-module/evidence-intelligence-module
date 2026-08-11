# Brainstorm Log — Evidence Intelligence Module

**Purpose:** Record of *why* things that no longer exist in this repo were removed, and why structural decisions (standalone scope, directory layout) were made the way they were. This is not a restatement of current rules — those live in `Constitution.md` — it's the answer to "why is X missing?" or "why isn't this built the obvious way?" See `CLAUDE.md`'s directory map, which points here for exactly that.

**Condensed 2026-08-12:** earlier content that duplicated `Constitution.md`, `README.md`, or `Modeling-Approach.md`, or that later rounds made moot, was cut. Full original history is in git.

---

## 1. Starting point

Two white papers landed in what was then `documents/documentation/` (later renamed `documents/research/` — see Round 4): **Evidence-Collection-Generation-White-Paper.md**, proposing a satellite+weather "Evidence Intelligence Module" on the thesis that most legitimate PMFBY claim failures are an *evidence poverty* problem, not fraud; and **Document-Lapse-Report-White-Paper.md**, an audit of the voice-agent claim-intimation docs that found real defects (broken WhatsApp EXIF pipeline, wrong retention period, timeline conflicts) — deleted in Round 2 along with the initiative it audited.

Goal as stated by the user: satellite + weather evidence only, CCE explicitly out of scope from the start. Standards reference: `YESTECH_Manual_2023.md`.

## 2. Scope decision — standalone, not integrated with voice-agent

Initial framing (mine) proposed integrating the new module directly into the voice-agent initiative's existing schema, topics, and tools, and editing its `HLD.md` §9 in place to resolve a boundary contradiction it had with the new module. User pushback, across several rounds, landed on:

> The Evidence Intelligence Module is a **fully standalone initiative**. It has its own data model, its own document set, and no dependency on, reference to, or edit of anything inside `initiatives/voice-agent-claim-intimation/`. It still conceptually supports "claim intimation" as a business goal, but exposes a generic, consumer-agnostic evidence-request/output contract rather than assuming any specific intimation channel's internals.

Practical effect worth keeping: because this was a fresh design rather than a fix to voice-agent's docs, retention was stated correctly (10 years, IRDAI) from day one — there was no 5-year bug to inherit.

Three deep-dives (`baseline/`, the voice-agent spec, `notes/`/`reference-plan/`) preceded this decision and found real but non-blocking issues, concluding nothing was *purely* redundant — so a blind delete pass wasn't justified at the time. That conclusion was itself overtaken by events: Round 2 deleted `baseline/` and the voice-agent initiative outright anyway, once they were judged out of scope rather than redundant.

## 3. Round 2 — modeling rigor grounded in YES-TECH, repo scrapped to match new scope

Two things converged:

1. **Rigor check.** Round 1's `HLD.md`/`Evidence-Flow-Spec.md` used a single NDVI-difference threshold plus one generic regression as the entire damage/yield engine — not grounded in `YESTECH_Manual_2023.md`, which (Appendix 1, past line 2000, missed in Round 1) mandates five real modeling approaches: semi-physical (RUE), AI/ML, Crop Simulation Models, Ensemble, and Crop Health Factor (CHF — entropy-weighted, blended 70/30 with CCE). Instruction: match that rigor and exceed it. Full component definitions now live in `Modeling-Approach.md`, not restated here.
2. **Scrap everything else.** Confirmed explicitly, twice: delete `baseline/` (4 files), all of `initiatives/voice-agent-claim-intimation/` (8 files), `documentation/Document-Lapse-Report-White-Paper.md`, and `notes/Original-Inclusion-Notes.md` / `Original-Exclusion-Notes.md` (scope-capture files that were never treated as a source of truth for this module's boundaries anyway). Kept: `YESTECH_Manual_2023.md`, the module's own doc set, the source white paper, and this log. No salvage pass was needed on the lapse report — its one durable fact (IRDAI's 10-year retention mandate) was already independently sourced in `Constitution.md` §7.

Result: `Modeling-Approach.md` created (five components re-purposed for per-field evidence scoring, not IU-level CCE-blended yield); `HLD.md`, `Evidence-Flow-Spec.md`, and `Constitution.md` §6 updated to match. The Constitution §3/§4 boundaries (no CCE ingestion, no standalone predictive alerting) were unchanged throughout — only the rigor of the non-CCE components increased.

## 4. Round 3 — stale root-level plan file deleted

`implementation_plan.md` (repo root) was the original replan for the voice-agent system — proposing edits to files and initiatives that Round 2 had already deleted. Its entire premise (peril-type gating, WhatsApp photo evidence, NCIP integration tiers) was voice-agent scope that had been deliberately removed. Deleted; recoverable from git history.

## 5. Round 4 — restructured for consumption (Claude + human readers)

Four concrete problems found and fixed:

1. **No `CLAUDE.md`** — nothing loaded automatically into a fresh session's context. Added, stating the goal, the three hard boundaries, and a directory map.
2. **Ambiguous folder naming** — `documents/documentation/` renamed to `documents/research/`; `documents/standards/` created for the relocated, unedited `YESTECH_Manual_2023.md` (external, authoritative, kept visibly separate from anything this team authored).
3. **Real duplication** — Constitution §6 and the module `README.md` §6 both restated the full YES-TECH adopted/not-adopted list. Trimmed `README.md` §6 to a pointer; Constitution stays the single source.
4. **Fragmented mission statement** — added a one-sentence "Goal, in one sentence" line at the top of the module `README.md`.

All cross-references were re-verified after the moves (grepped for dangling old paths, found none). Left alone deliberately: the white paper's own content, and the numeric `§N` cross-references within the module docs.

## 6. Round 5 — external ACIS pitch evaluated and trimmed to a technical reference

A document named `ACIS_ML_Platform_Document.md` (originally `CropSure_ML_Platform_Document.md`, renamed by the user) landed at the repo root — an external, third-party SaaS platform pitch. Evaluated against `Constitution.md` and found to conflict with all three hard boundaries: a configurable CCE-blending ratio (§4), continuous proactive anomaly scanning with auto-notification and an auto-trigger that generates a claim document without a reported event (§3), and its own multi-tenant SaaS product architecture rather than a component behind a generic evidence-request contract (§5).

Confirmed with the user: an external pitch being evaluated, not something to build as specified. Decision: keep the technically sound ideas that don't depend on CCE data or proactive alerting (HLS cross-sensor harmonization, STARFM/ESTARFM fusion, foundation-model crop segmentation, a physics-informed neural network, per-prediction confidence intervals, an isolation-forest anomaly-scoring technique separated from its always-on wrapper, blockchain hash-anchoring), reject everything CCE-, SaaS-, or prediction-shaped (tenancy, dashboards, pricing, roadmap, staffing, financials), and don't leave the rejected material in place. The trimmed, rewritten content became `documents/research/Remote-Sensing-ML-Techniques-Reference.md` (reference only, not a design spec, with its own "what was deliberately not kept" section). The original root-level file was deleted; one pointer line added to the module `README.md`'s reading order.

Not done: no edits to `Constitution.md`, `HLD.md`, `Modeling-Approach.md`, or `Evidence-Flow-Spec.md` to actually adopt any kept technique — that's a separate future decision per technique.
