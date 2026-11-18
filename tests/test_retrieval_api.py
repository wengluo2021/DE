from app.retrieval.types import FIXTURE_CORPUS_VERSION
import pytest
from fastapi.testclient import TestClient

from app.retrieval import RetrievalError
from tests.test_retrieval import service_at
from tests.support.b_app import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(service_at(tmp_path))) as client:
        yield client


def build(client):
    response = client.post("/api/indexes/build", json={"corpus_version": FIXTURE_CORPUS_VERSION})
    assert response.status_code == 202
    assert response.json()["state"] == "queued"
    task = client.get("/api/tasks/" + response.json()["task_id"]).json()
    assert task["state"] == "completed", task
    return task["result"]


def test_full_api_contract_and_debug_frontend(client):
    assert client.get("/b-debug").status_code == 200
    assert "textContent" in client.get("/b-debug").text
    assert not client.get("/b-debug/status").json()["ready"]
    docs = client.get("/api/documents", params={"corpus_version": FIXTURE_CORPUS_VERSION}).json()["items"]
    assert len(docs) == 4
    assert set(docs[0]) == {"document_id", "title", "source_url", "corpus_version", "article_count", "char_count"}
    assert client.get(f"/api/documents/fixture/chunks?corpus_version={FIXTURE_CORPUS_VERSION}").status_code == 409
    manifest = build(client)
    assert client.get("/b-debug/status").json()["ready"]
    response = client.get(f"/api/documents/fixture/chunks?corpus_version={FIXTURE_CORPUS_VERSION}&condition=s400")
    assert response.json()["items"][0]["start"] == 0
    body = {"question": "personal information deletion", "corpus_version": FIXTURE_CORPUS_VERSION, "condition": "s400", "top_k": 5}
    response = client.post("/api/search", json=body)
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"corpus_version", "index_version", "condition", "hits", "timing_ms"}
    assert data["index_version"] == manifest["index_version"]
    for hit in data["hits"]:
        doc = client.get(f"/api/documents/{hit['document_id']}?corpus_version={FIXTURE_CORPUS_VERSION}").json()
        assert doc["text"][hit["start"]:hit["end"]] == hit["text"]
    compare = client.post("/api/compare", json={"question": body["question"], "corpus_version": FIXTURE_CORPUS_VERSION,
                                               "left_condition": "f400", "right_condition": "s400"}).json()
    assert compare["index_version"] == data["index_version"]
    assert compare["left"]["hits"] and compare["right"]["hits"]


@pytest.mark.parametrize("change", [{"question": ""}, {"question": " \n"}, {"condition": "bad"},
                                    {"top_k": 0}, {"top_k": 6}, {"top_k": True}, {"top_k": "5"}, {"extra": 1}])
def test_uniform_validation_errors(client, change):
    body = {"question": "test", "corpus_version": FIXTURE_CORPUS_VERSION, "condition": "s400", "top_k": 5} | change
    response = client.post("/api/search", json=body)
    assert response.status_code == 422
    assert set(response.json()) == {"code", "message"}
    assert response.json()["code"] == "INVALID_REQUEST"


def test_missing_objects_versions_and_not_ready(client):
    assert client.get("/api/tasks/missing").status_code == 404
    assert client.get(f"/api/documents/missing?corpus_version={FIXTURE_CORPUS_VERSION}").status_code == 404
    assert client.get("/api/documents?corpus_version=wrong").status_code == 409
    assert client.get("/api/documents").json()["code"] == "INVALID_REQUEST"
    response = client.post("/api/search", json={"question": "test", "condition": "s400", "corpus_version": FIXTURE_CORPUS_VERSION})
    assert response.status_code == 409
    assert response.json()["code"] == "INDEX_NOT_READY"


def test_right_side_error_cannot_be_replaced_with_left_results(client):
    build(client)
    service = client.app.state.service
    original = service.indexes.store
    store = original(next(iter(service.indexes._stores)))
    query = store.query
    def fail_right(condition, vector, top_k):
        if condition == "s400":
            raise RetrievalError("INDEX_NOT_READY", "injected right failure")
        return query(condition, vector, top_k)
    store.query = fail_right
    response = client.post("/api/compare", json={"question": "test", "corpus_version": FIXTURE_CORPUS_VERSION,
                                                "left_condition": "f400", "right_condition": "s400"})
    assert response.status_code == 409
    assert response.json() == {"code": "INDEX_NOT_READY", "message": "injected right failure"}


def test_failed_task_has_explicit_error(client):
    response = client.post("/api/indexes/build", json={"corpus_version": "wrong"})
    task = client.get("/api/tasks/" + response.json()["task_id"]).json()
    assert task["state"] == "failed"
    assert task["error"]["code"] == "VERSION_MISMATCH"
