import logging
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from core.database import get_db, engine, Base
from core.models import ClinicalProfile, RawSource, AuditLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="HLEO API", version="1.0.0")

Base.metadata.create_all(bind=engine)

# ── Templates & static files ──────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── Routes ────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/stats")
def stats(db: Session = Depends(get_db)):
    profiles_count = db.execute(
        select(func.count()).select_from(ClinicalProfile)
    ).scalar()
    sources_count = db.execute(
        select(func.count()).select_from(RawSource)
    ).scalar()
    return {
        "clinical_profiles": profiles_count,
        "raw_sources": sources_count,
    }


@app.get("/search")
def search(q: str = Query(..., description="Search query")):
    """
    Collect results from all sources (Reddit, PubMed, EuropePMC, ClinicalTrials).
    LLM-based clinical profile extraction runs only when OPENAI_API_KEY is set.
    """
    from core.pipeline import HLEOPipeline

    pipeline = HLEOPipeline()
    raw = pipeline.collect(q)

    def _sr(obj):
        try:
            return asdict(obj)
        except TypeError:
            return str(obj)

    pubmed         = [_sr(a) for a in raw["pubmed"]]
    europepmc      = [_sr(a) for a in raw["europepmc"]]
    clinicaltrials = [_sr(a) for a in raw["clinicaltrials"]]
    reddit         = [_sr(p) for p in raw["reddit"]]

    llm_available = pipeline.extractor.client is not None

    return {
        "query": q,
        "llm_extraction": llm_available,
        "totals": {
            "pubmed":          len(pubmed),
            "europepmc":       len(europepmc),
            "clinicaltrials":  len(clinicaltrials),
            "reddit":          len(reddit),
        },
        "pubmed":          pubmed,
        "europepmc":       europepmc,
        "clinicaltrials":  clinicaltrials,
        "reddit":          reddit,
    }
