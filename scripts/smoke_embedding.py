"""真实模型冒烟：用合成数据检查编码、四组索引、检索及 API，不是正式法规评估。"""
from app.retrieval.types import FIXTURE_CORPUS_VERSION
import argparse
from pathlib import Path
from time import perf_counter
import platform
import importlib.metadata
import sys
import json

from app.retrieval import RetrievalService, RetrievalError
from app.retrieval.embedding import LocalEmbedder
from app.retrieval.types import load_config, fixture_loader, ROOT, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--data-dir")
    parser.add_argument("--model-dir")
    parser.add_argument("--output", default="artifacts/b/real-smoke.json")
    args = parser.parse_args()
    config = load_config(args.config, model_dir=args.model_dir, data_dir=args.data_dir)
    config["data_dir"] = str(Path(config["data_dir"]) / "b-fixtures/real")
    embedder = LocalEmbedder(config["embedding"])
    service = RetrievalService(fixture_loader, embedder, config)
    begin = perf_counter()
    # 完整且校验通过的同版本索引可复用；指定空数据目录则会重新编码构建四组。
    manifest = service.build_indexes(FIXTURE_CORPUS_VERSION)
    vectors = embedder.encode(["personal information deletion", "library book renewal"], query=True)
    assert len(vectors) == 2 and all(len(v) == 1024 for v in vectors)
    checks = []
    # 3 个主题问题 × 4 个条件 = 12 次检索，检查第一名返回了对应主题的文档。
    cases = json.loads((ROOT / "tests/fixtures/b/search_cases.json").read_text(encoding="utf-8"))
    questions = [(case["question"], case["expected_document_id"]) for case in cases]
    for condition in config["conditions"]:
        for question, expected_document in questions:
            result = service.search_result(question, condition, FIXTURE_CORPUS_VERSION)
            assert any(hit["document_id"] == expected_document for hit in result["hits"]), result
            assert result["hits"][0]["document_id"] == expected_document, result
            for hit in result["hits"]:
                source = service.document(hit["document_id"], FIXTURE_CORPUS_VERSION)
                assert source["text"][hit["start"]:hit["end"]] == hit["text"]
                assert hit["source_url"] == source["source_url"]
                assert hit["article_ids"] == [a["article_id"] for a in source["articles"]
                    if max(hit["start"], a["start"]) < min(hit["end"], a["end"])]
            checks.append({"question": question, "expected_document_id": expected_document, **result})
    # 故意构造超长输入，用真实 tokenizer 验证“超限拒绝”是否生效。
    # 英文 law 重复 9000 次；具体 token 数由真实 tokenizer 决定。
    try:
        embedder.encode(["law " * 9000], query=True, ids=["overflow-query"])
    except RetrievalError as exc:
        assert exc.code == "MODEL_INPUT_TOO_LONG"
        overflow = exc.as_dict()
    else:
        raise AssertionError("Real tokenizer overflow was not rejected")
    # 在同一进程通过 HTTP 测试客户端调用真实服务，不需要另外先启动 uvicorn。
    from fastapi.testclient import TestClient
    from tests.support.b_app import create_app
    with TestClient(create_app(service, mode="real")) as client:
        status = client.get("/b-debug/status")
        assert status.json()["ready"]
        response = client.post("/api/search", json={"question": questions[0][0], "condition": "s400", "corpus_version": FIXTURE_CORPUS_VERSION})
        assert response.status_code == 200, response.text
        compare = client.post("/api/compare", json={"question": questions[1][0], "corpus_version": FIXTURE_CORPUS_VERSION, "left_condition": "f800", "right_condition": "s800"})
        assert compare.status_code == 200, compare.text
    # 保存软件版本、索引材料、命中快照与 API 响应，便于组员和老师核对。
    result = {"state": "passed", "scope": "real embedding + synthetic fixtures, NOT formal evaluation",
              "python": platform.python_version(), "platform": platform.platform(),
              "packages": {n: importlib.metadata.version(n) for n in ["torch", "sentence-transformers", "transformers", "chromadb"]},
              "device": config["embedding"]["device"], "dimension": len(vectors[0]), "overflow_check": overflow,
              "source_slice_checks": "passed for every retrieved hit",
              "manifest": manifest, "checks": checks, "api_search": response.json(), "api_compare": compare.json(),
              "elapsed_ms": round((perf_counter() - begin) * 1000, 3)}
    target = Path(args.output)
    if not target.is_absolute():
        target = ROOT / target
    write_json(target, result)
    write_json(target.with_name("model-manifest.json"), {"model_id": embedder.identity()["model_id"],
               "revision": embedder.identity()["revision"], "files": embedder.identity()["files"]})
    print(f"PASS: 12 real retrieval checks, tokenizer overflow and HTTP APIs; record: {target}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Real smoke FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
