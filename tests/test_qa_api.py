from copy import deepcopy

from contextlib import nullcontext
from fastapi.testclient import TestClient
import pytest

from app.config import load_settings
from app.main import create_app
from app.qa.errors import QAError
from app.qa.client import GenerationResponse
from app.qa.service import QAService
from tests.support.c_fixtures import FixtureGenerator,document_loader,retrieve


@pytest.fixture
def settings(tmp_path):
    return load_settings(environ={},overrides={"data_dir":str(tmp_path/"data"),
                "generation":{"provider":"mock","model":"fixture-model"}})


def service(settings,generator=None):
    return QAService(settings,retriever=retrieve,document_loader=document_loader,
                     generator=generator or FixtureGenerator(),index_version="c-fixture-index-v1")


def body(conversation=None):
    return {"question":"What does Article 2 state?","condition":"s400",
            "corpus_version":"fixture-en-v2","conversation_id":conversation}


def test_ask_history_and_health_are_real_persistent_apis(settings):
    app=create_app(settings,qa_service=service(settings),test_mode=True)
    with TestClient(app) as client:
        health=client.get("/api/health").json()
        assert health["mode"]=="test" and health["ready"] and health["frontend_mode"]=="preview"
        assert health["components"]["generation"]["mode"]=="mock"
        first=client.post("/api/ask",json=body())
        assert first.status_code==200 and first.json()["answer"]=="Article 2 states B.[1]"
        conversation=first.json()["conversation_id"]
        second=client.post("/api/ask",json=body(conversation))
        assert second.status_code==200 and first.json()["ask_id"]!=second.json()["ask_id"]
        assert len(client.get("/api/conversations").json()["items"])==1
        assert len(client.get("/api/conversations/"+conversation).json()["asks"])==2
        assert client.get("/").status_code==200
    reopened=create_app(settings,qa_service=service(settings),test_mode=True)
    with TestClient(reopened) as client:
        assert len(client.get("/api/conversations/"+conversation).json()["asks"])==2


def test_no_data_does_not_fall_back_to_demo_or_test_results(settings):
    app=create_app(settings)
    with TestClient(app) as client:
        health=client.get("/api/health").json()
        assert not health["ready"] and health["available_conditions"]==[]
        result=client.post("/api/ask",json=body())
        assert result.status_code==409 and result.json()["code"]=="RETRIEVAL_NOT_CONFIGURED"
        conversations=client.get("/api/conversations").json()["items"]
        history=client.get("/api/conversations/"+conversations[0]["id"]).json()
        assert history["asks"][0]["state"]=="failed" and history["asks"][0]["result"] is None


@pytest.mark.parametrize("path",["/api/conversations/missing","/api/tasks/missing"])
def test_unknown_resources_use_uniform_error_format(settings,path):
    with TestClient(create_app(settings)) as client:
        result=client.get(path)
        assert result.status_code==404 and set(result.json())=={"code","message"}


def test_invalid_request_returns_422_without_sensitive_input_echo(settings):
    with TestClient(create_app(settings)) as client:
        invalid=body();invalid["condition"]="fixture-sensitive-input"
        response=client.post("/api/ask",json=invalid)
        assert response.status_code==422 and "fixture-sensitive-input" not in response.text
        assert client.get("/api/conversations").json()["items"]==[]


def test_model_failure_is_503_and_saved_without_trace_in_http_body(settings):
    class Failure:
        def generate(self,messages):
            raise QAError("LLM_AUTH_ERROR","No access",503)
    with TestClient(create_app(settings,qa_service=service(settings,Failure()),test_mode=True)) as client:
        result=client.post("/api/ask",json=body())
        assert result.status_code==503 and set(result.json())=={"code","message"}
        convo=client.get("/api/conversations").json()["items"][0]["id"]
        run=client.get("/api/conversations/"+convo).json()["asks"][0]
        assert run["state"]=="failed" and len(run["evidence"])==1


def test_unverified_provider_text_is_not_in_normal_conversation_api(settings):
    class Invalid:
        def generate(self,messages):
            return GenerationResponse("UNVERIFIED-CANDIDATE","fixture-model","stop",None,None,
                                      {"content":"UNVERIFIED-CANDIDATE"})
    app=create_app(settings,qa_service=service(settings,Invalid()),test_mode=True)
    with TestClient(app) as client:
        assert client.post("/api/ask",json=body()).status_code==502
        conversation=client.get("/api/conversations").json()["items"][0]["id"]
        response=client.get("/api/conversations/"+conversation)
        assert "UNVERIFIED-CANDIDATE" not in response.text
        assert "UNVERIFIED-CANDIDATE" in str(app.state.runtime.store.conversation(conversation))


def test_b_router_factory_is_registered_and_uses_persistent_tasks(settings):
    class Retrieval:
        def __init__(self):
            self.built=False
            self.indexes=self
        def lock(self):
            return nullcontext()
        def completed(self,version):
            if not self.built:
                raise QAError("INDEX_NOT_READY","Not built",409)
            return {"index_version":"fixture-index"},document_loader(version)
        def build_indexes(self,version):
            self.built=True
            return {"index_version":"fixture-index"}
        def documents(self,version):
            return document_loader(version)
        def search_result(self,question,condition,corpus_version,top_k=5):
            return retrieve(question=question,condition=condition,corpus_version=corpus_version,top_k=top_k)
    retrieval=Retrieval()
    with TestClient(create_app(settings,retrieval_service=retrieval,test_mode=True)) as client:
        result=client.post("/api/indexes/build",json={"corpus_version":"fixture-en-v2"})
        assert result.status_code==202
        import time
        for _ in range(100):
            task=client.get("/api/tasks/"+result.json()["task_id"]).json()
            if task["state"] in {"completed","failed"}:
                break
            time.sleep(0.01)
        assert task["state"]=="completed" and task["result_id"]=="fixture-index"
        assert client.get("/api/documents?corpus_version=fixture-en-v2").status_code==200
        assert client.post("/api/search",json=dict(body(),top_k=5)).status_code==422
        valid={key:value for key,value in body().items() if key!="conversation_id"}
        assert client.post("/api/search",json=dict(valid,top_k=5)).status_code==200
