import json
import os
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from reader3 import Book, BookMetadata, ChapterContent, TOCEntry
from ai_hello import run_hello, AIHelloError


import logfire  # type: ignore

load_dotenv(override=False)

app = FastAPI()

env = os.getenv("LOGFIRE_ENV", "local")
logfire.configure(environment=env)
logfire.instrument_fastapi(app)
logfire.instrument_pydantic_ai()  # instrument PydanticAI agents
    
templates = Jinja2Templates(directory="templates")

# Where are the book folders located?
BOOKS_DIR = "."


def load_json_if_exists(path: str) -> Optional[Dict[str, Any]]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def combine_paragraph_annotations(paragraphs: List[Dict[str, Any]], ai_doc: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge paragraph text/html with AI annotations for rendering.
    """
    annotations = {}
    if ai_doc:
        for ann in ai_doc.get("paragraph_annotations", []):
            annotations[ann.get("paragraph_id")] = ann

    combined = []
    for p in paragraphs:
        ann = annotations.get(p["id"], {})
        score = ann.get("importance_score")
        importance_class = "importance-none"
        if isinstance(score, (int, float)):
            if score >= 0.75:
                importance_class = "importance-high"
            elif score >= 0.4:
                importance_class = "importance-medium"
            else:
                importance_class = "importance-low"

        combined.append({
            **p,
            "importance_score": score,
            "importance_class": importance_class,
            "summary_ai": ann.get("summary"),
        })

    return combined


@app.get("/api/hello-ai", response_class=JSONResponse)
async def hello_ai(model: Optional[str] = None):
    """
    Simple AI smoke test endpoint. Returns a short message to confirm model connectivity.
    """
    try:
        result = await run_hello(model=model)
        return JSONResponse(result)
    except AIHelloError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@lru_cache(maxsize=10)
def load_book_cached(folder_name: str) -> Optional[Book]:
    """
    Loads the book from the pickle file.
    Cached so we don't re-read the disk on every click.
    """
    file_path = os.path.join(BOOKS_DIR, folder_name, "book.pkl")
    if not os.path.exists(file_path):
        return None

    try:
        with open(file_path, "rb") as f:
            book = pickle.load(f)
        return book
    except Exception as e:
        print(f"Error loading book {folder_name}: {e}")
        return None


def find_cover_image(book_id: str, book: Book) -> Optional[str]:
    """
    Attempt to find a cover image path for the given book by scanning its image map.
    Prefers filenames containing 'cover'; falls back to the first image if none match.
    Returns a URL usable by the /read/{book_id}/images/{image_name} route.
    """
    if not book or not book.images:
        return None

    # Prefer image keys that look like a cover
    def pick_first(paths: List[str]) -> Optional[str]:
        for p in paths:
            if p:
                return p
        return None

    cover_candidates = [rel for orig, rel in book.images.items() if "cover" in orig.lower() or "cover" in rel.lower()]
    rel_path = pick_first(cover_candidates) or pick_first(list(book.images.values()))

    if not rel_path:
        return None

    rel_path = rel_path.lstrip("./")
    # book.images values are typically like "images/<file>"
    if rel_path.startswith("images/"):
        image_name = os.path.basename(rel_path)
        return f"/read/{book_id}/images/{image_name}"

    return f"/read/{book_id}/{rel_path}"


def find_section_path(toc: List[TOCEntry], target_href: str) -> List[Dict[str, str]]:
    """
    Return a breadcrumb-like list of dicts from the root TOC to the matching href.
    Each entry contains title and href (file_href) for display.
    """
    def normalize(h: str) -> str:
        cleaned = unquote(h or "").lstrip("./")
        return cleaned.split("#")[0]

    target_norm = normalize(target_href)
    target_base = os.path.basename(target_norm)

    def matches(node_href: str) -> bool:
        node_norm = normalize(node_href)
        node_base = os.path.basename(node_norm)
        return node_norm == target_norm or node_base == target_base

    def walk(nodes: List[TOCEntry], path: List[Dict[str, str]]) -> Optional[List[Dict[str, str]]]:
        for node in nodes:
            current = path + [{"title": node.title, "href": node.file_href}]
            if matches(node.file_href):
                return current
            if node.children:
                found = walk(node.children, current)
                if found:
                    return found
        return None

    return walk(toc, []) or []

@app.get("/", response_class=HTMLResponse)
async def library_view(request: Request):
    """Lists all available processed books."""
    books = []

    # Scan directory for folders ending in '_data' that have a book.pkl
    if os.path.exists(BOOKS_DIR):
        for item in os.listdir(BOOKS_DIR):
            if item.endswith("_data") and os.path.isdir(item):
                # Try to load it to get the title
                book = load_book_cached(item)
                if book:
                    books.append({
                        "id": item,
                        "title": book.metadata.title,
                        "author": ", ".join(book.metadata.authors),
                        "chapters": len(book.spine),
                        "cover_url": find_cover_image(item, book)
                    })

    return templates.TemplateResponse("library.html", {"request": request, "books": books})

@app.get("/read/{book_id}", response_class=HTMLResponse)
async def redirect_to_first_chapter(book_id: str):
    """Helper to just go to chapter 0."""
    return await read_chapter(book_id=book_id, chapter_index=0)

@app.get("/read/{book_id}/{chapter_index}", response_class=HTMLResponse)
async def read_chapter(request: Request, book_id: str, chapter_index: int):
    """The main reader interface."""
    book = load_book_cached(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if chapter_index < 0 or chapter_index >= len(book.spine):
        raise HTTPException(status_code=404, detail="Chapter not found")

    current_chapter = book.spine[chapter_index]
    book_dir = os.path.join(BOOKS_DIR, book_id)

    # Optional structured chapter and AI docs
    chapter_doc = load_json_if_exists(os.path.join(book_dir, "chapters", f"{chapter_index}.json"))
    ai_doc = None
    paragraphs_for_render = []
    if chapter_doc and chapter_doc.get("paragraphs"):
        paragraphs_for_render = combine_paragraph_annotations(chapter_doc["paragraphs"], ai_doc)

    # Calculate Prev/Next links
    prev_idx = chapter_index - 1 if chapter_index > 0 else None
    next_idx = chapter_index + 1 if chapter_index < len(book.spine) - 1 else None
    section_path = find_section_path(book.toc, current_chapter.href)
    if not section_path:
        section_path = [{"title": current_chapter.title, "href": current_chapter.href}]

    return templates.TemplateResponse("reader.html", {
        "request": request,
        "book": book,
        "current_chapter": current_chapter,
        "chapter_index": chapter_index,
        "book_id": book_id,
        "prev_idx": prev_idx,
        "next_idx": next_idx,
        "chapter_doc": chapter_doc,
        "ai_doc": ai_doc,
        "paragraphs": paragraphs_for_render,
        "section_path": section_path,
    })

@app.get("/read/{book_id}/images/{image_name}")
async def serve_image(book_id: str, image_name: str):
    """
    Serves images specifically for a book.
    The HTML contains <img src="images/pic.jpg">.
    The browser resolves this to /read/{book_id}/images/pic.jpg.
    """
    # Security check: ensure book_id is clean
    safe_book_id = os.path.basename(book_id)
    safe_image_name = os.path.basename(image_name)

    img_path = os.path.join(BOOKS_DIR, safe_book_id, "images", safe_image_name)

    if not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(img_path)


if __name__ == "__main__":
    import uvicorn
    print("Starting server at http://127.0.0.1:8123")
    uvicorn.run(app, host="127.0.0.1", port=8123)
