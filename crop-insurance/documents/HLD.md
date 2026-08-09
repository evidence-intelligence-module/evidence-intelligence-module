# Crop Insurance Claim Intimation Platform

## High-Level Design

Prepared: August 2026  
Document status: Phase 1 architecture proposal

---

## 1. Purpose

This document defines the high-level architecture for a crop insurance claim intimation platform for India. The platform enables farmers and assisted-channel users to determine whether a crop loss requires intimation, submit complete evidence within the required window, route the claim to the correct institution, and track acknowledgement/status.

The design is intentionally an orchestration layer. It is not a replacement for PMFBY/NCIP, insurer claim systems, CCE processes, WINDS, YES-TECH, banks, CSCs, or state agriculture systems.

## 2. Architecture Goals

| Goal | Description |
|---|---|
| Farmer-first | Provide simple claim guidance in local languages and assisted-channel contexts |
| Rule-aware | Handle claim type, crop, season, state, scheme, and deadline variation |
| Offline tolerant | Capture evidence during poor connectivity and sync later |
| Integration ready | Support API, CSV, email, dashboard, and manual operating workflows |
| Auditable | Preserve event timeline, consent, submission attempts, and acknowledgements |
| Secure by default | Protect farmer identity, policy, land, bank, and location data |
| Scalable by state | Add rules and partner integrations without rewriting the product |

## 3. System Context

```text
Farmer / CSC / Bank / Agent
        |
        v
Claim Intimation Platform
        |
        +--> PMFBY / NCIP channels
        +--> Insurer claim systems
        +--> Bank / PACS / CSC workflow
        +--> District agriculture / revenue officials
        +--> Weather, satellite, and scheme reference sources
        +--> SMS / WhatsApp / IVR / email providers
```

## 4. Major User Journeys

### 4.1 Farmer-Initiated Claim

1. User selects language and identifies location, crop, season, event date, and damage type.
2. Platform checks whether the damage type requires individual intimation.
3. Deadline engine calculates remaining time.
4. User captures photos, GPS, timestamp, farmer declaration, policy/application details, and land/crop information.
5. Platform validates minimum completeness.
6. Routing engine sends or prepares submission for insurer/PMFBY/bank/district channel.
7. Acknowledgement ledger records submission attempt and result.
8. Farmer receives SMS/WhatsApp/IVR/app confirmation and next-step instructions.

### 4.2 Automatic Area-Based Claim Explanation

1. User reports broad drought/flood/yield concern.
2. Platform identifies that claim is likely area-approach or weather-index triggered.
3. User is told that individual intimation may not be required.
4. Platform records advisory interaction and optionally subscribes the farmer to status alerts.
5. Status service later explains CCE, YES-TECH, RWBCIS, or state-notified event progress where data is available.

### 4.3 Assisted-Channel Submission

1. CSC/VLE, bank, or field agent logs into assisted dashboard.
2. Agent searches or creates farmer profile with consent.
3. Agent completes guided claim intake.
4. Platform generates structured packet and acknowledgement slip.
5. Agent can monitor claim handoff queue and failed submissions.

## 5. Logical Architecture

```text
Client Layer
  - Farmer PWA/mobile app
  - Assisted-channel web app
  - Partner/admin dashboard
  - SMS/WhatsApp/IVR entry points

Experience Services
  - Claim triage service
  - Multilingual content service
  - Evidence capture service
  - Notification service

Domain Services
  - Farmer profile service
  - Policy/application service
  - Scheme rules service
  - Deadline service
  - Claim packet service
  - Routing and submission service
  - Acknowledgement ledger
  - Claim status service
  - Audit and consent service

Integration Layer
  - PMFBY/NCIP adapter
  - Insurer adapter
  - Bank/PACS/CSC adapter
  - District official workflow adapter
  - Weather/remote-sensing reference adapter
  - Messaging adapter

Data Layer
  - Relational operational database
  - Object storage for evidence
  - Rules repository
  - Event/audit log
  - Analytics warehouse
```

## 6. Core Components

| Component | Responsibility |
|---|---|
| Claim triage service | Determines claim path based on location, crop, peril, event timing, and scheme rules |
| Scheme rules service | Stores versioned PMFBY/RWBCIS/state rules, claim windows, evidence requirements, and routing rules |
| Deadline service | Calculates intimation deadlines and reminder schedules |
| Evidence capture service | Manages geo-tagged photos, metadata, offline drafts, upload sync, and media validation |
| Claim packet service | Produces a normalized claim packet for API, CSV, PDF, email, or manual submission |
| Routing service | Selects destination channel and manages retries/failures |
| Acknowledgement ledger | Records all submission attempts, timestamps, channel responses, and manual handoffs |
| Status service | Pulls or receives updates from partners and maps them to farmer-friendly stages |
| Notification service | Sends reminders, acknowledgements, status updates, and escalation messages |
| Partner dashboard | Gives insurers/admins/agents operational queues and filters |

## 7. Data Domains

| Domain | Example attributes |
|---|---|
| Farmer | Name, mobile, language, consent records, assisted-channel linkage |
| Farm/land | State, district, village, survey/plot identifier, GPS/polygon, acreage |
| Policy/application | PMFBY application number, insurer, season, crop, sum insured reference, bank/PACS reference |
| Loss event | Peril, event date/time, discovery date, crop stage, damage description |
| Evidence | Photos, GPS, timestamp, device metadata, declaration, supporting documents |
| Claim | Claim type, deadline, status, submission packet, acknowledgement |
| Rule | Scheme, state, crop, season, claim type, window, evidence, routing |
| Audit | Actor, action, timestamp, channel, outcome, data version |

## 8. Integration Strategy

Phase 1 should support multiple integration depths because official APIs may be unavailable or inconsistent.

| Integration level | Mechanism | Use case |
|---|---|---|
| Level 0 | Export packet as PDF/CSV | Manual insurer or district handoff |
| Level 1 | Email/SFTP/batch upload | Partner accepts structured daily claim packets |
| Level 2 | Partner API | Real-time submission and status pull |
| Level 3 | Event webhook | Partner pushes claim status changes |

The routing layer must preserve the same internal claim model regardless of partner integration maturity.

## 9. Security and Privacy

Minimum controls:

- Explicit consent before collecting identity, location, land, policy, or media data.
- Role-based access for farmer, assisted agent, insurer, district official, and platform admin.
- Encryption in transit and at rest.
- Signed URLs or equivalent controlled access for evidence media.
- Tamper-evident audit logs for submission and acknowledgement events.
- Configurable data retention by scheme, partner contract, and legal requirement.
- Masking of bank/account identifiers in non-essential views.

## 10. Availability and Resilience

The most important resilience requirement is offline capture at the edge. Farmers and agents must be able to create a complete draft during a connectivity outage and sync when available.

Recommended service qualities:

| Capability | Target behavior |
|---|---|
| Offline draft | Store claim draft, photos, GPS, and timestamp locally until sync |
| Retry | Automatic retry for failed uploads and submissions |
| Idempotency | Prevent duplicate claim packets for repeated sync attempts |
| Observability | Track submission failures by channel, region, and partner |
| Degraded mode | Generate downloadable/printable packet if direct submission fails |

## 11. Deployment View

```text
CDN / Edge
  -> Web/PWA frontend

API Gateway
  -> Authentication and authorization
  -> Rate limiting
  -> Request routing

Application Services
  -> Claim triage
  -> Rules
  -> Evidence
  -> Routing
  -> Notifications
  -> Status

Data Platform
  -> PostgreSQL-compatible operational database
  -> Object storage
  -> Queue/event bus
  -> Analytics store

External Providers
  -> Messaging
  -> Insurer/PMFBY/bank/district systems
  -> Weather/reference data sources
```

## 12. Phase 1 MVP Boundaries

MVP must include:

- Farmer/agent intake for pilot states.
- Claim type decision tree.
- Deadline and reminder engine.
- Offline evidence capture.
- Claim packet generation.
- Submission handoff tracking.
- Basic partner dashboard.
- Status stages, even if some stages are manually updated.

MVP should defer:

- Fully automated adjudication.
- Payment reconciliation.
- Nationwide rule coverage.
- Deep CCE dispute tooling.
- Advanced remote-sensing loss estimation.

## 13. Key Architecture Decisions

| Decision | Recommendation |
|---|---|
| Client type | PWA-first for fast pilot rollout; native wrapper can follow if needed |
| Rules model | Versioned data-driven rules, not hard-coded logic |
| Evidence storage | Object storage with metadata in relational database |
| Integrations | Adapter pattern with API/CSV/manual modes |
| Status model | Canonical internal stages mapped from partner-specific statuses |
| Event handling | Queue-based async routing and notifications |
| Pilot operating mode | Hybrid digital plus assisted workflow |

## 14. Open Questions

1. Which two states and districts will be used for Phase 1?
2. Which insurers or district offices will accept structured submission packets?
3. Which languages are required for the pilot?
4. Will the platform be allowed to submit directly to official channels, or only assist and prepare packets?
5. What is the minimum acceptable acknowledgement proof for operational and legal purposes?
6. What partner data can be used for status tracking?

## 15. References

- PMFBY Guidelines page: https://pmfby.gov.in/guidelines
- PMFBY FAQ: https://www.pmfby.gov.in/faq
- PIB, "Climate Risk and Crop Insurance", 24 July 2026: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2289028
- Baseline roadmap: `document/Crop-Insurance-Claim-Intimation-Roadmap-India.md`
