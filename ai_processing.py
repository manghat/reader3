"""
AI processing pipeline for reader3 using PydanticAI with fallback stubs.

Outputs are stored per chapter in <book_dir>/ai/<index>.json.
"""

from __future__ import annotations

import json
import os
import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import logfire  # type: ignore
except ImportError:  # pragma: no cover - optional in dev
    logfire = None  # type: ignore

try:
    from pydantic_ai import Agent, RunContext  # type: ignore
except ImportError:  # pragma: no cover - optional in dev
    Agent = None  # type: ignore
    RunContext = None  # type: ignore


# --- Data containers ---

@dataclass
class ParagraphAnnotation:
    paragraph_id: str
    importance_score: Optional[float] = None
    summary: Optional[str] = None


@dataclass
class ChapterAIResult:
    chapter_index: int
    content_hash: str
    paragraph_annotations: List[ParagraphAnnotation]
    chapter_summary_short: Optional[str] = None
    chapter_summary_long: Optional[str] = None
    qa_items: Optional[List[Dict[str, str]]] = None
    reflection_prompts: Optional[List[str]] = None
    mindmap_mermaid: Optional[str] = None
    created_at: str = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_index": self.chapter_index,
            "content_hash": self.content_hash,
            "paragraph_annotations": [
                {
                    "paragraph_id": p.paragraph_id,
                    "importance_score": p.importance_score,
                    "summary": p.summary,
                }
                for p in self.paragraph_annotations
            ],
            "chapter_summary_short": self.chapter_summary_short,
            "chapter_summary_long": self.chapter_summary_long,
            "qa_items": self.qa_items,
            "reflection_prompts": self.reflection_prompts,
            "mindmap_mermaid": self.mindmap_mermaid,
            "created_at": self.created_at,
        }


# --- Helpers ---

def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _hash_for_paragraphs(paragraphs: List[Dict[str, Any]]) -> str:
    hasher = hashlib.sha256()
    for p in paragraphs:
        hasher.update(p.get("text", "").encode("utf-8"))
    return hasher.hexdigest()


def _fake_ai(paragraphs: List[Dict[str, Any]], content_hash: str, chapter_index: int) -> ChapterAIResult:
    """
    Deterministic fallback for local dev when PydanticAI is unavailable.
    """
    anns = []
    for idx, p in enumerate(paragraphs):
        importance = 1.0 if idx == 0 else max(0.2, 1.0 - idx * 0.05)
        summary = p.get("text", "")[:120]
        anns.append(ParagraphAnnotation(paragraph_id=p["id"], importance_score=importance, summary=summary))

    mindmap = "graph TD;\n  Start[Chapter]-->KeyIdea1;\n  Start-->KeyIdea2;\n  KeyIdea1-->DetailA;"

    return ChapterAIResult(
        chapter_index=chapter_index,
        content_hash=content_hash,
        paragraph_annotations=anns,
        chapter_summary_short="(stub) Short chapter summary.",
        chapter_summary_long="(stub) Long chapter summary expanding on main ideas.",
        qa_items=[{"question": "(stub) What is the key idea?", "answer": "Placeholder answer."}],
        reflection_prompts=["(stub) How would you apply this idea this week?"],
        mindmap_mermaid=mindmap,
    )


def _build_agent() -> Agent:
    """
    Configure the PydanticAI agent. Requires pydantic_ai to be installed and a provider set.
    """
    if Agent is None:
        raise RuntimeError("pydantic-ai is not installed. Add it to dependencies and install.")

    model = os.getenv("READER3_MODEL", "openai:gpt-4o-mini")
    system_prompt = (
        "You are an assistant that annotates EPUB chapters. "
        "For each paragraph, provide importance (0-1) and a short summary. "
        "Also provide chapter summaries, 3-5 Q&A pairs, 3-5 reflection prompts, "
        "and a Mermaid graph capturing main concepts."
    )

    # Minimal agent; downstream structured output is post-processed.
    return Agent(model=model, system_prompt=system_prompt)


async def _run_agent(agent: Agent, paragraphs: List[Dict[str, Any]]) -> ChapterAIResult:
    """
    Execute the agent call. The prompt requests structured JSON; the parser here is defensive.
    """
    # Build a simple prompt body with paragraph text.
    numbered = [f"{p['id']}: {p['text']}" for p in paragraphs]
    user_prompt = "\n".join(numbered)

    result = await agent.run(
        f"Annotate the following paragraphs:\n{user_prompt}\n\n"
        "Return JSON with keys: paragraph_annotations (list of {paragraph_id, importance_score, summary}), "
        "chapter_summary_short, chapter_summary_long, qa_items (list of {question, answer}), "
        "reflection_prompts (list), mindmap_mermaid (string)."
    )

    try:
        data = result.data if hasattr(result, "data") else result
    except Exception:
        data = result

    anns = []
    for item in data.get("paragraph_annotations", []):
        anns.append(
            ParagraphAnnotation(
                paragraph_id=item.get("paragraph_id"),
                importance_score=item.get("importance_score"),
                summary=item.get("summary"),
            )
        )

    return ChapterAIResult(
        chapter_index=data.get("chapter_index") or 0,
        content_hash=data.get("content_hash") or "",
        paragraph_annotations=anns,
        chapter_summary_short=data.get("chapter_summary_short"),
        chapter_summary_long=data.get("chapter_summary_long"),
        qa_items=data.get("qa_items"),
        reflection_prompts=data.get("reflection_prompts"),
        mindmap_mermaid=data.get("mindmap_mermaid"),
    )


# --- Public API ---

async def process_chapter_ai(book_dir: Path, chapter_index: int, force: bool = False) -> ChapterAIResult:
    """
    Load paragraph data for a chapter, run AI processing, and persist results.
    Skips processing if ai/<idx>.json exists with matching content_hash unless force=True.
    """
    chapters_path = book_dir / "chapters" / f"{chapter_index}.json"
    ai_path = book_dir / "ai" / f"{chapter_index}.json"

    if not chapters_path.exists():
        raise FileNotFoundError(f"Chapter data missing: {chapters_path}")

    chapter_doc = _load_json(chapters_path)
    paragraphs = chapter_doc.get("paragraphs", [])
    content_hash = chapter_doc.get("content_hash") or _hash_for_paragraphs(paragraphs)

    if ai_path.exists() and not force:
        existing = _load_json(ai_path)
        if existing.get("content_hash") == content_hash:
            return ChapterAIResult(
                chapter_index=existing.get("chapter_index", chapter_index),
                content_hash=content_hash,
                paragraph_annotations=[
                    ParagraphAnnotation(
                        paragraph_id=p.get("paragraph_id"),
                        importance_score=p.get("importance_score"),
                        summary=p.get("summary"),
                    )
                    for p in existing.get("paragraph_annotations", [])
                ],
                chapter_summary_short=existing.get("chapter_summary_short"),
                chapter_summary_long=existing.get("chapter_summary_long"),
                qa_items=existing.get("qa_items"),
                reflection_prompts=existing.get("reflection_prompts"),
                mindmap_mermaid=existing.get("mindmap_mermaid"),
                created_at=existing.get("created_at", existing.get("saved_at", datetime.now().isoformat())),
            )

    # If logfire is installed, start a span.
    if logfire:
        logfire.info("Processing AI for chapter", book_dir=str(book_dir), chapter_index=chapter_index)

    use_stub = os.getenv("READER3_FAKE_AI", "0") == "1" or Agent is None
    agent = None
    if not use_stub:
        try:
            agent = _build_agent()
        except Exception as e:  # Defensive: mismatched pydantic_ai versions or bad config
            use_stub = True
            if logfire:
                logfire.error("AI agent init failed, using stub", error=str(e))

    if use_stub or agent is None:
        result = _fake_ai(paragraphs, content_hash, chapter_index)
    else:
        try:
            result = await _run_agent(agent, paragraphs)
            result.content_hash = content_hash
            result.chapter_index = chapter_index
        except Exception as e:
            # Fallback to stub if the provider errors (e.g., missing key)
            if logfire:
                logfire.error("AI provider error, using stub", error=str(e))
            result = _fake_ai(paragraphs, content_hash, chapter_index)

    _write_json(ai_path, result.to_dict())
    return result
