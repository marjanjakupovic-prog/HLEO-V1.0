---
name: Session Management
description: Feature 003 – AI session lifecycle, isolation, and limit enforcement
---

# Session Management (Feature 003)

## The rule
ChatSession has 5 new columns (status, search_query, search_context, updated_at, closed_at). These were added via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` — `Base.metadata.create_all` does NOT add columns to already-existing Postgres tables.

**Why:** The project uses managed Postgres (not SQLite). create_all is idempotent for new tables but does nothing for new columns on existing tables. Any future model change to existing tables needs an explicit ALTER TABLE migration script.

**How to apply:** When adding columns to any existing model (ChatSession, ChatMessage, PartnerRegistry, etc.), run a migration with `engine.connect()` + `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` before restarting the app.

## Limits (backend-enforced)
- `_MAX_ACTIVE = 10` and `_MAX_CLOSED = 20` constants in `main.py`
- All limit checks use `func.count()` queries at request time — no cached counters
- 409 status + exact spec error message string on violation

## Session isolation
- `/assistant/chat` rejects messages to closed sessions (409)
- `search_context` is persisted to `ChatSession.search_context` (JSON) on every chat call that carries one
- When no `search_context` is sent by the frontend, the backend loads `session.search_context` from DB and rebuilds a `SearchContext` object — guarantees the AI never sees context from a different session
- Frontend `openSession()` restores `_activeSearchCtx` from the session's stored `search_context` on load

## Endpoints added
- `POST /assistant/sessions` — create (10-active limit)
- `PATCH /assistant/sessions/{id}` — rename / close / reopen (with respective limits)
- `DELETE /assistant/sessions/{id}` — permanent delete (messages + session row)
- `GET /assistant/sessions` — returns `{ active: [...], closed: [...] }` with message_count, updated_at, closed_at
- `GET /assistant/sessions/{id}` — now includes `search_context` and `status` fields
