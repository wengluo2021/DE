from copy import deepcopy
import hashlib
import json

import pytest

from app.config import load_settings
from app.evaluation.data import GoldCase,load_gold
from app.evaluation.metrics import case_metrics,evidence_coverage,summarize
from app.evaluation.review import ReviewPatch,merge_review
from app.qa.errors import QAError
from tests.support.c_fixtures import document_loader
from tests.support.evaluation_fixtures import dataset


def test_coverage_requires_full_document_specific_union():
    evidence=[{"document_id":"a","start":10,"end":20},{"document_id":"b","start":0,"end":2}]
    hits=[{"document_id":"a","rank":1,"start":10,"end":15},
          {"document_id":"a","rank":2,"start":15,"end":20},
          {"document_id":"b","rank":3,"start":0,"end":2}]
    assert evidence_coverage(hits,evidence,1)=={"any":False,"all":False}
    assert evidence_coverage(hits,evidence,2)=={"any":True,"all":False}
    assert evidence_coverage(hits,evidence,5)=={"any":True,"all":True}
    hits[1]["start"]=16
    assert evidence_coverage(hits,evidence,2)=={"any":False,"all":False}
    hits[1]["start"]=15;hits[1]["document_id"]="other"
    assert evidence_coverage(hits,evidence,2)=={"any":False,"all":False}
    assert evidence_coverage(hits,[],5)=={"any":None,"all":None}


def test_fixed_denominators_errors_pending_and_zero_claims():
    gold=dataset().snapshot()
    rows=[{"condition":"s400","case_id":g["case_id"],"state":"error"} for g in gold]
    initial=summarize(gold,rows)
    assert initial["s400"]["answer_accuracy"]=={"numerator":0,"denominator":24,"pending":0,"failed_cases":24,"value":0}
    assert initial["s400"]["refusal_accuracy"]["denominator"]==6
    assert initial["s400"]["errors"]==30 and initial["s400"]["citation_accuracy"]["value"] is None
    assert initial["f400"]["answer_accuracy"]["pending"]==24
    rows[0].update(state="completed",result={"status":"answered","claims":[{"citation_numbers":[1]}]},review=None)
    state=summarize(gold,rows)["s400"]
    assert state["answer_accuracy"]["value"] is None and state["citation_accuracy"]["pending"]==1
    rows[0]["review"]={"answer_grade":"partial","claim_reviews":[{"claim_index":0,"supported":False}]}
    state=summarize(gold,rows)["s400"]
    assert state["answer_accuracy"]["value"]==0 and state["partial_answers"]==1
    assert state["citation_accuracy"]["denominator"]==1 and state["citation_accuracy"]["value"]==0


def test_unverified_retrieval_is_not_a_hit_and_tokens_include_retries():
    gold=dataset().snapshot()[0]
    trace={"retrieval":{"hits":[{"document_id":"fixture","rank":1,"start":13,"end":25}]},
           "sources_verified":False,"attempts":[{"usage":{"total_tokens":12}},{"usage":None}],"context_chars":12}
    assert case_metrics(gold,trace)["hit_at_5"]["all"] is None
    trace["sources_verified"]=True
    metrics=case_metrics(gold,trace)
    assert metrics["hit_at_1"]["all"] is True
    assert metrics["tokens"]["total_tokens"]=={"known_total":12,"known_attempts":1,"unknown_attempts":1}
    assert metrics["tokens"]["prompt_tokens"]["unknown_attempts"]==2


def write_gold(tmp_path,*,mutation=None,manifest_mutation=None,raw_mutation=None):
    folder=tmp_path/"eval";folder.mkdir()
    cases=dataset().snapshot()
    if mutation:
        mutation(cases)
    raw=("\n".join(json.dumps(c,ensure_ascii=False) for c in cases)+"\n").encode()
    if raw_mutation:
        raw=raw_mutation(raw)
    version=hashlib.sha256(raw).hexdigest()
    (folder/"gold.jsonl").write_bytes(raw)
    manifest={"schema_version":"1.0","corpus_version":"fixture-en-v2","gold_version":version,
              "answerable_count":24,"unanswerable_count":6}
    if manifest_mutation:
        manifest_mutation(manifest)
    (folder/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
    return load_settings(environ={},overrides={"data_dir":str(tmp_path),"gold_version":version})


def test_gold_reads_exact_raw_hash_and_frozen_source(tmp_path):
    settings=write_gold(tmp_path)
    gold=load_gold(settings,document_loader)
    assert len(gold.cases)==30 and not gold.synthetic
    assert gold.gold_version==settings.experiment.gold_version
    (tmp_path/"eval/gold.jsonl").write_bytes((tmp_path/"eval/gold.jsonl").read_bytes()+b"\n")
    with pytest.raises(QAError,match="Frozen gold"):
        load_gold(settings,document_loader)


@pytest.mark.parametrize("change",["text","article","duplicate","count","manifest","bom","crlf","no_newline"])
def test_gold_rejects_invalid_freeze_or_evidence(tmp_path,change):
    mutation={"text":lambda c:c[0]["evidence"][0].update(text="C."),
              "article":lambda c:c[0]["evidence"][0].update(article_id="fixture-a001"),
              "duplicate":lambda c:c[1].update(case_id=c[0]["case_id"]),
              "count":lambda c:c.pop()}.get(change)
    raw={"bom":lambda b:b"\xef\xbb\xbf"+b,"crlf":lambda b:b.replace(b"\n",b"\r\n"),"no_newline":lambda b:b[:-1]}.get(change)
    manifest=(lambda m:m.update(corpus_version="wrong")) if change=="manifest" else None
    settings=write_gold(tmp_path,mutation=mutation,manifest_mutation=manifest,raw_mutation=raw)
    with pytest.raises(QAError) as error:
        load_gold(settings,document_loader)
    assert error.value.code=="INVALID_GOLD_DATA"


@pytest.mark.parametrize("change",["reference","boolean","empty_evidence","refusal"])
def test_gold_case_shape_is_strict(change):
    case=dataset().snapshot()[0]
    if change=="reference":case["reference_answer"]=None
    if change=="boolean":case["answerable"]=1
    if change=="empty_evidence":case["evidence"]=[]
    if change=="refusal":case["answerable"]=False
    with pytest.raises(ValueError):GoldCase.model_validate(case)


def test_review_partial_patch_and_question_shape_rules():
    gold=dataset().snapshot()[0]
    output={"status":"answered","claims":[{"citation_numbers":[1]}]}
    first=merge_review(None,ReviewPatch(reviewer="C",answer_grade="correct",claim_reviews=[{"claim_index":0,"supported":True,"reason":"Read source B."}]),gold,output)
    changed=merge_review(first,ReviewPatch(reviewer="C",notes="Checked again"),gold,output)
    assert changed["answer_grade"]=="correct" and changed["claim_reviews"]==first["claim_reviews"]
    cleared=merge_review(first,ReviewPatch(reviewer="C",answer_grade=None),gold,output)
    assert cleared["answer_grade"] is None
    for patch in ({"refusal_correct":True},{"claim_reviews":[{"claim_index":1,"supported":True,"reason":"invalid"}]}):
        with pytest.raises(ValueError):merge_review(None,ReviewPatch(reviewer="C",**patch),gold,output)
    with pytest.raises(ValueError):
        merge_review(None,ReviewPatch(reviewer="C",answer_grade="correct"),gold,{"status":"insufficient","claims":[]})
    with pytest.raises(ValueError):
        merge_review(None,ReviewPatch(reviewer="C",refusal_correct=True),dataset().snapshot()[24],output)
    with pytest.raises(ValueError):ReviewPatch(reviewer="C",claim_reviews=[{"claim_index":0,"supported":True}])
