---
name: Query Orchestrator
description: Feature 001 v1 — language detection + scientific English translation before collector calls
---

## Rule
Every search endpoint (`/search`, `/pipeline/run`, `/experiences/ingest`) passes the user query through `QueryOrchestrator.process(q)` before calling any collector. The collectors always receive `orch.search_query` (English), not the raw user input.

**Why:** PubMed, EuropePMC, and ClinicalTrials.gov return significantly fewer results for non-English queries. Translating first ensures equivalent recall regardless of input language.

## How to apply
- Module: `hleo_v1/core/orchestrator.py`
- Module-level singleton in `main.py`: `_orchestrator = QueryOrchestrator()`
- All search endpoints call `orch = _orchestrator.process(q)` and use `orch.search_query` for collection
- All responses include an `"orchestration"` key with `orch.to_dict()` (original_query, search_query, detected_language, translation_applied, confidence)
- Single gpt-4o-mini call with `response_format={"type": "json_object"}`, temperature=0, max_tokens=150
- Process-lifetime MD5-keyed cache prevents duplicate GPT calls for the same query text

## Extension points (future versions)
- v2: add query expansion / MeSH term injection step in `_run()`
- v3: accept session context in `process()` for context-aware translation
- v4: multi-language result fusion (translate back, re-rank)

## Verified behaviour
- IT query `"finasteride perdita capelli effetti collaterali"` → detected `it`, translated to `"finasteride hair loss side effects"`, all three collectors return results
- EN query passes through unchanged (`translation_applied: False`)
- Cache hit: repeated identical query skips GPT call
