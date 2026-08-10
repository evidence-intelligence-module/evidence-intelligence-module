# Voice-Assisted Crop Claim Intimation — Peril Validation Logic

## Document metadata
- **Title:** Voice-Assisted Crop Claim Intimation — Peril Validation Logic
- **Status:** Prototype design
- **Scope:** Peril classification and eligibility pre-validation for claim intake

## 1. Purpose
The Pradhan Mantri Fasal Bima Yojana (PMFBY) distinguishes between perils requiring individual farmer intimation and perils assessed through government area-based mechanisms (such as Crop Cutting Experiments (CCE), weather stations, and satellite data). The voice agent must accurately classify the reported peril before creating a claim draft. This prevents invalid intimations from entering the processing pipeline and helps set correct expectations for the farmer right at the beginning of the call.

## 2. PMFBY Peril Classification Matrix

| Peril | Category | Individual Intimation Required | Assessment Model | 72-Hour Window | Platform Action |
|---|---|---|---|---|---|
| Hailstorm | Localized calamity | Yes | Individual farm assessment | Yes | Proceed to intake |
| Landslide | Localized calamity | Yes | Individual farm assessment | Yes | Proceed to intake |
| Inundation (localized) | Localized calamity | Yes | Individual farm assessment | Yes | Proceed to intake |
| Cloudburst | Localized calamity | Yes | Individual farm assessment | Yes | Proceed to intake |
| Natural fire (lightning) | Localized calamity | Yes | Individual farm assessment | Yes | Proceed to intake |
| Post-harvest unseasonal rain | Post-harvest loss | Yes | Individual farm assessment | Yes (from harvest) | Proceed to intake |
| Post-harvest cyclone | Post-harvest loss | Yes | Individual farm assessment | Yes (from harvest) | Proceed to intake |
| Drought / dry spell | Widespread yield loss | No | Area-based CCE | N/A | Advisory exit |
| Flood (widespread) | Widespread yield loss | No | Area-based CCE | N/A | Advisory exit |
| Pest / disease epidemic | Widespread yield loss | No | Area-based CCE | N/A | Advisory exit |
| Mid-season adversity | Mid-season adversity | No (government notified) | Area-based notification | N/A | Advisory exit |
| Prevented / failed sowing | Prevented sowing | Scheme/state dependent | Area-level validation | State-specific | Conditional intake |
| RWBCIS weather-index trigger | Weather-based | No | Automated weather station | N/A | Advisory exit |

## 3. State and District Override Rules
While the PMFBY standard matrix applies nationally, state notifications can override these rules:
- Some states extend individual intimation requirements to additional perils beyond the PMFBY standard list.
- State notifications change seasonally (Kharif vs. Rabi) and can vary by district.
- The rule service must support district-level and season-level overrides. 
- *Example:* A state may require individual intimation for localized pest outbreaks in specific districts during a particular season.
- Override rules are stored in the `rule_versions` table with `insurer/state/crop applicability` and `effective dates`.
- All overrides must go through the human-in-the-loop document knowledge approval process before becoming active in the system.

## 4. Validation Algorithm

The system executes the following step-by-step algorithm to evaluate incoming claims:

```text
INPUT: reported_peril, district_code, season, crop_code, event_date

1. Normalize reported_peril using fuzzy matching against the canonical peril vocabulary.
   - If confidence < 0.7, ask the farmer a clarification question with options.
   - Canonical vocabulary includes farmer-language synonyms (e.g., "olaa" → hailstorm in Hindi/Marathi).

2. Query rule_versions for active approved rules matching:
   WHERE district = district_code
   AND season = season
   AND peril = normalized_peril
   AND effective_from <= event_date
   AND (effective_to IS NULL OR effective_to >= event_date)
   AND approval_status = 'APPROVED'

3. If rule found:
   a. If rule.intimation_required = TRUE:
      - Return INDIVIDUAL_REQUIRED
      - Include deadline_hours, required_fields, required_evidence from rule
   b. If rule.intimation_required = FALSE:
      - Return AREA_BASED
      - Include farmer_explanation_template from rule

4. If no rule found:
   a. Fall back to PMFBY national default classification (§2 matrix)
   b. If still ambiguous (e.g., prevented sowing varies by state):
      - Return AMBIGUOUS
      - Trigger human operator escalation

5. Log the triage decision to peril_triage_log with all inputs and outputs.
```

## 5. Farmer-Language Explanation Templates

The following table provides example templates for each advisory exit scenario. These messages are delivered when a peril is classified as area-based and does not require individual intimation.

| Peril Classification | Hindi Template | English Template |
|---|---|---|
| Area-based (drought) | "आपके जिले में सूखे का नुकसान सरकारी फसल कटाई प्रयोगों के माध्यम से आंका जाता है। व्यक्तिगत सूचना की आवश्यकता नहीं है। हम आपको मूल्यांकन परिणाम उपलब्ध होने पर सूचित करेंगे।" | "Drought losses in your district are assessed through government crop cutting experiments. Individual intimation is not required. We will notify you when assessment results are available." |
| Area-based (flood) | "आपके जिले में बाढ़ का नुकसान क्षेत्र-स्तरीय मूल्यांकन के तहत आता है। व्यक्तिगत दावा सूचना की आवश्यकता नहीं है।" | "Flood damage in your district falls under area-level assessment. Individual claim intimation is not required." |
| Area-based (pest) | "कीट/रोग का प्रकोप क्षेत्र-स्तरीय मूल्यांकन के अंतर्गत आता है। सरकार द्वारा मूल्यांकन किया जाएगा।" | "Pest or disease outbreaks are assessed at the area level. The government will conduct the assessment." |
| RWBCIS trigger | "आपकी फसल मौसम-आधारित बीमा योजना के अंतर्गत है। मुआवजा मौसम स्टेशन के आंकड़ों से स्वचालित रूप से तय किया जाता है।" | "Your crop is covered under a weather-based insurance scheme. Compensation is automatically determined from weather station data." |
| Ambiguous | "हम आपकी स्थिति को सही तरीके से समझने के लिए आपको एक विशेषज्ञ से जोड़ रहे हैं।" | "We are connecting you with a specialist to understand your situation correctly." |

## 6. Fuzzy Peril Vocabulary

To map farmer descriptions to canonical PMFBY perils, the system employs a fuzzy matching approach. 

| Farmer term (Hindi/Marathi) | Canonical peril | Confidence |
|---|---|---|
| ओला / ओले पड़ना / गारा | Hailstorm | 0.95 |
| बाढ़ / पानी भर जाना (localized) | Inundation | 0.85 |
| बाढ़ / नदी में बाढ़ (widespread) | Flood (widespread) | 0.80 |
| सूखा / पानी नहीं मिला | Drought | 0.95 |
| भूस्खलन / जमीन खिसकना | Landslide | 0.90 |
| बादल फटना | Cloudburst | 0.95 |
| बिजली से आग | Natural fire (lightning) | 0.90 |
| कीड़ा लगना / इल्ली | Pest/disease | 0.85 |
| बेमौसम बारिश (post-harvest) | Post-harvest unseasonal rain | 0.85 |
| तूफान / चक्रवात | Post-harvest cyclone | 0.80 |

*Note: The confidence thresholds provided above are starting points for the prototype and must be refined based on pilot call analysis.*

## 7. Rule Versioning and Seasonal Refresh

Rules require continuous updating to reflect changing policies and guidelines:
- Rules are versioned using the format: `{insurer}-{state}-{season}-{year}.{version}` (e.g., `aic-mh-kharif-2026.1`).
- Each season transition (Kharif → Rabi, Rabi → Kharif) triggers a rule refresh process:
  1. Insurance operations uploads the new state notification PDFs.
  2. Document knowledge pipeline extracts peril classification rules.
  3. LLM-assisted extraction creates rule candidates.
  4. Human reviewer validates candidates against source documents.
  5. Approved rules are published with new version numbers and effective dates.
  6. Previous season rules are marked expired but retained for audit.
- Runtime services reject unapproved or expired rules.
- Emergency mid-season rule additions (e.g., a state extends coverage to a new peril) follow the same approval pipeline with expedited review.

## 8. Audit and Compliance

To comply with the DPDP Act and PMFBY audit requirements:
- Every peril triage decision is logged to `peril_triage_log` with:
  - Session ID, FIN, land ID, reported peril (original farmer words)
  - Normalized peril, district, season
  - Rule version used for classification
  - Classification result (INDIVIDUAL_REQUIRED / AREA_BASED / AMBIGUOUS)
  - Whether farmer advisory message was delivered
  - Timestamp
- Logs are immutable and retained for a minimum of 5 years.
- Monthly analytics: classify peril triage outcomes by district, season, and result to detect rule gaps.
- Anomaly detection: flag unusual patterns (e.g., a high volume of AMBIGUOUS results for a specific peril in a district may indicate a missing rule).
