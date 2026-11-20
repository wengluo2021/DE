from copy import deepcopy
import hashlib
import json

import pytest

from app.config import ROOT,load_settings
from app.data import load_corpus
from app.data.corpus import canonical_hash,frozen_path
from app.data.validation import validate_bundle
from app.qa.errors import QAError
from scripts.prepare_config import prepare_config
from scripts.validate_data import main as validate_main
from tests.support.integration_fixtures import write_bundle


def settings_for(path,bundle,**extra):
    return load_settings(environ={},overrides={"data_dir":str(path),"corpus_version":bundle["corpus_version"],
                         "gold_version":bundle["gold_version"],**extra})


def test_frozen_bundle_validates_and_agrees_with_b_loader(tmp_path):
    bundle=write_bundle(tmp_path,omit_optional=True)
    from app.retrieval.types import formal_loader
    documents=load_corpus(tmp_path,bundle["corpus_version"],formal=True)
    assert documents==formal_loader(tmp_path)(bundle["corpus_version"])==bundle["documents"]
    assert "chapter" not in documents[0]["articles"][0]
    report=validate_bundle(settings_for(tmp_path,bundle,mode="formal"))
    assert report["document_count"]==5 and report["answerable_count"]==24 and report["unanswerable_count"]==6
    assert report["external_model_calls"]==0


@pytest.mark.parametrize("kind",["raw","processed","structure","version","duplicate","schema","bom","crlf","duplicate_key","document_contract"])
def test_frozen_corruption_is_rejected_without_modifying_input(tmp_path,kind):
    bundle=write_bundle(tmp_path)
    manifest=bundle["manifest"]
    if kind in {"raw","processed"}:
        path=tmp_path/("raw/synthetic-0.txt" if kind=="raw" else "processed/synthetic-0.json")
        path.write_bytes(path.read_bytes()+b" ")
    if kind=="structure":manifest["documents"][0]["structure_sha256"]="0"*64
    if kind=="version":manifest["corpus_version"]="0"*64
    if kind=="duplicate":manifest["documents"][1]["document_id"]=manifest["documents"][0]["document_id"]
    if kind=="schema":manifest["schema_version"]="2.0"
    if kind=="document_contract":
        doc=bundle["documents"][0];doc["articles"][0]["end"]=999
        path=tmp_path/"processed/synthetic-0.json"
        path.write_text(json.dumps(doc),encoding="utf-8")
        manifest["documents"][0]["processed_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
    raw=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()
    if kind=="bom":raw=b"\xef\xbb\xbf"+raw
    if kind=="crlf":raw=raw.replace(b"\n",b"\r\n")
    if kind=="duplicate_key":raw=raw.replace(b'"schema_version": "1.0"',b'"schema_version":"2.0","schema_version":"1.0"')
    (tmp_path/"manifest.json").write_bytes(raw)
    before={p:p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(QAError) as error:load_corpus(tmp_path,bundle["corpus_version"])
    assert error.value.code=="INVALID_CORPUS_DATA"
    assert all(path.read_bytes()==value for path,value in before.items())


@pytest.mark.parametrize("path",["../outside","/etc/passwd","C:/private.txt","C:private.txt","\\\\server\\share\\data","data\\raw\\file.txt","data/raw/../../secret"])
def test_snapshot_paths_are_portable_and_contained(tmp_path,path):
    with pytest.raises(ValueError):frozen_path(tmp_path,path)


def test_missing_corpus_and_formal_document_count_are_explicit(tmp_path):
    with pytest.raises(QAError) as error:load_corpus(tmp_path,"a"*64)
    assert error.value.code=="CORPUS_NOT_CONFIGURED"
    bundle=write_bundle(tmp_path,count=1)
    assert len(load_corpus(tmp_path,bundle["corpus_version"]))==1
    with pytest.raises(QAError):load_corpus(tmp_path,bundle["corpus_version"],formal=True)


def test_prepare_config_validates_then_writes_new_keyless_file(tmp_path,monkeypatch):
    # This test selects its frozen temporary corpus. Container runtime defaults
    # must not replace it; production process-env > JSON priority stays intact.
    monkeypatch.delenv("DERAG_DATA_DIR",raising=False)
    source=tmp_path/"SYNTHETIC";bundle=write_bundle(source)
    target=tmp_path/"formal-contract-test.json"
    base_before=(ROOT/"config/experiment.json").read_bytes()
    report=prepare_config(source,target,transport="curl")
    settings=load_settings(target,environ={})
    assert settings.experiment.mode=="formal" and settings.experiment.generation.transport=="curl"
    assert settings.experiment.corpus_version==bundle["corpus_version"] and settings.experiment.gold_version==bundle["gold_version"]
    assert not settings.api_key() and "api_key" not in target.read_text(encoding="utf-8")
    assert base_before==(ROOT/"config/experiment.json").read_bytes() and report["external_model_calls"]==0
    with pytest.raises(QAError) as error:prepare_config(source,target)
    assert error.value.code=="OUTPUT_EXISTS"
    assert validate_main(["--config",str(target)])==0


def test_prepare_config_never_writes_partial_plan_for_missing_or_invalid_gold(tmp_path):
    source=tmp_path/"SYNTHETIC";bundle=write_bundle(source)
    target=tmp_path/"must-not-exist.json"
    (source/"eval/gold.jsonl").write_bytes(b"{}\n")
    with pytest.raises(QAError):prepare_config(source,target)
    assert not target.exists()
    with pytest.raises(QAError):prepare_config(tmp_path/"missing",target)
    assert not target.exists()


def test_validate_cli_returns_failure_without_contacting_model(tmp_path,capsys):
    assert validate_main(["--data-dir",str(tmp_path)])==1
    error=json.loads(capsys.readouterr().err)
    assert error["external_model_calls"]==0 and error["error"]["code"]=="CORPUS_NOT_CONFIGURED"
