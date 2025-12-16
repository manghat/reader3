# reader 3

![reader3](reader3.png)

A lightweight, self-hosted EPUB reader that lets you read through EPUB books one chapter at a time. This makes it very easy to copy paste the contents of a chapter to an LLM, to read along. Basically - get epub books (e.g. [Project Gutenberg](https://www.gutenberg.org/) has many), open them up in this reader, copy paste text around to your favorite LLM, and read together and along.

This project was 90% vibe coded just to illustrate how one can very easily [read books together with LLMs](https://x.com/karpathy/status/1990577951671509438). I'm not going to support it in any way, it's provided here as is for other people's inspiration and I don't intend to improve it. Code is ephemeral now and libraries are over, ask your LLM to change it in whatever way you like.

## Usage

The project uses [uv](https://docs.astral.sh/uv/). So for example, download [Dracula EPUB3](https://www.gutenberg.org/ebooks/345) to this directory as `dracula.epub`, then:

```bash
uv run reader3.py dracula.epub
```

This creates the directory `dracula_data`, which registers the book to your local library. We can then run the server:

```bash
uv run server.py
```

And visit [localhost:8123](http://localhost:8123/) to see your current Library. You can easily add more books, or delete them from your library by deleting the folder. It's not supposed to be complicated or complex.

## AI overlays (optional)

- Dependencies: `pydantic-ai` and `logfire` are listed in `pyproject.toml`. Install via `uv sync` if you manage a virtual env, or run directly with `uv run ...` (uv will handle an ephemeral env).
- Configure a model provider with `READER3_MODEL` (e.g., `openai:gpt-4o-mini`). Set `READER3_FAKE_AI=1` to use local stubbed outputs.
- From the reader view, click “Process AI” on a chapter to generate importance highlights, summaries, Q&A, reflections, and a Mermaid mind map. Results are cached under `<book>_data/ai/<chapter>.json`.

## Manual test flow

1) Convert an EPUB: `uv run reader3.py your_book.epub`
2) Start the server: `uv run server.py`
3) Open `http://127.0.0.1:8123`, choose your book, open a chapter.
4) Click “Process AI” to generate overlays; reload auto-applies cached results. Paragraphs will gain highlight tiers and optional summary toggles; sidebar tabs show summaries/Q&A/reflections/mind map.

## License

MIT
