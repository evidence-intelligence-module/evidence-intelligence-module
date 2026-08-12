from datetime import date

from evidence_intelligence.store.evidence_store import retention_expiry_date


def test_retention_is_ten_years_from_generation():
    """Constitution §7 / FR-029."""
    expiry = retention_expiry_date(date(2026, 8, 12))
    assert expiry == date(2036, 8, 12)


def test_retention_handles_leap_day():
    expiry = retention_expiry_date(date(2028, 2, 29))
    assert expiry == date(2038, 2, 28)
