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
    )


settings = load_settings()
