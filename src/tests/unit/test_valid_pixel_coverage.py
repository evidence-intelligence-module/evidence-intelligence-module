"""Coverage-gating tests for per-pixel cloud/shadow masking (tasks.md T0-07).

The defect: `optical_composite` filtered whole *scenes* on
`CLOUDY_PIXEL_PERCENTAGE < 20` and then composited every pixel of the scenes
that passed. A scene 19% cloudy overall can be entirely clouded over one
0.16 ha field, and cloud over vegetation depresses NDVI — so the pipeline
reported obscured ground indistinguishably from crop loss, with no figure
anywhere saying how much of the field had actually been seen.

Masking itself runs server-side in Earth Engine and cannot be exercised
without live credentials. The *decision* it feeds — is this composite backed
by enough of the field to rely on — is a pure function precisely so it can be
tested here. That separation is the point: its absence is why the gap
survived a green suite."""

from __future__ import annotations

from datetime import date

import pytest

from evidence_intelligence.ingestion.gee_client import ImageryComposite
from evidence_intelligence.ingestion.imagery import has_sufficient_coverage


def composite(fraction: float | None) -> ImageryComposite:
    return ImageryComposite(
        source_dataset="Sentinel-2 SR Harmonized",
        source_version="COPERNICUS/S2_SR_HARMONIZED",
        acquisition_date=date(2026, 7, 20),
        index_value=0.42,
        valid_pixel_fraction=fraction,
    )


# -- unset threshold: measure and disclose, never suppress -------------------


@pytest.mark.parametrize("fraction", [0.0, 0.05, 0.5, 1.0, None])
def test_unset_threshold_never_suppresses_evidence(fraction):
    """No sourced value exists for how much of a field must be visible, so the
    default must not silently discard evidence. The fraction is still measured
    and disclosed in the package — it just doesn't gate."""
    assert has_sufficient_coverage(composite(fraction), None) is True


# -- configured threshold ----------------------------------------------------


def test_coverage_at_or_above_threshold_is_sufficient():
    assert has_sufficient_coverage(composite(0.80), 0.80) is True
    assert has_sufficient_coverage(composite(0.95), 0.80) is True


def test_coverage_below_threshold_is_insufficient():
    """The case the whole task exists for: a field almost entirely under cloud
    whose composite would otherwise have supplied a confident NDVI value."""
    assert has_sufficient_coverage(composite(0.12), 0.80) is False


def test_zero_coverage_is_insufficient():
    assert has_sufficient_coverage(composite(0.0), 0.80) is False


# -- absence handling --------------------------------------------------------


def test_missing_composite_is_insufficient():
    assert has_sufficient_coverage(None, 0.80) is False
    assert has_sufficient_coverage(None, None) is False


def test_unmeasured_coverage_is_not_treated_as_zero_coverage():
    """"We could not measure coverage" is not "there was no coverage". Reading
    an unknown as zero would discard usable evidence on a missing measurement,
    against the module's never-fail-silently posture — it is disclosed in the
    accuracy statement as unmeasured instead."""
    assert has_sufficient_coverage(composite(None), 0.80) is True
