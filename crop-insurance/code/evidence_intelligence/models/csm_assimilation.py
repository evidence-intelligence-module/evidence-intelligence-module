"""Component 3 — Crop Simulation Model Assimilation, advanced tier
(Modeling-Approach.md §4). Gated behind `settings.csm_high_scrutiny_enabled`,
defaulting to disabled: the trigger criteria for what counts as a
"high-scrutiny" request is not yet defined by any source document — see
specs/001-evidence-generation-pipeline/issue/open query - CSM high-scrutiny
trigger criteria (FR-011).md. This module is a real, callable implementation;
only the decision of *when* to call it is unresolved."""

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
