"""Characterization tests for the Phase 0.4 decomposition (tasks.md T0R-01).

Each scenario's full observable pipeline output is compared against a recorded
snapshot. This is the safety net every later T0R task's gate is checked
against — see `specs/002-satellite-evidence-parity/pipeline-decomposition-design.md`
§8.1 for why a change-detector rather than a correctness oracle.
"""

from __future__ import annotations

import pytest

from tests.golden import KNOWN_WRONG, PINNED, SCENARIOS, fixture_path, load_fixture, run_scenario


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_pipeline_output_matches_recorded_fixture(scenario, tmp_path):
    """Any diff here is a behaviour change. For a `pinned` scenario that is a
    regression; for a `known-wrong` one it is the task doing its job, and the
    fixture is re-recorded as part of that task."""
    assert fixture_path(scenario).exists(), (
        f"no recorded fixture for {scenario.name} — run "
        f"`python scripts/record_golden_fixtures.py`"
    )
    assert run_scenario(scenario, tmp_path) == load_fixture(scenario)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_every_fixture_declares_a_label_and_reason(scenario):
    """A fixture nobody labelled is a fixture nobody will know how to treat
    when it flips."""
    assert scenario.label in (PINNED, KNOWN_WRONG)
    assert scenario.reason.strip()

    recorded = load_fixture(scenario)
    assert recorded["_label"] == scenario.label
    assert recorded["_label_reason"] == scenario.reason


def test_pipeline_is_deterministic_across_runs(tmp_path):
    """The harness is only meaningful if an unchanged pipeline produces an
    unchanged snapshot — otherwise every later gate reports false drift."""
    scenario = next(s for s in SCENARIOS if s.name == "healthy_hailstorm")
    assert run_scenario(scenario, tmp_path) == run_scenario(scenario, tmp_path)


def test_both_labels_are_represented():
    """If nothing is `known-wrong`, the design's expected flips were not
    captured; if nothing is `pinned`, nothing is actually protected."""
    labels = {s.label for s in SCENARIOS}
    assert labels == {PINNED, KNOWN_WRONG}
