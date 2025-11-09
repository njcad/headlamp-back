from models.chat_request import ChatRequest
from models.chat_response import ChatResponse
from services.orchestrator_service import OrchestratorService


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
        # Call orchestrator to handle business logic
        # Orchestrator returns full ChatResponse with message and optional orgs
        return await OrchestratorService.chat(
            user_id=request.user_id,
            message=request.message,
            clickedOrgIds=request.clickedOrgIds,
        )


__all__ = ["ControllerService"]

