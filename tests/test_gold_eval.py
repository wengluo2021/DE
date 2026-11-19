# Remaining-time display. Example: [Progress] 50.00% Elapsed: 00:00:01 Remaining: 00:00:01
import hashlib
import json
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import validate_data


class Progress:
    """实时进度与剩余时间。

    示例:
        progress = Progress(total=4)
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


PROGRESS = Progress(5)


def tearDownModule() -> None:
    PROGRESS.finish()


def case(case_id: str, evidence: list[dict], *, refuse: bool = False, version: str = "v") -> dict:
    return {
        "case_id": case_id,
        "corpus_version": version,
        "question": "What does the frozen text require?",
        "question_type": "unanswerable" if refuse else ("multi_evidence" if len(evidence) > 1 else "single_article"),
        "should_refuse": refuse,
        "reference_answer": "The frozen text does not contain enough information." if refuse else "Alpha rule.",
        "key_facts": [] if refuse else [item["quote"] for item in evidence],
        "evidence": evidence,
        "refusal_reason": "The text has no such rule." if refuse else None,
    }


class GoldEvalTests(unittest.TestCase):
    def setUp(self) -> None:
        PROGRESS.advance()
        self.text = "Article 1\nAlpha rule.\n\nANNEX\nArticle 1\nAnnex rule.\n"
        self.article_end = self.text.index("\n\nANNEX")
        self.annex_start = self.text.index("ANNEX")
        self.documents = [{
            "document_id": "eu_mini",
            "text": self.text,
            "articles": [{"article_id": "eu_mini:article:1", "start": 0, "end": self.article_end}],
        }]
        self.structures = {
            "eu_mini": {
                "eu_mini:article:1": (0, self.article_end),
                "eu_mini:annex:1": (self.annex_start, len(self.text)),
            }
        }

    def evidence(self, holder: str, quote: str, *, article: bool = True) -> dict:
        start = self.text.index(quote)
        item = {
            "document_id": "eu_mini",
            "start": start,
            "end": start + len(quote),
            "quote": quote,
        }
        item["article_id" if article else "structure_id"] = holder
        return item

    def test_cross_reference_stays_in_declared_article(self) -> None:
        quote = "Alpha rule."
        errors = validate_data.check_cases(self.documents, self.structures, [case("q1", [self.evidence("eu_mini:article:1", quote)])], "v")
        self.assertEqual(errors, [])

    def test_duplicate_article_number_uses_declared_structure(self) -> None:
        annex_quote = "Annex rule."
        good = case("q1", [self.evidence("eu_mini:annex:1", annex_quote, article=False)])
        self.assertEqual(validate_data.check_cases(self.documents, self.structures, [good], "v"), [])
        bad = self.evidence("eu_mini:annex:1", "Article 1", article=False)
        bad["start"] = 0
        bad["end"] = len("Article 1")
        bad["quote"] = "Article 1"
        errors = validate_data.check_cases(self.documents, self.structures, [case("q2", [bad])], "v")
        self.assertTrue(any("does not match" in message or "outside" in message for message in errors))

    def test_span_mismatch_and_refusal_and_duplicate(self) -> None:
        broken = self.evidence("eu_mini:article:1", "Alpha rule.")
        broken["quote"] = "Alpha  rule."
        mismatch = validate_data.check_cases(self.documents, self.structures, [case("q1", [broken])], "v")
        self.assertTrue(mismatch)
        refused = case("q1", [self.evidence("eu_mini:article:1", "Alpha rule.")], refuse=True)
        refusal_errors = validate_data.check_cases(self.documents, self.structures, [refused], "v")
        self.assertTrue(any("empty evidence" in message for message in refusal_errors))
        first = case("same", [self.evidence("eu_mini:article:1", "Alpha rule.")])
        second = case("same", [self.evidence("eu_mini:article:1", "Alpha rule.")])
        duplicate = validate_data.check_cases(self.documents, self.structures, [first, second], "v")
        self.assertTrue(any("duplicated" in message for message in duplicate))
        wrong_version = case("q1", [self.evidence("eu_mini:article:1", "Alpha rule.")], version="other")
        version_errors = validate_data.check_cases(self.documents, self.structures, [wrong_version], "v")
        self.assertTrue(any("corpus_version" in message for message in version_errors))

    def test_temp_copy_detects_hash_and_crlf_without_touching_official_files(self) -> None:
        official_gold = (ROOT / "data" / "eval" / "gold.jsonl").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ("data/formal_corpus", "data/processed", "data/eval"):
                shutil.copytree(ROOT / relative, root / relative)
            shutil.copy2(ROOT / "data" / "corpus_manifest.json", root / "data" / "corpus_manifest.json")
            gold = root / "data" / "eval" / "gold.jsonl"
            manifest = json.loads((root / "data" / "eval" / "manifest.json").read_text(encoding="utf-8"))
            manifest["gold_version"] = "0" * 64
            manifest["gold_sha256"] = "0" * 64
            (root / "data" / "eval" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            code = validate_data.validate_eval(root)
            self.assertEqual(code, 1)
            gold.write_bytes(gold.read_bytes().replace(b"\n", b"\r\n"))
            raw = gold.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            manifest["gold_version"] = digest
            manifest["gold_sha256"] = digest
            (root / "data" / "eval" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            code = validate_data.validate_eval(root)
            self.assertEqual(code, 1)
        self.assertEqual((ROOT / "data" / "eval" / "gold.jsonl").read_bytes(), official_gold)

    def test_eval_scope_rejects_document_id(self) -> None:
        self.assertEqual(validate_data.main(["--scope", "eval", "--document-id", "eu_consumer_rights_2011_83"]), 1)


if __name__ == "__main__":
    unittest.main()
