from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, JSON, String, Text,
)

from core.database import Base


class RawSource(Base):
    __tablename__ = "hleo_raw_sources"

    id            = Column(Integer, primary_key=True, index=True)
    episode_id    = Column(String, unique=True, index=True)
    user_id       = Column(String, index=True)
    source_type   = Column(String)          # pubmed | europepmc | clinicaltrials | reddit
    platform      = Column(String)
    external_url  = Column(String, unique=True)
    post_timestamp = Column(DateTime(timezone=True))
    raw_text      = Column(Text)
    ingested_at   = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class ClinicalProfile(Base):
    __tablename__ = "hleo_clinical_profiles"

    id                   = Column(Integer, primary_key=True, index=True)
    episode_id           = Column(String, unique=True, index=True)
    user_id              = Column(String, index=True)       # source platform
    final_category       = Column(String)
    confidence_score     = Column(Float)
    adjudication_required = Column(Boolean, default=False)
    extracted_payload    = Column(JSON)                    # ClinicalProfile dict
    validation_payload   = Column(JSON)                    # metadata: title, abstract_chars, source url
    processed_at         = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class PatientExperience(Base):
    """
    Structured patient-reported experience extracted from Reddit posts.
    One row per Reddit post that passes extraction.
    """
    __tablename__ = "hleo_patient_experiences"

    id               = Column(Integer, primary_key=True, index=True)
    episode_id       = Column(String, unique=True, index=True)
    source_platform  = Column(String, default="reddit")
    source_url       = Column(String)
    author           = Column(String)
    raw_text         = Column(Text)
    extracted_profile = Column(JSON)           # PatientExperienceProfile dict
    query_context    = Column(String)          # search query that surfaced this post
    ingested_at      = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class SourceAttribution(Base):
    """
    Links a clinical profile (or patient experience) to its provenance.
    One row per source for each profile (could be multiple citations).
    """
    __tablename__ = "hleo_source_attributions"

    id                  = Column(Integer, primary_key=True, index=True)
    profile_episode_id  = Column(String, index=True)  # FK to hleo_clinical_profiles.episode_id
    source_type         = Column(String)               # pubmed | europepmc | clinicaltrials | reddit
    source_title        = Column(String)
    source_url          = Column(String)
    external_id         = Column(String)               # PMID / NCT / DOI
    journal             = Column(String)
    pub_year            = Column(String)
    abstract_excerpt    = Column(Text)
    added_at            = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class ChatSession(Base):
    __tablename__ = "hleo_chat_sessions"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    title      = Column(String)                    # first user message (truncated)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class ChatMessage(Base):
    __tablename__ = "hleo_chat_messages"

    id           = Column(Integer, primary_key=True, index=True)
    session_id   = Column(String, index=True)
    role         = Column(String)              # user | assistant
    content      = Column(Text)
    context_used = Column(JSON)               # list of episode_ids used as RAG context
    created_at   = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class AuditLog(Base):
    __tablename__ = "hleo_audit_log"

    id         = Column(Integer, primary_key=True, index=True)
    episode_id = Column(String, index=True)
    action     = Column(String)
    status     = Column(String)
    details    = Column(Text)
    timestamp  = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
