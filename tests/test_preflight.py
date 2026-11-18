import json

import pytest

from app.config import ROOT,load_settings
from app.integration import check_dependencies,integration_status
from scripts.preflight import main


def test_unified_runtime_matches_installed_versions():
    assert check_dependencies()=={"ready":True,"missing":[],"mismatched":[]}


def test_dependency_checker_distinguishes_missing_and_wrong_version(tmp_path):
    path=tmp_path/"requirements.txt"
    path.write_text("pydantic==0.0.0\nSYNTHETIC-not-a-real-package==1.0\n",encoding="utf-8")
    status=check_dependencies(path)
    assert not status["ready"] and status["missing"]==["SYNTHETIC-not-a-real-package"]
    assert status["mismatched"][0]["package"]=="pydantic"


def test_preflight_no_data_is_not_ready_and_never_generates(tmp_path,monkeypatch):
    from app.retrieval.embedding import LocalEmbedder
    from app.qa.client import ChatCompletionsClient
    monkeypatch.setattr(LocalEmbedder,"identity",lambda self:{"model_id":"synthetic","revision":"a"*40,"dimension":1024,"files":{"synthetic":"b"*64}})
    def forbidden(*args,**kwargs):pytest.fail("Preflight must never generate or encode")
    monkeypatch.setattr(ChatCompletionsClient,"generate",forbidden)
    monkeypatch.setattr(LocalEmbedder,"encode",forbidden)
    settings=load_settings(environ={},overrides={"data_dir":str(tmp_path)})
    status=integration_status(settings)
    assert not status["ready_for_qa"] and not status["ready_for_evaluation"] and not status["formal_ready"]
    assert status["components"]["model_files"]["ready"] and not status["components"]["model_files"]["encoder_loaded"]
    assert status["components"]["corpus"]["code"]=="CORPUS_NOT_CONFIGURED"
    assert status["external_model_calls"]==status["index_builds"]==0


def test_preflight_preserves_existing_report(tmp_path,capsys):
    target=tmp_path/"report.json";target.write_text("original",encoding="utf-8")
    assert main(["--output",str(target)])==1
    assert "OUTPUT_EXISTS" in capsys.readouterr().err and target.read_text()=="original"


def test_foreign_exception_method_code_is_not_serialized():
    from app.integration import _issue
    class NativeError(Exception):
        def code(self):return "native"
    issue=_issue(NativeError(),"MODEL_CHECK_FAILED")
    assert issue["code"]=="MODEL_CHECK_FAILED"
    json.dumps(issue)
