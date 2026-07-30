"""
HLEO v1.0 — FastAPI application
Endpoints:
  GET  /                     → dashboard UI
  GET  /health               → key/version status
  GET  /stats                → DB row counts
  GET  /search?q=            → fast collect from all sources (no LLM)
  POST /pipeline/run?q=      → collect + LLM-extract articles → DB
  GET  /profiles?limit=      → saved clinical profiles
  POST /experiences/ingest?q= → collect Reddit + LLM-extract patient experiences → DB
  GET  /experiences?limit=   → saved patient experiences
  POST /assistant/chat       → AI Clinical Assistant (RAG over DB)
  GET  /assistant/sessions/{session_id} → chat history
"""
import logging
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Depends, Query, Request, Body
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import select, func, desc, or_
from sqlalchemy.orm import Session

from core.database import get_db, engine, Base
from core.models import (
    ClinicalProfile, RawSource, AuditLog,
    PatientExperience, SourceAttribution, ChatSession, ChatMessage,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple in-memory translation cache (avoids re-calling LLM for identical text+lang pairs)
_translate_cache: dict = {}

app = FastAPI(title="HLEO API", version="1.0.0")
Base.metadata.create_all(bind=engine)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    try:
        return asdict(obj)
    except TypeError:
        return str(obj)


# ── Core routes ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health_check():
    import os
    key = os.getenv("OPENAI_API_KEY", "")
    return {
        "status": "ok",
        "version": "1.0.0",
        "openai_key_set": bool(key),
        "openai_key_prefix": key[:8] + "…" if key else None,
    }


@app.get("/stats")
def stats(db: Session = Depends(get_db)):
    return {
        "clinical_profiles": db.execute(
            select(func.count()).select_from(ClinicalProfile)
        ).scalar(),
        "patient_experiences": db.execute(
            select(func.count()).select_from(PatientExperience)
        ).scalar(),
        "raw_sources": db.execute(
            select(func.count()).select_from(RawSource)
        ).scalar(),
        "source_attributions": db.execute(
            select(func.count()).select_from(SourceAttribution)
        ).scalar(),
        "chat_sessions": db.execute(
            select(func.count()).select_from(ChatSession)
        ).scalar(),
    }


# ── Search (fast, no LLM) ─────────────────────────────────────────────────────

@app.get("/search")
def search(q: str = Query(..., description="Search query")):
    """Collect results from all sources — no LLM, returns raw data immediately."""
    from core.pipeline import HLEOPipeline
    pipeline = HLEOPipeline()
    raw = pipeline.collect(q)

    pubmed         = [_to_dict(a) for a in raw["pubmed"]]
    europepmc      = [_to_dict(a) for a in raw["europepmc"]]
    clinicaltrials = [_to_dict(a) for a in raw["clinicaltrials"]]
    reddit_raw     = [_to_dict(p) for p in raw["reddit"]]

    return {
        "query": q,
        "llm_extraction": pipeline.extractor.client is not None,
        "totals": {
            "pubmed":         len(pubmed),
            "europepmc":      len(europepmc),
            "clinicaltrials": len(clinicaltrials),
            "reddit":         len(reddit_raw),
        },
        "pubmed": pubmed, "europepmc": europepmc,
        "clinicaltrials": clinicaltrials, "reddit": reddit_raw,
    }


# ── Article pipeline ──────────────────────────────────────────────────────────

@app.post("/pipeline/run")
def run_pipeline(q: str = Query(...), db: Session = Depends(get_db)):
    """
    Full article pipeline:
    1. Collect from PubMed, EuropePMC, ClinicalTrials
    2. LLM-extract a ClinicalProfile from each abstract
    3. Save profile + SourceAttribution to DB
    Returns summary and saved profiles.
    """
    from core.pipeline import HLEOPipeline
    from core.article_extractor import ArticleExtractor

    pipeline  = HLEOPipeline()
    extractor = ArticleExtractor()

    if extractor.client is None:
        return {"error": "OPENAI_API_KEY not set — cannot run LLM extraction."}

    raw = pipeline.collect(q)

    articles = []
    for item in raw["pubmed"]:
        articles.append({
            "source":     "pubmed",
            "episode_id": f"pubmed-{item.pmid}",
            "title":      item.title,
            "abstract":   item.abstract or "",
            "url":        f"https://pubmed.ncbi.nlm.nih.gov/{item.pmid}/",
            "external_id": item.pmid,
            "journal":    (item.metadata or {}).get("journal", ""),
            "pub_year":   str((item.metadata or {}).get("pubdate", ""))[:4],
            "meta":       item.metadata or {},
        })
    for item in raw["europepmc"]:
        ep_id = (item.metadata or {}).get("id") or (item.doi or "").replace("/", "-")
        articles.append({
            "source":     "europepmc",
            "episode_id": f"europepmc-{ep_id}",
            "title":      item.title,
            "abstract":   item.abstract or "",
            "url":        f"https://doi.org/{item.doi}" if item.doi else "",
            "external_id": item.doi or ep_id,
            "journal":    (item.metadata or {}).get("journal", ""),
            "pub_year":   str(item.year or ""),
            "meta":       item.metadata or {},
        })
    for item in raw["clinicaltrials"]:
        nct = (item.metadata or {}).get("nct_id", "unknown")
        articles.append({
            "source":     "clinicaltrials",
            "episode_id": f"clinicaltrial-{nct}",
            "title":      item.title,
            "abstract":   item.abstract or "",
            "url":        f"https://clinicaltrials.gov/study/{nct}" if nct != "unknown" else "",
            "external_id": nct,
            "journal":    "",
            "pub_year":   "",
            "meta":       item.metadata or {},
        })

    saved = []
    errors = []

    for art in articles:
        episode_id = art["episode_id"]

        existing = db.execute(
            select(ClinicalProfile).where(ClinicalProfile.episode_id == episode_id)
        ).scalar_one_or_none()

        if existing:
            saved.append({
                "episode_id": episode_id,
                "status":  "already_exists",
                "db_id":   existing.id,
                "source":  art["source"],
                "title":   art["title"],
                "profile": existing.extracted_payload,
                "attribution": _get_attribution(db, episode_id),
            })
            continue

        if not art["abstract"]:
            errors.append({
                "episode_id": episode_id,
                "error": "No abstract available — skipped.",
            })
            continue

        try:
            payload = extractor.extract(
                title=art["title"],
                abstract=art["abstract"],
                source=art["source"],
            )

            row = ClinicalProfile(
                episode_id=episode_id,
                user_id=art["source"],
                final_category="N/A",
                confidence_score=0.0,
                adjudication_required=False,
                extracted_payload=payload,
                validation_payload={
                    "source":         art["source"],
                    "title":          art["title"],
                    "url":            art["url"],
                    "abstract_chars": len(art["abstract"]),
                    "journal":        art["journal"],
                    "pub_year":       art["pub_year"],
                    "meta":           art["meta"],
                },
            )
            db.add(row)
            db.flush()

            # Source attribution
            attr = SourceAttribution(
                profile_episode_id=episode_id,
                source_type=art["source"],
                source_title=art["title"],
                source_url=art["url"],
                external_id=art["external_id"],
                journal=art["journal"],
                pub_year=art["pub_year"],
                abstract_excerpt=art["abstract"][:500],
            )
            db.add(attr)
            db.commit()
            db.refresh(row)

            saved.append({
                "episode_id": episode_id,
                "status": "saved",
                "db_id":  row.id,
                "source": art["source"],
                "title":  art["title"],
                "profile": payload,
                "attribution": _get_attribution(db, episode_id),
            })
            logger.info(f"Saved profile {episode_id}")

        except Exception as exc:
            db.rollback()
            logger.exception(f"Failed to process {episode_id}: {exc}")
            errors.append({"episode_id": episode_id, "error": str(exc)})

    return {
        "query":           q,
        "processed":       len(articles),
        "saved":           len([s for s in saved if s["status"] == "saved"]),
        "already_existed": len([s for s in saved if s["status"] == "already_exists"]),
        "errors":          len(errors),
        "results":         saved,
        "error_details":   errors,
    }


def _get_attribution(db: Session, episode_id: str) -> Optional[dict]:
    attr = db.execute(
        select(SourceAttribution).where(SourceAttribution.profile_episode_id == episode_id)
    ).scalar_one_or_none()
    if not attr:
        return None
    return {
        "source_type":  attr.source_type,
        "source_title": attr.source_title,
        "source_url":   attr.source_url,
        "external_id":  attr.external_id,
        "journal":      attr.journal,
        "pub_year":     attr.pub_year,
        "abstract_excerpt": attr.abstract_excerpt,
    }


# ── Clinical profiles ─────────────────────────────────────────────────────────

@app.get("/profiles")
def list_profiles(
    limit: int = Query(20, ge=1, le=100),
    db:    Session = Depends(get_db),
):
    """Return saved clinical profiles with source attribution."""
    rows = db.execute(
        select(ClinicalProfile)
        .order_by(desc(ClinicalProfile.processed_at))
        .limit(limit)
    ).scalars().all()

    result = []
    for r in rows:
        vp = r.validation_payload or {}
        attr = _get_attribution(db, r.episode_id)
        result.append({
            "id":                   r.id,
            "episode_id":           r.episode_id,
            "user_id":              r.user_id,
            "final_category":       r.final_category,
            "confidence_score":     r.confidence_score,
            "adjudication_required": r.adjudication_required,
            "processed_at":         r.processed_at.isoformat() if r.processed_at else None,
            "title":    vp.get("title", ""),
            "source":   vp.get("source", r.user_id),
            "url":      vp.get("url", ""),
            "journal":  vp.get("journal", ""),
            "pub_year": vp.get("pub_year", ""),
            "profile":  r.extracted_payload,
            "attribution": attr,
        })

    return {
        "total":    db.execute(select(func.count()).select_from(ClinicalProfile)).scalar(),
        "profiles": result,
    }


# ── Patient experiences ───────────────────────────────────────────────────────

@app.post("/experiences/ingest")
def ingest_experiences(q: str = Query(...), db: Session = Depends(get_db)):
    """
    Collect Reddit posts via PRAW OAuth, LLM-extract patient experiences, save to DB.

    Always returns a structured response including:
      reddit_status  — ok | no_credentials | auth_error | rate_limited | no_results | network_error
      reddit_reason  — human-readable explanation of the status
    """
    from collectors.reddit import RedditCollector, STATUS_OK, STATUS_NO_CREDENTIALS
    from core.patient_extractor import PatientExperienceExtractor

    extractor = PatientExperienceExtractor()
    if extractor.client is None:
        return {
            "query": q, "collected": 0, "saved": 0, "errors": 0, "results": [],
            "reddit_status": "no_openai_key",
            "reddit_reason": "OPENAI_API_KEY is not set — LLM extraction is disabled.",
        }

    # ── Collect from Reddit via PRAW ────────────────────────────────────────
    collector = RedditCollector()
    raw_reddit, reddit_status, reddit_reason = collector.search_with_status(q, limit=15)
    logger.info(f"Reddit [{reddit_status}] for '{q}': {reddit_reason}")

    if reddit_status != STATUS_OK:
        return {
            "query":          q,
            "collected":      0,
            "saved":          0,
            "already_existed": 0,
            "errors":         0,
            "results":        [],
            "error_details":  [],
            "reddit_status":  reddit_status,
            "reddit_reason":  reddit_reason,
        }

    # ── Extract and save ────────────────────────────────────────────────────
    saved  = []
    errors = []

    for post in raw_reddit:
        episode_id = f"reddit-exp-{abs(hash(post.url))}"

        existing = db.execute(
            select(PatientExperience).where(PatientExperience.episode_id == episode_id)
        ).scalar_one_or_none()
        if existing:
            saved.append({
                "episode_id": episode_id,
                "status":  "already_exists",
                "title":   post.title,
                "profile": existing.extracted_profile,
            })
            continue

        body = (post.text or "").strip()
        if len(body) < 50:
            errors.append({"episode_id": episode_id, "error": "Post body too short — skipped."})
            continue

        try:
            profile = extractor.extract(
                title=post.title,
                text=body,
                author=post.author or "",
                url=post.url or "",
            )

            row = PatientExperience(
                episode_id=episode_id,
                source_platform="reddit",
                source_url=post.url,
                author=post.author,
                raw_text=body[:4000],
                extracted_profile=profile,
                query_context=q,
            )
            db.add(row)
            db.commit()
            db.refresh(row)

            saved.append({
                "episode_id": episode_id,
                "status": "saved",
                "db_id":  row.id,
                "title":  post.title,
                "url":    post.url,
                "profile": profile,
            })
            logger.info(f"Saved patient experience {episode_id}")

        except Exception as exc:
            db.rollback()
            logger.exception(f"Failed to extract experience {episode_id}: {exc}")
            errors.append({"episode_id": episode_id, "error": str(exc)})

    n_saved = len([s for s in saved if s["status"] == "saved"])
    return {
        "query":           q,
        "collected":       len(raw_reddit),
        "saved":           n_saved,
        "already_existed": len([s for s in saved if s["status"] == "already_exists"]),
        "errors":          len(errors),
        "results":         saved,
        "error_details":   errors,
        "reddit_status":   STATUS_OK,
        "reddit_reason":   f"Retrieved {len(raw_reddit)} post(s); {n_saved} new experience(s) saved.",
    }


@app.get("/experiences")
def list_experiences(
    limit: int = Query(20, ge=1, le=100),
    db:    Session = Depends(get_db),
):
    rows = db.execute(
        select(PatientExperience)
        .order_by(desc(PatientExperience.ingested_at))
        .limit(limit)
    ).scalars().all()

    return {
        "total": db.execute(select(func.count()).select_from(PatientExperience)).scalar(),
        "experiences": [
            {
                "id":           r.id,
                "episode_id":   r.episode_id,
                "source_url":   r.source_url,
                "query_context": r.query_context,
                "ingested_at":  r.ingested_at.isoformat() if r.ingested_at else None,
                "profile":      r.extracted_profile,
            }
            for r in rows
        ],
    }


# ── AI Clinical Assistant ─────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    language: Optional[str] = "en"   # ISO 639-1 code, e.g. "en" / "it"


@app.post("/assistant/chat")
def assistant_chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    AI Clinical Assistant — RAG over stored profiles and patient experiences.
    Creates a session if none provided; returns assistant response + session_id.
    """
    import os, json as _json

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return {"error": "OPENAI_API_KEY not set."}

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    # ── Session management ──────────────────────────────────────────
    session_id = body.session_id or str(uuid.uuid4())
    session = db.execute(
        select(ChatSession).where(ChatSession.session_id == session_id)
    ).scalar_one_or_none()

    if not session:
        title = body.message[:80]
        session = ChatSession(session_id=session_id, title=title)
        db.add(session)
        db.commit()

    # ── Load conversation history ───────────────────────────────────
    history_rows = db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .limit(20)
    ).scalars().all()

    messages_history = [
        {"role": r.role, "content": r.content} for r in history_rows
    ]

    # ── RAG: retrieve relevant context from DB ──────────────────────
    user_msg_lower = body.message.lower()
    context_snippets = []
    context_episode_ids = []

    # Search clinical profiles
    cp_rows = db.execute(
        select(ClinicalProfile)
        .order_by(desc(ClinicalProfile.processed_at))
        .limit(30)
    ).scalars().all()

    for cp in cp_rows:
        vp = cp.validation_payload or {}
        title = vp.get("title", "").lower()
        payload = cp.extracted_payload or {}
        # Simple relevance: check if any key term overlaps
        payload_text = _json.dumps(payload).lower()
        if any(word in title or word in payload_text
               for word in user_msg_lower.split() if len(word) > 3):
            diag     = ", ".join(payload.get("diagnosis", [])[:3])
            treats   = ", ".join(payload.get("treatments", [])[:4])
            outcomes = ", ".join(payload.get("outcomes", [])[:3])
            ev_level = payload.get("evidence_level", "")
            snippet  = (
                f"[Clinical Profile — {cp.user_id.upper()}, {vp.get('pub_year','')}] "
                f"'{vp.get('title','')[:100]}'"
                f"{f' ({ev_level})' if ev_level else ''}\n"
                f"  Diagnosis: {diag or 'N/A'}\n"
                f"  Treatments: {treats or 'N/A'}\n"
                f"  Outcomes: {outcomes or 'N/A'}"
            )
            context_snippets.append(snippet)
            context_episode_ids.append(cp.episode_id)
            if len(context_snippets) >= 5:
                break

    # Search patient experiences
    pe_rows = db.execute(
        select(PatientExperience)
        .order_by(desc(PatientExperience.ingested_at))
        .limit(30)
    ).scalars().all()

    for pe in pe_rows:
        p = pe.extracted_profile or {}
        payload_text = _json.dumps(p).lower()
        if any(word in payload_text for word in user_msg_lower.split() if len(word) > 3):
            condition = p.get("condition", "unknown condition")
            summary   = p.get("experience_summary", "")
            treats    = ", ".join(p.get("treatments_tried", [])[:3])
            outcomes  = ", ".join(p.get("reported_outcomes", [])[:3])
            snippet   = (
                f"[Patient Experience — Reddit]\n"
                f"  Condition: {condition}\n"
                f"  Summary: {summary[:200] if summary else 'N/A'}\n"
                f"  Treatments tried: {treats or 'N/A'}\n"
                f"  Reported outcomes: {outcomes or 'N/A'}"
            )
            context_snippets.append(snippet)
            context_episode_ids.append(pe.episode_id)
            if len(context_snippets) >= 8:
                break

    # ── Build system prompt ─────────────────────────────────────────
    context_block = (
        "\n\n".join(context_snippets)
        if context_snippets
        else "No relevant records found in the database for this query."
    )

    _LANG_MAP = {
        "it": "Italian", "en": "English", "fr": "French",
        "de": "German",  "es": "Spanish", "pt": "Portuguese",
    }
    _resp_lang  = _LANG_MAP.get(body.language or "en", "English")
    _lang_note  = (
        f"\n\nIMPORTANT: You must respond entirely in {_resp_lang}. "
        f"All your answers, labels, and explanations must be written in {_resp_lang}."
        if _resp_lang != "English" else ""
    )

    system_prompt = (
        "You are HLEO Clinical Assistant, an AI that helps clinicians and researchers "
        "understand evidence from scientific literature and patient-reported experiences.\n\n"
        "You have access to a curated database of extracted clinical profiles and patient "
        "experiences. You answer questions based ONLY on information in the provided context "
        "and general medical knowledge. You always:\n"
        "- Cite the source type (e.g. PubMed article, patient experience) when referencing data.\n"
        "- Acknowledge uncertainty; never overstate evidence.\n"
        "- Recommend consulting a qualified clinician for personal medical decisions.\n"
        "- Are concise (3-6 sentences unless detail is specifically requested).\n\n"
        f"RETRIEVED CONTEXT ({len(context_snippets)} records):\n"
        "─────────────────────────────────────\n"
        f"{context_block}\n"
        "─────────────────────────────────────"
        f"{_lang_note}"
    )

    # ── Call LLM ───────────────────────────────────────────────────
    llm_messages = [{"role": "system", "content": system_prompt}]
    llm_messages.extend(messages_history)
    llm_messages.append({"role": "user", "content": body.message})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=llm_messages,
        temperature=0.3,
        max_tokens=800,
    )
    assistant_text = response.choices[0].message.content

    # ── Persist messages ───────────────────────────────────────────
    db.add(ChatMessage(
        session_id=session_id,
        role="user",
        content=body.message,
        context_used=[],
    ))
    db.add(ChatMessage(
        session_id=session_id,
        role="assistant",
        content=assistant_text,
        context_used=context_episode_ids,
    ))
    db.commit()

    return {
        "session_id":          session_id,
        "response":            assistant_text,
        "context_used_count":  len(context_snippets),
        "context_episode_ids": context_episode_ids,
    }


@app.get("/assistant/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    messages = db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    ).scalars().all()

    return {
        "session_id": session_id,
        "messages": [
            {
                "role":         m.role,
                "content":      m.content,
                "context_used": m.context_used,
                "created_at":   m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


# ── Translation endpoint ──────────────────────────────────────────────────────

class TranslateRequest(BaseModel):
    text: str
    target_lang: str = "it"
    content_type: str = "clinical_article"   # clinical_article | patient_experience | general


@app.post("/translate")
async def translate_text(body: TranslateRequest):
    """
    AI translation endpoint used by the frontend language switcher.
    Accepts {text, target_lang, content_type}.
    Returns  {translation, summary, target_lang, content_type}.
    Results are cached in _translate_cache (process lifetime) to avoid re-calling the LLM.
    """
    import os, json as _json, hashlib

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured.")

    cache_key = hashlib.md5(
        f"{body.target_lang}:{body.content_type}:{body.text[:500]}".encode()
    ).hexdigest()
    if cache_key in _translate_cache:
        return _translate_cache[cache_key]

    LANG_NAMES = {
        "it": "Italian",    "en": "English",   "fr": "French",
        "de": "German",     "es": "Spanish",   "pt": "Portuguese",
        "zh": "Chinese",    "ja": "Japanese",  "ar": "Arabic",
        "ru": "Russian",    "nl": "Dutch",     "pl": "Polish",
    }
    lang_name     = LANG_NAMES.get(body.target_lang, body.target_lang)
    content_label = body.content_type.replace("_", " ")

    prompt = (
        f"You are a professional medical translator and summariser.\n\n"
        f"Translate the following {content_label} text to {lang_name}, "
        f"preserving all medical terminology accurately. "
        f"Also provide a concise summary in {lang_name} (2-3 sentences max).\n\n"
        f"TEXT:\n{body.text[:3000]}\n\n"
        "Respond with JSON only:\n"
        '{"translation": "...", "summary": "..."}'
    )

    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=1500,
        temperature=0.2,
    )

    result = _json.loads(response.choices[0].message.content)
    out = {
        "translation":  result.get("translation", ""),
        "summary":      result.get("summary", ""),
        "target_lang":  body.target_lang,
        "content_type": body.content_type,
    }
    _translate_cache[cache_key] = out
    logger.info(f"Translated {len(body.text)} chars to {lang_name} ({body.content_type})")
    return out


@app.get("/assistant/sessions")
def list_sessions(
    limit: int = Query(10, ge=1, le=50),
    db:    Session = Depends(get_db),
):
    rows = db.execute(
        select(ChatSession)
        .order_by(desc(ChatSession.created_at))
        .limit(limit)
    ).scalars().all()

    return {
        "sessions": [
            {
                "session_id": r.session_id,
                "title":      r.title,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
