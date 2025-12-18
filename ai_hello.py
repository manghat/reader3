"""
Simple AI smoke call to verify model connectivity and Logfire/PydanticAI wiring.
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict, Optional
from uuid import uuid4

try:
    import logfire  # type: ignore
except ImportError:  # pragma: no cover - optional
    logfire = None  # type: ignore

try:
    from pydantic_ai import Agent  # type: ignore
except ImportError:  # pragma: no cover
    Agent = None  # type: ignore


class AIHelloError(Exception):
    pass


async def run_hello(model: Optional[str] = None, timeout: float = 15.0) -> Dict[str, Any]:
    """
    Run a small "hello world" AI call to confirm connectivity and instrumentation.
    """
    if Agent is None:
        raise AIHelloError("pydantic-ai is not installed.")

    model_name = model or os.getenv("READER3_MODEL", "openai:gpt-4o-mini")
    if not model_name:
        raise AIHelloError("Model name is not configured (set READER3_MODEL).")

    # Require appropriate API key based on provider prefix.
    if model_name.startswith("openai:") and not os.getenv("OPENAI_API_KEY"):
        raise AIHelloError("OPENAI_API_KEY is not set; required for OpenAI models.")
    if (model_name.startswith("gemini:") or model_name.startswith("google:")) and not (
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    ):
        raise AIHelloError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set; required for Gemini/Google models.")

    agent = Agent(model=model_name, system_prompt="You are a concise assistant.")
    run_id = str(uuid4())

    if logfire:
        logfire.info("hello_ai_start", model=model_name, run_id=run_id, timeout_s=timeout)

    started = time.perf_counter()
    try:
        result = await asyncio.wait_for(agent.run("Say 'hello, reader3'."), timeout=timeout)
        message = result.output if hasattr(result, "output") else result
        return {
            "status": "success",
            "model": model_name,
            "run_id": run_id,
            "message": message,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    except Exception as exc:
        if logfire:
            logfire.error("hello_ai_failed", model=model_name, run_id=run_id, error=str(exc))
        raise AIHelloError(str(exc))
