"""Non-generating integration checks; never download weights or build indexes."""
from importlib import metadata
import os
from pathlib import Path
import re
import shutil
import sys

from app.config import ROOT
from app.data import corpus_loader
from app.evaluation.data import load_gold
from app.qa.errors import QAError


def check_dependencies(requirements_path=None):
    missing,mismatched=[],[]
    paths=[Path(requirements_path)] if requirements_path is not None else [ROOT/"requirements.txt"]
    if requirements_path is None and sys.platform=="linux":paths.append(ROOT/"requirements-linux.txt")
    lines=[line for path in paths for line in path.read_text(encoding="utf-8").splitlines()]
    for line in lines:
        line=line.strip()
        if not line or line.startswith("#"):continue
        match=re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)",line)
        if not match:raise ValueError("Runtime lock must contain exact package pins")
        name,expected=match.groups()
        try:actual=metadata.version(name)
        except metadata.PackageNotFoundError:
            missing.append(name);continue
        # The official CPU wheel adds a local build suffix to the same pinned torch release.
        matches=actual==expected or (name.lower()=="torch" and actual==expected+"+cpu")
        if not matches:mismatched.append({"package":name,"expected":expected,"actual":actual})
    return {"ready":not missing and not mismatched,"missing":missing,"mismatched":mismatched}


def _issue(error,default):
    code=getattr(error,"code",default)
    if not isinstance(code,str):code=default
    return {"ready":False,"code":code,
            "message":error.message if isinstance(error,QAError) else "Check the frozen configuration and required artifacts"}


def integration_status(settings):
    cfg=settings.experiment
    components={"dependencies":check_dependencies()}
    loader=corpus_loader(cfg.data_dir,formal=cfg.mode=="formal")
    try:
        documents=loader(cfg.corpus_version)
        components["corpus"]={"ready":True,"document_count":len(documents),"corpus_version":cfg.corpus_version}
    except QAError as error:
        components["corpus"]=_issue(error,"INVALID_CORPUS_DATA")
    try:
        if not components["corpus"]["ready"]:
            raise QAError("CORPUS_REQUIRED","Validate A's corpus before checking gold",409)
        gold=load_gold(settings,loader)
        components["gold"]={"ready":True,"gold_version":gold.gold_version,
                            "answerable_count":sum(c.answerable for c in gold.cases),
                            "unanswerable_count":sum(not c.answerable for c in gold.cases)}
    except QAError as error:
        components["gold"]=_issue(error,"INVALID_GOLD_DATA")
    embedder=None
    try:
        if not components["dependencies"]["ready"]:
            raise QAError("DEPENDENCIES_REQUIRED","Install the unified runtime lock",409)
        from app.retrieval.embedding import LocalEmbedder
        embedder=LocalEmbedder(settings.retrieval_config()["embedding"])
        identity=embedder.identity()
        components["model_files"]={"ready":True,"model_id":identity["model_id"],"revision":identity["revision"],
                                   "dimension":identity["dimension"],"file_count":len(identity["files"]),"encoder_loaded":False}
    except Exception as error:
        components["model_files"]=_issue(error,"MODEL_CHECK_FAILED")
    service=None
    try:
        if not components["corpus"]["ready"] or not components["model_files"]["ready"]:
            raise QAError("INDEX_PREREQUISITES_MISSING","Validate corpus and model files before checking indexes",409)
        from app.retrieval import RetrievalService
        from app.retrieval.vector_store import validate_store_path
        service=RetrievalService(loader,embedder,settings.retrieval_config())
        # Check the actual derived path before opening a native client, even if no index exists yet.
        docs=service.indexes.documents(cfg.corpus_version)
        from app.retrieval.types import digest
        version=digest(service.indexes.material(cfg.corpus_version,docs))
        validate_store_path(service.indexes.root/"chroma"/version)
        with service.indexes.lock():
            manifest,_=service.indexes.completed(cfg.corpus_version)
        components["indexes"]={"ready":True,"index_version":manifest["index_version"],"conditions":list(cfg.conditions),
                               "chunk_counts":{c:manifest["conditions"][c]["count"] for c in cfg.conditions}}
    except Exception as error:
        components["indexes"]=_issue(error,"INDEX_CHECK_FAILED")
    finally:
        if service is not None:
            try:
                service.close()
            except Exception as error:
                components["indexes"]=_issue(error,"INDEX_CLOSE_FAILED")
    transport_ready=cfg.generation.transport=="httpx" or shutil.which("curl.exe" if os.name=="nt" else "curl") is not None
    components["generation"]={"ready":settings.llm_configured and transport_ready,
                               "configured":settings.llm_configured,"transport":cfg.generation.transport,
                               "transport_available":transport_ready,"connectivity_verified":False}
    qa_ready=all(components[name]["ready"] for name in ("dependencies","corpus","model_files","indexes","generation"))
    evaluation_ready=qa_ready and components["gold"]["ready"]
    return {"schema_version":"1.0","state":"ready" if evaluation_ready else "not_ready","mode":cfg.mode,
            "ready_for_qa":qa_ready,"ready_for_evaluation":evaluation_ready,
            "formal_ready":cfg.mode=="formal" and evaluation_ready,"components":components,
            "configuration":settings.public_snapshot(),"experiment_fingerprint":settings.experiment_fingerprint(),
            "external_model_calls":0,"index_builds":0}
