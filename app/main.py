"""Single production entry: persistent QA APIs and existing preview pages."""
from contextlib import asynccontextmanager
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from app.api import create_retrieval_routers
from app.api.qa import create_qa_router
from app.api.system import create_system_router
from app.config import load_settings
from app.qa.client import redact
from app.qa.errors import QAError
from app.runtime import Runtime,RetrievalProxy,TaskProxy
STATIC_DIR = Path(__file__).parent / "static"
PROJECT_DESIGN = Path(__file__).parent.parent / "项目设计.md"

def create_app(settings=None,*,qa_service=None,retrieval_service=None,database_path=None,test_mode=False):
    settings=settings or load_settings(env_file=os.environ.get("DERAG_ENV_FILE"))
    runtime=Runtime(settings,qa_service=qa_service,retrieval_service=retrieval_service,
                    database_path=database_path,test_mode=test_mode)
    @asynccontextmanager
    async def lifespan(app):
        runtime.open()
        try:
            yield
        finally:
            runtime.close()
    app=FastAPI(title="DERag",version="0.2.0",lifespan=lifespan)
    app.state.runtime=runtime
    app.mount("/static",StaticFiles(directory=STATIC_DIR),name="static")
    app.include_router(create_qa_router(runtime))
    app.include_router(create_system_router(runtime))
    app.include_router(create_retrieval_routers(RetrievalProxy(runtime),TaskProxy(runtime)))

    @app.exception_handler(QAError)
    async def qa_error(request,exc):
        return JSONResponse(redact(exc.as_dict(),settings.api_key()),status_code=exc.status)
    @app.exception_handler(RequestValidationError)
    async def input_error(request,exc):
        return JSONResponse({"code":"INVALID_REQUEST","message":"Request fields failed validation"},status_code=422)
    @app.exception_handler(Exception)
    async def internal_error(request,exc):
        # Recognize B's existing error without importing its heavy package in C-only mode.
        if type(exc).__module__=="app.retrieval.errors" and type(getattr(exc,"status",None)) is int:
            return JSONResponse(redact(exc.as_dict(),settings.api_key()),status_code=exc.status)
        return JSONResponse({"code":"INTERNAL_ERROR","message":"Service could not complete the request"},status_code=500)

    @app.get("/",include_in_schema=False)
    @app.get("/documents",include_in_schema=False)
    @app.get("/compare",include_in_schema=False)
    @app.get("/evaluation",include_in_schema=False)
    def frontend():
        return FileResponse(STATIC_DIR/"index.html")
    @app.get("/project-design",include_in_schema=False)
    def project_design():
        return FileResponse(PROJECT_DESIGN,media_type="text/plain; charset=utf-8")
    return app


app=create_app()
