"""B 独立验证应用：装配同一套业务 API 和验证页，导入时不下载模型或建库。"""
from app.retrieval.types import FIXTURE_CORPUS_VERSION
import copy
import logging
import os
from pathlib import Path
from threading import RLock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api import create_retrieval_routers, install_retrieval_error_handlers
from app.retrieval import RetrievalService, RetrievalError
from app.retrieval.embedding import LocalEmbedder, MockEmbedder
from app.retrieval.types import CONDITIONS, fixture_loader, load_config


class MemoryTaskManager:
    """仅供单进程测试的内存任务管理器；重启会丢任务，正式持久化任务由 C 提供。"""
    def __init__(self):
        self.tasks, self.lock = {}, RLock()

    def submit(self, function, background_tasks):
        task_id = "index-task-" + uuid4().hex
        with self.lock:
            self.tasks[task_id] = {"task_id": task_id, "state": "queued"}
        # 先登记 queued，再在响应后的后台任务中执行；网页用任务 ID 查询后续状态。
        background_tasks.add_task(self._run, task_id, function)
        return {"task_id": task_id, "state": "queued"}

    def _run(self, task_id, function):
        # 状态流转：queued → running → completed/failed；失败时保留可读原因。
        with self.lock:
            self.tasks[task_id]["state"] = "running"
        try:
            result = function()
            with self.lock:
                self.tasks[task_id].update(state="completed", result=result)
        except Exception as exc:
            error = exc.as_dict() if isinstance(exc, RetrievalError) else {"code": "INTERNAL_ERROR", "message": "Build failed; see server log"}
            logging.getLogger(__name__).exception("B index build failed")
            with self.lock:
                self.tasks[task_id].update(state="failed", error=error)

    def get(self, task_id):
        with self.lock:
            if task_id not in self.tasks:
                raise RetrievalError("NOT_FOUND", "Task not found", 404)
            return copy.deepcopy(self.tasks[task_id])


def make_service(mode, config=None):
    """选择 mock 测试向量或 real 本地模型，两种模式都读取 B 的合成文档。"""
    config = copy.deepcopy(config or load_config())
    if mode not in ("mock", "real"):
        raise ValueError("DERAG_B_DEBUG_MODE must be mock or real")
    # 按模式隔离索引；真实模型缺失时会报错，不会悄悄换成模拟向量。
    config["data_dir"] = str(Path(config["data_dir"]) / "b-fixtures" / mode)
    return RetrievalService(fixture_loader, MockEmbedder() if mode == "mock" else LocalEmbedder(config["embedding"]), config)


def create_app(service=None, *, mode=None):
    """测试可传入自己的 service；命令行启动则按环境变量创建独立验证服务。"""
    mode = mode or os.environ.get("DERAG_B_DEBUG_MODE", "mock")
    service = service or make_service(mode)
    app = FastAPI(title="DERag B independent retrieval verification", version="1.0.0")
    tasks = MemoryTaskManager()
    install_retrieval_error_handlers(app)
    app.include_router(create_retrieval_routers(service, tasks))
    app.state.service, app.state.tasks = service, tasks

    @app.get("/api/tasks/{task_id}")
    def task(task_id: str):
        return tasks.get(task_id)

    @app.get("/b-debug")
    def debug():
        return FileResponse(Path(__file__).parent / "static/b_debug.html")

    @app.get("/b-debug/status")
    def status():
        # 只检查当前版本能否使用，不主动建库；页面据此启用或禁用检索按钮。
        model = service.indexes.embedder
        result = {"mode": mode, "corpus_version": FIXTURE_CORPUS_VERSION, "synthetic_corpus": True,
                  "model": model.config if isinstance(model, LocalEmbedder) else model.identity(),
                  "index_version": None, "ready": False, "conditions": {c: False for c in CONDITIONS}}
        try:
            with service.indexes.lock():
                manifest, _ = service.indexes.completed(FIXTURE_CORPUS_VERSION)
            result.update(ready=True, index_version=manifest["index_version"], conditions=manifest["conditions"])
        except RetrievalError as exc:
            result["error"] = exc.as_dict()
        return result

    return app


# uvicorn tests.support.b_app:app 会导入这个应用；网页路径为 /b-debug。
app = create_app()
