"""Component 3 — Crop Simulation Model Assimilation, advanced tier
(Modeling-Approach.md §4). Gated behind `settings.csm_high_scrutiny_enabled`,
defaulting to disabled.

**Do not enable this tier yet.** `run()` below is a placeholder, not an
implementation: it echoes back the `damage_signal` it was handed, which at
`pipeline.py`'s call site is `ndvi_drop` — the same quantity already driving
Component 2's feature vector. `models/ensemble.py` combines components by
confidence-weighted average, so agreement between them reads as
corroboration; adding a component that restates another's input therefore
manufactures corroboration in a figure that ends up in a legal evidence
package. The 0.4 calibration confidence bounds how much, not whether.

Two separate things are outstanding, in this order:
1. Implement Component 3 — wire a calibrated WOFOST/InfoCrop run with
   remote-sensing-assimilated LAI/soil-moisture state (Modeling-Approach.md §4).
2. Then define what makes a request "high-scrutiny" — see
   specs/001-evidence-generation-pipeline/issue/open query - CSM high-scrutiny
   trigger criteria (FR-011).md, reframed 2026-08-13.

An earlier version of this docstring claimed the module was "a real, callable
implementation" with only the trigger unresolved. That was wrong, and it
invited enabling the flag."""

from __future__ import annotations

from dataclasses import dataclass

METHODOLOGY_VERSION = "csm-assimilation-wofost-v1"


@dataclass
class CsmResult:
    damage_fraction: float
    calibration_confidence: float


def run(geometry: dict, damage_signal: float) -> CsmResult:
    """Placeholder for a WOFOST/InfoCrop run with remote-sensing-assimilated
    LAI/soil-moisture state (Modeling-Approach.md §4). A real deployment
    wires this to a calibrated crop simulation model; until then this
    reflects the same damage_signal the other components observed, at a
    reduced confidence to avoid overstating this tier's current maturity."""
    return CsmResult(
        damage_fraction=max(0.0, min(1.0, damage_signal)),
        calibration_confidence=0.4,
    )
