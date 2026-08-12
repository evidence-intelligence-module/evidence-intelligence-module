# Open Query: what personal data may enter the module via opaque attachment metadata, and what governs its retention

**Spec/Plan/Tasks**: [../spec.md](../spec.md) FR-006, [../data-model.md](../data-model.md) `supplementary_evidence_attachments`, [../contracts/evidence-request-api-extensions.md](../contracts/evidence-request-api-extensions.md), [../tasks.md](../tasks.md) T018/T019 — `src/evidence_intelligence/api/routes.py`
**Status**: Open — should be settled before T018 ships, since the endpoint's shape determines what data the module durably holds.

## The question

FR-006 adds `POST /evidence-requests/{request_id}/supplementary-evidence`, taking an `attachment_type`, a `uri`, and `caller_supplied_metadata` — the last defined in `data-model.md` as "opaque JSON, never validated or interpreted against any specific channel's schema", explicitly mirroring `external_reference_id`'s opacity in `001`.

Opacity is the right call for *coupling*. The open question is what it implies for *personal data*:

1. What is this module's posture when a caller places farmer identifiers, phone numbers, or Aadhaar-adjacent references in an unvalidated JSON blob it stores for ten years?
2. Does the module dereference the submitted `uri`, and if so, what may it point at?

## What was checked

**Constitution §5 keeps caller schemas out; it does not keep personal data out.** §5 says the module "does not assume, depend on, or reference any specific claim-intimation channel's internal data model", and `contracts/`'s implementers' notes state that no field "accepts or returns a caller's internal claim ID, farmer ID, or policy schema". That holds for the *typed* fields. `caller_supplied_metadata` is by construction the one field where a caller can put anything at all, and callers routinely do put identifiers in free-form metadata slots. The boundary is stated but not enforced anywhere in the design.

**The retention rule was written for evidence, not for personal data.** Constitution §7 and `store/evidence_store.py`'s `RETENTION_YEARS = 10` set a ten-year floor, correctly, because evidence supporting a disputed claim must outlive the dispute. A geotagged photograph plus whatever a caller attached to it is personal data about an identifiable individual, and India's Digital Personal Data Protection Act, 2023 attaches purpose-limitation and erasure obligations to it. No document in this repo reconciles a ten-year evidentiary retention floor with those obligations, and `documents/` contains no data-protection section at all. This is a genuine gap, not a settled position.

**The attachment is a reference, not an upload — which raises its own question.** `contracts/` specifies that the endpoint "does not accept raw file uploads" and takes a `uri` "reference to the already-stored evidence object". Nothing states whether the module ever fetches that URI, nor constrains its scheme or host. If anything downstream dereferences it — package assembly, a map render, a future re-evaluation path — an unconstrained caller-supplied URI is a server-side request forgery vector and a route to reading objects the caller should not be able to reach through this service. If nothing ever dereferences it, that is worth stating explicitly, because it is the property the design is relying on.

**`geometry` is already the module's real personal-data surface, and predates this.** A field boundary plus an event date plus a peril type identifies a specific farm. That is inherent to the module's purpose and not a defect — but it means the module is already processing personal data under DPDP terms, and adding photographs and opaque metadata changes the scale, not the fact.

## Options

| Option | Description |
|---|---|
| A. Constrain the surface, keep the opacity | Allowlist URI schemes/hosts (or accept only references into the module's own object store), size-cap `caller_supplied_metadata`, and state in the contract that metadata is stored verbatim, never parsed, never dereferenced, never used in any figure. Preserves Constitution §5's decoupling while bounding what can arrive. |
| B. Add a data-protection section to `documents/` | Reconcile Constitution §7's ten-year evidentiary retention with DPDP purpose-limitation and erasure — e.g. distinguishing evidence artifacts (retained) from caller-supplied personal data (erasable on request), and stating which is which. Larger, and it is a `documents/` change, not a `002` change. |
| C. Drop `caller_supplied_metadata` | The field has no consumer: nothing in `data-model.md`, `contracts/`, or any model reads it. Removing it eliminates the ingress entirely at zero functional cost. `external_reference_id` already covers the legitimate correlation need. |
| D. Accept as-is | Defensible only if paired with an explicit, recorded decision that the module treats everything a caller sends as the caller's responsibility under their own DPDP obligations. That is a real position, but it should be written down rather than inferred from the field's opacity. |

## Recommendation

Not resolved unilaterally here — this is a governance decision under Constitution §8, not a design detail.

Leaning C + A: `caller_supplied_metadata` currently has no reader anywhere in the design, so the cheapest way to resolve a personal-data ingress is to not open it; and whatever happens to that field, the `uri` should be constrained and the "never dereferenced" property stated rather than assumed. B is worth doing on its own timeline — the module is already processing personal data via `geometry` today, and `documents/` is silent on it.

## Resolution

Open. Surfaced during a full-scope re-evaluation of `002` on 2026-08-13.
