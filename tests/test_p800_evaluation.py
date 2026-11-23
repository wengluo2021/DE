"""P800 extension evaluation is a separate 30-item run, never the frozen 120."""
from copy import deepcopy
import csv
import io
import json
import time

from fastapi.testclient import TestClient
import pytest

from app.config import load_settings
from app.qa.service import QAService
from app.main import create_app
from tests.support.c_fixtures import document_loader, retrieve
from tests.support.evaluation_fixtures import dataset, EvaluationGenerator


def p800_retrieve(*, question, condition=None, corpus_version, top_k=5):
    base = retrieve(question=question, condition="s800", corpus_version=corpus_version, top_k=top_k)
    hit = deepcopy(base["hits"][0])
    hit["condition"] = "p800"
    hit["chunk_id"] = "p800-fixture-" + hit["chunk_id"][:16]
    return {"condition": "p800", "corpus_version": corpus_version,
            "index_version": "c-fixture-index-v1", "hits": [hit], "timing_ms": 0.0}


def setup(tmp_path):
    settings = load_settings(environ={}, overrides={
        "data_dir": str(tmp_path / "data"), "gold_version": "fixture-gold-v1",
        "generation": {"provider": "mock", "model": "fixture-model"}})
    generator = EvaluationGenerator()
    qa = QAService(settings, retriever=retrieve, document_loader=document_loader,
                   generator=generator, index_version="c-fixture-index-v1")
    p800 = QAService(settings, retriever=p800_retrieve, document_loader=document_loader,
                     generator=generator, index_version="c-fixture-index-v1")
    app = create_app(settings, qa_service=qa, test_mode=True, gold_loader=dataset)
    return app, generator, p800


def wait(client, task_id):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        task = client.get("/api/tasks/" + task_id).json()
        if task["state"] in {"completed", "failed"}:
            return task
        time.sleep(0.05)
    pytest.fail("P800 evaluation did not finish")


def test_p800_runs_30_cases_as_extension_and_exports(tmp_path):
    app, generator, p800 = setup(tmp_path)
    with TestClient(app) as client:
        app.state.runtime.p800_qa = p800
        response = client.post("/api/evaluations/p800/run",
                               json={"corpus_version": "fixture-en-v2", "gold_version": "fixture-gold-v1"})
        assert response.status_code == 202, response.text
        plan = response.json()
        task = wait(client, plan["task_id"])
        assert task["state"] == "completed" and task["completed"] == task["total"] == 30
        assert task["result"] == {"run_id": plan["run_id"], "processed": 30, "total": 30, "errors": 0}

        run = client.get("/api/evaluations/" + plan["run_id"]).json()
        assert run["state"] == "completed"
        assert len(run["cases"]) == 30
        assert {row["condition"] for row in run["cases"]} == {"p800"}
        assert list(run["summary"]) == ["p800"]
        assert len(run["paired_cases"]) == 30
        assert set(run["paired_cases"][0]["conditions"]) == {"p800"}
        assert run["summary"]["p800"]["hit_at_5_all"]["value"] == 1
        assert run["summary"]["p800"]["answer_accuracy"]["pending"] == 24
        assert run["config"]["conditions"] == ["p800"]
        assert run["config"]["extension"] == "p800"
        assert not run["formal_results"]

        # The extension did not create a second four-condition run or 120 rows.
        assert len(client.get("/api/evaluations").json()["items"]) == 1

        row = next(r for r in run["cases"] if r["gold"]["answerable"])
        review = {"reviewer": "p800-test", "answer_grade": "correct",
                  "claim_reviews": [{"claim_index": 0, "supported": True, "reason": "Synthetic B."}]}
        path = f"/api/evaluations/{plan['run_id']}/cases/{row['case_id']}?condition=p800"
        assert client.patch(path, json=review).status_code == 200
        after = client.get("/api/evaluations/" + plan["run_id"]).json()
        assert after["summary"]["p800"]["answer_accuracy"]["pending"] == 23
        assert len(after["review_history"]) == 1

        exported = list(csv.DictReader(io.StringIO(
            client.get(f"/api/evaluations/{plan['run_id']}/export?format=csv").text)))
        assert len(exported) == 30
        assert all(row["condition"] == "p800" for row in exported)
        assert len(generator.messages) == 30


def test_p800_preflight_rejects_missing_p800_provider(tmp_path):
    app, _, _ = setup(tmp_path)
    app.state.runtime.p800_qa = None
    with TestClient(app) as client:
        # The injected four-condition QA is deliberately still present: P800 must
        # not silently reuse it when a dedicated P800 provider is missing.
        app.state.runtime.injected_qa = None
        response = client.post("/api/evaluations/p800/run",
                               json={"corpus_version": "fixture-en-v2", "gold_version": "fixture-gold-v1"})
        assert response.status_code in {409, 503}
        assert client.get("/api/evaluations").json()["items"] == []
