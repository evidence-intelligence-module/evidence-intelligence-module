# Crop Insurance Documentation

**Start here if you're new:** [`initiatives/evidence-intelligence-module/README.md`](initiatives/evidence-intelligence-module/README.md) — one page, states the problem and the goal. Everything else in this directory supports that document.

This directory holds a single active initiative — the **Evidence Intelligence Module**, a satellite + weather evidence-generation service supporting crop-damage and yield-loss claims under PMFBY/RWBCIS — plus the reference material it's built from. Earlier platform material (a broader baseline platform design and a voice-assisted claim-intimation initiative) was removed as out of scope; it's recoverable from git history if ever needed.

## Directory Guide

| Location | What's in it | Why it's separate |
|---|---|---|
| [`initiatives/evidence-intelligence-module/`](initiatives/evidence-intelligence-module/) | Constitution, HLD, Modeling-Approach, Evidence-Flow-Spec, README | The active work — everything that defines what's being built |
| [`standards/`](standards/) | `YESTECH_Manual_2023.md` (verbatim, unedited) | An **external, authoritative** government manual — not our content, kept separate so it's never confused with something we authored or could drift from the source |
| [`research/`](research/) | The original Evidence Collection & Generation white paper | **Internal** source research the initiative was derived from — read on demand for extra depth, not required to understand the goal |
| [`notes/brainstorm-auth.md`](notes/brainstorm-auth.md) | Running decision log | *Why* the module is scoped the way it is — read only if you need the history behind a decision |

## Recommended Reading Order

1. [Evidence Intelligence Module — README](initiatives/evidence-intelligence-module/README.md) — the goal, the problem, and what this fixes. **If you only read one document, read this one.**
2. [Constitution](initiatives/evidence-intelligence-module/Constitution.md) — non-negotiables and scope boundaries everything else must respect.
3. [HLD](initiatives/evidence-intelligence-module/HLD.md) — system architecture: components, data model, interface contract.
4. [Modeling-Approach](initiatives/evidence-intelligence-module/Modeling-Approach.md) — the modeling science, mapped against [`standards/YESTECH_Manual_2023.md`](standards/YESTECH_Manual_2023.md).
5. [Evidence-Flow-Spec](initiatives/evidence-intelligence-module/Evidence-Flow-Spec.md) — the detailed step-by-step pipeline.
6. [Evidence Collection & Generation White Paper](research/Evidence-Collection-Generation-White-Paper.md) — optional deep-dive: peril-specific evidence packages, legal admissibility detail, cost-benefit analysis.

## The Boundary, in One Place

So it never needs re-deriving: this module does **not** touch CCE, does **not** run standalone predictive alerting, and does **not** depend on any specific claim-intimation channel's internals. Full reasoning in the Constitution's boundary sections.
