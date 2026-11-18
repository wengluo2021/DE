"""Validate frozen bytes and shared contracts without loading B/Chroma/models."""
import hashlib
import json
from pathlib import Path,PurePosixPath,PureWindowsPath
import re

from app.contracts import Document
from app.qa.errors import QAError


def canonical_hash(value):
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    value={}
    for key,item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON key")
        value[key]=item
    return value


def read_frozen_json(path):
    raw=path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError("JSON must use UTF-8 without BOM and LF")
    value=json.loads(raw.decode("utf-8"),object_pairs_hook=_unique)
    if not isinstance(value,dict):
        raise ValueError("Expected a JSON object")
    return value


def frozen_path(data_dir,relative):
    if (not isinstance(relative,str) or not relative.strip() or "\\" in relative
            or any(ord(c)<32 for c in relative)):
        raise ValueError("Expected a portable relative snapshot path")
    posix,windows=PurePosixPath(relative),PureWindowsPath(relative)
    if windows.drive or posix.is_absolute() or ".." in posix.parts:
        raise ValueError("Snapshot path must stay inside the data directory")
    parts=posix.parts[1:] if posix.parts and posix.parts[0]=="data" else posix.parts
    resolved=(data_dir/Path(*parts)).resolve()
    if not resolved.is_relative_to(data_dir.resolve()) or not resolved.is_file():
        raise ValueError("Missing or escaping snapshot")
    return resolved


def _sha(value):
    if not isinstance(value,str) or re.fullmatch(r"[a-f0-9]{64}",value) is None:
        raise ValueError("Expected a frozen SHA-256")
    return value


def load_corpus(data_dir,corpus_version,*,formal=False):
    """Return exact validated Document dictionaries; never normalize or repair A."""
    root=Path(data_dir).resolve()
    if not (root/"manifest.json").is_file():
        raise QAError("CORPUS_NOT_CONFIGURED","A's frozen corpus manifest is missing",409)
    try:
        manifest=read_frozen_json(root/"manifest.json")
        if (manifest["schema_version"]!="1.0" or _sha(manifest["corpus_version"])!=corpus_version
                or not isinstance(manifest["parser_version"],str) or not manifest["parser_version"].strip()):
            raise ValueError("Corpus header or version mismatch")
        entries=manifest["documents"]
        if not isinstance(entries,list) or not entries or (formal and not 5<=len(entries)<=8):
            raise ValueError("Formal corpus must contain the team's 5-8 documents")
        documents,materials,seen=[],[],set()
        for entry in entries:
            if entry["document_id"] in seen:
                raise ValueError("Repeated document ID")
            seen.add(entry["document_id"])
            files={}
            for key in ("raw","processed"):
                path=frozen_path(root,entry[key+"_path"])
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                if digest!=_sha(entry[key+"_sha256"]):
                    raise ValueError("Frozen file hash differs")
                files[key]=path
            data=read_frozen_json(files["processed"])
            doc=Document.model_validate(data)
            if (doc.document_id!=entry["document_id"] or doc.corpus_version!=corpus_version
                    or doc.raw_path!=entry["raw_path"] or doc.raw_sha256!=entry["raw_sha256"]
                    or hashlib.sha256(doc.text.encode("utf-8")).hexdigest()!=_sha(entry["text_sha256"])
                    or canonical_hash(data["articles"])!=_sha(entry["structure_sha256"])):
                raise ValueError("Frozen source metadata, text or structure differs")
            material={key:data[key] for key in ("document_id","title","issuer","source_url","published_at","effective_at","raw_sha256")}
            material.update(text_sha256=entry["text_sha256"],structure_sha256=entry["structure_sha256"])
            materials.append(material);documents.append(data)
        expected=canonical_hash({"parser_version":manifest["parser_version"],"documents":sorted(materials,key=lambda d:d["document_id"])})
        if expected!=corpus_version:
            raise ValueError("Corpus version material differs")
        return sorted(documents,key=lambda d:d["document_id"])
    except (OSError,ValueError,KeyError,TypeError,AttributeError):
        raise QAError("INVALID_CORPUS_DATA","Frozen corpus files, hashes or document contracts failed validation",409) from None


def corpus_loader(data_dir,*,formal=False):
    return lambda version:load_corpus(data_dir,version,formal=formal)
