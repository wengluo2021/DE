"""Validate A's existing frozen corpus and gold without changing either."""
import argparse
import json
import sys

from app.config import load_settings
from app.data.validation import validate_bundle
from app.qa.errors import QAError


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--data-dir")
    parser.add_argument("--corpus-version")
    parser.add_argument("--corpus-only",action="store_true")
    args=parser.parse_args(argv)
    try:
        overrides={}
        if args.data_dir:overrides["data_dir"]=args.data_dir
        if args.corpus_version:overrides["corpus_version"]=args.corpus_version
        settings=load_settings(args.config,overrides=overrides)
        print(json.dumps(validate_bundle(settings,corpus_only=args.corpus_only),ensure_ascii=False))
        return 0
    except QAError as error:
        result={"state":"failed","error":error.as_dict(),"external_model_calls":0}
    except (OSError,ValueError):
        result={"state":"failed","error":{"code":"CONFIGURATION_ERROR","message":"Check the configuration and frozen data paths"},"external_model_calls":0}
    print(json.dumps(result,ensure_ascii=False),file=sys.stderr)
    return 1


if __name__=="__main__":
    raise SystemExit(main())
