from fastapi import APIRouter, Request

from backend.shared.contracts import AskRequest, AssistantAnswer

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/ask", response_model=AssistantAnswer)
async def ask(request: Request, body: AskRequest):
    return await request.app.state.assistant.ask(body.question, request.app.state.settings)
