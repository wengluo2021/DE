"""Create a new validated formal configuration from A's manifests; never edit A."""
import argparse
import json
from pathlib import Path
import sys

from app.config import ROOT,load_settings
from app.data.corpus import read_frozen_json
from app.data.validation import validate_bundle
from app.qa.errors import QAError


def prepare_config(data_dir,output,*,base_config=None,transport=None,gold_dir=None,structure_dir=None):
    directory=Path(data_dir)
    directory=(directory if directory.is_absolute() else ROOT/directory).resolve()
    destination=Path(output)
    destination=destination if destination.is_absolute() else ROOT/destination
    if destination.exists():
        raise QAError("OUTPUT_EXISTS","Choose a new configuration filename; existing configurations are preserved",409)
    try:
        corpus=read_frozen_json(directory/"manifest.json")
        a_export=corpus.get("kind")=="formal_corpus"
        def directory_path(value,default):
            path=Path(value) if value is not None else default
            return (path if path.is_absolute() else ROOT/path).resolve()
        gold_root=directory_path(gold_dir,directory.parent/"eval" if a_export else directory/"eval")
        structure_root=directory_path(structure_dir,directory.parent/"processed") if a_export else None
        gold=read_frozen_json(gold_root/"manifest.json")
        overrides={"mode":"formal","data_dir":str(directory),"corpus_version":corpus["corpus_version"],
                   "gold_version":gold["gold_version"],"gold_dir":str(gold_root),
                   "structure_dir":str(structure_root) if structure_root else None,
                   "input_adapter":"eurlex-a-v1" if a_export else "canonical-v1"}
        if transport:overrides["generation"]={"transport":transport}
        # No key is copied into the generated experiment file.
        settings=load_settings(base_config,environ={},overrides=overrides,api_key="")
        report=validate_bundle(settings)
    except QAError:
        raise
    except (OSError,ValueError,KeyError,TypeError):
        raise QAError("FORMAL_INPUTS_NOT_READY","Supply A's complete frozen manifests, corpus and 24/6 gold before preparing formal configuration",409) from None
    content=settings.experiment.model_dump(mode="json")
    for section,key in ((None,"data_dir"),(None,"gold_dir"),(None,"structure_dir"),
                        ("embedding","model_dir"),("generation","prompt_path")):
        target=content if section is None else content[section]
        if target[key] is None:continue
        path=Path(target[key])
        target[key]=path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open("x",encoding="utf-8",newline="\n") as stream:
        stream.write(json.dumps(content,ensure_ascii=False,indent=2)+"\n")
    return dict(report,output=str(destination))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir",default="data")
    parser.add_argument("--output",default="config/experiment.formal.json")
    parser.add_argument("--base-config")
    parser.add_argument("--transport",choices=("httpx","curl"))
    parser.add_argument("--gold-dir")
    parser.add_argument("--structure-dir")
    args=parser.parse_args(argv)
    try:
        print(json.dumps(prepare_config(args.data_dir,args.output,base_config=args.base_config,transport=args.transport,
                                       gold_dir=args.gold_dir,structure_dir=args.structure_dir),ensure_ascii=False))
        return 0
    except QAError as error:
        result=error.as_dict()
    except OSError:
        result={"code":"CONFIGURATION_WRITE_FAILED","message":"Could not save the new configuration"}
    print(json.dumps({"state":"failed","error":result,"external_model_calls":0},ensure_ascii=False),file=sys.stderr)
    return 1


if __name__=="__main__":
    raise SystemExit(main())
