"""Stage a new portable, hashed delivery from validated inputs; never call a model."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from app.config import ROOT,load_settings
from app.data.corpus import frozen_path,read_frozen_json
from app.data.validation import validate_bundle
from app.qa.errors import QAError
from scripts.verify_delivery import verify_delivery

SOURCE_TREES=("app","scripts","tests","docs")
SOURCE_FILES=("Dockerfile",".dockerignore",".env.example","requirements.txt","requirements-dev.txt","requirements-linux.txt",
              "requirements-api.txt","requirements-b.txt","requirements-b-dev.txt","requirements-c.txt","requirements-c-dev.txt","README.md",
              "项目设计.md","开发文档.md","B开发文档.md","B测试.md","config/experiment.json","config/retrieval.example.json")


def _source_files(root):
    for relative in SOURCE_FILES:
        path=root/relative
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise QAError("DELIVERY_SOURCE_MISSING","Required public source files are missing",409)
        yield relative,path
    for tree in SOURCE_TREES:
        if not (root/tree).is_dir() or (root/tree).is_symlink() or not (root/tree).resolve().is_relative_to(root):
            raise QAError("DELIVERY_SOURCE_MISSING","Required source directories must exist without symbolic links",409)
        for path in sorted((root/tree).rglob("*")):
            relative=path.relative_to(root)
            if (any(part.startswith('.') or part=="__pycache__" for part in relative.parts)
                    or path.suffix in {".pyc",".pyo",".env",".sqlite3",".key",".pem"}
                    or ".env." in path.name):continue
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise QAError("DELIVERY_SOURCE_LINK","Delivery source must not contain symbolic links",409)
            if path.is_file():yield relative.as_posix(),path


def prepare_delivery(output,*,config_path=None,synthetic=False,project_root=ROOT):
    root=Path(project_root).resolve()
    destination=Path(output).resolve()
    if destination.exists():
        raise QAError("OUTPUT_EXISTS","Choose a new delivery directory; existing output is preserved",409)
    if destination==root or any(destination.is_relative_to(root/tree) for tree in SOURCE_TREES+("config","data","models",".git")):
        raise QAError("INVALID_DELIVERY_PATH","Choose output outside source, data and model directories",409)
    # os.devnull explicitly suppresses dotenv; no process credentials enter the snapshot.
    settings=load_settings(config_path,project_root=root,env_file=os.devnull,environ={},api_key="")
    cfg=settings.experiment
    if (synthetic and cfg.mode!="development") or (not synthetic and cfg.mode!="formal"):
        raise QAError("DELIVERY_MODE_MISMATCH","Formal delivery requires formal configuration; synthetic rehearsal requires development mode",409)
    validation=validate_bundle(settings)
    manifest=read_frozen_json(cfg.data_dir/"manifest.json")
    if not synthetic:
        marked="synthetic" in manifest["parser_version"].lower()
        for entry in manifest["documents"]:
            doc=read_frozen_json(frozen_path(cfg.data_dir,entry["processed_path"]))
            marked=marked or "synthetic" in doc["title"].lower()
        if marked:
            raise QAError("SYNTHETIC_DELIVERY_FORBIDDEN","Marked synthetic input cannot become a formal delivery",409)
    sources=dict(_source_files(root))
    inputs={"manifest.json":cfg.data_dir/"manifest.json","eval/manifest.json":cfg.data_dir/"eval/manifest.json",
            "eval/gold.jsonl":cfg.data_dir/"eval/gold.jsonl"}
    for entry in manifest["documents"]:
        for key in ("raw_path","processed_path"):
            path=frozen_path(cfg.data_dir,entry[key])
            relative=path.relative_to(cfg.data_dir.resolve()).as_posix()
            if not relative.startswith(("raw/","processed/")):
                raise QAError("INVALID_DELIVERY_LAYOUT","Snapshots must use raw/ and processed/ for portable delivery",409)
            inputs[relative]=path
    for relative,path in inputs.items():sources["data/"+relative]=path
    # Frozen input bytes are copied exactly; only the new portable configuration is serialized.
    payload={relative:path.read_bytes() for relative,path in sources.items()}
    portable=cfg.model_dump(mode="json")
    portable["data_dir"]="data"
    portable["embedding"]["model_dir"]="models/embedding"
    portable["generation"]["prompt_path"]="config/prompt.delivery.txt"
    payload["config/prompt.delivery.txt"]=cfg.generation.prompt_path.read_bytes()
    payload["config/experiment.delivery.json"]=(json.dumps(portable,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    destination.mkdir(parents=True,exist_ok=False)
    for relative,content in payload.items():
        target=destination/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(content)
    staged=load_settings("config/experiment.delivery.json",project_root=destination,env_file=os.devnull,environ={},api_key="")
    validate_bundle(staged)
    if settings.experiment_fingerprint()!=staged.experiment_fingerprint():
        raise QAError("DELIVERY_CONFIGURATION_CHANGED","Portable configuration changed the experiment fingerprint",409)
    inventory={"schema_version":"1.0","kind":"synthetic_rehearsal" if synthetic else "formal_candidate",
               "corpus_version":cfg.corpus_version,"gold_version":cfg.gold_version,
               "experiment_fingerprint":settings.experiment_fingerprint(),"configuration":"config/experiment.delivery.json",
               "files":{p:hashlib.sha256(b).hexdigest() for p,b in sorted(payload.items())},
               "validation":validation,"official_provenance_verified":False,
               "model_weights_included":False,"runtime_databases_or_indexes_included":False,
               "container_built":False,"external_model_calls":0}
    (destination/"DELIVERY-MANIFEST.json").write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    result=verify_delivery(destination)
    return dict(result,output=str(destination),experiment_fingerprint=inventory["experiment_fingerprint"],
                model_weights_included=False,container_built=False)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--synthetic",action="store_true",help="Explicit development rehearsal; never a formal package")
    args=parser.parse_args(argv)
    try:
        print(json.dumps(prepare_delivery(args.output,config_path=args.config,synthetic=args.synthetic),ensure_ascii=False));return 0
    except QAError as error:
        result=error.as_dict()
    except (OSError,ValueError):
        result={"code":"DELIVERY_PREPARATION_FAILED","message":"Check configuration, inputs and output; incomplete output is preserved for inspection"}
    print(json.dumps({"state":"failed","error":result,"external_model_calls":0}),file=sys.stderr);return 1


if __name__=="__main__":raise SystemExit(main())
