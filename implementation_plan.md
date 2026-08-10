# Replanned Implementation: Voice-Assisted Crop Insurance Claim Intimation System

**Date:** 10 August 2026  
**Context:** Complete replan incorporating business logic evaluation, existing design documentation, and updated regulatory/technical research.

---

## Background & Rationale for Replan

The existing workspace contains a mature, well-structured documentation suite across [baseline](file:///d:/Barrel/task/ACIX/crop-insurance/documents/baseline/) and [voice-agent initiative](file:///d:/Barrel/task/ACIX/crop-insurance/documents/initiatives/voice-agent-claim-intimation/current-design/) directories. However, the external business logic evaluation surfaced **critical gaps** that require architectural revisions before implementation begins:

1. **Peril-type gating is missing** — the system must validate whether a reported calamity actually *requires* individual intimation before processing.
2. **Mandatory visual evidence collection** — a voice-only flow is insufficient; geo-tagged photo/video evidence must be collected in-band (WhatsApp) or asynchronously.
3. **NCIP/Insurer API integration strategy is underspecified** — third-party APIs are rarely public; the system needs a formal multi-tier integration model with graceful fallback.
4. **Phone-number-to-farmer resolution is ambiguous** — rural households share phones; the system needs explicit identity disambiguation.
5. **Seasonal policy multiplicity** — a farmer may have overlapping policies on the same plot across Kharif/Rabi seasons.
6. **AgriStack integration opportunity** — UFSI (Unified Farmer Service Interface) and the Farmer Registry now provide standardized identity/land verification APIs.
7. **IndicWhisper over vanilla Whisper** — domain-specific fine-tuned ASR is needed for accurate crop insurance terminology in regional languages.

---

## User Review Required

> [!IMPORTANT]
> **Integration Tier Decision:** The NCIP and insurer backends do not expose public APIs for third-party claim submission. This plan proposes a 4-tier integration model (Level 0–3) where the prototype starts at Level 0/1 (CSV/PDF export + email/SFTP) and graduates to Level 2/3 (REST API + Webhooks) only after formal institutional authorization from DA&FW or participating insurers. **Do you have any existing institutional relationships or authorization pathways with AIC, SBI General, or the DA&FW that could accelerate Level 2/3 integration?**

> [!IMPORTANT]
> **AgriStack Sandbox Access:** The replan proposes using AgriStack's UFSI APIs for farmer identity verification and land parcel resolution (replacing manual FIN seeding). This requires applying through the DA&FW for sandbox access under the consent-brokered framework. **Should we proceed with AgriStack integration as the primary identity/land source, or keep the current self-managed FIN/land registry and add AgriStack as a future enhancement?**

> [!WARNING]
> **Claim Settlement & Grievance Redressal Out of Scope:** The business logic evaluation included detailed flows for Claim Settlement (surveyor allocation, evidence validation, loss calculation, DBT disbursement) and Grievance Redressal (status inquiry, rejection management, appeals). Per the existing scope boundaries in the workspace ([Business-Justification.md](file:///d:/Barrel/task/ACIX/crop-insurance/documents/initiatives/voice-agent-claim-intimation/current-design/Business-Justification.md), [baseline HLD §12](file:///d:/Barrel/task/ACIX/crop-insurance/documents/baseline/HLD.md#L213)), these are explicitly excluded from Phase 1. **Should we maintain this boundary, or expand Phase 1 scope to include settlement tracking and grievance redressal?**

---

## Open Questions

> [!IMPORTANT]
> 1. **Pilot Language Selection:** The current plan specifies "Hindi + one pilot-state language." Given IndicWhisper's stronger performance for Hindi and Marathi, should we target **Maharashtra (Hindi + Marathi)** as the pilot state, or is there a preferred alternative?

> [!IMPORTANT]
> 2. **Telephony Provider:** The reference plan evaluates Exotel, Twilio, and Knowlarity. Exotel and Knowlarity offer stronger India-specific SIP trunking and regulatory compliance (TRAI DLT registration). **Do you have a provider preference or existing contract?**

> [!IMPORTANT]
> 3. **WhatsApp Business API Partner:** Do you plan to use **Twilio** as the WhatsApp BSP (Business Solution Provider), or a domestic alternative like **Gupshup / Kaleyra / Infobip** which may offer better India pricing and vernacular template pre-approval?

> [!IMPORTANT]
> 4. **Hosting & Compliance:** Given Aadhaar data protection mandates (Aadhaar Vault, no raw Aadhaar storage), DPDP Act consent requirements, and the need to run Ollama/Qwen inference privately — is the deployment target **India-region cloud (AWS Mumbai / Azure Central India / GCP Mumbai)** or on-premise?

---

## Proposed Changes

The replan modifies **all three** voice-agent initiative documents and adds new documents. Baseline documents remain unchanged.

---

### Component 1: Business Justification (Revised)

#### [MODIFY] [Business-Justification.md](file:///d:/Barrel/task/ACIX/crop-insurance/documents/initiatives/voice-agent-claim-intimation/current-design/Business-Justification.md)

**Changes:**
- Add a new section **§2.1 Peril-Type Gating** explaining that the service must pre-validate whether the reported calamity type actually requires individual farmer intimation before processing. Widespread yield-loss perils (drought, flood) assessed via government CCEs should be triaged out immediately with a clear farmer-language explanation.
- Expand **§6 MVP Scope** to include:
  - Mandatory geo-tagged photo/video evidence prompting via WhatsApp follow-up after voice intake.
  - AgriStack UFSI integration (if approved) for Farmer Registry and land parcel verification as an alternative to self-managed FIN seeding.
  - IndicWhisper (AI4Bharat fine-tuned Whisper) as the primary ASR engine instead of vanilla Whisper.
- Add a new section **§5.1 Phone-to-Farmer Disambiguation** documenting the multi-FIN resolution flow when one phone number maps to multiple registered farmers.
- Add a new section **§5.2 Seasonal Policy Resolution** documenting the FIN → Land ID → Active Policy (Season/Year) lookup chain.

---

### Component 2: High-Level Design (Revised)

#### [MODIFY] [HLD.md](file:///d:/Barrel/task/ACIX/crop-insurance/documents/initiatives/voice-agent-claim-intimation/current-design/HLD.md)

**Changes:**

**§2 System Context — Revised Architecture Diagram:**
Replace the existing text-based system context with a revised version that includes:
- **AgriStack UFSI** as an external dependency for farmer/land verification (consent-brokered).
- **Evidence Collection Service** as a distinct component between voice intake and Kafka queueing.
- **Peril Validation Gateway** between the Dialogue Orchestrator and the Rule Service.
- **NCIP / Insurer Adapter Tier** explicitly showing the 4-level integration model.

```text
Farmer phone call / WhatsApp
           |
           v
Telephony + WhatsApp gateway (Exotel/Twilio + Gupshup/Twilio)
           |
           v
Voice session service
  IndicWhisper STT <-> Dialogue orchestrator (Qwen 2.5/Ollama) <-> TTS
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

**§3 Primary Call Journey — Revised Flow (12 steps → 16 steps):**

1. Receive call; detect/select language; state purpose and capture consent.
2. Match caller phone to registered farmer contacts.
3. **NEW: If multiple FINs map to the phone, present farmer names and ask caller to identify themselves: *"Is this call for [Name A] or [Name B]?"***
4. Verify identity via OTP or assisted verification.
5. Fetch eligible active land/policy summaries for the verified FIN.
6. **NEW: If multiple active policies exist on the same plot (Kharif vs. Rabi), present season-specific options: *"Are you reporting for your Kharif 2026 soybean policy or your Rabi 2025-26 wheat policy on plot 142/3A?"***
7. If more than one land parcel is plausible, present readable choices (village, crop, area — not opaque IDs).
8. Capture loss event details: peril type, date/time, crop stage, description.
9. **NEW: Peril validation gateway checks `[District] + [Season] + [Peril]` against approved scheme rules:**
   - **If covered under individual intimation:** Proceed to draft creation.
   - **If area-based / CCE-assessed:** Inform farmer immediately: *"Drought losses in your district are assessed through government yield estimates. Individual intimation is not required. We will notify you when assessment results are available."* Log advisory interaction and exit intake.
   - **If ambiguous/unrecognized:** Escalate to human operator.
10. Create/update idempotent claim-intimation draft; prefill trusted fields.
11. **NEW: Prompt farmer for geo-tagged photographic evidence via WhatsApp:** *"We will send you a WhatsApp message now. Please reply with 2-3 clear photos of the crop damage taken at your field."*
12. Read back complete summary: land, policy reference (masked), event, deadline, missing evidence status, intended submission action.
13. On explicit spoken confirmation, publish `claim-intimation.confirmed` event to Kafka.
14. **NEW: Deduplication check** — submission worker checks `FIN + Land ID + Calamity Date + Calamity Type`. If duplicate, merge evidence and return existing transaction number.
15. Submission worker validates, creates insurer-specific packet, submits through approved route (Level 0–3).
16. Notify farmer via WhatsApp/SMS with platform transaction number, official acknowledgement (when available), and next steps.

**§4 Core Services — New additions:**

| Service | Responsibility |
|---|---|
| **Peril validation gateway** | Classifies reported peril as individual-intimation-required vs. area-based; returns scheme rule match or rejection reason in farmer-friendly language |
| **Evidence collection service** | Manages asynchronous WhatsApp photo/video prompts, EXIF metadata extraction, GPS-to-land-parcel boundary matching, 72-hour timestamp compliance check |
| **Identity disambiguation service** | Resolves phone → multiple FINs mapping; presents named choices; manages OTP for sensitive actions |

**§5 FIN and Land Identifier — Revised lookup chain:**

Add the primary key lookup logic:
```
Phone Number → List of registered FINs
  → Farmer selects identity (voice)
    → FIN → Land Parcels (Khasra/Survey No.)
      → Active Policies (filtered by current Season/Year)
        → Selected Land-Policy pair for this intimation
```

**§6 Document Knowledge Pipeline — Unchanged** (existing design is sound).

**§7 Security — Add:**
- Aadhaar Vault compliance: store only Aadhaar reference keys, never raw Aadhaar numbers.
- DPDP Act 2023 consent-brokered data access for any AgriStack integration.
- Call recording consent must be captured *before* recording begins; recording must stop if consent is withdrawn.

**§8 Prototype Deployment — Revised:**
- Replace "Whisper" with "IndicWhisper (AI4Bharat fine-tuned)" as the primary ASR engine.
- Add note on prompt-tuning: *"All STT requests include domain context prompt: 'This is a conversation about crop insurance claim intimation under PMFBY/RWBCIS in India.'"*
- Add IndicNLP normalization layer for Devanagari/Tamil script preservation.

---

### Component 3: Low-Level Design (Revised)

#### [MODIFY] [LLD.md](file:///d:/Barrel/task/ACIX/crop-insurance/documents/initiatives/voice-agent-claim-intimation/current-design/LLD.md)

**Changes:**

**§1 Canonical Data Model — Add/modify entities:**

| Entity | Key fields (new/modified) |
|---|---|
| `farmer_contacts` | Add: `linked_fin_ids` (array) to support one-phone-many-farmers mapping |
| `policies` | Add: `season_year` (e.g., "KHARIF_2026"), `sum_insured`, `premium_paid`, `enrollment_source` |
| `land_policy_links` | Add: `season_year`, `crop_variety`, `sowing_date` for seasonal disambiguation |
| `claim_intimations` | Add: `peril_validation_result` (ENUM: INDIVIDUAL_REQUIRED, AREA_BASED, AMBIGUOUS), `peril_validation_rule_version`, `deduplication_key` (composite hash of FIN+LandID+EventDate+PerilType) |
| `claim_evidence` | Add: `exif_gps_lat`, `exif_gps_lon`, `exif_timestamp`, `gps_land_match_result` (ENUM: MATCH, MISMATCH, UNKNOWN), `evidence_channel` (WHATSAPP, UPLOAD, OPERATOR) |
| **NEW: `peril_triage_log`** | `id`, `session_id`, `fin`, `land_id`, `reported_peril`, `district`, `season`, `rule_version`, `result` (INDIVIDUAL_REQUIRED / AREA_BASED / AMBIGUOUS), `farmer_message_delivered`, `timestamp` |
| **NEW: `agristack_sync_log`** | `id`, `fin`, `sync_type` (FARMER_REGISTRY / LAND_VERIFICATION / CROP_SOWN), `request_hash`, `response_status`, `consent_reference`, `timestamp` |

**§2 Required Constraints and Indexes — Add:**

```sql
-- Deduplication index for claim intimations
create unique index uq_dedup_key on claim_intimations(deduplication_key)
  where status NOT IN ('DUPLICATE_MERGED');

-- Peril triage audit
create index ix_peril_triage_session on peril_triage_log(session_id);
create index ix_peril_triage_result on peril_triage_log(result, timestamp);

-- Evidence GPS matching
create index ix_evidence_gps on claim_evidence(exif_gps_lat, exif_gps_lon)
  where gps_land_match_result IS NOT NULL;
```

**§3 State Machines — Revised:**

```text
Voice session (revised):
STARTED -> CONSENTED -> IDENTITY_DISAMBIGUATED -> IDENTIFIED
  -> SEASON_SELECTED -> LAND_SELECTED -> DETAILS_CAPTURED
  -> PERIL_VALIDATED -> EVIDENCE_PROMPTED -> SUMMARY_READ
  -> CONFIRMED -> COMPLETED
              \-> AREA_BASED_ADVISORY | HUMAN_HANDOFF | ABANDONED

Claim intimation (revised):
DRAFT -> PERIL_TRIAGED -> TRIAGED -> EVIDENCE_PENDING | READY_FOR_CONFIRMATION
READY_FOR_CONFIRMATION -> CONFIRMED -> DEDUP_CHECKED
  -> QUEUED -> SUBMITTED
DEDUP_CHECKED -> DUPLICATE_MERGED (returns existing transaction number)
QUEUED -> SUBMISSION_FAILED -> MANUAL_REVIEW
SUBMITTED -> ACKNOWLEDGED
```

**§4 Voice and Inference Flow — Revised:**
- Step 2: Replace "Whisper" with "IndicWhisper with domain prompt-tuning and IndicNLP normalization."
- Add Step 2.1: "If STT confidence for a critical domain term (peril name, crop name, village name) is below threshold, the system uses the `triage_intimation` tool's fuzzy-match list to present closest options for farmer confirmation."
- Add Step 8: "After confirmation but before Kafka publish, the Evidence Collection Service sends a WhatsApp message with an expiring upload link. The voice agent says: *'We are sending you a WhatsApp message now. Please reply with photos of your damaged crop. Your reference number is [transaction number].'*"

**§5 Agent Tools (MCP-Compatible Contracts) — Add new tools:**

| Tool | Input | Result |
|---|---|---|
| `disambiguate_caller` | call ID, mobile, list of linked FINs | Farmer names for voice presentation |
| `validate_peril` | land ID, event type, district, season | Peril classification result (INDIVIDUAL / AREA_BASED / AMBIGUOUS) + farmer-language explanation |
| `request_evidence` | draft ID, channel (WHATSAPP), farmer mobile | Evidence upload link + WhatsApp message ID |
| `check_deduplication` | FIN, land ID, event date, peril type | Existing transaction number (if duplicate) or null |

**§6 Kafka Topics — Add:**

| Topic | Producer | Consumer | Purpose |
|---|---|---|---|
| `peril-triage.completed` | peril validation gateway | analytics/audit worker | Log peril classification decisions |
| `evidence.upload.received` | WhatsApp webhook handler | evidence validation worker | Process incoming photos, extract EXIF, match GPS to land |
| `evidence.validation.completed` | evidence validation worker | claim draft service | Update draft with evidence status |

**§9 Insurer Adapter Interface — Revised to explicitly include Level 0-3:**

```text
Level 0 - EXPORT_FOR_MANUAL_HANDOFF:
  buildPacket(canonicalIntimation) -> PDF/CSV file
  No automated submission. Operator manually uploads to NCIP portal or emails to insurer.

Level 1 - BATCH_UPLOAD:
  buildPacket(canonicalIntimation) -> Structured CSV/JSON
  submit(packet, destination_email_or_sftp) -> delivery confirmation
  No real-time status. Acknowledgement tracked manually.

Level 2 - PARTNER_API:
  validate(canonicalIntimation) -> validation result
  buildPacket(canonicalIntimation) -> insurer API payload
  submit(packet, idempotencyKey) -> submitted | pending | failed
  pollOrReceiveAcknowledgement(reference) -> acknowledgement/status

Level 3 - WEBHOOK_INTEGRATION:
  All Level 2 capabilities +
  receiveStatusWebhook(event) -> status update persisted + farmer notified
```

**§12 Prototype Build Order — Revised (12 weeks → 14 weeks):**

| Phase | Weeks | Focus |
|---|---|---|
| **Foundation** | 1–2 | Schema migration (add peril triage, dedup, evidence GPS fields), FIN/land seed with AgriStack sandbox (if approved), consent framework, IndicWhisper integration with domain prompt-tuning |
| **Core Voice Loop** | 3–4 | Call simulation, IndicWhisper + Qwen tool loop, identity disambiguation, seasonal policy resolution, land selection with readable prompts |
| **Peril Validation** | 5–6 | Peril validation gateway, scheme rule seeding for pilot district/season/crop combinations, area-based advisory flow, peril triage logging |
| **Evidence & Dedup** | 7–8 | WhatsApp evidence collection flow, EXIF/GPS extraction and land-boundary matching, deduplication engine, Kafka outbox/workers, notification service |
| **Insurer Adapters** | 9–10 | Level 0 (PDF/CSV export) adapter for AIC/PMFBY, proposed Level 1 adapter for SBI General, operator manual-review queue |
| **Security & Testing** | 11–12 | Aadhaar Vault compliance, DPDP consent audit, end-to-end acceptance tests (all 7 existing + 5 new), security penetration testing, failure injection |
| **Pilot Rollout** | 13–14 | Approved live telephony/WhatsApp pilot in 2 districts, measured rollout, integration refinement, KPI measurement |

---

### Component 4: New Document — Evidence Collection Specification

#### [NEW] [Evidence-Collection-Spec.md](file:///d:/Barrel/task/ACIX/crop-insurance/documents/initiatives/voice-agent-claim-intimation/current-design/Evidence-Collection-Spec.md)

**Purpose:** Detail the mandatory geo-tagged photo/video evidence collection workflow that bridges the gap between voice-only intake and PMFBY's visual proof requirements.

**Contents:**
- WhatsApp-triggered evidence prompt flow (post voice call)
- EXIF metadata extraction pipeline (GPS coordinates, timestamp, device info)
- GPS-to-land-parcel boundary matching algorithm (point-in-polygon check against registered plot boundaries)
- 72-hour timestamp compliance validation (EXIF timestamp vs. reported event date)
- Evidence quality checks (image resolution, blur detection, completeness)
- Asynchronous evidence attachment to existing claim draft
- Fallback: operator-assisted photo upload via web dashboard
- Evidence retention and deletion policy per DPDP Act

---

### Component 5: New Document — Peril Validation Logic

#### [NEW] [Peril-Validation-Logic.md](file:///d:/Barrel/task/ACIX/crop-insurance/documents/initiatives/voice-agent-claim-intimation/current-design/Peril-Validation-Logic.md)

**Purpose:** Codify the peril-type gating logic that determines whether a farmer's reported loss requires individual intimation or is assessed via government area-based mechanisms.

**Contents:**
- PMFBY peril classification matrix:

| Peril Category | Individual Intimation Required? | Assessment Model | Platform Action |
|---|---|---|---|
| Hailstorm | **Yes** | Individual farm | Proceed to intake |
| Landslide | **Yes** | Individual farm | Proceed to intake |
| Inundation (localized) | **Yes** | Individual farm | Proceed to intake |
| Cloudburst | **Yes** | Individual farm | Proceed to intake |
| Natural fire (lightning) | **Yes** | Individual farm | Proceed to intake |
| Post-harvest loss (unseasonal rain, cyclone) | **Yes** | Individual farm | Proceed to intake |
| Drought / dry spell | **No** | Area-based (CCE) | Advisory exit |
| Widespread flood | **No** | Area-based (CCE) | Advisory exit |
| Pest/disease epidemic | **No** | Area-based (CCE) | Advisory exit |
| RWBCIS weather-index trigger | **No** | Automated weather | Advisory exit |

- State/district override rules (some states extend individual intimation to additional perils)
- Farmer-language explanation templates for each advisory exit
- Rule versioning and seasonal refresh process
- Audit logging requirements for every triage decision

---

### Component 6: New Document — Integration Tier Strategy

#### [NEW] [Integration-Tier-Strategy.md](file:///d:/Barrel/task/ACIX/crop-insurance/documents/initiatives/voice-agent-claim-intimation/current-design/Integration-Tier-Strategy.md)

**Purpose:** Document the formal multi-tier integration model for NCIP, insurer backends, AgriStack, and banking systems.

**Contents:**
- Level 0–3 integration model (as described in revised HLD §9)
- NCIP integration pathway:
  - Current status: API-based ecosystem exists but requires DA&FW authorization
  - Recommended approach: Apply for NCIP sandbox access; begin with Level 0 (manual) + Level 1 (SFTP/email batch)
  - AgriStack UFSI for identity/land verification (separate from claim submission)
  - API Setu as potential government API gateway
- Insurer-specific adapter strategy:
  - AIC/PMFBY: Level 0 (CSV/PDF) initially, upgrade to Level 2 after formal approval
  - SBI General (proposed): Level 0 initially
  - Future insurers: Adapter interface makes adding new partners a configuration-level change
- AgriStack integration:
  - Farmer Registry API for FIN-to-identity verification
  - Land Verification API for plot-to-coordinates matching
  - Crop Sown Registry for seasonal crop validation
  - Consent-brokered access via DPDP Act framework
- Authorization pathway: Formal letter to DA&FW → Sandbox access → Certification → Production

---

## Verification Plan

### Automated Tests

```bash
# Unit tests for peril validation logic
pytest tests/unit/test_peril_validation.py -v

# Integration tests for identity disambiguation
pytest tests/integration/test_identity_disambiguation.py -v

# Deduplication engine tests
pytest tests/unit/test_deduplication.py -v

# Evidence GPS-to-land matching tests
pytest tests/unit/test_evidence_gps_matching.py -v

# End-to-end voice flow simulation
pytest tests/e2e/test_voice_claim_flow.py -v

# Kafka consumer idempotency tests
pytest tests/integration/test_kafka_idempotency.py -v
```

### Acceptance Tests (Expanded — 7 existing + 5 new)

**Existing (from current LLD):**
1. A registered farmer with three lands selects the intended parcel correctly through voice prompts.
2. The service creates only one draft for repeated turns or reconnects using the same idempotency key.
3. A claim missing evidence remains pending and receives a WhatsApp upload link.
4. A call cannot submit without consent, verification, rule match, summary read-back, and explicit confirmation.
5. A failed insurer submission is retried safely, moved to manual review, and communicated honestly to the farmer.
6. A newly ingested insurance document cannot affect runtime triage until a reviewer approves its extracted rule version.
7. Audit data reconstructs every lookup, selection, confirmation, submission attempt, and notification for a transaction number.

**New:**
8. **Peril gating:** A farmer reporting "drought" in a CCE-assessed district receives an advisory exit explanation and no draft is created.
9. **Phone disambiguation:** A call from a shared phone with 2 registered FINs presents both farmer names and correctly resolves the selected identity.
10. **Seasonal policy resolution:** A farmer with both Kharif and Rabi policies on the same plot is presented with season-specific options and the correct policy is selected.
11. **Evidence GPS validation:** A photo with GPS coordinates outside the registered land parcel boundary is flagged and the farmer is asked to retake the photo at the field.
12. **Deduplication:** Three voice calls from the same farmer for the same event on the same plot within 72 hours produce exactly one transaction number; the second and third calls receive the existing reference.

### Manual Verification
- Deploy to staging with simulated Exotel/Twilio SIP trunk
- Conduct 20 test calls in Hindi and Marathi covering all acceptance test scenarios
- Verify WhatsApp evidence collection flow end-to-end with real device photos
- Validate Level 0 CSV/PDF export output against NCIP manual submission format
- Review audit logs for completeness and PII masking compliance
