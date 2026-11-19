"""Portable delivery, credential isolation, exact frozen bytes and tamper checks."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from app.config import ROOT,load_settings
from app.qa.errors import QAError
from scripts.prepare_delivery import SOURCE_FILES,prepare_delivery,main
from scripts.verify_delivery import verify_delivery
from tests.support.integration_fixtures import write_bundle


def project(tmp_path,*,mode="development"):
    root=tmp_path/"source"
    for relative in SOURCE_FILES:
        p=root/relative;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes((ROOT/relative).read_bytes())
    for tree in ("app","scripts","tests","docs"):(root/tree).mkdir(exist_ok=True)
    p=root/"app/qa/prompts/answer.txt";p.parent.mkdir(parents=True)
    p.write_bytes((ROOT/"app/qa/prompts/answer.txt").read_bytes())
    (root/"app/public.py").write_bytes(b"# public source\r\n")
    bundle=write_bundle(root/"data")
    config=json.loads((ROOT/"config/experiment.json").read_text(encoding="utf-8"))
    config.update(mode=mode,data_dir="data",corpus_version=bundle["corpus_version"],gold_version=bundle["gold_version"])
    path=root/"config/rehearsal.json";path.write_text(json.dumps(config),encoding="utf-8")
    return root,path,bundle


def test_delivery_preserves_frozen_bytes_fingerprint_and_excludes_private_generated_files(tmp_path,monkeypatch):
    root,config,bundle=project(tmp_path)
    (root/".env").write_text("LLM_API_KEY=SYNTHETIC-SECRET\nLLM_MODEL=wrong-local-model\n",encoding="utf-8")
    for name in ("app/local.env","app/local.env.backup","app/.env.local","app/token.key",
                 "data/sqlite/derag.sqlite3","data/chroma/generated.bin","models/embedding/model.bin"):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text("SYNTHETIC-SECRET",encoding="utf-8")
    monkeypatch.setenv("LLM_API_KEY","SYNTHETIC-SECRET")
    monkeypatch.setenv("LLM_MODEL","wrong-process-model")
    output=tmp_path/"delivery"
    result=prepare_delivery(output,config_path=config,synthetic=True,project_root=root)
    assert result["kind"]=="synthetic_rehearsal" and result["state"]=="verified"
    assert not result["container_built"] and not result["model_weights_included"]
    manifest=json.loads((output/"DELIVERY-MANIFEST.json").read_text(encoding="utf-8"))
    assert not manifest["official_provenance_verified"] and manifest["external_model_calls"]==0
    assert (output/"app/public.py").read_bytes()==(root/"app/public.py").read_bytes()
    for name in ("manifest.json","eval/manifest.json","eval/gold.jsonl","raw/synthetic-0.txt","processed/synthetic-0.json"):
        assert (output/"data"/name).read_bytes()==(root/"data"/name).read_bytes()
    for p in output.rglob('*'):
        if p.is_file():assert b"SYNTHETIC-SECRET" not in p.read_bytes()
    settings=load_settings(config,project_root=root,env_file="missing-explicit-env",environ={})
    staged=load_settings("config/experiment.delivery.json",project_root=output,env_file="missing-explicit-env",environ={})
    assert staged.experiment.data_dir==output/"data"
    assert staged.experiment.embedding.model_dir==output/"models/embedding"
    assert settings.experiment_fingerprint()==staged.experiment_fingerprint()==manifest["experiment_fingerprint"]
    assert staged.experiment.generation.model!="wrong-process-model" and not staged.llm_configured
    assert verify_delivery(output)["file_count"]==len(manifest["files"])
    # -S disables third-party site packages: verification must work before installing dependencies.
    run=subprocess.run([sys.executable,"-S",str(ROOT/"scripts/verify_delivery.py"),str(output)],capture_output=True,text=True,timeout=15)
    assert run.returncode==0,run.stderr
    assert json.loads(run.stdout)["kind"]=="synthetic_rehearsal"


def test_existing_output_is_preserved_and_missing_input_creates_nothing(tmp_path):
    root,config,_=project(tmp_path)
    output=tmp_path/"existing";output.mkdir();(output/"marker").write_text("keep")
    with pytest.raises(QAError) as e:prepare_delivery(output,config_path=config,synthetic=True,project_root=root)
    assert e.value.code=="OUTPUT_EXISTS" and (output/"marker").read_text()=="keep"
    (root/"data/eval/gold.jsonl").unlink()
    with pytest.raises(QAError):prepare_delivery(tmp_path/"missing",config_path=config,synthetic=True,project_root=root)
    assert not (tmp_path/"missing").exists()


@pytest.mark.parametrize("synthetic,mode",[(False,"development"),(True,"formal"),(False,"formal")])
def test_development_and_marked_synthetic_cannot_become_formal_delivery(tmp_path,synthetic,mode):
    root,config,_=project(tmp_path,mode=mode)
    with pytest.raises(QAError) as e:prepare_delivery(tmp_path/"output",config_path=config,synthetic=synthetic,project_root=root)
    assert e.value.code in {"DELIVERY_MODE_MISMATCH","SYNTHETIC_DELIVERY_FORBIDDEN"}
    assert not (tmp_path/"output").exists()


def test_changed_frozen_input_and_output_inside_source_are_rejected_before_writing(tmp_path):
    root,config,_=project(tmp_path)
    with pytest.raises(QAError) as e:prepare_delivery(root/"app/output",config_path=config,synthetic=True,project_root=root)
    assert e.value.code=="INVALID_DELIVERY_PATH"
    (root/"data/raw/synthetic-0.txt").write_text("tampered",encoding="utf-8")
    with pytest.raises(QAError):prepare_delivery(tmp_path/"output",config_path=config,synthetic=True,project_root=root)
    assert not (tmp_path/"output").exists()


@pytest.mark.parametrize("change",["modified","missing","unexpected"])
def test_verifier_rejects_tampered_missing_and_unlisted_files(tmp_path,change):
    root,config,_=project(tmp_path)
    output=tmp_path/"delivery"
    prepare_delivery(output,config_path=config,synthetic=True,project_root=root)
    path=output/"app/public.py"
    if change=="modified":path.write_text("tampered")
    elif change=="missing":path.unlink()
    else:(output/"unexpected.env").write_text("unlisted")
    with pytest.raises(ValueError):verify_delivery(output)


@pytest.mark.parametrize("path",["../escape","/absolute","C:/secret","raw\\x","data/../x","","app//public.py","DELIVERY-MANIFEST.json"])
def test_verifier_rejects_inventory_escape_and_nonportable_paths(tmp_path,path):
    root=tmp_path/"package";root.mkdir()
    manifest={"schema_version":"1.0","kind":"synthetic_rehearsal","corpus_version":"a"*64,
              "gold_version":"b"*64,"experiment_fingerprint":"c"*64,"files":{path:"d"*64}}
    (root/"DELIVERY-MANIFEST.json").write_text(json.dumps(manifest),encoding="utf-8")
    with pytest.raises(ValueError):verify_delivery(root)


def test_prepare_cli_preserves_an_existing_target_without_model_call(tmp_path,capsys):
    output=tmp_path/"keep";output.mkdir()
    assert main(["--output",str(output)])==1
    assert "OUTPUT_EXISTS" in capsys.readouterr().err
