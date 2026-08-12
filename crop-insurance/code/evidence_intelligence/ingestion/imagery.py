"""Imagery Ingestion (HLD §3). Pre/post-event acquisition, historical
baseline, SAR flood substitution, and the phenology sanity check
(Evidence-Flow-Spec.md §3-4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from evidence_intelligence.ingestion.gee_client import (
    GEEClient,
    ImageryComposite,
    SarComposite,
)
from evidence_intelligence.store.schema import PerilType

PRE_EVENT_WINDOW_DAYS = 30
POST_EVENT_WINDOW_DAYS = 15
HISTORICAL_BASELINE_YEARS = 5


@dataclass
class ImageryIngestionResult:
    pre_event: ImageryComposite | None
    post_event: ImageryComposite | None
    historical: list[ImageryComposite]
    sar: SarComposite | None
    usable: bool
    phenology_flag: str | None


def _phenology_sanity_check(pre_event: ImageryComposite | None) -> str | None:
    """Evidence-Flow-Spec.md §3: flagged, not blocked, if the pre-event NDVI
    doesn't plausibly indicate a standing crop before the claimed event."""
    if pre_event is None or pre_event.index_value is None:
        return None
    if pre_event.index_value < 0.2:
        return (
            "pre-event NDVI is low for the claimed crop calendar window; "
            "a crop may not have plausibly been standing before the claimed event"
        )
    return None


def ingest_imagery(
    client: GEEClient,
    geometry: dict,
    event_date: date,
    peril_type: PerilType,
) -> ImageryIngestionResult:
    """FR-005/FR-006/FR-007: pre/post-event windows, SAR substitution for
    flood-compatible/cloud-blocked cases, and a 5-year historical baseline."""
    pre_start = event_date - timedelta(days=PRE_EVENT_WINDOW_DAYS)
    pre_end = event_date - timedelta(days=1)
    post_start = event_date
    post_end = event_date + timedelta(days=POST_EVENT_WINDOW_DAYS)

    pre_event = client.optical_composite(geometry, pre_start, pre_end)
    post_event = client.optical_composite(geometry, post_start, post_end)

    # FR-006: SAR substitutes only for flood-compatible perils — radar
    # flood-extent detection isn't a meaningful signal for e.g. drought or
    # heatwave, which instead fall through to the weather-only path (FR-022).
    sar: SarComposite | None = None
    usable = post_event is not None
    if post_event is None and peril_type.is_flood_compatible:
        sar = client.sar_composite(geometry, pre_end, post_start, post_end)
        usable = sar is not None

    historical = client.historical_composite(
        geometry, pre_start, pre_end, years=HISTORICAL_BASELINE_YEARS
    )

    return ImageryIngestionResult(
        pre_event=pre_event,
        post_event=post_event,
        historical=historical,
        sar=sar,
        usable=usable,
        phenology_flag=_phenology_sanity_check(pre_event),
    )
