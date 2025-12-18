"""
AI processing pipeline for reader3 using PydanticAI with fallback stubs.

Outputs are stored per chapter in <book_dir>/ai/<index>.json.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

try:
    import logfire  # type: ignore
except ImportError:  # pragma: no cover - optional in dev
    logfire = None  # type: ignore

try:
    from pydantic_ai import Agent  # type: ignore
except ImportError:  # pragma: no cover - optional in dev
    Agent = None  # type: ignore


# --- Data containers ---

_logfire_configured = False

def _load_env_from_file(path: str = ".env") -> None:
    """
    Lightweight .env loader to avoid external deps.
    Only sets variables that are not already defined.
    """
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, val = stripped.split("=", 1)
        key = key.strip()
        val = val.strip()
        if key and key not in os.environ:
            os.environ[key] = val


def _configure_logfire_if_possible() -> None:
    global _logfire_configured
    if _logfire_configured or not logfire:
        return
    token = os.getenv("LOGFIRE_TOKEN")
    if not token:
        return
    try:
        # Configure once; ignore failures so the app still runs.
        logfire.configure(token=token)
        _logfire_configured = True
    except Exception:
        pass


_load_env_from_file()
_configure_logfire_if_possible()
AI_CALL_TIMEOUT = float(os.getenv("READER3_AI_TIMEOUT", "30.0"))


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
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "success"  # success | failed
    source: str = "fresh"  # fresh | cache | stub
    run_id: str = ""
    model: Optional[str] = None
    model_settings: Optional[Dict[str, Any]] = None
    run_duration_ms: Optional[float] = None
    error: Optional[str] = None

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
            "status": self.status,
            "source": self.source,
            "run_id": self.run_id,
            "model": self.model,
            "model_settings": self.model_settings,
            "run_duration_ms": self.run_duration_ms,
            "error": self.error,
        }


# --- Helpers ---

def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    tmp_path = Path(tmp_name)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


def _hash_for_paragraphs(paragraphs: List[Dict[str, Any]]) -> str:
    hasher = hashlib.sha256()
    for p in paragraphs:
        hasher.update(p.get("text", "").encode("utf-8"))
    return hasher.hexdigest()


def _truncate(text: Optional[str], limit: int) -> Optional[str]:
    if text is None:
        return None
    return str(text)[:limit]


def _sanitize_result(result: ChapterAIResult) -> ChapterAIResult:
    for ann in result.paragraph_annotations:
        ann.summary = _truncate(ann.summary, 500)
    result.chapter_summary_short = _truncate(result.chapter_summary_short, 1200)
    result.chapter_summary_long = _truncate(result.chapter_summary_long, 2400)
    if result.qa_items:
        clean_qa = []
        for qa in result.qa_items:
            clean_qa.append(
                {
                    "question": _truncate(qa.get("question"), 800),
                    "answer": _truncate(qa.get("answer"), 800),
                }
            )
        result.qa_items = clean_qa
    if result.reflection_prompts:
        result.reflection_prompts = [_truncate(p, 400) for p in result.reflection_prompts if p is not None]
    result.mindmap_mermaid = _truncate(result.mindmap_mermaid, 4000)
    return result


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
        source="stub",
    )


def _build_agent(model: str, temperature: float) -> Agent:
    """
    Configure the PydanticAI agent. Requires pydantic_ai to be installed and a provider set.
    """
    if Agent is None:
        raise RuntimeError("pydantic-ai is not installed. Add it to dependencies and install.")

    system_prompt = (
        "You are an assistant that annotates EPUB chapters. "
        "For each paragraph, provide importance (0-1) and a short summary. "
        "Also provide chapter summaries, 3-5 Q&A pairs, 3-5 reflection prompts, "
        "and a Mermaid graph capturing main concepts."
    )

    return Agent(model=model, system_prompt=system_prompt, model_settings={"temperature": temperature})


async def _run_agent(agent: Agent, paragraphs: List[Dict[str, Any]]) -> ChapterAIResult:
    """
    Execute the agent call. The prompt requests structured JSON; the parser here is defensive.
    """
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


async def _run_with_retries(agent: Agent, paragraphs: List[Dict[str, Any]], attempts: int = 3, backoff: float = 0.5) -> ChapterAIResult:
    last_exc: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            return await _run_agent(agent, paragraphs)
        except Exception as e:  # pragma: no cover - defensive
            last_exc = e
            if attempt < attempts:
                await asyncio.sleep(backoff * attempt)
    if last_exc:
        raise last_exc
    raise RuntimeError("AI failed without exception.")


def _archive_existing(ai_path: Path, history_dir: Path) -> None:
    if not ai_path.exists():
        return
    history_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    history_path = history_dir / f"{ai_path.stem}-{timestamp}{ai_path.suffix}"
    shutil.copy2(ai_path, history_path)


def _record_failure(
    chapter_index: int,
    content_hash: str,
    model: str,
    model_settings: Dict[str, Any],
    error: str,
    source: str,
    run_id: str,
) -> ChapterAIResult:
    return ChapterAIResult(
        chapter_index=chapter_index,
        content_hash=content_hash,
        paragraph_annotations=[],
        chapter_summary_short=None,
        chapter_summary_long=None,
        qa_items=None,
        reflection_prompts=None,
        mindmap_mermaid=None,
        status="failed",
        source=source,
        run_id=run_id,
        model=model,
        model_settings=model_settings,
        error=error,
    )


_inflight: Dict[Tuple[str, int], asyncio.Lock] = {}


def _get_lock(book_dir: Path, chapter_index: int) -> asyncio.Lock:
    key = (str(book_dir.resolve()), chapter_index)
    if key not in _inflight:
        _inflight[key] = asyncio.Lock()
    return _inflight[key]


# --- Public API ---

async def process_chapter_ai(book_dir: Path, chapter_index: int, force: bool = False) -> ChapterAIResult:
    """
    Load paragraph data for a chapter, run AI processing, and persist results.
    Skips processing if ai/<idx>.json exists with matching content_hash unless force=True.
    """
    chapters_path = book_dir / "chapters" / f"{chapter_index}.json"
    ai_path = book_dir / "ai" / f"{chapter_index}.json"
    history_dir = book_dir / "ai" / "history"

    if not chapters_path.exists():
        raise FileNotFoundError(f"Chapter data missing: {chapters_path}")

    chapter_doc = _load_json(chapters_path)
    paragraphs = chapter_doc.get("paragraphs", [])
    content_hash = chapter_doc.get("content_hash") or _hash_for_paragraphs(paragraphs)
    model = os.getenv("READER3_MODEL", "openai:gpt-4o-mini")
    model_settings: Dict[str, Any] = {"temperature": float(os.getenv("READER3_TEMPERATURE", "0.0"))}

    def _result_from_existing(existing: Dict[str, Any], source: str) -> ChapterAIResult:
        return ChapterAIResult(
            chapter_index=existing.get("chapter_index", chapter_index),
            content_hash=existing.get("content_hash", content_hash),
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
            status=existing.get("status", "success"),
            source=source,
            run_id=existing.get("run_id", ""),
            model=existing.get("model", model),
            model_settings=existing.get("model_settings", model_settings),
            run_duration_ms=existing.get("run_duration_ms"),
            error=existing.get("error"),
        )

    if ai_path.exists() and not force:
        existing = _load_json(ai_path)
        if existing.get("content_hash") == content_hash:
            return _result_from_existing(existing, "cache")

    lock = _get_lock(book_dir, chapter_index)
    async with lock:
        if ai_path.exists() and not force:
            existing = _load_json(ai_path)
            if existing.get("content_hash") == content_hash:
                return _result_from_existing(existing, "cache")

        use_stub = os.getenv("READER3_FAKE_AI", "0") == "1"
        run_id = str(uuid4())
        run_started = time.perf_counter()

        if logfire:
            logfire.info(
                "Processing AI for chapter",
                book_dir=str(book_dir),
                chapter_index=chapter_index,
                content_hash=content_hash,
                force=force,
                use_stub=use_stub,
                run_id=run_id,
                model=model,
                timeout_s=AI_CALL_TIMEOUT,
            )

        agent: Optional[Agent] = None
        if not use_stub:
            try:
                agent = _build_agent(model, model_settings["temperature"])
            except Exception as e:
                use_stub = True
                if logfire:
                    logfire.error("AI agent init failed, using stub", error=str(e))

        try:
            if use_stub or agent is None:
                result = _fake_ai(paragraphs, content_hash, chapter_index)
                result.model = model
                result.model_settings = model_settings
                result.run_id = run_id
            else:
                ai_result = await asyncio.wait_for(
                    _run_with_retries(agent, paragraphs),
                    timeout=AI_CALL_TIMEOUT,
                )
                result = ChapterAIResult(
                    chapter_index=chapter_index,
                    content_hash=content_hash,
                    paragraph_annotations=ai_result.paragraph_annotations,
                    chapter_summary_short=ai_result.chapter_summary_short,
                    chapter_summary_long=ai_result.chapter_summary_long,
                    qa_items=ai_result.qa_items,
                    reflection_prompts=ai_result.reflection_prompts,
                    mindmap_mermaid=ai_result.mindmap_mermaid,
                    status="success",
                    source="fresh",
                    run_id=run_id,
                    model=model,
                    model_settings=model_settings,
                )
        except Exception as e:
            if logfire:
                logfire.error(
                    "AI provider error",
                    error=str(e),
                    book_dir=str(book_dir),
                    chapter_index=chapter_index,
                    run_id=run_id,
                    model=model,
                )
            result = _record_failure(
                chapter_index=chapter_index,
                content_hash=content_hash,
                model=model,
                model_settings=model_settings,
                error=str(e),
                source="fresh",
                run_id=run_id,
            )

        result.run_duration_ms = round((time.perf_counter() - run_started) * 1000, 2)
        result = _sanitize_result(result)

        if ai_path.exists():
            _archive_existing(ai_path, history_dir)

        _write_json_atomic(ai_path, result.to_dict())
        if logfire:
            logfire.info(
                "AI processing finished",
                book_dir=str(book_dir),
                chapter_index=chapter_index,
                run_id=run_id,
                status=result.status,
                source=result.source,
                duration_ms=result.run_duration_ms,
                model=result.model,
                error=result.error,
            )
        return result
