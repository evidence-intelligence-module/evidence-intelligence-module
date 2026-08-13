"""Contract tests for the observation layer (tasks.md T0R-02).

These test the *rule*, not the arithmetic: an input that was not measured must
stay unmeasured all the way through, and must carry a reason. The four defects
this module exists to prevent (T0-02, T0-03, T0-04, the DSI weight collapse)
were all violations of that rule at a call site, so it is the rule that needs
covering.
"""

from __future__ import annotations

import pytest

from evidence_intelligence.observation import (
    Absent,
    FieldObservations,
    Observation,
    ObservationBuilder,
    ndvi_to_fapar,
)


def _built(**kwargs) -> FieldObservations:
    builder = ObservationBuilder()
    for name, value in kwargs.items():
        builder.record(name, value, source="test", absent_reason=f"{name} not measured")
    return builder.build()


def test_absent_signal_reads_as_none_not_zero():
    """The whole point: `None` is not `0.0`. A model's 0.0 means "no deviation
    observed", which is a claim about the field, not about our coverage."""
    obs = _built(measured=0.42, unmeasured=None)
    assert obs.value("measured") == 0.42
    assert obs.value("unmeasured") is None


def test_a_genuine_zero_is_preserved_not_confused_with_absence():
    """The converse, which is just as important: a measured zero is a real
    observation and must not be treated as missing."""
    obs = _built(genuine_zero=0.0)
    assert obs.value("genuine_zero") == 0.0
    assert obs.is_present("genuine_zero") is True
    assert obs.absent_reason("genuine_zero") is None


def test_absence_carries_a_reason():
    """"Missing" and "missing because no post-event composite cleared the cloud
    gate" are different claims in an evidence package."""
    obs = _built(unmeasured=None)
    assert obs.absent_reason("unmeasured") == "unmeasured not measured"


def test_never_attempted_is_distinguishable_from_recorded_absence():
    obs = _built(unmeasured=None)
    assert obs.absent_reason("nobody_asked") == "never attempted"
    assert obs.value("nobody_asked") is None


def test_present_omits_absent_signals_rather_than_defaulting_them():
    """This is what a feature vector is built from — T0-04 was this going
    wrong, diluting every estimate toward zero with unmeasured features."""
    obs = _built(a=1.0, b=None, c=3.0)
    assert obs.present(("a", "b", "c")) == {"a": 1.0, "c": 3.0}


def test_there_is_no_accessor_that_can_silently_yield_a_default():
    """The enforcement mechanism, given ruff runs E/F/I/UP with no type checker
    (pyproject.toml). If either of these ever exists, a caller can turn an
    unmeasured signal into a number without writing the number down."""
    obs = _built(a=1.0)
    assert not hasattr(obs, "get")
    with pytest.raises(TypeError):
        obs["a"]


def test_empty_and_absent_history_both_read_as_none():
    """Treating "no archive" as "zero variance" is what collapsed the DSI's
    entropy weighting onto a single indicator."""
    builder = ObservationBuilder()
    builder.record_history("has_archive", [0.1, 0.2], absent_reason="n/a")
    builder.record_history("empty_archive", [], absent_reason="n/a")
    builder.record_history("no_archive", None, absent_reason="no source wired")
    obs = builder.build()

    assert obs.history("has_archive") == (0.1, 0.2)
    assert obs.history("empty_archive") is None
    assert obs.history("no_archive") is None
    assert obs.history_absent_reason("no_archive") == "no source wired"
    assert obs.history_absent_reason("empty_archive") == "archive returned no usable composites"


def test_observation_records_provenance_for_the_manifest():
    """A reader of a §65B package must be able to tell a reading from a
    substituted default, so the source string travels with the value."""
    builder = ObservationBuilder()
    builder.record("m", 1.0, source="Sentinel-2 SR Harmonized", absent_reason="n/a")
    obs = builder.build()
    assert obs.source("m") == "Sentinel-2 SR Harmonized"
    assert obs.source("absent_one") is None


def test_ndvi_to_fapar_propagates_absence():
    """T0-02: substituting 0.0 made "we could not see the field"
    indistinguishable from "no green vegetation left", i.e. total damage."""
    assert ndvi_to_fapar(None) is None
    assert ndvi_to_fapar(0.75) == pytest.approx(0.762)
    assert ndvi_to_fapar(0.0) == 0.0  # clipped, not negative


def test_signals_are_one_of_exactly_two_states():
    builder = ObservationBuilder()
    builder.record("a", 1.0, source="s", absent_reason="r")
    builder.record("b", None, source="s", absent_reason="r")
    obs = builder.build()
    assert isinstance(obs.signals["a"], Observation)
    assert isinstance(obs.signals["b"], Absent)
