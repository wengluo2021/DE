"""Check dependencies, A data, model files, B indexes and generation configuration."""
import argparse
import json
from pathlib import Path
import sys

from app.config import load_settings
from app.integration import integration_status


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--env-file")
    parser.add_argument("--output",type=Path,help="Save to a new evidence file; existing files are preserved")
    args=parser.parse_args(argv)
    if args.output and args.output.exists():
        print("OUTPUT_EXISTS: Choose a new report filename",file=sys.stderr);return 1
    try:
        result=integration_status(load_settings(args.config,env_file=args.env_file))
        text=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            with args.output.open("x",encoding="utf-8",newline="\n") as stream:stream.write(text)
        print(text)
        return 0 if result["state"]=="ready" else 1
    except (OSError,ValueError):
        print("PREFLIGHT_ERROR: Check the configuration, runtime lock and report directory",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
