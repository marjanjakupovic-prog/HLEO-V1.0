# HLEO v1.0

A clinical research pipeline that collects data from Reddit, PubMed, EuropePMC, and ClinicalTrials, then uses an OpenAI LLM to extract and classify clinical profiles (originally focused on trichology/hair-loss treatments).

## How to run

The app is a FastAPI server. The workflow `Start application` runs it:

```
cd hleo_v1 && uvicorn api.main:app --host 0.0.0.0 --port 5000
```

- Dashboard: `/`
- Health check: `/health`
- Database stats: `/stats`
- Swagger UI: `/docs`

## Stack

- **Backend**: FastAPI + Uvicorn (Python)
- **Database**: PostgreSQL (Replit managed — uses `DATABASE_URL` env var)
- **ORM**: SQLAlchemy 2.x
- **LLM**: OpenAI `gpt-4o` (requires `OPENAI_API_KEY` secret)
- **Data sources**: Reddit (public API), PubMed, EuropePMC, ClinicalTrials

## Required secrets

| Secret | Purpose |
|--------|---------|
| `OPENAI_API_KEY` | LLM extraction and clinical profile classification |

## Project structure

```
hleo_v1/
  api/main.py          — FastAPI app entry point
  core/
    database.py        — SQLAlchemy engine, session, Base, get_db()
    models.py          — ORM models (RawSource, ClinicalProfile, AuditLog)
    schemas.py         — Pydantic schemas
    extractor.py       — LLM-based clinical profile extractor
    validator.py       — Profile validation logic
    judge.py           — Category assignment logic
    pipeline.py        — End-to-end pipeline (collect → extract → validate → judge)
  collectors/          — Data collectors (Reddit, PubMed, EuropePMC, ClinicalTrials)
  search/              — Web search helpers (Bing, SearXNG, deduplication)
  crawlers/            — HTML crawler + text extractor
  tests/               — pytest test suite
```

## Notes

- The desktop GUI (`app.py` / `ui/`) uses PySide6 and cannot run on Replit (no display).
- Docker Compose (`docker-compose.yml`) is the original local setup; not used on Replit.
- Database tables are created automatically on startup via `Base.metadata.create_all(bind=engine)`.
