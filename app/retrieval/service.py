"""B 对外的业务入口：测试和 C 的问答模块共用同一套建库、检索与对照逻辑。"""
from time import perf_counter
from .chunking import chunks_for_condition
from .errors import RetrievalError
from .indexes import IndexManager
from .types import CONDITIONS
from .vector_store import ChromaStore


class RetrievalService:
    """通过注入文档加载器、编码器和向量库工厂，让 B 无需等待 A/C 就能测试。"""
    def __init__(self, document_loader, embedder, config, vector_store_factory=ChromaStore):
        self.indexes = IndexManager(document_loader, embedder, vector_store_factory, config)

    def build_indexes(self, corpus_version):
        return self.indexes.build_indexes(corpus_version)

    def close(self):
        self.indexes.close()

    def documents(self, corpus_version):
        return self.indexes.documents(corpus_version)

    def document(self, document_id, corpus_version):
        for doc in self.documents(corpus_version):
            if doc["document_id"] == document_id:
                return doc
        raise RetrievalError("NOT_FOUND", f"Document not found: {document_id}", 404)

    def chunks(self, document_id, condition, corpus_version):
        """分块预览读取已完成索引的导出文件，与实际检索使用的块保持一致。"""
        self._validate("chunks", condition, 5)
        self.document(document_id, corpus_version)
        with self.indexes.lock():
            manifest, _ = self.indexes.completed(corpus_version)
            return [c for c in self.indexes.read_chunks(manifest["index_version"], condition) if c["document_id"] == document_id]

    def _validate(self, question, condition, top_k):
        # 业务层也校验参数，因为 C 可以直接调用 Python 函数而不经过 HTTP 校验。
        if not isinstance(question, str) or not question.strip() or condition not in CONDITIONS or type(top_k) is not int or not 1 <= top_k <= 5:
            raise RetrievalError("INVALID_REQUEST", "Question required; condition f400/s400/f800/s800; top_k 1..5", 422)

    def _search(self, question, condition, top_k, manifest, docs):
        """内部检索：编码问题 → 查向量库 → 从冻结正文补齐可引用的证据。"""
        start = perf_counter()
        version = manifest["index_version"]
        # 与建库共用编码器；query=True 使用配置中的问题前缀和相同归一化规则。
        vector = self.indexes.embedder.encode([question], query=True, ids=["question"])[0]
        found = self.indexes.store(version).query(condition, vector, top_k)
        # Chroma 返回 ID 和距离，完整证据以 JSONL 块记录及 A 的冻结文档为准。
        chunk_map = {c["chunk_id"]: c for c in self.indexes.read_chunks(version, condition)}
        doc_map = {d["document_id"]: d for d in docs}
        hits = []
        for rank, (chunk_id, distance) in enumerate(found, 1):
            if chunk_id not in chunk_map:
                raise RetrievalError("SOURCE_MISMATCH", "Retrieved ID absent from chunk export")
            chunk = chunk_map[chunk_id]
            doc = doc_map[chunk["document_id"]]
            # 返回前再次按 Python 原文位置核对；C 可据此生成能回溯到原文的引用。
            if chunk["text"] != doc["text"][chunk["start"]:chunk["end"]]:
                raise RetrievalError("SOURCE_MISMATCH", "Retrieved chunk differs from frozen source")
            fields = ("chunk_id", "corpus_version", "condition", "document_id", "article_ids", "start", "end", "text")
            hit = {k: chunk[k] for k in fields}
            # cosine 距离越小越近；转成 1-distance 后越大越相关，但分数不是概率。
            # 条号标签从 A 的条文表获取，不根据片段文字猜测。
            hit.update(rank=rank, score=1.0 - float(distance), title=doc["title"], source_url=doc["source_url"],
                       article_labels=[a["label"] for a in doc["articles"] if a["article_id"] in chunk["article_ids"]])
            hits.append(hit)
        return {"condition": condition, "hits": hits, "timing_ms": round((perf_counter() - start) * 1000, 3)}

    def search_result(self, question, condition, corpus_version, top_k=5):
        """供 HTTP 使用的完整结果，包含语料版本、索引版本与实际检索耗时。"""
        self._validate(question, condition, top_k)
        with self.indexes.lock():
            manifest, docs = self.indexes.completed(corpus_version)
            result = self._search(question, condition, top_k, manifest, docs)
            return dict(result, corpus_version=corpus_version, index_version=manifest["index_version"])

    def search(self, question, condition, corpus_version, top_k=5):
        """供 C 的问答模块直接调用，只返回 SearchHit 列表，不生成回答。"""
        return self.search_result(question, condition, corpus_version, top_k)["hits"]

    def compare(self, question, left_condition, right_condition, corpus_version):
        """同题对照：同一索引版本分别查两侧，各取最多 5 块；任一侧失败就报错。"""
        self._validate(question, left_condition, 5)
        self._validate(question, right_condition, 5)
        with self.indexes.lock():
            manifest, docs = self.indexes.completed(corpus_version)
            # 锁内只确定一次版本，防止两侧不小心使用不同语料或索引。
            sides = [self._search(question, c, 5, manifest, docs) for c in (left_condition, right_condition)]
            for side in sides:
                # 返回块数相同不代表上下文长度相同，所以额外报告各侧的字符总数。
                side["context_chars"] = sum(h["end"] - h["start"] for h in side["hits"])
            return {"question": question, "corpus_version": corpus_version, "index_version": manifest["index_version"],
                    "left": sides[0], "right": sides[1]}
