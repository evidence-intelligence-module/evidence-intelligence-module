# Pipeline Decomposition Design

**Date**: 2026-08-13
**Status**: Approved design, not yet implemented
**Implements**: `T0R-01` … `T0R-08` in [`tasks.md`](./tasks.md)
**Scope**: `src/evidence_intelligence/` structural refactor plus one behavioural correction to Component 5 (DSI)

---

## 1. Why

`pipeline.py` is 761 lines, of which `run_pipeline` is roughly 370 and
`_deliver_weather_only_preliminary` a near-duplicate 60. Four defects have been
found in it, all of the same shape — an input that was never measured being read
as a measured value:

| Defect | What was absent | What it silently became |
|---|---|---|
| `T0-02` | post-event NDVI | `0.0` → a maximum-damage reading, in the claimant's favour |
| `T0-03` | LSWI (no source wired) | the NDVI drop — a different physical quantity |
| `T0-04` | 11 of 17 declared features | `0.0` → every estimate diluted toward zero |
| DSI weight collapse (this document) | 5 of 6 historical archives | weight `0.0` → a single-indicator score presented as a six-indicator composite |

The first three were fixed individually, at the call site, by adding a
conditional and a comment. The fourth was found on 2026-08-13 and is not yet
tracked anywhere. It will not be the last: the discipline that prevents this
class of defect is currently a convention repeated at six call sites, enforced
by nothing.

This design makes that discipline a property of a type rather than a habit, and
decomposes the orchestration around it so that each stage can be understood and
tested on its own.

**Non-goals.** No change to the Evidence Request Interface, the store schema,
the `ModelComponent` enum, per-component `methodology_version` strings, the
modelling science in `semi_physical.py`/`ai_ml.py`/`dsi.py`, or any of the
boundaries in `documents/constitution.md`. This is a restructuring plus one
disclosure fix, not a modelling change.

## 2. Constraints

1. **Per-component `methodology_version` stays per-component.**
   `"semi-physical-v1"`, `"ai-ml-rf-v1"`, `"dsi-entropy-v1"` and their siblings
   are written into the §65B package individually. Collapsing them into one
   version string would mean retraining Component 2 invalidates the version
   recorded against a physics model that did not change, which breaks the
   re-derivability argument the package rests on (Constitution §2.1/§2.2).
2. **`ModelComponent` and the store schema do not change.** Five distinct row
   types are what make a package independently re-derivable.
3. **No new invented figures.** Every threshold, weight, and cut point in scope
   keeps its current sourced-or-disclosed status; this design introduces none.
4. **No type checker available.** `pyproject.toml` runs `ruff` with `E`/`F`/`I`/`UP`
   only. Enforcement must be structural — API shape and tests — not annotations.

## 3. Architecture

Six stages. Arrows are data; no stage calls another.

```
request
   │
   ▼
[1] ingestion/            (exists, unchanged)   → ImageryBundle, WeatherBundle
   │
   ▼
[2] observation.py        NEW                   → FieldObservations
   │                                               the single place raw bundles
   │                                               become named signals
   ├──────────────┬───────────────┬──────────────┐
   ▼              ▼               ▼              ▼
[3] models/    [4] models/    [5] causation/   (all read FieldObservations;
    registry       dsi.py         scoring.py     none reads a raw bundle)
    (C1/C2/C3)     (C5)
   │              │               │
   ▼              │               │
   ensemble (C4)  │               │
   └──────────────┴───────────────┘
   │
   ▼
[6] packaging/assembly.py NEW                   → PackageContent (both tiers)
   │
   ▼
pipeline.py = orchestrator only: thread the stages, perform every store write
```

### 3.1 Module ownership

| Module | Owns | Absorbed from `pipeline.py` |
|---|---|---|
| `observation.py` (new) | Raw bundles → named, present-or-absent signals | `_ndvi_to_fapar`, `_insolation_proxy_mj`, `_cross_pol_ratio_deviation`, `ndvi_drop`, `fapar_deviation`, `weather_anomaly_normalized`, `optical_pair_available`, `FALLBACK_TEMPERATURE_C` |
| `models/registry.py` (new) | `DamageEstimator` protocol, `Trainable` protocol, the three adapters, registry construction | the three hand-wired component call sites, `_load_ai_ml_model`, `_assumed_harvest_index` |
| `packaging/assembly.py` (new) | `PackageContent` for **both** tiers | `_build_manifest`, `_coverage_statement`, `_modeling_assumption_statements`, `_classify`, notes/accuracy assembly, all of `_deliver_weather_only_preliminary` |
| `pipeline.py` | Threading and persistence only | — (761 → ~120 lines) |

### 3.2 Two boundary rules

1. **Nothing downstream of `[2]` may import `ingestion`.** Estimators, DSI, and
   causation see `FieldObservations` and nothing else. This is what makes "was
   this measured?" one question with one answer, rather than six call sites each
   re-deriving it from `imagery.post_event is None`.
2. **Only `pipeline.py` may import `EvidenceStore`.** Every other module is pure.

Both are enforced by an import-graph test (§6.2), not by convention.

## 4. `FieldObservations`

### 4.1 The unifying observation

An absent *signal* and an empty *historical archive* are the same failure at
different axes — one at a point in time, one across time. Treating them as one
concept, under one rule, is what makes the DSI correction fall out of the design
rather than being bolted on as a special case.

### 4.2 The type

```python
@dataclass(frozen=True)
class Observation:
    value: float
    source: str                      # provenance, e.g. "COPERNICUS/S2_SR_HARMONIZED"

@dataclass(frozen=True)
class Absent:
    reason: str                      # "no usable post-event composite", "no source wired"

@dataclass(frozen=True)
class FieldObservations:
    signals:   Mapping[str, Observation | Absent]
    histories: Mapping[str, Sequence[float] | Absent]
    phenology_flag: str | None

    def value(self, name: str) -> float | None:                  # None when Absent/unknown
    def history(self, name: str) -> Sequence[float] | None:
    def present(self, names: Iterable[str]) -> dict[str, float]: # measured only
```

**There is deliberately no `get(name, default)` and no `__getitem__`.** The sole
scalar accessor returns `float | None`. A caller wanting a fallback must write it
visibly, where a reviewer will see it. With no type checker available, this API
shape *is* the enforcement mechanism.

### 4.3 Absence carries a reason

```python
obs.record("ndvi_deviation", ndvi_drop, source=..., absent_reason="no post-event optical pair")
```

Recording *why* an input is missing is what lets boundary rule 1 hold. Today
`_build_manifest` ([`pipeline.py:79-159`](../../src/evidence_intelligence/pipeline.py))
re-derives provenance by re-inspecting the raw bundles — 80 lines of parallel
bookkeeping maintained by hand, computed from a different source than the models
consume. Nothing forces the two to agree; a signal could be dropped while the
manifest still reported `USED`.

After this change the manifest is a **projection** of `FieldObservations` plus
the registry's per-model outcomes. The manifest and the models cannot disagree,
because the manifest is derived from what the models were given.

## 5. Models

### 5.1 The protocol pair

```python
@dataclass(frozen=True)
class Estimate:
    damage_fraction: float
    weight: float                    # this component's own confidence
    confidence_or_accuracy: dict     # persisted verbatim; shape unchanged

@dataclass(frozen=True)
class NotRun:
    reason: str                      # same vocabulary as Absent; feeds the manifest

class DamageEstimator(Protocol):
    component: ModelComponent        # store enum — unchanged
    methodology_version: str         # per-component — unchanged
    def estimate(self, obs: FieldObservations) -> Estimate | NotRun: ...

@runtime_checkable
class Trainable(Protocol):           # satisfied by AiMlEstimator alone
    def fit(self, features, labels) -> None: ...
    def evaluate(self, features, labels) -> dict: ...
    def save(self, path) -> None: ...
    @classmethod
    def load(cls, path): ...
```

Trainability becomes a declared capability rather than a special case in the
orchestration. Nothing in the pipeline asks which estimator is the machine-learnt
one; `Trainable` is referenced only by `scripts/train_ai_ml_model.py`. This is
the structural expression of the fact that Component 1 is physics, Component 3 is
calibration, and only Component 2 is fitted.

The existing model modules keep their science untouched — `SemiPhysicalEstimator`,
`AiMlEstimator`, and `CsmEstimator` are thin adapters that read
`FieldObservations` and call the current functions. Model code does not churn;
only its wiring does.

### 5.2 Registry

`csm_high_scrutiny_enabled` gating moves into registry construction, so the
execution loop carries no conditionals:

```python
results = [(e, e.estimate(obs)) for e in registry]
```

Component 3 remains disabled by default. This design does not change that, and
does not implement Component 3 — see the reframed open query on CSM
high-scrutiny trigger criteria in [`issue/`](./issue/README.md).

### 5.3 Weight computation moves to the estimators

`ensemble.semi_physical_weight` and `ensemble.ai_ml_weight` move onto the
respective estimators. The `UNTRAINED_PLACEHOLDER_WEIGHT = 0.15` cap is a
statement about Component 2's own confidence, not about blending policy. With it
relocated, `ensemble.combine` becomes purely mechanical and holds no
component-specific knowledge. The numeric behaviour is unchanged.

## 6. The DSI correction

### 6.1 What is actually wrong

The defect is an **internal inconsistency**, not a missing rule.
[`dsi.py`](../../src/evidence_intelligence/models/dsi.py) handles a missing
historical archive two different ways:

- `_min_max_normalize` returns the `0.5` midpoint — FR-023's "no fabricated
  baseline" behaviour, and correct.
- `_entropy_weights` computes `total = 0` → `entropy = 1.0` → **diversity `0.0`**,
  i.e. weight zero.

Weight zero nullifies the midpoint. The module computes a deliberate neutral
value and then silently discards it. Neither behaviour is wrong alone; holding
both is.

In the shipped pipeline, [`pipeline.py:472-479`](../../src/evidence_intelligence/pipeline.py)
passes `[]` for five of the six historical arrays. All five therefore receive
weight zero, normalisation puts the entire weight on `ndvi_deviation`, and **the
DSI score equals the normalised NDVI deviation**. `weather_anomaly_magnitude` —
the one indicator the pipeline reliably populates — is among those zeroed.

No package says so. `report_generator.py` prints only
`Damage Severity Index: {score}`, so a reader sees a composite-sounding figure
with no indication that five of six inputs contributed nothing.

### 6.2 The fix

Make the two halves consistent in the honest direction. Exclusion is preferred
over neutrality because a contributed `0.5` is itself a fabricated data point —
it asserts "this indicator reports average" — which is what FR-023 exists to
prevent.

```python
@dataclass
class DsiResult:
    score: float | None                       # None when nothing can contribute
    entropy_weights: dict[str, float]         # over contributing indicators only
    normalized_indicators: dict[str, float]   # ALL indicators; midpoint preserved
    contributing: list[str]
    excluded: dict[str, str]                  # name -> reason
```

**FR-023 is untouched.** `normalized_indicators` still reports the `0.5` midpoint
for every indicator, for transparency. What changes is that indicators with no
archive are excluded from the *weighted sum* explicitly and named as excluded in
the package.

### 6.3 Behavioural delta

- **Existing DSI unit tests pass unchanged.** All three in
  [`test_dsi.py`](../../src/tests/unit/test_dsi.py) assert on
  `normalized_indicators`; none asserts on weights under an empty archive.
- **The score is numerically identical in today's pipeline**, since weight
  already collapsed to `ndvi_deviation = 1.0`; excluding the other five and
  renormalising over `{ndvi_deviation}` also yields `1.0`.
- **One edge case changes**: when *no* indicator has an archive, the score
  becomes `None` rather than a confident-looking `0.5`.
- **Every package gains disclosure** of which indicators contributed and which
  were excluded, with reasons.

The disclosure is the substance of this fix. The number was never going to be
wrong — it was going to be a single-indicator measurement presented as a
six-indicator composite.

### 6.4 A second DSI defect, pinned but not fixed here

Found while recording the `T0R-01` fixtures, and recorded so it is not mistaken
for something this design resolves.

`pipeline.py` populates the `ndvi_deviation` historical archive with
`historical_ndvi` — a list of **absolute NDVI index values** — while the current
indicator for that name is a **deviation**. These are different physical
quantities, which is precisely the `T0-03` mismatch appearing in a second place.

The `varied_historical_archive` fixture pins the consequence: a 0.45 NDVI drop
normalized against a 0.62–0.81 index range falls below the floor and clips, so
the package reports a **Damage Severity Index of 0.0 for a field that lost 0.45
NDVI**. It went unseen because every pre-existing test archive held five
identical values, making `hi == lo` and returning the `0.5` midpoint regardless.

Fixing it requires a source of historical *deviations* — each prior season's drop
measured against its own baseline — which is data work adjacent to `T05-03` and
`T05-05`, not a restructuring. It is deliberately out of scope here; where it
lands should be decided before Phase 0.4 closes.

## 7. Persistence and packaging

### 7.1 Orchestrator

```python
def run_pipeline(request_id, geometry, event_date, peril_type, store, settings, **clients):
    store.set_status(request_id, RequestStatus.IN_PROGRESS)

    imagery = ingest_imagery(...)                            # I/O
    weather = ingest_weather(...)                            # I/O
    obs     = observe(imagery, weather, peril_type)          # pure

    if imagery.usable:
        estimates = [(e, e.estimate(obs)) for e in registry] # pure
        record = assemble_complete(obs, estimates, ...)      # pure
    else:
        record = assemble_preliminary(obs, ...)              # pure

    _persist(store, storage, record)                         # every write, one place
    store.set_status(request_id, record.terminal_status)
```

`PipelineRecord` carries the satellite row, weather row, component rows,
`PackageContent`, tier, and terminal status. `_persist` is the only function in
the codebase that calls `store.add_*`.

**Deliberate change**: writes batch at the end rather than landing incrementally.
A mid-run crash now leaves no rows, where today it leaves an orphaned
satellite/weather row with no package attached. `run_pipeline_background` marks
the request `FAILED` either way, so nothing observable regresses — and for a
§65B record, "no run" is a cleaner artifact than "a run that describes inputs but
produced no evidence". Recorded here because it is a real change, not a refactor
side effect.

`store.set_status(IN_PROGRESS)` stays at the top; status transitions are not part
of the batch.

### 7.2 Packaging unification

One builder, tier as a parameter, replacing the duplicated
`_deliver_weather_only_preliminary` path. What the preliminary tier gains:

| Element | Preliminary today | After |
|---|---|---|
| Evidence-inputs manifest | missing | **added** |
| Coverage statement | missing | **added** ("no usable optical composite") |
| Modeling assumptions (Harvest Index, damage bands) | missing | **stays out** |

The last row is deliberate. Unification must not mean every package carries every
statement: a Harvest Index disclosure on a package containing no yield-loss
figure is noise, and noise trains readers to skip disclosures. The manifest and
coverage statement are added because a preliminary package is precisely the one
where a reader most needs to know what was attempted and what failed.

## 8. Testing

### 8.1 Characterization fixtures

Recorded **before** any change: full JSON package snapshots per scenario, stored
under `src/tests/fixtures/golden/`. Each is labelled either:

- `pinned` — must not change; any diff is a regression.
- `known-wrong` — expected to change, naming the migration step that changes it
  and why.

These capture current behaviour *including* its known-wrong parts. They are a
change-detector, not a correctness oracle. The DSI fix will deliberately flip
one, which is the point.

Expected `known-wrong` flips: preliminary packages gaining a manifest and
coverage statement (§7.2); DSI returning `None` where no indicator has an archive
(§6.3).

### 8.2 New structural tests

1. **Import-graph test** — no module under `models/`, `causation/`, or
   `packaging/` imports `ingestion` or `store`. Enforces §3.2 mechanically.
2. **Absence-propagation test**, parametrized over every consumer — construct
   `FieldObservations` with signal *X* `Absent`, assert the consumer's output is
   `None` or excluded, never a number. This is the test that would have caught
   all four defects in §1, and the one the current suite structurally cannot
   express.
3. **Manifest-agreement test** — every signal a model consumed appears `USED` in
   the manifest; every `Absent` appears with its recorded reason.

### 8.3 Existing suite

All 117 existing tests (80 unit, 25 integration, 12 contract, verified
2026-08-13) pass at every step, except where a fixture is explicitly labelled
`known-wrong`.

## 9. Migration

Characterization-first strangler. Each step is independently revertible and has a
verification gate.

| Step | Task | Change | Gate |
|---|---|---|---|
| 0 | `T0R-01` | Golden fixtures + `pinned`/`known-wrong` labels | 46 pass; snapshots recorded |
| 1 | `T0R-02` | `observation.py` + `FieldObservations`; pipeline builds and reads it | all `pinned` byte-identical |
| 2 | `T0R-03` | Import-graph + absence-propagation tests | initially fail for consumers still reading bundles — that failure is step 3's specification |
| 3 | `T0R-04` | `models/registry.py` + three adapters; loop replaces three call sites | `pinned` identical |
| 4 | `T0R-05` | DSI exclude/renormalise/disclose | 3 DSI unit tests pass unchanged; one `known-wrong` flips |
| 5 | `T0R-06` | `packaging/assembly.py`; delete `_deliver_weather_only_preliminary` | preliminary `known-wrong` flip; complete stay `pinned` |
| 6 | `T0R-07` | `PipelineRecord` + `_persist`; stages go pure | `pinned` identical; write order asserted |
| 7 | `T0R-08` | Delete dead helpers from `pipeline.py` | ruff clean; 761 → ~120 lines |

Step 4 is independent of step 3 and could land earlier; sequencing it after keeps
each fixture flip attributable to exactly one step.

## 10. Sequencing against queued Phase 0 work

This refactor should land **before** two already-queued tasks, because it makes
both smaller:

- **`T0-08`** (one satellite row per source; today only the post-event source
  persists) modifies exactly the write path that `_persist` centralises. Landing
  it first means the write logic is built twice.
- **`T05-02`** (compute `crop_condition_variability`, a `modeling-approach.md` §6
  DSI indicator that "has never been computed") becomes a single `obs.record(...)`
  call afterwards — landing into a DSI that will correctly report it as
  contributing rather than silently zero-weighting it.

**`T0-06`** (causation's hardcoded temporal and spatial terms) is independent and
can proceed in parallel.

## 10a. Corrections to this design, from the 2026-08-13 cross-check

A systematic re-reading of this design against `001`/`002`'s `spec.md`,
`plan.md`, `data-model.md` and `contracts/` found four places where it is wrong
or underspecified. They are corrections to the design above, not new scope.

1. **Boundary rule 2 overstates the guarantee.** §3.2 says "only `pipeline.py`
   may import `EvidenceStore`". That is already false and legitimately so:
   `api/routes.py` imports it for `Depends(get_store)`, which is `001`'s
   completed `T022`/`T023`. (`002`'s `T018` and `TV-01` would have added more;
   both were struck on 2026-08-13 per `constitution.md` §9, so the API layer's
   set of store consumers is unchanged.) The
   rule is about the **six pipeline stages**, not the whole codebase — which is
   what `T0R-03`'s import-graph test actually enforces (`models/`, `causation/`,
   `packaging/`). Read §3.2 as scoped to those; the API layer is an explicit
   exception.

2. **`PipelineRecord` carries the wrong cardinality.** §7.1 says "the satellite
   row", singular, matching today's single `add_satellite_result` call. `T0-08`
   requires **one row per source considered** — up to seven per request
   (pre-event, post-event, five historical composites). The field must be
   `satellite_rows: list[...]`. §10's claim that landing `T0R-07` first makes
   `T0-08` "smaller" holds only once this is fixed; as written the two designs
   contradict.

3. **`FieldObservations` is scalar-only and US3 needs vectors.** `value()`
   returns `float | None` by deliberate design (§4.2). `002`'s `T022`/`T023` add
   Presto foundation-model embeddings, which are vector-valued, as an additive
   Component 2 feature source. Nothing here says how a vector feature is
   represented. This is unresolved rather than merely unaddressed, and it
   surfaces when `T023` is implemented — decide before then whether embeddings
   live in a parallel `vectors:` mapping or outside `FieldObservations` entirely.

4. **Nine `002` tasks target code this design supersedes.** `T012`, `T017`,
   `T025`, `T029`, `T036`, `T043` all say "surface `<field>` … in
   `packaging/report_generator.py`", which `T0R-06` replaces as the assembly
   point — implementing them literally recreates the two-divergent-paths problem
   `T0R-06` exists to close. `T024`, `T028`, `T035` write to `pipeline.py`
   directly, bypassing `T0R-07`'s `_persist`. All nine need re-scoping; tracked
   as `T0R-09`.

## 11. Open items this design does not resolve

None of the following are blockers for the work above; they are recorded so the
refactor is not mistaken for resolving them.

- The AI/ML training-label question remains open; this design changes how
  Component 2 is wired, not what it is trained on.
- Component 3 remains an unimplemented placeholder, disabled by default.
- The Harvest Index constant and damage classification bands remain disclosed
  assumptions (`T0-17`/`T0-18`), unchanged here.
- `map_uris` remains unpopulated — GIS map export is unbuilt roadmap work, out of
  scope for this refactor.
