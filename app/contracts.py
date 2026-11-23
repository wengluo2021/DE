"""Shared boundary contracts for DERag's evidence-based question answering.

Only Pydantic and the standard library are imported here. Importing contracts
must not initialize Chroma, load an embedding model, or contact a provider.
Frozen source strings and source URLs are validated without normalization.
"""

from __future__ import annotations

from datetime import date
from pathlib import PurePosixPath, PureWindowsPath
import re
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


CONDITIONS = ("f400", "s400", "f800", "s800")
Condition = Literal["f400", "s400", "f800", "s800", "p800"]
AnswerStatus = Literal["answered", "insufficient"]
INSUFFICIENT_ANSWER = "当前知识库没有足够证据回答这个问题。"


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("must contain a non-whitespace character")
    return value


def _frozen_text(value: str) -> str:
    if "\r" in value or value.startswith("\ufeff"):
        raise ValueError("frozen text must use LF and must not start with a BOM")
    return value


NonBlankStr = Annotated[str, StringConstraints(min_length=1), AfterValidator(_nonblank)]
FrozenText = Annotated[str, AfterValidator(_frozen_text)]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Offset = Annotated[int, Field(strict=True, ge=0)]
CitationNumber = Annotated[int, Field(strict=True, ge=1, le=5)]


class ContractModel(BaseModel):
    """Reject misspelled fields and coercions such as True -> 1 or '5' -> 5."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Article(ContractModel):
    article_id: NonBlankStr
    label: NonBlankStr
    chapter: NonBlankStr | None = None
    section: NonBlankStr | None = None
    start: Offset
    end: Offset

    @model_validator(mode="after")
    def nonempty_interval(self) -> Self:
        if self.end <= self.start:
            raise ValueError("article interval must satisfy start < end")
        return self


class Document(ContractModel):
    schema_version: Literal["1.0"]
    document_id: NonBlankStr
    corpus_version: NonBlankStr
    title: NonBlankStr
    issuer: NonBlankStr
    source_url: NonBlankStr
    published_at: str | None
    effective_at: str | None
    raw_path: NonBlankStr
    raw_sha256: Sha256
    text: FrozenText
    articles: list[Article]

    @field_validator("source_url")
    @classmethod
    def source_is_http_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("source_url must be an absolute HTTP(S) URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("source_url must not contain credentials")
        # Keep the exact authoritative string; URL model types may normalize it.
        return value

    @field_validator("published_at", "effective_at")
    @classmethod
    def nullable_iso_date(cls, value: str | None) -> str | None:
        if value is not None:
            parsed = date.fromisoformat(value)
            if parsed.isoformat() != value:
                raise ValueError("dates must be YYYY-MM-DD or null")
        return value

    @field_validator("raw_path")
    @classmethod
    def relative_snapshot_path(cls, value: str) -> str:
        windows_path = PureWindowsPath(value)
        posix_path = PurePosixPath(value.replace("\\", "/"))
        if windows_path.drive or windows_path.is_absolute() or posix_path.is_absolute() or ".." in posix_path.parts:
            raise ValueError("raw_path must stay relative to the project")
        return value

    @model_validator(mode="after")
    def source_intervals(self) -> Self:
        previous_end = 0
        seen: set[str] = set()
        for article in self.articles:
            if article.article_id in seen:
                raise ValueError("article IDs must be unique within a document")
            if article.start < previous_end or article.end > len(self.text):
                raise ValueError("article intervals must be ordered, disjoint, and inside frozen text")
            seen.add(article.article_id)
            previous_end = article.end
        return self


class SearchHit(ContractModel):
    rank: CitationNumber
    score: float
    chunk_id: NonBlankStr
    corpus_version: NonBlankStr
    condition: Condition
    document_id: NonBlankStr
    article_ids: list[NonBlankStr]
    start: Offset
    end: Offset
    text: FrozenText
    title: NonBlankStr
    source_url: NonBlankStr
    article_labels: list[NonBlankStr]

    @model_validator(mode="after")
    def block_interval(self) -> Self:
        if self.end <= self.start or len(self.text) != self.end - self.start:
            raise ValueError("hit text length must equal its nonempty Python character interval")
        if len(self.text) > (400 if self.condition.endswith("400") else 800):
            raise ValueError("hit exceeds its condition's character limit")
        if len(self.article_ids) != len(set(self.article_ids)):
            raise ValueError("hit article IDs must be unique")
        if len(self.article_ids) != len(self.article_labels):
            raise ValueError("article IDs and labels must correspond one-to-one")
        return self

    def validate_source(self, document: Document) -> Self:
        """Check this hit against an independently loaded frozen document.

        Valid syntax alone cannot establish source correctness or factual
        support. The QA service calls this before handing evidence to a model.
        """
        if self.document_id != document.document_id or self.corpus_version != document.corpus_version:
            raise ValueError("hit document or corpus differs from the frozen source")
        if self.end > len(document.text) or self.text != document.text[self.start:self.end]:
            raise ValueError("hit text differs from the frozen document slice")
        if self.title != document.title or self.source_url != document.source_url:
            raise ValueError("hit title or URL differs from authoritative source metadata")
        covered = [article for article in document.articles if article.start < self.end and article.end > self.start]
        if self.article_ids != [article.article_id for article in covered]:
            raise ValueError("hit article IDs differ from the articles actually covered")
        if self.article_labels != [article.label for article in covered]:
            raise ValueError("hit labels differ from authoritative article labels")
        return self


class SearchResult(ContractModel):
    """Matches B's search_result() dictionary without importing its service."""

    condition: Condition
    hits: list[SearchHit] = Field(max_length=5)
    timing_ms: float = Field(ge=0)
    corpus_version: NonBlankStr
    index_version: NonBlankStr

    @model_validator(mode="after")
    def coherent_hits(self) -> Self:
        if [hit.rank for hit in self.hits] != list(range(1, len(self.hits) + 1)):
            raise ValueError("hit ranks must be continuous, unique, and in returned order")
        if len({hit.chunk_id for hit in self.hits}) != len(self.hits):
            raise ValueError("a search result must not repeat a chunk")
        if any(hit.corpus_version != self.corpus_version or hit.condition != self.condition for hit in self.hits):
            raise ValueError("all hits must belong to the result's corpus and condition")
        return self


class Citation(SearchHit):
    n: CitationNumber

    @model_validator(mode="after")
    def number_is_rank(self) -> Self:
        if self.n != self.rank:
            raise ValueError("citation n must equal this round's hit rank")
        return self


class Claim(ContractModel):
    text: NonBlankStr
    citation_numbers: list[CitationNumber] = Field(min_length=1, max_length=5)

    @field_validator("text")
    @classmethod
    def no_inline_citation_numbers(cls, value: str) -> str:
        if re.search(r"\[\s*\d+\s*\]", value):
            raise ValueError("claim text must not contain inline citation numbers; use citation_numbers")
        return value

    @field_validator("citation_numbers")
    @classmethod
    def unique_numbers(cls, values: list[int]) -> list[int]:
        if len(values) != len(set(values)):
            raise ValueError("a claim must not repeat a citation number")
        return values


class ModelOutput(ContractModel):
    """The model cannot provide a second, unchecked free-text answer."""

    status: AnswerStatus
    claims: list[Claim]

    @model_validator(mode="after")
    def status_matches_claims(self) -> Self:
        if self.status == "answered" and not self.claims:
            raise ValueError("answered output must contain claims")
        if self.status == "insufficient" and self.claims:
            raise ValueError("insufficient output must contain no factual claims")
        return self


class GenerationInfo(ContractModel):
    provider: NonBlankStr
    model: NonBlankStr
    prompt_sha256: Sha256 | None
    temperature: float = Field(ge=0)
    seed: int | None = Field(default=None, strict=True)

    @model_validator(mode="after")
    def real_prompts_are_versioned(self) -> Self:
        if self.provider != "mock" and self.prompt_sha256 is None:
            raise ValueError("non-mock generation requires the actual prompt SHA-256")
        return self


class TimingInfo(ContractModel):
    retrieve: float = Field(ge=0)
    generate: float = Field(ge=0)


def render_answer(claims: list[Claim]) -> str:
    """Render validated claims once; no model-supplied answer is trusted."""
    return "\n".join(claim.text + "".join(f"[{number}]" for number in claim.citation_numbers) for claim in claims)


class AskResult(ContractModel):
    ask_id: NonBlankStr
    conversation_id: NonBlankStr
    status: AnswerStatus
    answer: NonBlankStr
    claims: list[Claim]
    citations: list[Citation] = Field(max_length=5)
    corpus_version: NonBlankStr
    index_version: NonBlankStr
    condition: Condition
    generation: GenerationInfo
    timing_ms: TimingInfo

    @model_validator(mode="after")
    def validated_answer(self) -> Self:
        if [citation.n for citation in self.citations] != list(range(1, len(self.citations) + 1)):
            raise ValueError("citation snapshots must retain continuous current-round ranks")
        if len({citation.chunk_id for citation in self.citations}) != len(self.citations):
            raise ValueError("citation snapshots must not repeat a chunk")
        if any(citation.condition != self.condition or citation.corpus_version != self.corpus_version for citation in self.citations):
            raise ValueError("citation snapshots must match this answer's corpus and condition")
        if self.status == "insufficient":
            if self.claims or self.answer != INSUFFICIENT_ANSWER:
                raise ValueError("insufficient results require empty claims and the fixed refusal")
        else:
            if not self.claims:
                raise ValueError("answered results require factual claims")
            available = {citation.n for citation in self.citations}
            if any(number not in available for claim in self.claims for number in claim.citation_numbers):
                raise ValueError("claims may cite only evidence from this answer")
            if self.answer != render_answer(self.claims):
                raise ValueError("answer must be rendered from the validated claims")
        return self

    def validate_snapshot(self, retrieval: SearchResult) -> Self:
        """Verify that unused evidence was also retained, without re-searching.

        The model alone cannot detect a missing trailing, unused hit. Comparing
        to the original retrieval result is a required QA service boundary.
        """
        if (self.condition, self.corpus_version, self.index_version) != (
            retrieval.condition, retrieval.corpus_version, retrieval.index_version
        ):
            raise ValueError("answer and retrieval versions or condition differ")
        stored = [citation.model_dump(exclude={"n"}) for citation in self.citations]
        if stored != [hit.model_dump() for hit in retrieval.hits]:
            raise ValueError("answer must retain all original retrieval hits unchanged")
        return self


class AskRequest(ContractModel):
    question: NonBlankStr = Field(max_length=1000)
    condition: Condition
    corpus_version: NonBlankStr
    conversation_id: NonBlankStr | None = None


class EvaluationRunRequest(ContractModel):
    corpus_version: NonBlankStr
    gold_version: NonBlankStr


class ErrorResponse(ContractModel):
    code: NonBlankStr
    message: NonBlankStr
