"""B 的统一字段、配置和数据校验；不依赖 A/C 尚未集成的代码，也不加载模型。"""
from pathlib import Path
from typing import Callable, Protocol, TypedDict
import hashlib
import json
import os

from .errors import RetrievalError

# 根据源码位置定位 DERag 根目录，相对路径不依赖终端从哪个目录启动。
ROOT = Path(__file__).resolve().parents[2]
# 两种算法 × 两个字符上限；四组共用后续编码、向量库和检索流程。
CONDITIONS = {"f400": ("fixed", 400), "s400": ("structured", 400),
              "f800": ("fixed", 800), "s800": ("structured", 800)}
FIXTURE_CORPUS_VERSION = "fixture-en-v2"
CHUNKER_VERSION = "structure-offset-v2"


class Chunk(TypedDict):
    """原文块的字段约定；start/end 是 Python 字符下标，text 必须等于原文切片。"""
    chunk_id: str
    corpus_version: str
    condition: str
    boundary_method: str
    target_chars: int
    document_id: str
    article_ids: list[str]
    start: int
    end: int
    text: str


class SearchHit(TypedDict):
    """交给 C 的检索证据：块位置加来源信息；rank 从 1 开始，score 越高越相关。"""
    rank: int
    score: float
    chunk_id: str
    corpus_version: str
    condition: str
    document_id: str
    article_ids: list[str]
    start: int
    end: int
    text: str
    title: str
    source_url: str
    article_labels: list[str]


IndexManifest = dict
DocumentLoader = Callable[[str], list[dict]]


class Embedder(Protocol):
    """编码器接口；测试实现和真实模型遵循同一签名，便于独立开发与替换。"""
    def identity(self) -> dict: ...
    def encode(self, texts: list[str], *, query: bool = False,
               ids: list[str] | None = None) -> list[list[float]]: ...


def canonical(value) -> str:
    """固定 JSON 的键顺序与分隔符，让相同配置在不同机器上得到同一哈希。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value) -> str:
    """对规范 JSON 求 SHA-256，用于语料、条文结构和索引版本。"""
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    """分批读取文件计算哈希，避免把数 GB 模型权重一次性读入内存。"""
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value):
    """先写临时文件再替换，减少读到只写了一半的 JSON 的风险。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    tmp.replace(path)


def load_config(path=None, *, model_dir=None, data_dir=None) -> dict:
    """加载独立配置；显式参数优先于环境变量，环境变量优先于文件中的路径。"""
    config_path = Path(path or os.environ.get("DERAG_RETRIEVAL_CONFIG", ROOT / "config/retrieval.example.json"))
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["conditions"] != list(CONDITIONS) or config["retrieval"]["metric"] != "cosine":
        raise RetrievalError("INVALID_REQUEST", "Expected all four conditions and cosine metric", 422)
    if config["retrieval"]["chunker_version"] != CHUNKER_VERSION:
        raise RetrievalError("VERSION_MISMATCH", "Configured chunker does not match implementation")
    for key, override in (("model_dir", model_dir or os.environ.get("DERAG_MODEL_DIR")),):
        value = Path(override or config["embedding"][key])
        config["embedding"][key] = str(value if value.is_absolute() else ROOT / value)
    value = Path(data_dir or os.environ.get("DERAG_DATA_DIR") or config["data_dir"])
    config["data_dir"] = str(value if value.is_absolute() else ROOT / value)
    return config


def validate_documents(documents: list[dict], corpus_version: str):
    """检查版本、文档 ID、正文换行和条文区间；发现不一致直接拒绝，不自行修复。"""
    seen = set()
    for doc in documents:
        if doc["corpus_version"] != corpus_version:
            raise RetrievalError("VERSION_MISMATCH", "Document corpus differs from request")
        if doc["document_id"] in seen:
            raise RetrievalError("SOURCE_MISMATCH", "Duplicate document_id")
        seen.add(doc["document_id"])
        text = doc["text"]
        if not isinstance(text, str) or "\r" in text or text.startswith("\ufeff"):
            raise RetrievalError("SOURCE_MISMATCH", "Expected frozen LF text without BOM")
        previous = 0
        article_ids = set()
        for article in doc["articles"]:
            start, end = article["start"], article["end"]
            # previous 是上一条的结束位置：允许条间空白，但不允许乱序或重叠。
            if (type(start) is not int or type(end) is not int or
                    not 0 <= previous <= start < end <= len(text) or
                    article["article_id"] in article_ids):
                raise RetrievalError("SOURCE_MISMATCH", "Invalid/overlapping article offsets or IDs")
            previous = end
            article_ids.add(article["article_id"])


def fixture_loader(corpus_version: str) -> list[dict]:
    """读取 B 自带的短样例和三个主题长样例；全部为合成数据，不是官方法规。"""
    documents = [json.loads((ROOT / "tests/fixtures/b/document.json").read_text(encoding="utf-8"))]
    documents += json.loads((ROOT / "tests/fixtures/b/long_documents.json").read_text(encoding="utf-8"))
    validate_documents(documents, corpus_version)
    return documents


def formal_loader(data_dir: Path) -> DocumentLoader:
    """返回正式数据加载函数；使用前核对 A 的原始、处理、正文、结构和语料哈希。"""
    def load(corpus_version):
        manifest_path = data_dir / "manifest.json"
        if not manifest_path.exists():
            raise RetrievalError("NOT_FOUND", f"Missing A corpus manifest: {manifest_path}", 404)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["corpus_version"] != corpus_version:
            raise RetrievalError("VERSION_MISMATCH", "Requested corpus differs from A manifest")
        documents, materials = [], []
        def safe_file(relative):
            # A 保存的是相对路径；data/... 也支持映射到 DERAG_DATA_DIR 指定的挂载目录。
            # 禁止绝对路径、.. 和解析后越界，防止读取数据目录以外的文件。
            rel = Path(relative)
            if rel.is_absolute() or ".." in rel.parts:
                raise RetrievalError("SOURCE_MISMATCH", "Corpus paths must be relative")
            result = (data_dir / Path(*rel.parts[1:]) if rel.parts and rel.parts[0] == "data" else data_dir / rel).resolve()
            if not result.is_relative_to(data_dir.resolve()):
                raise RetrievalError("SOURCE_MISMATCH", "Corpus path escapes data directory")
            return result
        for entry in manifest["documents"]:
            for key in ("raw", "processed"):
                path = safe_file(entry[f"{key}_path"])
                if not path.is_file() or file_hash(path) != entry[f"{key}_sha256"]:
                    raise RetrievalError("SOURCE_MISMATCH", f"Invalid {key} snapshot: {entry['document_id']}")
            doc = json.loads(safe_file(entry["processed_path"]).read_text(encoding="utf-8"))
            # 完整文件哈希与正文/条文结构分别校验；改条文位置也必须改变语料版本。
            if (doc["document_id"] != entry["document_id"] or
                doc["raw_sha256"] != entry["raw_sha256"] or
                doc["raw_path"] != entry["raw_path"] or
                hashlib.sha256(doc["text"].encode("utf-8")).hexdigest() != entry["text_sha256"] or
                digest(doc["articles"]) != entry["structure_sha256"]):
                raise RetrievalError("SOURCE_MISMATCH", "Frozen document hash/metadata mismatch")
            item = {key: doc[key] for key in ("document_id", "title", "issuer", "source_url", "published_at", "effective_at", "raw_sha256")}
            item.update({key: entry[key] for key in ("text_sha256", "structure_sha256")})
            materials.append(item)
            documents.append(doc)
        # 版本材料不包含 corpus_version 本身，避免“哈希里包含自己的哈希”的循环依赖。
        material = {"parser_version": manifest["parser_version"], "documents": sorted(materials, key=lambda x: x["document_id"])}
        if digest(material) != corpus_version:
            raise RetrievalError("SOURCE_MISMATCH", "Corpus version hash mismatch")
        validate_documents(documents, corpus_version)
        return documents
    return load
