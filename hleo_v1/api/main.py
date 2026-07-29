import logging

from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from core.database import get_db, engine, Base
from core.models import ClinicalProfile, RawSource, AuditLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="HLEO API", version="1.0.0")

# Create tables on startup
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
