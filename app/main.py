"""Serve the frontend preview until the RAG API is implemented."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


STATIC_DIR = Path(__file__).parent / "static"
PROJECT_DESIGN = Path(__file__).parent.parent / "项目设计.md"

app = FastAPI(title="DERag", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "phase": "frontend_preview"}


@app.get("/", include_in_schema=False)
@app.get("/documents", include_in_schema=False)
@app.get("/compare", include_in_schema=False)
@app.get("/evaluation", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/project-design", include_in_schema=False)
def project_design() -> FileResponse:
    return FileResponse(PROJECT_DESIGN, media_type="text/plain; charset=utf-8")
