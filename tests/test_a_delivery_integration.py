"""Real frozen A delivery: read-only adaptation, source hashes and annex gold."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil

import pytest

from app.config import ROOT, load_settings
from app.data.corpus import load_corpus, read_frozen_json
from app.data.document_view import document_view
from app.data.validation import validate_bundle
from app.evaluation.data import load_gold, validate_cases, source_structures, _a_case
from app.evaluation.metrics import evidence_coverage
from app.qa.errors import QAError
from scripts.prepare_config import prepare_config
from scripts.prepare_delivery import prepare_delivery
from scripts.verify_delivery import verify_delivery


def settings_for(**overrides):
    corpus=read_frozen_json(ROOT/"data/formal_corpus/manifest.json")
    gold=read_frozen_json(ROOT/"data/eval/manifest.json")
    config={"mode":"formal","data_dir":"data/formal_corpus","gold_dir":"data/eval",
            "structure_dir":"data/processed","input_adapter":"eurlex-a-v1",
            "corpus_version":corpus["corpus_version"],"gold_version":gold["gold_version"]}
    config.update(overrides)
    return load_settings(env_file=os.devnull,environ={},api_key="",overrides=config)


def originals():
    cfg=settings_for().experiment
    return load_corpus(cfg.data_dir,cfg.corpus_version,formal=True)


def test_full_a_documents_are_returned_unchanged_and_match_b():
    from app.retrieval.types import formal_loader, digest
    cfg=settings_for().experiment
    docs=originals()
    before=deepcopy(docs)
    assert docs==formal_loader(cfg.data_dir)(cfg.corpus_version)
    assert len(docs)==5 and sum(len(d["articles"]) for d in docs)==121
    assert sum(len(document_view(d).text) for d in docs)==391777
    for doc in docs:
        document_view(doc)
    assert docs==before and digest(docs)==digest(before)


@pytest.mark.parametrize("mutation",["unknown_field","article_alias","article_text","block_text"])
def test_rich_source_projection_rejects_misspellings_or_forged_offsets(mutation):
    doc=deepcopy(originals()[0])
    if mutation=="unknown_field":doc["tittle"]=doc["title"]
    if mutation=="article_alias":doc["articles"][0]["chapter_id"]="wrong"
    if mutation=="article_text":doc["articles"][0]["text"]+="!"
    if mutation=="block_text":doc["articles"][0]["blocks"][0]["text"]+="!"
    with pytest.raises(ValueError):document_view(doc)


def test_all_30_cases_preserve_questions_references_and_42_source_intervals():
    settings=settings_for()
    docs=originals()
    before=(ROOT/"data/eval/gold.jsonl").read_bytes()
    dataset=load_gold(settings,lambda _:docs)
    assert len(dataset.cases)==30 and sum(c.answerable for c in dataset.cases)==24
    assert sum(len(c.evidence) for c in dataset.cases)==42
    rows=[json.loads(line) for line in before.decode().splitlines()]
    for case,row in zip(dataset.cases,rows):
        assert case.question==row["question"] and case.key_facts==row["key_facts"]
        assert (case.reference_answer if case.answerable else case.refusal_reference)==row["reference_answer"]
        for evidence,item in zip(case.evidence,row["evidence"]):
            assert evidence.text==item["quote"]
            assert (evidence.document_id,evidence.start,evidence.end)==(item["document_id"],item["start"],item["end"])
    annex=next(e for c in dataset.cases for e in c.evidence if e.structure_id)
    assert annex.article_id is None and annex.structure_id=="eu_unfair_practices_2005_29:annex:I"
    hit={"document_id":annex.document_id,"rank":1,"start":annex.start,"end":annex.end}
    assert evidence_coverage([hit],[annex.model_dump()],5)=={"any":True,"all":True}
    with pytest.raises(KeyError):validate_cases(dataset.cases,[document_view(d) for d in docs])
    validate_cases(dataset.cases,[document_view(d) for d in docs],source_structures(settings,docs))
    assert (ROOT/"data/eval/gold.jsonl").read_bytes()==before


def test_annex_structure_tampering_fails_before_evaluation(tmp_path):
    target=tmp_path/"accepted"
    shutil.copytree(ROOT/"data/processed",target)
    doc=next(d for d in originals() if d["document_id"]=="eu_unfair_practices_2005_29")
    path=target/(doc["document_id"]+".json")
    path.write_bytes(path.read_bytes()+b" ")
    with pytest.raises(QAError) as error:
        load_gold(settings_for(structure_dir=str(target)),lambda _:originals())
    assert error.value.code=="INVALID_GOLD_DATA"


@pytest.mark.parametrize("mutation",["different_corpus","unknown_field","bool_coercion","both_ids"])
def test_a_gold_adapter_rejects_invalid_raw_boundaries(mutation):
    row=json.loads((ROOT/"data/eval/gold.jsonl").read_text(encoding="utf-8").splitlines()[0])
    version=row["corpus_version"]
    if mutation=="different_corpus":row["corpus_version"]="0"*64
    if mutation=="unknown_field":row["answers"]=[]
    if mutation=="bool_coercion":row["should_refuse"]=0
    if mutation=="both_ids":row["evidence"][0]["structure_id"]="forged-annex"
    with pytest.raises(ValueError):_a_case(row,version)


def test_formal_configuration_and_portable_package_keep_exact_inputs(tmp_path):
    config=tmp_path/"formal.json"
    report=prepare_config(ROOT/"data/formal_corpus",config,transport="curl")
    assert report["document_count"]==5 and report["answerable_count"]==24
    settings=load_settings(config,env_file=os.devnull,environ={})
    assert settings.experiment.input_adapter=="eurlex-a-v1"
    staged=tmp_path/"delivery"
    result=prepare_delivery(staged,config_path=config)
    assert result["kind"]=="formal_candidate" and result["state"]=="verified"
    moved=load_settings("config/experiment.delivery.json",project_root=staged,env_file=os.devnull,environ={})
    assert moved.experiment_fingerprint()==settings.experiment_fingerprint()
    assert validate_bundle(moved)["unanswerable_count"]==6
    for doc in originals():
        identifier=doc["document_id"]
        for relative in (f"data/formal_corpus/processed/{identifier}.json",f"data/processed/{identifier}.json"):
            assert (staged/relative).read_bytes()==(ROOT/relative).read_bytes()
    assert verify_delivery(staged)["state"]=="verified"


def test_legacy_fingerprint_and_adapter_identity_are_stable():
    canonical=load_settings(env_file=os.devnull,environ={},api_key="")
    data=canonical.public_snapshot()
    for key in ("data_dir","gold_dir","structure_dir","input_adapter"):data.pop(key)
    data["embedding"].pop("model_dir")
    data["generation"].pop("prompt_path")
    data["generation"].pop("api_key_configured")
    expected=hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    assert canonical.experiment_fingerprint()==expected
    settings=settings_for()
    moved=settings_for(gold_dir="elsewhere/eval",structure_dir="elsewhere/processed")
    assert settings.experiment_fingerprint()==moved.experiment_fingerprint()
    assert settings.experiment_fingerprint()!=settings_for(input_adapter="canonical-v1").experiment_fingerprint()
