from fastapi import APIRouter

from app.contracts import AskRequest, AskResult


def create_qa_router(runtime):
    router=APIRouter(prefix="/api",tags=["qa"])

    @router.post("/ask",response_model=AskResult)
    def ask(body:AskRequest):
        with runtime.admission:
            runtime.ensure_no_evaluation()
            return runtime.qa.ask(body)

    @router.get("/conversations")
    def conversations():
        return {"items":runtime.store.conversations()}

    @router.get("/conversations/{conversation_id}")
    def conversation(conversation_id:str):
        result=runtime.store.conversation(conversation_id)
        for ask in result["asks"]:
            # Rejected candidates/raw provider diagnostics stay in storage for evaluation,
            # never appear as an unchecked answer in normal conversation responses.
            ask.pop("trace",None)
        return result

    return router
