from app.retrieval.types import FIXTURE_CORPUS_VERSION
import copy
import json
import math
from pathlib import Path
from types import SimpleNamespace
import pytest

from app.retrieval import RetrievalService, RetrievalError
from app.retrieval.embedding import MockEmbedder, LocalEmbedder
from app.retrieval.types import (ROOT, CONDITIONS, fixture_loader, load_config, formal_loader,
                                 canonical, digest, write_json, file_hash)


def service_at(tmp_path, *, loader=fixture_loader, embedder=None):
    config = load_config(data_dir=tmp_path)
    return RetrievalService(loader, embedder or MockEmbedder(), config)


def test_chroma_build_search_compare_and_idempotency(tmp_path):
    service = service_at(tmp_path)
    manifest = service.build_indexes(FIXTURE_CORPUS_VERSION)
    assert manifest["state"] == "completed"
    assert set(manifest["conditions"]) == set(CONDITIONS)
    assert service.build_indexes(FIXTURE_CORPUS_VERSION) == manifest
    version = manifest["index_version"]
    for condition in CONDITIONS:
        exported = service.indexes.read_chunks(version, condition)
        assert len(service.indexes.store(version).ids(condition)) == len(exported)
        assert manifest["conditions"][condition]["count"] == len(exported)
        for hit in service.search("personal information deletion", condition, FIXTURE_CORPUS_VERSION):
            doc = service.document(hit["document_id"], FIXTURE_CORPUS_VERSION)
            assert hit["text"] == doc["text"][hit["start"]:hit["end"]]
            assert hit["source_url"] == doc["source_url"]
    result = service.compare("library book renewal", "f400", "s400", FIXTURE_CORPUS_VERSION)
    assert result["index_version"] == version
    for side in ("left", "right"):
        assert result[side]["context_chars"] == sum(len(x["text"]) for x in result[side]["hits"])
        assert len(result[side]["hits"]) == 5
    # New service/process-style restart reopens persistent Chroma, no rebuild required.
    reopened = service_at(tmp_path)
    assert reopened.search("renewal", "s800", FIXTURE_CORPUS_VERSION)


class FixedEmbedder(MockEmbedder):
    def encode(self, texts, *, query=False, ids=None):
        return [[0.9, math.sqrt(0.19)] if query else [1.0, 0.0] for _ in texts]

    def identity(self):
        return dict(super().identity(), model_id="test-only/fixed", dimension=2)


def test_exact_hit_contract_cosine_score_and_less_than_five(tmp_path):
    s = service_at(tmp_path, loader=lambda v: fixture_loader(v)[:1], embedder=FixedEmbedder())
    s.build_indexes(FIXTURE_CORPUS_VERSION)
    hits = s.search("What does Article 2 say?", "s400", FIXTURE_CORPUS_VERSION)
    expected = json.loads((ROOT / "tests/fixtures/b/expected_hits.json").read_text(encoding="utf-8"))["hit"]
    assert len(hits) == 1
    score = hits[0].pop("score")
    assert score == pytest.approx(expected.pop("score"), abs=1e-6)
    assert hits[0] == expected


def test_versions_reject_source_mutation_and_incomplete_indexes(tmp_path):
    docs = fixture_loader(FIXTURE_CORPUS_VERSION)
    service = service_at(tmp_path, loader=lambda v: copy.deepcopy(docs))
    with pytest.raises(RetrievalError, match="Build all"):
        service.search("test", "s400", FIXTURE_CORPUS_VERSION)
    manifest = service.build_indexes(FIXTURE_CORPUS_VERSION)
    with pytest.raises(RetrievalError) as exc:
        service.search("test", "s400", "another-version")
    assert exc.value.code == "VERSION_MISMATCH"
    docs[0]["text"] += "变动"
    with pytest.raises(RetrievalError) as exc:
        service.search("test", "s400", FIXTURE_CORPUS_VERSION)
    assert exc.value.code == "INDEX_NOT_READY"
    docs[0]["text"] = docs[0]["text"][:-2]
    path = service.indexes.manifest_path(manifest["index_version"])
    manifest["state"] = "failed"
    write_json(path, manifest)
    with pytest.raises(RetrievalError, match="incomplete"):
        service.search("test", "s400", FIXTURE_CORPUS_VERSION)
    assert service.build_indexes(FIXTURE_CORPUS_VERSION)["state"] == "completed"


def test_failed_partial_build_cannot_query_and_retry_has_no_duplicates(tmp_path):
    class Failing(MockEmbedder):
        fail = True
        calls = 0
        def encode(self, texts, **kwargs):
            self.calls += 1
            if self.fail and self.calls == 2:
                raise RetrievalError("EMBEDDING_UNAVAILABLE", "injected failure", 503)
            return super().encode(texts, **kwargs)
    model = Failing()
    service = service_at(tmp_path, embedder=model)
    with pytest.raises(RetrievalError, match="injected"):
        service.build_indexes(FIXTURE_CORPUS_VERSION)
    with pytest.raises(RetrievalError, match="incomplete"):
        service.search("test", "s400", FIXTURE_CORPUS_VERSION)
    model.fail = False
    manifest = service.build_indexes(FIXTURE_CORPUS_VERSION)
    assert manifest["state"] == "completed"
    for condition in CONDITIONS:
        assert len(service.indexes.store(manifest["index_version"]).ids(condition)) == manifest["conditions"][condition]["count"]


def test_chunk_export_tampering_is_detected(tmp_path):
    s = service_at(tmp_path)
    m = s.build_indexes(FIXTURE_CORPUS_VERSION)
    s.indexes.chunk_path(m["index_version"], "s400").write_text("{}\n", encoding="utf-8")
    with pytest.raises(RetrievalError) as exc:
        s.search("test", "s400", FIXTURE_CORPUS_VERSION)
    assert exc.value.code == "SOURCE_MISMATCH"


def test_token_overflow_before_sentence_transformer_can_truncate(tmp_path):
    config = load_config()["embedding"]
    config["max_input_tokens"] = 4
    embedder = LocalEmbedder(config)
    called = []
    embedder._model = SimpleNamespace(tokenizer=lambda text, **kw: {"input_ids": list(range(len(text) + 2))},
                                     encode=lambda *a, **kw: called.append(True))
    embedder._load = lambda: None
    with pytest.raises(RetrievalError) as exc:
        embedder.encode(["abc"], ids=["doc/chunk-123"])
    assert exc.value.code == "MODEL_INPUT_TOO_LONG"
    assert "doc/chunk-123" in exc.value.message
    assert not called


def test_missing_model_and_formal_data_do_not_fallback(tmp_path):
    config = load_config(model_dir=tmp_path)["embedding"]
    with pytest.raises(RetrievalError) as exc:
        LocalEmbedder(config).encode(["text"])
    assert exc.value.code == "EMBEDDING_UNAVAILABLE"
    with pytest.raises(RetrievalError) as exc:
        formal_loader(tmp_path)(FIXTURE_CORPUS_VERSION)
    assert exc.value.code == "NOT_FOUND"


def test_formal_manifest_hash_validation(tmp_path):
    doc = copy.deepcopy(fixture_loader(FIXTURE_CORPUS_VERSION)[0])
    raw = tmp_path / "raw/a.txt"
    raw.parent.mkdir()
    raw.write_text(doc["text"], encoding="utf-8", newline="\n")
    doc["raw_path"] = "data/raw/a.txt"
    doc["raw_sha256"] = file_hash(raw)
    entry = {"document_id": doc["document_id"], "raw_path": doc["raw_path"], "raw_sha256": doc["raw_sha256"],
             "processed_path": "data/processed/a.json", "text_sha256": file_hash(raw), "structure_sha256": digest(doc["articles"])}
    material = {k: doc[k] for k in ("document_id", "title", "issuer", "source_url", "published_at", "effective_at", "raw_sha256")}
    material.update(text_sha256=entry["text_sha256"], structure_sha256=entry["structure_sha256"])
    version = digest({"parser_version": "test-parser-v1", "documents": [material]})
    doc["corpus_version"] = version
    processed = tmp_path / "processed/a.json"
    write_json(processed, doc)
    entry["processed_sha256"] = file_hash(processed)
    write_json(tmp_path / "manifest.json", {"schema_version": "1.0", "corpus_version": version,
                                           "parser_version": "test-parser-v1", "documents": [entry]})
    assert formal_loader(tmp_path)(version) == [doc]
    raw.write_text("tampered", encoding="utf-8")
    with pytest.raises(RetrievalError) as exc:
        formal_loader(tmp_path)(version)
    assert exc.value.code == "SOURCE_MISMATCH"


def test_index_version_ignores_machine_paths_but_covers_model_settings(tmp_path):
    first, second = service_at(tmp_path / "a"), service_at(tmp_path / "b")
    docs = fixture_loader(FIXTURE_CORPUS_VERSION)
    assert first.indexes.material(FIXTURE_CORPUS_VERSION, docs) == second.indexes.material(FIXTURE_CORPUS_VERSION, docs)
    class Other(MockEmbedder):
        def identity(self):
            return dict(super().identity(), revision="changed-revision")
    second.indexes.embedder = Other()
    assert digest(first.indexes.material(FIXTURE_CORPUS_VERSION, docs)) != digest(second.indexes.material(FIXTURE_CORPUS_VERSION, docs))
