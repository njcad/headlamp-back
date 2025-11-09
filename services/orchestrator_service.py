from typing import Optional
from uuid import UUID

from models.chat_response import ChatResponse
from repos import agent_chat_repository, human_chat_repository
from services.llm_service import LLMService


class OrchestratorService:
    """
    Orchestrates the conversation flow:
    - Retrieves conversation history
    - Coordinates LLM calls and tool execution
    - Saves messages to database
    - Uses implicit state management (orgs presence indicates matching phase)
    """

    @staticmethod
    async def chat(
        user_id: UUID,
        message: str,
        clickedOrgIds: Optional[list[int]] = None,
    ) -> ChatResponse:
        """
        Main entry point for chat requests.
        
        Flow:
        1. Save user message (and handle org selection if present)
        2. Get conversation history
        3. Call LLM service (which may trigger tool calls)
        4. Handle tool call results if needed
        5. Save agent response
        6. Return formatted response
        """
        # 1. Save user message
        # If clickedOrgIds is present, include it in the message context
        if clickedOrgIds:
            message_with_selection = f"{message} [Selected organizations: {', '.join(map(str, clickedOrgIds))}]"
            human_chat_repository.create(user_id=user_id, message=message_with_selection)
        else:
            human_chat_repository.create(user_id=user_id, message=message)
        
        # 2. Get conversation history (merged and sorted)
        conversation_history = OrchestratorService._get_conversation_history(user_id)
        
        # 3. Call LLM service
        llm_response = await LLMService.generate_response(
            conversation_history=conversation_history,
            clickedOrgIds=clickedOrgIds,
        )
        
        # 4. Handle tool calls if present
        response = OrchestratorService._handle_llm_response(llm_response=llm_response)
        
        # 5. Save agent response
        agent_chat_repository.create(
            user_id=user_id,
            message=response.message,
            model=llm_response.get("model", "gpt-4"),
            tool_calls=llm_response.get("tool_calls"),
        )
        
        return response

    @staticmethod
    def _get_conversation_history(user_id: UUID) -> list[dict]:
        """
        Retrieve and merge conversation history from both tables.
        Returns list of messages in OpenAI format: [{"role": "user/assistant", "content": "..."}]
        """
        human_messages = human_chat_repository.get_by_user_id(user_id)
        agent_messages = agent_chat_repository.get_by_user_id(user_id)
        
        # Combine and sort by timestamp
        all_messages = []
        for msg in human_messages:
            all_messages.append({
                "role": "user",
                "content": msg.message,
                "timestamp": msg.timestamp,
            })
        for msg in agent_messages:
            all_messages.append({
                "role": "assistant",
                "content": msg.message,
                "timestamp": msg.timestamp,
            })
        
        # Sort by timestamp
        all_messages.sort(key=lambda x: x["timestamp"])
        
        # Convert to OpenAI format (remove timestamp)
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in all_messages
        ]

    @staticmethod
    def _handle_llm_response(llm_response: dict) -> ChatResponse:
        """
        Process LLM response and handle tool calls if present.
        Returns a ChatResponse with orgs if matching occurred.
        Uses implicit state: presence of orgs indicates matching phase.
        """
        message = llm_response.get("message", "")
        orgs = llm_response.get("orgs")  # LLM service returns orgs if matching tool was called
        
        return ChatResponse(
            message=message,
            orgs=orgs,
        )


__all__ = ["OrchestratorService"]
