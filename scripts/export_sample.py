# Export the accepted single-document sample into B's loader format.
# Re-running this script rebuilds the same adapted JSON, manifest, and sample version.

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.retrieval.types import digest, file_hash, write_json

DOCUMENT_ID = "eu_consumer_rights_2011_83"
PARSER_VERSION = "eurlex_html_v1"
ACCEPTED_JSON = ROOT / "data" / "processed" / f"{DOCUMENT_ID}.json"
ACCEPTED_TEXT = ROOT / "data" / "processed" / f"{DOCUMENT_ID}.txt"
ACCEPTED_HTML = ROOT / "data" / "raw" / f"{DOCUMENT_ID}.html"
SAMPLE_ROOT = ROOT / "data" / "sample_corpus"
SAMPLE_JSON = SAMPLE_ROOT / "processed" / f"{DOCUMENT_ID}.json"
SAMPLE_MANIFEST = SAMPLE_ROOT / "manifest.json"
SAMPLE_JSONL = ROOT / "data" / "eval" / "sample.jsonl"
SAMPLE_QUESTIONS = ROOT / "data" / "eval" / "sample_manifest.json"


class Progress:
    """实时进度与剩余时间。

    示例:
        progress = Progress(total=4)
        progress.advance()
        progress.finish()
    输出格式: [Progress] 12.50% Elapsed: 00:00:01 Remaining: 00:00:07
    """

    def __init__(self, total: int) -> None:
        self.total = max(int(total), 1)
        self.done = 0
        self.started = time.monotonic()
        self._render()

    def advance(self, steps: int = 1) -> None:
        self.done += steps
        self._render()

    def finish(self) -> None:
        self.done = self.total
        self._render(final=True)

    def _render(self, final: bool = False) -> None:
        elapsed = time.monotonic() - self.started
        ratio = min(self.done / self.total, 1.0)
        remaining = 0.0 if ratio <= 0 or ratio >= 1 else elapsed * (1 - ratio) / ratio
        whole = max(0, int(elapsed + 0.5))
        hours, rest = divmod(whole, 3600)
        minutes, secs = divmod(rest, 60)
        elapsed_text = f"{hours:02d}:{minutes:02d}:{secs:02d}"
        whole = max(0, int(remaining + 0.5))
        hours, rest = divmod(whole, 3600)
        minutes, secs = divmod(rest, 60)
        remaining_text = f"{hours:02d}:{minutes:02d}:{secs:02d}"
        print(
            f"\r[Progress] {ratio * 100:6.2f}% Elapsed: {elapsed_text} Remaining: {remaining_text}",
            end="",
            flush=True,
        )
        if final:
            print(flush=True)


def adapt_article(article: dict) -> dict:
    """Add the fields B reads, without changing the accepted article identity or offsets."""
    label = f"Article {article['number']}"
    chapter = article["chapter_id"]
    section = article["section_id"]
    adapted: dict = {}
    for key, value in article.items():
        adapted[key] = value
        if key == "number":
            adapted["label"] = label
        elif key == "chapter_id":
            adapted["chapter"] = chapter
        elif key == "section_id":
            adapted["section"] = section
    return adapted


def build_document(accepted: dict, text: str, corpus_version: str) -> dict:
    meta = accepted["source"]
    articles = [adapt_article(article) for article in accepted["articles"]]
    chapters = [
        {
            "structure_id": chapter["structure_id"],
            "number": chapter["number"],
            "label": chapter["label"],
            "heading": chapter["heading"],
            "start": chapter["start"],
            "end": chapter["end"],
            "article_ids": chapter["article_ids"],
        }
        for chapter in accepted["chapters"]
    ]
    return {
        "schema_version": "1.0",
        "kind": "integration_sample",
        "document_id": DOCUMENT_ID,
        "corpus_version": corpus_version,
        "title": meta["title"],
        "issuer": meta["institution"],
        "source_url": meta["official_url"],
        "published_at": meta["dates"]["publication_date"],
        "effective_at": meta["dates"]["entry_into_force_date"],
        "raw_path": f"data/raw/{DOCUMENT_ID}.html",
        "raw_sha256": file_hash(ACCEPTED_HTML),
        "text": text,
        "articles": articles,
        "chapters": chapters,
        "source_fields": {
            "language": meta["language"],
            "celex": meta["celex"],
            "eli": meta["eli"],
            "version_type": meta["version_type"],
            "dates": meta["dates"],
            "cleaning_rule_version": PARSER_VERSION,
            "accepted_clean_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "accepted_structure_json_sha256": file_hash(ACCEPTED_JSON),
        },
    }


def version_material(document: dict) -> dict:
    item = {
        key: document[key]
        for key in (
            "document_id",
            "title",
            "issuer",
            "source_url",
            "published_at",
            "effective_at",
            "raw_sha256",
        )
    }
    item["text_sha256"] = hashlib.sha256(document["text"].encode("utf-8")).hexdigest()
    item["structure_sha256"] = digest(document["articles"])
    return {"parser_version": PARSER_VERSION, "documents": [item]}


def sync_questions(corpus_version: str) -> str:
    cases = [json.loads(line) for line in SAMPLE_JSONL.read_text(encoding="utf-8").splitlines() if line]
    rendered = []
    for case in cases:
        case["corpus_version"] = corpus_version
        rendered.append(json.dumps(case, ensure_ascii=False))
    SAMPLE_JSONL.write_text("\n".join(rendered) + "\n", encoding="utf-8", newline="\n")
    sample_sha = file_hash(SAMPLE_JSONL)
    manifest = json.loads(SAMPLE_QUESTIONS.read_text(encoding="utf-8"))
    manifest["corpus_version"] = corpus_version
    manifest["sample_sha256"] = sample_sha
    write_json(SAMPLE_QUESTIONS, manifest)
    return sample_sha


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    progress = Progress(4)
    accepted = json.loads(ACCEPTED_JSON.read_text(encoding="utf-8"))
    text = ACCEPTED_TEXT.read_text(encoding="utf-8")
    if accepted.get("cleaning_rule_version") != PARSER_VERSION:
        raise SystemExit(f"expected cleaning rule {PARSER_VERSION}")
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != hashlib.sha256(ACCEPTED_TEXT.read_bytes()).hexdigest():
        raise SystemExit("accepted text changed while reading")
    progress.advance()
    provisional = build_document(accepted, text, corpus_version="")
    material = version_material(provisional)
    corpus_version = digest(material)
    document = build_document(accepted, text, corpus_version)
    for original, adapted in zip(accepted["articles"], document["articles"], strict=True):
        if (
            original["article_id"] != adapted["article_id"]
            or original["text"] != adapted["text"]
            or original["blocks"] != adapted["blocks"]
            or original["start"] != adapted["start"]
            or original["end"] != adapted["end"]
        ):
            raise SystemExit(f"accepted article identity changed: {original['article_id']}")
        if adapted["label"] != f"Article {original['number']}":
            raise SystemExit(f"label mismatch: {original['article_id']}")
        if adapted["chapter"] != original["chapter_id"] or adapted["section"] != original["section_id"]:
            raise SystemExit(f"chapter/section mapping mismatch: {original['article_id']}")
    if digest(version_material(document)) != corpus_version:
        raise SystemExit("corpus version changed after it was inserted")
    progress.advance()
    write_json(SAMPLE_JSON, document)
    entry = material["documents"][0]
    write_json(
        SAMPLE_MANIFEST,
        {
            "schema_version": "1.0",
            "kind": "integration_sample",
            "corpus_version": corpus_version,
            "parser_version": PARSER_VERSION,
            "documents": [
                {
                    "document_id": DOCUMENT_ID,
                    "raw_path": document["raw_path"],
                    "raw_sha256": document["raw_sha256"],
                    "processed_path": f"data/processed/{DOCUMENT_ID}.json",
                    "processed_sha256": file_hash(SAMPLE_JSON),
                    "text_sha256": entry["text_sha256"],
                    "structure_sha256": entry["structure_sha256"],
                }
            ],
        },
    )
    progress.advance()
    sample_sha = sync_questions(corpus_version)
    progress.advance()
    progress.finish()
    print(f"corpus_version={corpus_version}")
    print(f"structure_sha256={entry['structure_sha256']}")
    print(f"processed_sha256={file_hash(SAMPLE_JSON)}")
    print(f"sample_sha256={sample_sha}")
    print(f"articles={len(document['articles'])}")


if __name__ == "__main__":
    main()
