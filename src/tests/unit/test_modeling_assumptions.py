"""Disclosure of the two modeling assumptions that shape reported figures
without being derived from a request's own data (tasks.md T0-17, T0-18).

Both were live in shipped output. Neither is a wrong *number* exactly — the
problem is that a reader could not tell they were assumptions at all:

- Yield loss is `damage_fraction × Harvest Index`, with one Harvest Index
  applied to every crop, against `modeling-approach.md` §2's explicit
  commitment to per-variety published values "clearly labeled as a modeling
  assumption".
- `negligible`/`minor`/`moderate`/`severe` come from cut points that appear
  nowhere in `documents/`, and `yestech_manual_2023.md` defines no
  transferable severity banding.

A disclosed assumption can be discounted by whoever reads the package. An
undisclosed one is indistinguishable from a measurement."""

from __future__ import annotations

import pytest

from evidence_intelligence.config import DEFAULT_DAMAGE_CLASSIFICATION_BANDS, _parse_bands
from evidence_intelligence.models.semi_physical import CropParameters
from evidence_intelligence.pipeline import (
    _assumed_harvest_index,
    _classify,
    _modeling_assumption_statements,
)

BANDS = DEFAULT_DAMAGE_CLASSIFICATION_BANDS


# -- T0-17: banding is configurable, and behaviour is unchanged --------------


@pytest.mark.parametrize(
    ("fraction", "expected"),
    [
        (0.0, "negligible"),
        (0.09, "negligible"),
        (0.1, "minor"),
        (0.32, "minor"),
        (0.33, "moderate"),
        (0.65, "moderate"),
        (0.66, "severe"),
        (1.0, "severe"),
    ],
)
def test_default_bands_reproduce_the_previous_behaviour(fraction, expected):
    """These bands ship in packages already issued, so making them
    configurable must not silently reclassify anything."""
    assert _classify(fraction, BANDS) == expected


def test_bands_are_configurable():
    assert _classify(0.5, (0.6, 0.7, 0.8)) == "negligible"
    assert _classify(0.5, (0.1, 0.2, 0.3)) == "severe"


def test_band_parsing_rejects_non_ascending_or_wrong_length():
    """A malformed banding would reorder severity labels silently."""
    assert _parse_bands("0.2,0.4,0.8") == (0.2, 0.4, 0.8)
    assert _parse_bands(None) == BANDS
    assert _parse_bands("") == BANDS
    with pytest.raises(ValueError):
        _parse_bands("0.6,0.3,0.9")
    with pytest.raises(ValueError):
        _parse_bands("0.1,0.5")


# -- T0-18: one Harvest Index, sourced from one place ------------------------


def test_harvest_index_comes_from_crop_parameters_not_a_second_literal():
    """Components 1 and 2 previously carried the same 0.4 in two unconnected
    places, free to drift apart."""
    assert _assumed_harvest_index() == CropParameters().harvest_index


# -- both must reach the package --------------------------------------------


def test_harvest_index_assumption_is_stated():
    statements = " ".join(_modeling_assumption_statements(BANDS))
    assert "Harvest Index" in statements
    assert str(_assumed_harvest_index()) in statements
    assert "modeling assumption" in statements
    assert "uniformly to all crops" in statements


def test_banding_is_stated_as_convention_not_standard():
    statements = " ".join(_modeling_assumption_statements(BANDS))
    assert "presentational convention" in statements
    assert "not a sourced standard" in statements


def test_stated_bands_track_the_configured_ones():
    """The disclosure must describe the banding actually in force, or it is
    worse than none at all."""
    statements = " ".join(_modeling_assumption_statements((0.2, 0.5, 0.9)))
    assert "0.2" in statements and "0.5" in statements and "0.9" in statements
    assert "0.33" not in statements
