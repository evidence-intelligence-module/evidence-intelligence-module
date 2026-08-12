# Open Query: what does SAR actually measure for a non-flood peril, and what damage signal does it produce

**Spec/Plan/Tasks**: [../spec.md](../spec.md) User Story 1, FR-001, [../research.md](../research.md) §2, [../tasks.md](../tasks.md) T008/T010 — `src/evidence_intelligence/ingestion/source_registry.py`, `imagery.py`
**Status**: Open — blocks User Story 1 from delivering its stated value. Not blocking T008's catalog work, but blocking any claim that a SAR-sourced package for a hailstorm or cloudburst carries a real damage signal.

## The question

User Story 1's headline scenario is "a hailstorm/flood/cloudburst claim filed during Kharif season, when the field has been under persistent cloud cover", resolved by prioritizing cloud-penetrating SAR. FR-001 requires preferring SAR "when optical sources are unusable due to cloud cover", with no peril restriction.

Neither `spec.md` nor `plan.md` nor `research.md` says **what SAR measures for a peril that is not flooding**, or what damage figure the pipeline derives from it.

## What was checked

**Today SAR is flood-only, by explicit design.** `store/schema.py`'s `PerilType.is_flood_compatible` returns `True` for `FLOOD` and nothing else, and `ingestion/imagery.py` only reaches for SAR when that property holds. So a cloud-covered *hailstorm* or *cloudburst* claim — two of User Story 1's own three named examples — never reaches SAR at all today; it falls through to the weather-only preliminary package. US1 necessarily changes this, and the change is not specified.

**The existing SAR analysis is a flood detector, not a damage model.** `ingestion/gee_client.py`'s `sar_composite` implements Evidence-Flow-Spec.md §4 step 3: Sentinel-1 VV backscatter below −15 dB with a >3 dB drop from the pre-event baseline, vectorized into a flood extent. That threshold pair is a water-surface specular-reflection test. It is not a hail-damage, lodging, or canopy-loss test, and applying it to a hailstorm claim would either detect nothing or detect something that does not mean what the package would say it means.

**The damage number would come from a synthesized input, not from SAR.** When SAR substitutes for post-event optical, `pipeline.py` leaves `post_event` as `None`, and the NDVI-derived features fall back to `0.0` — which makes the apparent NDVI drop equal to the entire pre-event NDVI, i.e. maximum damage. The package would honestly record "Sentinel-1 SAR" in its source attribution while the damage fraction came from a defaulted zero. Routing more perils to SAR without resolving this multiplies that path rather than closing it. (Recorded as a defect and corrected separately; noted here because it is *why* this query matters.)

**Physically defensible SAR signals exist but none is specified.** `models/ai_ml.py`'s `FEATURE_NAMES` already declares `vh_vv_backscatter_deviation` and `rvi` (Radar Vegetation Index), and `Modeling-Approach.md` §6's DSI indicator table already names "SAR VH backscatter deviation (structural/flood damage)". Neither is populated anywhere in the pipeline today. InSAR coherence loss is the conventional signal for lodging and abrupt canopy-structure change, and is not mentioned in any document in this repo.

## Options

| Option | Description |
|---|---|
| A. Keep SAR flood-only; restrict FR-001 accordingly | Narrow User Story 1 to flood-compatible perils and state plainly that cloud-covered hail/drought claims still fall to the weather-only preliminary path. Honest, no new science, but delivers much less than US1 promises. |
| B. Populate the already-declared SAR features (VH/VV ratio, RVI) as a general structural-change signal | Uses feature slots the modeling approach already committed to; makes SAR contribute to Component 2 and the DSI for any peril rather than producing a flood polygon. Requires stating what magnitude of VH/VV or RVI deviation means what, which is itself a sourcing question. |
| C. Add InSAR coherence loss for lodging/structure-change perils | The conventional remote-sensing answer for hail/wind lodging. Materially more processing (coherence requires SLC pairs, not the GRD product currently used) and a new data path, so a larger change than it appears. |
| D. Route SAR by peril, with an explicit per-peril interpretation table | A registry entry per (peril, SAR signal) pair, so "SAR was used" always resolves to a stated interpretation rather than a generic substitution. Composable with B and C. |

## Recommendation

Not resolved unilaterally here. Leaning D as the framing plus B as the first implementation: a per-peril interpretation table makes the source-selection logic honest about what it is claiming, and VH/VV + RVI reuse feature slots this module has already committed to and disclosed. C is the technically strongest answer for hail specifically but is a larger change than User Story 1 currently scopes, and should be costed before being promised.

Option A remains a legitimate outcome. It is better for the module to say "no usable evidence for this cloud-covered hailstorm claim" than to attach a real satellite's name to a damage figure that came from a defaulted zero.

## Resolution

Open. Surfaced during a full-scope re-evaluation of `002` on 2026-08-13.
