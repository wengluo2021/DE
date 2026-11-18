"""Explicit M1 synthetic fixtures; never loaded as production fallback."""
from copy import deepcopy
import hashlib
import json

from app.config import ROOT
from app.qa.client import GenerationResponse

FIXTURE_ROOT = ROOT / "tests/fixtures/b"


def document_loader(corpus_version):
    document = json.loads((FIXTURE_ROOT / "document.json").read_text(encoding="utf-8"))
    if corpus_version != document["corpus_version"]:
        raise ValueError("Unsupported fixture corpus version")
    return [document]


def retrieve(*, question, condition, corpus_version, top_k=5):
    # Fixed evidence for plumbing, not semantic ranking and not an evaluation gold case.
    document_loader(corpus_version)
    if condition not in {"f400", "s400", "f800", "s800"} or top_k != 5:
        raise ValueError("Unsupported fixture condition")
    hit = deepcopy(json.loads((FIXTURE_ROOT / "expected_hits.json").read_text(encoding="utf-8"))["hit"])
    method = "fixed" if condition.startswith("f") else "structured"
    size = int(condition[1:])
    hit["condition"] = condition
    hit["chunk_id"] = hashlib.sha256(
        f'{corpus_version}|{method}|{size}|{hit["document_id"]}|{hit["start"]}|{hit["end"]}'.encode()).hexdigest()
    return {"condition": condition, "corpus_version": corpus_version, "index_version": "c-fixture-index-v1",
            "hits": [hit], "timing_ms": 0.0}


class FixtureGenerator:
    def generate(self, messages):
        content = json.dumps({"status": "answered", "claims": [{"text": "Article 2 states B.", "citation_numbers": [1]}]})
        raw = {"model": "fixture-model", "choices": [{"message": {"content": content}, "finish_reason": "stop"}]}
        return GenerationResponse(content, "fixture-model", "stop", None, "fixture-response", raw)
