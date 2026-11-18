from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, ConfigDict, Field


class BuildRequest(BaseModel):
    """建库请求只指定语料版本；四组条件和模型设置统一由配置决定。"""
    model_config = ConfigDict(extra="forbid")
    corpus_version: str = Field(min_length=1)


def create_indexes_router(service, task_manager):
    router = APIRouter(tags=["indexes"])

    @router.post("/indexes/build", status_code=202)
    def build(body: BuildRequest, background_tasks: BackgroundTasks):
        # 编码建库可能耗时较长，先返回 202 和任务 ID；前端通过任务接口轮询状态。
        # lambda 包装成无参数函数，由注入的任务管理器安排执行。
        return task_manager.submit(lambda: service.build_indexes(body.corpus_version), background_tasks)

    return router
