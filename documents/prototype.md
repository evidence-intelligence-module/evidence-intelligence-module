# Prototype — Running Pipeline Steps 1 and 2 Standalone

**What this is:** a runbook for exercising **intake** and **ingestion** — the first two stages of
[`technical-flow-diagrams.md`](technical-flow-diagrams.md)'s end-to-end flow — against live data for
a single field, without running the rest of the pipeline.

**Why these two stages specifically.** Steps 1 and 2 are the only stages with no database and no
object-storage dependency. Intake is Pydantic validation plus an EWKT conversion; ingestion is Earth
Engine calls returning plain dataclasses. Everything from step 3 onward writes rows and packages. So
these two can be run from a single script with one external dependency — an Earth Engine service
account — which makes them the right place to start when validating that the module can see a
particular field at all.

**What this is not.** Not a second implementation. The script below calls the same
`ingest_imagery` / `ingest_weather` that [`pipeline.py`](../src/evidence_intelligence/pipeline.py)
calls at its own step 2, with the same arguments, and then stops before `observe()`. If the two ever
disagree, the service is right and this document is stale.

---

## 1. Prerequisites

| Requirement | Why | Blocking? |
|---|---|---|
| Python 3.11 | Matches `src/pyproject.toml` | Yes |
| Earth Engine service account + JSON key | Every satellite and weather source except IMD is fetched through Earth Engine; `_ensure_initialized` raises without it ([gee_client.py:104](../src/evidence_intelligence/ingestion/gee_client.py#L104)) | **Yes — start this first** |
| PostgreSQL + PostGIS | Not needed. Nothing here writes a row | No |
| Object storage | Not needed. Nothing here writes a package | No |
| IMD AWS API base URL | Optional. Unset means station corroboration is recorded absent, which is a valid result | No |

Obtaining the service account is a multi-step Google process — create a Cloud project, enable the
Earth Engine API, register the project for Earth Engine use, create a service account, grant it
Earth Engine access, download the JSON key. Registration approval is not instant, so begin it before
anything else here.

## 2. Setup

```powershell
cd d:\barrel\evidence-intelligence-module\src
python -m venv .venv
.venv\Scripts\pip install -e .

$env:GEE_SERVICE_ACCOUNT_CREDENTIALS = "d:\path\to\ee-service-account.json"
$env:GEE_SERVICE_ACCOUNT_EMAIL       = "your-sa@your-project.iam.gserviceaccount.com"
```

`DATABASE_URL` and `EVIDENCE_STORE_BUCKET` are deliberately not set — [`config.py`](../src/evidence_intelligence/config.py)
defaults them, and nothing in steps 1–2 reads either.

## 3. The runner

Save as `prototype/run.py` (or anywhere on the path with `src/` importable) and run from `src/`.

```python
"""Prototype runner for pipeline steps 1 and 2 — intake and ingestion only.

Calls the same ingest_imagery / ingest_weather that pipeline.run_pipeline
calls, then stops before observe(). Writes no database row, no package, and no
object-storage key.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from shapely.geometry import shape

from evidence_intelligence.geometry import to_ewkt
from evidence_intelligence.ingestion.gee_client import GEEClient, ImageryComposite
from evidence_intelligence.ingestion.imagery import (
    HISTORICAL_BASELINE_YEARS,
    POST_EVENT_WINDOW_DAYS,
    PRE_EVENT_WINDOW_DAYS,
    ImageryIngestionResult,
    ingest_imagery,
)
from evidence_intelligence.ingestion.weather import (
    EVENT_WINDOW_DAYS_AFTER,
    EVENT_WINDOW_DAYS_BEFORE,
    IMDClient,
    WeatherClient,
    WeatherIngestionResult,
    WeatherObservation,
    ingest_weather,
)
from evidence_intelligence.store.schema import PerilType

RUNS_DIR = Path(__file__).parent / "runs"

# Perils for which ingest_weather fetches GPM IMERG. Mirrors
# pipeline.CLOUDBURST_HAILSTORM_PERILS rather than importing it, so this
# prototype does not depend on a private constant of the service.
GPM_PERILS = {PerilType.CLOUDBURST, PerilType.HAILSTORM}


@dataclass(frozen=True)
class FieldPreset:
    label: str
    geometry: dict
    event_date: date
    peril_type: PerilType
    external_reference_id: str
    note: str


def _box(lon: float, lat: float, half_deg: float = 0.001) -> dict:
    """A square GeoJSON Polygon centred on lon/lat.

    At ~20 degrees N, half_deg=0.001 is roughly 220 m on a side (~4.8 ha) — a
    few hundred Sentinel-2 pixels at the 10 m scale optical_composite reduces
    at. Much smaller and one cloud shadow moves the regional mean; much larger
    and it stops describing a single field.

    Arbitrary test extent, never a cadastral boundary — real geometry arrives
    with the request and is not derived here (constitution.md 9.2).
    """
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon - half_deg, lat - half_deg],
            [lon + half_deg, lat - half_deg],
            [lon + half_deg, lat + half_deg],
            [lon - half_deg, lat + half_deg],
            [lon - half_deg, lat - half_deg],
        ]],
    }


# Chandrapur district, Vidarbha, Maharashtra. 10 July sits in peak kharif
# monsoon, which is the point: optical coverage is expected to be poor, so
# these presets exercise the tier decision rather than only the happy path.
_CHANDRAPUR = (79.300, 19.950)

PRESETS: dict[str, FieldPreset] = {
    "chandrapur-flood": FieldPreset(
        label="Chandrapur, Maharashtra — flood, 10 July 2025",
        geometry=_box(*_CHANDRAPUR),
        event_date=date(2025, 7, 10),
        peril_type=PerilType.FLOOD,
        external_reference_id="prototype-chandrapur-flood",
        note=(
            "Flood is the only peril whose is_flood_compatible property is True, "
            "so this is the only preset that can reach SAR substitution when "
            "monsoon cloud makes optical unusable."
        ),
    ),
    "chandrapur-unseasonal-rain": FieldPreset(
        label="Chandrapur, Maharashtra — unseasonal rain, 10 July 2025",
        geometry=_box(*_CHANDRAPUR),
        event_date=date(2025, 7, 10),
        peril_type=PerilType.UNSEASONAL_RAIN,
        external_reference_id="prototype-chandrapur-unseasonal-rain",
        note=(
            "Identical geometry and date to chandrapur-flood, differing only in "
            "peril. SAR is never attempted, so unusable optical falls straight "
            "through to Tier C. Run both to isolate the branch peril controls."
        ),
    ),
    "chandrapur-cloudburst": FieldPreset(
        label="Chandrapur, Maharashtra — cloudburst, 10 July 2025",
        geometry=_box(*_CHANDRAPUR),
        event_date=date(2025, 7, 10),
        peril_type=PerilType.CLOUDBURST,
        external_reference_id="prototype-chandrapur-cloudburst",
        note=(
            "The only preset that triggers the GPM IMERG fetch, which carries no "
            "baseline and no anomaly — it measures intensity, not deviation."
        ),
    ),
}

DEFAULT_PRESET = "chandrapur-flood"


def _composite_json(composite: ImageryComposite | None) -> dict | None:
    if composite is None:
        return None
    return {
        "source_dataset": composite.source_dataset,
        "source_version": composite.source_version,
        "acquisition_date": str(composite.acquisition_date),
        "index_type": composite.index_type,
        "index_value": composite.index_value,
        "lswi_value": composite.lswi_value,
        "valid_pixel_fraction": composite.valid_pixel_fraction,
    }


def _observation_json(observation: WeatherObservation | None) -> dict | None:
    if observation is None:
        return None
    return {
        "source_dataset": observation.source_dataset,
        "source_version": observation.source_version,
        "observed_value": observation.observed_value,
        "historical_baseline": observation.historical_baseline,
        "anomaly_score": observation.anomaly_score,
    }


def _tier_preview(imagery: ImageryIngestionResult) -> tuple[str, str]:
    """Which package tier step 3 would select from this ingestion.

    Restates pipeline's branch rather than importing it — the prototype stops
    at step 2, so this is a preview for the reader, not the real decision.
    """
    if imagery.post_event is not None:
        return "A", "COMPLETE, optical — C1 + C2 (+C3) + C4 + C5, all NDVI signals present"
    if imagery.sar is not None:
        return "B", "COMPLETE, SAR-substituted — C1 omitted, NDVI-derived signals absent"
    return "C", "WEATHER_ONLY_PRELIMINARY — status INSUFFICIENT_DATA, re-runnable"


def _build_record(
    preset: FieldPreset,
    imagery: ImageryIngestionResult,
    weather: WeatherIngestionResult,
    started_at: datetime,
) -> dict:
    tier, tier_detail = _tier_preview(imagery)
    event = preset.event_date
    return {
        "prototype_run": {
            "started_at": started_at.isoformat(),
            "preset": preset.label,
            "note": preset.note,
            "scope": "pipeline steps 1-2 only; no observe(), no models, no package",
        },
        "intake": {
            "geometry_ewkt": to_ewkt(preset.geometry),
            "event_date": str(event),
            "peril_type": preset.peril_type.value,
            "external_reference_id": preset.external_reference_id,
            "is_flood_compatible": preset.peril_type.is_flood_compatible,
            "triggers_gpm_imerg": preset.peril_type in GPM_PERILS,
        },
        "derived_windows": {
            "optical_pre": [
                str(event - timedelta(days=PRE_EVENT_WINDOW_DAYS)),
                str(event - timedelta(days=1)),
            ],
            "optical_post": [
                str(event),
                str(event + timedelta(days=POST_EVENT_WINDOW_DAYS)),
            ],
            "historical_years": HISTORICAL_BASELINE_YEARS,
            "weather": [
                str(event - timedelta(days=EVENT_WINDOW_DAYS_BEFORE)),
                str(event + timedelta(days=EVENT_WINDOW_DAYS_AFTER)),
            ],
        },
        "imagery": {
            "pre_event": _composite_json(imagery.pre_event),
            "post_event": _composite_json(imagery.post_event),
            "historical": [_composite_json(c) for c in imagery.historical],
            "historical_years_returned": len(imagery.historical),
            "sar": (
                None
                if imagery.sar is None
                else {
                    "source_dataset": imagery.sar.source_dataset,
                    "source_version": imagery.sar.source_version,
                    "acquisition_date": str(imagery.sar.acquisition_date),
                    "vv_drop_db": imagery.sar.vv_drop_db,
                    "vh_drop_db": imagery.sar.vh_drop_db,
                    "flood_extent_ewkt": to_ewkt(imagery.sar.flood_extent_geojson),
                }
            ),
            "usable": imagery.usable,
            "phenology_flag": imagery.phenology_flag,
        },
        "weather": {
            "precipitation": _observation_json(weather.precipitation),
            "near_real_time_precipitation": _observation_json(
                weather.near_real_time_precipitation
            ),
            "reanalysis_temperature": _observation_json(weather.reanalysis),
            "soil_moisture": _observation_json(weather.soil_moisture),
            "precipitation_total_mm": weather.precipitation_total_mm,
            "precipitation_max_daily_mm": weather.precipitation_max_daily_mm,
            "station_corroboration": weather.station_corroboration,
        },
        "tier_preview": {"tier": tier, "detail": tier_detail},
    }


def _print_report(record: dict) -> None:
    def line(label: str, value: object) -> None:
        print(f"    {label:<24}: {value}")

    run = record["prototype_run"]
    intake = record["intake"]
    windows = record["derived_windows"]
    imagery = record["imagery"]
    weather = record["weather"]

    print(f"\n{'=' * 78}\n{run['preset']}\n{'=' * 78}")
    print(f"\n  {run['note']}\n")

    print("STEP 1 — INTAKE (what routes.py validates before returning 202)")
    line("event_date", intake["event_date"])
    line("peril_type", intake["peril_type"])
    line("flood_compatible", intake["is_flood_compatible"])
    line("triggers GPM IMERG", intake["triggers_gpm_imerg"])
    line("external_reference_id", intake["external_reference_id"])
    line("geometry (EWKT)", f"{intake['geometry_ewkt'][:56]}...")

    print("\n  Windows, all derived from event_date alone:")
    line("optical pre", " .. ".join(windows["optical_pre"]))
    line("optical post", " .. ".join(windows["optical_post"]))
    line("historical", f"{windows['historical_years']} prior years, same pre-window")
    line("weather", " .. ".join(windows["weather"]))

    print("\nSTEP 2 — INGESTION")
    print("\n  IMAGERY")
    for key in ("pre_event", "post_event"):
        composite = imagery[key]
        if composite is None:
            line(key, "None — no usable composite")
            continue
        line(key, f"NDVI={composite['index_value']} LSWI={composite['lswi_value']}")
        line("  source", f"{composite['source_dataset']} ({composite['source_version']})")
        line("  acquisition_date", composite["acquisition_date"])
        line("  valid_pixel_fraction", composite["valid_pixel_fraction"])
    line(
        "historical",
        f"{imagery['historical_years_returned']} of "
        f"{windows['historical_years']} years returned",
    )
    for composite in imagery["historical"]:
        if composite is not None:
            line(f"  {composite['acquisition_date']}", f"NDVI={composite['index_value']}")
    if imagery["sar"] is None:
        line("sar", "not attempted (optical usable, or peril not flood)")
    else:
        sar = imagery["sar"]
        line("sar vv_drop_db", sar["vv_drop_db"])
        line(
            "sar vh_drop_db",
            sar["vh_drop_db"]
            if sar["vh_drop_db"] is not None
            else "None — single-pol acquisition",
        )
        line(
            "flood_extent",
            "present" if sar["flood_extent_ewkt"] else "None — no flooded pixels",
        )
    line("usable", f"{imagery['usable']}   <- decides the tier")
    line("phenology_flag", imagery["phenology_flag"] or "no flag")

    print("\n  WEATHER")
    for key, label in (
        ("precipitation", "precipitation"),
        ("reanalysis_temperature", "temperature"),
        ("soil_moisture", "soil_moisture"),
        ("near_real_time_precipitation", "gpm_nrt"),
    ):
        observation = weather[key]
        if observation is None:
            line(label, "not fetched for this peril")
            continue
        line(label, f"observed={observation['observed_value']}")
        line("  baseline (5yr)", observation["historical_baseline"])
        line("  anomaly", observation["anomaly_score"])
    line("precipitation_total_mm", weather["precipitation_total_mm"])
    line("precipitation_max_daily", weather["precipitation_max_daily_mm"])
    line(
        "imd_station",
        "present" if weather["station_corroboration"] else "None — unset or unreachable",
    )

    tier = record["tier_preview"]
    print(f"\nSTEP 3 PREVIEW — Tier {tier['tier']}")
    print(f"    {tier['detail']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", choices=sorted(PRESETS), default=DEFAULT_PRESET)
    parser.add_argument(
        "--minimum-valid-pixel-fraction",
        type=float,
        default=None,
        help=(
            "Coverage gate. Unset by default, matching shipped configuration: "
            "coverage is measured and disclosed but never suppresses a composite."
        ),
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Print the report without writing a JSON artifact.",
    )
    args = parser.parse_args(argv)

    preset = PRESETS[args.preset]
    started_at = datetime.utcnow()

    # Step 1: the only validation routes.py performs before accepting.
    try:
        shape(preset.geometry)
    except Exception as exc:
        print(f"invalid GeoJSON geometry (the API would 400): {exc}", file=sys.stderr)
        return 2

    # Step 2: live Earth Engine. Every .getInfo() below is a blocking round
    # trip, so a full run takes minutes rather than seconds.
    print(f"\ncontacting Earth Engine for preset {args.preset!r} — takes a few minutes...")
    imagery = ingest_imagery(
        GEEClient(),
        preset.geometry,
        preset.event_date,
        preset.peril_type,
        minimum_valid_pixel_fraction=args.minimum_valid_pixel_fraction,
    )
    weather = ingest_weather(
        WeatherClient(),
        IMDClient(),
        preset.geometry,
        preset.event_date,
        peril_type_is_cloudburst_or_hailstorm=preset.peril_type in GPM_PERILS,
    )

    record = _build_record(preset, imagery, weather, started_at)
    _print_report(record)

    if not args.no_save:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        path = RUNS_DIR / f"{started_at:%Y%m%dT%H%M%S}-{args.preset}.json"
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(f"\n  written: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 4. Running it

```powershell
cd d:\barrel\evidence-intelligence-module\src
..\.venv\Scripts\python ..\prototype\run.py --preset chandrapur-flood
```

Each run prints a report and writes `prototype/runs/<timestamp>-<preset>.json` holding every figure
observed, including the absent ones. `--no-save` suppresses the artifact.

Expect **minutes, not seconds**: every `.getInfo()` is a blocking round trip, and one run issues two
optical composites, five historical composites, up to eighteen weather reductions, and possibly a
SAR pass — all sequential ([`technical-flow-diagrams.md` §5](technical-flow-diagrams.md)).

## 5. Reading a result

### The three fields that decide everything

| Field | Meaning |
|---|---|
| `imagery.usable` | The tier decision in one boolean. `True` means the field was seen; `False` means it was not, and no damage fraction will ever be computed for this request |
| `valid_pixel_fraction` | How much of the geometry was seen cloud- and shadow-free at least once. This is what separates "the field is damaged" from "we could not see the field". `None` means coverage could not be measured, which is disclosed as unknown rather than read as zero |
| `historical_years_returned` | How many of the five prior years produced a composite. Fewer years means a thinner baseline; zero means the DSI has no archive to normalise against |

### What absence means

Every `None` in the output is a claim, not a gap in the script:

- `post_event: None` — no optical composite cleared the coverage gate for the post-event window.
- `sar: null` with a flood peril — Sentinel-1 was attempted and returned nothing usable.
- `vh_drop_db: None` — the acquisitions covering this geometry were single-polarization. VH is
  never substituted by VV; cross-pol tracks canopy volume scattering and co-pol tracks surface
  ([gee_client.py:217](../src/evidence_intelligence/ingestion/gee_client.py#L217)).
- `historical_baseline: None` — no prior year returned a value, so `anomaly_score` is also `None`.
  An unmeasurable anomaly stays absent rather than becoming a measured zero.
- `station_corroboration: null` — `IMD_AWS_API_BASE_URL` is unset or the call failed. IMD
  corroborates and never substitutes, so this is a valid result, not a degraded one.

### Tier preview

`tier_preview` restates what step 3 would decide. Tier C is not a failure — the service still
generates a full weather-only package with the complete §65B field set and leaves the request
re-runnable.

## 6. Chandrapur on 10 July — what to expect, and why

The preset is chosen to be *informative*, not to succeed:

1. **Optical will probably fail.** 10 July is peak kharif monsoon in Vidarbha. The per-pixel SCL
   mask drops cloud, cirrus, and shadow before compositing, so persistent monsoon cover leaves few
   or no valid pixels over a ~4.8 ha extent. A `post_event` of `None` here is the system working.
2. **Peril alone decides whether that is recoverable.** `is_flood_compatible` is `True` only for
   `PerilType.FLOOD` ([schema.py:45](../src/evidence_intelligence/store/schema.py#L45)). The same
   geometry and date submitted as `unseasonal_rain` never attempts Sentinel-1 and lands in Tier C.
   Running `chandrapur-flood` and `chandrapur-unseasonal-rain` back to back isolates that branch
   with everything else held constant — the most useful single experiment here.
3. **The year is chosen deliberately.** 2025 rather than 2026: ERA5-Land and SMAP publish with real
   lag, so a recent event can return `None` for temperature and soil moisture, and the five-year
   baseline needs well-archived prior years. Verify current availability before changing it rather
   than assuming.
4. **Expect the phenology flag.** Kharif sowing in Vidarbha is typically June, so by 10 July the
   crop is early-vegetative and pre-event NDVI may sit below 0.2, firing
   `_phenology_sanity_check` ([imagery.py:59](../src/evidence_intelligence/ingestion/imagery.py#L59)).
   It flags and never blocks.
5. **The geometry is not a farm.** An arbitrary square at 19.950°N, 79.300°E. Its NDVI is a real
   measurement of real ground, and says nothing about any actual insured field.

## 7. Boundaries this prototype respects

- **It never sources its own inputs.** Geometry, event date, and peril are supplied as literals, the
  same way the API receives them from a caller. Field-boundary derivation and land records are
  permanently out of scope ([`constitution.md` §9.2](constitution.md)).
- **It does not widen the request surface.** Only `geometry`, `event_date`, `peril_type`, and an
  opaque `external_reference_id` — §9.1's data-minimisation rule.
- **It invents no figures.** Everything printed is either returned by ingestion or `None`. The tier
  preview is a restatement of a branch in `pipeline.py`, not a second opinion.
- **It writes nothing the service would write.** No `evidence_requests` row, no package, no object
  storage key. A prototype run leaves no trace in the evidence record.

## 8. Related documents

| Document | Relationship |
|---|---|
| [`technical-flow-diagrams.md`](technical-flow-diagrams.md) | The as-built flow this prototype covers the first two stages of. §5 and §6 detail the ingestion internals |
| [`evidence-flow-spec.md`](evidence-flow-spec.md) | The *intended* pipeline. Where it and the code disagree, the code is what this prototype exercises |
| [`constitution.md`](constitution.md) §9 | The scope boundaries §7 above respects |
| [`specs/001-evidence-generation-pipeline/quickstart.md`](../specs/001-evidence-generation-pipeline/quickstart.md) | Setup for the *full* service, including PostgreSQL and the real `POST`/poll flow |
