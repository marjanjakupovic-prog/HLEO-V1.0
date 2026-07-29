from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text

from core.database import Base


class RawSource(Base):
    __tablename__ = "hleo_raw_sources"

    id = Column(Integer, primary_key=True, index=True)
    episode_id = Column(String, unique=True, index=True)
    user_id = Column(String, index=True)
    source_type = Column(String)
    platform = Column(String)
    external_url = Column(String, unique=True)
    post_timestamp = Column(DateTime(timezone=True))
    raw_text = Column(Text)
    ingested_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class ClinicalProfile(Base):
    __tablename__ = "hleo_clinical_profiles"

    id = Column(Integer, primary_key=True, index=True)
    episode_id = Column(String, unique=True, index=True)
    user_id = Column(String, index=True)
    final_category = Column(String)
    confidence_score = Column(Float)
    adjudication_required = Column(Boolean, default=False)
    extracted_payload = Column(JSON)
    validation_payload = Column(JSON)
    processed_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class AuditLog(Base):
    __tablename__ = "hleo_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    episode_id = Column(String, index=True)
    action = Column(String)
    status = Column(String)
    details = Column(Text)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
