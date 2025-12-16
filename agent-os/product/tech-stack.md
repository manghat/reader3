# Product Tech Stack

## Runtime & Package Management
- Python 3.10+
- Package manager: `uv` with `pyproject.toml` + `uv.lock` (keep deps minimal and documented)
- Web server: Uvicorn (FastAPI ASGI)

## Backend & Web
- FastAPI for HTTP endpoints
- Jinja2 server-side templates for library/reader views
- Inline/minimal vanilla JS for interactions (TTS controls, highlighting, voice capture)
- CSS scoped in templates (no external framework)

## AI & Processing
- Pydantic AI for AI orchestration; Logfire for tracing/observability (optional)
- Model provider configured via `READER3_MODEL` (e.g., `openai:gpt-4o-mini`)
- Chapter-level AI artifacts cached at `<book>_data/ai/<chapter>.json` (explain/summarize/mind map/Q&A)

## TTS
- Replicate-hosted Kokoro TTS (current choice)
- Supports paragraph/chapter audio generation; cache audio assets for reuse
- Text–audio sync layer drives highlight timing in the reader UI

## Storage & Data
- File-based persistence per book:
  - `<book>_data/book.pkl` for master book object
  - `<book>_data/chapters/<index>.json` for chapter text + hashes
  - `<book>_data/ai/<index>.json` for AI overlays
  - Cached audio assets alongside book data
- Serialization: pickle + JSON; no external DB

## Frontend Experience
- Server-rendered HTML (Jinja) with responsive layout targets (desktop + mobile-friendly pass planned)
- Reader UI elements: chapter navigation, AI overlays, TTS player, highlight sync, voice reflection controls

## Testing & Quality
- Recommended: pytest for unit/flow tests (none committed yet)
- Manual flows: `uv run reader3.py <book.epub>` then `uv run server.py`; trigger AI/TTS per chapter

## Deployment & Ops
- Self-host focus: run `uv run server.py` with env vars for AI/TTS keys
- Provide example env/config for Replicate + AI provider; process manager suggested for uptime
- Logging/tracing via Logfire when configured; otherwise standard server logs
