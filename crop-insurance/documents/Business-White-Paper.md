# Crop Insurance Claim Intimation Platform for India

## Business White Paper

Prepared: August 2026  
Source baseline: `Crop-Insurance-Claim-Intimation-Roadmap-India.md` and public PMFBY/RWBCIS scheme material

---

## Executive Summary

India has one of the world's largest public crop insurance ecosystems, anchored by Pradhan Mantri Fasal Bima Yojana (PMFBY) and Restructured Weather Based Crop Insurance Scheme (RWBCIS). The insurance architecture is mature in coverage design, but the claim intimation journey remains fragmented, time-sensitive, and difficult for farmers to navigate.

The most acute business problem is not only claim settlement delay. It is the failure of valid losses to enter the claim pipeline correctly, especially for farmer-initiated claim categories where intimation must generally be made within 72 hours. Farmers must understand whether their loss is an individual claim or an automatic area-based claim, collect evidence, identify the right channel, and track the claim across government, insurer, bank, and field-assessment actors.

This white paper proposes a farmer-first claim intimation platform that acts as a unified orchestration layer across schemes, insurers, banks, CSCs, district officials, and existing PMFBY digital channels. The platform does not replace PMFBY, insurer systems, CCE workflows, WINDS, or YES-TECH. Instead, Phase 1 focuses on correct routing, deadline compliance, evidence capture, multilingual assistance, and claim status transparency.

## Strategic Context

Crop insurance in India operates through multiple claim mechanics:

| Claim category | Farmer action | Assessment model | Platform implication |
|---|---:|---|---|
| Localized calamity | Required | Individual farm assessment | Guided intimation, evidence capture, deadline control |
| Post-harvest loss | Required | Individual farm assessment | Harvest-window validation and geo-tagged media |
| Prevented or failed sowing | Often farmer-initiated, scheme/state dependent | Area-level validation | Scheme-aware triage and state-specific routing |
| Widespread yield shortfall | Not required | Area approach using CCE/technology yield estimates | Farmer education and passive status visibility |
| Mid-season adversity | Not individually required | Notified area trigger | Notification and status explainability |
| Weather-index claims under RWBCIS | Not individually required | Weather trigger | Automated event explanation and payout status |

The key product insight is that farmers need a "claim eligibility and routing assistant" before they need a form. A single generic claim form will not solve the problem because different claim types have different eligibility rules, evidence needs, timelines, and responsible institutions.

## Problem Statement

The current intimation journey creates avoidable claim failure through:

1. Strict intimation timelines that are poorly understood at village level.
2. Multiple reporting channels with inconsistent acknowledgements.
3. Confusion between individual claims and automatic area-based claims.
4. High documentation burden immediately after a weather shock.
5. Limited multilingual and low-literacy support.
6. Weak claim status visibility after submission.
7. State-level variation in scheme participation and operational rules.
8. Limited practical use of weather and remote-sensing data at the farmer-facing layer.

The result is lower trust, higher grievance volume, missed claim windows, duplicate submissions, and avoidable operational load for insurers and government field staff.

## Proposed Solution

Build a digital and assisted-channel platform that provides:

| Capability | Business value |
|---|---|
| Scheme-aware claim triage | Reduces incorrect or unnecessary intimation attempts |
| 72-hour deadline calculator | Reduces avoidable rejections for late intimation |
| Offline-first evidence capture | Allows farmers/agents to capture proof during poor connectivity |
| Multi-channel submission orchestration | Sends the intimation to the right insurer, portal, bank, or district channel |
| Acknowledgement ledger | Creates farmer-visible proof of reporting attempt and submission status |
| Multilingual guidance | Improves access for smallholders and non-English users |
| Status tracker | Reduces repeat calls and improves trust |
| Partner dashboard | Gives insurers, CSCs, and field officials clean queues and evidence packets |

## Target Users

| User group | Primary need |
|---|---|
| Smallholder farmer | Know whether to intimate, submit before deadline, receive acknowledgement |
| CSC/VLE or village agent | Help farmers submit complete claims quickly |
| Bank/PACS staff | Route loanee-farmer claim information without manual rework |
| Insurer claim team | Receive structured, deduplicated, geo-tagged claim packets |
| District agriculture/revenue officials | View localized event clusters and field-assessment workload |
| State program administrators | Monitor compliance, SLA bottlenecks, and grievance signals |

## Business Objectives

Phase 1 should target measurable operational outcomes:

| Objective | Indicative KPI |
|---|---|
| Reduce missed intimation windows | % farmer-initiated claims submitted within 72 hours |
| Improve claim packet completeness | % submissions with required identity, policy, location, crop, and evidence fields |
| Reduce channel confusion | % users correctly triaged to individual vs automatic claim path |
| Improve transparency | % claims with visible acknowledgement and current stage |
| Reduce support burden | Repeat inquiry rate per claim |
| Establish institutional viability | Number of pilot integrations or operating agreements |

## Phase 1 Replanned Roadmap

Phase 1 should run as a 12-week pilot with two parallel tracks: product build and institutional validation.

| Phase | Weeks | Focus | Key outputs |
|---|---:|---|---|
| Discovery and rule codification | 1-3 | PMFBY, RWBCIS, and pilot-state operating rules | Claim rule matrix, claim type decision tree, evidence checklist |
| MVP build | 2-6 | Farmer/agent intake, offline capture, deadline engine, acknowledgement ledger | Web/PWA or mobile MVP, admin console, submission packet format |
| Partner workflow setup | 4-7 | Insurer, CSC/bank, and district official workflows | Routing playbooks, CSV/API handoff, escalation paths |
| Pilot launch | 7-10 | 2-3 districts across 2 states | Live intimation support, operational monitoring |
| Evaluation and scale plan | 11-12 | KPI review and integration backlog | Pilot report, Phase 2 architecture backlog, commercial proposal |

## Phase 1 Scope

In scope:

- Claim type triage for localized calamity, post-harvest loss, prevented/failed sowing, widespread yield loss, mid-season adversity, and RWBCIS-style triggers.
- Rules engine for pilot states and selected crops.
- Farmer/agent guided intake in priority regional languages.
- Offline photo, GPS, timestamp, and draft claim capture.
- Submission packet generation for PMFBY/insurer/bank/district channels.
- Acknowledgement and status tracking where a system or operational feed is available.
- Partner dashboard for claim queues and field assessment coordination.

Out of scope for Phase 1:

- Direct payment processing.
- Replacing PMFBY, NCIP, insurer core claim systems, CCE systems, WINDS, or YES-TECH.
- Automated claim adjudication.
- Nationwide state coverage.
- Legal dispute or grievance adjudication.

## Operating Model

The platform should operate as a neutral facilitation layer:

1. Farmer or assisted-channel user reports the event.
2. Platform identifies scheme, crop, season, location, policy/application reference, and claim type.
3. Rules engine determines whether individual intimation is required.
4. Evidence service captures geo-tagged photos, timestamps, crop condition, and farmer declaration.
5. Routing service submits or prepares packets for the correct official channel.
6. Acknowledgement ledger records every attempt, success, failure, and manual handoff.
7. Status service updates the farmer and partner teams through SMS, WhatsApp, IVR, app, or dashboard.

## Risk Analysis

| Risk | Impact | Mitigation |
|---|---|---|
| Lack of official APIs | Status visibility may be incomplete | Start with CSV/manual assisted workflow; design adapters for future APIs |
| State-level rule variation | Wrong routing or expectations | Pilot-state rule governance and versioned rule approvals |
| Poor connectivity after calamity | Farmers cannot submit on time | Offline-first drafts and delayed sync with timestamp proof |
| Fraudulent or duplicate claims | Partner trust risk | Device, geo, timestamp, land parcel, and application-number deduplication |
| Privacy and consent gaps | Compliance and trust risk | Explicit consent, minimal data collection, audit logs, retention policy |
| Low adoption | Weak business outcome | CSC/bank/agent-assisted channels plus regional language UX |

## Business Case

The platform creates value by reducing avoidable friction rather than by changing insurance underwriting. For government and insurers, it can reduce incomplete submissions, repeat calls, and grievance escalation. For farmers, it improves clarity, confidence, and proof of action. For distribution partners, it creates a standard assisted-service workflow that can be measured and improved.

The strongest initial wedge is localized calamity and post-harvest loss, because these are high-stress, high-deadline, farmer-initiated claim categories where better intimation directly changes outcomes.

## Recommended Next Step

Proceed with a Phase 1 pilot design workshop with one PMFBY-heavy state, one state with meaningful local variation, one insurer, and one assisted-channel partner. The workshop should finalize pilot districts, crops, languages, handoff rules, and minimum data-sharing arrangements before engineering begins.

## References

- PMFBY Guidelines page, Ministry of Agriculture & Farmers Welfare: https://pmfby.gov.in/guidelines
- PMFBY FAQ and insurer list: https://www.pmfby.gov.in/faq
- PIB, "Climate Risk and Crop Insurance", 24 July 2026: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2289028
- PIB, "Advancing Crop Insurance Through Technology", 2025: https://www.pib.gov.in/PressNoteDetails.aspx?ModuleId=3&NoteId=155010
- Baseline roadmap: `document/Crop-Insurance-Claim-Intimation-Roadmap-India.md`
