import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest import TestCase

import ai_processing as mod
from ai_processing import process_chapter_ai


def make_chapter(book_dir: Path, chapter_index: int = 0, paragraphs: int = 3) -> None:
    chapters_dir = book_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "paragraphs": [
            {"id": f"p{idx}", "text": f"Paragraph {idx} text"} for idx in range(paragraphs)
        ]
    }
    with (chapters_dir / f"{chapter_index}.json").open("w", encoding="utf-8") as f:
        json.dump(payload, f)


class AIProcessingTests(TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.book_dir = Path(self.tmp.name) / "book1_data"
        self.book_dir.mkdir(parents=True, exist_ok=True)
        make_chapter(self.book_dir)
        os.environ["READER3_FAKE_AI"] = "1"

    def tearDown(self) -> None:
        self.tmp.cleanup()
        os.environ.pop("READER3_FAKE_AI", None)

    def test_cache_skip_without_force(self) -> None:
        first = asyncio.run(process_chapter_ai(self.book_dir, 0, force=False))
        second = asyncio.run(process_chapter_ai(self.book_dir, 0, force=False))

        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(second.source, "cache")
        self.assertEqual(second.status, "success")

    def test_force_rerun_archives_history(self) -> None:
        first = asyncio.run(process_chapter_ai(self.book_dir, 0, force=False))
        history_dir = self.book_dir / "ai" / "history"
        self.assertFalse(history_dir.exists())

        second = asyncio.run(process_chapter_ai(self.book_dir, 0, force=True))
        self.assertNotEqual(first.run_id, second.run_id)
        self.assertTrue(history_dir.exists())
        history_files = list(history_dir.glob("0-*.json"))
        self.assertGreaterEqual(len(history_files), 1)

    def test_failure_marks_status(self) -> None:
        class DummyAgent:
            def __init__(self, *args, **kwargs) -> None:
                pass

        async def failing_run(*args, **kwargs):
            raise RuntimeError("boom")

        original_agent = mod.Agent
        original_runner = mod._run_with_retries
        os.environ["READER3_FAKE_AI"] = "0"
        mod.Agent = DummyAgent  # type: ignore
        mod._run_with_retries = failing_run  # type: ignore
        try:
            result = asyncio.run(process_chapter_ai(self.book_dir, 0, force=True))
            self.assertEqual(result.status, "failed")
            self.assertTrue(result.error)
        finally:
            mod.Agent = original_agent  # type: ignore
            mod._run_with_retries = original_runner  # type: ignore
            os.environ["READER3_FAKE_AI"] = "1"
