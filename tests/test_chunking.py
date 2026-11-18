from app.retrieval.types import FIXTURE_CORPUS_VERSION
import copy
import json
from app.retrieval.types import ROOT
import pytest

from app.retrieval.chunking import chunk_document, chunks_for_condition, validate_coverage
from app.retrieval.errors import RetrievalError
from app.retrieval.types import fixture_loader, validate_documents, CONDITIONS


def doc(text, articles=None):
    d = copy.deepcopy(fixture_loader(FIXTURE_CORPUS_VERSION)[0])
    d.update(text=text, articles=articles or [])
    return d


def article(start, end, label="第一条", chapter=None):
    return {"article_id": str(start), "label": label, "chapter": chapter, "section": None, "start": start, "end": end}


def test_contract_offsets_and_id():
    d = json.loads((ROOT / "tests/fixtures/b/legacy_zh_document.json").read_text(encoding="utf-8"))
    assert [(c["start"], c["end"]) for c in chunk_document(d, "fixed", 8)] == [(0, 8), (8, 13)]
    assert [(c["start"], c["end"]) for c in chunk_document(d, "structured", 8)] == [(0, 7), (7, 13)]
    c = chunks_for_condition(d, "s400")[0]
    assert c["chunk_id"] == "5377f046c4c0835be07c79e905ea0bd77e695e28c99a7e04ab5accc90f701881"
    assert c["article_ids"] == ["fixture-a001", "fixture-a002"]


@pytest.mark.parametrize("length", [0, 1, 399, 400, 401, 799, 800, 801, 2401])
@pytest.mark.parametrize("condition", list(CONDITIONS))
def test_unicode_coverage_limits_and_stability(length, condition):
    text = ("法😀\n ab。" * (length // 7 + 2))[:length]
    d = doc(text)
    chunks = chunks_for_condition(d, condition)
    assert "".join(c["text"] for c in chunks) == text
    validate_coverage(d, chunks, CONDITIONS[condition][1])
    assert chunks == chunks_for_condition(d, condition)
    d["corpus_version"] = "fixture-v2"
    changed = chunks_for_condition(d, condition)
    assert not {c["chunk_id"] for c in chunks} & {c["chunk_id"] for c in changed}


def test_chapter_heading_attaches_to_following_article():
    text = "第一章 总则\n第一条 内容。\n第二章 流程\n第二条 办理。\n"
    second_heading = text.index("第二章")
    d = doc(text, [article(text.index("第一条"), second_heading - 1, chapter="第一章"),
                   article(text.index("第二条"), len(text) - 1, "第二条", "第二章")])
    chunks = chunk_document(d, "structured", 400)
    assert [(c["start"], c["end"]) for c in chunks] == [(0, second_heading), (second_heading, len(text))]


def test_inline_article_reference_does_not_split():
    text = "第一条 根据第十条规定。\n第二章 这是条文内示例，不是章标题。"
    d = doc(text, [article(0, len(text))])
    assert len(chunk_document(d, "structured", 400)) == 1


def test_metadata_chapter_transition_without_heading():
    d = doc("第一条 A。\n第二条 B。", [article(0, 6, chapter="甲"), article(7, 13, chapter="乙")])
    assert [c["end"] for c in chunk_document(d, "structured", 400)] == [7, 13]


def test_sentence_fallback_counts_and_no_loss():
    text = "😀" * 1001 + "。\n短句。"
    stats = {}
    chunks = chunk_document(doc(text, [article(0, len(text))]), "structured", 400, stats=stats)
    assert stats["long_sentence_fallback"] == 1
    assert stats["no_article_fallback"] == 0
    assert "".join(c["text"] for c in chunks) == text
    stats = {}
    chunk_document(doc("无条号。\n另一段。"), "structured", 8, stats=stats)
    assert stats["no_article_fallback"] == 1


def test_greedy_articles_and_oversized_title():
    text = "第一章 " + "很长的标题" * 12 + "\n第一条 A。\n第二条 B。\n"
    d = doc(text, [article(text.index("第一条"), text.index("第二条") - 1),
                   article(text.index("第二条"), len(text) - 1)])
    chunks = chunk_document(d, "structured", 20)
    validate_coverage(d, chunks, 20)
    assert any(c["article_ids"] == [] for c in chunks)


@pytest.mark.parametrize("limit", [0, -1, True, 3.2])
def test_invalid_limits(limit):
    with pytest.raises(RetrievalError):
        chunk_document(doc("内容"), "fixed", limit)


def test_reject_invalid_article_offsets():
    with pytest.raises(RetrievalError, match="offsets"):
        validate_documents([doc("123", [article(0, 2), article(1, 3)])], FIXTURE_CORPUS_VERSION)


def test_english_fixture_hashes_offsets_and_contract():
    import hashlib
    documents = fixture_loader(FIXTURE_CORPUS_VERSION)
    for document in documents:
        assert document["text"].isascii()
        assert (ROOT / document["raw_path"]).read_bytes() == document["text"].encode("utf-8")
        assert hashlib.sha256(document["text"].encode("utf-8")).hexdigest() == document["raw_sha256"]
        for entry in document["articles"]:
            assert document["text"][entry["start"]:entry["end"]].startswith(entry["label"] + " ")
        for condition in CONDITIONS:
            chunks = chunks_for_condition(document, condition)
            validate_coverage(document, chunks, CONDITIONS[condition][1])
    assert len(documents[0]["text"]) == 25
    assert [(a["start"], a["end"]) for a in documents[0]["articles"]] == [(0, 12), (13, 25)]


@pytest.mark.parametrize("heading", ["Chapter 2", "CHAPTER II", "Section 2"])
@pytest.mark.parametrize("with_metadata", [False, True])
def test_english_heading_attaches_to_next_article(heading, with_metadata):
    text = f"Article 1 Keep records.\n{heading} Procedure\nArticle 2 Reply promptly."
    start = text.index(heading)
    d = doc(text, [article(0, start - 1, "Article 1"),
                   article(text.index("Article 2"), len(text), "Article 2", heading if with_metadata else None)])
    assert [(c["start"], c["end"]) for c in chunk_document(d, "structured", 400)] == [(0, start), (start, len(text))]


def test_english_inline_heading_reference_is_not_a_new_chapter():
    text = "Article 1 Follow this quoted example:\nChapter II is mentioned inside this article."
    assert len(chunk_document(doc(text, [article(0, len(text), "Article 1")]), "structured", 400)) == 1


def test_english_sentence_splitting_preserves_decimal_and_domain():
    from app.retrieval.chunking import BOUNDARY
    text = 'Article 1 The fee is 3.14 at example.org. Keep the receipt! Reply promptly? Archive it; Done.'
    ends = [m.end() for m in BOUNDARY.finditer(text)]
    assert [text[a:b] for a, b in zip([0] + ends, ends)] == [
        'Article 1 The fee is 3.14 at example.org. ', 'Keep the receipt! ',
        'Reply promptly? ', 'Archive it; ', 'Done.']
    stats = {}
    chunks = chunk_document(doc(text, [article(0, len(text), "Article 1")]), "structured", 45, stats=stats)
    assert stats["long_sentence_fallback"] == 0
    assert all(c["end"] in ends for c in chunks)
    assert ''.join(c["text"] for c in chunks) == text


def test_active_loader_rejects_stale_chinese_corpus_version():
    with pytest.raises(RetrievalError) as exc:
        fixture_loader("fixture-v1")
    assert exc.value.code == "VERSION_MISMATCH"
