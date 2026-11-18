"""构建四组索引并记录版本；四组全部校验成功后，整个版本才允许查询。"""
from pathlib import Path
from time import perf_counter
from filelock import FileLock
import json

from .chunking import chunks_for_condition
from .errors import RetrievalError
from .types import CONDITIONS, CHUNKER_VERSION, canonical, digest, file_hash, write_json, validate_documents
from .vector_store import store_identity


class IndexManager:
    """负责分块导出、向量写入与 manifest 清单；依赖通过构造函数注入。"""
    def __init__(self, loader, embedder, store_factory, config):
        self.loader, self.embedder, self.store_factory, self.config = loader, embedder, store_factory, config
        self.root = Path(config["data_dir"])
        self._stores = {}

    def lock(self):
        """同一数据目录用文件锁协调建库与查询，避免查询读到正在写入的索引。"""
        self.root.mkdir(parents=True, exist_ok=True)
        return FileLock(self.root / ".retrieval.lock", timeout=600)

    def documents(self, corpus_version):
        """从注入的加载器取文档并统一排序，使构建顺序可以复现。"""
        docs = self.loader(corpus_version)
        validate_documents(docs, corpus_version)
        return sorted(docs, key=lambda d: d["document_id"])

    def material(self, corpus_version, docs):
        """索引的版本材料：语料、算法、四组条件、模型和向量库有效配置。"""
        return {"corpus_version": corpus_version, "chunker_version": CHUNKER_VERSION,
                "conditions": [{"condition": c, "boundary_method": m, "target_chars": n} for c, (m, n) in CONDITIONS.items()],
                # 测试语料使用命名版本，不是内容哈希；额外摘要可发现同名样例被修改。
                "source_digest": digest(docs), "embedding": self.embedder.identity(), "vector_store": store_identity()}

    def manifest_path(self, version):
        return self.root / "indexes" / (version + ".json")

    def store(self, version):
        # 每个版本使用独立目录；同一服务实例重复查询时复用 Chroma 客户端。
        if version not in self._stores:
            self._stores[version] = self.store_factory(self.root / "chroma" / version)
        return self._stores[version]

    def chunk_path(self, version, condition):
        return self.root / "chunks" / version / (condition + ".jsonl")

    def read_chunks(self, version, condition):
        """读取权威块记录；JSONL 每行一个块，保存完整文本、条号和原文位置。"""
        return [json.loads(line) for line in self.chunk_path(version, condition).read_text(encoding="utf-8").splitlines() if line]

    def verify(self, manifest, docs):
        """同时核对导出文件、重新切分结果和库内 ID，避免复用缺块或损坏的索引。"""
        version = manifest["index_version"]
        for condition in CONDITIONS:
            path = self.chunk_path(version, condition)
            if not path.is_file() or file_hash(path) != manifest["conditions"][condition]["chunks_sha256"]:
                raise RetrievalError("SOURCE_MISMATCH", f"Corrupt chunk export: {condition}")
            chunks = self.read_chunks(version, condition)
            expected = [c for doc in docs for c in chunks_for_condition(doc, condition)]
            if chunks != expected:
                raise RetrievalError("SOURCE_MISMATCH", "Export differs from frozen source/chunker")
            if self.store(version).ids(condition) != {c["chunk_id"] for c in chunks}:
                raise RetrievalError("INDEX_NOT_READY", f"Collection IDs differ from chunk export: {condition}")

    def completed(self, corpus_version):
        """按当前语料和配置精确找索引，不自动拿“最近一次”的其他版本代替。"""
        docs = self.documents(corpus_version)
        material = self.material(corpus_version, docs)
        version = digest(material)
        path = self.manifest_path(version)
        if not path.exists():
            raise RetrievalError("INDEX_NOT_READY", "Build all four indexes for this corpus/configuration first")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if (manifest.get("state") != "completed" or manifest.get("material") != material or
                manifest.get("index_version") != version):
            raise RetrievalError("INDEX_NOT_READY", "Index is incomplete or incompatible")
        self.verify(manifest, docs)
        return manifest, docs

    def build_indexes(self, corpus_version):
        """构建入口：加载校验 → 四组分块 → 统一编码入库 → 完整校验 → 标为完成。"""
        with self.lock():
            docs = self.documents(corpus_version)
            material = self.material(corpus_version, docs)
            version = digest(material)
            path = self.manifest_path(version)
            if path.exists():
                old = json.loads(path.read_text(encoding="utf-8"))
                # 重复建相同版本时先校验再复用；失败版本会进入下方重试流程。
                if old.get("state") == "completed":
                    self.verify(old, docs)
                    return old
            manifest = {"schema_version": "1.0", "corpus_version": corpus_version, "index_version": version,
                        "state": "running", "material": material, "conditions": {},
                        "runtime": {"device": self.config["embedding"]["device"],
                                    "batch_size": self.config["embedding"]["batch_size"]}}
            write_json(path, manifest)
            begin = perf_counter()
            try:
                # 先切完并校验四组的原文覆盖，再开始昂贵的模型编码。
                all_chunks = {}
                for condition in CONDITIONS:
                    stats = {}
                    chunks = [c for doc in docs for c in chunks_for_condition(doc, condition, stats)]
                    all_chunks[condition] = chunks
                    target = self.chunk_path(version, condition)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    # 显式使用 UTF-8 和 LF，让导出字节及其哈希不随操作系统换行习惯改变。
                    target.write_text("".join(canonical(c) + "\n" for c in chunks), encoding="utf-8", newline="\n")
                    lengths = [len(c["text"]) for c in chunks]
                    manifest["conditions"][condition] = {"count": len(chunks), "min_chars": min(lengths, default=0),
                        "mean_chars": sum(lengths) / len(lengths) if lengths else 0, "max_chars": max(lengths, default=0),
                        "fallbacks": stats, "chunks_sha256": file_hash(target)}
                # 同次构建中，相同文本可复用同一模型向量；各条件仍保留各自的块 ID。
                cache = {}
                for condition, chunks in all_chunks.items():
                    start = perf_counter()
                    store = self.store(version)
                    store.collection(condition, create=True)
                    # 稳定 ID 配合 upsert：失败后重新构建覆盖已有记录，不重复插入。
                    batch_size = self.config["embedding"]["batch_size"]
                    for pos in range(0, len(chunks), batch_size):
                        batch = chunks[pos:pos + batch_size]
                        # 只编码缓存里没有的文本；同时传入文档/块 ID，超限时报错可直接定位。
                        missing = {c["text"]: f"{c['document_id']}/{c['chunk_id']}" for c in batch if c["text"] not in cache}
                        vectors = self.embedder.encode(list(missing), ids=list(missing.values())) if missing else []
                        if len(vectors) != len(missing):
                            raise RetrievalError("EMBEDDING_UNAVAILABLE", "Embedding batch count mismatch", 503)
                        cache.update(zip(missing, vectors, strict=True))
                        store.upsert(condition, batch, [cache[c["text"]] for c in batch])
                    manifest["conditions"][condition]["build_ms"] = round((perf_counter() - start) * 1000, 3)
                # 只有四组都写入且核对通过，才发布 completed 状态。
                self.verify(manifest, docs)
                manifest["state"] = "completed"
                manifest["build_ms"] = round((perf_counter() - begin) * 1000, 3)
                write_json(path, manifest)
                return manifest
            except Exception as exc:
                # 保留失败原因供任务/CLI 展示；查询端会拒绝这个未完成版本。
                manifest.update(state="failed", error=str(exc))
                write_json(path, manifest)
                raise
