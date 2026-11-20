from dataclasses import dataclass
import hashlib
import json

from pydantic import Field,StrictBool,model_validator

from app.contracts import ContractModel,Document,FrozenText,NonBlankStr,Offset
from app.qa.errors import QAError
from app.data.corpus import read_frozen_json,_unique
from app.data.corpus import frozen_path,_sha
from app.data.document_view import document_view


class GoldEvidence(ContractModel):
    document_id:NonBlankStr
    article_id:NonBlankStr|None=None
    structure_id:NonBlankStr|None=None
    start:Offset
    end:Offset
    text:FrozenText=Field(min_length=1,max_length=399)

    @model_validator(mode="after")
    def interval(self):
        if (self.article_id is None)==(self.structure_id is None):
            raise ValueError("Evidence needs exactly one article or structure ID")
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
    refusal_reference:NonBlankStr|None=None

    @model_validator(mode="after")
    def case_shape(self):
        if self.schema_version!="1.0":
            raise ValueError("Unsupported gold schema")
        if self.answerable:
            if (not self.reference_answer or not self.key_facts or not self.evidence
                    or self.unanswerable_reason is not None or self.refusal_reference is not None):
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


def validate_cases(cases,documents,structures=None):
    docs={d.document_id:d for d in documents}
    if len(docs)!=len(documents) or not cases or len({case.case_id for case in cases})!=len(cases):
        raise ValueError("Gold cases must be nonempty and have unique IDs")
    for case in cases:
        for evidence in case.evidence:
            doc=docs[evidence.document_id]
            if evidence.article_id is not None:
                article=next(a for a in doc.articles if a.article_id==evidence.article_id)
                start,end=article.start,article.end
            else:
                start,end=(structures or {})[doc.document_id][evidence.structure_id]
            if not start<=evidence.start<evidence.end<=end:
                raise ValueError("Gold evidence must stay inside its declared source structure")
            if evidence.text!=doc.text[evidence.start:evidence.end]:
                raise ValueError("Gold text must equal the frozen document slice")


def source_structures(settings,documents):
    """Validate A's accepted full structures before accepting annex evidence."""
    cfg=settings.experiment
    if cfg.input_adapter!="eurlex-a-v1":
        return {}
    if cfg.structure_dir is None:
        raise ValueError("A's accepted structure directory is required")
    result={}
    for doc in documents:
        if not isinstance(doc,dict) or doc.get("kind")!="formal_corpus":
            raise ValueError("The EUR-Lex adapter requires formal A exports")
        path=frozen_path(cfg.structure_dir,doc["document_id"]+".json")
        metadata=doc["source_fields"]
        if hashlib.sha256(path.read_bytes()).hexdigest()!=_sha(metadata["accepted_structure_json_sha256"]):
            raise ValueError("Accepted full structure SHA differs")
        full=read_frozen_json(path)
        text_sha=hashlib.sha256(doc["text"].encode("utf-8")).hexdigest()
        if (full["document_id"]!=doc["document_id"] or full["clean_text_sha256"]!=text_sha
                or metadata["accepted_clean_text_sha256"]!=text_sha):
            raise ValueError("Accepted full structure belongs to different text")
        structures={}
        for item in full["annexes"]:
            identifier=item["structure_id"]
            start,end=item["start"],item["end"]
            if (not isinstance(identifier,str) or not identifier.strip() or identifier in structures
                    or type(start) is not int or type(end) is not int
                    or not 0<=start<end<=len(doc["text"])
                    or item["text"]!=doc["text"][start:end]):
                raise ValueError("Accepted annex ID, interval or text differs")
            structures[identifier]=(start,end)
        result[doc["document_id"]]=structures
    return result


def _a_case(raw,corpus_version):
    expected={"case_id","corpus_version","question","question_type","should_refuse",
              "reference_answer","key_facts","evidence","refusal_reason"}
    if (not isinstance(raw,dict) or set(raw)!=expected or raw["corpus_version"]!=corpus_version
            or type(raw["should_refuse"]) is not bool
            or raw["question_type"] not in {"single_article","multi_evidence","unanswerable"}
            or (raw["question_type"]=="unanswerable")!=raw["should_refuse"]
            or not isinstance(raw["reference_answer"],str) or not raw["reference_answer"].strip()):
        raise ValueError("Unexpected A gold fields or corpus version")
    evidence=[]
    for item in raw["evidence"]:
        keys=set(item)
        common={"document_id","start","end","quote"}
        if keys not in (common|{"article_id"},common|{"structure_id"}):
            raise ValueError("Unexpected A evidence fields")
        evidence.append({("text" if key=="quote" else key):value for key,value in item.items()})
    return GoldCase.model_validate({"schema_version":"1.0","case_id":raw["case_id"],
        "question":raw["question"],"topic":raw["question_type"],"answerable":not raw["should_refuse"],
        "reference_answer":None if raw["should_refuse"] else raw["reference_answer"],
        "refusal_reference":raw["reference_answer"] if raw["should_refuse"] else None,
        "key_facts":raw["key_facts"],"evidence":evidence,"unanswerable_reason":raw["refusal_reason"]})


def load_gold(settings,document_loader):
    """Validate A's existing frozen outputs; never collect sources or author gold."""
    cfg=settings.experiment
    if not cfg.gold_version:
        raise QAError("GOLD_NOT_CONFIGURED","Configure A's frozen gold version before evaluation",409)
    try:
        manifest=read_frozen_json(cfg.gold_root/"manifest.json")
        raw=(cfg.gold_root/"gold.jsonl").read_bytes()
        if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n"):
            raise ValueError("Gold must be UTF-8 without BOM, with LF and a final newline")
        version=hashlib.sha256(raw).hexdigest()
        if (manifest.get("schema_version")!="1.0" or manifest.get("corpus_version")!=cfg.corpus_version
                or manifest.get("gold_version")!=version or cfg.gold_version!=version):
            raise ValueError("Gold manifest or configuration version differs")
        rows=[json.loads(line,object_pairs_hook=_unique) for line in raw.decode("utf-8").splitlines()]
        if cfg.input_adapter=="eurlex-a-v1":
            if (manifest.get("kind")!="gold_set" or manifest.get("gold_sha256")!=version
                    or manifest.get("question_count")!=30 or manifest.get("refusal_count")!=6):
                raise ValueError("A gold manifest differs")
            cases=[_a_case(row,cfg.corpus_version) for row in rows]
        else:
            cases=[GoldCase.model_validate(row) for row in rows]
        originals=list(document_loader(cfg.corpus_version))
        documents=[document_view(d) for d in originals]
        if any(d.corpus_version!=cfg.corpus_version for d in documents):
            raise ValueError("Document corpus version differs")
        validate_cases(cases,documents,source_structures(settings,originals))
        answerable=sum(c.answerable for c in cases)
        if (answerable!=24 or len(cases)-answerable!=6 or manifest.get("answerable_count",24)!=24
                or manifest.get("unanswerable_count",6)!=6):
            raise ValueError("Frozen gold must have exactly 24 answerable and 6 unanswerable cases")
        return GoldDataset(cfg.corpus_version,version,cases)
    except (OSError,ValueError,KeyError,StopIteration,TypeError):
        raise QAError("INVALID_GOLD_DATA","Frozen gold data, versions or evidence failed validation",409) from None
