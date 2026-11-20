"""SYNTHETIC hashed bundles for contract tests; never create official A data."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from app.config import ROOT
from app.data.corpus import canonical_hash
from tests.support.evaluation_fixtures import dataset


def _json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")


def write_bundle(directory,*,count=5,omit_optional=False,source_documents=None,with_gold=True):
    root=Path(directory);docs=[];entries=[];materials=[]
    base=json.loads((ROOT/"tests/fixtures/b/document.json").read_text(encoding="utf-8"))
    sources=source_documents if source_documents is not None else [base]*count
    for index,source in enumerate(sources):
        doc=deepcopy(source)
        doc.update(document_id=f"synthetic-doc-{index}",title=f"SYNTHETIC integration document {index}: {source['title']}",
                   source_url=f"https://example.org/synthetic/{index}",raw_path=f"data/raw/synthetic-{index}.txt")
        if omit_optional:
            for article in doc["articles"]:
                article.pop("chapter");article.pop("section")
        raw=root/f"raw/synthetic-{index}.txt";raw.parent.mkdir(parents=True,exist_ok=True)
        raw.write_bytes(doc["text"].encode("utf-8"))
        doc["raw_sha256"]=hashlib.sha256(raw.read_bytes()).hexdigest()
        entry={"document_id":doc["document_id"],"raw_path":doc["raw_path"],"raw_sha256":doc["raw_sha256"],
               "processed_path":f"data/processed/synthetic-{index}.json","text_sha256":doc["raw_sha256"],
               "structure_sha256":canonical_hash(doc["articles"])}
        material={key:doc[key] for key in ("document_id","title","issuer","source_url","published_at","effective_at","raw_sha256")}
        material.update(text_sha256=entry["text_sha256"],structure_sha256=entry["structure_sha256"])
        docs.append(doc);entries.append(entry);materials.append(material)
    version=canonical_hash({"parser_version":"SYNTHETIC-test-parser-v1","documents":sorted(materials,key=lambda d:d["document_id"])})
    for index,(doc,entry) in enumerate(zip(docs,entries)):
        doc["corpus_version"]=version
        path=root/f"processed/synthetic-{index}.json";_json(path,doc)
        entry["processed_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
    manifest={"schema_version":"1.0","corpus_version":version,"parser_version":"SYNTHETIC-test-parser-v1","documents":entries}
    _json(root/"manifest.json",manifest)
    if not with_gold:
        return {"corpus_version":version,"gold_version":None,"documents":docs,"cases":[],"manifest":manifest}
    cases=dataset().snapshot()
    for case in cases:
        for evidence in case["evidence"]:evidence["document_id"]=docs[0]["document_id"]
    raw=("".join(json.dumps(case,ensure_ascii=False,sort_keys=True)+"\n" for case in cases)).encode()
    path=root/"eval/gold.jsonl";path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    gold_version=hashlib.sha256(raw).hexdigest()
    _json(root/"eval/manifest.json",{"schema_version":"1.0","corpus_version":version,"gold_version":gold_version,
                                    "answerable_count":24,"unanswerable_count":6})
    return {"corpus_version":version,"gold_version":gold_version,"documents":docs,"cases":cases,"manifest":manifest}
