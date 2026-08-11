# Crop Insurance Documentation

This directory now contains a single active initiative: the **Evidence Intelligence Module**, a satellite + weather evidence-generation service supporting crop-damage and yield-loss claims under PMFBY/RWBCIS. Earlier platform material (a broader baseline platform design and a voice-assisted claim-intimation initiative) has been removed — it was not load-bearing for this initiative and is recoverable from git history if ever needed.

## Directory Guide

| Location | Contents | Use |
|---|---|---|
| [`initiatives/evidence-intelligence-module/`](initiatives/evidence-intelligence-module/) | Constitution, HLD, Modeling-Approach, and Evidence-Flow-Spec | The active initiative — start here |
| [`documentation/Evidence-Collection-Generation-White-Paper.md`](documentation/Evidence-Collection-Generation-White-Paper.md) | Original research/business-case white paper | Source material the initiative is derived from |
| [`notes/brainstorm-auth.md`](notes/brainstorm-auth.md) | Running decision log | Why the module is scoped and designed the way it is |

**External standards reference:** [`YESTECH_Manual_2023.md`](../../YESTECH_Manual_2023.md) (repo root) — the DA&FW/MNCFC government manual this module's modeling approach targets matching and exceeding.

## Recommended Reading Order

1. [Evidence Intelligence Module — README](initiatives/evidence-intelligence-module/README.md) — orientation, the problem, and what this fixes.
2. [Constitution](initiatives/evidence-intelligence-module/Constitution.md) — non-negotiables and scope boundaries.
3. [HLD](initiatives/evidence-intelligence-module/HLD.md) — system architecture.
4. [Modeling-Approach](initiatives/evidence-intelligence-module/Modeling-Approach.md) — the modeling science, mapped against YES-TECH.
5. [Evidence-Flow-Spec](initiatives/evidence-intelligence-module/Evidence-Flow-Spec.md) — the detailed pipeline.
6. [Evidence Collection & Generation White Paper](documentation/Evidence-Collection-Generation-White-Paper.md) — original source research.

The module is standalone: CCE, standalone predictive alerting, and any specific claim-intimation channel's internal implementation are explicitly out of scope (see Constitution §3–§5).
