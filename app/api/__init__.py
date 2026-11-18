"""HTTP 装配入口：C 在正式 FastAPI 应用中注册路由工厂与统一异常处理器。"""
import logging
from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.retrieval.errors import RetrievalError


def install_retrieval_error_handlers(app: FastAPI):
    """把业务错误和参数错误都转换成 {code, message}，供前端统一展示。"""
    @app.exception_handler(RetrievalError)
    async def business_error(request: Request, exc: RetrievalError):
        return JSONResponse(exc.as_dict(), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def input_error(request: Request, exc: RequestValidationError):
        # FastAPI 默认返回 detail；这里显式转成三人约定的错误格式。
        message = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        return JSONResponse({"code": "INVALID_REQUEST", "message": message}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        # 未预期错误记录完整日志，不能伪装成检索无命中；客户端收到统一的 500 响应。
        logging.getLogger(__name__).error("Unhandled retrieval API error", exc_info=exc)
        return JSONResponse({"code": "INTERNAL_ERROR", "message": "Unexpected server error; see server log"}, status_code=500)


def create_retrieval_routers(service, task_manager):
    """注入 B 服务与任务管理器；后者提供 submit(建库函数, BackgroundTasks) 接口。"""
    from .documents import create_documents_router
    from .indexes import create_indexes_router
    from .search import create_search_router
    router = APIRouter(prefix="/api")
    router.include_router(create_documents_router(service))
    router.include_router(create_indexes_router(service, task_manager))
    router.include_router(create_search_router(service))
    return router
