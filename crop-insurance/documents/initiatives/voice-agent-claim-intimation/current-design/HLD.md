# Voice-Assisted Crop Claim Intimation

## High-Level Design

**Status:** Prototype architecture  
**Scope:** Farmer-initiated claim intimation for one or two approved insurers.

## 1. Design Principles

- Voice first, but never voice only: use WhatsApp/SMS/email for evidence links and acknowledgements.
- Constrain the AI to guided intake and approved tools; backend rules and validation determine workflow.
- Treat a farmer's mobile number as a lookup hint, not proof of identity; use consent and OTP/verified caller controls before sensitive actions.
- Store canonical structured data in PostgreSQL and media/original documents in object storage.
- Keep insurer-specific requirements behind adapters; the voice flow works against one canonical request.
- Submit only after a spoken read-back and explicit confirmation.

## 2. System Context

```text
Farmer phone call / WhatsApp
           |
           v
Telephony + WhatsApp gateway (Exotel/Twilio + Gupshup/Twilio)
           |
           v
Voice session service
  IndicWhisper STT <-> dialogue orchestrator (Qwen 2.5/Ollama) <-> TTS
                       |
                       v
          Controlled agent tools / APIs
                       |
                       +---> Farmer identity service
                       |       +---> AgriStack UFSI (Farmer Registry, Land Verification)
                       |       +---> Local PostgreSQL (FIN, contacts, consent)
                       +---> Peril validation gateway
                       |       +---> Rule service (versioned scheme/state/crop rules)
                       |       +---> Peril-type classifier (individual vs. area-based)
                       +---> Evidence collection service
                       |       +---> WhatsApp photo/video prompt
                       |       +---> EXIF/GPS/timestamp validator
                       |       +---> S3-compatible object storage
                       +---> Claim draft and packet service
                       +---> Notification and acknowledgement service
                       |
                       v
              PostgreSQL + object storage
                       |
                       v
                     Kafka topics
                       |
                       v
       Submission workers + insurer adapters
                       |
                       +---> Level 0: CSV/PDF export (manual handoff)
                       +---> Level 1: Email/SFTP batch upload
                       +---> Level 2: Partner REST API (NCIP/insurer)
                       +---> Level 3: Event webhook (status push)
```

## 3. Primary Call Journey

1. Receive call; detect or select language; state purpose and capture consent.
2. Match the caller's phone number to registered farmer contacts.
3. If multiple FINs are linked to the phone, present farmer names and ask the caller to identify themselves: "Is this call for [Name A] or [Name B]?"
4. Verify identity via OTP or assisted verification before accessing any policy data.
5. Fetch eligible active land and policy summaries for the verified FIN.
6. If multiple active policies exist on the same plot across seasons, present season-specific options: "Are you reporting for your Kharif 2026 soybean policy or your Rabi 2025-26 wheat policy on plot 142/3A?"
7. If more than one land parcel is plausible, present readable choices using village, crop, season, and area — not opaque IDs.
8. Capture loss event details: peril type, date and time, crop stage, and damage description.
9. Peril validation gateway checks the reported peril against approved scheme rules for the selected district, season, and crop:
   - If covered under individual intimation: proceed to draft creation.
   - If area-based or CCE-assessed: inform the farmer immediately in their regional language ("Drought losses in your district are assessed through government yield estimates. Individual intimation is not required."), log the advisory interaction, and exit intake gracefully.
   - If ambiguous or unrecognized: escalate to a human operator.
10. Create or update an idempotent claim-intimation draft; prefill trusted fields and ask only for missing mandatory fields.
11. Prompt the farmer for geo-tagged photographic evidence via WhatsApp: "We will send you a WhatsApp message now. Please reply with 2-3 clear photos of the crop damage taken at your field."
12. Read back the complete summary: land, policy reference (masked), event, deadline, missing evidence status, and intended submission action.
13. On explicit spoken confirmation, publish a `claim-intimation.confirmed` event to Kafka.
14. Submission worker performs deduplication check using FIN, land ID, calamity date, and calamity type. If a duplicate is detected, the existing transaction number is returned and evidence is merged.
15. Submission worker validates, creates the insurer-specific packet, and submits through the approved route (Level 0-3 adapter).
16. Notify the farmer via WhatsApp and SMS with the platform transaction number, official acknowledgement when available, and next steps.

## 4. Core Services

| Service | Responsibility |
|---|---|
| Voice session service | Call state, turn handling, recordings/transcripts subject to consent, interruption recovery |
| Speech services | Whisper transcription and regional-language TTS; retain confidence and timestamps |
| Dialogue orchestrator | Qwen 2.5/Ollama or approved model; gathers facts but cannot query DB or submit directly |
| Agent tool gateway | Authenticates, authorizes, validates schemas, redacts logs, and exposes business-level tools |
| Farmer profile service | FIN, contact verification, consent, and profile lifecycle |
| Land-policy service | Returns concise eligible parcel and policy summaries; resolves selected parcel |
| Rule service | Versioned insurer/state/crop rules, deadline logic, mandatory fields, and routing eligibility |
| Claim draft service | Canonical request, validation, confirmation, idempotency, and packet readiness |
| Document knowledge service | Ingests sanctioned insurer documents, extracts structured requirements, and publishes reviewed rule candidates |
| Submission adapter service | Converts canonical requests to partner-specific API/export/manual handoff and tracks responses |
| Notification service | Resend for email; approved SMS/WhatsApp provider for transactional messages |
| Peril validation gateway | Classifies reported peril as individual-intimation-required vs. area-based; returns scheme rule match or advisory exit explanation in farmer-friendly regional language |
| Evidence collection service | Manages asynchronous WhatsApp photo/video prompts, EXIF metadata extraction, GPS-to-land-parcel boundary matching, and 72-hour timestamp compliance checks |
| Identity disambiguation service | Resolves phone-to-multiple-FINs mapping; presents named choices during voice flow; manages OTP for sensitive actions |

## 5. FIN and Land Identifier

`FIN` is the immutable, platform-issued Farmer Identification Number, for example `FIN-IN-MH-00018427`. It is never inferred from a phone number and is not exposed in every message.

Each land parcel has an immutable UUID and a human-readable composite reference:

```text
LAND-{FIN}-{STATE}-{DISTRICT}-{VILLAGE}-{PLOT}
Example: LAND-FIN-IN-MH-00018427-MH-NASHIK-NIPHAD-142-3A
```

The composite reference is a display/search key, not the database primary key. Normalize each component, preserve the authority/source for the survey/plot number, and append a short parcel sequence only when the source plot number is not unique. During calls, read a friendly summary such as “plot 142/3A in Niphad, soybean, 1.2 hectares.”

The primary lookup chain during a voice session follows this resolution order:

```text
Phone Number → List of registered FINs (may be multiple)
  → Farmer selects identity (voice confirmation)
    → FIN → Land Parcels (Khasra/Survey No.)
      → Active Policies (filtered by current Season/Year)
        → Selected Land-Policy pair for this intimation
```

## 6. Document Knowledge Pipeline

The system needs a separate knowledge process because insurer forms and instructions change. It must not let an LLM silently invent rules.

```text
Approved insurer/public document or authorised URL
  -> fetch/upload with provenance and version
  -> OCR/text extraction + structural parsing
  -> LLM-assisted candidate extraction
  -> normalized rule/context object
  -> human insurance-operations approval
  -> versioned rule service
```

The resulting object contains document source, effective dates, insurer/state/crop applicability, claim type, deadline policy, required fields/evidence, field mappings, submission route, and reviewer approval. The voice agent consumes only approved active versions.

## 7. Security and Operating Controls

- Obtain consent before account lookup and a second explicit confirmation before submission.
- Mask policy and personal identifiers in read-back, notifications, logs, and operator screens.
- Use least-privilege tools, row-level data access, encrypted storage, signed object URLs, and a tamper-evident audit trail.
- Keep AI prompts free of unnecessary PII; pass stable internal IDs after verification.
- Enforce idempotency on draft creation and partner submission.
- Escalate to a human for failed identity checks, land/policy disagreement, rule uncertainty, low transcription confidence, or partner failure near deadline.
- Comply with Aadhaar Vault requirements: store only Aadhaar reference keys, never raw Aadhaar numbers, in all platform databases and logs.
- Implement DPDP Act 2023 consent-brokered data access for any AgriStack UFSI integration; farmer must explicitly authorize sharing of registry data.
- Capture call recording consent before recording begins; stop recording immediately if consent is withdrawn mid-call.

## 8. Prototype Deployment

Deploy containerized services behind an API gateway. PostgreSQL holds canonical transactional objects; object storage holds source documents, evidence, and consented call artifacts; Kafka carries asynchronous work. Ollama inference may run in a segregated private environment for the prototype, with capacity and language-quality testing before production use. Use IndicWhisper (AI4Bharat fine-tuned Whisper) as the primary ASR engine instead of vanilla Whisper, with domain prompt-tuning: all STT requests include the context prompt "This is a conversation about crop insurance claim intimation under PMFBY/RWBCIS in India." Apply IndicNLP normalization for Devanagari and Tamil script preservation. Telephony, WhatsApp, and Resend are external providers behind provider adapters.

## 9. Explicit Boundaries

The architecture does not include CCE, field experiments, loss/calamity prediction, satellite assessment, on-ground verification, claim approval, or payment. It records only the farmer's reported intimation and the controlled handoff outcome.
