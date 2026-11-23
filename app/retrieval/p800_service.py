"""Read-only P800 parent–child retrieval for the experimental frontend page.

The formal four-condition experiment remains untouched.  This service reads the
separate ``<data_dir>/extension/p800`` index built by ``scripts.build_p800`` and
returns parent-level hits whose matched child is included for highlighting.
"""
from __future__ import annotations

from pathlib import Path
import json
from time import perf_counter

from .errors import RetrievalError
from .parent_child import aggregate_parents
from .vector_store import ChromaStore


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


class P800Service:
    """Lazy, read-only access to one built P800 extension index."""

    def __init__(self, directory: Path, *, embedder, documents: list[dict], corpus_version: str):
        self.directory = Path(directory)
        self.embedder = embedder
        self.corpus_version = corpus_version
        self.documents = {document["document_id"]: document for document in documents}

        manifest_path = self.directory / "manifest.json"
        if not manifest_path.is_file():
            raise RetrievalError(
                "P800_NOT_READY",
                "P800 index is not built. Run: python -m scripts.build_p800 --config config/experiment.formal-a.json",
                409,
            )
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RetrievalError("P800_NOT_READY", "P800 manifest is unreadable", 409) from exc
        if manifest.get("state") != "completed":
            raise RetrievalError("P800_NOT_READY", "P800 index build is incomplete or failed", 409)
        if manifest.get("corpus_version") != corpus_version:
            raise RetrievalError("VERSION_MISMATCH", "P800 index belongs to another corpus version", 409)

        self.manifest = manifest
        self.index_version = manifest["index_version"]
        try:
            self.parents = {row["chunk_id"]: row for row in _read_jsonl(self.directory / "parents.jsonl")}
            self.children = {row["chunk_id"]: row for row in _read_jsonl(self.directory / "children.jsonl")}
        except (OSError, ValueError) as exc:
            raise RetrievalError("P800_NOT_READY", "P800 parent/child exports are unreadable", 409) from exc
        counts = manifest.get("counts", {})
        if len(self.parents) != counts.get("parents") or len(self.children) != counts.get("children"):
            raise RetrievalError("SOURCE_MISMATCH", "P800 manifest counts differ from the JSONL exports", 409)

        chroma_dir = self.directory / "chroma" / self.index_version
        if not chroma_dir.is_dir():
            raise RetrievalError("P800_NOT_READY", "P800 Chroma directory is missing", 409)
        self.store = ChromaStore(chroma_dir)

    @classmethod
    def from_data_dir(cls, data_dir: Path, *, embedder, documents: list[dict], corpus_version: str):
        return cls(Path(data_dir) / "extension" / "p800", embedder=embedder,
                   documents=documents, corpus_version=corpus_version)

    @staticmethod
    def status(data_dir: Path) -> dict:
        """Cheap status check used by the page; never loads the embedding model."""
        directory = Path(data_dir) / "extension" / "p800"
        manifest_path = directory / "manifest.json"
        if not manifest_path.is_file():
            return {
                "ready": False,
                "reason": "P800_NOT_BUILT",
                "message": "P800 index is not built. Run scripts.build_p800 first.",
                "directory": str(directory),
            }
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"ready": False, "reason": "P800_MANIFEST_INVALID",
                    "message": "P800 manifest is unreadable.", "directory": str(directory)}
        version = manifest.get("index_version")
        chroma_dir = directory / "chroma" / version if version else None
        ready = bool(
            manifest.get("state") == "completed"
            and version
            and chroma_dir is not None
            and chroma_dir.is_dir()
            and (directory / "parents.jsonl").is_file()
            and (directory / "children.jsonl").is_file()
        )
        return {
            "ready": ready,
            "reason": None if ready else "P800_NOT_READY",
            "message": None if ready else "P800 index is incomplete; rebuild it with scripts.build_p800.",
            "directory": str(directory),
            "state": manifest.get("state"),
            "index_version": version,
            "corpus_version": manifest.get("corpus_version"),
            "child_chars": manifest.get("material", {}).get("child_chars"),
            "min_child_chars": manifest.get("material", {}).get("min_child_chars"),
            "counts": manifest.get("counts", {}),
        }

    def search(self, question: str, *, candidate_k: int = 50, top_k: int = 5) -> dict:
        if not isinstance(question, str) or not question.strip():
            raise RetrievalError("INVALID_REQUEST", "Question is required", 422)
        if type(candidate_k) is not int or not 5 <= candidate_k <= 100:
            raise RetrievalError("INVALID_REQUEST", "candidate_k must be an integer between 5 and 100", 422)
        if top_k != 5:
            raise RetrievalError("INVALID_REQUEST", "P800 returns exactly five parents", 422)

        start = perf_counter()
        vector = self.embedder.encode([question], query=True, ids=["question"])[0]
        found = self.store.query("p800", vector, candidate_k)
        hits = aggregate_parents(found, self.children, self.parents, top_k=top_k)
        for hit in hits:
            document = self.documents.get(hit["document_id"])
            if document is None:
                raise RetrievalError("SOURCE_MISMATCH", "P800 parent belongs to an absent document", 409)
            hit["title"] = document["title"]
            hit["source_url"] = document["source_url"]
            hit["article_labels"] = [
                article["label"] for article in document["articles"]
                if article["article_id"] in hit["article_ids"]
            ]
            child = self.children.get(hit["matched_child_id"])
            hit["matched_child_text"] = child["text"] if child is not None else ""
        return {
            "condition": "p800",
            "corpus_version": self.corpus_version,
            "index_version": self.index_version,
            "candidate_k": candidate_k,
            "child_count": len(found),
            "parent_count": len({hit["chunk_id"] for hit in hits}),
            "hits": hits,
            "timing_ms": round((perf_counter() - start) * 1000, 3),
        }

    def close(self):
        self.store.close()
