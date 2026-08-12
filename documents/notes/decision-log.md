# Decision Log — Evidence Intelligence Module

**Purpose:** Record of *why* things that no longer exist in this repo were removed, and why structural decisions (standalone scope, directory layout) were made the way they were. This is not a restatement of current rules — those live in `Constitution.md` — it's the answer to "why is X missing?" or "why isn't this built the obvious way?" See `CLAUDE.md`'s directory map, which points here for exactly that.

**Condensed 2026-08-12:** earlier content that duplicated `Constitution.md`, `README.md`, or `Modeling-Approach.md`, or that later rounds made moot, was cut. Full original history is in git.

---

## 1. Starting point

Two white papers landed in what was then `documents/documentation/` (later renamed `documents/research/` — see Round 4): **evidence-collection-generation-white-paper.md**, proposing a satellite+weather "Evidence Intelligence Module" on the thesis that most legitimate PMFBY claim failures are an *evidence poverty* problem, not fraud; and **Document-Lapse-Report-White-Paper.md**, an audit of the voice-agent claim-intimation docs that found real defects (broken WhatsApp EXIF pipeline, wrong retention period, timeline conflicts) — deleted in Round 2 along with the initiative it audited.

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

## 6. Round 5 — external platform pitch evaluated and trimmed to a technical reference

A document titled with the external platform's own product name (originally `CropSure_ML_Platform_Document.md`, renamed by the user) landed at the repo root — an external, third-party SaaS platform pitch. Evaluated against `Constitution.md` and found to conflict with all three hard boundaries: a configurable CCE-blending ratio (§4), continuous proactive anomaly scanning with auto-notification and an auto-trigger that generates a claim document without a reported event (§3), and its own multi-tenant SaaS product architecture rather than a component behind a generic evidence-request contract (§5).

Confirmed with the user: an external pitch being evaluated, not something to build as specified. Decision: keep the technically sound ideas that don't depend on CCE data or proactive alerting (HLS cross-sensor harmonization, STARFM/ESTARFM fusion, foundation-model crop segmentation, a physics-informed neural network, per-prediction confidence intervals, an isolation-forest anomaly-scoring technique separated from its always-on wrapper, blockchain hash-anchoring), reject everything CCE-, SaaS-, or prediction-shaped (tenancy, dashboards, pricing, roadmap, staffing, financials), and don't leave the rejected material in place. The trimmed, rewritten content became `documents/research/remote-sensing-ml-techniques-reference.md` (reference only, not a design spec, with its own "what was deliberately not kept" section). The original root-level file was deleted; one pointer line added to the module `README.md`'s reading order.

Not done: no edits to `Constitution.md`, `HLD.md`, `Modeling-Approach.md`, or `Evidence-Flow-Spec.md` to actually adopt any kept technique — that's a separate future decision per technique.

## 7. Round 7 — Spec Kit engineering tree connected back to the documentation tree

`specs/001-evidence-generation-pipeline/` (Spec Kit's `spec.md` → `plan.md` → `tasks.md`, implementing `HLD.md`) and `.specify/`/`SETUP.md` were added at the repo root, outside this directory, and initially left unlinked from it — neither `CLAUDE.md` nor `documents/README.md` mentioned them.

User asked to restructure for clarity, scoped explicitly to include this tree. Checked first whether `crop-insurance/documents/` itself was actually confusing: it wasn't — Round 4 already fixed folder naming, Round 5 already fixed duplication, and the reading order/cross-references have held since. Moving files here again would have re-risked what those rounds already got right for no real benefit.

Decision: connect the two trees with cross-links instead of moving anything. `CLAUDE.md`'s directory map now has two explicit groups — "domain documentation" (this tree, hand-authored) vs. "engineering execution state" (`specs/`, `.specify/`, regenerated via `/speckit-*` skills) — rather than one flat list. `documents/README.md` gained a "Turning This Into Code" pointer to `specs/001-.../`; `HLD.md` gained a reciprocal "Implemented by" pointer back; `plan.md` gained an "Implements" pointer to `HLD.md`, mirroring the "Governed by" convention this tree already uses. `specs/001-.../issue/` (open questions deferred during `/speckit-specify`/`/speckit-plan` rather than guessed at, matching this log's own convention of recording *why* something is missing rather than leaving it unexplained) gained a `README.md` index since it had grown to three files with no listing.

No file in `crop-insurance/documents/` was moved or renamed.

## 8. Round 8 — considered decommissioning Constitution.md/HLD.md, decided against

After Round 7 connected the two trees, user asked whether `Constitution.md` and `HLD.md` could be decommissioned from `documents/` now that `specs/001-evidence-generation-pipeline/` exists. Declined, for reasons worth keeping:

1. `specs/001-.../` is scoped to *one feature*. `Constitution.md`/`HLD.md` are scoped to the whole initiative and would still be needed as the thing any future `specs/002-.../` implements — decommissioning them now would leave nothing durable behind once this feature's spec directory stops being the active one.
2. `Constitution.md` §8 already governs this exact situation: amendment requires an explicit, recorded decision with rationale, not silent removal or superseding by a later document. Deleting it wouldn't be an amendment.
3. The actual discomfort prompting the question was resolved instead by fixing the two genuinely stale duplicates found in this same pass — `documents/README.md`'s reading order had drifted from the module README's (missing the Round 6 research-reference addition), and `data-model.md`/`contracts/evidence-request-api.md` didn't say outright that they're derived from `HLD.md`, not independent. Both fixed by trimming to a pointer and adding an explicit "derived from, not authoritative" line respectively — same "single source of truth wins" instinct as Round 4, applied without touching governance documents themselves.

`Constitution.md` and `HLD.md` remain unchanged and canonical.

## 9. Round 9 — standards/, research/, notes/ moved inside this initiative's own directory

Previously siblings of `initiatives/` under `documents/` (a Round 4 decision, at a time when the repo's shape was less settled). User asked for them to move under `initiatives/evidence-intelligence-module/` instead, since there is and has only ever been one active initiative in this repo — keeping them as top-level siblings bought nothing but an extra directory hop, and this module's own decision log, standards reference, and source research are logically part of it, not the wider (currently nonexistent) multi-initiative structure Round 4's layout was implicitly designed for.

Moved with `git mv` (history preserved): `documents/standards/` → `initiatives/evidence-intelligence-module/standards/`, `documents/research/` → `.../research/`, `documents/notes/` → `.../notes/`. All cross-references updated: `Constitution.md` §6, `Modeling-Approach.md` §1, and this module's own `README.md` §6/§7 now link to `./standards/...` and `./research/...` (same-directory, no longer `../../`); `CLAUDE.md`, `SETUP.md`, and `.specify/memory/constitution.md` updated to the new `notes/brainstorm-auth.md` path. `documents/README.md` rewritten — it now only holds this one directory, so its "Directory Guide" collapsed from four sibling rows into one row describing what's inside the initiative directory.

Not moved: `Constitution.md`, `HLD.md`, `Modeling-Approach.md`, `Evidence-Flow-Spec.md`, and this module's own `README.md` — already in the right place, per Round 8.

## 10. Round 10 — `documents/` moved out of `crop-insurance/` to the repo root

User asked for the whole `documents/` tree (as reorganized in Round 9) to move out from under `crop-insurance/` to sit at the repo root, as a sibling of `crop-insurance/` rather than nested inside it. `crop-insurance/` now contains only `code/` (still empty).

Moved with `git mv` (history preserved): `crop-insurance/documents/` → `documents/`. This shifted every file under it up one directory level, so every relative link crossing that boundary needed a `../` removed: `HLD.md`'s pointer to `specs/001-evidence-generation-pipeline/`, `documents/README.md`'s same pointer, and — going the other direction — `plan.md`/`data-model.md`/`contracts/evidence-request-api.md`'s "derived from"/"implements" pointers back to `HLD.md`, plus `CLAUDE.md`, `SETUP.md`, and `.specify/memory/constitution.md`'s references to this directory and to `notes/brainstorm-auth.md`. Links entirely *within* this initiative directory (Constitution → standards/, README → research/, etc., fixed in Round 9) were unaffected, since they and their targets moved together.

Left alone deliberately: `crop-insurance/code/` — the user asked to move `documents/` specifically, not `code/`, so `crop-insurance/` remains as the (currently empty-except-`code/`) implementation namespace. `specs/001-.../tasks.md`'s many `crop-insurance/code/...` file paths are correspondingly still correct and were not touched.

## 11. Round 11 — top-level `documents/README.md` and the module's own `README.md` merged into one

After Round 10, `documents/` contained exactly one subdirectory, so its own `README.md` had shrunk to a thin directory index (start-here pointer, a directory-guide table, a `specs/` pointer) sitting alongside the module's real orientation doc at `initiatives/evidence-intelligence-module/README.md` — two files answering "what is this" with genuinely distinct but increasingly overlapping content. User asked why, then asked to merge them, keeping the result at the top level (`documents/README.md`).

Merged: the module `README.md`'s full content (goal, problem table, end-to-end flow diagram, what-this-fixes table, explicit boundaries, standards alignment, reading order, roadmap pointer) plus the top `README.md`'s unique content (single-initiative framing, directory guide, `specs/` pointer) into one file at `documents/README.md`. The old top `README.md`'s separate "Recommended Reading Order" (itself already just a pointer to the module's §7, per Round 7/9) and "The Boundary, in One Place" section (a shorter restatement of the module README's own §5) were dropped rather than merged — both were pure duplicates once the two files became one. `documents/initiatives/evidence-intelligence-module/README.md` deleted (`git rm`); every link into it — internal section links (now `initiatives/evidence-intelligence-module/Constitution.md` etc. instead of `./Constitution.md`), `CLAUDE.md`'s "Start here" pointer and directory map, `SETUP.md`'s reading order — updated to point at `documents/README.md` instead.

Net effect: one orientation document, not two. `initiatives/evidence-intelligence-module/` now holds only `Constitution.md`, `HLD.md`, `Modeling-Approach.md`, `Evidence-Flow-Spec.md`, `standards/`, `research/`, `notes/` — no README of its own, since `documents/README.md` now serves that role for the whole tree.

## 12. Round 12 — this file renamed from `brainstorm-auth.md` to `decision-log.md`

User pointed out the old name didn't fit: "auth" is a leftover from when this log tracked decisions about the voice-agent claim-intimation initiative (which had an auth-adjacent scope) — that initiative was deleted back in Round 2, but the filename never caught up. Every other document already described this file in prose as the "running decision log," never as a "brainstorm log," so the rename brings the filename in line with what it's actually called everywhere it's referenced.

Renamed with `git mv` (history preserved): `notes/brainstorm-auth.md` → `notes/decision-log.md`. Title changed from "Brainstorm Log" to "Decision Log" to match. Every live reference updated: `CLAUDE.md` (both mentions), `SETUP.md`, `documents/README.md` (Reading Order §8 and Directory Guide), `.specify/memory/constitution.md` (both mentions), and `research/remote-sensing-ml-techniques-reference.md`'s pointer.

Left alone deliberately: this file's own Round 9–11 entries above, which mention `notes/brainstorm-auth.md` by the name it actually had at the time those rounds happened — same treatment Round 1's mention of the pre-Round-4 `documents/documentation/` name got. Historical entries describe what was true when they were written, not what's true now.

## 13. Round 13 — implementation moved from `crop-insurance/code/` to `src/`

Between Round 12 and this round, `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement` ran (not detailed here — this log tracks structural/naming decisions about the documentation tree, not a build log; the implementation itself is `src/`'s own history). `plan.md`'s Project Structure had placed the code under `crop-insurance/code/` — Round 10's own note above ("left alone deliberately... `crop-insurance/` remains as the implementation namespace") — because that was the pre-existing empty directory `CLAUDE.md` already designated for it before any of this work started.

User asked for it to live under `src/` at the repo root instead. Moved with a plain filesystem move (nothing under `crop-insurance/code/` had been committed yet, so no `git mv` history to preserve): `crop-insurance/code/` → `src/`, taking its `.venv`, `pyproject.toml`, `docker-compose.yml`, `evidence_intelligence/` package, and `tests/` with it as one unit. `crop-insurance/` was left with nothing in it once `code/` moved (`documents/` had already left in Round 10), so the empty directory was removed — nothing named `crop-insurance/` remains anywhere in the repo.

Every reference updated: `CLAUDE.md` (moved the `src/` row out of "Domain documentation" into a new "Implementation" group, since generated code isn't hand-authored domain prose, and fixed the now-doubly-stale "no build/test step" claim in Working Conventions), `SETUP.md`, `.specify/memory/constitution.md`, `documents/README.md`, `HLD.md`'s "Implemented by" pointer, and all 49 path references across `specs/001-.../plan.md` and `tasks.md`.

## 14. Round 14 — operational how-to consolidated into a root `GUIDE.md`

Configure/run/train instructions had spread across two files answering overlapping questions: `SETUP.md` (Prerequisites, Verify the environment) and `README.md` (`How to Use It` steps 1-5, `Training the AI/ML Model`), plus a third location, `specs/001-evidence-generation-pipeline/issue/`, holding the open questions someone operating the service would want to know about. User asked for one root guide covering configure, run, train, and an issues index.

Considered physically relocating the `issue/` files into the new guide too. Declined: they're cross-referenced by relative path from `tasks.md`, `spec.md`, `data-model.md`, `research.md`, and `checklists/requirements.md`, and `CLAUDE.md` already documents `issue/` as living under the Spec Kit feature directory, regenerated/updated via `/speckit-*` skills rather than hand-restructured (per this file's own recurring "leave Spec Kit's own territory alone" instinct — see Round 7). Asked the user directly; confirmed index-only. `GUIDE.md`'s "Open Issues" section links to `specs/001-evidence-generation-pipeline/issue/README.md` rather than duplicating its table; the four issue files themselves did not move.

Created `GUIDE.md` at the repo root: Configure (merging `SETUP.md`'s Prerequisites/Verify-environment with `README.md`'s environment-setup and env-var sections), Running the App (`README.md` steps 3-5), Training the AI/ML Model (`README.md`'s section, verbatim), and the Open Issues index described above.

`README.md` trimmed: "How to Use It" and "Training the AI/ML Model" replaced with a pointer to `GUIDE.md`; "Repository Layout" gained a `GUIDE.md` row; "Current Status" repointed its training and open-issues mentions. `SETUP.md` trimmed: Prerequisites and Verify-the-environment sections removed (now in `GUIDE.md`), replaced with pointers; "Notes" repoints its test-run command to `GUIDE.md` instead of restating it. `CLAUDE.md`'s Implementation table gained a `GUIDE.md` row, and its two "see `SETUP.md` before running anything" pointers (directory map, Working Conventions) were repointed to `GUIDE.md`, since that's now where the actual run/build instructions live — `SETUP.md` still covers Spec Kit's own tooling setup, a genuinely different thing.

Every in-repo comment that named `README.md "Training the AI/ML Model"` as the source of truth was updated to name `GUIDE.md` instead, since the section moved: `src/scripts/train_ai_ml_model.py`, `src/evidence_intelligence/config.py`, `src/evidence_intelligence/models/ai_ml.py`, and the `issue/` file on AI/ML training data source. `src/evidence_intelligence/ingestion/gee_client.py`'s runtime error message (pointing operators at setup docs when `GEE_SERVICE_ACCOUNT_CREDENTIALS` is missing) was repointed from `SETUP.md` to `GUIDE.md` for the same reason.

## 15. Round 15 — `documents/initiatives/evidence-intelligence-module/` flattened into `documents/`

The `initiatives/` wrapper existed to let multiple initiatives sit side-by-side under `documents/`, but the only other initiative it was ever built for (`voice-agent-claim-intimation/`) was deleted back in Round 2 — this repo has held a single active initiative ever since. User pointed out the nesting (`documents/initiatives/evidence-intelligence-module/...`) no longer earns its place now that it's redundant with the repo's own scope.

Moved with `git mv` (history preserved) directly onto `documents/`: `Constitution.md`, `HLD.md`, `Modeling-Approach.md`, `Evidence-Flow-Spec.md`, `notes/decision-log.md` (this file), `research/evidence-collection-generation-white-paper.md`, `research/remote-sensing-ml-techniques-reference.md`, `standards/YESTECH_Manual_2023.md` — internal `notes/`, `research/`, `standards/` structure preserved, only the `initiatives/evidence-intelligence-module/` segment removed. The now-empty `documents/initiatives/` directory was deleted.

Every live reference updated: `documents/README.md` (Reading Order, Explicit Boundaries, Standards Alignment, and Directory Guide — including its own explanatory prose, since "everything lives in one initiative directory" became "everything lives directly under `documents/`"), `CLAUDE.md`'s directory map (collapsed the nested `↳` rows), root `README.md`, `SETUP.md`, `.specify/memory/constitution.md` (four mentions), `documents/Constitution.md`'s own "Applies to" line (was a path fragment, now points at `documents/README.md`/`CLAUDE.md` instead), and the `HLD.md` pointer in `specs/001-.../plan.md`, `data-model.md`, and `contracts/evidence-request-api.md`.

Left alone deliberately: every entry above this one, including this file's own Round 9–14 mentions of `initiatives/evidence-intelligence-module/` paths — same historical-accuracy treatment Round 12 gave `brainstorm-auth.md`. `YESTECH_Manual_2023.md`'s own body text (unrelated uses of the word "initiatives") was not touched — it's external, verbatim content.

## 16. Round 16 — every file under `documents/` renamed to lowercase

User asked for the `research/` filenames to be lowercased, then extended it to every file under `documents/`. No deeper rationale was given or needed — it is a naming-consistency pass, bringing the hand-authored domain tree in line with the lowercase-kebab convention `specs/` and `src/` already follow. `notes/decision-log.md` and the `research/` directory contents were already lowercase or became so in the first half of this round.

Renamed with `git mv` (history preserved, recorded as `R100` renames rather than delete-plus-add — worth noting on Windows, where a case-only rename is invisible to a plain `mv` because the filesystem is case-insensitive while git is not):

`Constitution.md` → `constitution.md`, `HLD.md` → `hld.md`, `Modeling-Approach.md` → `modeling-approach.md`, `Evidence-Flow-Spec.md` → `evidence-flow-spec.md`, `standards/YESTECH_Manual_2023.md` → `standards/yestech_manual_2023.md`, `research/Evidence-Collection-Generation-White-Paper.md` → `research/evidence-collection-generation-white-paper.md`, `research/Remote-Sensing-ML-Techniques-Reference.md` → `research/remote-sensing-ml-techniques-reference.md`, `research/Satellite-Parity-Global-Precedent-Research.md` → `research/satellite-parity-global-precedent-research.md`.

**`README.md` keeps its uppercase name** — the one deliberate exception. It was renamed to `readme.md` in the first pass of this round, flagged as a reversible judgement call, and reverted at the user's request the same day. Nothing functionally depended on either spelling (GitHub and editors resolve it case-insensitively); the exception exists because a lowercase readme breaks a near-universal convention and reads as an error rather than as a choice. Recorded here rather than left as an unexplained inconsistency, so nobody "fixes" it later.

Every live reference updated across `CLAUDE.md`, `README.md`, `GUIDE.md`, `SETUP.md`, `.specify/memory/constitution.md`, both `specs/` trees (including all `issue/` files), and `src/`'s Python docstrings — which cite `modeling-approach.md §N` and `evidence-flow-spec.md §N` throughout, so this touched code comments as well as prose. Verified afterwards: no capitalized references remain, and every `documents/...` path and relative sibling link resolves to an existing file.

One rename remains a reversible judgement call rather than an obvious win. **`YESTECH_Manual_2023.md` → `yestech_manual_2023.md`** renames an external, verbatim government document (DA&FW/MNCFC) whose filename doubles as its citation identity, and lowercasing flattens the `YESTECH` acronym. `CLAUDE.md` permits relocating it ("never edit it, only relocate/reference it"), so this is within bounds. Its body text was not touched. If the citation identity later proves to matter more than the naming consistency, this is the one to revert — the same way `README.md` was.

Left alone deliberately: every entry above this one, including their mentions of `Constitution.md`, `HLD.md`, `Modeling-Approach.md`, and the old `research/` filenames — same historical-accuracy treatment Rounds 12 and 15 applied. Those are prose descriptions of past repo states, not live navigation links, and rewriting them would make this log claim something untrue about what the files were called at the time. A bulk find-and-replace across the repo did initially rewrite them; that was reverted once the convention was noticed, which is the reason this entry exists rather than a silently-edited history.
