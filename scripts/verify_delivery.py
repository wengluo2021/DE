"""Verify a fresh unpacked delivery before running it; standard library only."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath,PureWindowsPath
import re
import sys


def _unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError("Duplicate inventory field")
        result[key]=value
    return result


def verify_delivery(directory):
    root=Path(directory).resolve()
    try:
        manifest_path=root/"DELIVERY-MANIFEST.json"
        if manifest_path.is_symlink():raise ValueError("Manifest must be a regular file")
        manifest=json.loads(manifest_path.read_text(encoding="utf-8"),object_pairs_hook=_unique)
        if manifest["schema_version"]!="1.0" or manifest["kind"] not in {"formal_candidate","synthetic_rehearsal"}:
            raise ValueError("Unknown delivery format")
        for key in ("corpus_version","gold_version","experiment_fingerprint"):
            if not isinstance(manifest[key],str) or not re.fullmatch(r"[a-f0-9]{64}",manifest[key]):
                raise ValueError("Invalid frozen version")
        files=manifest["files"]
        if not isinstance(files,dict) or not files:raise ValueError("Empty file inventory")
        for relative,expected in files.items():
            path=PurePosixPath(relative)
            if (not relative or "\\" in relative or path.is_absolute() or PureWindowsPath(relative).drive
                    or ".." in path.parts or ":" in relative or path.as_posix()!=relative
                    or any(ord(c)<32 for c in relative) or relative=="DELIVERY-MANIFEST.json"):
                raise ValueError("Invalid inventory path")
            if not isinstance(expected,str) or not re.fullmatch(r"[a-f0-9]{64}",expected):
                raise ValueError("Invalid file hash")
            source=root.joinpath(*path.parts)
            if (not source.resolve().is_relative_to(root) or not source.is_file()
                    or any(p.is_symlink() for p in [source,*source.parents] if p.is_relative_to(root))):
                raise ValueError("Missing or escaping inventory file")
            if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:
                raise ValueError("File hash differs")
        actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
        if actual!=set(files)|{"DELIVERY-MANIFEST.json"}:
            raise ValueError("Unexpected files; verify before running the delivery")
        return {"state":"verified","kind":manifest["kind"],"file_count":len(files),
                "corpus_version":manifest["corpus_version"],"gold_version":manifest["gold_version"],
                "official_provenance_verified":False,"external_model_calls":0}
    except (OSError,ValueError,KeyError,TypeError,AttributeError):
        raise ValueError("Delivery inventory, paths or SHA-256 checks failed; preserve and inspect the package") from None


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    args=parser.parse_args(argv)
    try:
        print(json.dumps(verify_delivery(args.directory),ensure_ascii=False));return 0
    except ValueError as error:
        print(json.dumps({"state":"failed","code":"DELIVERY_INTEGRITY_ERROR","message":str(error)}),file=sys.stderr)
        return 1


if __name__=="__main__":raise SystemExit(main())
