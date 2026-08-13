"""Raw ingestion bundles -> named, present-or-absent signals (tasks.md T0R-02).

The single place where "what did we actually measure for this field?" is
decided. Everything downstream — the damage estimators, the DSI, the causation
engine — reads `FieldObservations` and never a raw bundle, so that question has
one answer rather than six call sites each re-deriving it from
`imagery.post_event is None`.

**Why this module exists.** Four defects have been found in this pipeline with
one shape: an input that was never measured being read as a measured value
(`T0-02` post-event NDVI -> `0.0`; `T0-03` LSWI -> the NDVI drop; `T0-04` 11 of
17 features -> `0.0`; the DSI weight collapse -> five archives silently
zero-weighted). Each was fixed at its call site with a conditional and a
comment. The discipline that prevents the class was a convention repeated
across a 761-line `pipeline.py`, enforced by nothing.

Here it is enforced by the API: `Absent` carries a reason, `value()` returns
`float | None`, and there is deliberately **no `get(name, default)` and no
`__getitem__`**. A caller that wants a fallback has to write it visibly, where
a reviewer will see it. `pyproject.toml` runs ruff `E`/`F`/`I`/`UP` with no type
checker, so the shape of this API is the enforcement — not annotations.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

# -- Signal names -------------------------------------------------------------
# Constants rather than string literals at call sites: a typo in a literal reads
# as an absent signal, which this module is specifically built to make loud.

NDVI_DEVIATION = "ndvi_deviation"
FAPAR_DEVIATION = "fapar_deviation"
RAINFALL_ANOMALY = "rainfall_anomaly"
TEMPERATURE_ANOMALY = "temperature_anomaly"
SOIL_MOISTURE_DEVIATION = "soil_moisture_deviation"
VH_VV_BACKSCATTER_DEVIATION = "vh_vv_backscatter_deviation"
SAR_VH_BACKSCATTER_DEVIATION = "sar_vh_backscatter_deviation"
LSWI_DEVIATION = "lswi_deviation"
WEATHER_ANOMALY_MAGNITUDE = "weather_anomaly_magnitude"

PRE_EVENT_NDVI = "pre_event_ndvi"
POST_EVENT_NDVI = "post_event_ndvi"
PRE_EVENT_FAPAR = "pre_event_fapar"
POST_EVENT_FAPAR = "post_event_fapar"
PRE_EVENT_LSWI = "pre_event_lswi"
POST_EVENT_LSWI = "post_event_lswi"
PRE_EVENT_TEMP_C = "pre_event_temp_c"
POST_EVENT_TEMP_C = "post_event_temp_c"
PRE_EVENT_INSOLATION_MJ = "pre_event_insolation_mj"
POST_EVENT_INSOLATION_MJ = "post_event_insolation_mj"


@dataclass(frozen=True)
class Observation:
    """A signal that was measured. Existing at all means it was observed."""

    value: float
    source: str
    """Provenance, e.g. "Sentinel-2 SR Harmonized" — or a statement that this
    value is a substituted default rather than a measurement. Read by the
    evidence-inputs manifest, so it belongs in a §65B package: a reader must be
    able to tell a reading from a stand-in."""


@dataclass(frozen=True)
class Absent:
    """A signal that was not measured, and why.

    The reason is required. "Missing" and "missing because no post-event
    composite cleared the cloud gate" are different claims in an evidence
    package, and only the second one is auditable.
    """

    reason: str


@dataclass(frozen=True)
class FieldObservations:
    signals: Mapping[str, Observation | Absent]
    histories: Mapping[str, tuple[float, ...] | Absent]
    phenology_flag: str | None = None

    # -- Accessors. Note what is absent: no `get(name, default)`, no
    # `__getitem__`. Both would let an unmeasured signal become a number
    # without anyone writing the number down.

    def value(self, name: str) -> float | None:
        """The measured value, or `None` if absent or unknown."""
        signal = self.signals.get(name)
        return signal.value if isinstance(signal, Observation) else None

    def source(self, name: str) -> str | None:
        signal = self.signals.get(name)
        return signal.source if isinstance(signal, Observation) else None

    def absent_reason(self, name: str) -> str | None:
        """Why a signal is missing, or `None` if it is present."""
        signal = self.signals.get(name)
        if isinstance(signal, Absent):
            return signal.reason
        return None if isinstance(signal, Observation) else "never attempted"

    def is_present(self, name: str) -> bool:
        return isinstance(self.signals.get(name), Observation)

    def present(self, names: Iterable[str]) -> dict[str, float]:
        """Only the measured signals among `names`.

        This is what a model's feature vector is built from. A signal that could
        not be measured is omitted rather than defaulted, because a model's
        `0.0` means "no deviation observed", which is a claim about the field
        rather than about our coverage of it (`T0-03`/`T0-04`).
        """
        return {name: self.value(name) for name in names if self.is_present(name)}

    def history(self, name: str) -> tuple[float, ...] | None:
        """The historical archive for an indicator, or `None` if there is none.

        An empty archive and an absent one are the same thing here, and both
        return `None` — an indicator with no history cannot be normalized
        against history, and treating "no archive" as "zero variance" is what
        collapsed the DSI's entropy weighting onto a single indicator.
        """
        archive = self.histories.get(name)
        return archive if isinstance(archive, tuple) and archive else None

    def history_absent_reason(self, name: str) -> str | None:
        archive = self.histories.get(name)
        if isinstance(archive, Absent):
            return archive.reason
        if isinstance(archive, tuple) and not archive:
            return "archive returned no usable composites"
        return None if isinstance(archive, tuple) else "never attempted"


class ObservationBuilder:
    """Accumulates signals. `record` takes both a source and an absent-reason so
    the caller has to have decided what each case means before writing either."""

    def __init__(self) -> None:
        self._signals: dict[str, Observation | Absent] = {}
        self._histories: dict[str, tuple[float, ...] | Absent] = {}

    def record(
        self, name: str, value: float | None, *, source: str, absent_reason: str
    ) -> None:
        """`None` is recorded as `Absent`, never coerced to a number."""
        self._signals[name] = (
            Absent(absent_reason) if value is None else Observation(float(value), source)
        )

    def record_history(
        self, name: str, values: Sequence[float] | None, *, absent_reason: str
    ) -> None:
        self._histories[name] = (
            Absent(absent_reason) if values is None else tuple(float(v) for v in values)
        )

    def build(self, phenology_flag: str | None = None) -> FieldObservations:
        return FieldObservations(
            signals=dict(self._signals),
            histories=dict(self._histories),
            phenology_flag=phenology_flag,
        )


# -- Derivations --------------------------------------------------------------

FALLBACK_TEMPERATURE_C = 25.0
"""Used only when ERA5-Land returns no reading for the window at all. Kept as an
explicit `is None` check rather than `or`, since 0 °C is a valid temperature that
`or` would silently replace with this default."""

INSOLATION_PROXY_MJ = 18.0
"""No dedicated insolation feed is wired yet — a fixed regional-average proxy,
disclosed as a known limitation (FR-019)."""

NO_OPTICAL_PAIR = "no usable pre/post optical pair in the analysis window"


def ndvi_to_fapar(ndvi: float | None) -> float | None:
    """`None` in, `None` out — an absent NDVI has no fAPAR, and substituting 0.0
    made "we could not see the field" indistinguishable from "the field has no
    green vegetation left", i.e. total damage (tasks.md T0-02)."""
    if ndvi is None:
        return None
    return max(0.0, min(1.0, 1.24 * ndvi - 0.168))


def cross_pol_ratio_deviation(sar) -> float | None:
    """`vh_vv_backscatter_deviation` (modeling-approach.md §3's Component 2
    feature table) — how much the cross-polarized ratio changed over the event.

    In dB the ratio is a difference, so the change in (VH − VV) between the pre-
    and post-event composites reduces exactly to `vh_drop − vv_drop`. `None`
    unless both polarizations were measured; the feature is omitted rather than
    defaulted in that case (tasks.md T0-15)."""
    if sar is None or sar.vh_drop_db is None or sar.vv_drop_db is None:
        return None
    return sar.vh_drop_db - sar.vv_drop_db


def observe(imagery, weather) -> FieldObservations:
    """Build the observation set for one request.

    A faithful lift of what `pipeline.py` computed inline — including two
    substitutions that are preserved here rather than corrected, because
    `T0R-02`'s gate is that every `pinned` fixture stays byte-identical. Both are
    now *visible* in the signal's `source` string instead of buried in an
    expression, which is the precondition for fixing them under their own task
    and their own fixture. See the inline notes on `POST_EVENT_TEMP_C` and
    `WEATHER_ANOMALY_MAGNITUDE`."""
    builder = ObservationBuilder()

    pre_ndvi = imagery.pre_event.index_value if imagery.pre_event else None
    post_ndvi = imagery.post_event.index_value if imagery.post_event else None
    pre_fapar = ndvi_to_fapar(pre_ndvi)
    post_fapar = ndvi_to_fapar(post_ndvi)
    optical_pair_available = pre_ndvi is not None and post_ndvi is not None

    pre_source = imagery.pre_event.source_dataset if imagery.pre_event else ""
    post_source = imagery.post_event.source_dataset if imagery.post_event else ""

    builder.record(
        PRE_EVENT_NDVI, pre_ndvi, source=pre_source,
        absent_reason="no usable pre-event optical composite",
    )
    builder.record(
        POST_EVENT_NDVI, post_ndvi, source=post_source,
        absent_reason="no usable post-event optical composite",
    )
    builder.record(
        PRE_EVENT_FAPAR, pre_fapar,
        source=f"{pre_source}, approximated from NDVI (FR-019 known limitation)",
        absent_reason="no usable pre-event optical composite",
    )
    builder.record(
        POST_EVENT_FAPAR, post_fapar,
        source=f"{post_source}, approximated from NDVI (FR-019 known limitation)",
        absent_reason="no usable post-event optical composite",
    )
    # Real LSWI from SWIR (tasks.md T05-08). Falls back to NDVI only where the
    # source carried no usable SWIR band, and says so in the provenance — the
    # two are different physical quantities, so a reader must be able to tell
    # which one a water-stress figure was computed from.
    pre_lswi = imagery.pre_event.lswi_value if imagery.pre_event else None
    post_lswi = imagery.post_event.lswi_value if imagery.post_event else None
    builder.record(
        PRE_EVENT_LSWI,
        pre_lswi if pre_lswi is not None else pre_ndvi,
        source=(
            f"{pre_source}, LSWI = (NIR-SWIR)/(NIR+SWIR)"
            if pre_lswi is not None
            else f"{pre_source}, NDVI standing in for LSWI (no usable SWIR band)"
        ),
        absent_reason="no usable pre-event optical composite",
    )
    builder.record(
        POST_EVENT_LSWI,
        post_lswi if post_lswi is not None else post_ndvi,
        source=(
            f"{post_source}, LSWI = (NIR-SWIR)/(NIR+SWIR)"
            if post_lswi is not None
            else f"{post_source}, NDVI standing in for LSWI (no usable SWIR band)"
        ),
        absent_reason="no usable post-event optical composite",
    )
    # modeling-approach.md §6's DSI indicator, never populated before T05-08
    # because no LSWI existed to deviate. Positive = moisture lost.
    builder.record(
        LSWI_DEVIATION,
        pre_lswi - post_lswi if pre_lswi is not None and post_lswi is not None else None,
        source=f"{pre_source} -> {post_source}, LSWI = (NIR-SWIR)/(NIR+SWIR)",
        absent_reason="requires a real LSWI on both sides; no usable SWIR band",
    )

    builder.record(
        NDVI_DEVIATION,
        max(0.0, pre_ndvi - post_ndvi) if optical_pair_available else None,
        source=f"{pre_source} -> {post_source}",
        absent_reason=NO_OPTICAL_PAIR,
    )
    builder.record(
        FAPAR_DEVIATION,
        pre_fapar - post_fapar if pre_fapar is not None and post_fapar is not None else None,
        source=f"{pre_source} -> {post_source}, approximated from NDVI",
        absent_reason=NO_OPTICAL_PAIR,
    )

    # PRESERVED SUBSTITUTION (1 of 2): a fixed 25 °C stands in when ERA5-Land
    # returns no reading, so Component 1 reports a confident result computed
    # from a temperature nobody measured. Behaviour is unchanged here; the
    # substitution is now stated in the signal's provenance instead of being
    # invisible past the `is None` check.
    observed_temp_c = weather.reanalysis.observed_value
    temp_is_measured = observed_temp_c is not None
    builder.record(
        PRE_EVENT_TEMP_C,
        observed_temp_c if temp_is_measured else FALLBACK_TEMPERATURE_C,
        source=(
            weather.reanalysis.source_dataset
            if temp_is_measured
            else f"substituted default {FALLBACK_TEMPERATURE_C} °C — no reading for the window"
        ),
        absent_reason="unreachable: a default is substituted",
    )
    builder.record(
        POST_EVENT_TEMP_C,
        observed_temp_c if temp_is_measured else FALLBACK_TEMPERATURE_C,
        source=(
            weather.reanalysis.source_dataset
            if temp_is_measured
            else f"substituted default {FALLBACK_TEMPERATURE_C} °C — no reading for the window"
        ),
        absent_reason="unreachable: a default is substituted",
    )

    for name in (PRE_EVENT_INSOLATION_MJ, POST_EVENT_INSOLATION_MJ):
        builder.record(
            name, INSOLATION_PROXY_MJ,
            source="fixed regional-average proxy — no insolation feed wired (FR-019)",
            absent_reason="unreachable: a constant proxy is used",
        )

    builder.record(
        RAINFALL_ANOMALY, weather.precipitation.anomaly_score,
        source=weather.precipitation.source_dataset,
        absent_reason="no historical baseline to compare the window against",
    )
    builder.record(
        TEMPERATURE_ANOMALY, weather.reanalysis.anomaly_score,
        source=weather.reanalysis.source_dataset,
        absent_reason="no historical baseline to compare the window against",
    )
    builder.record(
        SOIL_MOISTURE_DEVIATION, weather.soil_moisture.anomaly_score,
        source=weather.soil_moisture.source_dataset,
        absent_reason="no historical baseline to compare the window against",
    )

    # PRESERVED SUBSTITUTION (2 of 2): `abs(anomaly_score or 0.0)` turns an
    # unmeasurable anomaly into a measured zero — the exact shape of T0-02/T0-03
    # — and that zero reaches both the DSI and the causation score. Preserved
    # for T0R-02's byte-identical gate, stated in provenance, and flagged in
    # tasks.md for a task that owns the fixture it will flip.
    precipitation_anomaly = weather.precipitation.anomaly_score
    builder.record(
        WEATHER_ANOMALY_MAGNITUDE,
        min(1.0, abs(precipitation_anomaly or 0.0)),
        source=(
            weather.precipitation.source_dataset
            if precipitation_anomaly is not None
            else "substituted 0.0 — no precipitation anomaly could be computed"
        ),
        absent_reason="unreachable: a default is substituted",
    )

    builder.record(
        SAR_VH_BACKSCATTER_DEVIATION,
        imagery.sar.vh_drop_db if imagery.sar is not None else None,
        source=imagery.sar.source_dataset if imagery.sar is not None else "",
        absent_reason=(
            "SAR acquisitions carried a single polarization (VV only)"
            if imagery.sar is not None
            else "no SAR composite for this peril"
        ),
    )
    builder.record(
        VH_VV_BACKSCATTER_DEVIATION,
        cross_pol_ratio_deviation(imagery.sar),
        source=imagery.sar.source_dataset if imagery.sar is not None else "",
        absent_reason=(
            "requires both VH and VV; acquisitions carried a single polarization"
            if imagery.sar is not None
            else "no SAR composite for this peril"
        ),
    )

    # NOTE (T0R-01 finding, pinned not fixed): this archive holds absolute NDVI
    # *index values* while NDVI_DEVIATION above is a *drop* — different physical
    # quantities, the T0-03 mismatch in a second place. Preserved verbatim; see
    # pipeline-decomposition-design.md §6.4.
    builder.record_history(
        NDVI_DEVIATION,
        [c.index_value for c in imagery.historical if c.index_value is not None],
        absent_reason="no historical composites returned for this geometry",
    )
    for name in (
        FAPAR_DEVIATION,
        SAR_VH_BACKSCATTER_DEVIATION,
        WEATHER_ANOMALY_MAGNITUDE,
        LSWI_DEVIATION,
        "crop_condition_variability",
    ):
        builder.record_history(name, None, absent_reason="no historical archive wired")

    return builder.build(phenology_flag=imagery.phenology_flag)
