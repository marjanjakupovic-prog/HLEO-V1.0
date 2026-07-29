import logging
from dataclasses import asdict

from fastapi import FastAPI, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from core.database import get_db, engine, Base
from core.models import ClinicalProfile, RawSource, AuditLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="HLEO API", version="1.0.0")

Base.metadata.create_all(bind=engine)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>HLEO v1.0</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen flex items-center justify-center p-10">
        <div class="max-w-lg w-full bg-white rounded-xl shadow-md p-8">
            <h1 class="text-3xl font-bold text-blue-800 mb-2">HLEO v1.0</h1>
            <p class="text-gray-500 mb-6">Clinical Research Pipeline</p>
            <div class="space-y-3">
                <a href="/health" class="block px-4 py-2 bg-blue-50 rounded-lg text-blue-700 hover:bg-blue-100">
                    🩺 Health check
                </a>
                <a href="/docs" class="block px-4 py-2 bg-blue-50 rounded-lg text-blue-700 hover:bg-blue-100">
                    📄 API documentation (Swagger UI)
                </a>
                <a href="/stats" class="block px-4 py-2 bg-blue-50 rounded-lg text-blue-700 hover:bg-blue-100">
                    📊 Database stats
                </a>
                <a href="/search?q=cancer" class="block px-4 py-2 bg-green-50 rounded-lg text-green-700 hover:bg-green-100">
                    🔬 Example search: cancer
                </a>
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/stats")
def stats(db: Session = Depends(get_db)):
    profiles_count = db.execute(select(func.count()).select_from(ClinicalProfile)).scalar()
    sources_count = db.execute(select(func.count()).select_from(RawSource)).scalar()
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
        """Convert SearchResult / RawTestimonial dataclasses to dicts."""
        try:
            return asdict(obj)
        except TypeError:
            return str(obj)

    pubmed = [_sr(a) for a in raw["pubmed"]]
    europepmc = [_sr(a) for a in raw["europepmc"]]
    clinicaltrials = [_sr(a) for a in raw["clinicaltrials"]]
    reddit = [_sr(p) for p in raw["reddit"]]

    # Attempt full LLM processing only if extractor is ready
    llm_results = []
    llm_available = pipeline.extractor.client is not None
    if llm_available:
        llm_results = pipeline.process(q)

    return {
        "query": q,
        "llm_extraction": llm_available,
        "totals": {
            "pubmed": len(pubmed),
            "europepmc": len(europepmc),
            "clinicaltrials": len(clinicaltrials),
            "reddit": len(reddit),
        },
        "pubmed": pubmed,
        "europepmc": europepmc,
        "clinicaltrials": clinicaltrials,
        "reddit": reddit,
        **({"llm_processed": len(llm_results)} if llm_available else {}),
    }
