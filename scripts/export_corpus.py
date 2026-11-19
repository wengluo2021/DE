# Export the five accepted documents into B's formal_loader package.
# The accepted JSON files stay unchanged. corpus_version follows app.retrieval.types.

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.retrieval.types import digest, file_hash, formal_loader, write_json

PARSER_VERSION = "eurlex_html_v1"
OFFICIAL_IDS = (
    "eu_consumer_rights_2011_83",
    "eu_digital_content_2019_770",
    "eu_sale_of_goods_2019_771",
    "eu_unfair_practices_2005_29",
    "eu_unfair_terms_93_13",
)
VERSION_KEYS = (
    "document_id",
    "title",
    "issuer",
    "source_url",
    "published_at",
    "effective_at",
    "raw_sha256",
    "text_sha256",
    "structure_sha256",
)


class Progress:
    """实时进度与剩余时间。

    示例:
        progress = Progress(total=5)
        progress.advance()
        progress.finish()
    输出格式: [Progress] 20.00% Elapsed: 00:00:01 Remaining: 00:00:04
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
        print(
            f"\r[Progress] {ratio * 100:6.2f}% Elapsed: {format_duration(elapsed)} Remaining: {format_duration(remaining)}",
            end="",
            flush=True,
        )
        if final:
            print(flush=True)


def format_duration(seconds: float) -> str:
    whole = max(0, int(seconds + 0.5))
    hours, rest = divmod(whole, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def fail(message: str) -> None:
    print(f"export_corpus.py: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_sources(root: Path) -> list[dict]:
    """Read the source catalog in document_id order. Do not scan data/raw."""
    source_path = root / "data" / "sources.json"
    if not source_path.is_file():
        fail(f"file={source_path}: sources.json is missing")
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"file={source_path}: sources.json cannot be read: {exc}")
    items = payload.get("sources") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items:
        fail(f"file={source_path}: sources list is empty or invalid")
    seen: set[str] = set()
    names: set[str] = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            fail(f"file={source_path}: source {index} is not an object")
        document_id = item.get("document_id")
        if not isinstance(document_id, str) or not document_id:
            fail(f"file={source_path}: source {index} has invalid document_id")
        if document_id in seen:
            fail(f"file={source_path}: document_id {document_id} is duplicated")
        seen.add(document_id)
        snapshot = item.get("snapshot")
        relative = snapshot.get("path") if isinstance(snapshot, dict) else None
        digest_value = snapshot.get("sha256") if isinstance(snapshot, dict) else None
        path = Path(relative) if isinstance(relative, str) else None
        if path is None or path.is_absolute() or ".." in path.parts or not relative:
            fail(f"file={source_path} document_id={document_id}: snapshot path is invalid")
        if not isinstance(digest_value, str) or len(digest_value) != 64:
            fail(f"file={source_path} document_id={document_id}: snapshot sha256 is invalid")
        if Path(relative).name in names:
            fail(f"file={source_path} document_id={document_id}: snapshot file name is duplicated")
        names.add(Path(relative).name)
    return sorted(items, key=lambda item: item["document_id"])


def section_records(document_id: str, accepted: dict) -> list[dict]:
    nested = [section for chapter in accepted.get("chapters", []) for section in chapter.get("sections") or []]
    top = accepted.get("sections")
    if top is None:
        return nested
    if not isinstance(top, list):
        fail(f"document_id={document_id}: sections mirror is not a list")
    if [item.get("structure_id") for item in top] != [item.get("structure_id") for item in nested]:
        fail(f"document_id={document_id}: top-level sections do not match the chapter sections")
    return top


def adapt_article(article: dict) -> dict:
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
    if "label" not in adapted or "chapter" not in adapted or "section" not in adapted:
        fail(f"article {article.get('article_id')}: missing number, chapter_id, or section_id")
    return adapted


def adapt_chapter(chapter: dict) -> dict:
    adapted = {
        "structure_id": chapter["structure_id"],
        "number": chapter["number"],
        "label": chapter["label"],
        "heading": chapter["heading"],
        "start": chapter["start"],
        "end": chapter["end"],
        "article_ids": list(chapter["article_ids"]),
    }
    nested = chapter.get("sections") or []
    if nested:
        adapted["section_ids"] = [section["structure_id"] for section in nested]
    return adapted


def adapt_section(section: dict) -> dict:
    return {
        "structure_id": section["structure_id"],
        "number": section["number"],
        "label": section["label"],
        "heading": section["heading"],
        "chapter_id": section["chapter_id"],
        "start": section["start"],
        "end": section["end"],
        "article_ids": list(section["article_ids"]),
    }


def build_document(accepted: dict, text: str, raw_path: str, raw_sha256: str, corpus_version: str) -> dict:
    meta = accepted["source"]
    document_id = accepted["document_id"]
    dates = meta["dates"]
    if "publication_date" not in dates or "entry_into_force_date" not in dates:
        fail(f"document_id={document_id}: publication_date or entry_into_force_date is absent")
    sections = section_records(document_id, accepted)
    return {
        "schema_version": "1.0",
        "kind": "formal_corpus",
        "document_id": document_id,
        "corpus_version": corpus_version,
        "title": meta["title"],
        "issuer": meta["institution"],
        "source_url": meta["official_url"],
        "published_at": dates["publication_date"],
        "effective_at": dates["entry_into_force_date"],
        "raw_path": raw_path,
        "raw_sha256": raw_sha256,
        "text": text,
        "articles": [adapt_article(article) for article in accepted["articles"]],
        "chapters": [adapt_chapter(chapter) for chapter in accepted["chapters"]],
        "sections": [adapt_section(section) for section in sections],
        "source_fields": {
            "language": meta["language"],
            "celex": meta["celex"],
            "eli": meta["eli"],
            "version_type": meta["version_type"],
            "dates": dates,
            "official_journal": meta.get("official_journal"),
            "cleaning_rule_version": accepted["cleaning_rule_version"],
            "accepted_clean_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "accepted_structure_json_sha256": None,
        },
    }


def check_article_identity(document_id: str, text: str, accepted: dict, adapted: dict) -> None:
    if adapted["document_id"] != document_id or adapted["text"] != text:
        fail(f"document_id={document_id}: adapted text or id changed")
    for original, article in zip(accepted["articles"], adapted["articles"], strict=True):
        article_id = original["article_id"]
        if (
            article["article_id"] != article_id
            or article["text"] != original["text"]
            or article["blocks"] != original["blocks"]
            or article["start"] != original["start"]
            or article["end"] != original["end"]
        ):
            fail(f"document_id={document_id}: accepted article identity changed: {article_id}")
        start, end = article["start"], article["end"]
        if text[start:end] != article["text"]:
            fail(f"document_id={document_id}: article slice mismatch: {article_id}")
        if article["label"] != f"Article {original['number']}":
            fail(f"document_id={document_id}: label mismatch: {article_id}")
        if article["chapter"] != original["chapter_id"] or article["section"] != original["section_id"]:
            fail(f"document_id={document_id}: chapter/section mapping mismatch: {article_id}")
        if original["chapter_id"] is None and article["chapter"] is not None:
            fail(f"document_id={document_id}: null chapter was replaced: {article_id}")
        if original["section_id"] is None and article["section"] is not None:
            fail(f"document_id={document_id}: null section was replaced: {article_id}")


def check_practices_sections(document: dict) -> None:
    document_id = "eu_unfair_practices_2005_29"
    if document["document_id"] != document_id:
        return
    if len(document["sections"]) != 2:
        fail(f"document_id={document_id}: expected 2 sections, found {len(document['sections'])}")
    by_id = {article["article_id"]: article for article in document["articles"]}
    chapter_two = f"{document_id}:chapter:2"
    section_one = f"{document_id}:chapter:2:section:1"
    section_two = f"{document_id}:chapter:2:section:2"
    article_five = by_id[f"{document_id}:article:5"]
    if article_five["chapter"] != chapter_two or article_five["section"] is not None:
        fail(f"document_id={document_id}: article 5 must stay directly in chapter 2")
    expected = {
        f"{document_id}:article:6": section_one,
        f"{document_id}:article:7": section_one,
        f"{document_id}:article:8": section_two,
        f"{document_id}:article:9": section_two,
    }
    for article_id, section_id in expected.items():
        article = by_id[article_id]
        if article["chapter"] != chapter_two or article["section"] != section_id:
            fail(f"document_id={document_id}: section mapping mismatch: {article_id}")
    membership = {section["structure_id"]: section["article_ids"] for section in document["sections"]}
    if article_five["article_id"] in membership[section_one] or article_five["article_id"] in membership[section_two]:
        fail(f"document_id={document_id}: article 5 was placed inside a section")
    if membership[section_one] != [f"{document_id}:article:6", f"{document_id}:article:7"]:
        fail(f"document_id={document_id}: section 1 article list changed")
    if membership[section_two] != [f"{document_id}:article:8", f"{document_id}:article:9"]:
        fail(f"document_id={document_id}: section 2 article list changed")


def version_item(document: dict) -> dict:
    item = {
        "document_id": document["document_id"],
        "title": document["title"],
        "issuer": document["issuer"],
        "source_url": document["source_url"],
        "published_at": document["published_at"],
        "effective_at": document["effective_at"],
        "raw_sha256": document["raw_sha256"],
    }
    item["text_sha256"] = hashlib.sha256(document["text"].encode("utf-8")).hexdigest()
    item["structure_sha256"] = digest(document["articles"])
    return item


def version_material(documents: list[dict]) -> dict:
    items = [version_item(document) for document in documents]
    items.sort(key=lambda item: item["document_id"])
    return {"parser_version": PARSER_VERSION, "documents": items}


def read_accepted(root: Path, source: dict) -> tuple[dict, str, Path, Path]:
    document_id = source["document_id"]
    json_path = root / "data" / "processed" / f"{document_id}.json"
    text_path = root / "data" / "processed" / f"{document_id}.txt"
    html_path = root / source["snapshot"]["path"]
    if not html_path.is_file():
        fail(f"document_id={document_id} file={html_path}: registered snapshot does not exist")
    if file_hash(html_path) != source["snapshot"]["sha256"]:
        fail(f"document_id={document_id} file={html_path}: snapshot sha256 mismatch")
    if not json_path.is_file() or not text_path.is_file():
        fail(f"document_id={document_id}: accepted processed txt or json is missing")
    accepted = json.loads(json_path.read_text(encoding="utf-8"))
    if accepted.get("document_id") != document_id:
        fail(f"document_id={document_id} file={json_path}: document_id mismatch")
    if accepted.get("cleaning_rule_version") != PARSER_VERSION:
        fail(f"document_id={document_id}: cleaning rule is not {PARSER_VERSION}")
    meta = accepted.get("source")
    if not isinstance(meta, dict):
        fail(f"document_id={document_id}: accepted source metadata is missing")
    if meta.get("snapshot_path") != source["snapshot"]["path"] or meta.get("snapshot_sha256") != source["snapshot"]["sha256"]:
        fail(f"document_id={document_id}: accepted snapshot path or hash differs from sources.json")
    if not isinstance(meta.get("title"), str) or not isinstance(meta.get("institution"), str) or not isinstance(meta.get("official_url"), str):
        fail(f"document_id={document_id}: title, institution, or official_url is not a string")
    text_bytes = text_path.read_bytes()
    text = text_bytes.decode("utf-8")
    text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if text_sha != hashlib.sha256(text_bytes).hexdigest() or text_sha != accepted.get("clean_text_sha256"):
        fail(f"document_id={document_id} file={text_path}: clean text hash mismatch")
    return accepted, text, json_path, html_path


def prepare_documents(root: Path, sources: list[dict]) -> tuple[list[dict], list[dict]]:
    provisional = []
    accepted_rows = []
    for source in sources:
        accepted, text, json_path, html_path = read_accepted(root, source)
        raw_name = Path(source["snapshot"]["path"]).name
        raw_path = f"data/raw/{raw_name}"
        document = build_document(accepted, text, raw_path, source["snapshot"]["sha256"], "")
        document["source_fields"]["accepted_structure_json_sha256"] = file_hash(json_path)
        check_article_identity(source["document_id"], text, accepted, document)
        check_practices_sections(document)
        provisional.append(document)
        accepted_rows.append(
            {
                "accepted": accepted,
                "text": text,
                "json_path": json_path,
                "html_path": html_path,
                "raw_name": raw_name,
            }
        )
    version = digest(version_material(provisional))
    documents = []
    for document in provisional:
        frozen = dict(document)
        frozen["corpus_version"] = version
        frozen["source_fields"] = dict(document["source_fields"])
        documents.append(frozen)
    if digest(version_material(documents)) != version:
        fail("corpus version changed after it was inserted")
    return documents, accepted_rows


def export_corpus(root: Path) -> dict:
    sources = load_sources(root)
    documents, accepted_rows = prepare_documents(root, sources)
    version = documents[0]["corpus_version"]
    package = root / "data" / "formal_corpus"
    raw_dir = package / "raw"
    processed_dir = package / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    catalog = []
    for source, document, row in zip(sources, documents, accepted_rows, strict=True):
        document_id = document["document_id"]
        raw_destination = raw_dir / row["raw_name"]
        raw_destination.write_bytes(row["html_path"].read_bytes())
        if file_hash(raw_destination) != document["raw_sha256"]:
            fail(f"document_id={document_id}: formal raw copy hash changed")
        processed_path = processed_dir / f"{document_id}.json"
        write_json(processed_path, document)
        processed_sha = file_hash(processed_path)
        item = version_item(document)
        if item["text_sha256"] != hashlib.sha256(row["text"].encode("utf-8")).hexdigest():
            fail(f"document_id={document_id}: text hash changed while exporting")
        entries.append(
            {
                "document_id": document_id,
                "raw_path": document["raw_path"],
                "raw_sha256": document["raw_sha256"],
                "processed_path": f"data/processed/{document_id}.json",
                "processed_sha256": processed_sha,
                "text_sha256": item["text_sha256"],
                "structure_sha256": item["structure_sha256"],
            }
        )
        catalog.append(
            {
                "document_id": document_id,
                "title": document["title"],
                "issuer": document["issuer"],
                "source_url": document["source_url"],
                "language": document["source_fields"]["language"],
                "celex": document["source_fields"]["celex"],
                "eli": document["source_fields"]["eli"],
                "version_type": document["source_fields"]["version_type"],
                "published_at": document["published_at"],
                "effective_at": document["effective_at"],
                "dates": document["source_fields"]["dates"],
                "accepted": {
                    "raw_path": source["snapshot"]["path"],
                    "raw_sha256": source["snapshot"]["sha256"],
                    "clean_text_path": f"data/processed/{document_id}.txt",
                    "clean_text_sha256": item["text_sha256"],
                    "structure_json_path": f"data/processed/{document_id}.json",
                    "structure_json_sha256": document["source_fields"]["accepted_structure_json_sha256"],
                },
                "formal": {
                    "raw_path": f"data/formal_corpus/raw/{row['raw_name']}",
                    "raw_sha256": document["raw_sha256"],
                    "processed_path": f"data/formal_corpus/processed/{document_id}.json",
                    "processed_sha256": processed_sha,
                    "text_sha256": item["text_sha256"],
                    "structure_sha256": item["structure_sha256"],
                },
                "structure_counts": {
                    "chapters": len(document["chapters"]),
                    "sections": len(document["sections"]),
                    "main_articles": len(document["articles"]),
                },
                "cleaning_rules": row["accepted"]["cleaning_rules"],
            }
        )
    expected_raw = {row["raw_name"] for row in accepted_rows}
    expected_json = {f"{document['document_id']}.json" for document in documents}
    for path in raw_dir.iterdir():
        if path.is_file() and path.name not in expected_raw:
            path.unlink()
    for path in processed_dir.iterdir():
        if path.is_file() and path.name not in expected_json:
            path.unlink()
    package_manifest = {
        "schema_version": "1.0",
        "kind": "formal_corpus",
        "corpus_version": version,
        "parser_version": PARSER_VERSION,
        "documents": entries,
    }
    write_json(package / "manifest.json", package_manifest)
    corpus_manifest = {
        "schema_version": "1.0",
        "kind": "corpus_manifest",
        "corpus_version": version,
        "parser_version": PARSER_VERSION,
        "path_basis": {
            "corpus_manifest": "Paths in data/corpus_manifest.json are relative to the project root.",
            "formal_package": (
                "B sets data_dir to data/formal_corpus and reads data/formal_corpus/manifest.json. "
                "A path starting with data/ drops that first segment and resolves inside data_dir."
            ),
        },
        "version_algorithm": {
            "module": "app.retrieval.types",
            "canonical": "json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))",
            "digest": "SHA-256 of the canonical JSON encoded as UTF-8",
            "material": {
                "parser_version": PARSER_VERSION,
                "documents": f"sorted by document_id; fields: {', '.join(VERSION_KEYS)}",
            },
            "structure_sha256": "digest of the adapted articles array, including label, chapter, and section",
            "accepted_structure_json_sha256": "SHA-256 of the accepted data/processed JSON file bytes",
            "excluded_from_fingerprint": ["corpus_version", "processed_sha256", "registered_at", "exported_at"],
        },
        "package": {
            "data_dir": "data/formal_corpus",
            "manifest": "data/formal_corpus/manifest.json",
            "manifest_sha256": file_hash(package / "manifest.json"),
        },
        "documents": catalog,
    }
    write_json(root / "data" / "corpus_manifest.json", corpus_manifest)
    return {
        "corpus_version": version,
        "documents": len(documents),
        "main_articles": sum(len(document["articles"]) for document in documents),
        "entries": entries,
    }


def verify_corpus(root: Path) -> dict:
    package = root / "data" / "formal_corpus"
    manifest_path = package / "manifest.json"
    corpus_path = root / "data" / "corpus_manifest.json"
    if not manifest_path.is_file() or not corpus_path.is_file():
        fail("formal manifest or corpus manifest is missing")
    package_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    corpus_manifest = json.loads(corpus_path.read_text(encoding="utf-8"))
    version = package_manifest["corpus_version"]
    if corpus_manifest["corpus_version"] != version:
        fail("corpus manifest version differs from the formal package")
    documents = formal_loader(package)(version)
    identities = [document["document_id"] for document in documents]
    if len(identities) != len(set(identities)):
        fail("formal_loader returned duplicate document ids")
    if identities != sorted(identities):
        fail("formal package document order is not sorted by document_id")
    article_count = 0
    for document, entry, catalog in zip(documents, package_manifest["documents"], corpus_manifest["documents"], strict=True):
        document_id = document["document_id"]
        if document_id != entry["document_id"] or document_id != catalog["document_id"]:
            fail(f"document_id={document_id}: manifest row is out of order")
        accepted_text = (root / catalog["accepted"]["clean_text_path"]).read_text(encoding="utf-8")
        if document["text"] != accepted_text:
            fail(f"document_id={document_id}: loaded text differs from the accepted txt")
        if hashlib.sha256(document["text"].encode("utf-8")).hexdigest() != entry["text_sha256"]:
            fail(f"document_id={document_id}: text_sha256 mismatch")
        if digest(document["articles"]) != entry["structure_sha256"]:
            fail(f"document_id={document_id}: structure_sha256 mismatch")
        if entry["structure_sha256"] != catalog["formal"]["structure_sha256"]:
            fail(f"document_id={document_id}: package and corpus structure hashes differ")
        if file_hash(package / "raw" / Path(catalog["formal"]["raw_path"]).name) != entry["raw_sha256"]:
            fail(f"document_id={document_id}: formal raw hash mismatch")
        if file_hash(package / "processed" / f"{document_id}.json") != entry["processed_sha256"]:
            fail(f"document_id={document_id}: formal processed hash mismatch")
        if file_hash(root / catalog["accepted"]["structure_json_path"]) != catalog["accepted"]["structure_json_sha256"]:
            fail(f"document_id={document_id}: accepted structure file hash mismatch")
        accepted = json.loads((root / catalog["accepted"]["structure_json_path"]).read_text(encoding="utf-8"))
        check_article_identity(document_id, document["text"], accepted, document)
        check_practices_sections(document)
        article_count += len(document["articles"])
        if catalog["structure_counts"]["main_articles"] != len(document["articles"]):
            fail(f"document_id={document_id}: article count differs from the manifest")
    material = version_material(documents)
    if digest(material) != version:
        fail("recomputed corpus version differs from the manifest")
    if set(identities) == set(OFFICIAL_IDS):
        if article_count != 121:
            fail(f"official corpus main articles computed as {article_count}")
        if len(documents) != 5:
            fail(f"official corpus document count computed as {len(documents)}")
    return {
        "corpus_version": version,
        "documents": len(documents),
        "main_articles": article_count,
    }


def require_official_catalog(sources: list[dict]) -> None:
    """正式 CLI 只接受五份官方文档。缺少或多出文档时失败，且此时尚未写交付包。"""
    found = {item["document_id"] for item in sources}
    expected = set(OFFICIAL_IDS)
    missing = sorted(expected - found)
    extra = sorted(found - expected)
    if not missing and not extra:
        return
    detail = "official export requires exactly these document_ids: " + ", ".join(OFFICIAL_IDS)
    if missing:
        detail += "; missing: " + ", ".join(missing)
    if extra:
        detail += "; extra: " + ", ".join(extra)
    fail(detail)


def export_official(root: Path) -> dict:
    """正式入口。通用 export_corpus 仍可导出测试用小语料。"""
    require_official_catalog(load_sources(root))
    return export_corpus(root)


def main(root: Path | None = None) -> int:
    root = ROOT if root is None else root
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    progress = Progress(2)
    summary = export_official(root)
    progress.advance()
    checked = verify_corpus(root)
    progress.advance()
    progress.finish()
    if summary["corpus_version"] != checked["corpus_version"]:
        fail("export and loader versions differ")
    print(f"corpus_version={checked['corpus_version']}")
    print(f"documents={checked['documents']}")
    print(f"main_articles={checked['main_articles']}")
    print("result=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
