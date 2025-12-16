# Task Breakdown: Stabilize Chapter AI Pipeline

## Overview
Total Tasks: 12

## Task List

### Backend: AI Pipeline Reliability

#### Task Group 1: Deterministic runs, caching, versioning
**Dependencies:** None

- [ ] 1.0 Ensure deterministic AI invocation
  - [ ] 1.1 Fix model/temperature/prompts to stable defaults for explain/summarize/mind map/Q&A
  - [ ] 1.2 Preserve content_hash gating; only rerun on force or content change
  - [ ] 1.3 Validate required fields before write; sanitize lengths
- [ ] 1.4 Versioned reruns
  - [ ] 1.4.1 Before overwrite, archive to `ai/history/<chapter>-<timestamp>.json`
  - [ ] 1.4.2 Record run metadata (run id/timestamp/model/settings/content_hash/status)
  - [ ] 1.4.3 Expose last run timestamp and source (cache/fresh) in API response

**Acceptance Criteria:**
- AI outputs deterministic given same input; content_hash skip respected.
- Forced runs create history copy with metadata; latest file updated safely (temp-then-move).

#### Task Group 2: Reliability, retries, concurrency guard
**Dependencies:** Task Group 1

- [ ] 2.0 Add bounded retry/backoff for transient provider errors
  - [ ] 2.0.1 Limit attempts; log failures; fall back to stub only when explicitly configured
- [ ] 2.1 Mark failure/needs-retry status in output/response
- [ ] 2.2 Guard concurrent runs per chapter (serialize or short-circuit in-flight)
- [ ] 2.3 Fail fast for missing chapter data; keep explicit stub path via `READER3_FAKE_AI`

**Acceptance Criteria:**
- Transient failures retried within bounds; failures reported with status and message.
- Concurrent triggers on same chapter do not collide; missing data errors are explicit.

#### Task Group 3: Logging & observability (Logfire/structured logs)
**Dependencies:** Task Group 1

- [ ] 3.0 Add Logfire spans around agent init, calls, retries, and writes (omit PII)
- [ ] 3.1 Log structured fields: book_id, chapter_index, content_hash, model, duration, status, source (cache/fresh)
- [ ] 3.2 Ensure logs degrade gracefully when Logfire unavailable

**Acceptance Criteria:**
- Logs/spans emitted for success/failure with key metadata; no crashes when Logfire missing.

### API Layer

#### Task Group 4: API response/status surface
**Dependencies:** Task Groups 1-2

- [ ] 4.0 Extend `/read/{book_id}/{chapter_index}/process_ai` response to include status, last_run_at, source (cache/fresh), error (if any)
- [ ] 4.1 Ensure error handling returns clear HTTP messages (non-PII), with needs-retry indicator

**Acceptance Criteria:**
- API returns enriched status payload; failures are clear and safe.

### Frontend (Templates/UI)

#### Task Group 5: Reader UI feedback & responsiveness
**Dependencies:** Task Group 4

- [ ] 5.0 Update `templates/reader.html` to show statuses: idle, processing, failed/needs retry, last processed timestamp
- [ ] 5.1 Add retry CTA wired to existing trigger; reflect loading/error states
- [ ] 5.2 Ensure mobile responsiveness for status/CTA elements (per responsive standards)

**Acceptance Criteria:**
- Users see processing/failed/success states and last-run time; mobile layout remains usable.

### Testing (Targeted)

#### Task Group 6: Focused tests (backend/API/UI flow)
**Dependencies:** Task Groups 1-5

- [ ] 6.0 Add 2-6 focused tests total (or dev-time scripts) covering:
  - [ ] 6.0.1 Cache skip vs force path
  - [ ] 6.0.2 Versioned rerun writes history and metadata
  - [ ] 6.0.3 Retry/failure marks status in response
- [ ] 6.1 Run only the above targeted tests/scripts (keep fast; mock AI provider)

**Acceptance Criteria:**
- Targeted tests pass; behaviors verified for cache/force, history, and failure status.
