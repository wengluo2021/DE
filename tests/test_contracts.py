"""Behavioral tests for the shared contracts; no embedding/model is loaded."""

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts import (
    AskRequest,
    AskResult,
    Citation,
    Claim,
    Document,
    GenerationInfo,
    INSUFFICIENT_ANSWER,
    ModelOutput,
    SearchHit,
    SearchResult,
    render_answer,
)


FIXTURES = Path(__file__).parent / "fixtures" / "b"


@pytest.fixture
def document_data():
    return json.loads((FIXTURES / "document.json").read_text(encoding="utf-8"))


@pytest.fixture
def hit_data():
    return json.loads((FIXTURES / "expected_hits.json").read_text(encoding="utf-8"))["hit"]


@pytest.fixture
def result_data(hit_data):
    return {
        "ask_id": "ask-one",
        "conversation_id": "chat-one",
        "status": "answered",
        "answer": "Article 2 says B.[1]",
        "claims": [{"text": "Article 2 says B.", "citation_numbers": [1]}],
        "citations": [dict(hit_data, n=1)],
        "corpus_version": hit_data["corpus_version"],
        "index_version": "fixture-index-v1",
        "condition": hit_data["condition"],
        "generation": {"provider": "mock", "model": "fixture-model", "prompt_sha256": None, "temperature": 0, "seed": None},
        "timing_ms": {"retrieve": 10, "generate": 20},
    }


def retrieval_for(data, hits):
    return SearchResult.model_validate({
        "condition": data["condition"], "corpus_version": data["corpus_version"],
        "index_version": data["index_version"], "timing_ms": 10, "hits": hits,
    })


def test_current_b_dictionaries_round_trip_without_importing_b(document_data, hit_data, result_data):
    document = Document.model_validate(document_data)
    hit = SearchHit.model_validate(hit_data)
    assert document.model_dump() == document_data
    assert hit.model_dump() == hit_data
    assert hit.validate_source(document) is hit
    result = AskResult.model_validate(result_data)
    assert result.validate_snapshot(retrieval_for(result_data, [hit_data])) is result
    assert result.model_dump() == result_data


def test_unicode_offsets_and_surrounding_whitespace_are_not_normalized(document_data, hit_data):
    text = "  第一条 😀。\n第二条 B。  "
    second_start = text.index("第二条")
    document_data.update(text=text)
    document_data["articles"] = [
        {"article_id": "a1", "label": "第一条", "chapter": None, "section": None, "start": 2, "end": text.index("\n")},
        {"article_id": "a2", "label": "第二条", "chapter": None, "section": None, "start": second_start, "end": len(text) - 2},
    ]
    document = Document.model_validate(document_data)
    start = text.index("😀")
    hit_data.update(start=start, end=start + 1, text="😀", article_ids=["a1"], article_labels=["第一条"])
    hit = SearchHit.model_validate(hit_data).validate_source(document)
    assert document.text == text
    assert hit.end - hit.start == 1
    assert document.text[hit.start:hit.end] == "😀"


@pytest.mark.parametrize("bad_text", ["\ufeffArticle 1 A.", "Article 1 A.\r\nArticle 2 B."])
def test_frozen_text_cannot_be_silently_cleaned(document_data, bad_text):
    document_data.update(text=bad_text, articles=[])
    with pytest.raises(ValidationError):
        Document.model_validate(document_data)


@pytest.mark.parametrize("change", [
    {"start": True}, {"start": "0"}, {"start": -1}, {"end": 0}, {"end": 26},
])
def test_article_positions_are_strict_python_character_intervals(document_data, change):
    document_data["articles"][0].update(change)
    with pytest.raises(ValidationError):
        Document.model_validate(document_data)


@pytest.mark.parametrize("fault", ["overlap", "duplicate", "reversed"])
def test_document_rejects_incoherent_article_structure(document_data, fault):
    if fault == "overlap":
        document_data["articles"][1]["start"] = 11
    elif fault == "duplicate":
        document_data["articles"][1]["article_id"] = document_data["articles"][0]["article_id"]
    else:
        document_data["articles"].reverse()
    with pytest.raises(ValidationError):
        Document.model_validate(document_data)


@pytest.mark.parametrize("path", ["../raw.txt", "/tmp/raw.txt", "C:\\raw.txt", "C:raw.txt", "\\\\host\\raw.txt"])
def test_snapshot_paths_remain_relative(document_data, path):
    document_data["raw_path"] = path
    with pytest.raises(ValidationError):
        Document.model_validate(document_data)


def test_nullable_dates_empty_document_and_exact_url_are_supported(document_data):
    document_data.update(text="", articles=[], source_url="https://example.org", published_at="2026-11-18")
    document = Document.model_validate(document_data)
    assert document.text == ""
    assert document.source_url == "https://example.org"
    assert document.effective_at is None


@pytest.mark.parametrize("change", [
    {"source_url": "javascript:alert(1)"}, {"source_url": "https://user:pass@example.org/"},
    {"published_at": "20261118"}, {"effective_at": "2026-02-30"}, {"raw_sha256": "bad"}, {"unexpected": True},
])
def test_document_rejects_invalid_metadata_instead_of_coercing_it(document_data, change):
    document_data.update(change)
    with pytest.raises(ValidationError):
        Document.model_validate(document_data)


@pytest.mark.parametrize("score", [-0.5, 1.1])
def test_similarity_score_is_not_a_probability(hit_data, score):
    assert SearchHit.model_validate(dict(hit_data, score=score)).score == score


@pytest.mark.parametrize("change", [
    {"score": float("nan")}, {"score": float("inf")}, {"rank": True}, {"rank": "1"},
    {"rank": 0}, {"rank": 6}, {"text": "short"}, {"end": 0}, {"source_url": 123},
])
def test_malformed_hit_is_rejected(hit_data, change):
    with pytest.raises(ValidationError):
        SearchHit.model_validate(dict(hit_data, **change))


@pytest.mark.parametrize("change", [
    {"document_id": "other"}, {"corpus_version": "other-version"}, {"title": "wrong title"},
    {"source_url": "https://example.org/wrong"}, {"article_ids": ["fixture-a002", "fixture-a001"]},
    {"article_labels": ["Article 2", "Article 1"]}, {"text": "X" * 25},
])
def test_correctly_shaped_hit_still_requires_authoritative_source_check(document_data, hit_data, change):
    hit = SearchHit.model_validate(dict(hit_data, **change))
    with pytest.raises(ValueError):
        hit.validate_source(Document.model_validate(document_data))


@pytest.mark.parametrize("ranks", [[1, 1], [1, 3], [2, 1]])
def test_rank_duplicates_gaps_and_reordering_are_not_repaired(hit_data, result_data, ranks):
    hits = [dict(hit_data, rank=rank, chunk_id=f"chunk-{index}") for index, rank in enumerate(ranks)]
    with pytest.raises(ValidationError):
        retrieval_for(result_data, hits)


@pytest.mark.parametrize("change", [{"condition": "f400"}, {"corpus_version": "other"}])
def test_retrieval_cannot_mix_conditions_or_corpora(hit_data, result_data, change):
    with pytest.raises(ValidationError):
        retrieval_for(result_data, [dict(hit_data, **change)])


def test_citation_number_must_equal_rank(hit_data):
    with pytest.raises(ValidationError):
        Citation.model_validate(dict(hit_data, n=2))


@pytest.mark.parametrize("numbers", [[], [0], [6], [True], ["1"], [1, 1]])
def test_claim_requires_valid_unique_integer_citation_numbers(numbers):
    with pytest.raises(ValidationError):
        Claim.model_validate({"text": "A fact.", "citation_numbers": numbers})


@pytest.mark.parametrize("text", [
    "wrong[99]", "[1] A fact.", "A fact.[1][2]", "A fact.[ 2 ]", "A fact.[１２]", "A fact.[\n3\n]",
])
def test_claim_cannot_smuggle_inline_citation_markers(text):
    with pytest.raises(ValidationError):
        Claim.model_validate({"text": text, "citation_numbers": [1]})


def test_claim_preserves_bracketed_text_that_is_not_a_citation():
    claim = Claim(text="Clause [A] describes the rule.", citation_numbers=[1])
    assert render_answer([claim]) == "Clause [A] describes the rule.[1]"


@pytest.mark.parametrize("data", [
    {"status": "answered", "claims": []},
    {"status": "insufficient", "claims": [{"text": "A fact.", "citation_numbers": [1]}]},
    {"status": "failed", "claims": []},
    {"status": "answered", "claims": [{"text": "A fact.", "citation_numbers": [1]}], "answer": "unchecked answer"},
])
def test_model_has_only_two_business_states_and_no_unchecked_answer(data):
    with pytest.raises(ValidationError):
        ModelOutput.model_validate(data)


def test_rendering_uses_only_claims_and_their_citation_lists():
    claims = [Claim(text="First.", citation_numbers=[1, 2]), Claim(text="Second.", citation_numbers=[2])]
    assert render_answer(claims) == "First.[1][2]\nSecond.[2]"


@pytest.mark.parametrize("fault", ["unknown_reference", "free_text", "wrong_version", "wrong_condition", "gapped_citations"])
def test_answer_result_rejects_invalid_answer_or_evidence_binding(result_data, fault):
    if fault == "unknown_reference":
        result_data["claims"][0]["citation_numbers"] = [2]
        result_data["answer"] = "Article 2 says B.[2]"
    elif fault == "free_text":
        result_data["answer"] += " An unsupported extra fact."
    elif fault == "wrong_version":
        result_data["citations"][0]["corpus_version"] = "other"
    elif fault == "wrong_condition":
        result_data["citations"][0]["condition"] = "f400"
    else:
        result_data["citations"][0].update(rank=2, n=2)
    with pytest.raises(ValidationError):
        AskResult.model_validate(result_data)


def test_unused_retrieval_evidence_must_not_be_dropped(hit_data, result_data):
    second_hit = dict(hit_data, rank=2, chunk_id="second-chunk")
    retrieval = retrieval_for(result_data, [hit_data, second_hit])
    incomplete = AskResult.model_validate(result_data)
    with pytest.raises(ValueError):
        incomplete.validate_snapshot(retrieval)
    result_data["citations"].append(dict(second_hit, n=2))
    complete = AskResult.model_validate(result_data)
    assert complete.validate_snapshot(retrieval) is complete
    assert complete.claims[0].citation_numbers == [1]
    assert len(complete.citations) == 2


def test_refusal_retains_all_retrieved_evidence_and_uses_fixed_text(hit_data, result_data):
    result_data.update(status="insufficient", claims=[], answer=INSUFFICIENT_ANSWER)
    result = AskResult.model_validate(result_data)
    assert result.validate_snapshot(retrieval_for(result_data, [hit_data])) is result
    assert len(result.citations) == 1
    result_data["citations"] = []
    assert AskResult.model_validate(result_data).validate_snapshot(retrieval_for(result_data, [])).citations == []
    result_data["answer"] = "Probably no answer."
    with pytest.raises(ValidationError):
        AskResult.model_validate(result_data)


def test_same_number_can_belong_to_separate_ask_snapshots(result_data):
    first = AskResult.model_validate(result_data)
    other = copy.deepcopy(result_data)
    other["ask_id"] = "ask-two"
    other["citations"][0]["chunk_id"] = "another-question-chunk"
    second = AskResult.model_validate(other)
    assert first.citations[0].n == second.citations[0].n == 1
    assert (first.ask_id, first.citations[0].n) != (second.ask_id, second.citations[0].n)
    assert first.citations[0].chunk_id != second.citations[0].chunk_id


def test_real_prompt_requires_hash_and_generation_has_no_secret_field(result_data):
    generation = dict(result_data["generation"], provider="authorized-provider")
    with pytest.raises(ValidationError):
        GenerationInfo.model_validate(generation)
    generation["prompt_sha256"] = "a" * 64
    assert GenerationInfo.model_validate(generation).prompt_sha256 == "a" * 64
    generation["api_key"] = "not-a-real-key"
    with pytest.raises(ValidationError):
        GenerationInfo.model_validate(generation)


@pytest.mark.parametrize("change", [
    {"question": " \n"}, {"question": "a" * 1001}, {"question": 12},
    {"condition": "S400"}, {"condition": "bad"}, {"corpus_version": ""},
    {"conversation_id": " "}, {"top_k": 3},
])
def test_ask_request_is_strict_and_does_not_allow_experiment_overrides(change):
    data = {"question": "What does Article 2 say?", "condition": "s400", "corpus_version": "fixture-en-v2"}
    with pytest.raises(ValidationError):
        AskRequest.model_validate(data | change)


def test_request_validation_preserves_input_text_and_defaults_conversation():
    request = AskRequest.model_validate({"question": "  A question?  ", "condition": "s400", "corpus_version": "fixture-en-v2"})
    assert request.question == "  A question?  "
    assert request.conversation_id is None
