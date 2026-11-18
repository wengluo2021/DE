from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.config import ROOT, load_settings
from app.contracts import INSUFFICIENT_ANSWER
from app.qa.client import GenerationResponse
from app.qa.errors import QAError
from app.qa.service import QAService

FIXTURES = ROOT / "tests/fixtures/b"


def response(content=None, *, finish="stop"):
    text = json.dumps(content or {"status": "answered", "claims": [
        {"text": "Article 2 states B.", "citation_numbers": [1]}]})
    return GenerationResponse(text, "fixture-model", finish, {"prompt_tokens": 3, "completion_tokens": 2},
                              "fixture-response", {"choices": [{"message": {"content": text}}]})


class Generator:
    def __init__(self, *values):
        self.values = list(values or (response(),))
        self.messages = []

    def generate(self, messages):
        self.messages.append(deepcopy(messages))
        value = self.values.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


@pytest.fixture
def setup():
    document = json.loads((FIXTURES / "document.json").read_text(encoding="utf-8"))
    hit = json.loads((FIXTURES / "expected_hits.json").read_text(encoding="utf-8"))["hit"]
    retrieved = {"condition": "s400", "hits": [hit], "timing_ms": 1.5,
                 "corpus_version": "fixture-en-v2", "index_version": "fixture-index-v1"}
    settings = load_settings(environ={}, api_key="fixture-private-key", overrides={"generation": {"provider": "mock"}})
    return settings, document, retrieved


def make_service(setup, generator=None, *, retrieved=None, loader=None, index_version=None):
    settings, document, original = setup
    calls = []
    def retrieve(**kwargs):
        calls.append(kwargs)
        return deepcopy(original if retrieved is None else retrieved)
    service = QAService(settings, retriever=retrieve, document_loader=loader or (lambda version: [deepcopy(document)]),
                        generator=generator or Generator(), index_version=index_version, sleeper=lambda seconds: None)
    return service, calls


def ask(service):
    return service.ask_with_trace("What does Article 2 state?", "s400", "fixture-en-v2")


def test_answer_is_rendered_from_verified_claims_and_preserves_full_snapshot(setup):
    service, calls = make_service(setup)
    result, trace = ask(service)
    assert result.answer == "Article 2 states B.[1]"
    assert result.citations[0].text == setup[1]["text"]
    assert trace.context_chars == 25
    assert trace.attempts[0]["state"] == "completed"
    assert trace.timing_ms["generate"] >= 0
    assert calls == [{"question": "What does Article 2 state?", "condition": "s400",
                      "corpus_version": "fixture-en-v2", "top_k": 5}]


def test_unused_hits_are_also_retained(setup):
    hit1, hit2 = deepcopy(setup[2]["hits"][0]), deepcopy(setup[2]["hits"][0])
    hit1.update(chunk_id="chunk-1", end=13, text=setup[1]["text"][:13],
                article_ids=["fixture-a001"], article_labels=["Article 1"])
    hit2.update(rank=2, chunk_id="chunk-2", start=13, text=setup[1]["text"][13:],
                article_ids=["fixture-a002"], article_labels=["Article 2"])
    retrieved = deepcopy(setup[2]); retrieved["hits"] = [hit1, hit2]
    output = response({"status": "answered", "claims": [{"text": "B.", "citation_numbers": [2]}]})
    result, _ = ask(make_service(setup, Generator(output), retrieved=retrieved)[0])
    assert [c.n for c in result.citations] == [1, 2]
    assert result.answer == "B.[2]"


def test_no_hits_refuses_without_model_or_document_load(setup):
    retrieved = deepcopy(setup[2]); retrieved["hits"] = []
    generator = Generator()
    def no_loader(version):
        raise AssertionError("source load not needed")
    result, trace = ask(make_service(setup, generator, retrieved=retrieved, loader=no_loader)[0])
    assert result.status == "insufficient" and result.answer == INSUFFICIENT_ANSWER
    assert result.claims == [] and result.citations == [] and trace.attempts == []
    assert not generator.messages


def test_evidence_insufficient_preserves_all_hits(setup):
    generator = Generator(response({"status": "insufficient", "claims": []}))
    result, trace = ask(make_service(setup, generator)[0])
    assert result.status == "insufficient" and len(result.citations) == 1
    assert trace.context_chars == 25


@pytest.mark.parametrize("mutate", [
    lambda hit: hit.update(source_url="https://wrong.example/source"),
    lambda hit: hit.update(title="wrong title"),
    lambda hit: hit.update(article_labels=["Wrong 1", "Wrong 2"]),
    lambda hit: hit.update(text=hit["text"].replace("B.", "C.")),
    lambda hit: hit.update(document_id="missing"),
])
def test_wrong_source_is_rejected_before_generation(setup, mutate):
    retrieved = deepcopy(setup[2]); mutate(retrieved["hits"][0])
    generator = Generator()
    service, _ = make_service(setup, generator, retrieved=retrieved)
    with pytest.raises(QAError) as error:
        ask(service)
    assert error.value.code == "SOURCE_MISMATCH" and not generator.messages
    assert error.value.trace["attempts"] == []


def test_invalid_rank_is_not_silently_renumbered(setup):
    retrieved = deepcopy(setup[2]); retrieved["hits"][0]["rank"] = 2
    with pytest.raises(QAError, match="shared contract") as error:
        ask(make_service(setup, retrieved=retrieved)[0])
    assert error.value.code == "RETRIEVAL_CONTRACT_ERROR"


@pytest.mark.parametrize("kind", ["corpus", "condition", "index"])
def test_mismatched_version_is_a_conflict(setup, kind):
    service, calls = make_service(setup, index_version="other" if kind == "index" else None)
    with pytest.raises(QAError) as error:
        if kind == "corpus":
            service.ask("q", "s400", "old")
        elif kind == "condition":
            service.ask("q", "f400", "fixture-en-v2")
        else:
            ask(service)
    assert error.value.status == 409
    assert not calls if kind == "corpus" else len(calls) == 1


def test_invalid_citation_can_be_repaired_once_without_retrieving_again(setup):
    bad = response({"status": "answered", "claims": [{"text": "B.", "citation_numbers": [5]}]})
    generator = Generator(bad, response())
    service, calls = make_service(setup, generator)
    result, trace = ask(service)
    assert len(calls) == 1 and len(generator.messages) == 2 and result.status == "answered"
    assert [a["state"] for a in trace.attempts] == ["failed", "completed"]
    assert generator.messages[1][:2] == generator.messages[0]
    assert len(generator.messages[1]) == 4


@pytest.mark.parametrize("output", [
    {"status": "answered", "claims": [{"text": "B.[99]", "citation_numbers": [1]}]},
    {"status": "answered", "claims": [{"text": "B.", "citation_numbers": []}]},
    {"status": "answered", "claims": [], "answer": "unchecked"},
    {"status": "insufficient", "claims": [{"text": "B.", "citation_numbers": [1]}]},
])
def test_invalid_model_output_remains_error_after_two_attempts(setup, output):
    generator = Generator(response(output), response(output))
    with pytest.raises(QAError) as error:
        ask(make_service(setup, generator)[0])
    assert error.value.code == "INVALID_MODEL_OUTPUT" and error.value.status == 502
    assert len(generator.messages) == 2 and len(error.value.trace["attempts"]) == 2


def test_transport_and_format_retries_share_one_budget(setup):
    timeout = QAError("LLM_TIMEOUT", "timed out", 503, retryable=True)
    bad = response({"status": "answered", "claims": []})
    generator = Generator(timeout, bad, response())
    with pytest.raises(QAError) as error:
        ask(make_service(setup, generator)[0])
    assert error.value.code == "INVALID_MODEL_OUTPUT"
    assert len(generator.messages) == 2 and len(generator.values) == 1


def test_auth_failure_does_not_retry_and_message_is_redacted(setup):
    generator = Generator(QAError("LLM_AUTH_ERROR", "fixture-private-key denied", 503))
    with pytest.raises(QAError) as error:
        ask(make_service(setup, generator)[0])
    assert len(generator.messages) == 1
    assert "fixture-private-key" not in str(error.value) + json.dumps(error.value.trace)


def test_model_finish_length_is_not_a_success(setup):
    generator = Generator(response(finish="length"), response(finish="length"))
    with pytest.raises(QAError) as error:
        ask(make_service(setup, generator)[0])
    assert error.value.code == "LLM_OUTPUT_TRUNCATED"


def test_duplicate_json_keys_are_rejected_even_if_the_last_value_is_valid(setup):
    raw = '{"status":"answered","status":"insufficient","claims":[]}'
    invalid = GenerationResponse(raw, "fixture-model", "stop", None, None, {})
    generator = Generator(invalid, invalid)
    with pytest.raises(QAError) as error:
        ask(make_service(setup, generator)[0])
    assert error.value.code == "INVALID_MODEL_OUTPUT" and len(generator.messages) == 2


def test_nonfinal_model_response_is_not_a_refusal_or_success(setup):
    generator = Generator(response(finish="content_filter"))
    with pytest.raises(QAError) as error:
        ask(make_service(setup, generator)[0])
    assert error.value.code == "LLM_OUTPUT_INCOMPLETE" and len(generator.messages) == 1


def test_retrieval_failure_is_retained_without_model_call(setup):
    class BrokenIndex(Exception):
        status = 409
    def broken(**kwargs):
        raise BrokenIndex("internal source detail")
    service, _ = make_service(setup)
    service.retriever = broken
    with pytest.raises(QAError) as error:
        ask(service)
    assert error.value.status == 409 and error.value.code == "RETRIEVAL_FAILED"
    assert error.value.trace["attempts"] == []
    assert error.value.trace["finished_at"] is not None


def test_unexpected_generator_exception_is_an_error_and_does_not_echo_details(setup):
    generator = Generator(RuntimeError("fixture-private-key"))
    with pytest.raises(QAError) as error:
        ask(make_service(setup, generator)[0])
    assert error.value.code == "GENERATOR_ERROR"
    assert "fixture-private-key" not in str(error.value) + json.dumps(error.value.trace)


def test_conversation_and_evidence_numbers_are_isolated_per_ask(setup):
    generator = Generator(response(), response())
    service, _ = make_service(setup, generator)
    first = service.ask("first question", "s400", "fixture-en-v2", "same-chat")
    second = service.ask("second question", "s400", "fixture-en-v2", "same-chat")
    assert first.ask_id != second.ask_id and first.conversation_id == second.conversation_id
    assert first.citations[0].n == second.citations[0].n == 1
    assert "first question" not in json.dumps(generator.messages[1])
    assert "reference_answer" not in json.dumps(generator.messages)
    assert "key_facts" not in json.dumps(generator.messages)
    assert "answerable" not in json.dumps(generator.messages)


def test_bad_request_does_not_search(setup):
    service, calls = make_service(setup)
    with pytest.raises(QAError) as error:
        service.ask(" ", "s400", "fixture-en-v2")
    assert error.value.status == 422 and not calls


def test_prompt_is_a_frozen_byte_snapshot_including_crlf(setup, tmp_path):
    prompt = tmp_path / "prompt.txt"; prompt.write_bytes(b"Return JSON.\r\n")
    settings = load_settings(environ={}, overrides={"generation": {"prompt_path": str(prompt)}})
    service = QAService(settings, retriever=lambda **kw: None, document_loader=lambda v: [], generator=Generator())
    assert service.prompt == "Return JSON.\r\n"
    prompt.write_bytes(b"changed")
    with pytest.raises(QAError) as error:
        QAService(settings, retriever=None, document_loader=None, generator=Generator())
    assert error.value.code == "PROMPT_VERSION_MISMATCH"
