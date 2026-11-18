"""Retrieve once, verify evidence, generate bounded claims, validate, and trace."""
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import time
from uuid import uuid4

from pydantic import ValidationError

from app.config import Settings
from app.contracts import (AskRequest, AskResult, Citation, Document, GenerationInfo,
                           INSUFFICIENT_ANSWER, ModelOutput, SearchResult, TimingInfo, render_answer)
from .client import GenerationResponse, redact
from .errors import QAError


def _now():
    return datetime.now(timezone.utc).isoformat()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate model output key")
        result[key] = value
    return result


@dataclass
class AskTrace:
    ask_id: str
    conversation_id: str
    question: str
    condition: str
    corpus_version: str
    started_at: str = field(default_factory=_now)
    finished_at: str | None = None
    retrieval: dict | None = None
    context_chars: int = 0
    attempts: list = field(default_factory=list)
    timing_ms: dict = field(default_factory=lambda: {"retrieve": None, "generate": 0.0})
    error: dict | None = None

    def to_dict(self):
        return deepcopy(asdict(self))


class QAService:
    def __init__(self, settings: Settings, *, retriever, document_loader, generator,
                 index_version=None, sleeper=time.sleep):
        self.settings = settings
        self.retriever = retriever
        self.document_loader = document_loader
        self.generator = generator
        self.index_version = index_version
        self.sleeper = sleeper
        prompt_bytes = settings.experiment.generation.prompt_path.read_bytes()
        self.prompt = prompt_bytes.decode("utf-8")
        if hashlib.sha256(prompt_bytes).hexdigest() != settings.prompt_sha256:
            raise QAError("PROMPT_VERSION_MISMATCH", "Prompt changed after configuration was loaded", 409)

    def ask(self, question, condition, corpus_version, conversation_id=None):
        return self.ask_with_trace(question, condition, corpus_version, conversation_id)[0]

    def ask_with_trace(self, question, condition, corpus_version, conversation_id=None):
        try:
            request = AskRequest(question=question, condition=condition,
                                 corpus_version=corpus_version, conversation_id=conversation_id)
        except ValidationError:
            raise QAError("INVALID_REQUEST", "Question, condition, version or conversation ID is invalid", 422) from None
        trace = AskTrace("ask-" + uuid4().hex, request.conversation_id or "chat-" + uuid4().hex,
                         request.question, request.condition, request.corpus_version)
        try:
            return self._run(request, trace), trace
        except QAError as exc:
            trace.error = exc.as_dict()
            if trace.attempts:
                first = datetime.fromisoformat(trace.attempts[0]["started_at"])
                trace.timing_ms["generate"] = (datetime.now(timezone.utc) - first).total_seconds() * 1000
            trace.finished_at = _now()
            exc.trace = trace.to_dict()
            raise

    def _run(self, request, trace):
        settings = self.settings
        cfg = settings.experiment
        gen = cfg.generation
        if request.corpus_version != cfg.corpus_version:
            raise QAError("VERSION_MISMATCH", "Requested corpus does not match the active configuration", 409)
        if cfg.mode == "formal" and self.index_version is None:
            raise QAError("INDEX_NOT_CONFIGURED", "A fixed active index version is required in formal mode", 409)
        try:
            raw = self.retriever(question=request.question, condition=request.condition,
                                 corpus_version=request.corpus_version, top_k=5)
        except Exception as exc:
            status = getattr(exc, "status", 503)
            if type(status) is not int or status not in {404, 409, 422, 502, 503}:
                status = 503
            raise QAError("RETRIEVAL_FAILED", "Evidence retrieval failed; inspect the retrieval component", status) from None
        try:
            retrieved = SearchResult.model_validate(raw.model_dump() if isinstance(raw, SearchResult) else raw)
        except ValidationError:
            raise QAError("RETRIEVAL_CONTRACT_ERROR", "Retrieved evidence does not match the shared contract", 502) from None
        trace.retrieval = retrieved.model_dump(mode="json")
        trace.timing_ms["retrieve"] = retrieved.timing_ms
        if (retrieved.condition != request.condition or retrieved.corpus_version != request.corpus_version
                or (self.index_version is not None and retrieved.index_version != self.index_version)):
            raise QAError("VERSION_MISMATCH", "Retrieved evidence belongs to another condition or index version", 409)
        if retrieved.hits:
            try:
                docs = [Document.model_validate(d.model_dump() if isinstance(d, Document) else d)
                        for d in self.document_loader(request.corpus_version)]
                if len({d.document_id for d in docs}) != len(docs):
                    raise ValueError("duplicate document")
                sources = {d.document_id: d for d in docs}
                for hit in retrieved.hits:
                    hit.validate_source(sources[hit.document_id])
            except (ValueError, KeyError, TypeError):
                raise QAError("SOURCE_MISMATCH", "Evidence cannot be verified against the frozen source", 502) from None
            except Exception:
                raise QAError("SOURCE_UNAVAILABLE", "Frozen source documents could not be loaded", 503) from None
        trace.context_chars = sum(len(hit.text) for hit in retrieved.hits)
        citations = [Citation(**hit.model_dump(), n=hit.rank) for hit in retrieved.hits]
        model = gen.model or "not-configured"
        generation_time = 0.0
        if not retrieved.hits:
            output = ModelOutput(status="insufficient", claims=[])
        else:
            evidence = [{"n": c.n, "title": c.title, "article_labels": c.article_labels,
                         "chunk_id": c.chunk_id, "text": c.text} for c in citations]
            messages = [{"role": "system", "content": self.prompt},
                        {"role": "user", "content": json.dumps({"question": request.question,
                         "evidence": evidence}, ensure_ascii=False)}]
            start = time.perf_counter()
            for number in range(1, gen.max_attempts + 1):
                attempt = {"number": number, "started_at": _now()}
                trace.attempts.append(attempt)
                try:
                    response = self.generator.generate(deepcopy(messages))
                    if not isinstance(response, GenerationResponse):
                        raise QAError("LLM_INVALID_RESPONSE", "Generator returned an invalid response object", 502, retryable=True)
                    # Redact again so even an injected adapter cannot leak credentials into traces.
                    response = GenerationResponse(**redact(asdict(response), settings.api_key()))
                    if not isinstance(response.model, str) or not response.model.strip():
                        raise QAError("LLM_INVALID_RESPONSE", "Generator returned invalid model metadata", 502, retryable=True)
                    attempt["response"] = deepcopy(response.raw)
                    attempt["content"] = response.content
                    attempt["usage"] = deepcopy(response.usage)
                    attempt["model"] = response.model
                    attempt["finish_reason"] = response.finish_reason
                    if response.finish_reason == "length":
                        raise QAError("LLM_OUTPUT_TRUNCATED", "Generated answer was truncated", 502, retryable=True)
                    if response.finish_reason not in {None, "stop"}:
                        raise QAError("LLM_OUTPUT_INCOMPLETE", "Generation service did not return a final answer", 502)
                    try:
                        parsed = json.loads(response.content, object_pairs_hook=_unique_object)
                        output = ModelOutput.model_validate(parsed)
                        available = {c.n for c in citations}
                        if any(n not in available for claim in output.claims for n in claim.citation_numbers):
                            raise ValueError("citation absent from this round")
                    except (ValueError, ValidationError):
                        raise QAError("INVALID_MODEL_OUTPUT", "Generated claims or citations failed validation", 502, retryable=True) from None
                    model = response.model
                    attempt["state"] = "completed"
                    attempt["finished_at"] = _now()
                    break
                except QAError as exc:
                    exc = QAError(exc.code, redact(exc.message, settings.api_key()), exc.status, retryable=exc.retryable)
                    attempt["state"] = "failed"
                    attempt["error"] = exc.as_dict()
                    attempt["finished_at"] = _now()
                    if not exc.retryable or number == gen.max_attempts:
                        raise exc from None
                    if exc.code in {"INVALID_MODEL_OUTPUT", "LLM_OUTPUT_TRUNCATED"}:
                        # Same original evidence. No gold answer or additional retrieval is introduced.
                        messages.append({"role": "assistant", "content": response.content})
                        messages.append({"role": "user", "content": "The previous output failed " + exc.code
                                         + ". Return only the required JSON using valid evidence numbers. "
                                         "If evidence is insufficient use insufficient and empty claims."})
                    else:
                        self.sleeper(0.25)
                except Exception:
                    attempt["state"] = "failed"
                    attempt["error"] = {"code": "GENERATOR_ERROR", "message": "Unexpected generator failure"}
                    attempt["finished_at"] = _now()
                    raise QAError("GENERATOR_ERROR", "Unexpected generator failure", 502) from None
            generation_time = (time.perf_counter() - start) * 1000
        trace.timing_ms["generate"] = generation_time
        answer = render_answer(output.claims) if output.status == "answered" else INSUFFICIENT_ANSWER
        try:
            result = AskResult(ask_id=trace.ask_id, conversation_id=trace.conversation_id,
                               status=output.status, answer=answer, claims=output.claims, citations=citations,
                               corpus_version=request.corpus_version, index_version=retrieved.index_version,
                               condition=request.condition,
                               generation=GenerationInfo(provider=gen.provider, model=model,
                               prompt_sha256=settings.prompt_sha256, temperature=gen.temperature, seed=gen.seed),
                               timing_ms=TimingInfo(retrieve=retrieved.timing_ms, generate=generation_time))
            result.validate_snapshot(retrieved)
        except (ValidationError, ValueError):
            raise QAError("ANSWER_CONTRACT_ERROR", "Answer could not be validated against the complete evidence snapshot", 502) from None
        trace.finished_at = _now()
        return result
