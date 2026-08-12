"""Component 1 — Semi-Physical Damage Model (Modeling-Approach.md §2).
RUE-chain expected-vs-observed biomass deviation, adapted from YES-TECH's
absolute-yield RUE model to a damage-detection comparison.

Harvest Index is sourced from published crop-variety reference values, never
from CCE data (Constitution §4) — `CropParameters` below is a placeholder for
that reference table, not a locally-measured constant."""

from __future__ import annotations

from dataclasses import dataclass, field

METHODOLOGY_VERSION = "semi-physical-v1"

# A unit-sanity bound, not an agronomic threshold: no 2m air temperature over
# an Indian field is outside this range in any unit this model accepts, so a
# reading outside it means the caller supplied something other than celsius
# (ERA5-Land serves kelvin, ~300). Distinguished from `CropParameters.temp_max_c`,
# which is a real agronomic limit a genuine heatwave can legitimately exceed —
# the model must keep returning zero biomass in that case, but must not report
# high calibration confidence when the input was never celsius at all
# (tasks.md T0-01).
TEMPERATURE_UNIT_SANITY_RANGE_C = (-90.0, 60.0)


@dataclass(frozen=True)
class CropParameters:
    """Published crop-variety reference values (Modeling-Approach.md §2),
    not CCE-derived. Placeholder defaults — a real deployment populates this
    from an agronomic reference table per crop/region."""

    rue_max_g_per_mj: float = 2.5
    harvest_index: float = 0.4
    temp_min_c: float = 8.0
    temp_optimum_c: float = 25.0
    temp_max_c: float = 40.0
    lswi_max: float = 0.5


@dataclass
class SemiPhysicalResult:
    expected_biomass: float
    observed_biomass: float
    damage_fraction: float
    calibration_confidence: float
    input_warnings: list[str] = field(default_factory=list)


def _water_stress_scalar(lswi: float, lswi_max: float) -> float:
    return (1 + lswi) / (1 + lswi_max)


def _temperature_stress_scalar(temp_c: float, params: CropParameters) -> float:
    """Bounded 0-1 function of observed temperature relative to the crop's
    min/optimum/max thresholds (Modeling-Approach.md §2)."""
    if temp_c <= params.temp_min_c or temp_c >= params.temp_max_c:
        return 0.0
    if temp_c <= params.temp_optimum_c:
        return (temp_c - params.temp_min_c) / (params.temp_optimum_c - params.temp_min_c)
    return (params.temp_max_c - temp_c) / (params.temp_max_c - params.temp_optimum_c)


def _biomass(
    par_mj: float,
    fapar: float,
    lswi: float,
    temp_c: float,
    params: CropParameters,
) -> float:
    water_stress = _water_stress_scalar(lswi, params.lswi_max)
    temp_stress = _temperature_stress_scalar(temp_c, params)
    return params.rue_max_g_per_mj * par_mj * fapar * water_stress * temp_stress


def run(
    pre_event_insolation_mj: float,
    pre_event_fapar: float,
    pre_event_lswi: float,
    pre_event_temp_c: float,
    post_event_insolation_mj: float,
    post_event_fapar: float,
    post_event_lswi: float,
    post_event_temp_c: float,
    params: CropParameters | None = None,
) -> SemiPhysicalResult:
    """Expected biomass (pre-event trajectory, projected forward under
    unchanged conditions) vs. observed post-event biomass — the deviation is
    the damage signal (Modeling-Approach.md §2)."""
    params = params or CropParameters()

    expected = _biomass(
        pre_event_insolation_mj, pre_event_fapar, pre_event_lswi, pre_event_temp_c, params
    )
    observed = _biomass(
        post_event_insolation_mj, post_event_fapar, post_event_lswi, post_event_temp_c, params
    )

    damage_fraction = 0.0
    if expected > 0:
        damage_fraction = max(0.0, min(1.0, (expected - observed) / expected))

    # Calibration confidence degrades if inputs sit outside the physically
    # plausible fAPAR/LSWI range this model was parameterized against, or
    # outside the range any celsius reading could occupy — the latter means
    # the caller supplied the wrong unit, and reporting 0.85 confidence on a
    # result derived from it would be a fabricated accuracy figure.
    warnings: list[str] = []
    if not (0.0 <= pre_event_fapar <= 1.0 and 0.0 <= post_event_fapar <= 1.0):
        warnings.append("fAPAR input outside the physically plausible [0, 1] range")

    lo, hi = TEMPERATURE_UNIT_SANITY_RANGE_C
    for label, temp_c in (("pre-event", pre_event_temp_c), ("post-event", post_event_temp_c)):
        if not lo <= temp_c <= hi:
            warnings.append(
                f"{label} temperature {temp_c} is outside the range any celsius reading "
                f"can occupy ([{lo}, {hi}]) — check the source's unit"
            )

    calibration_confidence = 0.85 if not warnings else 0.5

    return SemiPhysicalResult(
        expected_biomass=expected,
        observed_biomass=observed,
        damage_fraction=damage_fraction,
        calibration_confidence=calibration_confidence,
        input_warnings=warnings,
    )
