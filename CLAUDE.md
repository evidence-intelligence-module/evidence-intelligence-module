# Evidence Intelligence Module — Crop Insurance

## What this repo is, right now

One active initiative: the **Evidence Intelligence Module** — a satellite + weather evidence-generation service that turns heterogeneous satellite and weather observations into reproducible, spatially explicit, auditable technical evidence supporting crop-damage and yield-loss claims under India's PMFBY/RWBCIS crop insurance schemes.

**Start here:** [`documents/README.md`](documents/README.md) — states the problem and the goal in full. This file is a pointer, not a substitute for reading it.

## Hard boundaries — do not silently relax these

1. **No CCE.** This module does not ingest Crop Cutting Experiment data, does not implement CCE-blended yield determination, and never claims to replace CCE.
2. **No standalone prediction.** The module reacts to a reported/claimed loss event; it does not run proactive predictive alerting.
3. **Standalone by design.** The module exposes a generic evidence-request interface and has no dependency on any specific claim-intimation channel's internal schema. A prior voice-assisted claim-intimation initiative existed in this repo and was **deliberately deleted** (see `documents/notes/decision-log.md` §2/§6 for why) — do not treat its absence as an oversight, and do not recreate dependencies on it.

Full reasoning for all three lives in the Constitution — see below. If a task seems to require relaxing one of these, that's a scope decision for the user to make explicitly, not something to infer from a single request.

## Directory map

**Domain documentation** — what's being built and why; hand-authored, changes rarely:

| Path | What it is |
|---|---|
| `documents/README.md` | Orientation for the whole initiative — goal, problem, boundaries, reading order. Start here (see above). |
| `documents/constitution.md` → `hld.md` → `modeling-approach.md` → `evidence-flow-spec.md` | Non-negotiables → architecture → modeling science → pipeline detail, in reading order (after `documents/README.md`). Everything lives directly under `documents/` — this repo has a single active initiative, so there's no per-initiative subdirectory. |
| `documents/technical-flow-diagrams.md` | Mermaid diagrams of the **as-built** service in `src/` — runtime topology, request status machine, evidence-tier decision, GEE/weather ingestion internals, the observation layer's measured/substituted/absent discipline, model and ensemble wiring, causation scoring, packaging, schema, config gates, test seams. Derived from the code, not hand-authored design: it tracks `src/` and will drift if the code changes without it. §15 maps each thin spot to the tracker that owns it. |
| `documents/standards/yestech_manual_2023.md` | External, verbatim government manual (DA&FW/MNCFC). Not our content — never edit it, only relocate/reference it. The modeling approach is designed to match and exceed its rigor. |
| `documents/research/` | Internal source white paper the initiative was derived from. Optional depth, not required reading. |
| `documents/notes/decision-log.md` | Running decision log — why the module is scoped the way it is, including why earlier material (baseline platform docs, the voice-agent initiative, an old root-level `implementation_plan.md`) was deleted, and why the documentation tree itself is laid out this way. Read this before assuming something is "missing." |

**Engineering execution state** — Spec Kit's translation of the domain documentation above into a buildable plan; regenerated/updated via `/speckit-*` skills, not hand-authored prose:

| Path | What it is |
|---|---|
| `specs/001-evidence-generation-pipeline/` | The Spec Kit feature directory implementing `evidence-intelligence-module/hld.md`: `spec.md` (requirements) → `plan.md` (architecture-to-code mapping) → `research.md`/`data-model.md`/`contracts/`/`quickstart.md` (Phase 0/1 design) → `tasks.md` (executable task list). `issue/` holds open questions the spec/plan deliberately deferred rather than guessed at (see its `README.md`). |
| `specs/002-satellite-evidence-parity/` | A second Spec Kit feature against the same running service — a roadmap extending `001`'s pipeline to push satellite-only evidence generation as close as achievable to CCE-level verification confidence (tiered confidence/fallback output, higher-resolution/SAR-priority sourcing, open geospatial foundation-model feature augmentation, independent crop-type cross-check), without relaxing the no-CCE boundary. Grounded in `documents/research/satellite-parity-global-precedent-research.md`. Same internal structure as `001` (`spec.md` → `plan.md` → Phase 0/1 artifacts → `tasks.md`, plus `issue/`), and its `data-model.md`/`contracts/` are explicitly additive extensions of `001`'s, not an independent schema. |
| `.specify/` | Spec Kit's own scaffolding — templates, PowerShell scripts, `memory/constitution.md` (a Spec-Kit-facing distillation of the domain Constitution, kept in sync with it, not an independent authority). Not hand-edited in normal use. |
| `SETUP.md` | Machine/tooling setup for a fresh clone (Spec Kit CLI, PowerShell, the `brainstorming` skill's optional Node dependency). Separate from this file, which is orientation, not setup. |

**Implementation** — executed from `specs/001-evidence-generation-pipeline/tasks.md`, not hand-designed independently of it:

| Path | What it is |
|---|---|
| `src/` | The Evidence Generation Pipeline service (Python/FastAPI): `evidence_intelligence/` (the package — `api/`, `ingestion/`, `models/`, `causation/`, `packaging/`, `store/`, per `plan.md`'s Project Structure) and `tests/` (`contract/`, `integration/`, `unit/`). Has its own `pyproject.toml`/`.venv`/`docker-compose.yml` — see `GUIDE.md` before running anything here. |
| `GUIDE.md` | Operational how-to for `src/`: configuration, running the service, training the AI/ML model, and an index of current open issues. Separate from `SETUP.md`, which covers Spec Kit's own tooling, not this application. |

## Working conventions

- Cross-document references use `File.md §N — Section Title` or a markdown link; when adding new cross-references, prefer linking to the file and naming the section by its actual heading text so references survive renumbering.
- Every evidence-generation claim in the docs should be traceable to either a named public dataset or a specific section of `yestech_manual_2023.md` — don't invent figures or citations.
- `src/` has a real build/test step (`pytest`, `ruff`) — see `GUIDE.md`. Everything under `documents/` and `specs/` remains documentation: "correctness" there means internal consistency (cross-references resolve, no contradicted boundaries) and factual accuracy against the cited sources.
