# Evidence Intelligence Module — Technical Flow & Architecture Diagrams

**What this is:** the *as-built* technical behaviour of the running service in [`src/`](../src/), drawn as
Mermaid diagrams. Control flow, data flow, decision gates, model wiring, epistemic state
(measured / substituted / absent), persistence, and configuration — not a file or module tree.

**How it relates to the other documents.** [`hld.md`](hld.md) is the source of truth for the
*intended* architecture and [`evidence-flow-spec.md`](evidence-flow-spec.md) for the *intended*
pipeline; both are hand-authored and change rarely. This document is derived from the code and
therefore describes what actually executes today, including the places where the implementation is
thinner than the design (§15 indexes them). Where the two disagree, the design documents state the
target and this one states the current state — neither overrides the other.

Every diagram is annotated with the file and line the behaviour comes from. Re-derive it by reading
those; there is no generator.

---

## 1. Runtime topology

What exists at run time, in one process, and what it talks to.

```mermaid
flowchart LR
    subgraph Caller["Any requester (generic contract, no privileged caller)"]
        C["HTTP client"]
    end

    subgraph Proc["Service process (uvicorn + FastAPI)"]
        MW["RequestLoggingMiddleware<br/>trace_id, structured JSON logs<br/>catch-all 500 + X-Trace-Id"]
        RT["routes.py<br/>POST /evidence-requests -> 202<br/>GET /evidence-requests/:id"]
        BT["Starlette BackgroundTasks<br/>run_pipeline_background"]
        PL["pipeline.run_pipeline<br/>orchestration"]
        OB["observation.observe<br/>signal layer"]
        MD["models/<br/>C1 C2 C3 C4 C5"]
        CA["causation.scoring"]
        PK["packaging.report_generator"]
        CFG["config.Settings<br/>read once at import"]
        CACHE["_ai_ml_model_cache<br/>per-process, keyed by path"]
    end

    subgraph Ext["External dependencies"]
        GEE["Google Earth Engine<br/>Sentinel-2 SR Harmonized<br/>Landsat 8/9 C2 L2<br/>Sentinel-1 GRD<br/>CHIRPS, ERA5-Land, GPM IMERG, SMAP"]
        IMD["IMD AWS station API<br/>httpx, 10s timeout, optional"]
        DB[("PostgreSQL + PostGIS<br/>5 tables, GeoAlchemy2")]
        OS[("Object storage<br/>LocalObjectStorage today<br/>S3-compatible interface")]
        JL["Trained model artifact<br/>joblib .joblib file"]
    end

    C --> MW --> RT
    RT -->|"create_request, RECEIVED"| DB
    RT -->|"schedules after response"| BT
    BT --> PL
    PL --> OB --> MD --> CA --> PK
    PL <-->|"getInfo, server-side compute"| GEE
    PL <-->|"station_record"| IMD
    PL -->|"status + every intermediate row"| DB
    PK -->|"put package.json, report.pdf"| OS
    CFG -.->|"gates"| PL
    CACHE -.->|"loads once"| JL
    JL -.-> MD
    C -->|"poll"| RT
    RT -->|"latest_package"| DB
```

| Aspect | As built |
|---|---|
| Concurrency model | Single process; analysis runs in Starlette's in-process background task, not a queue or worker pool ([routes.py:88](../src/evidence_intelligence/api/routes.py#L88)) |
| GEE session | Module-level `_initialized` flag; one `ee.Initialize` per process ([gee_client.py:104](../src/evidence_intelligence/ingestion/gee_client.py#L104)) |
| DB session | Module-level engine/sessionmaker built from `default_settings.database_url` — `get_session` does not read the injected `Settings`, so a test/settings override changes model gates but not the database it points at ([dependencies.py:20](../src/evidence_intelligence/api/dependencies.py#L20)) |
| Session lifetime vs background work | The `EvidenceStore` handed to the background task comes from a `yield` dependency, whose teardown (`session.close()`) runs before background tasks on FastAPI ≥ 0.106. SQLAlchemy sessions stay usable after `close()`, so pipeline writes land in fresh transactions rather than the request's — worth confirming against a live Postgres, since the suite injects `FakeEvidenceStore` and cannot observe it |
| Config | `settings = load_settings()` executes at import ([config.py:91](../src/evidence_intelligence/config.py#L91)); env changes need a restart |
| Model artifact | Loaded lazily and cached per path; a load failure logs and degrades to the untrained placeholder rather than raising ([pipeline.py:58](../src/evidence_intelligence/pipeline.py#L58)) |

## 2. Request lifecycle — status machine

The five `RequestStatus` values and exactly what moves between them.

```mermaid
stateDiagram-v2
    [*] --> RECEIVED: POST accepted, row written, 202 returned
    RECEIVED --> IN_PROGRESS: background task starts, set_status at pipeline entry
    IN_PROGRESS --> COMPLETE: usable imagery, COMPLETE package written, completed_at stamped
    IN_PROGRESS --> INSUFFICIENT_DATA: imagery.usable is false, WEATHER_ONLY_PRELIMINARY package written first
    IN_PROGRESS --> FAILED: unhandled exception, logged, status set in the except block
    INSUFFICIENT_DATA --> IN_PROGRESS: retry_insufficient_data re-ingests and imagery is now usable
    COMPLETE --> [*]
    FAILED --> [*]

    note right of INSUFFICIENT_DATA
        A preliminary package already exists and is never
        mutated. A later COMPLETE run appends a second
        package row; GET returns the newest by generated_at.
    end note

    note right of FAILED
        FR-022 covers only the imagery-unavailable case.
        run_pipeline_background extends never-fail-silently
        to every other exception, including a failed
        set_status, which is logged and swallowed.
    end note
```

| Aspect | As built |
|---|---|
| `RECEIVED` is momentary | Written by `create_request`, overwritten by the pipeline's first statement ([pipeline.py:240](../src/evidence_intelligence/pipeline.py#L240)) |
| Retry trigger | `retry_insufficient_data` exists and is tested, but nothing in `src/` schedules it — no cron, queue, or scheduler is wired ([pipeline.py:689](../src/evidence_intelligence/pipeline.py#L689)) |
| `estimated_completion` | 10 minutes normally, 24 hours while `INSUFFICIENT_DATA`; declared operational estimates, not evidentiary figures ([routes.py:25](../src/evidence_intelligence/api/routes.py#L25)) |
| Immutability | No component, weather, satellite, or package row is ever updated in place — every stage inserts ([evidence_store.py:111](../src/evidence_intelligence/store/evidence_store.py#L111), [:194](../src/evidence_intelligence/store/evidence_store.py#L194)) |

## 3. End-to-end sequence, as built

The intended sequence is [`evidence-flow-spec.md` §9](evidence-flow-spec.md). This is the executed
one, including where control returns to the caller and where each row is written.

```mermaid
sequenceDiagram
    autonumber
    participant R as Requester
    participant API as routes.py
    participant DB as EvidenceStore
    participant P as pipeline.run_pipeline
    participant GEE as GEEClient
    participant WX as WeatherClient / IMDClient
    participant O as observe()
    participant M as models + causation
    participant PKG as report_generator
    participant OS as Object storage

    R->>API: POST geometry, event_date, peril_type, external_reference_id
    API->>API: shape() validates GeoJSON, to_ewkt() normalises to EWKT at SRID 4326
    API->>DB: create_request -> RECEIVED
    API-->>R: 202 request_id, IN_PROGRESS, estimated_completion
    Note over API,P: response is already sent, everything below is the background task

    P->>DB: set_status IN_PROGRESS
    P->>GEE: optical_composite pre-event, 30d ending event_date-1
    P->>GEE: optical_composite post-event, event_date .. +15d
    P->>GEE: historical_composite, same window x 5 prior years
    alt post-event optical unusable AND peril is flood
        P->>GEE: sar_composite, orbit-pinned VV and VH
    end
    P->>WX: CHIRPS mean/total/max, ERA5-Land temp, SMAP, GPM if cloudburst or hailstorm
    P->>WX: same-window baselines x 5 prior years
    P->>WX: IMD station_record, optional corroboration
    P->>O: observe(imagery, weather) -> FieldObservations

    alt imagery.usable is false
        P->>M: causation.score with every satellite-derived term absent
        P->>DB: add_weather_result
        P->>PKG: WEATHER_ONLY_PRELIMINARY package
        PKG->>OS: put package.json + report.pdf
        P->>DB: add_package, set_status INSUFFICIENT_DATA
    else usable
        P->>DB: add_satellite_result, flood extent as EWKT or NULL
        opt optical pair present
            P->>M: C1 semi-physical
            P->>DB: add_component_result SEMI_PHYSICAL
        end
        P->>M: C2 AI/ML over measured features only
        P->>DB: add_component_result AI_ML
        opt CSM_HIGH_SCRUTINY_ENABLED and ndvi_drop present
            P->>M: C3 CSM assimilation, placeholder
            P->>DB: add_component_result CSM_ASSIMILATION
        end
        P->>M: C4 ensemble, confidence-weighted
        P->>DB: add_component_result ENSEMBLE + damage_classification
        P->>M: C5 DSI, entropy-weighted
        P->>DB: add_component_result DSI
        P->>M: causation.score over measurable terms
        P->>DB: add_weather_result with causation score
        P->>PKG: COMPLETE package with manifest, accuracy statements, notes
        PKG->>OS: put package.json + report.pdf
        P->>DB: add_package, set_status COMPLETE
    end

    R->>API: GET /evidence-requests/:id
    API->>DB: get_request + latest_package + list_weather_results
    API-->>R: status, package URIs, methodology_version, causation score, tier note
```

## 4. The tier decision — which kind of package a request gets

One branch decides everything downstream: whether the field was seen at all, and by what sensor.

```mermaid
flowchart TD
    S["ingest_imagery"] --> PRE["Pre-event optical<br/>Sentinel-2, else Landsat 8/9"]
    S --> POST["Post-event optical"]
    PRE --> GATE1{"has_sufficient_coverage<br/>vs MINIMUM_VALID_PIXEL_FRACTION"}
    POST --> GATE2{"has_sufficient_coverage"}
    GATE1 -->|"below threshold"| PRENONE["pre_event = None"]
    GATE2 -->|"below threshold"| POSTNONE["post_event = None"]

    GATE2 -->|"passes"| USABLE["usable = True"]
    POSTNONE --> FLOODQ{"peril_type.is_flood_compatible<br/>i.e. peril == flood"}
    FLOODQ -->|"no"| NOTUSABLE["usable = False"]
    FLOODQ -->|"yes"| SAR["sar_composite<br/>VV mandatory, VH best-effort"]
    SAR -->|"VV drop measurable"| USABLESAR["usable = True, SAR substitutes"]
    SAR -->|"None"| NOTUSABLE

    USABLE --> T1["Tier A — COMPLETE, optical<br/>C1 + C2 (+C3) + C4 + C5<br/>all NDVI-derived signals present"]
    USABLESAR --> T2["Tier B — COMPLETE, SAR-substituted<br/>C1 omitted, NDVI-derived signals absent<br/>evidence rests on flood extent + weather<br/>disclosed in accuracy_statement"]
    NOTUSABLE --> T3["Tier C — WEATHER_ONLY_PRELIMINARY<br/>no damage fraction, no DSI, no classification<br/>status INSUFFICIENT_DATA, re-runnable"]

    T1 --> OUT["Package + rows"]
    T2 --> OUT
    T3 --> OUT
```

| Aspect | As built |
|---|---|
| Coverage gate is inert by default | `minimum_valid_pixel_fraction` is `None` unless a deployment sets it; coverage is always measured and disclosed, and only *suppresses* a composite once a value exists ([imagery.py:32](../src/evidence_intelligence/ingestion/imagery.py#L32)) |
| Unknown coverage ≠ zero coverage | A composite whose fraction could not be measured passes the gate and is disclosed as "coverage not measured" |
| SAR is not a general fallback | Only `PerilType.FLOOD` reaches it; drought, heatwave, hailstorm etc. fall through to Tier C ([schema.py:40](../src/evidence_intelligence/store/schema.py#L40)) |
| Tier B honesty rule | SAR yields no NDVI-equivalent, so Component 1 and every NDVI-derived signal stay absent instead of being estimated from a substituted value ([pipeline.py:522](../src/evidence_intelligence/pipeline.py#L522)) |
| Tier C is never a bare failure | A weather-only package with full §65B fields is still generated and stored ([pipeline.py:600](../src/evidence_intelligence/pipeline.py#L600)) |

## 5. Imagery ingestion internals (Earth Engine)

Where the pixels come from and what is computed server-side before anything reaches Python.

```mermaid
flowchart TD
    subgraph Win["Windows, derived from event_date"]
        W1["pre: -30d .. -1d"]
        W2["post: 0 .. +15d"]
        W3["historical: same window, 5 prior years"]
        W4["SAR pre: pre_end-30d .. pre_end"]
    end

    subgraph Optical["optical_composite"]
        A["ImageCollection COPERNICUS/S2_SR_HARMONIZED<br/>filterBounds + filterDate<br/>CLOUDY_PIXEL_PERCENTAGE under 95, a performance prefilter only"]
        A -->|"collection not empty"| B["Per-pixel SCL mask<br/>drop 0,1,2,3,8,9,10,11<br/>keep vegetation, bare, water, unclassified"]
        A -->|"empty"| L["ImageCollection LANDSAT/LC09/C02/T1_L2<br/>QA_PIXEL bits 0-5 masked"]
        B --> C["median() composite"]
        L --> C2["median() composite"]
        C --> D["NDVI = normalizedDifference B8, B4<br/>LSWI = normalizedDifference B8, B11"]
        C2 --> D2["NDVI = SR_B5, SR_B4<br/>LSWI = SR_B5, SR_B6"]
        D --> E["reduceRegion mean, scale 10m"]
        D2 --> E2["reduceRegion mean, scale 30m"]
        E --> F["valid_pixel_fraction<br/>count().gt(0).unmask(0) then mean"]
        E2 --> F
    end

    subgraph Sar["sar_composite, flood-compatible perils only"]
        G["COPERNICUS/S1_GRD, IW mode"]
        G --> H["_dominant_orbit of the post-event pass<br/>orbitProperties_pass + relativeOrbitNumber_start"]
        H --> I["Pin pre and post medians to that geometry<br/>filter transmitterReceiverPolarisation"]
        I --> J["vv_drop_db = pre - post<br/>vh_drop_db = pre - post, None if VH never acquired"]
        J --> K["flood mask: post-event VV below -15 dB<br/>AND drop above 3 dB<br/>reduceToVectors scale 10m -> FeatureCollection"]
        K --> K2["to_ewkt: dissolve features with unary_union<br/>empty collection -> NULL, not an empty geometry"]
    end

    W1 --> Optical
    W2 --> Optical
    W3 --> Optical
    W4 --> Sar
    F --> P["Phenology sanity check<br/>pre-event NDVI below 0.2 -> flag, never block"]
```

| Aspect | Value / rule | Source |
|---|---|---|
| Masking order | Mask per pixel **before** compositing, so cloudy pixels never enter the median | [gee_client.py:160](../src/evidence_intelligence/ingestion/gee_client.py#L160) |
| Why `unmask(0)` matters | GEE reducers skip masked pixels; without it, coverage would always read 1.0 exactly when coverage was worst | [gee_client.py:147](../src/evidence_intelligence/ingestion/gee_client.py#L147) |
| SWIR band choice | S2 **B11** (~1565–1655 nm), not B12 — B11 matches the MODIS band LSWI is defined on; reduction pinned to 10 m so B11 is resampled up rather than degrading NIR | [gee_client.py:20](../src/evidence_intelligence/ingestion/gee_client.py#L20) |
| Orbit pinning | Backscatter varies with incidence angle and look direction; differencing ascending against descending manufactures exactly the >3 dB drop read as flooding | [gee_client.py:254](../src/evidence_intelligence/ingestion/gee_client.py#L254) |
| VH is never substituted by VV | Cross-pol tracks canopy volume scattering, co-pol tracks surface — a missing VH leaves the signal absent | [gee_client.py:217](../src/evidence_intelligence/ingestion/gee_client.py#L217) |
| Blocking calls | `.getInfo()` per collection-size check and per reduction — each is a synchronous round trip inside the background task | throughout `gee_client.py` |

## 6. Weather ingestion internals

```mermaid
flowchart LR
    E["event_date"] --> W["Window: -7d .. +3d"]
    W --> P1["CHIRPS UCSB-CHG/CHIRPS/DAILY<br/>mean over window, 5 km scale"]
    W --> P2["CHIRPS sum -> precipitation_total_mm"]
    W --> P3["CHIRPS max -> precipitation_max_daily_mm"]
    W --> T["ERA5-Land DAILY_AGGR temperature_2m<br/>kelvin -> celsius at the boundary"]
    W --> SM["SMAP SPL4SMGP sm_surface"]
    W --> G{"peril is cloudburst<br/>or hailstorm?"}
    G -->|"yes"| NRT["GPM IMERG V07 precipitationCal<br/>no baseline, no anomaly"]
    G -->|"no"| SKIP["not fetched"]

    P1 --> B["Same calendar window, 5 prior years<br/>mean of the non-null years"]
    T --> B
    SM --> B
    B --> AN{"anomaly form"}
    AN -->|"precipitation, soil moisture"| REL["relative: (obs - base) / abs(base)<br/>None when base == 0"]
    AN -->|"temperature"| ABS["absolute: obs - base, in degrees C"]
    W --> IMDQ{"IMD_AWS_API_BASE_URL set?"}
    IMDQ -->|"yes"| IMDC["httpx GET /station-data, 10s timeout<br/>any HTTPError -> None"]
    IMDQ -->|"no"| IMDN["station_corroboration = None"]
    IMDC --> OUT["WeatherIngestionResult"]
    REL --> OUT
    ABS --> OUT
    NRT --> OUT
```

| Aspect | As built |
|---|---|
| Why total and max exist alongside the mean | 200 mm in one day inside a 10-day window averages to 20 mm/day — indistinguishable from steady rain, and cloudburst/hailstorm are the module's highest-value cases ([weather.py:117](../src/evidence_intelligence/ingestion/weather.py#L117)) |
| Unit conversion boundary | ERA5-Land serves kelvin; converting at the client keeps every `*_temp_c` consumer honest. Returning kelvin previously pushed every reading past `temp_max_c`, zeroing Component 1's biomass at full confidence ([weather.py:134](../src/evidence_intelligence/ingestion/weather.py#L134)) |
| Baseline cost | Each of the three baselined sources issues 5 extra GEE reductions per request (~18 reductions total for weather alone) |
| IMD posture | Corroborates, never substitutes; absence is recorded, not filled ([weather.py:152](../src/evidence_intelligence/ingestion/weather.py#L152)) |
| Optional client methods | `_optional` tolerates a client without the extreme-rainfall statistics rather than failing the request ([weather.py:314](../src/evidence_intelligence/ingestion/weather.py#L314)) |

## 7. The observation layer — the module's central discipline

`observe()` is the single place that decides *what was actually measured for this field*. Everything
downstream reads `FieldObservations` and never a raw bundle. This is what prevents the recurring
defect class where an unmeasured input becomes a number.

```mermaid
flowchart TD
    subgraph In["Raw bundles"]
        IM["ImageryIngestionResult"]
        WE["WeatherIngestionResult"]
    end

    IM --> OBS["observe()"]
    WE --> OBS

    OBS --> M["MEASURED — Observation(value, source)"]
    OBS --> S["SUBSTITUTED — a value nobody measured,<br/>stated in the signal's source string"]
    OBS --> A["ABSENT — Absent(reason), required reason"]

    M --> M1["pre/post NDVI, ndvi_deviation = max(0, pre - post)"]
    M --> M2["pre/post fAPAR and fapar_deviation<br/>fAPAR = clip(1.24 x NDVI - 0.168, 0, 1)"]
    M --> M3["pre/post LSWI and lswi_deviation from SWIR"]
    M --> M4["rainfall_anomaly, temperature_anomaly, soil_moisture_deviation"]
    M --> M5["sar_vh_backscatter_deviation, vh_vv_backscatter_deviation = vh_drop - vv_drop"]

    S --> S1["pre/post temp: 25.0 C when ERA5 returned nothing<br/>identical on both sides either way"]
    S --> S2["pre/post insolation: fixed 18.0 MJ proxy, no feed wired"]
    S --> S3["weather_anomaly_magnitude: min(1, abs(anomaly or 0.0))<br/>unmeasurable anomaly becomes a measured 0.0"]
    S --> S4["LSWI falls back to NDVI only where SWIR was unusable<br/>provenance says which"]

    A --> A1["no usable pre/post optical pair"]
    A --> A2["no SAR composite for this peril"]
    A --> A3["single-polarization acquisition, VH only"]
    A --> A4["no historical baseline to compare against"]

    M1 --> API2["Accessors: value() -> float or None<br/>is_present(), present(names), history(), absent_reason()<br/>deliberately NO get(name, default) and NO __getitem__"]
    S1 --> API2
    A1 --> API2
    API2 --> D1["C1 semi-physical"]
    API2 --> D2["C2 feature vector"]
    API2 --> D3["C5 DSI indicators"]
    API2 --> D4["Causation terms"]
    API2 --> D5["Evidence-inputs manifest"]
```

| Aspect | As built |
|---|---|
| Enforcement mechanism | The API shape, not a type checker — no default-returning accessor exists, so a fallback must be written visibly at the call site ([observation.py:79](../src/evidence_intelligence/observation.py#L79)) |
| Why the reason is mandatory | "Missing" and "missing because no post-event composite cleared the cloud gate" are different claims in an evidence package; only the second is auditable |
| Empty history == no history | Both return `None`; treating "no archive" as "zero variance" is what collapses the DSI's entropy weights ([observation.py:118](../src/evidence_intelligence/observation.py#L118)) |
| Known preserved substitutions | The 25 °C temperature and the 0.0 weather anomaly are deliberately *not* corrected here — they were lifted verbatim so the golden fixtures stay byte-identical, and are flagged for tasks that own the fixture flip ([observation.py:292](../src/evidence_intelligence/observation.py#L292), [:343](../src/evidence_intelligence/observation.py#L343)) |
| Known quantity mismatch | The NDVI *history* holds absolute index values while `NDVI_DEVIATION` is a drop — pinned, not fixed ([observation.py:381](../src/evidence_intelligence/observation.py#L381)) |

## 8. Damage model layer and ensemble weighting

Five components, three gates, one confidence-weighted blend.

```mermaid
flowchart TD
    OBS["FieldObservations"]

    OBS --> G1{"optical pair present?"}
    G1 -->|"yes"| C1["C1 Semi-Physical, RUE chain<br/>biomass = RUE_max 2.5 x PAR x fAPAR x W x T<br/>W = (1+LSWI)/(1+0.5)<br/>T piecewise on 8 / 25 / 40 C<br/>damage = clip((exp - obs)/exp, 0, 1)"]
    G1 -->|"no"| C1SKIP["absent from the ensemble<br/>no fabricated estimate"]

    OBS --> C2["C2 AI/ML Random Forest<br/>17 declared features, 6 supplied today<br/>n_estimators 200, max_features sqrt,<br/>min_samples_leaf 5, random_state 42"]
    C2 --> C2Q{"AI_ML_MODEL_PATH loaded?"}
    C2Q -->|"no"| C2P["placeholder = clip(mean(abs(supplied))/2, 0, 1)<br/>status untrained_placeholder, MAE/RMSE/NRMSE null"]
    C2Q -->|"yes"| C2T["RF predict, clipped 0-1<br/>status trained, held-out metrics reported"]

    OBS --> G3{"CSM_HIGH_SCRUTINY_ENABLED<br/>AND ndvi_drop present?"}
    G3 -->|"yes"| C3["C3 CSM assimilation — PLACEHOLDER<br/>echoes the ndvi_drop it was handed<br/>calibration_confidence 0.4"]
    G3 -->|"no, the default"| C3SKIP["not run"]

    C1 --> W1["weight = calibration_confidence<br/>0.85 clean, 0.5 with input warnings"]
    C2P --> W2P["weight = 0.15"]
    C2T --> W2T["weight = max(0.05, 1 - min(nrmse, 1))"]
    C3 --> W3["weight = 0.4"]

    W1 --> ENS["C4 Ensemble<br/>damage = sum(w x d) / sum(w)<br/>combined_confidence = sum(w)/n, capped 1.0<br/>zero total weight -> plain mean, confidence 0"]
    W2P --> ENS
    W2T --> ENS
    W3 --> ENS

    ENS --> CLS["_classify against DAMAGE_CLASSIFICATION_BANDS<br/>default 0.1 / 0.33 / 0.66<br/>negligible, minor, moderate, severe"]
    ENS --> YL["yield loss = damage x Harvest Index 0.4"]

    OBS --> C5["C5 DSI, independent of the ensemble"]
    CLS --> PKG2["Package"]
    YL --> PKG2
    C5 --> PKG2
```

| Aspect | As built |
|---|---|
| C1 algebra today | Insolation is the same constant on both sides and temperature is passed identically, so RUE, PAR and the temperature scalar cancel: the damage fraction reduces to `1 − (fAPAR_post × (1+LSWI_post)) / (fAPAR_pre × (1+LSWI_pre))`, clipped. It still contributes weight 0.85 to the blend ([semi_physical.py:75](../src/evidence_intelligence/models/semi_physical.py#L75)) |
| C1 unit sanity check | A temperature outside [−90, 60] means the caller supplied non-celsius; confidence drops to 0.5 and a warning reaches the package ([semi_physical.py:23](../src/evidence_intelligence/models/semi_physical.py#L23)) |
| C2 feature reality | Supplied: `ndvi_deviation`, `fapar_deviation`, `rainfall_anomaly`, `temperature_anomaly`, `soil_moisture_deviation`, `vh_vv_backscatter_deviation`. The other 11 of 17 are never computed and are omitted from the placeholder's mean; a **trained** model still receives `0.0` for them in the ordered array ([ai_ml.py:146](../src/evidence_intelligence/models/ai_ml.py#L146)) |
| C2 load safety | `load()` refuses artifacts trained under a different feature order or methodology version ([ai_ml.py:122](../src/evidence_intelligence/models/ai_ml.py#L122)) |
| C3 status | A placeholder that restates another component's input into a confidence-weighted average — i.e. it manufactures corroboration. Keep the flag off ([csm_assimilation.py:1](../src/evidence_intelligence/models/csm_assimilation.py#L1)) |
| Harvest Index | One `0.4` for every crop, read from `CropParameters` so C1 and C2 cannot drift apart; the request contract carries no crop type to look a real value up by, and every package discloses this ([pipeline.py:161](../src/evidence_intelligence/pipeline.py#L161)) |
| Classification bands | Configuration, not a sourced standard; disclosed in every package ([pipeline.py:673](../src/evidence_intelligence/pipeline.py#L673)) |

## 9. Causation scoring — exclusion, not zero-filling

```mermaid
flowchart TD
    subgraph Terms["Four alignment terms, each float or None"]
        T1["Temporal 30%<br/>drop within 7d = 100, 7 to 14d = 70, beyond 14d = 30"]
        T2["Spatial 25%<br/>covers geometry = 100, within 5km = 80,<br/>within 10km = 50, else 0"]
        T3["Magnitude 25%<br/>100 x (1 - abs(weather_norm - ndvi_norm))"]
        T4["Physiological 20%<br/>peril 'other' -> 50 generic pass<br/>else flagged 40 / clean 90"]
    end

    P["pipeline call site"] -->|"days_between = None<br/>no break-point date exists"| T1
    P -->|"distance_km = None<br/>anomaly footprint never computed"| T2
    P -->|"weather_anomaly (substituted 0.0 if unmeasurable)<br/>ndvi_drop/0.5 or None"| T3
    P -->|"phenology_flag + phenology_checked"| T4

    T1 --> SPLIT{"value is None?"}
    T2 --> SPLIT
    T3 --> SPLIT
    T4 --> SPLIT
    SPLIT -->|"yes"| EX["excluded, name -> reason<br/>carried into JSON and PDF"]
    SPLIT -->|"no"| CON["contributing"]

    CON --> SUM["score = round( sum(v x w) / sum(w over contributing) )<br/>renormalised, not zero-filled"]
    EX --> SUM
    SUM --> NONE{"no term measured?"}
    NONE -->|"yes"| NULLSC["score = None<br/>package says so, damage figures unaffected"]
    NONE -->|"no"| LOW{"below CAUSATION_LOW_CONFIDENCE_THRESHOLD?"}
    LOW -->|"threshold unset (default)"| DELIV["low_confidence = False"]
    LOW -->|"yes"| LABEL["labelled low-confidence,<br/>still delivered in full, never suppressed"]
```

| Aspect | As built |
|---|---|
| Effective score today, Tier A/B | Temporal and spatial are always `None` at the call site, so the score is the renormalised blend of magnitude and physiological only — weights 0.25 and 0.20 become 55.6% and 44.4% ([pipeline.py:453](../src/evidence_intelligence/pipeline.py#L453)) |
| Effective score today, Tier C | All four terms absent → `score = None`, except `peril_type = other`, where the physiological generic pass returns 50 before the never-checked branch is reached ([scoring.py:123](../src/evidence_intelligence/causation/scoring.py#L123)) |
| Why exclusion beats zero | Scoring an unmeasured NDVI drop as `0.0` made the magnitude term report *perfect* correlation whenever the weather anomaly was also near zero — how a request with no imagery once outscored one with a full optical pair ([scoring.py:1](../src/evidence_intelligence/causation/scoring.py#L1)) |
| Why renormalise | Letting an excluded term keep its share of the 100 points is the same error as scoring it zero, one step removed |
| Persistence | Nullable column — a request with nothing measurable stores no score rather than a fabricated one ([schema.py:159](../src/evidence_intelligence/store/schema.py#L159)) |

## 10. Damage Severity Index (Component 5)

```mermaid
flowchart LR
    subgraph Ind["Six indicators, direction-aware"]
        I1["ndvi_deviation +"]
        I2["lswi_deviation +"]
        I3["sar_vh_backscatter_deviation +"]
        I4["fapar_deviation +"]
        I5["weather_anomaly_magnitude +"]
        I6["crop_condition_variability -<br/>inverted, never populated"]
    end

    Ind --> N["Min-Max normalise against this field's own archive<br/>no archive OR hi == lo -> 0.5 neutral midpoint<br/>clip to 0-1, invert if negative direction"]
    HIST["Historical archives<br/>only ndvi_deviation is wired (5 optical composites)<br/>the other five are recorded absent"] --> N
    HIST --> W["Entropy weights<br/>e = -sum(p ln p)/ln n over abs values<br/>diversity = 1 - e, normalised to sum 1<br/>empty archive -> e = 1 -> diversity 0"]
    N --> S["score = sum(weight x normalised)"]
    W --> S
    S --> R["Stored as the DSI component row<br/>and reported as supporting evidence only"]
```

| Aspect | As built |
|---|---|
| Per-field, never per-group | Normalised against the field's own archive rather than an IU or regional average — the deliberate divergence from CHF-style indices ([dsi.py:1](../src/evidence_intelligence/models/dsi.py#L1)) |
| Weight collapse | With five of six archives empty, their diversity is 0 and effectively all weight lands on `ndvi_deviation`; with *no* archive at all the weights fall back to uniform 1/6 over six 0.5 midpoints, producing a confident-looking 0.5 from no historical evidence ([dsi.py:41](../src/evidence_intelligence/models/dsi.py#L41)) |
| Quantity mismatch | The wired archive holds absolute NDVI values while the indicator is a drop, so a real 0.45 drop normalises below the archive floor — captured in the `varied_historical_archive` golden fixture as a known-wrong value |
| Absent ≠ zero | `pipeline` passes only measured indicators; `compute` treats an absent one as the 0.5 neutral midpoint rather than a measured 0.0 ([pipeline.py:427](../src/evidence_intelligence/pipeline.py#L427)) |

## 11. Package assembly and the §65B fields

```mermaid
flowchart TD
    subgraph Inputs["What the package is assembled from"]
        A1["Ensemble damage fraction + combined confidence"]
        A2["DSI score"]
        A3["Damage classification label"]
        A4["Causation score + contributing/excluded terms"]
        A5["Source attribution: dataset, version, acquisition date,<br/>window_total_mm, max_daily_mm, IMD corroboration"]
        A6["Accuracy statement: fAPAR approximation, model status,<br/>features measured n of 17, coverage %, HI and band assumptions"]
        A7["Notes: no historical baseline, phenology flag,<br/>causation not computed / partially computed, low confidence"]
        A8["Evidence-inputs manifest: 11 named inputs x<br/>USED / DEGRADED / UNAVAILABLE / NOT_APPLICABLE + detail"]
    end

    Inputs --> PC["PackageContent dataclass"]
    PC --> J["_build_json_record -> package.json<br/>yield loss and DSI both tagged<br/>supporting_evidence_not_authoritative<br/>+ standing CCE disclaimer"]
    PC --> P["_build_pdf -> report.pdf, ReportLab A4<br/>causation, estimates, chain of custody,<br/>accuracy statement, notes"]
    J --> ST["storage.put request_id/YYYYMMDDTHHMMSS/package.json"]
    P --> ST2["storage.put request_id/YYYYMMDDTHHMMSS/report.pdf"]
    J --> CK["checksum = sha256(json_bytes + pdf_bytes)"]
    P --> CK
    ST --> ROW["EvidencePackage row<br/>tier, URIs, methodology_version v1.0.0,<br/>checksum, generated_at,<br/>retention_expiry_date = +10 years"]
    ST2 --> ROW
    CK --> ROW
    ROW --> GET["GET returns the newest package for the request<br/>preliminary packages remain retrievable by package_id"]
```

| Aspect | As built |
|---|---|
| `map_uris` | Always `[]` — the GIS map exports promised by [`hld.md` §6](hld.md) are not implemented, though `folium`/`matplotlib` are already dependencies ([report_generator.py:186](../src/evidence_intelligence/packaging/report_generator.py#L186)) |
| `affected_area_ha` | Always `None` on both the ENSEMBLE row and the package, so [`evidence-flow-spec.md` §4 step 5](evidence-flow-spec.md)'s damaged-pixel area computation has no implementation |
| Manifest coverage | Built and attached on the COMPLETE path only; the weather-only path assembles its package through a second, duplicated code path that never passes a manifest — recorded as known-wrong in two golden fixtures ([pipeline.py:634](../src/evidence_intelligence/pipeline.py#L634)) |
| Retention | Enforced at package-creation time, with a Feb-29 leap-year guard ([evidence_store.py:29](../src/evidence_intelligence/store/evidence_store.py#L29)) |
| Every tier gets the full §65B field set | Source attribution, methodology version, accuracy statement, checksum and timestamp are present on preliminary packages too |

## 12. Persistence model

```mermaid
erDiagram
    EVIDENCE_REQUESTS ||--o{ SATELLITE_ANALYSIS_RESULTS : produces
    EVIDENCE_REQUESTS ||--o{ MODEL_COMPONENT_RESULTS : produces
    EVIDENCE_REQUESTS ||--o{ WEATHER_CORRELATION_RESULTS : produces
    EVIDENCE_REQUESTS ||--o{ EVIDENCE_PACKAGES : produces

    EVIDENCE_REQUESTS {
        string request_id PK
        geometry geometry "PostGIS GEOMETRY srid 4326, written as EWKT"
        date event_date
        enum peril_type "11 values"
        string external_reference_id "opaque, never interpreted"
        enum status "RECEIVED IN_PROGRESS COMPLETE INSUFFICIENT_DATA FAILED"
        datetime requested_at
        datetime completed_at "set only on COMPLETE"
    }
    SATELLITE_ANALYSIS_RESULTS {
        string result_id PK
        string source_dataset "mandatory provenance"
        string source_version
        date acquisition_date
        float pre_event_index_value "null when SAR substituted"
        float post_event_index_value "null when SAR substituted"
        string index_type "NDVI"
        geometry flood_extent_geometry "null unless SAR found flooding"
    }
    MODEL_COMPONENT_RESULTS {
        string result_id PK
        enum component "SEMI_PHYSICAL AI_ML CSM_ASSIMILATION ENSEMBLE DSI"
        string methodology_version "pinned per component"
        float point_estimate
        json confidence_or_accuracy "calibration, MAE RMSE NRMSE, entropy weights"
        string damage_classification "ENSEMBLE row only"
        float affected_area_ha "not computed today"
        json component_inputs "declared, unpopulated"
    }
    WEATHER_CORRELATION_RESULTS {
        string result_id PK
        string source_dataset "CHIRPS Daily"
        string source_version
        float observed_value
        float historical_baseline
        float anomaly_score
        int causation_confidence_score "nullable by design"
    }
    EVIDENCE_PACKAGES {
        string package_id PK
        enum package_tier "WEATHER_ONLY_PRELIMINARY COMPLETE"
        string pdf_uri
        string json_uri
        json map_uris "empty today"
        string methodology_version
        string checksum "sha256 over json + pdf"
        datetime generated_at
        date retention_expiry_date "generated_at + 10 years"
    }
```

Append-only in practice: one row per component per run, multiple packages per request, and a
preliminary package is superseded by insertion rather than mutation.

## 13. Configuration gates and what each one changes in the graph

```mermaid
flowchart LR
    subgraph Unset["Unset by default — no sourced value exists"]
        V1["MINIMUM_VALID_PIXEL_FRACTION"] --> E1["Coverage measured and disclosed<br/>but never suppresses a composite"]
        V2["CAUSATION_LOW_CONFIDENCE_THRESHOLD"] --> E2["low_confidence always False<br/>packages are never auto-rejected regardless"]
        V3["AI_ML_MODEL_PATH"] --> E3["C2 runs the disclosed placeholder<br/>ensemble weight 0.15"]
    end
    subgraph Off["Off by default — deliberately"]
        V4["CSM_HIGH_SCRUTINY_ENABLED=false"] --> E4["C3 skipped; enabling it would add<br/>false corroboration from a placeholder"]
    end
    subgraph Defaults["Defaulted, because something must exist"]
        V5["DAMAGE_CLASSIFICATION_BANDS=0.1,0.33,0.66"] --> E5["Every package gets a label<br/>and discloses that the cut points are a convention"]
    end
    subgraph Required["Required for real runs"]
        V6["GEE_SERVICE_ACCOUNT_CREDENTIALS"] --> E6["Absent -> ee.Initialize raises at first ingestion"]
        V7["DATABASE_URL"] --> E7["PostgreSQL + PostGIS"]
        V8["EVIDENCE_STORE_BUCKET<br/>EVIDENCE_STORE_LOCAL_ROOT"] --> E8["Local disk today, S3-compatible interface"]
        V9["IMD_AWS_API_BASE_URL"] --> E9["Unset -> no station corroboration, recorded as UNAVAILABLE"]
    end
```

The pattern is consistent and worth naming: **a threshold with no sourced value ships unset and
disclosed rather than guessed**, and the only exception is the classification bands, because
`damage_classification` is populated on every ENSEMBLE row so *some* mapping must exist — which is
why that one carries a disclosure string instead ([config.py:22](../src/evidence_intelligence/config.py#L22)).

## 14. Test seams and the reproducibility harness

```mermaid
flowchart TD
    subgraph Seams["Injection points"]
        S1["run_pipeline(gee_client, weather_client, imd_client,<br/>ai_ml_model, storage) — all optional, all defaulted"]
        S2["app.dependency_overrides for get_store and get_settings"]
    end
    S1 --> F["tests/fakes.py<br/>FakeGEEClient (scenario-keyed), FakeWeatherClient,<br/>FakeIMDClient, FakeEvidenceStore"]
    S2 --> F

    F --> L1["contract/ — 12 tests, request/response shape"]
    F --> L2["integration/ — 25 tests, whole-pipeline behaviour"]
    F --> L3["unit/ — 80 tests, per-module logic"]

    F --> G["tests/golden.py — 8 characterization scenarios<br/>healthy, flood SAR, single-pol, CSM on, partial cloud,<br/>varied history, weather-only, no history"]
    G --> SNAP["Full observable output snapshot:<br/>status, tier, package JSON, all component/satellite/weather rows<br/>floats rounded to 10dp, request_id and timestamp normalised"]
    SNAP --> RULE["Every recorded value is PINNED unless it appears in<br/>the scenario's known_wrong map, which names the task<br/>that will change it and why"]
    RULE --> DIFF["Diff outside the map = regression<br/>Diff inside the map = that task doing its job<br/>Re-record only as part of the named task"]
```

The golden harness is a change detector, not a correctness oracle: it deliberately pins values that
are known to be wrong, so that fixing one is a visible, attributable diff rather than a silent shift
([golden.py:1](../src/tests/golden.py#L1)). Determinism comes from `random_state=42`, fixed feature
ordering, pinned methodology versions per component, and fakes with no clock or network dependency.

## 15. Where the executed flow is thinner than the design

Read as a map from a diagram node to the tracker that owns it — not as new findings. Full status for
each lives in [`GUIDE.md`](../GUIDE.md) "Open Issues" and the two `issue/README.md` trackers.

| Diagram | Node | Gap | Owner |
|---|---|---|---|
| §8 | C1 semi-physical | Insolation constant and temperature identical on both sides, so those terms cancel; RUE applied to part of a season | `002` RUE part-of-season query; `T05-09` |
| §8 | C2 AI/ML | Untrained by default; 11 of 17 declared features never computed | `001` AI/ML training-data question |
| §8 | C3 CSM | Placeholder that echoes its input; flag correctly off | `001` CSM trigger query (reframed) |
| §8 | `_classify` | Band cut points appear in no source document — disclosed, not sourced | `002` `T0-17` (disclosure shipped) |
| §8 | Harvest Index | One `0.4` for all crops; no crop-type field in the request contract | `002` `T0-18` + User Story 4 |
| §9 | Temporal / spatial terms | Structurally unmeasurable today; excluded rather than fabricated | `002` `T05-05` (break-point date) |
| §10 | DSI archives | Five of six archives unwired; quantity mismatch on the sixth | `002` `T0R-05`, `T05-10` |
| §11 | `map_uris`, `affected_area_ha` | Promised by `hld.md` §6 / `evidence-flow-spec.md` §4, not implemented | not yet tracked as a task |
| §11 | Weather-only assembly | Duplicate package-assembly path, no manifest attached | `002` `T0R-06` |
| §2 | Retry scheduling | `retry_insufficient_data` exists but nothing calls it in `src/` | `002` `T05-06` (durability) |
| §11 | No outcome capture | The module discards claim outcomes — now **by design**, not by omission: label sourcing is out of scope per `constitution.md` §9.2 | closed; see `notes/2026-08-13-scope-boundaries-design.md` |
| §7 | Preserved substitutions | 25 °C temperature, 0.0 weather anomaly | flagged in `tasks.md`, fixture-owning tasks |

None of these are in the diagrams by accident: the module's stated posture is that an undisclosed
assumption is worse than a disclosed one, so most of them are already visible in the package a
reader receives.
