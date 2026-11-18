from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from .documents import Condition


class SearchRequest(BaseModel):
    """单组检索请求；禁止额外字段，top_k 严格限制为整数 1～5。"""
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1)
    corpus_version: str = Field(min_length=1)
    condition: Condition = "s400"
    top_k: int = Field(default=5, ge=1, le=5, strict=True)


class CompareRequest(BaseModel):
    """左右共用一个问题与语料版本；两侧固定取 top-5，无需分别传问题。"""
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1)
    corpus_version: str = Field(min_length=1)
    left_condition: Condition = "f400"
    right_condition: Condition = "s400"


def create_search_router(service):
    """API 复用 service 的检索/对照流程，不在路由里另写模型或排序逻辑。"""
    router = APIRouter(tags=["retrieval"])

    @router.post("/search")
    def search(body: SearchRequest):
        return service.search_result(body.question, body.condition, body.corpus_version, body.top_k)

    @router.post("/compare")
    def compare(body: CompareRequest):
        return service.compare(body.question, body.left_condition, body.right_condition, body.corpus_version)

    return router
