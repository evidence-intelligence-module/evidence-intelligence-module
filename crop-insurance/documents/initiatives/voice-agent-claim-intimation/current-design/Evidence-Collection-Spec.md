# Voice-Assisted Crop Claim Intimation — Evidence Collection Specification

**Scope:** Asynchronous evidence capture via WhatsApp after voice-based claim intake
**Status:** Prototype design

## 1. Purpose

The Pradhan Mantri Fasal Bima Yojana (PMFBY) mandates geo-tagged, time-stamped visual evidence for individual claim intimations, specifically for localized calamities and post-harvest losses. A purely voice-driven flow cannot fulfill this requirement. This specification defines the asynchronous evidence collection workflow that complements the voice intake, bridging the gap between voice-only intimation and PMFBY's visual proof requirements.

## 2. Evidence Requirements Under PMFBY

| Claim Type | Required Evidence | Geo-tag Required | Timestamp Required | Minimum Items |
| :--- | :--- | :--- | :--- | :--- |
| **Localized calamity** | Photos of damaged crop, GPS coordinates of field | Yes | Yes (capture within 72 hours of event) | 2 photos |
| **Post-harvest loss** | Photos of harvested/standing crop with visible damage, GPS of field | Yes | Yes (capture within notification period) | 2 photos |
| **Additional** | Farmer declaration (captured via voice confirmation), survey/plot identification | N/A | N/A | N/A |

## 3. Evidence Collection Flow

1. The Voice Agent confirms the claim draft and generates a platform transaction number.
2. The Voice Agent informs the farmer: "We are sending you a WhatsApp message now. Please reply with 2-3 clear photos of the crop damage taken at your field. Your reference number is [transaction number]."
3. The system sends a WhatsApp message via the BSP (Gupshup/Twilio) containing:
   - Transaction number
   - Instructions in the farmer's preferred language
   - An expiring upload session (valid for 48 hours)
4. The farmer replies with photos/videos via WhatsApp.
5. The WhatsApp webhook handler receives the media, downloads the original files, and publishes an `evidence.upload.received` Kafka event.
6. The Evidence validation worker processes each file:
   a. Extracts EXIF metadata (GPS lat/lon, timestamp, device info, image dimensions).
   b. Validates GPS coordinates against registered land parcel boundaries (point-in-polygon check).
   c. Validates the EXIF timestamp against the reported event date (must be within 72 hours).
   d. Performs basic quality checks (minimum resolution 640x480, blur detection score).
   e. Stores the original file in an S3-compatible object storage with a checksum.
   f. Updates the `claim_evidence` record with validation results.
7. The Evidence validation worker publishes an `evidence.validation.completed` Kafka event.
8. The Claim draft service updates the intimation status based on validation:
   - All evidence valid → `EVIDENCE_COMPLETE`
   - Some evidence flagged → `EVIDENCE_REVIEW_NEEDED`
   - No evidence received within 48 hours → `EVIDENCE_OVERDUE` (trigger reminder)
9. If evidence is flagged (e.g., GPS mismatch, timestamp outside window, high blur), the system sends a WhatsApp follow-up asking the farmer to retake photos at the field.

## 4. GPS-to-Land-Parcel Matching

- **Algorithm:** Each registered land parcel has a centroid GPS coordinate and approximate area. For the prototype, we use a circular boundary approximation: accept photos within a configurable radius (default 500m) of the parcel centroid. For production, the system will use polygon boundaries from AgriStack geo-referenced village maps if available.
- **Match Result Enum:** 
  - `MATCH`: Within boundary
  - `MISMATCH`: Outside boundary
  - `UNKNOWN`: No GPS in EXIF
- **Action:** A `MISMATCH` triggers a follow-up prompt to the farmer; it does not automatically reject the evidence.

## 5. 72-Hour Timestamp Compliance

- Extract the EXIF `DateTimeOriginal` from the photo.
- Compare it against the event date/time reported by the farmer during voice intake.
- The photo must be captured **after** the reported event time and **within 72 hours** of the event.
- If the timestamp is missing or stripped, mark as `TIMESTAMP_UNKNOWN`; do not reject, but flag the evidence for manual review.

## 6. Evidence Quality Checks

| Check | Threshold | Action on failure |
| :--- | :--- | :--- |
| **Minimum resolution** | 640x480 | Request retake |
| **Blur detection** | Laplacian variance score < 100 | Request retake with tip: "Please hold your phone steady" |
| **File format** | JPEG, PNG, MP4, MOV | Reject unsupported formats with explanation |
| **File size** | Max 20MB per file | Request compressed version or fewer files |
| **Duplicate detection** | Perceptual hash comparison | Merge, do not create duplicate evidence records |

## 7. Fallback Channels

- If the farmer does not have WhatsApp, send an SMS with a web upload link (short URL leading to a mobile-optimized upload page).
- If no smartphone evidence is possible, the voice agent can trigger an operator-assisted evidence collection via the partner dashboard.
- Common Service Center (CSC) / Village Level Entrepreneur (VLE) agents can upload evidence directly via the assisted-channel web dashboard.

## 8. Data Storage and Retention

- Original media files are stored in an S3-compatible object storage with server-side encryption.
- Evidence metadata (GPS, timestamp, quality scores, match results) is stored in the PostgreSQL `claim_evidence` table.
- Object storage paths use structured keys: `evidence/{transaction_number}/{evidence_id}.{ext}`
- Retention period: As per insurer/scheme requirement (typically 5 years for PMFBY claims).
- Deletion: The system will honor farmer consent withdrawal under the DPDP Act, redacting PII but preserving the audit trail.

## 9. Notification Flow

| Trigger | Channel | Message |
| :--- | :--- | :--- |
| **Evidence upload link sent** | WhatsApp | Transaction number + instructions + upload deadline |
| **Evidence received and valid** | WhatsApp | "Your photos have been received and verified. Your claim [transaction number] is being processed." |
| **Evidence flagged (GPS mismatch)** | WhatsApp | "The photo location does not match your registered field. Please take new photos at your field and send them." |
| **Evidence overdue (48 hours)** | WhatsApp + SMS | "Reminder: Please send photos of crop damage for claim [transaction number]. Upload deadline: [date]." |
| **Evidence collection complete** | Internal Kafka | Claim draft service updates status to READY_FOR_SUBMISSION |

## 10. Security and Privacy

- All media is transmitted via WhatsApp BSP using end-to-end TLS.
- Object storage uses signed URLs with a 1-hour expiry for any internal access.
- GPS coordinates in evidence are not exposed to the farmer; they are used strictly for internal validation.
- Evidence files are never stored on the voice/inference server; they are downloaded directly to object storage by the webhook handler.
- A comprehensive audit trail records every evidence upload, validation attempt, and access event.
