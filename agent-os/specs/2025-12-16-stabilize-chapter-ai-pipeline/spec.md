# Specification: Stabilize Chapter AI Pipeline

## Goal
Deliver reliable, deterministic chapter-level AI overlays (explain/summarize/mind map/Q&A) with user-triggered runs, versioned outputs, clear status, and observability, without expanding scope beyond text processing.

## User Stories
- As a reader, I want AI overlays to generate reliably per chapter so I can trust summaries and Q&A without rerunning repeatedly.
- As a developer/operator, I want reruns to create versioned outputs and log diagnostics so I can debug failures without losing prior results.
- As a reader, I want clear UI feedback when AI processing is running or failed so I know when to retry.

## Specific Requirements

**Deterministic AI runs**
- Use fixed model/temperature and stable prompts for explain/summarize/mind map/Q&A to produce predictable outputs.
- Preserve existing content_hash gating; only rerun when forced or when hash changes.
- Ensure AI payload fields remain consistent with `ai/<chapter>.json` schema consumed by templates.

**Versioned reruns**
- On forced rerun, keep a versioned copy (e.g., `ai/history/<chapter>-<timestamp>.json`) before overwriting `ai/<chapter>.json`.
- Store run metadata (run id/timestamp/model/settings/content_hash) in both latest and versioned files.
- Provide a lightweight way to surface the latest run timestamp in UI/API responses.

**Retry and error handling**
- Add bounded retry/backoff for transient provider errors; stop after few attempts and flag failure.
- Record failure status and error message in AI result (or sidecar) so UI can display “needs retry.”
- Fail fast on missing chapter data; avoid silent fallbacks except explicit stub mode.

**Triggering and execution model**
- Keep processing user-triggered, single chapter at a time (no batch mode).
- Guard against concurrent runs on the same chapter (serialize or short-circuit if in-flight).
- Respect existing `READER3_FAKE_AI` stub path for offline/dev.

**Caching and skips**
- If `ai/<chapter>.json` exists with matching content_hash and no force flag, skip processing and return cached results.
- When content_hash differs, treat as stale and rerun automatically; archive previous output in history.

**Logging and observability**
- Instrument with Logfire spans/metrics around agent init, calls, retries, and writes (omit PII).
- Include structured logs for success/failure, model used, duration, and content_hash.
- Expose minimal status in the API response (e.g., status, run timestamp, source=cache/fresh).

**UI feedback (templates/reader.html)**
- Show explicit states: idle, processing, failed/needs retry, and last processed timestamp.
- Keep current style but ensure mobile responsiveness for status elements and CTA (process button).
- Surface simple error text from backend (non-PII) and offer a retry CTA.

**Data integrity and validation**
- Validate required fields before write (paragraph ids, summaries, mind map string, QA/reflection lists).
- Sanitize/limit lengths to prevent oversized payloads breaking render.
- Ensure JSON written with UTF-8 and stable ordering; avoid partial writes (write temp then move).

## Visual Design
No mockups provided.

## Existing Code to Leverage

**ai_processing.process_chapter_ai** (ai_processing.py)
- Handles content_hash skip logic, stub mode, and JSON write path; extend with retries/versioning/metadata.

**server.py `process_ai_endpoint`**
- Maintains POST trigger per chapter; enhance responses to include status/timestamps and error states.

**templates/reader.html + combine_paragraph_annotations** (server.py)
- Existing rendering of AI overlays and process button; add status/failed banners while preserving styling and making responsive.

## Out of Scope
- TTS playback, highlight sync, or any audio features.
- Voice-driven reflections, exports, or session replays.
- Batch processing across multiple chapters.
- New overlay types beyond explain/summarize/mind map/Q&A.
- Major UI redesign or theming (dark mode) beyond minimal status/responsiveness tweaks.
