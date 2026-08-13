"""Environment/config loading. Values are read once at import time; nothing
here has a hard-coded fallback for values that must be provided per-deployment
(GEE credentials, database, storage)."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    gee_service_account_credentials: str | None
    gee_service_account_email: str | None
    database_url: str
    evidence_store_bucket: str
    causation_low_confidence_threshold: int | None
    csm_high_scrutiny_enabled: bool
    ai_ml_model_path: str | None
    minimum_valid_pixel_fraction: float | None
    damage_classification_bands: tuple[float, float, float]


def load_settings() -> Settings:
    return Settings(
        gee_service_account_credentials=os.environ.get("GEE_SERVICE_ACCOUNT_CREDENTIALS"),
        gee_service_account_email=os.environ.get("GEE_SERVICE_ACCOUNT_EMAIL"),
        database_url=os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://evidence_intelligence:evidence_intelligence@localhost:5432/evidence_intelligence",
        ),
        evidence_store_bucket=os.environ.get("EVIDENCE_STORE_BUCKET", "evidence-intelligence-dev"),
        # FR-024 / issue "causation confidence low-confidence threshold": no sourced
        # number exists yet (see specs/001-evidence-generation-pipeline/issue/). Unset
        # by default — a package is never auto-rejected regardless of this value.
        causation_low_confidence_threshold=(
            int(os.environ["CAUSATION_LOW_CONFIDENCE_THRESHOLD"])
            if "CAUSATION_LOW_CONFIDENCE_THRESHOLD" in os.environ
            else None
        ),
        # FR-011 / issue "CSM high-scrutiny trigger criteria": no defined trigger
        # exists yet. Defaults to disabled per tasks.md T038.
        csm_high_scrutiny_enabled=os.environ.get("CSM_HIGH_SCRUTINY_ENABLED", "false").lower()
        == "true",
        # Path to a model saved by AiMlModel.save() (see scripts/train_ai_ml_model.py).
        # Unset by default — the model ships untrained until one is trained and pointed
        # to here (see GUIDE.md "Training the AI/ML Model").
        ai_ml_model_path=os.environ.get("AI_ML_MODEL_PATH"),
        # tasks.md T0-07: the fraction of a field that must be cloud-free at least
        # once in the analysis window for its composite to count as usable. No
        # sourced value exists — how much of a field must be visible before an
        # index value means anything is exactly the kind of figure this repo
        # declines to invent (CLAUDE.md). Unset by default, matching the FR-024
        # precedent above: the fraction is always measured and disclosed in every
        # package, and only *gates* usability once a deployment supplies a value.
        minimum_valid_pixel_fraction=(
            float(os.environ["MINIMUM_VALID_PIXEL_FRACTION"])
            if "MINIMUM_VALID_PIXEL_FRACTION" in os.environ
            else None
        ),
        # tasks.md T0-17: cut points mapping a damage fraction to the
        # negligible/minor/moderate/severe label in every package. Unlike the
        # thresholds above these cannot ship unset — `damage_classification` is
        # populated on every ENSEMBLE row, so *some* mapping must exist. The
        # defaults are the values already in shipped code, retained so behaviour
        # is unchanged, but they appear nowhere in `documents/` and
        # `yestech_manual_2023.md` defines no transferable severity banding —
        # they are a presentational convention, and every package now says so
        # (see specs/001-evidence-generation-pipeline/issue/ "damage
        # classification band thresholds").
        damage_classification_bands=_parse_bands(
            os.environ.get("DAMAGE_CLASSIFICATION_BANDS")
        ),
    )


DEFAULT_DAMAGE_CLASSIFICATION_BANDS = (0.1, 0.33, 0.66)


def _parse_bands(raw: str | None) -> tuple[float, float, float]:
    """Three ascending cut points as `"0.1,0.33,0.66"`, or the default."""
    if not raw:
        return DEFAULT_DAMAGE_CLASSIFICATION_BANDS
    parts = tuple(float(part) for part in raw.split(","))
    if len(parts) != 3 or list(parts) != sorted(parts):
        raise ValueError(
            "DAMAGE_CLASSIFICATION_BANDS must be three ascending values, "
            f'e.g. "0.1,0.33,0.66" — got {raw!r}'
        )
    return parts


settings = load_settings()
