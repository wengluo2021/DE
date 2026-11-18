"""将文本编码为向量：支持测试向量和本地真实模型，编码前检查 token 上限。"""
from pathlib import Path
from threading import RLock
import hashlib
import math
import re

from .errors import RetrievalError
from .types import file_hash
import json


class MockEmbedder:
    """固定测试向量：同文同向量，便于测接口与数据库；不能代表真实语义效果。"""
    def identity(self):
        return {"model_id": "test-only/hashed-characters", "revision": "mock-v1",
                "files": {}, "dimension": 32, "normalize": True,
                "query_prefix": "", "document_prefix": "", "max_input_tokens": None,
                "token_policy": "not-applicable-test-vectors", "pooling": "test-only"}

    def encode(self, texts, *, query=False, ids=None):
        # 按字符哈希分配到 32 个维度，再归一化；整个过程不下载或调用模型。
        vectors = []
        for text in texts:
            v = [0.0] * 32
            for char in text:
                h = hashlib.sha256(char.encode("utf-8")).digest()
                v[h[0] % 32] += 1.0 if h[1] % 2 else -1.0
            norm = math.sqrt(sum(x * x for x in v))
            if not norm:
                v[0], norm = 1.0, 1.0
            vectors.append([x / norm for x in v])
        return vectors


class LocalEmbedder:
    """真实 BGE-M3 编码器；首次编码时才加载权重，同一实例后续复用模型。"""
    def __init__(self, config):
        # 固定模型自带 Normalize 层，所以只接受 normalize=true，避免配置与实际行为不符。
        if config["normalize"] is not True:
            raise RetrievalError("INVALID_REQUEST", "This frozen BGE-M3 pipeline requires normalize=true", 422)
        if any(type(config[k]) is not int or config[k] <= 0 for k in ("batch_size", "max_input_tokens", "dimension")):
            raise RetrievalError("INVALID_REQUEST", "Embedding sizes/limits must be positive integers", 422)
        self.config = dict(config)
        self.directory = Path(config["model_dir"])
        self._identity = None
        self._model = None
        # 多个 HTTP 请求可能共用模型；可重入锁也允许 encode 内继续调用 identity 校验。
        self._lock = RLock()

    def identity(self):
        """校验模型版本和逐文件哈希，返回参与索引版本计算的模型配置。"""
        with self._lock:
            if self._identity is None:
                path = self.directory / "derag-model-manifest.json"
                if not path.is_file():
                    raise RetrievalError("EMBEDDING_UNAVAILABLE", "Model missing. Run python -m scripts.fetch_embedding first", 503)
                manifest = json.loads(path.read_text(encoding="utf-8"))
                if (manifest["model_id"] != self.config["model_id"] or manifest["revision"] != self.config["revision"] or
                        not re.fullmatch(r"[0-9a-f]{40}", manifest["revision"])):
                    raise RetrievalError("VERSION_MISMATCH", "Model manifest/revision differs from configuration")
                files = manifest["files"]
                if not files or not any(n.endswith((".bin", ".safetensors")) for n in files):
                    raise RetrievalError("EMBEDDING_UNAVAILABLE", "Model manifest has no weights", 503)
                # 首次读取时核对文件内容；仅有同名目录不足以证明使用了同一份权重。
                for name, expected in files.items():
                    local = (self.directory / name).resolve()
                    if not local.is_relative_to(self.directory.resolve()) or not local.is_file() or file_hash(local) != expected:
                        raise RetrievalError("EMBEDDING_UNAVAILABLE", f"Model file checksum failed: {name}", 503)
                # 除下载缓存和清单本身，模型目录不能混入清单之外的文件。
                actual = {p.relative_to(self.directory).as_posix() for p in self.directory.rglob("*") if p.is_file()
                          and ".cache" not in p.relative_to(self.directory).parts and p.name != "derag-model-manifest.json"}
                if actual != set(files):
                    raise RetrievalError("EMBEDDING_UNAVAILABLE", "Unmanifested model files; use a clean model directory", 503)
                keys = ("model_id", "revision", "dimension", "normalize", "query_prefix", "document_prefix", "max_input_tokens", "pooling")
                self._identity = {k: self.config[k] for k in keys}
                self._identity.update(files=files, token_policy="reject-overflow-v1")
            return dict(self._identity)

    def _load(self):
        """仅从已校验的项目模型目录加载，并核对实际维度、窗口和池化方式。"""
        self.identity()
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                import torch
                torch.set_num_threads(self.config.get("cpu_threads", 4))
                # local_files_only 禁止加载时临时联网找权重；缺文件时明确报错。
                model = SentenceTransformer(str(self.directory), device=self.config["device"],
                                            local_files_only=True, trust_remote_code=False)
                if model.get_embedding_dimension() != self.config["dimension"]:
                    raise RetrievalError("VERSION_MISMATCH", "Actual embedding dimension differs from configuration")
                if self.config["max_input_tokens"] > model.max_seq_length:
                    raise RetrievalError("VERSION_MISMATCH", f"Configured token limit exceeds model limit {model.max_seq_length}")
                # CLS 池化：用序列首个特殊 token 对应的向量代表整段文本。
                pooling = model[1].get_config_dict()
                if self.config["pooling"] != "cls" or pooling.get("pooling_mode") != "cls":
                    raise RetrievalError("VERSION_MISMATCH", "Expected the frozen BGE-M3 CLS-only pooling")
                self._model = model
            except RetrievalError:
                raise
            except Exception as exc:
                raise RetrievalError("EMBEDDING_UNAVAILABLE", f"Local embedding load failed: {exc}", 503) from exc

    def encode(self, texts, *, query=False, ids=None):
        """按输入顺序返回向量；query=True 选择问题前缀，否则选择文档前缀。"""
        if not texts:
            return []
        with self._lock:
            self._load()
            prefix = self.config["query_prefix" if query else "document_prefix"]
            prepared = [prefix + t for t in texts]
            ids = ids or ["question" if query else str(i) for i in range(len(texts))]
            # 400/800 是字符数，模型上限却是 token 数，两者不能直接等同。
            # 先算“前缀+正文+特殊 token”的真实长度，超限直接报错，避免静默截掉证据。
            for text, identifier in zip(prepared, ids, strict=True):
                tokens = self._model.tokenizer(text, add_special_tokens=True, truncation=False)["input_ids"]
                if len(tokens) > self.config["max_input_tokens"]:
                    raise RetrievalError("MODEL_INPUT_TOO_LONG", f"{identifier}: {len(tokens)} tokens exceeds {self.config['max_input_tokens']}")
            try:
                vectors = self._model.encode(prepared, batch_size=self.config["batch_size"],
                                             normalize_embeddings=self.config["normalize"],
                                             show_progress_bar=False, convert_to_numpy=True).tolist()
            except Exception as exc:
                raise RetrievalError("EMBEDDING_UNAVAILABLE", f"Embedding encode failed: {exc}", 503) from exc
            # 入库前排除维度不符、NaN/无穷值或全零向量，避免污染检索索引。
            if len(vectors) != len(texts) or any(len(v) != self.config["dimension"] or not all(math.isfinite(x) for x in v) or not any(v) for v in vectors):
                raise RetrievalError("EMBEDDING_UNAVAILABLE", "Embedding returned invalid vectors", 503)
            return vectors
