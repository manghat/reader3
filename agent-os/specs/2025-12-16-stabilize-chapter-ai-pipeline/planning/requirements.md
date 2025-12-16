# Spec Requirements: Stabilize Chapter AI Pipeline

## Initial Description
Stabilize chapter AI pipeline — tighten per-chapter AI job flow (error handling, retries, caching), ensure explain/summarize/mind map/Q&A payloads are generated deterministically and stored per chapter.

## Requirements Discussion

### First Round Questions

**Q1:** I assume the scope is per-chapter AI generation for explain/summarize/mind map/Q&A (no other modes), writing outputs to `<book>_data/ai/<chapter>.json`. Is that correct, or should we include any additional overlays or per-paragraph outputs?  
**Answer:** This is correct for now; continue with the current flow.

**Q2:** I’m assuming we should standardize deterministic runs (fixed model, low temperature, consistent prompts) and avoid overwriting cached results unless the user explicitly reprocesses a chapter. Should reprocess overwrite in place, or create versioned snapshots?  
**Answer:** Deterministic and reruns should be versioned.

**Q3:** For reliability, should we add retry/backoff for transient provider errors and mark chapters with a clear “needs retry” state in the UI/logs rather than failing silently?  
**Answer:** Yes, if it is not too complicated.

**Q4:** Should AI processing stay single-chapter at a time (user-triggered from the UI/API), or do you want a batch mode to process multiple chapters with controlled concurrency?  
**Answer:** User-triggered always.

**Q5:** Do we need guardrails on input size (chunking long chapters) and timeouts per AI call, with partial saves if some steps succeed and others fail?  
**Answer:** Should be fine as-is.

**Q6:** For observability, should we instrument with Logfire (or structured logs) to capture prompt/response metadata minus PII, and surface minimal status back to the UI?  
**Answer:** Yes, use Logfire for instrumentation; during development, instrument visualization.

**Q7:** Anything explicitly out of scope for this spec (e.g., TTS, voice reflections, exports), so we keep this focused on the AI pipeline?  
**Answer:** Only do text processing; focus on prompts and UX first, TTS/voice/reflections later.

### Existing Code to Reference
**Similar Features Identified:**
- UI/templates: continue in the style of `templates/library.html` and `templates/reader.html`; keep pages mobile responsive and current setup unless a deviation is clearly beneficial.

No other similar existing features identified for reference.

### Follow-up Questions
None.

