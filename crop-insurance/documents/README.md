# Crop Insurance Documentation

This directory separates the original platform material from the active voice-assisted claim-intimation design. No source document was deleted during the restructure.

## Directory Guide

| Location | Contents | Use |
|---|---|---|
| [`baseline/`](baseline/) | Original platform HLD, LLD, business white paper, and India roadmap | Background and broader platform reference |
| [`initiatives/voice-agent-claim-intimation/current-design/`](initiatives/voice-agent-claim-intimation/current-design/) | Business justification, HLD, LLD, and supporting specifications | Primary implementation package for the voice-assisted prototype |
| [`initiatives/voice-agent-claim-intimation/reference-plan/`](initiatives/voice-agent-claim-intimation/reference-plan/) | Earlier voice-agent planning package | Reference material and design history |
| [`initiatives/evidence-intelligence-module/`](initiatives/evidence-intelligence-module/) | Constitution, HLD, and evidence-flow spec for satellite/weather claim evidence | Standalone initiative — generates auditable evidence to support claim intimation; no dependency on the voice-agent initiative |
| [`documentation/`](documentation/) | Evidence Collection & Generation white paper; Document Lapse Report audit | Research and audit source material |
| [`notes/`](notes/) | Preserved original inclusion and exclusion notes | Original requirements capture |

## Recommended Reading Order

1. [Business Justification](initiatives/voice-agent-claim-intimation/current-design/Business-Justification.md)
2. [Current HLD](initiatives/voice-agent-claim-intimation/current-design/HLD.md)
3. [Current LLD](initiatives/voice-agent-claim-intimation/current-design/LLD.md)
4. [Peril Validation Logic](initiatives/voice-agent-claim-intimation/current-design/Peril-Validation-Logic.md)
5. [Evidence Collection Specification](initiatives/voice-agent-claim-intimation/current-design/Evidence-Collection-Spec.md)
6. [Integration Tier Strategy](initiatives/voice-agent-claim-intimation/current-design/Integration-Tier-Strategy.md)
7. [Reference voice-agent plan](initiatives/voice-agent-claim-intimation/reference-plan/Voice-Agent-Claim-Intimation-Plan.md)
8. Relevant [baseline](baseline/) material.
9. [Evidence Intelligence Module](initiatives/evidence-intelligence-module/README.md) — standalone satellite/weather evidence-generation initiative; start with its own README, then Constitution, HLD, and Evidence-Flow-Spec.

The current design is limited to farmer-initiated claim intimation. It excludes CCE, prediction, on-ground verification, claim adjudication, and payment.
