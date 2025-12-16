# Product Roadmap

1. [x] Stabilize chapter AI pipeline — Tighten per-chapter AI job flow (error handling, retries, caching), ensure explain/summarize/mind map/Q&A payloads are generated deterministically and stored per chapter. `[S]`
2. [ ] Ship chapter overlays UI — Wire the AI outputs into the reader UI with clear triggers, loading/error states, and cached reload behavior so users reliably see overlays on every chapter. `[M]`
3. [ ] Integrate TTS playback (Replicate Kokoro) — Add backend calls to Replicate for paragraph/chapter audio, cache audio artifacts, and expose player controls (play/pause/seek) in the reader. `[M]`
4. [ ] Text–audio sync highlighting — Align TTS playback with paragraph/phrase highlights in the UI, including fallbacks for imperfect alignment and a toggle to disable syncing if needed. `[S]`
5. [ ] Voice-driven reflection sessions — Enable voice capture, send book/chapter context to AI for guided questioning, surface transcripts and follow-ups in the reader, and cache sessions per chapter. `[L]`
6. [ ] Reflection exports and replays — Let users export summaries/prompts and replay past sessions to review key takeaways or share with peers. `[S]`
7. [ ] Responsive/mobile reader pass — Optimize library/reader layouts, controls, and TTS/voice UI for mobile and touch, keeping chapter navigation and overlays usable on smaller screens. `[S]`
8. [ ] Self-host deploy profile — Provide configuration/env examples for TTS and AI keys, logging defaults, and a simple production run profile (process manager/docs) to host the experience reliably. `[S]`

> Notes
> - Ordered by dependencies: stabilize AI → surface overlays → add TTS → sync highlights → add voice reflection → exports → mobile polish → hosting profile.
> - Each item is end-to-end and testable via UI + API; avoid bootstrapping tasks since the app already exists.
