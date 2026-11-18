# HTTP 层只校验参数并转交业务服务；不在这里重新分块或修改正文。
from typing import Annotated, Literal
from fastapi import APIRouter, Query

# Literal 让 FastAPI 自动拒绝非法条件，并在 /docs 中显示可选值。
Condition = Literal["f400", "s400", "f800", "s800"]
Corpus = Annotated[str, Query(min_length=1)]


def create_documents_router(service):
    router = APIRouter(tags=["documents"])

    @router.get("/documents")
    def documents(corpus_version: Corpus):
        # 列表只返回摘要；点击文档时再通过详情接口获取全文。
        return {"items": [{"document_id": d["document_id"], "title": d["title"], "source_url": d["source_url"],
                           "corpus_version": d["corpus_version"], "article_count": len(d["articles"]), "char_count": len(d["text"])}
                          for d in service.documents(corpus_version)]}

    @router.get("/documents/{document_id}")
    def document(document_id: str, corpus_version: Corpus):
        return service.document(document_id, corpus_version)

    @router.get("/documents/{document_id}/chunks")
    def chunks(document_id: str, corpus_version: Corpus, condition: Condition = "s400"):
        # 展示实际入库的块，保证网页预览与后端检索使用相同的原文区间。
        return {"items": service.chunks(document_id, condition, corpus_version)}

    return router
