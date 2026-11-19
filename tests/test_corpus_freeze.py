# Remaining-time display. Example: [Progress] 50.00% Elapsed: 00:00:01 Remaining: 00:00:01
import hashlib
import io
import json
import shutil
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import export_corpus
from app.retrieval.errors import RetrievalError
from app.retrieval.types import formal_loader


class Progress:
    """实时进度与剩余时间。

    示例:
        progress = Progress(total=5)
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


PROGRESS = Progress(6)


def tearDownModule() -> None:
    PROGRESS.finish()


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def make_corpus(root: Path, *, include_processed: bool = True) -> None:
    html = b"<html>mini</html>"
    text = "Article 1\nAlpha.\n"
    article = {
        "article_id": "eu_mini:article:1",
        "number": "1",
        "chapter_id": None,
        "section_id": None,
        "text": text,
        "blocks": [],
        "start": 0,
        "end": len(text),
    }
    accepted = {
        "document_id": "eu_mini",
        "cleaning_rule_version": "eurlex_html_v1",
        "source": {
            "document_id": "eu_mini",
            "title": "Mini Directive",
            "institution": "Test Institution",
            "language": "en",
            "official_url": "https://example.test/mini",
            "eli": None,
            "celex": None,
            "version_type": "original_publication",
            "dates": {
                "publication_date": "2020-01-02",
                "entry_into_force_date": None,
            },
            "snapshot_path": "data/raw/Mini File.html",
            "snapshot_sha256": sha256(html),
        },
        "clean_text_sha256": sha256(text.encode("utf-8")),
        "cleaning_rules": {"version": "eurlex_html_v1", "main_articles": "mini"},
        "chapters": [],
        "articles": [article],
    }
    raw = root / "data" / "raw" / "Mini File.html"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(html)
    write_json(
        root / "data" / "sources.json",
        {"schema_version": "1", "sources": [{"document_id": "eu_mini", "snapshot": {"path": "data/raw/Mini File.html", "sha256": sha256(html)}}]},
    )
    if include_processed:
        text_path = root / "data" / "processed" / "eu_mini.txt"
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_bytes(text.encode("utf-8"))
        write_json(root / "data" / "processed" / "eu_mini.json", accepted)


def write_catalog(root: Path, document_ids: list[str]) -> None:
    sources = [
        {
            "document_id": document_id,
            "snapshot": {"path": f"data/raw/{document_id}.html", "sha256": "a" * 64},
        }
        for document_id in document_ids
    ]
    write_json(root / "data" / "sources.json", {"schema_version": "1", "sources": sources})


def run_official(root: Path) -> tuple[int, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = export_corpus.main(root)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    return code, stdout.getvalue() + stderr.getvalue()


def run_export(root: Path) -> tuple[int, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            export_corpus.export_corpus(root)
            code = 0
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    return code, stdout.getvalue() + stderr.getvalue()


class CorpusFreezeTests(unittest.TestCase):
    def setUp(self) -> None:
        PROGRESS.advance()

    def test_missing_processed_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_corpus(root, include_processed=False)
            code, output = run_export(root)
        self.assertEqual(code, 1)
        self.assertIn("accepted processed txt or json is missing", output)
        self.assertNotIn("result=ok", output)

    def test_hash_mismatch_fails_loader(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_corpus(root)
            code, output = run_export(root)
            self.assertEqual(code, 0, output)
            raw = root / "data" / "formal_corpus" / "raw" / "Mini File.html"
            raw.write_bytes(b"<html>changed</html>")
            version = json.loads((root / "data" / "formal_corpus" / "manifest.json").read_text(encoding="utf-8"))["corpus_version"]
            with self.assertRaises(RetrievalError) as caught:
                formal_loader(root / "data" / "formal_corpus")(version)
        self.assertEqual(caught.exception.code, "SOURCE_MISMATCH")

    def test_version_mismatch_fails_loader(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_corpus(root)
            self.assertEqual(run_export(root)[0], 0)
            manifest_path = root / "data" / "formal_corpus" / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            original = manifest["corpus_version"]
            with self.assertRaises(RetrievalError) as requested:
                formal_loader(root / "data" / "formal_corpus")("0" * 64)
            self.assertEqual(requested.exception.code, "VERSION_MISMATCH")
            manifest["corpus_version"] = "1" * 64
            write_json(manifest_path, manifest)
            with self.assertRaises(RetrievalError) as stored:
                formal_loader(root / "data" / "formal_corpus")("1" * 64)
        self.assertEqual(stored.exception.code, "SOURCE_MISMATCH")
        self.assertNotEqual(original, "1" * 64)

    def test_repeat_export_is_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_corpus(root)
            self.assertEqual(run_export(root)[0], 0)
            first = root / "data" / "formal_copy"
            shutil.copytree(root / "data" / "formal_corpus", first)
            first_manifest = (root / "data" / "corpus_manifest.json").read_bytes()
            self.assertEqual(run_export(root)[0], 0)
            second_manifest = (root / "data" / "corpus_manifest.json").read_bytes()
            self.assertEqual(first_manifest, second_manifest)
            for path in first.rglob("*"):
                if path.is_file():
                    current = root / "data" / "formal_corpus" / path.relative_to(first)
                    self.assertEqual(path.read_bytes(), current.read_bytes(), str(path.name))
            checked = export_corpus.verify_corpus(root)
            self.assertEqual(checked["documents"], 1)
            self.assertEqual(checked["main_articles"], 1)
            loaded = formal_loader(root / "data" / "formal_corpus")(checked["corpus_version"])
            self.assertIsNone(loaded[0]["effective_at"])
            self.assertIsNone(loaded[0]["articles"][0]["chapter"])
            self.assertIsNone(loaded[0]["articles"][0]["section"])
            self.assertEqual(loaded[0]["articles"][0]["label"], "Article 1")

    def test_official_cli_rejects_missing_document_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            present = [item for item in export_corpus.OFFICIAL_IDS if item != "eu_unfair_terms_93_13"]
            write_catalog(root, present)
            code, output = run_official(root)
            self.assertFalse((root / "data" / "formal_corpus").exists())
            self.assertFalse((root / "data" / "corpus_manifest.json").exists())
        self.assertEqual(code, 1)
        self.assertIn("missing: eu_unfair_terms_93_13", output)
        self.assertNotIn("documents=4", output)
        self.assertNotIn("result=ok", output)

    def test_official_cli_rejects_extra_document_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_catalog(root, [*export_corpus.OFFICIAL_IDS, "eu_extra"])
            code, output = run_official(root)
            self.assertFalse((root / "data" / "formal_corpus").exists())
            self.assertFalse((root / "data" / "corpus_manifest.json").exists())
        self.assertEqual(code, 1)
        self.assertIn("extra: eu_extra", output)
        self.assertNotIn("result=ok", output)


if __name__ == "__main__":
    unittest.main()
