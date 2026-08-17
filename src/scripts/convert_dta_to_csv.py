"""Convert Stata `.dta` files into CSV so they can be fed to the Component 2 pipeline.

Supplier datasets from Dataverse arrive as a zip of Stata files. This script reads
either a zip archive or a single `.dta` file and writes one CSV per Stata table,
named after the source member (e.g. `002_pbi_sitelevel.dta` -> `002_pbi_sitelevel.csv`).

Stata value labels are expanded to their text form so the CSV is human readable,
and Stata's missing values become empty CSV cells.

Usage:
    python scripts/convert_dta_to_csv.py \
        --input data/component2/raw/dataverse_files.zip \
        --output-dir data/component2/raw
"""

from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

# pandas is only needed for this one-off conversion utility, so it lives in the
# optional `data` extra rather than the runtime dependencies.
try:
    import pandas as pd
except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "This script needs pandas. Install it with:\n"
        "    pip install -e '.[data]'\n"
        "or:\n"
        "    pip install pandas"
    ) from exc


def _read_stata(payload: bytes) -> pd.DataFrame:
    return pd.read_stata(io.BytesIO(payload), convert_categoricals=True)


def _iter_stata_members(source: Path) -> list[tuple[str, bytes]]:
    """Return (stem, raw bytes) for every Stata table in `source`."""
    if source.suffix.lower() == ".dta":
        return [(source.stem, source.read_bytes())]

    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            members = [n for n in archive.namelist() if n.lower().endswith(".dta")]
            if not members:
                raise SystemExit(f"No .dta files found inside {source}")
            return [(Path(n).stem, archive.read(n)) for n in sorted(members)]

    raise SystemExit(f"Expected a .zip or .dta file, got {source}")


def convert(source: Path, output_dir: Path) -> list[tuple[Path, int, int]]:
    """Write one CSV per Stata table. Returns (path, rows, columns) per output."""
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[tuple[Path, int, int]] = []
    for stem, payload in _iter_stata_members(source):
        frame = _read_stata(payload)
        destination = output_dir / f"{stem}.csv"
        frame.to_csv(destination, index=False)
        results.append((destination, len(frame), len(frame.columns)))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to a .zip of Stata files, or a single .dta file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory that will receive the converted CSV file(s)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}")

    for destination, rows, columns in convert(args.input, args.output_dir):
        print(f"Wrote {rows:,} row(s) x {columns} column(s) to {destination}")


if __name__ == "__main__":
    main()
