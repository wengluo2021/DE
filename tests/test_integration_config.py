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


def test_process_env_file_is_shared_by_cli_and_app_and_explicit_path_wins(tmp_path):
    process_file=tmp_path/"process.env"
    process_file.write_text('LLM_MODEL=synthetic-process-file\nLLM_API_KEY=synthetic-process-key\nLLM_TRANSPORT=curl\n',encoding="utf-8")
    explicit_file=tmp_path/"explicit.env"
    explicit_file.write_text('LLM_MODEL=synthetic-explicit-file\nLLM_API_KEY=synthetic-explicit-key\n',encoding="utf-8")
    env={"DERAG_ENV_FILE":str(process_file)}
    settings=load_settings(environ=env)
    assert settings.experiment.generation.model=="synthetic-process-file"
    assert settings.api_key()=="synthetic-process-key" and settings.experiment.generation.transport=="curl"
    explicit=load_settings(env_file=explicit_file,environ=env)
    assert explicit.experiment.generation.model=="synthetic-explicit-file"
    assert explicit.api_key()=="synthetic-explicit-key"
    overridden=load_settings(environ=dict(env,LLM_MODEL="synthetic-process-override"))
    assert overridden.experiment.generation.model=="synthetic-process-override"
