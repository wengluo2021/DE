import json

import pytest

from app.config import ROOT,load_settings


def test_config_selection_transport_and_priority(tmp_path):
    alt=tmp_path/"alternate.json"
    data=json.loads((ROOT/"config/experiment.json").read_text(encoding="utf-8"))
    data["corpus_version"]="synthetic-config-selection";alt.write_text(json.dumps(data),encoding="utf-8")
    env=tmp_path/".env";env.write_text(f"DERAG_CONFIG={alt.as_posix()}\nLLM_TRANSPORT=curl\n",encoding="utf-8")
    selected=load_settings(env_file=env,environ={})
    assert selected.experiment.corpus_version=="synthetic-config-selection"
    assert selected.experiment.generation.transport=="curl"
    process=load_settings(env_file=env,environ={"LLM_TRANSPORT":"httpx"})
    assert process.experiment.generation.transport=="httpx"
    explicit=load_settings(ROOT/"config/experiment.json",env_file=env,environ={},overrides={"generation":{"transport":"httpx"}})
    assert explicit.experiment.corpus_version=="fixture-en-v2" and explicit.experiment.generation.transport=="httpx"
    assert explicit.experiment_fingerprint()!=selected.experiment_fingerprint()


def test_invalid_transport_and_mock_formal_generation_are_rejected():
    with pytest.raises(ValueError):load_settings(environ={"LLM_TRANSPORT":"unsafe"})
    with pytest.raises(ValueError):load_settings(environ={"DERAG_CONFIG":""})
    with pytest.raises(ValueError):
        load_settings(environ={},overrides={"mode":"formal","corpus_version":"a"*64,"gold_version":"b"*64,
                                            "generation":{"provider":"mock"}})
