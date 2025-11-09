from typing import Optional
from uuid import UUID

from models.application_draft import ApplicationDraft
from models.chat_response import ChatResponse
from repos import agent_chat_repository, human_chat_repository, user_repository
from services.application_service import ApplicationService
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
        doApply: Optional[list[int]] = None,
        application_draft: Optional[ApplicationDraft] = None,
    ) -> ChatResponse:
        """
        Main entry point for chat requests.
        
        Flow:
        1. Save user message (and handle org selection/application submission if present)
        2. Get conversation history
        3. If doApply is present, create applications for those orgs
        4. If clickedOrgIds is present (and not doApply), create application drafts
        5. Call LLM service (which may trigger tool calls)
        6. Handle tool call results if needed
        7. Save agent response
        8. Return formatted response
        """
        # 0. Ensure user exists (create on first chat)
        user_repository.ensure_exists(user_id=user_id)

        # 1. Save user message
        # If clickedOrgIds or doApply is present, include it in the message context
        if doApply:
            message_with_action = f"{message} [Submitting applications to organizations: {', '.join(map(str, doApply))}]"
            human_chat_repository.create(user_id=user_id, message=message_with_action)
        elif clickedOrgIds:
            message_with_selection = f"{message} [Selected organizations: {', '.join(map(str, clickedOrgIds))}]"
            human_chat_repository.create(user_id=user_id, message=message_with_selection)
        else:
            human_chat_repository.create(user_id=user_id, message=message)
        
        # 2. Get conversation history (merged and sorted)
        conversation_history = OrchestratorService._get_conversation_history(user_id)
        
        # 2.5. If doApply is present, create actual applications
        print(f"doApply: {doApply}")
        if doApply:
            print(f"Creating applications for organizations: {doApply}")
            await ApplicationService.create_applications(
                user_id=user_id,
                organization_ids=doApply,
                application_draft=application_draft,
            )
        # 2.6. If clickedOrgIds is present (but not doApply), create application drafts
        elif clickedOrgIds:
            application_draft = await ApplicationService.create_application_draft(
                organization_ids=clickedOrgIds,
                conversation_history=conversation_history,
            )
        
        # 3. Call LLM service
        llm_response = await LLMService.generate_response(
            conversation_history=conversation_history,
            clickedOrgIds=clickedOrgIds,
        )
        
        # 4. Handle tool calls if present
        response = OrchestratorService._handle_llm_response(
            llm_response=llm_response,
            user_id=user_id,
            application_draft=application_draft,
        )
        
        # 5. Save agent response
        agent_chat_repository.create(
            user_id=user_id,
            message=response.message,
            model=llm_response.get("model", "gpt-4"),
            tool_calls=llm_response.get("tool_calls"),
        )
        print(f"response: {response}")
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
    def _handle_llm_response(
        llm_response: dict,
        user_id: UUID,
        application_draft: Optional[ApplicationDraft] = None,
    ) -> ChatResponse:
        """
        Process LLM response and handle tool calls if present.
        Returns a ChatResponse with orgs if matching occurred, or applicationDraft if created.
        Uses implicit state: presence of orgs indicates matching phase, presence of draft indicates confirmation needed.
        """
        message = llm_response.get("message", "")
        orgs = llm_response.get("orgs")  # LLM service returns orgs if matching tool was called
        print(f"DEBUG orchestrator: orgs from llm_response: {orgs}, type: {type(orgs)}")
        
        # Convert snake_case to camelCase for frontend (ChatResponse model expects applicationDraft)
        return ChatResponse(
            user_id=user_id,
            message=message,
            orgs=orgs,
            applicationDraft=application_draft,
        )


__all__ = ["OrchestratorService"]
