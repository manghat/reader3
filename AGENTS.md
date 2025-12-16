# Repository Guidelines

## Project Structure & Module Organization
- Core conversion pipeline: `reader3.py` parses EPUBs into `*_data/book.pkl` plus extracted `images/`.
- Per-chapter artifacts: `*_data/chapters/<index>.json` (paragraphs + hash) and `*_data/ai/<index>.json` (AI annotations).
- AI scaffold: `ai_processing.py` orchestrates PydanticAI/logfire and caches chapter results.
- Web server: `server.py` (FastAPI + Jinja) serves the library and chapters from the generated `_data` folders.
- HTML templates: `templates/library.html` and `templates/reader.html`.
- Assets/examples: `dracula.epub`, `dracula_data/`, and `reader3.png`.
- Project config: `pyproject.toml`; lockfile `uv.lock`. No dedicated tests directory yet.

## Build, Test, and Development Commands
- `uv run reader3.py <book.epub>`: convert an EPUB into a `<book>_data/` folder.
- `uv run server.py`: start the reader at `http://127.0.0.1:8123`.
- Trigger AI for a chapter: `curl -X POST http://127.0.0.1:8123/read/<book_id>/<chapter_index>/process_ai` (reload page to see overlays).
- `uv lock --upgrade`: refresh the dependency lock if you change `pyproject.toml`.
- There are no automated tests defined; add `uv run pytest` once tests exist.

## Coding Style & Naming Conventions
- Language: Python 3.10+. Prefer type hints for new functions and data structures.
- Indentation: 4 spaces; keep lines reasonably short for readability.
- HTML/CSS: keep styling within templates; avoid inline scripts unless necessary.
- Filenames: snake_case for Python; keep generated book folders suffixed with `_data`.
- No formatter is configured; if you add one, document it here and keep diffs minimal.

## Testing Guidelines
- Add targeted tests when changing EPUB parsing or routing. Pytest is recommended (add to `pyproject.toml` dependencies and `uv.lock`).
- Name tests `test_<module>.py`; use fixture EPUBs kept small and committed to `tests/data/`.
- Run locally with `uv run pytest` once tests are added; prefer fast, isolated cases over end-to-end.

## Commit & Pull Request Guidelines
- Commit messages: use clear, present-tense summaries (e.g., `Add epub parsing fallback`, `Tighten image path handling`).
- Pull requests should describe the change, include repro/verification steps (commands run), and note any new config or data files.
- If UI changes occur, include a short note of before/after behavior; screenshots are helpful but optional.

## Security & Configuration Tips
- The server trusts local `_data` folders; do not expose it publicly without hardening.
- Image and HTML content are sanitized lightly; review any third-party EPUBs before hosting.
- Avoid writing outside the project root; `BOOKS_DIR` defaults to `.` — adjust deliberately if changing deployment layout.
- AI config: set `READER3_MODEL` to your provider/model (e.g., `openai:gpt-4o-mini`). Set `READER3_FAKE_AI=1` to use stubbed outputs. Install and configure logfire to capture traces; otherwise it is a no-op.
