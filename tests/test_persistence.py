import json
import sqlite3

import pytest

from app.config import load_settings
from app.contracts import AskRequest
from app.db.lease import ProcessLease
from app.db.store import SQLiteStore
from app.qa.errors import QAError
from app.qa.persistent import PersistentQA
from app.qa.service import QAService
from tests.support.c_fixtures import FixtureGenerator,document_loader,retrieve


@pytest.fixture
def components(tmp_path):
    settings=load_settings(environ={},api_key="fixture-persist-secret",overrides={
        "data_dir":str(tmp_path/"data"),"generation":{"provider":"mock","model":"fixture-model"}})
    store=SQLiteStore(tmp_path/"db/derag.sqlite3",secret=settings.api_key()); store.initialize()
    service=QAService(settings,retriever=retrieve,document_loader=document_loader,generator=FixtureGenerator())
    controller=PersistentQA(store,lambda:service,settings=settings)
    return settings,store,service,controller


def request(conversation=None,question="What does Article 2 state?"):
    return AskRequest(question=question,condition="s400",corpus_version="fixture-en-v2",conversation_id=conversation)


def test_history_and_full_evidence_survive_new_store_and_index_changes(components):
    settings,store,service,controller=components
    first=controller.ask(request())
    second=controller.ask(request(first.conversation_id))
    reopened=SQLiteStore(store.path)
    history=reopened.conversation(first.conversation_id)
    assert len(history["asks"])==2
    assert [a["result"]["citations"][0]["n"] for a in history["asks"]]==[1,1]
    assert history["asks"][0]["id"]!=history["asks"][1]["id"]
    assert history["asks"][0]["evidence"][0]["source_verified"] is True
    service.retriever=lambda **kwargs: (_ for _ in ()).throw(AssertionError("History must not re-search"))
    assert reopened.conversation(first.conversation_id)["asks"][0]["result"]["answer"]==first.answer
    assert len(reopened.conversations())==1


def test_unknown_conversation_does_not_create_a_new_one(components):
    _,store,_,controller=components
    with pytest.raises(QAError) as error:
        controller.ask(request("unknown"))
    assert error.value.status==404 and store.conversations()==[]


def test_generation_error_and_verified_evidence_are_saved(components):
    _,store,service,controller=components
    class Failure:
        def generate(self,messages):
            raise QAError("LLM_AUTH_ERROR","fixture-persist-secret rejected",503)
    service.generator=Failure()
    with pytest.raises(QAError):
        controller.ask(request())
    history=store.conversation(store.conversations()[0]["id"])
    run=history["asks"][0]
    assert run["state"]=="failed" and run["result"] is None
    assert run["error"]["code"]=="LLM_AUTH_ERROR"
    assert run["evidence"][0]["source_verified"] is True
    assert len(run["trace"]["attempts"])==1
    assert "fixture-persist-secret" not in json.dumps(history)


def test_unavailable_retrieval_is_a_saved_failed_ask(components):
    settings,store,_,_=components
    def unavailable():
        raise QAError("INDEX_NOT_READY","Build indexes",409)
    controller=PersistentQA(store,unavailable,settings=settings)
    with pytest.raises(QAError) as error:
        controller.ask(request())
    assert error.value.status==409
    saved=store.conversation(store.conversations()[0]["id"])["asks"][0]
    assert saved["state"]=="failed"
    assert saved["trace"]["configuration"]["generation"]["prompt_sha256"]==settings.prompt_sha256
    assert saved["trace"]["experiment_fingerprint"]==settings.experiment_fingerprint()


def test_process_interruption_keeps_already_saved_evidence(components):
    _,store,service,controller=components
    class SimulatedProcessStop(BaseException):
        pass
    class Stop:
        def generate(self,messages):
            raise SimulatedProcessStop()
    service.generator=Stop()
    with pytest.raises(SimulatedProcessStop):
        controller.ask(request())
    history=store.conversation(store.conversations()[0]["id"])
    assert history["asks"][0]["state"]=="running"
    assert len(history["asks"][0]["evidence"])==1
    reopened=SQLiteStore(store.path)
    assert reopened.recover_interrupted()["asks"]==1
    run=reopened.conversation(history["id"])["asks"][0]
    assert run["state"]=="failed" and run["error"]["code"]=="PROCESS_INTERRUPTED"
    assert len(run["evidence"])==1


def test_result_and_new_evidence_are_in_one_transaction(components):
    _,store,service,_=components
    req=request(); ask_id,conversation=store.start_ask(req)
    result,trace=service.ask_with_trace(req.question,req.condition,req.corpus_version,conversation,ask_id=ask_id)
    with sqlite3.connect(store.path) as db:
        db.executescript("""CREATE TRIGGER reject_success BEFORE UPDATE OF state ON asks
            WHEN NEW.state='answered' BEGIN SELECT RAISE(ABORT,'fixture failure'); END;""")
    with pytest.raises(sqlite3.IntegrityError):
        store.finish_ask(result,trace.to_dict())
    run=store.conversation(conversation)["asks"][0]
    assert run["state"]=="running" and run["evidence"]==[] and run["result"] is None


def test_completed_snapshot_cannot_be_changed(components):
    _,store,_,controller=components
    result=controller.ask(request())
    with pytest.raises(QAError) as error:
        store.save_progress(result.ask_id,{"retrieval":{"hits":[]}})
    assert error.value.code=="ASK_NOT_RUNNING"


def test_question_and_diagnostics_are_redacted_in_database(components):
    _,store,_,controller=components
    result=controller.ask(request(question="fixture-persist-secret"))
    history=store.conversation(result.conversation_id)
    assert "fixture-persist-secret" not in json.dumps(history)
    assert history["title"]=="[REDACTED]"


def test_single_owner_lease_is_released_for_next_start(tmp_path):
    first,second=ProcessLease(tmp_path/"service.lock"),ProcessLease(tmp_path/"service.lock")
    first.acquire()
    try:
        with pytest.raises(QAError) as error:
            second.acquire()
        assert error.value.code=="SERVICE_ALREADY_RUNNING"
    finally:
        first.release()
    second.acquire(); second.release()


def test_unknown_schema_is_not_silently_upgraded(tmp_path):
    path=tmp_path/"future.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL); INSERT INTO metadata VALUES('schema_version','future');")
    store=SQLiteStore(path)
    with pytest.raises(QAError) as error:
        store.initialize()
    assert error.value.code=="DATABASE_VERSION_MISMATCH"
    with sqlite3.connect(path) as db:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables=={"metadata"}
