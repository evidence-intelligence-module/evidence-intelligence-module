# Scope Boundaries — Design

**Date:** 2026-08-13
**Status:** Approved in discussion; not yet implemented.
**Produces:** a new `constitution.md` §9, five prunes across `specs/002-satellite-evidence-parity/` and both `issue/` trackers, and seven sync edits.

**This file is the rationale record, not the boundary source of truth.** Once §9 lands, `constitution.md` is authoritative and this document explains why §9 says what it says — the same relationship `notes/decision-log.md` has to the rest of the tree. Do not restate §9's content here as it evolves.

---

## 1. The decision, in one line

> **The module owns the transformation, not the supply chain at either end.**

Labeled data arrives; an evidence package leaves. Who produces the one and who consumes the other are outside this module.

This generalises two positions the initiative already held — Constitution §5 (no privileged caller, generic contract) and the 2026-08-13 decision that training-data sourcing is not this repo's concern — into a single rule from which the rest of the boundary set is derived rather than enumerated ad hoc.

## 2. Firmness: all boundaries are permanent

Every boundary in §9 is permanent. Crossing one requires a Constitution §8 amendment: an explicit, recorded decision with rationale, made before implementation.

Considered and rejected: a two-tier scheme mirroring the Constitution's own split between §4 (CCE — permanent in tone) and §3 ("out of scope, for now"). The argument for two tiers was that some entries — other insurance lines, other geographies — are honestly "not yet" rather than "never". The decision was one tier anyway, on the grounds that §8 is not an onerous door: it asks for a written decision and a reason, which is what anyone should produce before adding fraud scoring or a second country regardless. A uniform rule is also harder to erode than a graduated one.

**Consequence to accept knowingly:** supporting RWBCIS in another state is inside scope, but supporting another *country's* scheme now requires an amendment. That is the intended cost.

## 3. The cross-cutting rule: data minimisation

**The module accepts exactly `geometry`, `event_date`, `peril_type`, and an opaque `external_reference_id`, and never widens that surface.**

This replaces an earlier draft of the rule that read "no personal data, ever, in any request field, column, or package". That wording was wrong, and the correction is worth recording because it is easy to make again:

`specs/002-satellite-evidence-parity/issue/open query - personal data in caller-supplied attachment metadata (FR-006).md` establishes that a field boundary plus an event date plus a peril type identifies a specific farm. The module therefore processes personal data **today**, inherently, as a condition of doing its job — before any photograph or metadata blob is attached. A boundary asserting the absence of personal data would have been false on the module's own primary input.

Data minimisation says the true and useful thing instead: the surface is exactly as wide as the purpose requires, and it never grows. Personal-data *processing* is acknowledged; personal-data *accumulation* is barred.

**What this closes:** the attachment-metadata half of the personal-data query, decisively — the surface cannot widen, so the question of what may arrive through a widened surface does not arise.

**What this does not close:** reconciling Constitution §7's ten-year evidentiary retention floor with the DPDP Act 2023's purpose-limitation and erasure obligations, for `geometry` itself. That is Option B in the same query, it is a `documents/` change, and it survives this design untouched. See §11 below.

## 4. The boundary registry

28 rows in four groups. Three are pointers to boundaries that already exist (§3, §4, §5) and must never restate them; 25 are new.

### A. Upstream — how inputs are produced

| Boundary | What it means |
|---|---|
| Training-label sourcing, curation, annotation | A supplier delivers a CSV matching `FEATURE_NAMES` plus `damage_fraction`. Origin is recorded as *declared*, never verified. No annotation tooling, no labeling pipeline |
| Ground-truth survey operations | Field visits, agronomist networks, plot sampling |
| Commercial satellite procurement | Vendor contracts, tasking budgets, licence negotiation |
| Hosting or mirroring source archives | §7 already references sources rather than copying them. Stated as a boundary: this is not a tile server or an imagery archive |
| Owning master reference data | Crop calendars, crop-type maps, agro-climatic zone definitions — consumed as published products, never authored |
| Field boundary derivation and land records | Geometry arrives with the request; cadastral and land-title systems are separate |
| Sensor operations | Ingesting an image someone else captured is in scope; flying drones or deploying ground sensors is not |

### B. Downstream — what happens to the package

| Boundary | What it means |
|---|---|
| The consuming service | → §5, unchanged |
| Claim adjudication and settlement | The module evidences; it never decides. §4's logic generalised past CCE |
| Indemnity and payout computation | Sum insured, threshold yield, premium, deductible |
| Delivery and notification | The package sits at a URI and is fetched. An optional readiness callback announces that a package exists; that is not delivery |
| Farmer- or surveyor-facing UI | No app, no review screen, no override workflow |
| Dashboards, BI, portfolio analytics | Precedent: `decision-log.md` Round 6 rejected exactly this as SaaS-shaped |
| Dispute filing, certification, representation | The module produces §65B-admissible *content*. A §65B certificate is signed by a legal person; software does not issue one |
| Human override of an issued figure | Packages are append-only. Disagreement is recorded downstream, never as an edit to an issued package |

### C. Lateral — adjacent uses of the same data

| Boundary | What it means |
|---|---|
| Predictive / early-warning alerting | → §3, unchanged |
| CCE ingestion, validation, blending | → §4, unchanged |
| Fraud detection, claimant risk scoring | Constitution §1 is explicit: this closes the evidence gap, **not** the fraud gap. The module may report that data *contradicts* a claim — §3 already provides for corroborating or contradicting what was reported — but it must never score a claimant |
| Underwriting, risk rating, premium pricing | The same archive used in the opposite direction; makes the module an actuarial tool |
| Parametric / index-insurance trigger computation | Computing a payout trigger **is** acting as a determination authority, which §4 exists to prevent |
| Agronomic advisory | Irrigation, pesticide, or harvest-timing recommendations |
| Yield forecasting for markets or procurement | Commodity-desk use of the same pipeline |
| Continuous monitoring without a claimed event | §3 in new clothing, and it breaks §2.3's requirement that every package tie to a specific event |
| Other insurance lines and other geographies | PMFBY/RWBCIS, India. Not livestock, property, or health lines; not other countries |

### D. Platform — what this repository is not, as software

| Boundary | What it means |
|---|---|
| ML platform services | Feature store, experiment tracker, model registry, serving mesh. This repo ships a training script, a `.joblib` artifact, and a feature contract |
| SaaS product surface | Tenancy, billing, metering, subscriptions (Round 6 precedent) |
| Deployment and infrastructure | Terraform, Kubernetes, CI/CD, secrets management, autoscaling |
| Authentication and identity | A gateway concern. The service assumes an authenticated caller and issues no identities |

## 5. Carve-outs

Two rules above would cut real, wanted work if read literally. Both carve-outs belong in §9 itself, not only here.

1. **"No monitoring without a claimed event" governs issuing evidence, not internal testing.** `TV-03`'s negative-control harness deliberately runs the pipeline over fields with no claimed event to measure the false-positive rate. That is validation, produces no package, and survives.
2. **"No owning master reference data" permits consuming it.** `002`'s WorldCereal crop cross-check is unaffected. What is barred is becoming the authority for a crop map, not reading someone else's.

## 6. Where the boundaries are recorded

`constitution.md` gains **§9 Scope Boundaries**: the principle from §1 of this document, the data-minimisation rule, the four grouped tables, and the two carve-outs.

**The rows for §3, §4 and §5 point at those sections and never restate their content.** This is the load-bearing constraint on §9's form. `decision-log.md` Round 4 records this repo fixing exactly that failure once already — Constitution §6 and the module README both restated the full YES-TECH adopted/not-adopted list, and the fix was to make one a pointer. §9 is a registry, not a second copy.

Approaches considered:

- **Rejected — fold each boundary into the existing section whose logic it extends.** Fraud scoring under §1, adjudication under §4, delivery and auth under §5. Each rule would sit beside its rationale with no registry to drift, but the boundary set could no longer be read in one place, which is the primary requirement. It also means editing three stable governance sections rather than adding one.
- **Rejected — a separate `documents/scope-boundaries.md` with §9 delegating to it.** Keeps the Constitution short and lets the list grow without touching governance. Fails on the firmness decision: if every boundary is permanent and §8 governs amendments to *this document*, the firmest rules would live furthest from the process that protects them.

## 7. Prune list

Five groups. No `src/` code is deleted — none of the pruned items were ever implemented.

**Corrections found during execution** (recorded rather than silently absorbed, since this file is the plan of record):

- **`FR-024` was missed.** The claim-outcome *requirement* existed in `002/spec.md` alongside `TV-01`; striking the task without it would have left the spec demanding an interface no task built. Struck.
- **Two Key Entities were missed** — "Supplementary Evidence Attachment" and "Claim Outcome". Struck with their requirements.
- **`T014` was missed** — the contract test for the supplementary-evidence endpoint. Struck with `T018`/`T019`.
- **Struck requirements keep their identifiers.** `FR-006`, `FR-014`, `FR-019` and `FR-024` are marked removed in place rather than deleted, because `tasks.md`, `plan.md`, `quickstart.md` and the checklists cite them by number and renumbering would break every reference.
- **Final count: 42 touch points**, not the 35 estimated below.

### 7.1 Commercial satellite procurement (16)

| File | Change |
|---|---|
| `002/tasks.md` | Strike `T037`. Drop `commercial_tasking_client.py` from `T002`, `COMMERCIAL_TASKING_ENABLED` from `T003`, "commercial-tasking gating" from `T040`, and the commercial-tasking dependency note in the Dependencies section |
| `002/spec.md` | `FR-019` rewritten from "not authorized for this rollout" to out-of-scope per §9. `FR-013` is **narrowed, not struck**: recording whether a *commercial* source was considered loses its subject, but recording which free enhanced sources (Bhoonidhi LISS-4/EOS-04) were considered and not used is real provenance and stays. `FR-002` narrows to free/sovereign enhanced sources. The paid-imagery Edge Case and the Satellite Source Registry entity description both drop the commercial tier |
| `002/data-model.md` | `access_model` enum collapses to `FREE`. `considered_not_used` survives, but only for free enhanced sources. Validation-rule prose updated |
| `002/contracts/evidence-request-api-extensions.md` | `sources_considered_not_used` semantics: the note that it is always empty while commercial tasking is disabled becomes permanent rather than configuration-dependent |
| `002/research.md` | §5 becomes a historical record of a decision now superseded by §9; the PlanetScope correction note stays as history |
| `002/plan.md` | Project-structure entry for `commercial_tasking_client.py`; the `issue/` directory description |
| `002/quickstart.md` | Prerequisites note and the enhanced-source-unavailable scenario |
| `002/checklists/requirements.md` | Two references to the tasking-budget ambiguity |
| `002/issue/` | Tasking-budget query moves from *Resolved* to *Superseded by §9*; `README.md` row updated |

### 7.2 Field boundary assistance (4)

Strike `T038` and `FR-014`. Drop `field_boundary_assist.py` from `T002` and from `plan.md`'s project structure. The SAM2 remote-sensing domain-gap finding stays in `documents/research/satellite-parity-global-precedent-research.md` as research — it is no longer something this repo builds.

### 7.3 Training-label sourcing (7)

Strike `TV-01`, `TV-01a`, `TV-02`, `TV-05`. Retitle `002` Phase 0.6 from "Label Capture & Label-Free Validation" to **"Label-Free Validation"**, covering only `TV-03` and `TV-04`. Close `001`'s AI/ML-training-data query and `002`'s parity-validation query as scope decisions. Remove the "`TV-01` must land before Pilot & Validation" warning from `GUIDE.md` — the deadline dies with the task.

`TV-05` (ablation harness) goes because its stated justification is explicitly label scarcity: it is described in `tasks.md` as the available version of User Story 3's independent test *while the label question is open*. With labeled data arriving from a supplier, the direct measurement replaces it.

**One addition, not a removal:** `label_provenance` becomes a mandatory field in the artifact `AiMlModel.save()` writes, surfaced through `confidence_or_accuracy` into every package's accuracy statement. With sourcing out of scope, a declared provenance string is the only thing this repo can honestly record about where its training data came from — and without it, no package can say anything at all about whether Component 2 was trained on CCE-derived outcomes.

### 7.4 Authentication (1)

Nothing to delete. `GUIDE.md` gains an explicit statement that the service assumes gateway-terminated authentication on a trusted network, and issues no identities. Today's silence would otherwise read as "safe to expose".

### 7.5 Supplementary evidence attachments (7)

`FR-006` is removed. A geotagged photograph is personal data about an identifiable individual, arriving from outside, into a store with a ten-year retention floor — the clearest possible case of the request surface widening.

Strike `FR-006`, `T018`, `T019`. Remove the `supplementary_evidence_attachments` table from `data-model.md` and the endpoint from `contracts/`. The personal-data query closes on its attachment half. The supplementary-evidence re-evaluation query closes on its live half — whether attaching evidence re-evaluates anything.

## 8. Sync edits

| File | Change |
|---|---|
| `documents/constitution.md` | New §9. §1's "Out of scope now" sentence repointed from "Sections 3, 4, 5" to §9 |
| `CLAUDE.md` | Keeps its three hard boundaries verbatim — they shape day-to-day agent behaviour — and gains one pointer line to §9 for the full set |
| `.specify/memory/constitution.md` | The same §9 distillation; `CLAUDE.md` documents this file as kept in sync, not independent |
| `documents/notes/decision-log.md` | Round 17: why these boundaries were drawn now, and what was struck |
| `GUIDE.md` | The authentication statement; Open Issues rewritten as queries close; the `TV-01` deadline removed |
| `documents/hld.md` §5 | One clause making the optional callback explicitly a readiness notification rather than delivery, so it does not contradict the delivery boundary |
| `documents/technical-flow-diagrams.md` | §15's gap table cites `TV-01`; that row goes |

## 9. Verification

- Grep until zero live references remain for: `T037`, `T038`, `T018`, `T019`, `TV-01`, `TV-02`, `TV-05`, `commercial_tasking_client`, `field_boundary_assist`, `COMMERCIAL_TASKING_ENABLED`, `supplementary_evidence_attachments`, `access_model`
- **The FR identifiers must be grepped scoped to `specs/002-satellite-evidence-parity/` only.** The two features number their requirements independently and all three collide: `001`'s `FR-006` is SAR substitution for flood-compatible perils — load-bearing, implemented, and cited in `ingestion/imagery.py` — while `002`'s `FR-006` is the attachment endpoint being removed. `FR-014` and `FR-019` collide the same way. An unscoped grep-and-strike here would delete shipped behaviour
- Closed `issue/` files get a status change and a §9 pointer — **not** deletion or renaming. `spec.md`, `plan.md`, `tasks.md`, and the checklists link them by path, and the `open query - ` filename prefix is a naming convention rather than a status
- Prior `decision-log.md` entries stay exactly as written, including their references to now-struck task IDs. Only Round 17 is added. Precedent: Rounds 12, 15 and 16 all preserved historical entries describing repo states that no longer exist
- `src/` is untouched apart from `label_provenance`. The suite should still be 117 passing, plus one new test for the provenance field
- Re-validate `documents/technical-flow-diagrams.md`'s Mermaid blocks after editing §15

## 10. What must survive the prune

These are adjacent enough to get swept up by a careless pass:

- **`T0-16`** (package lineage) — split *out* of the FR-006 query as a standalone defect fix. Unrelated to attachments; survives
- **`TV-03`** (negative controls) and **`TV-04`** (reproducibility) — need no labels, and `TV-04` verifies a Constitution Principle I claim that nothing currently checks
- **Bhoonidhi / ISRO sovereign sources** — free, so enhanced-tier sourcing survives in full. Only paid procurement goes
- **WorldCereal crop cross-check** — consuming published reference data is explicitly permitted by carve-out 2
- **All of `001`** — untouched by this design

## 11. What this design does not resolve

- **DPDP versus the ten-year retention floor**, for `geometry` itself. Option B of the personal-data query. It is a `documents/` change, it needs a data-protection section that does not exist yet, and data minimisation narrows it without answering it
- **The remaining open queries** in both trackers — causation threshold, confidence tiers, harvest index, classification bands, RUE part-of-season, and the rest — are unaffected. Two of them (causation threshold, confidence tiers) wanted claim-outcome data that `TV-01` was going to capture. With `TV-01` struck, either the external data contract includes outcomes or both thresholds stay permanently unset. The repo's "unset rather than invented" discipline makes that survivable: packages ship without a low-confidence label rather than with a fabricated one
- **What a training-data supplier must deliver**, beyond the existing CSV shape. Out of scope to *source*, but the handoff contract itself is in scope and is not specified here

## 12. Consequences worth naming

- **Auth being out of scope is now a stated posture rather than an omission**, which raises rather than lowers the obligation to say so loudly in `GUIDE.md`
- **`label_provenance` is the entire provenance story for training data.** With sourcing external, that one declared string is all a §65B reader will ever see about where Component 2's calibration came from
- **A §65B certificate is signed by a person, not emitted by software.** Worth stating in §9 because the module's output is deliberately §65B-shaped, and the gap between "admissible content" and "certified record" is a legal act this repo cannot perform
