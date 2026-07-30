---
name: Context-Aware Assistant
description: Feature 002 — ChatRequest carries active search context; system prompt enforces 3-priority source order
---

## Rule
The assistant system prompt is structured in three explicit priority blocks whenever `search_context` is provided:
  1. **PRIORITY 1 — CURRENT SEARCH RESULTS** (articles from the user's last search)
  2. **PRIORITY 2 — HLEO DATABASE** (existing RAG over stored clinical profiles + patient experiences)
  3. **PRIORITY 3 — GENERAL KNOWLEDGE** (only if 1 and 2 are insufficient, must be declared)

**Why:** Without this, the model defaults to general knowledge even when fresh evidence is available in the search results, which violates HLEO's "evidence-first" philosophy.

## How to apply

### Backend (`api/main.py`)
- `ChatRequest` has an optional `search_context: Optional[SearchContext]` field
- `SearchContext` carries: `original_query`, `search_query` (EN), `detected_language`, `articles: List[SearchArticleCtx]`
- Each `SearchArticleCtx`: `source` ("pubmed"|"europepmc"|"clinicaltrials"), `title`, `abstract` (up to 600 chars), `url`
- When `search_context.articles` is non-empty, the search block leads the system prompt with explicit referencing instructions
- When search context is present but empty, a notice tells the model to declare general-knowledge fallback explicitly

### Frontend (`templates/index.html`)
- State: `let _activeSearchCtx = null;`
- After `GET /search` succeeds: populate `_activeSearchCtx` from `data.orchestration` + `allSearchResults` (reddit excluded, abstracts capped at 600 chars)
- `sendMessage()` includes `search_context: _activeSearchCtx` in the POST body — no UI change, purely data flow
- `_activeSearchCtx` is `null` until the first search, so existing assistant sessions without a prior search are unaffected

## Verified behaviour
- Without search context: uses DB RAG + general knowledge as before
- With search context (3 articles): response opens with "Nei risultati della tua ricerca..." cites [PubMed] / [Europe PMC] inline, no generic opener
