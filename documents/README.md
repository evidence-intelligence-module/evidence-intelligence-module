# Crop Insurance Documentation

**Start here if you're new:** [`initiatives/evidence-intelligence-module/README.md`](initiatives/evidence-intelligence-module/README.md) — one page, states the problem and the goal.

This directory holds a single active initiative — the **Evidence Intelligence Module**, a satellite + weather evidence-generation service supporting crop-damage and yield-loss claims under PMFBY/RWBCIS. Everything belonging to it (design docs, the external standard it's measured against, the research it's derived from, and the decision log explaining why it's scoped the way it is) lives together under `initiatives/evidence-intelligence-module/`, rather than scattered across sibling top-level folders — there's only one active initiative, so nothing is gained by keeping its supporting material separate from it. Earlier platform material (a broader baseline platform design and a voice-assisted claim-intimation initiative) was removed as out of scope; it's recoverable from git history if ever needed.

## What's Inside `initiatives/evidence-intelligence-module/`

| Location | What's in it |
|---|---|
| `README.md` → `Constitution.md` → `HLD.md` → `Modeling-Approach.md` → `Evidence-Flow-Spec.md` | The design docs themselves, in reading order — see the module README's own §7 for the full order including the items below |
| [`standards/`](initiatives/evidence-intelligence-module/standards/) | `YESTECH_Manual_2023.md` (verbatim, unedited) — an **external, authoritative** government manual, kept visibly separate from anything this team authored |
| [`research/`](initiatives/evidence-intelligence-module/research/) | The original Evidence Collection & Generation white paper, plus a trimmed remote-sensing/ML technique reference — **internal** source research the initiative was derived from |
| [`notes/brainstorm-auth.md`](initiatives/evidence-intelligence-module/notes/brainstorm-auth.md) | Running decision log — *why* the module is scoped the way it is, and why this directory itself is laid out the way it is |

## Recommended Reading Order

**If you only read one document, read this one:** [Evidence Intelligence Module — README](initiatives/evidence-intelligence-module/README.md) — the goal, the problem, and what this fixes. Its own §7 "Reading Order / Document Map" is the full, maintained order for everything else — not repeated here to avoid two copies going out of sync, as happened once already (see `notes/brainstorm-auth.md` Round 7).

## The Boundary, in One Place

So it never needs re-deriving: this module does **not** touch CCE, does **not** run standalone predictive alerting, and does **not** depend on any specific claim-intimation channel's internals. Full reasoning in the Constitution's boundary sections.

## Turning This Into Code

This directory is the *what and why* — hand-authored, changes rarely. The *how it gets built* lives separately, in [`specs/001-evidence-generation-pipeline/`](../../specs/001-evidence-generation-pipeline/) at the repo root: a Spec Kit feature directory (`spec.md` → `plan.md` → `tasks.md`) that translates `HLD.md` into a concrete, executable implementation plan for `crop-insurance/code/`. Kept as a separate tree deliberately — it's generated/updated via `/speckit-*` skills rather than written by hand, and changes at a different cadence than the documents above.
