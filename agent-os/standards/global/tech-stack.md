## Tech Stack: Reader 3

### Framework & Runtime
- [cite_start]**Language:** Python 3.10+ [cite: 2189]
- [cite_start]**Package Manager:** uv [cite: 2172]
- [cite_start]**Web Framework:** FastAPI 
- [cite_start]**AI Framework:** Pydantic AI (with Logfire for tracing) [cite: 2183]

### Frontend & UI
- [cite_start]**Templating:** Jinja2 (server-side rendering) 
- [cite_start]**Styling:** CSS (in-template styles, no external CSS framework) [cite: 2291]
- [cite_start]**Interactivity:** Vanilla JavaScript (minimal, inline) [cite: 2191]

### Database & Storage
- [cite_start]**Data Persistence:** Python `pickle` serialization 
- **File Structure:**
  - [cite_start]`*_data/book.pkl`: Master book object [cite: 2181]
  - [cite_start]`*_data/chapters/*.json`: Chapter text & content hashes [cite: 2182]
  - `*_data/ai/*.json`: AI annotations & summaries [cite: 2182]

### Testing & Quality
- [cite_start]**Test Framework:** pytest (recommended, though currently no tests exist) [cite: 2195]
- [cite_start]**Linting/Formatting:** Standard Python (no specific formatter enforced yet) [cite: 2192]

### Development Standards
- [cite_start]**Vibe Coding:** The project prefers simple, "vibe coded" solutions over complex architecture. [cite: 2169]
- [cite_start]**Self-Contained:** The server trusts local `_data` folders implicitly. [cite: 2200]