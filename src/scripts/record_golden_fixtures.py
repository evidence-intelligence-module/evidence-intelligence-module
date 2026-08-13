"""Records the Phase 0.4 characterization fixtures (tasks.md T0R-01).

Usage:
    python scripts/record_golden_fixtures.py            # write all fixtures
    python scripts/record_golden_fixtures.py --check    # report drift, write nothing

Run the recorder only as part of a task that is *supposed* to change output —
a `known-wrong` fixture flipping is the evidence that the task did what it
claimed. Re-recording to make a red suite go green defeats the entire purpose
of the harness; if a `pinned` fixture drifts, the change is the bug.
"""

from __future__ import annotations

import argparse
import json
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
                    print(f"MISSING  {scenario.name} [{scenario.label}]")
                    drifted.append(scenario.name)
                elif load_fixture(scenario) != snapshot:
                    print(f"DRIFTED  {scenario.name} [{scenario.label}]")
                    drifted.append(scenario.name)
                else:
                    print(f"ok       {scenario.name} [{scenario.label}]")
                continue

            write_fixture(scenario, snapshot)
            print(f"recorded {scenario.name} [{scenario.label}] -> {fixture_path(scenario).name}")

    if args.check and drifted:
        print(f"\n{len(drifted)} fixture(s) differ from what the pipeline now produces.")
        print("If this was intended by the task you are on, re-run without --check and")
        print("review the diff. If a `pinned` fixture is listed, the change is the bug.")
        return 1

    if not args.check:
        summary = json.dumps(
            {s.label: sum(1 for x in SCENARIOS if x.label == s.label) for s in SCENARIOS},
            sort_keys=True,
        )
        print(f"\n{len(SCENARIOS)} fixtures recorded: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
