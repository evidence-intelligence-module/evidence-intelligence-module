"""Report/Package Generator (HLD §3, §6). Assembles the pipeline's outputs
into the Output Artifact: PDF + JSON + maps, with the mandatory §65B fields
(Constitution §2.3, evidence-flow-spec.md §7) on every package regardless of
tier."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

SUPPORTING_EVIDENCE_DISCLAIMER = (
    "This yield-loss estimate and Damage Severity Index are supporting evidence "
    "components only. They are NOT an authoritative or indemnity-grade determination "
    "and do not replace or blend with any Crop Cutting Experiment (CCE) yield "
    "determination (Constitution §4, FR-026)."
)


@dataclass
class PackageContent:
    request_id: str
    package_tier: str  # "WEATHER_ONLY_PRELIMINARY" | "COMPLETE"
    methodology_version: str
    generated_at: datetime
    causation_confidence_score: int | None
    ensemble_damage_fraction: float | None
    ensemble_combined_confidence: float | None
    dsi_score: float | None
    damage_classification: str | None
    affected_area_ha: float | None
    causation_terms_contributing: list[str] = field(default_factory=list)
    causation_terms_excluded: dict = field(default_factory=dict)
    """Which of the four alignment terms were measured, and why the rest were
    not. A 60 computed from one term is a different claim from a 60 computed
    from four, and the score alone cannot distinguish them (T0-06)."""
    source_attribution: list[dict] = field(default_factory=list)
    accuracy_statement: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    evidence_inputs: list[dict] = field(default_factory=list)
    """Every input attempted for this request and what came of it (T0-09).

    Part of the §65B chain-of-custody argument, not a debug aid: it is what
    lets a reviewer distinguish a conclusion drawn from full evidence from one
    drawn after half the inputs were unavailable, and it distinguishes "we
    looked and found nothing" from "we never looked"."""


class LocalObjectStorage:
    """Dev/test object storage backed by the local filesystem, behind the
    same `put(key, bytes) -> uri` interface an S3-compatible client would
    expose (HLD §7). Swap for a real S3 client in production via
    EVIDENCE_STORE_BUCKET."""

    def __init__(self, bucket: str):
        self.bucket = bucket
        self.root = Path(os.environ.get("EVIDENCE_STORE_LOCAL_ROOT", ".evidence_store")) / bucket
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, content: bytes) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return f"file://{path.resolve()}"


def _checksum(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _build_json_record(content: PackageContent) -> dict:
    return {
        "request_id": content.request_id,
        "package_tier": content.package_tier,
        "methodology_version": content.methodology_version,
        "generated_at": content.generated_at.isoformat(),
        "causation_confidence_score": content.causation_confidence_score,
        "causation_terms": {
            "contributing": content.causation_terms_contributing,
            "excluded": content.causation_terms_excluded,
        },
        "yield_loss_estimate": {
            "value": content.ensemble_damage_fraction,
            "combined_confidence": content.ensemble_combined_confidence,
            "label": "supporting_evidence_not_authoritative",
        },
        "damage_severity_index": {
            "value": content.dsi_score,
            "label": "supporting_evidence_not_authoritative",
        },
        "damage_classification": content.damage_classification,
        "affected_area_ha": content.affected_area_ha,
        "source_attribution": content.source_attribution,
        "evidence_inputs": content.evidence_inputs,
        "accuracy_statement": content.accuracy_statement,
        "notes": content.notes,
        "disclaimer": SUPPORTING_EVIDENCE_DISCLAIMER,
    }


def _build_pdf(content: PackageContent) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"Evidence Report — {content.request_id}", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Package tier: {content.package_tier}", styles["Normal"]),
        Paragraph(f"Methodology version: {content.methodology_version}", styles["Normal"]),
        Paragraph(f"Generated: {content.generated_at.isoformat()}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Causation Analysis", styles["Heading2"]),
        Paragraph(
            "Causation confidence score: "
            + (
                "not computed — no alignment term could be measured"
                if content.causation_confidence_score is None
                else f"{content.causation_confidence_score} "
                f"(from {len(content.causation_terms_contributing)} of 4 alignment terms, "
                "reweighted over those measured)"
            ),
            styles["Normal"],
        ),
        *(
            [
                Paragraph(f"Term not measured — {name}: {reason}", styles["Italic"])
                for name, reason in content.causation_terms_excluded.items()
            ]
        ),
        Spacer(1, 12),
        Paragraph("Yield-Loss Estimate and Damage Severity Index", styles["Heading2"]),
        Paragraph(
            f"Ensemble yield-loss estimate: {content.ensemble_damage_fraction} "
            f"(combined confidence {content.ensemble_combined_confidence})",
            styles["Normal"],
        ),
        Paragraph(f"Damage Severity Index: {content.dsi_score}", styles["Normal"]),
        Paragraph(SUPPORTING_EVIDENCE_DISCLAIMER, styles["Italic"]),
        Spacer(1, 12),
        Paragraph("Source Attribution / Chain of Custody", styles["Heading2"]),
    ]
    for source in content.source_attribution:
        story.append(
            Paragraph(
                f"{source.get('source_dataset')} ({source.get('source_version')}) — "
                f"acquired {source.get('acquisition_date')}",
                styles["Normal"],
            )
        )
    story.append(Spacer(1, 12))
    story.append(Paragraph("Accuracy Statement", styles["Heading2"]))
    for statement in content.accuracy_statement:
        story.append(Paragraph(statement, styles["Normal"]))
    if content.notes:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Notes", styles["Heading2"]))
        for note in content.notes:
            story.append(Paragraph(note, styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()


def generate_package(content: PackageContent, storage: LocalObjectStorage) -> dict:
    """Returns the fields needed for `EvidenceStore.add_package` — every
    §65B field (source attribution, methodology, accuracy, chain of custody,
    checksum, timestamp) is present regardless of package_tier (FR-017–FR-020)."""
    json_record = _build_json_record(content)
    json_bytes = json.dumps(json_record, indent=2).encode("utf-8")
    pdf_bytes = _build_pdf(content)

    key_prefix = f"{content.request_id}/{content.generated_at.strftime('%Y%m%dT%H%M%S')}"
    json_uri = storage.put(f"{key_prefix}/package.json", json_bytes)
    pdf_uri = storage.put(f"{key_prefix}/report.pdf", pdf_bytes)

    checksum = _checksum(json_bytes + pdf_bytes)

    return {
        "pdf_uri": pdf_uri,
        "json_uri": json_uri,
        "map_uris": [],
        "checksum": checksum,
    }
