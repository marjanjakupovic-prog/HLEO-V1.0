---
name: HLEO architecture
description: Key architectural decisions for the HLEO v1.0 clinical research pipeline on Replit
---

## Architecture

**Run command:** `cd hleo_v1 && uvicorn api.main:app --host 0.0.0.0 --port 5000`

**DB:** Replit managed Postgres via `DATABASE_URL` env var. Tables auto-created on startup via `Base.metadata.create_all`.

**Tables (5):**
- `hleo_raw_sources` — raw ingested sources
- `hleo_clinical_profiles` — LLM-extracted profiles from articles (PubMed/EuropePMC/ClinicalTrials)
- `hleo_patient_experiences` — LLM-extracted structured journeys from Reddit posts
- `hleo_source_attributions` — provenance links from profile → original article
- `hleo_chat_sessions` + `hleo_chat_messages` — AI Clinical Assistant history

**LLM Models used:** `gpt-4o` throughout; `openai==2.50.0` required (2.x API).

**Two extraction schemas:**
- `core/clinical_schema.py → ClinicalProfile` — for scientific articles
- `core/patient_schema.py → PatientExperienceProfile` — for Reddit posts

**API endpoints:** GET `/search`, POST `/pipeline/run`, GET `/profiles`, POST `/experiences/ingest`, GET `/experiences`, POST `/assistant/chat`, GET `/assistant/sessions/{id}`

**UI:** Single-page Jinja2 template (`templates/index.html`), Tailwind CDN, four nav tabs: Search / Profiles / Experiences / AI Assistant.

**Why:** No Docker on Replit; all DB through managed Postgres; openai 1.x → 2.x upgrade was required due to httpx 0.28 incompatibility.
