from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from app.config import ROOT, load_settings


@pytest.fixture
def project(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "app/qa/prompts").mkdir(parents=True)
    (tmp_path / "app/qa/prompts/answer.txt").write_text("Return JSON from evidence.", encoding="utf-8")
    data = json.loads((ROOT / "config/experiment.json").read_text(encoding="utf-8"))
    (tmp_path / "config/experiment.json").write_text(json.dumps(data), encoding="utf-8")
    return tmp_path, data


def test_missing_key_is_unconfigured_and_cwd_does_not_change_paths(project, monkeypatch):
    root, _ = project
    monkeypatch.chdir(root / "config")
    settings = load_settings(project_root=root, environ={})
    assert not settings.llm_configured
    assert settings.experiment.data_dir == root / "data"
    assert settings.experiment.embedding.model_dir == root / "models/embedding"


def test_precedence_without_global_mutation(project, monkeypatch):
    root, _ = project
    (root / ".env").write_text("LLM_MODEL=dotenv\nLLM_API_KEY=fixture-dotenv-key\n", encoding="utf-8")
    monkeypatch.setenv("LLM_MODEL", "actual-process")
    before = dict(os.environ)
    assert load_settings(project_root=root, environ={}).experiment.generation.model == "dotenv"
    env = {"LLM_MODEL": "process", "LLM_API_KEY": "fixture-env-key"}
    settings = load_settings(project_root=root, environ=env, overrides={"generation": {"model": "explicit"}})
    assert settings.experiment.generation.model == "explicit"
    assert settings.api_key() == "fixture-env-key"
    assert dict(os.environ) == before
    assert env["LLM_MODEL"] == "process"


def test_explicit_empty_key_clears_old_key(project):
    root, _ = project
    settings = load_settings(project_root=root, environ={"LLM_API_KEY": "fixture-old"}, api_key="")
    assert not settings.llm_configured
    assert settings.api_key() == ""


def test_secrets_are_not_in_repr_snapshot_or_fingerprint(project):
    root, _ = project
    key = "fixture-secret-never-public"
    settings = load_settings(project_root=root, environ={}, api_key=key)
    assert key not in repr(settings)
    assert key not in json.dumps(settings.public_snapshot())
    other = load_settings(project_root=root, environ={}, api_key="different-fixture")
    missing = load_settings(project_root=root, environ={})
    assert settings.experiment_fingerprint() == other.experiment_fingerprint() == missing.experiment_fingerprint()


def test_fingerprint_ignores_machine_paths_but_includes_prompt(project):
    root, _ = project
    first = load_settings(project_root=root, environ={})
    moved = load_settings(project_root=root, environ={"DERAG_DATA_DIR": "elsewhere", "DERAG_MODEL_DIR": "weights"})
    assert first.experiment_fingerprint() == moved.experiment_fingerprint()
    (root / "app/qa/prompts/answer.txt").write_text("A changed prompt", encoding="utf-8")
    assert first.experiment_fingerprint() != load_settings(project_root=root, environ={}).experiment_fingerprint()


@pytest.mark.parametrize("override", [
    {"top_k": 3}, {"top_k": True}, {"top_k": 5.0}, {"conditions": ["f400", "s400"]},
    {"embedding": {"revision": "main"}}, {"generation": {"temperature": True}},
    {"generation": {"temperature": float("nan")}}, {"generation": {"max_attempts": 3}},
    {"generation": {"max_tokens": True}}, {"generation": {"timeout_seconds": 0}},
    {"generation": {"base_url": "https://user:fixture-credential@example.org/v1"}},
    {"generation": {"base_url": "https://llm.cs.cityu.edu.hk:99999/v1"}},
    {"generation": {"base_url": "https://llm.cs.cityu.edu.hk:not-a-port/v1"}},
    {"generation": {"base_url": "https://llm.cs.cityu.edu.hk/v1\n"}},
    {"generation": {"base_url": "https://llm.cs.cityu.edu.hk/\tv1"}},
    {"generation": {"json_mode": "false"}}, {"embedding": {"normalize": "true"}},
])
def test_bad_experiment_parameters_are_rejected(project, override):
    root, _ = project
    with pytest.raises(ValueError):
        load_settings(project_root=root, environ={}, overrides=override)


def test_error_does_not_echo_unknown_sensitive_config_field(project):
    root, _ = project
    with pytest.raises(ValueError) as error:
        load_settings(project_root=root, environ={}, overrides={"generation": {"api_key": "fixture-do-not-echo"}})
    assert "fixture-do-not-echo" not in str(error.value)


def test_formal_requires_real_frozen_versions(project):
    root, _ = project
    with pytest.raises(ValueError):
        load_settings(project_root=root, environ={}, overrides={"mode": "formal"})
    settings = load_settings(project_root=root, environ={}, overrides={
        "mode": "formal", "corpus_version": "a" * 64, "gold_version": "b" * 64})
    assert settings.experiment.mode == "formal"


def test_b_adapter_matches_existing_parameters_and_is_a_fresh_copy(project):
    root, _ = project
    settings = load_settings(project_root=root, environ={})
    expected = json.loads((ROOT / "config/retrieval.example.json").read_text())
    adapted = settings.retrieval_config()
    assert adapted["conditions"] == expected["conditions"]
    assert adapted["embedding"]["revision"] == expected["embedding"]["revision"]
    assert adapted["embedding"]["dimension"] == 1024
    adapted["embedding"]["revision"] = "changed"
    assert settings.retrieval_config()["embedding"]["revision"] == expected["embedding"]["revision"]


def test_empty_path_rejected(project):
    root, _ = project
    with pytest.raises(ValueError, match="paths"):
        load_settings(project_root=root, environ={"DERAG_DATA_DIR": ""})


def test_blank_key_is_unconfigured_and_header_whitespace_is_rejected(project):
    root, _ = project
    assert not load_settings(project_root=root, environ={}, api_key="   ").llm_configured
    with pytest.raises(ValueError, match="whitespace"):
        load_settings(project_root=root, environ={}, api_key="fixture key")


def test_config_import_does_not_load_heavy_retrieval_package():
    code = "import sys; import app.config; assert 'app.retrieval' not in sys.modules; assert 'chromadb' not in sys.modules"
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
