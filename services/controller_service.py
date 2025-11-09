from models.chat_request import ChatRequest
from models.chat_response import ChatResponse
from services.orchestrator_service import OrchestratorService
from repos import user_repository


class ControllerService:
    """Handles HTTP-level concerns: validation, error handling, response formatting."""

    @staticmethod
    async def handle_chat(request: ChatRequest) -> ChatResponse:
        """
        Process a chat request and return a response.
        
        This is a thin controller layer that:
        - Validates the request (handled by Pydantic)
        - Calls the orchestrator service
        - Formats the response
        - Handles errors (can be extended)
        """
        # Ensure user exists (create if missing to get Supabase default UUID)
        if request.user_id is None:
            user = user_repository.create()
        else:
            user = user_repository.ensure_exists(user_id=request.user_id)

        # Call orchestrator to handle business logic (returns ChatResponse with user_id)
        return await OrchestratorService.chat(
            user_id=user.id,
            message=request.message,
            clickedOrgIds=request.clickedOrgIds,
        )


__all__ = ["ControllerService"]

