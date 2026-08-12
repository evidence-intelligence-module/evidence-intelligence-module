"""Date helpers shared by the ingestion modules.

Both `ingestion/imagery.py` (via `gee_client.historical_composite`) and
`ingestion/weather.py` build multi-year historical baselines by taking the
same calendar window in each of the previous N years. `date.replace(year=...)`
raises `ValueError` for 29 February when the target year isn't a leap year,
which would fail every request whose analysis window happens to span a leap
day. `store/evidence_store.py`'s `retention_expiry_date` already guards this
exact case for retention dates; this is the same guard, shared, for the
ingestion side (tasks.md T0-12)."""

from __future__ import annotations

from datetime import date


def shift_years(value: date, years: int) -> date:
    """`value` moved by `years`, clamping 29 February to 28 February when the
    target year isn't a leap year — the same clamping direction
    `retention_expiry_date` uses, so the two never disagree about what
    "the same calendar day, N years away" means."""
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(month=2, day=28, year=value.year + years)
