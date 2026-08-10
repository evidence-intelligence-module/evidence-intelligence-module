# Voice-Assisted Crop Claim Intimation

## Low-Level Design

**Status:** Prototype implementation design  
**Primary path:** Inbound voice call -> confirmed draft -> Kafka submission workflow -> notification.

## 1. Canonical Data Model

Use UUID primary keys internally and retain business identifiers as unique keys. PostgreSQL stores relational state; JSONB is used only for versioned, source-shaped payloads and unstructured extraction results.

| Entity | Key fields |
|---|---|
| `farmers` | `id`, `fin` (unique), name, preferred language, status |
| `farmer_contacts` | `farmer_id`, type, normalized value, verified status, consent scope |
| `land_parcels` | `id`, `farmer_id`, `land_reference`, state/district/village, plot number, area, source and source reference |
| `policies` | `id`, `farmer_id`, insurer code, scheme, policy/application reference, season, status |
| `land_policy_links` | `land_parcel_id`, `policy_id`, crop, insured area, validity dates |
| `claim_intimations` | `id`, transaction number, FIN, status, source channel, selected land/policy, event facts, deadline, rule version, confirmation time, `peril_validation_result`, `peril_validation_rule_version`, `deduplication_key` |
| `claim_evidence` | `id`, intimation ID, object URI, checksum, type, capture time, metadata, `exif_gps_lat`, `exif_gps_lon`, `exif_timestamp`, `gps_land_match_result`, `evidence_channel` |
| `knowledge_documents` | source URL/upload, issuer, file hash, version, effective dates, ingestion status |
| `rule_versions` | insurer/state/crop applicability, JSON rule, approval status, effective dates |
| `submission_attempts` | intimation ID, adapter, idempotency key, request/response references, status |
| `voice_sessions` | provider call ID, verified FIN, language, consent, current state, transcript URI |
| `audit_events` | actor, action, entity type/ID, timestamp, correlation ID, redacted metadata |
| `peril_triage_log` | `id`, `session_id`, `fin`, `land_id`, `reported_peril`, `district`, `season`, `rule_version`, `result` (INDIVIDUAL_REQUIRED / AREA_BASED / AMBIGUOUS), `farmer_message_delivered`, `timestamp` |
| `agristack_sync_log` | `id`, `fin`, `sync_type` (FARMER_REGISTRY / LAND_VERIFICATION / CROP_SOWN), `request_hash`, `response_status`, `consent_reference`, `timestamp` |

Example transaction number: `CI-20260810-MH-7F3K92`. It is the farmer-facing reference; it is not an insurer acknowledgement number.

## 2. Required Constraints and Indexes

```sql
create unique index uq_farmers_fin on farmers(fin);
create unique index uq_land_reference on land_parcels(land_reference);
create unique index uq_claim_transaction on claim_intimations(transaction_number);
create unique index uq_submission_idempotency on submission_attempts(adapter_code, idempotency_key);
create index ix_contact_mobile on farmer_contacts(contact_value_normalized)
  where contact_type = 'MOBILE';
create index ix_claim_deadline on claim_intimations(status, deadline_at);
create unique index uq_dedup_key on claim_intimations(deduplication_key)
  where status NOT IN ('DUPLICATE_MERGED');
create index ix_peril_triage_session on peril_triage_log(session_id);
create index ix_peril_triage_result on peril_triage_log(result, timestamp);
create index ix_evidence_gps on claim_evidence(exif_gps_lat, exif_gps_lon)
  where gps_land_match_result IS NOT NULL;
```

Duplicate screening should compare FIN, land parcel, policy, claim type, event date, and peril. A potential duplicate must create a review state, never silently overwrite an earlier intimation.

## 3. State Machines

```text
Voice session:
STARTED -> CONSENTED -> IDENTITY_DISAMBIGUATED -> IDENTIFIED
  -> SEASON_SELECTED -> LAND_SELECTED -> DETAILS_CAPTURED
  -> PERIL_VALIDATED -> EVIDENCE_PROMPTED -> SUMMARY_READ
  -> CONFIRMED -> COMPLETED
              \-> AREA_BASED_ADVISORY | HUMAN_HANDOFF | ABANDONED

Claim intimation:
DRAFT -> PERIL_TRIAGED -> TRIAGED -> EVIDENCE_PENDING | READY_FOR_CONFIRMATION
READY_FOR_CONFIRMATION -> CONFIRMED -> DEDUP_CHECKED
  -> QUEUED -> SUBMITTED
DEDUP_CHECKED -> DUPLICATE_MERGED (returns existing transaction number)
QUEUED -> SUBMISSION_FAILED -> MANUAL_REVIEW
SUBMITTED -> ACKNOWLEDGED
```

Only the claim draft service can advance `CONFIRMED`; only the submission worker can advance `QUEUED` or `SUBMITTED`.

## 4. Voice and Inference Flow

1. Telephony provider streams audio chunks to the voice session service.
2. Voice session service sends chunked audio to Whisper and retains transcript segments with time and confidence.
3. The orchestrator passes a compact session summary, not raw history, to Qwen 2.5/Ollama.
4. The model returns either a farmer-facing utterance or a typed tool request. It may not issue SQL, HTTP URLs, or submission commands.
5. Tool gateway validates schema, session state, consent, access scope, and confidence threshold before invoking a domain API.
6. The result is transformed into a PII-minimized conversation fact and the next prompt.
7. TTS speaks the response. A barge-in interrupts TTS and starts a new turn.

For the prototype, require explicit confirmation of the selected land and all facts that affect deadline/routing. If STT confidence is low for a critical fact, ask a closed clarification question or transfer to an operator.

## 5. Agent Tools (MCP-Compatible Contracts)

Expose these through a custom `claim-intimation-mcp` server or an equivalent internal tool gateway. MCP is a contract boundary, not a route to unrestricted database access.

| Tool | Input | Result |
|---|---|---|
| `verify_caller` | call ID, mobile, OTP/verification result | FIN, safe profile summary, consent state |
| `list_eligible_lands` | FIN, current season | friendly parcel choices and policy summaries |
| `select_land` | FIN, land ID, spoken-selection confidence | selected parcel/policy or clarification choices |
| `triage_intimation` | land ID, event type/time, crop stage | applicable approved rule, deadline, required facts |
| `upsert_draft` | session ID, normalized facts, idempotency key | draft ID, missing fields, status |
| `get_confirmation_summary` | draft ID | farmer-readable masked summary |
| `confirm_intimation` | draft ID, consent/confirmation evidence | transaction number, queued status |
| `create_evidence_link` | draft ID, channel | expiring WhatsApp/SMS upload link |
| `handoff_to_operator` | session ID, reason | queue reference and context package |
| `disambiguate_caller` | call ID, mobile, list of linked FINs | farmer names for voice presentation; caller selects identity |
| `validate_peril` | land ID, event type, district, season | peril classification result (INDIVIDUAL_REQUIRED / AREA_BASED / AMBIGUOUS) and farmer-language explanation |
| `request_evidence` | draft ID, channel (WHATSAPP), farmer mobile | evidence upload link and WhatsApp message delivery ID |
| `check_deduplication` | FIN, land ID, event date, peril type | existing transaction number if duplicate, or null |

Separate internal MCP servers may expose document knowledge ingestion and notifications. No tool should be named or capable of `run_sql`, broad file access, or arbitrary message sending.

## 6. Kafka Topics and Workers

| Topic | Producer | Consumer | Purpose |
|---|---|---|---|
| `voice.transcript.created` | voice session | analytics/audit worker | Persist consented transcript metadata |
| `claim-intimation.confirmed` | claim draft service | submission worker | Begin validated handoff |
| `claim-intimation.submission-result` | insurer adapter | status/notification worker | Persist partner result and notify farmer |
| `knowledge-document.received` | ingestion API | extraction worker | Start document parsing |
| `knowledge-rule.candidate-created` | extraction worker | reviewer queue | Human approval workflow |
| `notification.requested` | domain services | provider worker | Send transactional messages |
| `peril-triage.completed` | peril validation gateway | analytics/audit worker | Log peril classification decisions and advisory exits |
| `evidence.upload.received` | WhatsApp webhook handler | evidence validation worker | Process incoming photos, extract EXIF metadata, match GPS to land parcel |
| `evidence.validation.completed` | evidence validation worker | claim draft service | Update draft with evidence validation status and GPS match result |

Use a transactional outbox in PostgreSQL to publish domain events safely. Consumers must be idempotent using event ID and aggregate version. Retry transient failures with exponential backoff; send exhausted failures to a dead-letter topic and operations queue.

## 7. Insurance Document Knowledge Object

```json
{
  "knowledgeDocumentId": "uuid",
  "source": {"type": "PARTNER_UPLOAD", "uri": "object://...", "sha256": "..."},
  "issuer": "SBI_GENERAL",
  "effectivePeriod": {"from": "2026-06-01", "to": null},
  "extraction": {
    "claimTypes": ["LOCALIZED_CALAMITY", "POST_HARVEST_LOSS"],
    "intimationWindowHours": 72,
    "requiredFields": ["event_time", "land_reference", "policy_reference"],
    "requiredEvidence": ["farmer_declaration"]
  },
  "review": {"status": "APPROVED", "reviewerId": "uuid", "approvedAt": "timestamp"},
  "publishedRuleVersion": "sbi-general-mh-kharif-2026.1"
}
```

Ingestion accepts only authorized partner uploads or approved public documents/URLs. OCR and model extraction create a `CANDIDATE` object. An insurance operations reviewer compares it with the source and explicitly publishes the rule version. Runtime services reject unapproved or expired rules.

## 8. APIs

```text
POST /v1/voice-sessions/{sessionId}/consent
POST /v1/caller-verifications
GET  /v1/farmers/by-mobile/{normalizedMobile}/eligible-lands
POST /v1/claim-intimations/triage
POST /v1/claim-intimations/drafts
POST /v1/claim-intimations/{id}/confirm
POST /v1/claim-intimations/{id}/evidence-upload-link
GET  /v1/claim-intimations/{id}
POST /v1/knowledge-documents
POST /v1/knowledge-documents/{id}/approve
```

All write APIs require correlation ID, authenticated service/actor identity, and idempotency key. The confirmation endpoint verifies: consent active, selected land/policy eligible, active approved rule, mandatory facts present, and explicit confirmation record present.

## 9. Insurer Adapter Interface

```text
Level 0 - EXPORT_FOR_MANUAL_HANDOFF:
  buildPacket(canonicalIntimation) -> PDF/CSV file
  No automated submission. Operator manually uploads to NCIP portal or emails to insurer.

Level 1 - BATCH_UPLOAD:
  buildPacket(canonicalIntimation) -> structured CSV/JSON batch file
  submit(packet, destination) -> email/SFTP delivery confirmation
  No real-time status. Acknowledgement tracked manually by operations.

Level 2 - PARTNER_API:
  validate(canonicalIntimation) -> validation result
  buildPacket(canonicalIntimation) -> insurer API payload + attachments
  submit(packet, idempotencyKey) -> submitted | pending | failed
  pollOrReceiveAcknowledgement(reference) -> acknowledgement/status

Level 3 - WEBHOOK_INTEGRATION:
  All Level 2 capabilities +
  receiveStatusWebhook(event) -> status update persisted + farmer notified
```

Implement an AIC/PMFBY adapter and a proposed SBI General adapter only after each partner approves the schema and method. Until then, adapters must operate in `EXPORT_FOR_ASSISTED_SUBMISSION` mode; do not claim a submission succeeded merely because a platform draft exists.

## 10. Notifications

On confirmation, send: platform transaction number, selected parcel summary, event date, what happens next, and evidence-upload link if applicable. On submission, distinguish `platform request accepted`, `official submission pending`, `submitted to partner`, and `official acknowledgement received`. Use Resend for email and an approved WhatsApp/SMS provider for mobile notifications; persist provider message IDs and delivery status.

## 11. Acceptance Tests

1. A registered farmer with three lands selects the intended parcel correctly through voice prompts.
2. The service creates only one draft for repeated turns or reconnects using the same idempotency key.
3. A claim missing evidence remains pending and receives a WhatsApp upload link.
4. A call cannot submit without consent, verification, rule match, summary read-back, and explicit confirmation.
5. A failed insurer submission is retried safely, moved to manual review, and communicated honestly to the farmer.
6. A newly ingested insurance document cannot affect runtime triage until a reviewer approves its extracted rule version.
7. Audit data reconstructs every lookup, selection, confirmation, submission attempt, and notification for a transaction number.
8. A farmer reporting drought in a CCE-assessed district receives an advisory exit explanation in their regional language, no draft is created, and the peril triage decision is logged.
9. A call from a shared phone with two registered FINs presents both farmer names and correctly resolves the selected identity before any policy data is accessed.
10. A farmer with both Kharif and Rabi policies on the same plot is presented with season-specific options and the correct policy is selected for the intimation.
11. A photo uploaded via WhatsApp with GPS coordinates outside the registered land parcel boundary is flagged; the farmer is asked to retake the photo at the field location.
12. Three voice calls from the same farmer for the same event on the same plot within 72 hours produce exactly one transaction number; the second and third calls receive the existing reference and their evidence is merged.

## 12. Prototype Build Order

Week 1-2: Schema migration (peril triage, deduplication, evidence GPS fields), FIN and land seed data, consent framework, IndicWhisper integration with domain prompt-tuning and IndicNLP normalization.  
Week 3-4: Call simulation, IndicWhisper + Qwen tool loop, identity disambiguation for shared phones, seasonal policy resolution, land selection with readable prompts.  
Week 5-6: Peril validation gateway, scheme rule seeding for pilot district/season/crop combinations, area-based advisory exit flow, peril triage logging.  
Week 7-8: WhatsApp evidence collection flow, EXIF and GPS extraction, GPS-to-land-boundary matching, deduplication engine, Kafka outbox and workers, notification service.  
Week 9-10: Level 0 CSV/PDF export adapter for AIC/PMFBY, proposed Level 1 adapter for SBI General, operator manual-review queue, document knowledge review flow.  
Week 11-12: Aadhaar Vault compliance, DPDP consent audit, all 12 acceptance tests, security and failure testing, operator queue integration.  
Week 13-14: Approved live telephony and WhatsApp pilot in two districts, measured rollout, integration refinement, KPI measurement against success targets.
