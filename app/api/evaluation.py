from typing import Literal
from fastapi import APIRouter,BackgroundTasks,Query
from fastapi.responses import Response

from app.contracts import Condition,EvaluationRunRequest
from app.evaluation.export import export_csv,export_json
from app.evaluation.review import ReviewPatch


def create_evaluation_router(runtime):
    router=APIRouter(prefix="/api/evaluations",tags=["evaluations"])

    @router.post("/run",status_code=202)
    def run(body:EvaluationRunRequest,background_tasks:BackgroundTasks):
        return runtime.evaluation.submit(body,background_tasks)

    @router.post("/p800/run",status_code=202)
    def run_p800(body:EvaluationRunRequest,background_tasks:BackgroundTasks):
        return runtime.evaluation.submit_p800(body,background_tasks)

    @router.get("")
    def runs():
        return {"items":runtime.evaluations.list_runs()}

    @router.get("/{run_id}")
    def result(run_id:str):
        return runtime.evaluations.get(run_id)

    @router.patch("/{run_id}/cases/{case_id}")
    def review(run_id:str,case_id:str,body:ReviewPatch,condition:Condition=Query(...)):
        return runtime.evaluations.review(run_id,condition,case_id,body)

    @router.get("/{run_id}/export")
    def export(run_id:str,format:Literal["json","csv"]="json"):
        run=runtime.evaluations.get(run_id)
        payload=export_json(run) if format=="json" else export_csv(run)
        # Filename is constant; never interpolate untrusted path/input into headers.
        return Response(payload,media_type="application/json" if format=="json" else "text/csv",
                        headers={"Content-Disposition":f'attachment; filename="evaluation.{format}"'})

    return router
