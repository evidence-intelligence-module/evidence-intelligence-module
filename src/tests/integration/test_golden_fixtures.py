"""Characterization tests for the Phase 0.4 decomposition (tasks.md T0R-01).

Each scenario's full observable pipeline output is compared against a recorded
snapshot. This is the safety net every later T0R task's gate is checked
against — see `specs/002-satellite-evidence-parity/pipeline-decomposition-design.md`
§8.1 for why a change-detector rather than a correctness oracle.

Labels are per-field: every recorded value is pinned unless it appears in the
scenario's `known_wrong` map. See `tests/golden.py` for why that is not the
same as the per-scenario labelling this harness started with.
"""

from __future__ import annotations

import pytest

from tests.golden import (
    SCENARIOS,
    fixture_path,
    load_fixture,
    path_exists,
    run_scenario,
)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_pipeline_output_matches_recorded_fixture(scenario, tmp_path):
    """Any diff is a behaviour change. Outside the `known_wrong` map that is a
    regression; inside it, it is the named task doing its job, and the fixture
    is re-recorded as part of that task."""
    assert fixture_path(scenario).exists(), (
        f"no recorded fixture for {scenario.name} — run "
        f"`python scripts/record_golden_fixtures.py`"
    )
    assert run_scenario(scenario, tmp_path) == load_fixture(scenario)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_known_wrong_paths_still_resolve(scenario):
    """A stale excuse is worse than none: if a `known_wrong` path no longer
    exists in the snapshot, the entry is describing a value that is gone, and
    nobody will notice the map has rotted."""
    recorded = load_fixture(scenario)
    for path in scenario.known_wrong:
        assert path_exists(recorded, path), (
            f"{scenario.name}: known_wrong path {path!r} does not resolve in the "
            "recorded snapshot — remove the entry or fix the path"
        )


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_every_scenario_declares_purpose_and_reasons(scenario):
    """A fixture nobody explained is a fixture nobody will know how to treat
    when it flips."""
    assert scenario.purpose.strip()
    for path, reason in scenario.known_wrong.items():
        assert reason.strip(), f"{scenario.name}: {path} has an empty reason"

    recorded = load_fixture(scenario)
    assert recorded["_purpose"] == scenario.purpose
    assert recorded["_known_wrong"] == dict(scenario.known_wrong)


def test_pipeline_is_deterministic_across_runs(tmp_path):
    """The harness is only meaningful if an unchanged pipeline produces an
    unchanged snapshot — otherwise every later gate reports false drift."""
    scenario = next(s for s in SCENARIOS if s.name == "healthy_hailstorm")
    assert run_scenario(scenario, tmp_path) == run_scenario(scenario, tmp_path)


def test_causation_is_flagged_wrong_on_every_scenario():
    """Not a style check — a regression guard on the harness itself.

    The first version of this file labelled whole scenarios, so five of eight
    were `pinned` while recording a causation score that is fabricated on every
    path. If a scenario is ever added without inheriting CAUSATION_KNOWN_WRONG,
    it silently re-pins that figure as correct.
    """
    for scenario in SCENARIOS:
        assert "package_json.causation_confidence_score" in scenario.known_wrong, (
            f"{scenario.name} does not flag its causation score as known-wrong; "
            "every path fabricates it until T0-06 lands"
        )
