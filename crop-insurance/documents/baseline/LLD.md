# Crop Insurance Claim Intimation Platform

## Low-Level Design

Prepared: August 2026  
Document status: Phase 1 implementation design

---

## 1. Scope

This LLD describes the Phase 1 implementation design for the claim intimation platform. It translates the HLD into service responsibilities, APIs, data models, state transitions, workflows, and operational controls.

Phase 1 assumes a hybrid operating environment: some partners may support APIs, while others may require CSV, email, dashboard, or manual handoff.

## 2. Functional Modules

| Module | Primary functions |
|---|---|
| Identity and access | Farmer OTP login, assisted-agent login, partner/admin roles |
| Consent | Capture and audit consent for identity, land, policy, location, and evidence use |
| Farmer profile | Store farmer contact, language, location, and assisted-channel linkage |
| Policy lookup | Capture or import PMFBY application/policy references |
| Claim triage | Determine claim category and whether intimation is required |
| Rules engine | Evaluate state, scheme, crop, season, peril, and timeline rules |
| Deadline engine | Calculate deadline, reminder schedule, and overdue state |
| Evidence manager | Capture/upload photos, GPS, timestamp, documents, and declarations |
| Claim packet | Normalize data for submission/export |
| Routing | Choose destination and delivery mechanism |
| Acknowledgement | Store submission attempt and acknowledgement proof |
| Status tracker | Maintain canonical claim status and partner-specific mappings |
| Notifications | SMS, WhatsApp, IVR, push, and email messages |
| Partner dashboard | Queue review, export, status update, and operational monitoring |

## 3. Claim Type Decision Logic

### 3.1 Input Fields

Minimum triage inputs:

| Field | Required | Notes |
|---|---:|---|
| State/district/village | Yes | From GPS or manual selection |
| Crop | Yes | Must be mapped to notified crop list for pilot |
| Season | Yes | Kharif/Rabi/other as configured |
| Event/peril | Yes | Hailstorm, inundation, cyclone, unseasonal rain, drought, etc. |
| Event date/time | Yes | Used for deadline calculation |
| Crop stage | Yes | Standing, harvested/cut-and-spread, sowing not completed |
| Harvest date | Conditional | Required for post-harvest path |
| Policy/application number | Preferred | Required before final packet submission where available |

### 3.2 Decision Tree

```text
Start
  |
  +-- Is farmer insured / application reference available?
  |     +-- No: create advisory case and collect callback details
  |     +-- Yes: continue
  |
  +-- Is event within configured crop/season window?
  |     +-- No: show likely ineligible/advisory path
  |     +-- Yes: continue
  |
  +-- Is crop harvested and drying in field?
  |     +-- Yes: evaluate post-harvest rule
  |     +-- No: continue
  |
  +-- Is peril localized and isolated?
  |     +-- Yes: localized calamity claim path
  |     +-- No: continue
  |
  +-- Is issue prevented/failed sowing?
  |     +-- Yes: prevented/failed sowing path
  |     +-- No: continue
  |
  +-- Is issue widespread yield loss or weather-index trigger?
        +-- Yes: automatic/area-approach advisory path
        +-- No: manual review path
```

## 4. Domain Model

### 4.1 Core Tables

```sql
farmers(
  id uuid primary key,
  full_name text,
  mobile_number text not null,
  preferred_language text,
  state_code text,
  district_code text,
  created_at timestamptz,
  updated_at timestamptz
)

farmer_consents(
  id uuid primary key,
  farmer_id uuid references farmers(id),
  consent_type text not null,
  consent_version text not null,
  granted boolean not null,
  captured_by_user_id uuid,
  captured_at timestamptz not null
)

farm_plots(
  id uuid primary key,
  farmer_id uuid references farmers(id),
  state_code text not null,
  district_code text not null,
  village_code text,
  survey_number text,
  area_hectares numeric,
  centroid_lat numeric,
  centroid_lng numeric,
  boundary_geojson jsonb,
  created_at timestamptz
)

policies(
  id uuid primary key,
  farmer_id uuid references farmers(id),
  farm_plot_id uuid references farm_plots(id),
  scheme_code text not null,
  insurer_code text,
  application_number text,
  policy_number text,
  season text not null,
  crop_code text not null,
  insured_area_hectares numeric,
  status text,
  source text,
  created_at timestamptz
)

loss_events(
  id uuid primary key,
  farmer_id uuid references farmers(id),
  farm_plot_id uuid references farm_plots(id),
  event_type text not null,
  event_started_at timestamptz,
  event_discovered_at timestamptz,
  crop_stage text not null,
  harvest_date date,
  description text,
  created_by_user_id uuid,
  created_at timestamptz
)

claims(
  id uuid primary key,
  farmer_id uuid references farmers(id),
  policy_id uuid references policies(id),
  loss_event_id uuid references loss_events(id),
  claim_type text not null,
  intimation_required boolean not null,
  deadline_at timestamptz,
  canonical_status text not null,
  rule_version text,
  created_at timestamptz,
  updated_at timestamptz
)
```

### 4.2 Evidence and Submission Tables

```sql
evidence_items(
  id uuid primary key,
  claim_id uuid references claims(id),
  evidence_type text not null,
  object_uri text,
  captured_lat numeric,
  captured_lng numeric,
  captured_at timestamptz,
  device_id text,
  checksum text,
  validation_status text,
  created_at timestamptz
)

claim_packets(
  id uuid primary key,
  claim_id uuid references claims(id),
  packet_version text not null,
  packet_json jsonb not null,
  generated_at timestamptz not null,
  generated_by_user_id uuid
)

submission_attempts(
  id uuid primary key,
  claim_id uuid references claims(id),
  destination_type text not null,
  destination_code text,
  delivery_method text not null,
  idempotency_key text not null unique,
  request_payload_ref text,
  response_payload jsonb,
  status text not null,
  attempted_at timestamptz not null,
  completed_at timestamptz
)

acknowledgements(
  id uuid primary key,
  claim_id uuid references claims(id),
  submission_attempt_id uuid references submission_attempts(id),
  acknowledgement_number text,
  acknowledgement_uri text,
  acknowledged_at timestamptz,
  source_channel text,
  created_at timestamptz
)

claim_status_history(
  id uuid primary key,
  claim_id uuid references claims(id),
  previous_status text,
  new_status text not null,
  partner_status text,
  source text not null,
  note text,
  changed_by_user_id uuid,
  changed_at timestamptz not null
)
```

### 4.3 Rules Tables

```sql
scheme_rules(
  id uuid primary key,
  rule_version text not null,
  scheme_code text not null,
  state_code text,
  district_code text,
  crop_code text,
  season text,
  claim_type text not null,
  peril_codes text[] not null,
  crop_stage text,
  intimation_required boolean not null,
  intimation_window_hours integer,
  effective_from date not null,
  effective_to date,
  priority integer not null,
  rule_json jsonb not null,
  approved_by text,
  approved_at timestamptz
)

evidence_requirements(
  id uuid primary key,
  rule_id uuid references scheme_rules(id),
  evidence_type text not null,
  required boolean not null,
  min_count integer default 1,
  validation_rule_json jsonb
)

routing_rules(
  id uuid primary key,
  rule_version text not null,
  scheme_code text not null,
  state_code text,
  district_code text,
  insurer_code text,
  claim_type text not null,
  destination_type text not null,
  destination_code text,
  delivery_method text not null,
  priority integer not null,
  active boolean not null
)
```

## 5. Canonical Claim Status Model

| Status | Meaning |
|---|---|
| draft | Claim intake started but not ready for submission |
| triaged | Claim type and intimation requirement determined |
| evidence_pending | Required evidence is incomplete |
| ready_to_submit | Packet is complete and destination is known |
| submitted | Submission attempt succeeded or packet was handed off |
| acknowledged | Destination returned acknowledgement or manual acknowledgement recorded |
| assessor_assigned | Partner indicates field assessment assignment |
| assessment_in_progress | Assessment/verification is underway |
| approved | Claim accepted for settlement |
| rejected | Claim rejected by partner/system |
| paid | Payment completed by official/insurer system |
| closed_advisory | No individual intimation required or case closed as advisory |

## 6. API Design

### 6.1 Farmer and Consent

```http
POST /api/v1/auth/otp/request
POST /api/v1/auth/otp/verify
GET  /api/v1/farmers/me
PATCH /api/v1/farmers/me
POST /api/v1/consents
GET  /api/v1/consents/me
```

### 6.2 Triage and Claim Intake

```http
POST /api/v1/claims/triage
POST /api/v1/claims
GET  /api/v1/claims/{claimId}
PATCH /api/v1/claims/{claimId}
POST /api/v1/claims/{claimId}/validate
POST /api/v1/claims/{claimId}/submit
GET  /api/v1/claims/{claimId}/timeline
```

Example triage request:

```json
{
  "stateCode": "MH",
  "districtCode": "PUNE",
  "cropCode": "SOYBEAN",
  "season": "KHARIF",
  "eventType": "HAILSTORM",
  "eventStartedAt": "2026-08-08T09:30:00+05:30",
  "cropStage": "STANDING",
  "schemeCode": "PMFBY"
}
```

Example triage response:

```json
{
  "claimType": "LOCALIZED_CALAMITY",
  "intimationRequired": true,
  "deadlineAt": "2026-08-11T09:30:00+05:30",
  "ruleVersion": "pmfby-pilot-2026.1",
  "requiredEvidence": [
    {"type": "GEO_PHOTO", "minCount": 2},
    {"type": "FARMER_DECLARATION", "minCount": 1},
    {"type": "APPLICATION_NUMBER", "minCount": 1}
  ],
  "routingHint": {
    "destinationType": "INSURER",
    "deliveryMethod": "PARTNER_API_OR_EXPORT"
  }
}
```

### 6.3 Evidence

```http
POST /api/v1/claims/{claimId}/evidence/upload-url
POST /api/v1/claims/{claimId}/evidence
GET  /api/v1/claims/{claimId}/evidence
DELETE /api/v1/evidence/{evidenceId}
```

### 6.4 Partner/Admin

```http
GET  /api/v1/partner/claims
GET  /api/v1/partner/claims/{claimId}
POST /api/v1/partner/claims/{claimId}/status
POST /api/v1/partner/claims/export
POST /api/v1/partner/submission-callback
```

## 7. Offline Sync Design

Client stores offline drafts in encrypted local storage where supported.

Offline draft object:

```json
{
  "localDraftId": "device-uuid-001",
  "createdAt": "2026-08-08T10:00:00+05:30",
  "farmer": {},
  "triageInputs": {},
  "lossEvent": {},
  "evidenceLocalRefs": [],
  "syncStatus": "PENDING",
  "clientGeneratedIdempotencyKey": "claim-sync-device-uuid-001"
}
```

Sync rules:

- Use client-generated idempotency key for claim creation.
- Upload evidence before final submission.
- Preserve original client capture timestamp and GPS metadata.
- Mark conflicts for assisted review if policy/application or farmer identity changes during sync.
- Allow printable/manual packet generation even when final digital submission fails.

## 8. Routing and Submission Flow

```text
Claim ready_to_submit
  |
  v
Load routing rules
  |
  +-- Partner API available?
  |     +-- Yes: submit API request with idempotency key
  |     +-- No: continue
  |
  +-- Batch/export route available?
  |     +-- Yes: enqueue CSV/PDF/email/SFTP packet
  |     +-- No: continue
  |
  +-- Manual dashboard route
        +-- Generate packet and assign to operations queue
```

Failure behavior:

- Retry transient API or messaging errors with exponential backoff.
- Never create a duplicate official submission without idempotency protection.
- Surface failed handoff to operations dashboard before the intimation deadline where possible.
- Send farmer a "received by platform, official submission pending" message if partner submission is delayed.

## 9. Notification Events

| Event | Recipient | Channel |
|---|---|---|
| Draft created | Farmer/agent | App/SMS optional |
| Deadline approaching | Farmer/agent | SMS/WhatsApp/IVR |
| Claim submitted | Farmer | SMS/WhatsApp/app |
| Submission failed | Agent/ops | Dashboard/email |
| Acknowledgement received | Farmer/agent | SMS/WhatsApp/app |
| Status changed | Farmer/agent | SMS/WhatsApp/app |
| Evidence incomplete | Farmer/agent | App/SMS |

## 10. Validation Rules

Minimum validation before submission:

| Validation | Rule |
|---|---|
| Farmer mobile | Must be verified or captured by authenticated assisted agent |
| Location | State and district required; GPS recommended for individual claims |
| Policy/application | Required where partner route needs it; otherwise advisory/manual review |
| Event date | Required for deadline calculation |
| Claim type | Must resolve from rules or enter manual review |
| Evidence | Required evidence count must be met |
| Consent | Required consent must be active |
| Duplicate check | Match farmer + crop + season + plot + event + claim type |

## 11. Role-Based Access

| Role | Permissions |
|---|---|
| Farmer | Create/view own claims, upload evidence, receive status |
| Assisted agent | Create claims for consented farmers, view assigned claims |
| Insurer partner | View/export claims routed to insurer, update statuses |
| District official | View claims in assigned geography, update field workflow status |
| Operations admin | Manage routing queues, correct failed handoffs, view audit |
| Rules admin | Create/edit draft rules |
| Rules approver | Approve and activate rule versions |

## 12. Audit Events

Audit log must record:

- OTP verification and login.
- Consent grant/revoke.
- Claim triage result and rule version.
- Evidence upload/delete.
- Deadline calculation.
- Packet generation.
- Submission attempt and response.
- Manual status update.
- Partner export.
- Admin rule change and approval.

## 13. Observability

Core dashboards:

| Dashboard | Metrics |
|---|---|
| Intimation operations | Claims by status, geography, insurer, deadline risk |
| Submission reliability | Success/failure by destination and delivery method |
| Evidence quality | Missing evidence, invalid GPS, upload failures |
| Farmer support | Repeat inquiries, overdue drafts, language usage |
| Rule performance | Manual-review rate by rule and claim type |
| Pilot KPIs | Within-window rate, completed packet rate, acknowledgement latency |

## 14. Test Strategy

| Test type | Coverage |
|---|---|
| Unit tests | Rule evaluation, deadline calculation, status transitions |
| API tests | Claim creation, evidence upload, submission idempotency |
| Integration tests | Messaging, export, partner API adapters |
| Offline tests | Draft creation, media persistence, sync retry |
| Security tests | Role access, consent enforcement, signed media URLs |
| UAT | Farmer and CSC assisted workflows in pilot languages |

Critical test cases:

1. Localized calamity submitted within 72 hours.
2. Localized calamity overdue but draft captured before deadline and synced after connectivity returns.
3. Post-harvest loss outside 14-day harvest window.
4. Widespread yield loss routed to advisory/no-individual-intimation path.
5. Duplicate claim attempt from same farmer and event.
6. Partner API fails and packet moves to manual queue.

## 15. Phase 1 Delivery Backlog

| Epic | Priority | Notes |
|---|---:|---|
| Farmer/agent authentication | P0 | OTP plus assisted login |
| Consent capture | P0 | Required before personal/location data use |
| Triage and rules engine | P0 | Pilot-state rules only |
| Deadline engine | P0 | 72-hour and configured windows |
| Claim intake forms | P0 | Farmer and assisted-channel flows |
| Evidence upload/offline draft | P0 | Geo-photo and declaration |
| Claim packet generation | P0 | JSON plus PDF/CSV export |
| Routing queue | P0 | API/export/manual modes |
| Acknowledgement ledger | P0 | Farmer-visible proof |
| Notifications | P1 | Deadline, submitted, acknowledged, status |
| Partner dashboard | P1 | Queue and status update |
| Analytics dashboard | P1 | Pilot KPIs |
| Advanced status integrations | P2 | Depends on partner readiness |

## 16. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Availability | 99.5% for API during pilot, excluding planned maintenance |
| Evidence upload | Support retry and resumable upload where possible |
| Data retention | Configurable by partner/scheme; default retention policy required before launch |
| Latency | Triage response under 2 seconds for cached rules |
| Scalability | Support district-level pilot with path to state-level expansion |
| Accessibility | Low-literacy flow, regional language support, assisted mode |
| Security | Encryption, RBAC, audit logs, secure media access |

## 17. Implementation Risks

| Risk | Engineering response |
|---|---|
| Rules become hard to maintain | Use versioned rules tables and approval workflow |
| Partner APIs unavailable | Keep export/manual delivery first-class |
| Offline media upload unreliable | Separate draft sync from evidence upload and show clear retry state |
| Duplicate submissions | Enforce idempotency and duplicate detection before routing |
| Status data sparse | Use canonical status with source labels and manual updates |
| Evidence tampering concerns | Store checksum, capture metadata, audit trail, and upload timestamp |

## 18. References

- High-level design: [HLD.md](HLD.md)
- Business white paper: [Business-White-Paper.md](Business-White-Paper.md)
- Baseline roadmap: [Roadmap-Region_India.md](Roadmap-Region_India.md)
