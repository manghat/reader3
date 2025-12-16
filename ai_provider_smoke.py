"""
Tiny PydanticAI smoke test for OpenAI and Gemini providers.

Usage:
  uv run python ai_provider_smoke.py --provider openai
  uv run python ai_provider_smoke.py --provider gemini
  uv run python ai_provider_smoke.py --provider both
"""

from __future__ import annotations

import argparse
import os
import sys

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider


def run_openai() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    model = OpenAIChatModel("gpt-4o-mini", provider=OpenAIProvider(api_key=api_key))
    agent = Agent(model)
    result = agent.run_sync("Say 'hello from openai' in exactly three words.")
    print("OpenAI response:", result.output)


def run_gemini() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    model = GoogleModel("gemini-2.5-flash", provider=GoogleProvider(api_key=api_key))
    agent = Agent(model)
    result = agent.run_sync("Say 'hello from gemini' in exactly three words.")
    print("Gemini response:", result.output)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider",
        choices=["openai", "gemini", "both"],
        default="both",
        help="Which provider(s) to test.",
    )
    args = parser.parse_args(argv)

    try:
        if args.provider in ("openai", "both"):
            run_openai()
        if args.provider in ("gemini", "both"):
            run_gemini()
    except Exception as exc:  # surface config errors quickly
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
