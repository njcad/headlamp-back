from fastapi import APIRouter

from models.chat_request import ChatRequest
from models.chat_response import ChatResponse
from services.controller_service import ControllerService

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Handle chat requests from users."""
    print(request)
    return await ControllerService.handle_chat(request)


__all__ = ["router"]