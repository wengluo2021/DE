"""Chroma 持久化适配：只接收已编码向量，不使用 Chroma 自带的默认模型。"""
from pathlib import Path
import importlib.metadata

from .errors import RetrievalError

# HNSW 是近似向量检索索引；四组固定同一参数，避免把向量库差异混入分块实验。
# 小同步阈值用于确保少量测试数据也能及时落盘；正式改参数后须统一重建四组。
HNSW = {"space": "cosine", "ef_construction": 100, "ef_search": 100,
        "max_neighbors": 16, "num_threads": 1, "batch_size": 2,
        "sync_threshold": 2, "resize_factor": 1.2}


def store_identity():
    """将实际引擎版本与配置纳入索引版本材料，便于复现和发现配置变更。"""
    return {"engine": "chromadb", "version": importlib.metadata.version("chromadb"), "hnsw": HNSW}


class ChromaStore:
    """一个目录对应一个索引版本，四个 collection 分别存放四种实验条件。"""
    def __init__(self, directory: Path):
        import chromadb
        from chromadb.config import Settings
        self.client = chromadb.PersistentClient(path=str(directory), settings=Settings(anonymized_telemetry=False))

    def collection(self, condition, create=False):
        # 查询时只读取已有 collection；缺失即报未就绪，不临时造一个空库来代替。
        if create:
            return self.client.get_or_create_collection(name="kb_" + condition,
                configuration={"hnsw": HNSW}, embedding_function=None)
        try:
            return self.client.get_collection(name="kb_" + condition, embedding_function=None)
        except Exception as exc:
            raise RetrievalError("INDEX_NOT_READY", f"Collection {condition} unavailable") from exc

    def upsert(self, condition, chunks, vectors):
        """按稳定 chunk_id 新增或覆盖；全文和 article_ids 保存在 JSONL，不塞入标量元数据。"""
        c = self.collection(condition, create=True)
        if not chunks:
            return
        c.upsert(ids=[x["chunk_id"] for x in chunks], embeddings=vectors,
                 metadatas=[{"document_id": x["document_id"], "start": x["start"], "end": x["end"]} for x in chunks])

    def ids(self, condition):
        return set(self.collection(condition).get(include=[])["ids"])

    def query(self, condition, vector, top_k):
        """返回 (块 ID, cosine 距离)，距离升序；已返回的同距离候选再按 ID 排序。"""
        c = self.collection(condition)
        count = c.count()
        if not count:
            return []
        # 库中不足 top_k 条时只返回实际数量，不人为补结果。
        data = c.query(query_embeddings=[vector], n_results=min(top_k, count), include=["distances"])
        return sorted(zip(data["ids"][0], data["distances"][0], strict=True), key=lambda pair: (pair[1], pair[0]))
