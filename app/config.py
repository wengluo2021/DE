"""Lightweight, explicit experiment configuration; no retrieval/model imports or network."""
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Literal, Mapping
from urllib.parse import urlsplit

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictBool, StrictFloat, StrictInt, ValidationError, field_validator, model_validator

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ("f400", "s400", "f800", "s800")


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class EmbeddingSettings(ConfigModel):
    model_id: str = Field(min_length=1)
    revision: str
    model_dir: Path
    device: Literal["cpu"] = "cpu"
    dimension: StrictInt = Field(gt=0)
    normalize: StrictBool
    query_prefix: str
    document_prefix: str = ""
    max_input_tokens: StrictInt = Field(gt=0)
    pooling: Literal["cls"] = "cls"
    batch_size: StrictInt = Field(gt=0)
    cpu_threads: StrictInt = Field(gt=0)

    @field_validator("revision")
    @classmethod
    def immutable_revision(cls, value):
        if not re.fullmatch(r"[a-f0-9]{40}", value):
            raise ValueError("embedding revision must be an immutable lowercase commit SHA")
        return value


class RetrievalSettings(ConfigModel):
    metric: Literal["cosine"] = "cosine"
    chunker_version: Literal["structure-offset-v2"] = "structure-offset-v2"


class GenerationSettings(ConfigModel):
    provider: str = Field(default="openai-compatible", min_length=1)
    base_url: str | None = None
    model: str | None = None
    temperature: StrictFloat | StrictInt = Field(default=0, ge=0, le=2)
    max_tokens: StrictInt = Field(default=1024, gt=0)
    timeout_seconds: StrictInt = Field(default=60, gt=0, le=300)
    max_attempts: StrictInt = Field(default=2, ge=1, le=2)
    prompt_path: Path
    json_mode: StrictBool = True
    transport: Literal["httpx", "curl"] = "httpx"
    seed: StrictInt | None = None

    @field_validator("base_url")
    @classmethod
    def safe_base_url(cls, value):
        if value is None:
            return None
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("LLM base URL must not contain control characters")
        url = urlsplit(value)
        if url.port is not None and not 1 <= url.port <= 65535:
            raise ValueError("LLM base URL port is out of range")
        local = url.hostname in {"127.0.0.1", "localhost", "::1"}
        if (not url.hostname or url.username or url.password or url.query or url.fragment
                or not (url.scheme == "https" or (local and url.scheme == "http"))):
            raise ValueError("LLM base URL must be HTTPS without credentials/query (HTTP allowed for loopback)")
        return value.rstrip("/")

    @field_validator("model")
    @classmethod
    def nonblank_model(cls, value):
        if value is not None and not value.strip():
            raise ValueError("model must not be blank")
        return value


class ExperimentSettings(ConfigModel):
    schema_version: Literal["1.0"] = "1.0"
    mode: Literal["development", "formal"] = "development"
    corpus_version: str = Field(min_length=1)
    gold_version: str | None = None
    conditions: tuple[str, ...]
    top_k: Literal[5] = 5
    data_dir: Path
    embedding: EmbeddingSettings
    retrieval: RetrievalSettings
    generation: GenerationSettings

    @field_validator("top_k", mode="before")
    @classmethod
    def strict_top_k(cls, value):
        if type(value) is not int or value != 5:
            raise ValueError("top_k must be the integer 5")
        return value

    @field_validator("conditions")
    @classmethod
    def fixed_conditions(cls, value):
        if value != CONDITIONS:
            raise ValueError("all four conditions must be in the fixed experiment order")
        return value

    @model_validator(mode="after")
    def formal_versions(self):
        if self.mode == "formal" and any(not v or not re.fullmatch(r"[a-f0-9]{64}", v)
                                         for v in (self.corpus_version, self.gold_version)):
            raise ValueError("formal mode requires frozen corpus and gold SHA-256 versions")
        return self


@dataclass(frozen=True)
class Settings:
    experiment: ExperimentSettings
    _api_key: SecretStr = field(repr=False)
    prompt_sha256: str

    @property
    def llm_configured(self):
        g = self.experiment.generation
        return bool(g.base_url and g.model and self._api_key.get_secret_value())

    def api_key(self):
        """Only a transport adapter should access this; never serialize the return value."""
        return self._api_key.get_secret_value()

    def public_snapshot(self):
        result = self.experiment.model_dump(mode="json")
        result["generation"]["prompt_sha256"] = self.prompt_sha256
        result["generation"]["api_key_configured"] = bool(self._api_key.get_secret_value())
        return result

    def experiment_fingerprint(self):
        result = self.public_snapshot()
        result.pop("data_dir")
        result["embedding"].pop("model_dir")
        result["generation"].pop("prompt_path")
        result["generation"].pop("api_key_configured")
        encoded = json.dumps(result, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def retrieval_config(self):
        """A fresh dict with all fields B expects; never imports B's heavy package."""
        data = self.experiment.model_dump(mode="json")
        return {k: deepcopy(data[k]) for k in ("schema_version", "corpus_version", "conditions",
                                               "top_k", "data_dir", "embedding", "retrieval")}


def _merge(base, extra):
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = deepcopy(value)


def _path(value, root):
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError("configuration paths must not be empty")
    path = Path(value)
    return str((path if path.is_absolute() else root / path).resolve())


def load_settings(config_path=None, *, project_root=ROOT, env_file=None,
                  environ: Mapping[str, str] | None = None, overrides=None,
                  api_key: str | None = None):
    """Explicit > process env > explicit/default dotenv > JSON, without environment mutation.

    api_key=None means no explicit override; api_key='' explicitly clears a credential.
    This loader never searches the other course, WSL, or the parent private directory.
    """
    root = Path(project_root).resolve()
    path = Path(_path(config_path if config_path is not None else "config/experiment.json", root))
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("experiment configuration must be a JSON object")
    data = deepcopy(data)
    dot_path = Path(_path(env_file if env_file is not None else ".env", root))
    env = dict(dotenv_values(dot_path, interpolate=False)) if dot_path.is_file() else {}
    env.update(dict(os.environ if environ is None else environ))
    for name, section, key in (("DERAG_DATA_DIR", None, "data_dir"),
                               ("DERAG_MODEL_DIR", "embedding", "model_dir"),
                               ("LLM_BASE_URL", "generation", "base_url"),
                               ("LLM_MODEL", "generation", "model")):
        if name in env:
            target = data if section is None else data.setdefault(section, {})
            target[key] = env[name] if env[name] else (None if key in {"base_url", "model"} else "")
    if overrides is not None:
        _merge(data, overrides)
    # Resolve paths before model validation and keep errors free of input values.
    data["data_dir"] = _path(data.get("data_dir", "data"), root)
    data.setdefault("embedding", {})["model_dir"] = _path(data.get("embedding", {}).get("model_dir", "models/embedding"), root)
    data.setdefault("generation", {})["prompt_path"] = _path(data.get("generation", {}).get("prompt_path", "app/qa/prompts/answer.txt"), root)
    try:
        experiment = ExperimentSettings.model_validate(data)
    except ValidationError as exc:
        locations = [".".join(str(x) for x in e["loc"]) + ":" + e["type"]
                     for e in exc.errors(include_input=False, include_context=False)]
        raise ValueError("Invalid experiment configuration: " + "; ".join(locations)) from None
    prompt = experiment.generation.prompt_path
    if not prompt.is_file():
        raise ValueError("configured prompt file is missing")
    secret = env.get("LLM_API_KEY", "") if api_key is None else api_key
    if secret is None:
        secret = ""
    if not isinstance(secret, str) or "\n" in secret or "\r" in secret:
        raise ValueError("LLM credential must be a single-line string")
    if not secret.strip():
        secret = ""
    elif any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in secret):
        raise ValueError("LLM credential must not contain whitespace or control characters")
    return Settings(experiment, SecretStr(secret), hashlib.sha256(prompt.read_bytes()).hexdigest())
