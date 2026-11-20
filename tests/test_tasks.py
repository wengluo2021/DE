import asyncio
from threading import Event
import time

from fastapi import BackgroundTasks
import pytest

from app.db.store import SQLiteStore
from app.qa.errors import QAError
from app.tasks.manager import TaskManager


@pytest.fixture
def store(tmp_path):
    value=SQLiteStore(tmp_path/"state.sqlite3",secret="fixture-task-secret");value.initialize()
    return value


def wait(manager,task_id):
    end=time.monotonic()+3
    while time.monotonic()<end:
        result=manager.get(task_id)
        if result["state"] in {"completed","failed"}:
            return result
        time.sleep(0.01)
    pytest.fail("Task did not finish")


def test_b_background_signature_and_persistent_result(store):
    manager=TaskManager(store); background=BackgroundTasks()
    try:
        task=manager.submit(lambda:{"index_version":"fixture-index"},background)
        assert task["state"]=="queued" and manager.get(task["task_id"])["state"]=="queued"
        asyncio.run(background())
        result=wait(manager,task["task_id"])
        assert result["result_id"]=="fixture-index" and result["completed"]==result["total"]==1
        assert SQLiteStore(store.path).task(task["task_id"])["state"]=="completed"
    finally:
        manager.close()


def test_equivalent_queued_task_is_rejected(store):
    manager=TaskManager(store); background=BackgroundTasks()
    try:
        task=manager.submit(lambda:None,background)
        with pytest.raises(QAError) as error:
            manager.submit(lambda:None,background)
        assert error.value.status==409 and error.value.code=="TASK_ALREADY_RUNNING"
        asyncio.run(background());wait(manager,task["task_id"])
    finally:
        manager.close()


@pytest.mark.parametrize("failure", [ValueError("fixture-task-secret"),QAError("FIXTURE_FAILURE","fixture-task-secret",502)])
def test_task_failure_is_saved_and_redacted(store,failure):
    manager=TaskManager(store)
    def work():
        raise failure
    try:
        task=manager.submit(work)
        result=wait(manager,task["task_id"])
        assert result["state"]=="failed"
        assert "fixture-task-secret" not in str(result)
    finally:
        manager.close()


def test_nonserializable_result_becomes_failed_instead_of_stuck_running(store):
    manager=TaskManager(store)
    try:
        task=manager.submit(lambda:{"bad":{1,2}})
        assert wait(manager,task["task_id"])["state"]=="failed"
    finally:
        manager.close()


def test_restart_marks_queued_and_running_tasks_interrupted(store):
    queued=store.create_task("fixture","queued")
    running=store.create_task("fixture","running");store.begin_task(running["task_id"])
    assert store.recover_interrupted()["tasks"]==2
    for task in (queued,running):
        assert store.task(task["task_id"])["error"]["code"]=="PROCESS_INTERRUPTED"
    assert store.create_task("fixture","queued")["state"]=="queued"


def test_worker_is_serial_and_progress_is_saved(store):
    manager=TaskManager(store); release=Event(); events=[]
    def first():
        events.append("first-start");release.wait(2);events.append("first-end")
    try:
        one=manager.submit(first,dedupe_key="first")
        two=manager.submit(lambda:events.append("second"),dedupe_key="second")
        time.sleep(0.02)
        assert "second" not in events
        release.set();wait(manager,one["task_id"]);wait(manager,two["task_id"])
        assert events==["first-start","first-end","second"]
    finally:
        release.set();manager.close()


def test_b_public_error_code_is_preserved_in_background_task(store):
    pytest.importorskip("filelock")
    from app.retrieval.errors import RetrievalError
    manager=TaskManager(store)
    def work():
        raise RetrievalError("INDEX_PATH_TOO_LONG","Use a shorter data directory",409)
    try:
        task=manager.submit(work)
        assert wait(manager,task["task_id"])["error"]["code"]=="INDEX_PATH_TOO_LONG"
    finally:
        manager.close()
