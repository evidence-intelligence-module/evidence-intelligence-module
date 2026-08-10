# Voice-Assisted Crop Claim Intimation — Integration Tier Strategy

**Status:** Prototype design  
**Scope:** External system integration model for claim submission, identity verification, and status tracking

## 1. Purpose
The crop insurance ecosystem in India involves multiple institutional actors (NCIP, insurance companies, banks, state governments, AgriStack) with varying levels of digital maturity and API availability. This document defines a pragmatic multi-tier integration strategy that allows the prototype to operate from day one with manual handoffs while providing a clear upgrade path to automated API integrations as institutional approvals are obtained.

## 2. Integration Tier Model

### Level 0 — Manual Export
- **Mechanism:** Generate PDF or CSV claim packets for manual upload to NCIP portal or email to insurer.
- **When to use:** Default starting position for all insurer/portal integrations until formal API access is granted.
- **Workflow:** Submission worker generates packet → Operator downloads from dashboard → Operator manually submits to NCIP/insurer portal → Operator updates platform with acknowledgement number.
- **Advantages:** No institutional approval needed; can start immediately.
- **Limitations:** Slow turnaround; operator bottleneck; no real-time status.

### Level 1 — Batch Upload
- **Mechanism:** Structured CSV/JSON files delivered via email or SFTP on a scheduled basis (e.g., twice daily).
- **When to use:** When the partner accepts structured data but does not offer a real-time API.
- **Workflow:** Submission worker generates batch file → Batch job delivers via SFTP/email at scheduled intervals → Partner processes batch → Platform polls for or receives batch acknowledgement.
- **Advantages:** Reduces manual effort; structured format reduces errors.
- **Limitations:** Not real-time; requires partner agreement on data format and delivery schedule.

### Level 2 — Partner REST API
- **Mechanism:** Real-time API calls to partner systems for claim submission and status polling.
- **When to use:** When formal API access has been granted by the partner (insurer, NCIP).
- **Workflow:** Submission worker calls partner API with idempotency key → Partner returns immediate validation result → Partner returns submission reference → Platform polls for status updates on a schedule.
- **Advantages:** Real-time submission; automated acknowledgement; reduced operational overhead.
- **Limitations:** Requires formal institutional authorization; API stability and uptime dependency.

### Level 3 — Webhook Integration
- **Mechanism:** All Level 2 capabilities plus partner pushes status change events via webhooks.
- **When to use:** When the partner supports event-driven status notifications.
- **Workflow:** All Level 2 flows + Partner fires webhook on status changes (surveyor assigned, assessment complete, approved, rejected) → Platform processes webhook → Farmer notified immediately.
- **Advantages:** Near real-time status updates; proactive farmer notifications; minimal polling overhead.
- **Limitations:** Requires the deepest level of partner integration and trust.

## 3. NCIP Integration Pathway

This section documents the National Crop Insurance Portal integration approach:

### 3.1 Current NCIP Architecture
- The NCIP is the centralized portal managed by Ministry of Agriculture & Farmers' Welfare (MoA&FW).
- It uses API-based integration for real-time data exchange with authorized stakeholders.
- Integration areas include: weather data (IMD), land records, AgriStack registries, PFMS accounting, and MNCFC satellite data.
- All integrations require LGD (Local Government Directory) code mapping.
- Data standards mandate Aadhaar Vault compliance.

### 3.2 Recommended Integration Approach

| Phase | Integration Level | Action Required |
|---|---|---|
| Prototype (Weeks 1-8) | Level 0 | Generate NCIP-compatible claim packets (PDF/CSV). Operator manually uploads. No institutional approval needed. |
| Pilot (Weeks 9-14) | Level 0 + Level 1 | Apply for NCIP sandbox access through DA&FW. Begin SFTP batch delivery if sandbox access is granted. |
| Post-Pilot | Level 2 | Complete NCIP API certification. Implement direct API submission with idempotency. |
| Scale | Level 3 | Negotiate webhook integration for real-time claim status pushback. |

### 3.3 Authorization Pathway
1. Draft formal letter to Department of Agriculture & Farmers Welfare (DA&FW) requesting integration authorization.
2. Apply for NCIP sandbox environment access.
3. Map internal data model to NCIP-mandated LGD codes and data standards.
4. Complete API certification in sandbox.
5. Obtain production API credentials.
6. Implement monitoring, exception handling, and sync-retry mechanisms per NCIP guidelines.

## 4. Insurer-Specific Adapter Strategy

### 4.1 AIC (Agriculture Insurance Company of India)
- **Role:** Primary insurer for PMFBY in many states.
- **Prototype integration:** Level 0 (PDF/CSV export formatted per AIC's claim intimation template).
- **Target integration:** Level 2 (REST API) after formal partnership approval.
- **Data format:** Must include: farmer name, FIN/Aadhaar reference, policy/application number, Khasra/survey number, crop, season, peril type, event date, event description, GPS coordinates, evidence file references.

### 4.2 SBI General (Proposed Pilot)
- **Role:** Private insurer with significant PMFBY market share.
- **Prototype integration:** Level 0 (CSV export in SBI General's prescribed format).
- **Target integration:** Level 1 (SFTP batch upload) during pilot.
- **Note:** SBI General is a proposed target, not an assumed partnership. The actual insurer must confirm in writing before any data exchange.

### 4.3 Future Insurers
- The adapter interface (`validate` → `buildPacket` → `submit` → `pollOrReceiveAcknowledgement`) ensures adding new insurers is a configuration-level change.
- Each new insurer requires: a signed data-sharing agreement, data format mapping, field mapping configuration, integration level selection, and testing in sandbox.

## 5. AgriStack UFSI Integration

### 5.1 Available APIs

| API | Purpose | Data Returned | Use in Platform |
|---|---|---|---|
| Farmer Registry | Verify farmer identity | Farmer ID, name, demographics, linked Aadhaar reference | FIN verification and profile enrichment |
| Land Verification | Validate land parcel ownership | Plot boundaries, area, ownership records | Land parcel resolution during voice flow |
| Crop Sown Registry | Confirm seasonal crop on parcel | Crop type, sowing date, season, land reference | Policy-crop matching and triage validation |

### 5.2 Integration Approach
- **Access:** Via Unified Farmer Service Interface (UFSI) APIs.
- **Authorization:** Requires DA&FW authorization and DPDP Act consent-brokered data access.
- **Consent:** Farmer must explicitly authorize data sharing during voice call consent step.
- **Sandbox:** AgriStack provides a sandbox for testing. Apply through the official AgriStack portal.
- **Fallback:** If AgriStack is unavailable, fall back to the self-managed FIN/land registry seeded during farmer pre-registration.

### 5.3 Data Flow
```text
Voice agent captures farmer consent for AgriStack data access
  → Platform sends consent-brokered request to UFSI
    → Farmer Registry returns verified identity
    → Land Verification returns registered parcels with boundaries
    → Crop Sown Registry returns current season's crop data
  → Platform enriches local PostgreSQL records
  → Voice agent presents verified land/crop options to farmer
```

### 5.4 Sync and Caching
- AgriStack data is cached locally in PostgreSQL with a TTL of 24 hours.
- Fresh lookups are triggered at the start of each voice session.
- All sync operations are logged in `agristack_sync_log`.
- If AgriStack API is unavailable, the voice agent proceeds with locally cached data and informs the farmer: "We are using your previously registered information."

## 6. Banking System Integration

- **Scope:** Not a direct integration target for the prototype.
- **Reason:** Bank/PACS systems feed farmer enrollment data into PMFBY/NCIP. The platform consumes this data indirectly through the policy records seeded during pre-registration or via AgriStack.
- **Future:** If banks offer APIs for enrollment verification, add a Bank Adapter at Level 1 or 2.

## 7. API Setu Gateway

- API Setu (apisetu.gov.in) is the government's standardized API gateway for public data services.
- Some PMFBY-adjacent services may be available through API Setu.
- Evaluate API Setu during the pilot for any available crop insurance or land record APIs.
- API Setu uses standard OAuth 2.0 authentication and provides sandbox testing environments.

## 8. Error Handling and Resilience

| Scenario | Handling |
|---|---|
| NCIP/insurer API timeout | Retry with exponential backoff (3 attempts, max 30s). On exhaustion, fall back to Level 0 export and alert operations. |
| AgriStack API unavailable | Use locally cached data. Log sync failure. Proceed with voice flow. |
| SFTP delivery failure | Retry 3 times. On exhaustion, queue for manual email delivery. |
| Webhook delivery failure | Partner retries with exponential backoff. Platform provides idempotent webhook endpoint. |
| Data format mismatch | Validation service rejects malformed packets before submission. Logs error for operations review. |
| Partner schema change | Adapter versioning allows parallel support for old and new schemas during transition. |

## 9. Monitoring and Observability

| Metric | Purpose |
|---|---|
| Submission success rate by integration level | Track reliability of each tier |
| Mean time from confirmation to acknowledgement | Measure end-to-end submission latency |
| API error rate by partner | Detect partner system issues early |
| AgriStack sync success rate | Monitor identity verification reliability |
| Manual handoff volume | Track operational overhead; drive Level 0 → Level 2 upgrades |
| Retry exhaustion rate | Identify systemic integration failures |

## 10. Compliance and Data Governance

- All data exchanged with external systems must comply with DPDP Act 2023.
- Aadhaar data: only Aadhaar reference keys (from Aadhaar Vault) are included in any external submission.
- Farmer consent: explicit, granular, and revocable. Consent scope includes: "share my identity with [insurer name] for claim processing."
- Data minimization: external submissions include only the fields required by the partner's published schema.
- Audit: every external API call (request, response, status) is logged with correlation ID and timestamp.
- Retention: submission logs retained per insurer/scheme requirement (typically 5 years).
