"""Records the Phase 0.4 characterization fixtures (tasks.md T0R-01).

Usage:
    python scripts/record_golden_fixtures.py            # write all fixtures
    python scripts/record_golden_fixtures.py --check    # report drift, write nothing

Run the recorder only as part of a task that is *supposed* to change output —
a flagged field flipping is the evidence that the task did what it claimed.
Re-recording to make a red suite go green defeats the entire purpose of the
harness; a diff in a field the scenario does not list as known-wrong is the bug.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.golden import (  # noqa: E402
    SCENARIOS,
    fixture_path,
    load_fixture,
    run_scenario,
    write_fixture,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report which fixtures would change without writing them",
    )
    args = parser.parse_args()

    drifted: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        for scenario in SCENARIOS:
            snapshot = run_scenario(scenario, Path(tmp))

            if args.check:
                if not fixture_path(scenario).exists():
                    print(f"MISSING  {scenario.name}")
                    drifted.append(scenario.name)
                elif load_fixture(scenario) != snapshot:
                    print(f"DRIFTED  {scenario.name}")
                    drifted.append(scenario.name)
                else:
                    print(f"ok       {scenario.name}")
                continue

            write_fixture(scenario, snapshot)
            print(f"recorded {scenario.name} ({len(scenario.known_wrong)} known-wrong field(s))")

    if args.check and drifted:
        print(f"\n{len(drifted)} fixture(s) differ from what the pipeline now produces.")
        print("If this was intended by the task you are on, re-run without --check and")
        print("review the diff against that scenario's known_wrong map. A diff in a")
        print("field that is not listed there is the bug.")
        return 1

    if not args.check:
        flagged = sum(len(s.known_wrong) for s in SCENARIOS)
        print(f"\n{len(SCENARIOS)} fixtures recorded, {flagged} field(s) flagged known-wrong.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
