from dataclasses import dataclass
import hashlib
import json

from pydantic import Field,StrictBool,model_validator

from app.contracts import ContractModel,Document,FrozenText,NonBlankStr,Offset
from app.qa.errors import QAError


class GoldEvidence(ContractModel):
    document_id:NonBlankStr
    article_id:NonBlankStr
    start:Offset
    end:Offset
    text:FrozenText=Field(min_length=1,max_length=399)

    @model_validator(mode="after")
    def interval(self):
        if self.end<=self.start or len(self.text)!=self.end-self.start:
            raise ValueError("Gold evidence must match a nonempty character interval")
        return self


class GoldCase(ContractModel):
    schema_version:str
    case_id:NonBlankStr
    question:NonBlankStr=Field(max_length=1000)
    topic:NonBlankStr
    answerable:StrictBool
    reference_answer:NonBlankStr|None
    key_facts:list[NonBlankStr]
    evidence:list[GoldEvidence]
    unanswerable_reason:NonBlankStr|None

    @model_validator(mode="after")
    def case_shape(self):
        if self.schema_version!="1.0":
            raise ValueError("Unsupported gold schema")
        if self.answerable:
            if not self.reference_answer or not self.key_facts or not self.evidence or self.unanswerable_reason is not None:
                raise ValueError("Answerable cases need a reference and evidence")
        elif self.reference_answer is not None or self.key_facts or self.evidence or not self.unanswerable_reason:
            raise ValueError("Unanswerable cases must describe why the frozen corpus is insufficient")
        return self


@dataclass(frozen=True)
class GoldDataset:
    corpus_version:str
    gold_version:str
    cases:list[GoldCase]
    synthetic:bool=False

    def snapshot(self):
        return [case.model_dump(mode="json") for case in self.cases]


def validate_cases(cases,documents):
    docs={d.document_id:d for d in documents}
    if len(docs)!=len(documents) or not cases or len({case.case_id for case in cases})!=len(cases):
        raise ValueError("Gold cases must be nonempty and have unique IDs")
    for case in cases:
        for evidence in case.evidence:
            doc=docs[evidence.document_id]
            article=next(a for a in doc.articles if a.article_id==evidence.article_id)
            if not article.start<=evidence.start<evidence.end<=article.end:
                raise ValueError("Gold evidence must stay inside its declared article")
            if evidence.text!=doc.text[evidence.start:evidence.end]:
                raise ValueError("Gold text must equal the frozen document slice")


def load_gold(settings,document_loader):
    """Validate A's existing frozen outputs; never collect sources or author gold."""
    cfg=settings.experiment
    if not cfg.gold_version:
        raise QAError("GOLD_NOT_CONFIGURED","Configure A's frozen gold version before evaluation",409)
    try:
        manifest=json.loads((cfg.data_dir/"eval/manifest.json").read_text(encoding="utf-8"))
        raw=(cfg.data_dir/"eval/gold.jsonl").read_bytes()
        if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n"):
            raise ValueError("Gold must be UTF-8 without BOM, with LF and a final newline")
        version=hashlib.sha256(raw).hexdigest()
        if (manifest.get("schema_version")!="1.0" or manifest.get("corpus_version")!=cfg.corpus_version
                or manifest.get("gold_version")!=version or cfg.gold_version!=version):
            raise ValueError("Gold manifest or configuration version differs")
        cases=[GoldCase.model_validate_json(line) for line in raw.decode("utf-8").splitlines()]
        documents=[Document.model_validate(d.model_dump() if isinstance(d,Document) else d)
                   for d in document_loader(cfg.corpus_version)]
        if any(d.corpus_version!=cfg.corpus_version for d in documents):
            raise ValueError("Document corpus version differs")
        validate_cases(cases,documents)
        answerable=sum(c.answerable for c in cases)
        if (answerable!=24 or len(cases)-answerable!=6 or manifest.get("answerable_count",24)!=24
                or manifest.get("unanswerable_count",6)!=6):
            raise ValueError("Frozen gold must have exactly 24 answerable and 6 unanswerable cases")
        return GoldDataset(cfg.corpus_version,version,cases)
    except (OSError,ValueError,KeyError,StopIteration,TypeError):
        raise QAError("INVALID_GOLD_DATA","Frozen gold data, versions or evidence failed validation",409) from None
