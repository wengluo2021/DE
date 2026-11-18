from fastapi import APIRouter


def create_system_router(runtime):
    router=APIRouter(prefix="/api",tags=["system"])

    @router.get("/health")
    def health():
        return runtime.health()

    @router.get("/tasks/{task_id}")
    def task(task_id:str):
        return runtime.tasks.get(task_id)

    return router
