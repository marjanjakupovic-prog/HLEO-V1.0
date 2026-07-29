import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from core.database import get_db, engine, Base
from core.models import ClinicalProfile, RawSource, AuditLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="HLEO API", version="1.0.0")

Base.metadata.create_all(bind=engine)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── Helpers ───────────────────────────────────────────────────────

def _to_dict(obj: Any) -> Any:
    """Recursively serialise dataclasses and Pydantic models to plain dicts."""
    if obj is None:
        return None
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    try:
        return asdict(obj)
    except TypeError:
        return str(obj)


# ── Routes ────────────────────────────────────────────────────────

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
        "raw_sources": db.execute(
            select(func.count()).select_from(RawSource)
        ).scalar(),
    }


@app.get("/search")
def search(q: str = Query(..., description="Search query")):
    """
    Collect results from all sources.
    When OPENAI_API_KEY is set, Reddit posts are also LLM-extracted.
    """
    from core.pipeline import HLEOPipeline

    pipeline = HLEOPipeline()
    llm_available = pipeline.extractor.client is not None

    # Always collect raw data from all sources
    raw = pipeline.collect(q)

    pubmed         = [_to_dict(a) for a in raw["pubmed"]]
    europepmc      = [_to_dict(a) for a in raw["europepmc"]]
    clinicaltrials = [_to_dict(a) for a in raw["clinicaltrials"]]
    reddit_raw     = [_to_dict(p) for p in raw["reddit"]]

    # Run full LLM pipeline on Reddit posts when key is available
    reddit_processed = []
    if llm_available and raw["reddit"]:
        from core.extractor import LLMExtractor
        from core.validator import HLEOValidator
        from core.judge import HLEOJudge
        from search.source_fetcher import SourceFetcher

        fetcher   = SourceFetcher()
        validator = HLEOValidator()
        judge     = HLEOJudge()

        for post in raw["reddit"]:
            entry: dict = {"post": _to_dict(post), "profile": None, "validation": None, "judge": None, "error": None}
            try:
                raw_sources = fetcher.fetch(post.url)
                profile     = pipeline.extractor.extract(post.text or post.title)
                validation  = validator.validate(profile, raw_sources, post.created_at)
                judge_res   = judge.evaluate(
                    profile.baseline_status.value,
                    profile.post_treatment_status.value,
                    validation.passed_validation,
                    profile.post_treatment_status.support_strength,
                    profile.conflict_detected,
                    profile.episode_id,
                )
                entry["profile"]    = _to_dict(profile)
                entry["validation"] = _to_dict(validation)
                entry["judge"]      = _to_dict(judge_res)
            except Exception as exc:
                logger.exception(f"LLM extraction failed for {post.url}: {exc}")
                entry["error"] = str(exc)
            reddit_processed.append(entry)

    return {
        "query": q,
        "llm_extraction": llm_available,
        "totals": {
            "pubmed":          len(pubmed),
            "europepmc":       len(europepmc),
            "clinicaltrials":  len(clinicaltrials),
            "reddit":          len(reddit_raw),
        },
        "pubmed":           pubmed,
        "europepmc":        europepmc,
        "clinicaltrials":   clinicaltrials,
        "reddit":           reddit_raw,
        "reddit_processed": reddit_processed,   # LLM profiles (empty list when key not set)
    }
