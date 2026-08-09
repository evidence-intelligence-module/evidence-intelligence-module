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
Telephony + WhatsApp gateway
           |
           v
Voice session service
  Whisper STT <-> dialogue orchestrator <-> TTS
                       |               
                       v
          Controlled agent tools / APIs
                       |
                       +--> Farmer, land, policy and consent services
                       +--> Rules and document-knowledge service
                       +--> Claim draft and packet service
                       +--> Notification and acknowledgement service
                       |
                       v
              PostgreSQL + object storage
                       |
                       v
                     Kafka topics
                       |
                       v
       Inference, document ingestion, insurer adapter workers
                       |
                       v
             AIC/PMFBY and private-insurer approved routes
```

## 3. Primary Call Journey

1. Receive call, select/detect language, state purpose, and capture consent.
2. Match the caller to a FIN using verified mobile number; use OTP or assisted verification if needed.
3. Fetch only the farmer's eligible active land/policy summaries.
4. If more than one land is plausible, ask using village, plot/survey number, crop, season, and area—not opaque IDs.
5. Capture loss event, date/time, crop stage, and description.
6. Rules service determines whether this selected pilot case requires individual intimation and the deadline.
7. Create/update an idempotent claim-intimation draft; prefill trusted fields and ask only for missing mandatory fields.
8. Read back land, policy reference (masked), event, deadline, missing evidence, and intended submission action.
9. On explicit confirmation, publish a `claim-intimation.confirmed` event to Kafka.
10. Submission worker validates, creates the insurer-specific packet, submits/handoffs through the approved route, and records the outcome.
11. Notify the farmer by WhatsApp/SMS/email with the platform transaction number and the official acknowledgement when available.

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

## 5. FIN and Land Identifier

`FIN` is the immutable, platform-issued Farmer Identification Number, for example `FIN-IN-MH-00018427`. It is never inferred from a phone number and is not exposed in every message.

Each land parcel has an immutable UUID and a human-readable composite reference:

```text
LAND-{FIN}-{STATE}-{DISTRICT}-{VILLAGE}-{PLOT}
Example: LAND-FIN-IN-MH-00018427-MH-NASHIK-NIPHAD-142-3A
```

The composite reference is a display/search key, not the database primary key. Normalize each component, preserve the authority/source for the survey/plot number, and append a short parcel sequence only when the source plot number is not unique. During calls, read a friendly summary such as “plot 142/3A in Niphad, soybean, 1.2 hectares.”

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

## 8. Prototype Deployment

Deploy containerized services behind an API gateway. PostgreSQL holds canonical transactional objects; object storage holds source documents, evidence, and consented call artifacts; Kafka carries asynchronous work. Ollama inference may run in a segregated private environment for the prototype, with capacity and language-quality testing before production use. Telephony, WhatsApp, and Resend are external providers behind provider adapters.

## 9. Explicit Boundaries

The architecture does not include CCE, field experiments, loss/calamity prediction, satellite assessment, on-ground verification, claim approval, or payment. It records only the farmer's reported intimation and the controlled handoff outcome.
