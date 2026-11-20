import json

import pytest

from scripts.ask import main


def test_mock_cli_uses_shared_service_and_explicit_synthetic_marker(capsys):
    assert main(["--fixtures", "--mock-llm", "--question", "What does Article 2 state?"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["mock_llm"] and data["synthetic_evidence"]
    assert data["result"]["generation"]["provider"] == "mock"
    assert data["result"]["answer"] == "Article 2 states B.[1]"


def test_cli_does_not_overwrite_existing_evidence(tmp_path, capsys):
    output = tmp_path / "keep.json"; output.write_text("existing record")
    assert main(["--fixtures", "--mock-llm", "--question", "q", "--output", str(output)]) == 1
    assert output.read_text() == "existing record"
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "OUTPUT_EXISTS"


def test_cli_writes_a_complete_new_record(tmp_path, capsys):
    output = tmp_path / "result.json"
    assert main(["--fixtures", "--mock-llm", "--question", "q", "--output", str(output)]) == 0
    capsys.readouterr()
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert len(saved["trace"]["attempts"]) == 1
    assert len(saved["result"]["citations"]) == 1
    assert b"\r\n" not in output.read_bytes()


@pytest.mark.parametrize("condition", ["f400", "s400", "f800", "s800"])
def test_all_conditions_use_the_same_pipeline(condition, capsys):
    assert main(["--fixtures", "--mock-llm", "--condition", condition, "--question", "q"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["result"]["condition"] == condition
    assert data["result"]["citations"][0]["condition"] == condition
