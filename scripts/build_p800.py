"""Build the P800 parent-child extension index.

This script deliberately builds only the extension collection.  It does not
touch the frozen four-condition index/version, does not call an LLM, and only
embeds child chunks (about 2.3k at the default 250-character child size).

Typical use (from the project root, with the project .venv active)::

    python -m scripts.build_p800 --config config/experiment.formal-a.json

For a model-free dry run that only writes parent/child JSONL and counts::

    python -m scripts.build_p800 --config config/experiment.formal-a.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.config import ROOT, load_settings
from app.data import corpus_loader
from app.retrieval.chunking import chunks_for_condition
from app.retrieval.embedding import LocalEmbedder
from app.retrieval.parent_child import split_children
from app.retrieval.types import canonical, digest, file_hash, write_json
from app.retrieval.vector_store import ChromaStore, store_identity

def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8", newline="\n")


def _parents_from_documents(documents: list[dict]) -> list[dict]:
    parents = [chunk for document in documents for chunk in chunks_for_condition(document, "s800")]
    parents.sort(key=lambda chunk: (chunk["document_id"], chunk["start"], chunk["end"], chunk["chunk_id"]))
    return parents


def _load_parents(path: Path, expected: list[dict]) -> list[dict]:
    parents = _read_jsonl(path)
    if any(parent.get("condition") != "s800" for parent in parents):
        raise ValueError("--parent-chunks must contain only s800 chunks")
    expected_by_id = {chunk["chunk_id"]: chunk for chunk in expected}
    actual_by_id = {chunk["chunk_id"]: chunk for chunk in parents}
    if actual_by_id.keys() != expected_by_id.keys():
        raise ValueError("--parent-chunks IDs differ from the frozen S800 chunker output")
    for chunk_id, parent in actual_by_id.items():
        if parent["text"] != expected_by_id[chunk_id]["text"]:
            raise ValueError(f"--parent-chunks text differs from frozen source: {chunk_id}")
    parents.sort(key=lambda chunk: (chunk["document_id"], chunk["start"], chunk["end"], chunk["chunk_id"]))
    return parents


def _manifest_path(out_dir: Path) -> Path:
    return out_dir / "manifest.json"


def _build(args) -> dict:
    settings = load_settings(args.config)
    config = settings.retrieval_config()
    corpus_version = config["corpus_version"]
    data_dir = Path(config["data_dir"])

    loader = corpus_loader(data_dir, formal=settings.experiment.mode == "formal")
    documents = sorted(loader(corpus_version), key=lambda document: document["document_id"])
    recomputed_parents = _parents_from_documents(documents)
    if args.parent_chunks:
        parent_path = Path(args.parent_chunks)
        if not parent_path.is_absolute():
            parent_path = ROOT / parent_path
        parents = _load_parents(parent_path, recomputed_parents)
    else:
        parents = recomputed_parents

    children = split_children(
        parents,
        child_chars=args.child_chars,
        min_child_chars=args.min_child_chars,
    )
    indexed = [child for child in children if child["indexable"]]
    if not indexed:
        raise ValueError("No indexable children were produced; lower --min-child-chars")
    indexed_parent_ids = {child["parent_id"] for child in indexed}
    unindexed_parent_ids = sorted({parent["chunk_id"] for parent in parents} - indexed_parent_ids)

    out_dir = Path(args.out) if args.out else (data_dir / "extension" / "p800")
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    parents_path = out_dir / "parents.jsonl"
    children_path = out_dir / "children.jsonl"
    _write_jsonl(parents_path, parents)
    _write_jsonl(children_path, children)

    summary = {
        "corpus_version": corpus_version,
        "parent_condition": "s800",
        "child_chars": args.child_chars,
        "min_child_chars": args.min_child_chars,
        "parents": len(parents),
        "children": len(children),
        "indexed_children": len(indexed),
        "skipped_short_children": len(children) - len(indexed),
        "parents_with_indexed_children": len(indexed_parent_ids),
        "parents_without_indexed_children": len(unindexed_parent_ids),
        "unindexed_parent_ids": unindexed_parent_ids,
        "out_dir": str(out_dir),
    }
    if args.dry_run:
        summary["dry_run"] = True
        print(canonical(summary))
        return summary

    embedder = LocalEmbedder(config["embedding"])
    identity = embedder.identity()
    material = {
        "extension": "parent-child",
        "corpus_version": corpus_version,
        "parent_condition": "s800",
        "child_chars": args.child_chars,
        "min_child_chars": args.min_child_chars,
        "parent_chunks_sha256": file_hash(parents_path),
        "child_chunks_sha256": file_hash(children_path),
        "indexed_children_digest": digest([child["chunk_id"] for child in indexed]),
        "embedding": identity,
        "vector_store": store_identity(),
    }
    index_version = digest(material)

    manifest_path = _manifest_path(out_dir)
    if manifest_path.is_file() and not args.force:
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (old.get("state") == "completed"
                and old.get("index_version") == index_version
                and old.get("material") == material):
            summary.update(index_version=index_version, state="completed", reused=True,
                           chroma=str(out_dir / "chroma" / index_version))
            print(canonical(summary))
            return summary

    manifest = {
        "schema_version": "1.0",
        "extension": "parent-child",
        "state": "running",
        "corpus_version": corpus_version,
        "index_version": index_version,
        "material": material,
        "counts": {
            "parents": len(parents),
            "children": len(children),
            "indexed_children": len(indexed),
            "parents_with_indexed_children": len(indexed_parent_ids),
            "parents_without_indexed_children": len(unindexed_parent_ids),
            "unindexed_parent_ids": unindexed_parent_ids,
        },
        "paths": {
            "parents": "parents.jsonl",
            "children": "children.jsonl",
            "chroma": f"chroma/{index_version}",
        },
        "runtime": {
            "device": config["embedding"].get("device"),
            "batch_size": args.batch_size or config["embedding"]["batch_size"],
        },
    }
    write_json(manifest_path, manifest)

    store = None
    try:
        store = ChromaStore(out_dir / "chroma" / index_version)
        collection = store.collection("p800", create=True)
        collection.count()  # fail early if the native collection cannot be opened
        batch_size = args.batch_size or config["embedding"]["batch_size"]
        cache: dict[str, list[float]] = {}
        for position in range(0, len(indexed), batch_size):
            batch = indexed[position:position + batch_size]
            missing = {
                child["text"]: f"{child['document_id']}/{child['chunk_id']}"
                for child in batch
                if child["text"] not in cache
            }
            vectors = embedder.encode(list(missing), ids=list(missing.values())) if missing else []
            if len(vectors) != len(missing):
                raise RuntimeError("Embedding batch count mismatch")
            cache.update(zip(missing, vectors, strict=True))
            store.upsert("p800", batch, [cache[child["text"]] for child in batch])
            print(f"embedded {min(position + len(batch), len(indexed))}/{len(indexed)}", flush=True)

        actual_ids = store.ids("p800")
        expected_ids = {child["chunk_id"] for child in indexed}
        if actual_ids != expected_ids:
            raise RuntimeError("Chroma collection IDs differ from the indexed child export")

        manifest["state"] = "completed"
        write_json(manifest_path, manifest)
        summary.update(index_version=index_version, state="completed", reused=False,
                       chroma=str(out_dir / "chroma" / index_version))
        print(canonical(summary))
        return summary
    except Exception as exc:
        manifest["state"] = "failed"
        manifest["error"] = str(exc)
        write_json(manifest_path, manifest)
        raise
    finally:
        if store is not None:
            store.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the P800 parent-child child index")
    parser.add_argument("--config", help="experiment JSON (default: DERAG_CONFIG or config/experiment.json)")
    parser.add_argument("--child-chars", type=int, default=250, help="maximum child length in Python characters")
    parser.add_argument("--min-child-chars", type=int, default=40,
                        help="children shorter than this stay in the parent but are not embedded")
    parser.add_argument("--batch-size", type=int, help="embedding batch size (default: config value)")
    parser.add_argument("--parent-chunks", help="optional existing s800.jsonl to reuse; IDs/text are verified")
    parser.add_argument("--out", help="output directory (default: <data_dir>/extension/p800)")
    parser.add_argument("--force", action="store_true", help="rebuild even when the manifest matches")
    parser.add_argument("--dry-run", action="store_true", help="only split/write JSONL; do not load the model")
    args = parser.parse_args()
    if args.child_chars <= 0:
        parser.error("--child-chars must be positive")
    if not 0 <= args.min_child_chars <= args.child_chars:
        parser.error("--min-child-chars must be between 0 and --child-chars")
    try:
        _build(args)
    except Exception as exc:
        print(f"P800 build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
