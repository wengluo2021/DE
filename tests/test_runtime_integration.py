"""Real B chunking/Chroma + C production composition; external adapters mocked."""
import json
import time

from fastapi.testclient import TestClient
import pytest

from app.config import load_settings
from app.data import corpus_loader
from app.main import create_app
from app.qa.client import ChatCompletionsClient
from app.qa.errors import QAError
from app.retrieval.embedding import MockEmbedder
from tests.support.c_fixtures import FixtureGenerator
from tests.support.integration_fixtures import write_bundle


class OfflineEncoder(MockEmbedder):
    def __init__(self,config):
        self.config=config


def _wait(client,task_id):
    end=time.monotonic()+15
    while time.monotonic()<end:
        task=client.get("/api/tasks/"+task_id).json()
        if task["state"] in {"completed","failed"}:return task
        time.sleep(0.02)
    pytest.fail("B/C integration task timed out")


def test_production_runtime_build_search_ask_and_restart_share_b(tmp_path,monkeypatch):
    from app.retrieval import embedding
    monkeypatch.setattr(embedding,"LocalEmbedder",OfflineEncoder)
    generator=FixtureGenerator();calls=[]
    def generate(self,messages):
        calls.append(messages);return generator.generate(messages)
    monkeypatch.setattr(ChatCompletionsClient,"generate",generate)
    data=tmp_path/"SYNTHETIC";bundle=write_bundle(data)
    settings=load_settings(environ={},api_key="synthetic-integration-key",overrides={
        "data_dir":str(data),"corpus_version":bundle["corpus_version"],"gold_version":bundle["gold_version"],
        "generation":{"model":"fixture-model"}})
    app=create_app(settings,test_mode=True)  # No QA or retrieval service injection.
    with TestClient(app) as client:
        assert app.state.runtime.retrieval is not None
        assert not client.get("/api/health").json()["ready"]
        body={"question":"What does Article 2 state?","condition":"s400","corpus_version":bundle["corpus_version"]}
        assert client.post("/api/ask",json=body).json()["code"]=="INDEX_NOT_READY"
        planned=client.post("/api/indexes/build",json={"corpus_version":bundle["corpus_version"]})
        assert planned.status_code==202
        task=_wait(client,planned.json()["task_id"])
        assert task["state"]=="completed" and task["kind"]=="indexes"
        index=task["result_id"]
        assert client.get("/api/health").json()["ready"]
        assert len(client.get("/api/documents",params={"corpus_version":bundle["corpus_version"]}).json()["items"])==5
        for condition in settings.experiment.conditions:
            question=dict(body,condition=condition)
            answer=client.post("/api/ask",json=question)
            assert answer.status_code==200
            result=answer.json()
            assert result["condition"]==condition and result["index_version"]==index
            assert len(result["citations"])==5 and result["answer"]=="Article 2 states B.[1]"
            for hit in result["citations"]:
                doc=next(d for d in bundle["documents"] if d["document_id"]==hit["document_id"])
                assert hit["text"]==doc["text"][hit["start"]:hit["end"]]
        compare=client.post("/api/compare",json={"question":body["question"],"corpus_version":bundle["corpus_version"],
                                              "left_condition":"f400","right_condition":"s800"}).json()
        assert compare["index_version"]==index and compare["left"]["condition"]=="f400" and compare["right"]["condition"]=="s800"
        conversation=result["conversation_id"]
        stored=client.get("/api/conversations/"+conversation).json()
        assert stored["asks"][0]["result"]==result and len(calls)==4
    with TestClient(create_app(settings,test_mode=True)) as reopened:
        assert reopened.get("/api/health").json()["ready"]
        assert reopened.get("/api/conversations/"+conversation).json()["asks"][0]["result"]==result
        assert len(calls)==4  # Reads/restart must not regenerate.


def test_invalid_a_inputs_are_rejected_before_b_assembly_and_model_call(tmp_path,monkeypatch):
    bundle=write_bundle(tmp_path)
    (tmp_path/"raw/synthetic-0.txt").write_text("tampered",encoding="utf-8")
    settings=load_settings(environ={},overrides={"data_dir":str(tmp_path),"corpus_version":bundle["corpus_version"]})
    with TestClient(create_app(settings)) as client:
        health=client.get("/api/health").json()
        assert not health["ready"] and health["components"]["retrieval"]["issue"]=="INVALID_CORPUS_DATA"
        assert client.get("/api/documents",params={"corpus_version":bundle["corpus_version"]}).json()["code"]=="INVALID_CORPUS_DATA"
        assert client.app.state.runtime.retrieval is None
