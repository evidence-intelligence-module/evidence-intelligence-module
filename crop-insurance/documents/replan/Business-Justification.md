# Voice-Assisted Crop Claim Intimation

## Business Justification

**Status:** Prototype proposal  
**Objective:** Help insured farmers create a complete, traceable crop-loss intimation on day 1 and, where applicable, within the insurer's 72-hour window.

## 1. Problem

For farmer-initiated crop-loss cases, the first 72 hours are the most important and the least accessible. Farmers may not know whether a loss needs individual intimation, which insurer/channel to contact, which parcel is affected, or which policy details and evidence are required. A typical farmer may also have several insured parcels, making a generic phone-based claim request incomplete or misdirected.

Existing portals, insurer helplines, CSCs, and bank channels remain important, but they expect the farmer to navigate terminology, documentation, and multiple systems while dealing with a crop-loss event. The result is late, incomplete, duplicated, or untracked intimations.

## 2. Proposed Service

Create a multilingual voice-assisted service reachable by phone call and WhatsApp. The service uses Whisper for speech-to-text and an inference model (initially Qwen 2.5 via Ollama or an equivalent controlled hosted model) to conduct a constrained conversation. It identifies the caller, asks which insured land is affected, gathers only missing information, creates a structured claim-intimation request, and sends an acknowledgement with a platform transaction number.

The service is an **intimation and submission-facilitation layer**. It does not decide claim eligibility, approve claims, predict calamities, perform CCE, or conduct on-ground verification.

## 3. Initial Pilot Choice

Start with two bounded integrations:

| Pilot lane | Purpose | Integration approach |
|---|---|---|
| AIC / PMFBY route | Establish the public-scheme and insurer-routing pattern | Approved partner API, secure export, or assisted handoff after partner validation |
| One private insurer, proposed SBI General | Validate a second insurer adapter and different operating workflow | Same canonical packet, insurer-specific adapter and acknowledgement mapping |

SBI General is a proposed prototype target, not an assumed partnership. The actual pilot insurers, districts, crops, submission method, and rule content must be agreed in writing before any live use.

## 4. Who Benefits

| Stakeholder | Benefit |
|---|---|
| Farmers | Local-language assistance, less form filling, clear deadline guidance, and proof that an intimation was raised |
| Insurers | More complete first-contact data, fewer repeat contacts, standardized packets, and an auditable intake trail |
| CSCs, banks, and field teams | A consistent assisted workflow and a queue for exceptions instead of free-form calls |
| Platform operations | Measurable completion, deadline-risk, submission, and acknowledgement metrics |

## 5. Value Hypothesis

The service creates value by removing friction before official claim handling begins:

1. Identify the affected insured parcel correctly.
2. Capture the loss event and required details before the deadline.
3. Reuse verified farmer, land, crop, and policy data instead of asking the farmer to repeat it.
4. Send one normalized packet through the appropriate approved insurer route.
5. Give the farmer a transaction number and next steps immediately.

The prototype is successful if it increases the share of complete farmer-initiated intimations created within 72 hours while reducing manual correction and repeat calls.

## 6. MVP Scope

In scope:

- Inbound phone voice flow and WhatsApp evidence/notification follow-up.
- Hindi plus one pilot-state language.
- Pre-registration and consent-led farmer lookup by verified mobile number; OTP fallback for sensitive actions.
- FIN-based farmer record, multiple land parcels, linked policies, and readable land references.
- Localized calamity and post-harvest-loss intake for selected insurer/state/crop combinations.
- Insurance-document ingestion that converts approved public or partner-provided documents into reviewable rule/context objects.
- PostgreSQL prototype store, Kafka-based asynchronous processing, claim packet generation, acknowledgement ledger, and SMS/WhatsApp/email notifications.
- Human handoff for ambiguity, policy mismatch, low confidence, or failed submission.

Out of scope:

- CCE and CCE disputes.
- Calamity prediction, weather-trigger creation, or loss assessment.
- On-ground verification, claim adjudication, settlement, or payment.
- Broad web scraping that bypasses site terms, access controls, or partner approval.
- Nationwide or all-insurer deployment.

## 7. Success Measures

| Measure | Prototype target |
|---|---:|
| Eligible callers with a draft created within 72 hours | >= 80% |
| Correct land selection in reviewed calls | >= 90% |
| Drafts requiring material manual correction | <= 15% |
| Successful acknowledgement delivery | >= 95% |
| Duplicate packets created | < 1% |
| Calls escalated due to ambiguity or confidence | Measured and reduced by iteration |

## 8. Delivery and Commercial Path

Run a 12-week controlled pilot in one state, two districts, selected crops, and one or two approved insurer routes. Begin with pre-registered farmers and an assisted fallback. Price the service initially as a pilot implementation plus a per-completed-intimation or per-active-farmer operating fee; avoid presenting it as a replacement for regulated insurer or government systems.

The immediate decision required is sponsor approval to validate insurer participation, data-sharing, telephony/WhatsApp access, the pilot rule set, and the permitted submission route.
