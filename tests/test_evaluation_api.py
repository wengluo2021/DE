from copy import deepcopy
import csv
import io
import json
from threading import Event
import time

from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
import pytest

from app.config import load_settings
from app.contracts import AskRequest,EvaluationRunRequest
from app.evaluation.repository import EvaluationAskStore
from app.main import create_app
from app.qa.persistent import PersistentQA
from app.qa.errors import QAError
from app.qa.service import QAService
from tests.support.c_fixtures import document_loader,retrieve
from tests.support.evaluation_fixtures import dataset,EvaluationGenerator


def setup(tmp_path,*,generator=None,gold_loader=dataset,test_mode=True):
    settings=load_settings(environ={},overrides={"data_dir":str(tmp_path/"data"),"gold_version":"fixture-gold-v1",
                              "generation":{"provider":"mock","model":"fixture-model"}})
    generator=generator or EvaluationGenerator()
    qa=QAService(settings,retriever=retrieve,document_loader=document_loader,generator=generator,index_version="c-fixture-index-v1")
    return create_app(settings,qa_service=qa,test_mode=test_mode,gold_loader=gold_loader),generator


def submit(client):
    return client.post("/api/evaluations/run",json={"corpus_version":"fixture-en-v2","gold_version":"fixture-gold-v1"})


def wait(client,task_id):
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        task=client.get("/api/tasks/"+task_id).json()
        if task["state"] in {"completed","failed"}:
            return task
        time.sleep(0.02)
    pytest.fail("Offline evaluation did not finish")


def test_full_120_same_qa_chain_scoring_and_read_only_exports(tmp_path):
    app,generator=setup(tmp_path)
    with TestClient(app) as client:
        response=submit(client)
        assert response.status_code==202
        plan=response.json();run_id=plan["run_id"]
        task=wait(client,plan["task_id"])
        assert task["state"]=="completed" and task["completed"]==task["total"]==120
        assert task["result"]=={"run_id":run_id,"processed":120,"total":120,"errors":0}
        run=client.get("/api/evaluations/"+run_id).json()
        assert len(run["cases"])==len({(r["condition"],r["case_id"]) for r in run["cases"]})==120
        assert len({r["conversation_id"] for r in run["cases"]})==120
        assert len({r["ask_id"] for r in run["cases"]})==120
        assert not run["review_complete"] and not run["finalizable"] and not run["formal_results"] and run["synthetic"]
        assert len(run["paired_cases"])==30 and len(run["paired_cases"][0]["conditions"])==4
        assert client.get("/api/conversations").json()=={"items":[]}
        assert len(generator.messages)==120 and "GOLD_ONLY" not in json.dumps(generator.messages)
        assert all(len(messages)==2 and set(json.loads(messages[1]["content"]))=={"question","evidence"} for messages in generator.messages)
        for condition,summary in run["summary"].items():
            assert summary["hit_at_5_all"]["value"]==1
            assert summary["answer_accuracy"]["pending"]==24
            assert summary["refusal_accuracy"]["pending"]==6
            assert summary["citation_accuracy"]["pending"]==24
            assert summary["tokens"]["total_tokens"]["known_total"]==900
        path=f"/api/evaluations/{run_id}/cases/synthetic-00"
        patch={"reviewer":"synthetic-test-only","answer_grade":"correct",
               "claim_reviews":[{"claim_index":0,"supported":True,"reason":"Synthetic B. is in its cited snapshot"}]}
        assert client.patch(path+"?condition=s400",json=patch).status_code==200
        after=client.get("/api/evaluations/"+run_id).json()
        assert after["summary"]["s400"]["answer_accuracy"]["pending"]==23
        assert after["summary"]["f400"]["answer_accuracy"]["pending"]==24
        assert client.patch(path+"?condition=s400",json={"reviewer":"synthetic-test-only","notes":"Revision"}).status_code==200
        assert client.patch(path+"?condition=invalid",json=patch).status_code==422
        assert client.patch(path+"?condition=s400",json=dict(patch,hit_at_5_all=True)).status_code==422
        assert client.patch(path+"?condition=s400",json=dict(patch,refusal_correct=True)).status_code==422
        for row in run["cases"]:
            grade=patch if row["gold"]["answerable"] else {"reviewer":"synthetic-test-only","refusal_correct":True}
            assert client.patch(f'/api/evaluations/{run_id}/cases/{row["case_id"]}?condition={row["condition"]}',json=grade).status_code==200
        final=client.get("/api/evaluations/"+run_id).json()
        assert final["review_complete"] and final["finalizable"] and not final["formal_results"]
        assert len(final["review_history"])==122
        assert all(s["answer_accuracy"]["value"]==s["refusal_accuracy"]["value"]==s["citation_accuracy"]["value"]==1 for s in final["summary"].values())
        saved=client.get(f"/api/evaluations/{run_id}/export?format=json")
        assert saved.json()==final and saved.status_code==200
        exported=list(csv.DictReader(io.StringIO(client.get(f"/api/evaluations/{run_id}/export?format=csv").text)))
        assert len(exported)==120 and len(generator.messages)==120
        first=final["cases"][0];csv_first=exported[0]
        assert json.loads(csv_first["result"])==first["result"] and json.loads(csv_first["gold"])==first["gold"]
        assert json.loads(csv_first["trace"])==first["trace"]
        assert json.loads(csv_first["configuration"])==final["config"]
        assert client.get(f"/api/evaluations/{run_id}/export?format=xlsx").status_code==422
        assert client.get("/api/evaluations").json()["items"][0]["run_id"]==run_id
    with TestClient(create_app(app.state.runtime.settings)) as reopened:
        history=reopened.get("/api/evaluations/"+run_id).json()
        assert history["review_complete"] and len(history["review_history"])==122


def test_technical_failures_keep_all_120_rows_evidence_and_fixed_denominators(tmp_path):
    app,generator=setup(tmp_path,generator=EvaluationGenerator(failure="synthetic-answer-00"))
    with TestClient(app) as client:
        plan=submit(client).json();task=wait(client,plan["task_id"])
        assert task["result"]["errors"]==4 and task["state"]=="completed"
        run=client.get("/api/evaluations/"+plan["run_id"]).json()
        failures=[r for r in run["cases"] if r["state"]=="error"]
        assert len(run["cases"])==120 and len(failures)==4
        for row in failures:
            assert row["error"]["code"]=="SYNTHETIC_FAILURE" and row["result"] is None
            assert row["trace"]["sources_verified"] and row["metrics"]["hit_at_5"]["all"]
            assert client.patch(f'/api/evaluations/{plan["run_id"]}/cases/{row["case_id"]}?condition={row["condition"]}',json={"reviewer":"test","answer_grade":"correct"}).status_code==409
        assert all(s["errors"]==1 and s["answer_accuracy"]["denominator"]==24 and s["answer_accuracy"]["pending"]==23 for s in run["summary"].values())
        assert len(list(csv.DictReader(io.StringIO(client.get(f'/api/evaluations/{plan["run_id"]}/export?format=csv').text))))==120


def test_active_evaluation_blocks_duplicate_build_and_interactive_ask(tmp_path):
    gate=Event();app,generator=setup(tmp_path,generator=EvaluationGenerator(gate=gate))
    with TestClient(app) as client:
        try:
            plan=submit(client).json()
            assert submit(client).status_code==409
            body={"question":"interactive","condition":"s400","corpus_version":"fixture-en-v2"}
            assert client.post("/api/ask",json=body).json()["code"]=="EVALUATION_ACTIVE"
            # B's build router resolves retrieval before submitting; exercise the shared admission boundary directly.
            from app.runtime import TaskProxy
            with pytest.raises(QAError,match="Wait for the evaluation"):
                TaskProxy(app.state.runtime).submit(lambda:None,BackgroundTasks())
            assert client.get("/api/conversations").json()["items"]==[]
        finally:
            gate.set()
        assert wait(client,plan["task_id"])["state"]=="completed"


@pytest.mark.parametrize("problem",["version","injected_without_test","missing_gold","bad_count","source","unpinned_index","config"])
def test_preflight_fails_before_any_generation_or_partial_plan(tmp_path,problem):
    def gold():
        value=dataset()
        if problem=="bad_count":value.cases.pop()
        if problem=="source":value.cases[0].evidence[0].text="C."
        return value
    app,generator=setup(tmp_path,gold_loader=None if problem=="missing_gold" else gold,test_mode=problem!="injected_without_test")
    if problem=="unpinned_index":app.state.runtime.injected_qa.index_version=None
    if problem=="config":
        app.state.runtime.injected_qa.settings=load_settings(environ={},overrides={"gold_version":"different"})
    with TestClient(app) as client:
        body={"corpus_version":"wrong" if problem=="version" else "fixture-en-v2","gold_version":"fixture-gold-v1"}
        response=client.post("/api/evaluations/run",json=body)
        assert response.status_code==409
        assert client.get("/api/evaluations").json()["items"]==[] and generator.messages==[]


def test_restart_keeps_completed_case_and_marks_remaining_interrupted(tmp_path):
    app,generator=setup(tmp_path);runtime=app.state.runtime
    runtime.open()
    try:
        plan=runtime.evaluations.create(runtime.settings,dataset(),"c-fixture-index-v1")
        runtime.store.begin_task(plan["task_id"]);runtime.evaluations.start_run(plan["run_id"])
        case=dataset().cases[0];condition="f400"
        qa=PersistentQA(EvaluationAskStore(runtime.evaluations,plan["run_id"],condition,case.case_id),runtime.get_qa_service,settings=runtime.settings)
        result=qa.ask(AskRequest(question=case.question,condition=condition,corpus_version="fixture-en-v2"))
        next_case=dataset().cases[1]
        ask_id,conversation=runtime.evaluations.begin_case(plan["run_id"],condition,next_case.case_id,AskRequest(question=next_case.question,condition=condition,corpus_version="fixture-en-v2"))
        trace={"ask_id":ask_id,"conversation_id":conversation,"question":next_case.question,"condition":condition,
               "corpus_version":"fixture-en-v2","retrieval":retrieve(question=next_case.question,condition=condition,corpus_version="fixture-en-v2"),"sources_verified":True}
        runtime.evaluations.progress(plan["run_id"],condition,next_case.case_id,trace)
        altered=deepcopy(trace);altered["retrieval"]["hits"][0]["text"]="different"
        with pytest.raises(QAError) as error:runtime.evaluations.progress(plan["run_id"],condition,next_case.case_id,altered)
        assert error.value.code=="EVIDENCE_CONFLICT"
    finally:
        runtime.close()
    with TestClient(create_app(runtime.settings)) as client:
        run=client.get("/api/evaluations/"+plan["run_id"]).json()
        assert run["state"]=="failed" and len(run["cases"])==120
        assert run["cases"][0]["result"]["ask_id"]==result.ask_id
        assert run["cases"][1]["trace"]==trace and run["cases"][1]["metrics"]["hit_at_5"]["all"]
        assert sum(r["state"]=="error" for r in run["cases"])==119
        assert client.get("/api/tasks/"+plan["task_id"]).json()["error"]["code"]=="PROCESS_INTERRUPTED"
        assert not run["finalizable"]


def test_background_index_task_prevents_evaluation_and_unknown_resources_are_404(tmp_path):
    app,generator=setup(tmp_path)
    with TestClient(app) as client:
        runtime=app.state.runtime
        runtime.store.create_task("indexes","deliberately-queued")
        assert submit(client).status_code==409 and generator.messages==[]
        assert client.get("/api/evaluations/missing").status_code==404
        assert client.patch("/api/evaluations/missing/cases/missing?condition=s400",json={"reviewer":"test"}).status_code==404
