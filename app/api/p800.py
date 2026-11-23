"""HTTP surface for the optional P800 parent–child retrieval page.

This is intentionally separate from the frozen four-condition ``/api/search``
and ``/api/compare`` endpoints.  It does not alter the experiment conditions,
index versions, or saved evaluation results.
"""
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.qa.errors import QAError


class P800SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=1000)
    corpus_version: str = Field(min_length=1)
    candidate_k: int = Field(default=50, ge=5, le=100, strict=True)


def create_p800_router(runtime):
    router = APIRouter(prefix="/api/p800", tags=["p800"])

    @router.get("/status")
    def status():
        return runtime.p800_status()

    @router.post("/search")
    def search(body: P800SearchRequest):
        cfg = runtime.settings.experiment
        if body.corpus_version != cfg.corpus_version:
            raise QAError("VERSION_MISMATCH", "Requested corpus does not match the active configuration", 409)
        return runtime.get_p800_service().search(body.question, candidate_k=body.candidate_k)

    return router
