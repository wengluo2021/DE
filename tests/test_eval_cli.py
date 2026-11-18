import json

import httpx
import pytest

from app.config import load_settings
from app.qa.errors import QAError
from scripts.run_eval import run_eval


def exercise(tmp_path,*,problem=None,existing=False):
    settings=load_settings(environ={},overrides={"gold_version":"fixture-gold-v1"})
    seen=[]
    run={"run_id":"eval-synthetic","task_id":"task-synthetic","state":"completed","synthetic":True,
         "review_complete":False,"corpus_version":"fixture-en-v2","gold_version":"fixture-gold-v1",
         "config":{"experiment_fingerprint":settings.experiment_fingerprint()}}
    def handle(request):
        seen.append((request.method,request.url.path))
        path=request.url.path
        if path=="/api/health":
            return httpx.Response(200,json={"ready":problem!="notready","experiment_fingerprint":"wrong" if problem=="config" else settings.experiment_fingerprint()})
        if path=="/api/evaluations/run":
            assert json.loads(request.content)=={"corpus_version":"fixture-en-v2","gold_version":"fixture-gold-v1"}
            return httpx.Response(202,json={"run_id":"eval-synthetic","task_id":"task-synthetic"})
        if path.startswith("/api/tasks/"):
            return httpx.Response(200,json={"state":"running" if problem=="timeout" else "failed" if problem=="failed" else "completed"})
        if path.endswith("/export"):
            content=json.dumps(run) if request.url.params["format"]=="json" else "case_id,condition\nsynthetic,f400\n"
            return httpx.Response(200,content=content.encode())
        if path=="/api/evaluations/eval-synthetic":
            return httpx.Response(200,json=dict(run,state="failed") if problem=="failed" else run)
        pytest.fail("Unexpected endpoint")
    output=tmp_path/"exports"
    if problem=="output":output.mkdir()
    client=httpx.Client(base_url="http://testserver",transport=httpx.MockTransport(handle))
    return settings,client,output,seen


def test_cli_submits_only_http_polls_and_exports_without_local_runner(tmp_path):
    settings,client,output,seen=exercise(tmp_path)
    with client:
        result=run_eval(settings,client,output)
    assert result["run_id"]=="eval-synthetic" and (output/"evaluation.json").exists() and (output/"evaluation.csv").exists()
    assert seen.count(("POST","/api/evaluations/run"))==1
    assert all(path.startswith("/api/") for _,path in seen)


@pytest.mark.parametrize("problem",["config","notready","output"])
def test_cli_preflight_mismatch_never_submits(tmp_path,problem):
    settings,client,output,seen=exercise(tmp_path,problem=problem)
    with client,pytest.raises(QAError):run_eval(settings,client,output)
    assert not any(method=="POST" for method,path in seen)


def test_cli_resumes_existing_run_even_when_generation_not_ready(tmp_path):
    settings,client,output,seen=exercise(tmp_path,problem="notready")
    with client:result=run_eval(settings,client,output,run_id="eval-synthetic")
    assert result["state"]=="completed" and not any(method=="POST" for method,path in seen)


def test_cli_timeout_records_run_id_and_does_not_restart(tmp_path):
    settings,client,output,seen=exercise(tmp_path,problem="timeout")
    times=iter([0,2])
    with client,pytest.raises(QAError) as error:
        run_eval(settings,client,output,timeout=1,monotonic=lambda:next(times))
    assert error.value.code=="EVALUATION_WAIT_TIMEOUT" and "eval-synthetic" in error.value.message
    assert not output.exists() and seen.count(("POST","/api/evaluations/run"))==1


def test_cli_failed_task_still_exports_saved_failures(tmp_path):
    settings,client,output,seen=exercise(tmp_path,problem="failed")
    with client:result=run_eval(settings,client,output)
    assert result["state"]=="failed" and (output/"evaluation.json").exists()
