# Voice Agent Claim Intimation Plan

Prepared: August 2026  
Parent initiative: Crop Insurance Claim Intimation Platform for India

---

## 1. Objective

Build a voice agent that can speak with farmers, understand their crop-insurance claim-intimation need, fetch existing farmer data from the backend, identify the correct land parcel and policy, prefill required intimation information, ask only for missing details, and hand off a structured claim packet for submission.

The agent should support farmers who may not be comfortable with forms, apps, English, or scheme terminology. The ideal interaction feels like an assisted call with a trained rural insurance operator, backed by structured backend tools.

## 2. In Scope

- Voice call intake for claim-intimation assistance.
- Farmer lookup by phone number, email, policy/application number, or assisted-agent reference.
- Retrieval of pre-collected farmer, land, crop, policy, and prior evidence data.
- Multi-land disambiguation, such as a farmer with three land parcels choosing the parcel affected by loss.
- Claim type triage for farmer-initiated intimation paths.
- Prefilling backend claim-intimation objects from existing data.
- Asking the farmer for missing fields only.
- Summarizing captured details back to the farmer for confirmation.
- Creating a draft or ready-to-submit claim packet.
- MCP/tool recommendations for backend access, document generation, messaging, and audit.

## 3. Out of Scope

- CCE processing or CCE dispute resolution.
- Calamity prediction.
- On-ground verification.
- Automated claim approval or settlement.
- Direct payment processing.
- Replacing PMFBY, insurer, bank, CSC, or state systems.

## 4. Target Conversation

Example scenario: the farmer owns or operates three land parcels and wants to intimate loss for one parcel.

```text
Agent: Namaste. I can help with crop insurance claim intimation. Are you calling from the phone number linked to your policy?

Farmer: Yes.

Agent: I found three insured land records. One is soybean in Village A, one is cotton in Village B, and one is paddy in Village C. Which land has the crop damage?

Farmer: Soybean, Village A.

Agent: I will proceed with the soybean land in Village A. Was the crop standing, harvested and drying, or not sown?

Farmer: Standing crop.

Agent: What happened to the crop?

Farmer: Hailstorm yesterday evening.

Agent: I have the land, policy, crop, and farmer details already. I need the approximate time of damage and whether photos are available. After that I will create the intimation draft and read the details back to you.
```

## 5. Recommended Architecture

```text
Phone / Web Call / Assisted Agent
        |
        v
Voice Gateway
  - SIP/WebRTC/telephony provider
  - Audio streaming
        |
        v
Realtime Voice Agent
  - Speech understanding
  - Regional language conversation
  - Tool calling
  - Confirmation before actions
        |
        v
Agent Orchestration Service
  - Session state
  - Tool policy
  - Human escalation
  - Audit events
        |
        v
MCP / Tool Layer
  - Farmer lookup
  - Land parcel lookup
  - Policy lookup
  - Claim triage
  - Document prefill
  - Evidence request
  - Submission handoff
  - Notification
        |
        v
Backend Platform
  - PostgreSQL operational data
  - Object storage for documents/photos/audio
  - Rules engine
  - Claim packet service
  - Acknowledgement ledger
```

## 6. Voice Technology Options

### Option A: Hosted Realtime Voice Agent

Use OpenAI Realtime for low-latency speech-to-speech over WebRTC, WebSocket, or SIP. This is the fastest path for a natural call experience because the model can handle audio input/output and tool calls during the same session.

Best fit:

- Pilot with real farmer calls.
- Multilingual interactive conversations.
- Interruptions and natural turn-taking.
- Tool-calling during a live call.

### Option B: Modular STT + LLM + TTS

Use a pipeline such as:

- Speech to text: Whisper or another STT service.
- Reasoning/dialogue: hosted model or local open model such as Qwen through Ollama.
- Text to speech: hosted or local TTS.
- Backend tools: MCP/custom APIs.

Best fit:

- More control over components.
- Offline or low-cost experiments.
- Local-model evaluation.

Tradeoff: latency and interruption handling can be harder than a native realtime voice stack.

### Recommended Path

Use Option A for the pilot voice experience and keep Option B as an evaluation track for cost-sensitive or offline/edge deployments. Do not start with a fully local stack unless the first milestone is only a lab prototype.

## 7. Backend Data Model

The agent should not operate on unstructured farmer notes. Store farmer and claim context as structured objects in PostgreSQL, with documents and media in object storage.

### Core Objects

```json
{
  "farmer": {
    "farmerId": "uuid",
    "name": "string",
    "mobile": "string",
    "email": "string",
    "preferredLanguage": "hi-IN",
    "consentStatus": "ACTIVE"
  },
  "landParcels": [
    {
      "landId": "uuid",
      "village": "string",
      "district": "string",
      "state": "string",
      "surveyNumber": "string",
      "areaHectares": 1.2,
      "crop": "SOYBEAN",
      "season": "KHARIF",
      "policyId": "uuid"
    }
  ],
  "policies": [
    {
      "policyId": "uuid",
      "scheme": "PMFBY",
      "insurer": "string",
      "applicationNumber": "string",
      "policyNumber": "string",
      "crop": "SOYBEAN",
      "season": "KHARIF",
      "status": "ACTIVE"
    }
  ]
}
```

### Claim Draft Object

```json
{
  "claimDraftId": "uuid",
  "farmerId": "uuid",
  "landId": "uuid",
  "policyId": "uuid",
  "callSessionId": "uuid",
  "claimType": "LOCALIZED_CALAMITY",
  "eventType": "HAILSTORM",
  "eventDateTime": "2026-08-08T18:30:00+05:30",
  "cropStage": "STANDING",
  "damageDescription": "Farmer reported hailstorm damage to standing soybean crop",
  "missingFields": ["geoTaggedPhotos"],
  "prefillStatus": "PARTIAL",
  "confirmationStatus": "PENDING",
  "submissionStatus": "DRAFT"
}
```

## 8. Data Collection Before the Call

The voice agent works best when farmer data is collected before the claim call. Recommended channels:

| Channel | Data collected | Notes |
|---|---|---|
| Policy enrollment/import | Farmer, crop, land, policy, insurer, season | Best source if partner integration exists |
| Phone number lookup | Farmer identity and linked policies | Should require OTP or call-line verification for sensitive data |
| Email upload | Policy PDF, land docs, claim forms | Use document extraction and human review for uncertain fields |
| Assisted CSC/bank intake | Farmer and land records | Good for low-literacy users |
| WhatsApp/SMS pre-registration | Mobile, language, location, crop | Useful for lightweight onboarding |
| Agent upload | Existing field team uploads documents/photos | Requires clear consent and audit trail |

## 9. MCP and Tooling Recommendation

MCP is useful here as a controlled tool boundary between the voice agent and backend actions. The voice model should not query the database directly. It should call named tools with explicit schemas and permission checks.

### Recommended MCP Servers

| MCP server | Build or plugin | Purpose |
|---|---|---|
| `farmer-records-mcp` | Custom | Lookup farmer by verified phone/email/application number |
| `land-policy-mcp` | Custom | Fetch land parcels, crop, season, and linked policy details |
| `claim-rules-mcp` | Custom | Triage claim type, deadline, required evidence, and routing |
| `claim-draft-mcp` | Custom | Create/update claim draft and prefilled document object |
| `document-generation-mcp` | Custom | Generate PDF/JSON claim packet from confirmed fields |
| `object-storage-mcp` | Custom | Store/retrieve policy PDFs, photos, call artifacts, and generated packets |
| `notification-mcp` | Custom or provider-backed | Send SMS/WhatsApp links, OTPs, evidence upload links, and acknowledgements |
| `audit-consent-mcp` | Custom | Record consent, tool calls, confirmations, and sensitive data access |
| `email-ingestion-mcp` | Outlook/Gmail/custom | Ingest pre-submitted farmer documents from email |
| `telephony-mcp` | Custom/Twilio/Exotel provider wrapper | Initiate calls, receive call events, and manage human escalation |
| `human-handoff-mcp` | Custom/CRM/helpdesk | Transfer complex calls to an operator with transcript and draft context |

### Plugin Notes

- If using managed Postgres, a Neon Postgres or Supabase connector can help for development/admin workflows, but production voice agents should use a narrow custom MCP rather than broad database access.
- If document collection through email is important, an Outlook Email or Gmail-style connector can be useful for ingestion, but the agent should only access documents after explicit farmer consent.
- For production calls in India, a telephony provider integration such as Exotel, Twilio, Knowlarity, or a SIP trunk should be wrapped behind your own `telephony-mcp`.

### Tool Safety Rule

Every tool should be designed around business actions, not raw tables.

Good:

```text
get_verified_farmer_profile(phone_number)
list_claim_eligible_land_parcels(farmer_id)
create_claim_draft(farmer_id, land_id, policy_id, event_details)
confirm_claim_summary(claim_draft_id)
generate_claim_packet(claim_draft_id)
```

Avoid:

```text
run_sql(query)
read_any_file(path)
send_any_email(to, body)
```

## 10. Agent Tool Contract

Minimum tools for MVP:

| Tool | Inputs | Output |
|---|---|---|
| `verify_farmer_identity` | phone/email/application number, OTP or call verification | verified farmer ID |
| `get_farmer_context` | farmer ID | farmer profile, language, linked land/policies |
| `select_land_parcel` | farmer ID, farmer spoken selection | selected land ID and confidence |
| `triage_claim_type` | land ID, policy ID, event, crop stage, event date | claim type, deadline, required fields |
| `create_or_update_claim_draft` | confirmed fields | claim draft ID and missing fields |
| `read_claim_summary` | claim draft ID | farmer-friendly summary |
| `mark_farmer_confirmation` | claim draft ID, confirmation result | confirmed/rejected/requires correction |
| `generate_claim_packet` | confirmed claim draft ID | packet URI and packet status |
| `send_evidence_upload_link` | claim draft ID, phone number | SMS/WhatsApp status |
| `handoff_to_human` | session ID, reason | queue ID and callback status |

## 11. Call Flow

```text
1. Start call
2. Detect language or ask language preference
3. Explain purpose and obtain consent
4. Verify farmer identity
5. Fetch farmer context
6. If multiple land parcels, ask farmer to choose affected land
7. Confirm selected land, crop, season, and policy
8. Ask event type, date/time, crop stage, and damage summary
9. Triage claim type and deadline
10. Prefill claim draft from backend data
11. Ask only missing required fields
12. Read claim summary back to farmer
13. Ask explicit confirmation
14. Generate claim packet or draft
15. Send acknowledgement/evidence link/next steps
16. Close call or transfer to human operator
```

## 12. Confirmation Policy

The agent must not submit or mark a claim packet as farmer-confirmed until it has read back:

- Farmer name or masked identity.
- Selected land parcel.
- Crop and season.
- Policy/application reference, masked where needed.
- Event type and event date/time.
- Claim type and deadline.
- Missing documents or evidence.
- Intended next action.

The farmer must give an explicit confirmation such as "yes, submit", "haan, bhejiye", or equivalent in the selected language.

## 13. Human Handoff Triggers

Escalate to a human when:

- Identity verification fails.
- Farmer disputes backend land/policy data.
- Farmer has more than one plausible affected land parcel and confidence is low.
- Claim type cannot be determined.
- The call concerns rejection, grievance, settlement dispute, or CCE.
- Farmer reports severe distress or asks for a person.
- Deadline is close and digital submission route fails.

## 14. Security, Privacy, and Compliance

Required controls:

- Consent before accessing farmer records.
- OTP or equivalent verification before revealing sensitive records.
- Do not read full Aadhaar, bank account, or sensitive identifiers aloud.
- Mask policy/account identifiers where possible.
- Record audit trail for every data fetch, claim draft update, and confirmation.
- Store call transcripts/audio only if consent and retention policy allow it.
- Separate raw call transcript from structured claim packet.
- Use least-privilege MCP tools rather than direct database access.

## 15. Phased Implementation Plan

### Phase 0: Design Sprint, 1-2 Weeks

Outputs:

- Final call scripts in 2 pilot languages.
- Farmer identity and consent policy.
- Land/policy data schema.
- MCP tool schemas.
- Human handoff process.

### Phase 1: Internal Prototype, 3-4 Weeks

Build:

- Voice or simulated voice agent.
- Farmer lookup by phone number.
- Multi-land selection flow.
- Claim draft prefill.
- Claim summary confirmation.
- Audit log.

Success criteria:

- Agent can complete 20 scripted calls with correct land selection and draft creation.
- No raw SQL or broad backend access from the agent.
- All confirmations are auditable.

### Phase 2: Assisted Pilot, 4-6 Weeks

Build:

- Real telephony/WebRTC call path.
- Regional language support.
- Evidence upload link by SMS/WhatsApp.
- Operator dashboard for failed/uncertain calls.
- Claim packet generation.

Success criteria:

- 80%+ successful identity verification for pre-registered farmers.
- 90%+ correct land parcel selection in test calls.
- Less than 10% manual correction rate for prefilled drafts.

### Phase 3: Production Pilot, 8-12 Weeks

Build:

- Partner routing integration.
- Stronger analytics.
- Call quality monitoring.
- Human escalation SLA.
- Privacy and retention controls.

Success criteria:

- Reduced time to create intimation packet.
- Increased within-window claim draft completion.
- Reduced farmer repeat calls.
- Clear audit evidence for all submissions and draft actions.

## 16. MVP Backlog

| Priority | Item |
|---|---|
| P0 | Farmer consent and identity verification |
| P0 | Farmer/land/policy context API |
| P0 | Multi-land disambiguation dialogue |
| P0 | Claim triage and deadline tool |
| P0 | Claim draft creation/update |
| P0 | Farmer confirmation summary |
| P0 | Audit log for tool calls |
| P1 | Telephony/WebRTC integration |
| P1 | SMS/WhatsApp evidence upload link |
| P1 | Human handoff dashboard |
| P1 | Claim packet PDF/JSON generation |
| P2 | Email document ingestion |
| P2 | Local model/Ollama evaluation |
| P2 | Advanced dialect and noise robustness testing |

## 17. Key Design Decisions

| Decision | Recommendation |
|---|---|
| Agent data access | Use narrow MCP tools, not direct DB access |
| Data store | PostgreSQL for structured objects; object storage for media/documents |
| First voice stack | Hosted realtime voice for pilot; local STT/LLM/TTS as evaluation track |
| Land selection | Agent reads concise land summaries and asks farmer to choose |
| Claim document fill | Backend claim draft service owns field mapping and validation |
| Submission | Require explicit read-back confirmation before packet generation/submission |
| Human escalation | Always available for identity, dispute, grievance, or low-confidence cases |

## 18. Open Questions

1. Which languages should the first pilot support?
2. Will calls be inbound, outbound, or both?
3. Which identifier is most reliable for farmer lookup: phone, email, application number, or bank/CSC reference?
4. Will policy and land data be imported from existing systems or collected by your own onboarding flow?
5. Should the agent generate only a draft, or also submit to an external channel after confirmation?
6. Which telephony provider is preferred for India deployment?

## 19. References

- OpenAI Realtime API reference: https://developers.openai.com/api/reference/resources/realtime
- OpenAI API quickstart and Agents SDK overview: https://platform.openai.com/docs/quickstart/make-your-first-api-request
- Existing HLD: `../Crop-Insurance-Claim-Intimation-HLD.md`
- Existing LLD: `../Crop-Insurance-Claim-Intimation-LLD.md`
- Inclusion notes: `../inclusion.md`
- Exclusion notes: `../exclusion list.md`
