# Remaining-time display. Example: [Progress] 50.00% Elapsed: 00:00:01 Remaining: 00:00:01
import hashlib
import io
import json
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import process_documents
import validate_data


class Progress:
    """实时进度与剩余时间。

    示例:
        progress = Progress(total=8)
        progress.advance()
    """

    def __init__(self, total: int) -> None:
        self.total = max(total, 1)
        self.done = 0
        self.started = time.monotonic()

    def advance(self) -> None:
        self.done += 1
        ratio = min(self.done / self.total, 1)
        elapsed = time.monotonic() - self.started
        remain = elapsed * (1 - ratio) / ratio if ratio else 0
        print(
            f"\r[Progress] {ratio * 100:6.2f}% Elapsed: {self.format(elapsed)} Remaining: {self.format(remain)}",
            end="",
            flush=True,
        )

    def finish(self) -> None:
        self.done = self.total
        self.advance()
        print()

    @staticmethod
    def format(seconds: float) -> str:
        seconds = max(0, int(seconds))
        return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


PROGRESS = Progress(9)


def tearDownModule() -> None:
    PROGRESS.finish()


def source(document_id: str, relative: str, digest: str) -> dict:
    return {
        "document_id": document_id,
        "snapshot": {"path": relative, "sha256": digest},
    }


def write_catalog(root: Path, sources: list[dict]) -> None:
    path = root / "data" / "sources.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": "1", "sources": sources}), encoding="utf-8")


def run_process(root: Path, *args: str) -> tuple[int, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = process_documents.main([*args, "--data-root", str(root)])
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    return code, stdout.getvalue() + stderr.getvalue()


def run_validate(root: Path, *args: str) -> tuple[int, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = validate_data.main([*args, "--data-root", str(root)])
    return code, stdout.getvalue() + stderr.getvalue()


class CorpusBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        PROGRESS.advance()

    def test_arguments_are_exclusive_and_required(self) -> None:
        with self.assertRaises(SystemExit):
            process_documents.main([])
        with self.assertRaises(SystemExit):
            process_documents.main(["--all", "--document-id", "eu_consumer_rights_2011_83"])
        with self.assertRaises(SystemExit):
            validate_data.main([])

    def test_empty_catalog_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_catalog(root, [])
            code, output = run_process(root, "--all")
        self.assertEqual(code, 1)
        self.assertIn("sources list is empty", output)
        self.assertIn("result=failed", output)
        self.assertNotIn("result=ok", output)

    def test_duplicate_document_id_fails(self) -> None:
        digest = "a" * 64
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_catalog(root, [source("eu_one", "data/raw/one.html", digest), source("eu_one", "data/raw/two.html", digest)])
            code, output = run_process(root, "--all")
        self.assertEqual(code, 1)
        self.assertIn("document_id eu_one is duplicated", output)
        self.assertNotIn("result=ok", output)

    def test_missing_snapshot_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_catalog(root, [source("eu_one", "data/raw/Missing File.html", "b" * 64)])
            code, output = run_process(root, "--all")
        self.assertEqual(code, 1)
        self.assertIn("Missing File.html", output)
        self.assertIn("does not exist", output)
        self.assertNotIn("result=ok", output)

    def test_hash_mismatch_fails_the_batch(self) -> None:
        payload = b"<html></html>"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            html = root / "data" / "raw" / "one.html"
            html.parent.mkdir(parents=True)
            html.write_bytes(payload)
            write_catalog(root, [source("eu_one", "data/raw/one.html", "c" * 64)])
            code, output = run_process(root, "--all")
        self.assertEqual(code, 1)
        self.assertIn("snapshot sha256 mismatch", output)
        self.assertIn("result=failed", output)
        self.assertNotIn("result=ok", output)

    def test_partial_failure_is_not_reported_as_success(self) -> None:
        payload = b"<html></html>"
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("one.html", "two.html"):
                path = root / "data" / "raw" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
            write_catalog(
                root,
                [
                    source("eu_bad", "data/raw/one.html", digest),
                    source("eu_good", "data/raw/two.html", digest),
                ],
            )

            def fake(_root: Path, item: dict) -> None:
                if item["document_id"] == "eu_bad":
                    raise SystemExit(1)

            original = process_documents.process_registered
            process_documents.process_registered = fake
            try:
                code, output = run_process(root, "--all")
            finally:
                process_documents.process_registered = original
        self.assertEqual(code, 1)
        self.assertIn("succeeded=1", output)
        self.assertIn("failed=1", output)
        self.assertIn("result=failed", output)
        self.assertNotIn("result=ok", output)

    def test_missing_processed_file_fails_validation(self) -> None:
        payload = b"<html></html>"
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            html = root / "data" / "raw" / "one.html"
            html.parent.mkdir(parents=True)
            html.write_bytes(payload)
            write_catalog(root, [source("eu_one", "data/raw/one.html", digest)])
            (root / "data" / "sample_corpus" / "processed").mkdir(parents=True)
            (root / "data" / "sample_corpus" / "processed" / "eu_one.json").write_text("{}", encoding="utf-8")
            (root / "data" / "processed").mkdir()
            (root / "data" / "processed" / "not_registered.json").write_text("{}", encoding="utf-8")
            code, output = run_validate(root, "--scope", "corpus")
        self.assertEqual(code, 1)
        self.assertIn("not_registered.json", output)
        self.assertIn("eu_one.json", output)
        self.assertNotIn("sample_corpus", output)
        self.assertNotIn("result=ok", output)

    def test_section_mirror_is_not_a_second_definition(self) -> None:
        document = {
            "title": {"structure_id": "d:title", "blocks": []},
            "preamble": {"structure_id": "d:preamble", "blocks": [], "recitals": []},
            "chapters": [
                {
                    "structure_id": "d:chapter:2",
                    "article_ids": ["d:article:6"],
                    "sections": [{"structure_id": "d:chapter:2:section:1", "chapter_id": "d:chapter:2"}],
                }
            ],
            "sections": [{"structure_id": "d:chapter:2:section:1", "chapter_id": "d:chapter:2"}],
            "articles": [
                {
                    "article_id": "d:article:6",
                    "chapter_id": "d:chapter:2",
                    "section_id": "d:chapter:2:section:1",
                    "blocks": [],
                }
            ],
            "signature": {"structure_id": "d:signature", "blocks": []},
            "footnotes": [],
            "annexes": [],
        }
        defined = validate_data.structure_definitions(document)
        self.assertEqual(defined.count("d:chapter:2:section:1"), 1)
        self.assertEqual(defined.count("d:chapter:2"), 1)
        references = [target for _owner, target in validate_data.structure_references(document)]
        self.assertIn("d:article:6", references)
        self.assertIn("d:chapter:2", references)
        self.assertEqual(defined.count("d:article:6"), 1)


if __name__ == "__main__":
    unittest.main()
