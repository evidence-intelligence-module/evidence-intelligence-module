# ACIX — Crop Insurance

## What this repo is, right now

One active initiative: the **Evidence Intelligence Module** — a satellite + weather evidence-generation service that turns heterogeneous satellite and weather observations into reproducible, spatially explicit, auditable technical evidence supporting crop-damage and yield-loss claims under India's PMFBY/RWBCIS crop insurance schemes.

**Start here:** [`crop-insurance/documents/initiatives/evidence-intelligence-module/README.md`](crop-insurance/documents/initiatives/evidence-intelligence-module/README.md) — states the problem and the goal in full. This file is a pointer, not a substitute for reading it.

## Hard boundaries — do not silently relax these

1. **No CCE.** This module does not ingest Crop Cutting Experiment data, does not implement CCE-blended yield determination, and never claims to replace CCE.
2. **No standalone prediction.** The module reacts to a reported/claimed loss event; it does not run proactive predictive alerting.
3. **Standalone by design.** The module exposes a generic evidence-request interface and has no dependency on any specific claim-intimation channel's internal schema. A prior voice-assisted claim-intimation initiative existed in this repo and was **deliberately deleted** (see `crop-insurance/documents/notes/brainstorm-auth.md` §2/§6 for why) — do not treat its absence as an oversight, and do not recreate dependencies on it.

Full reasoning for all three lives in the Constitution — see below. If a task seems to require relaxing one of these, that's a scope decision for the user to make explicitly, not something to infer from a single request.

## Directory map

| Path | What it is |
|---|---|
| `crop-insurance/documents/initiatives/evidence-intelligence-module/` | The active initiative: `README.md` (orientation) → `Constitution.md` (non-negotiables) → `HLD.md` (architecture) → `Modeling-Approach.md` (modeling science) → `Evidence-Flow-Spec.md` (pipeline detail) |
| `crop-insurance/documents/standards/YESTECH_Manual_2023.md` | External, verbatim government manual (DA&FW/MNCFC). Not our content — never edit it, only relocate/reference it. The modeling approach is designed to match and exceed its rigor. |
| `crop-insurance/documents/research/` | Internal source white paper the initiative was derived from. Optional depth, not required reading. |
| `crop-insurance/documents/notes/brainstorm-auth.md` | Running decision log — why the module is scoped the way it is, including why earlier material (baseline platform docs, the voice-agent initiative, an old root-level `implementation_plan.md`) was deleted. Read this before assuming something is "missing." |
| `crop-insurance/code/` | Empty — no implementation exists yet. This repo is currently documentation-only. |

## Working conventions

- Cross-document references use `File.md §N — Section Title` or a markdown link; when adding new cross-references, prefer linking to the file and naming the section by its actual heading text so references survive renumbering.
- Every evidence-generation claim in the docs should be traceable to either a named public dataset or a specific section of `YESTECH_Manual_2023.md` — don't invent figures or citations.
- This is a documentation-only repo today. There's no build, test, or run step to verify against — "correctness" here means internal consistency (cross-references resolve, no contradicted boundaries) and factual accuracy against the cited sources.
