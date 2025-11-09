import json
from typing import Optional

from openai import OpenAI

from config import settings
from models.org import OrgSummary
from prompts.intake import get_intake_system_prompt
from repos import intake_question_repository, org_repository


class LLMService:
    """
    Handles all OpenAI API interactions.
    Formats conversation history, makes API calls, handles tool calls.
    """

    # Tool definitions for OpenAI
    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "match_nonprofits",
                "description": "Find the top 3 most relevant nonprofit organizations based on the conversation history. Use this when you have gathered enough information about the person's needs and situation.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "extract_responses",
                "description": "Extract structured answers to intake questions from the conversation history. Use this after the user has selected organizations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question_responses": {
                            "type": "object",
                            "description": "Map of question IDs to their answers based on the conversation",
                            "additionalProperties": {"type": "string"},
                        },
                    },
                    "required": ["question_responses"],
                },
            },
        },
    ]

    @staticmethod
    async def generate_response(
        conversation_history: list[dict],
        clickedOrgIds: Optional[list[int]] = None,
    ) -> dict:
        """
        Generate a response from the LLM based on conversation history.
        
        Args:
            conversation_history: List of messages in OpenAI format
            clickedOrgIds: Optional list of organization IDs if user made selections
        
        Returns:
            {
                "message": str,  # The text response
                "model": str,     # Model used
                "tool_calls": Optional[list[dict]],  # Tool calls if any
                "orgs": Optional[list[OrgSummary]],  # Organizations if matching tool was called
            }
        """
        # Initialize OpenAI client
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
        
        client = OpenAI(api_key=settings.openai_api_key)
        
        # Get intake questions for system prompt
        intake_questions = intake_question_repository.get_all()
        question_texts = [q.question for q in intake_questions]
        
        # Build system prompt
        system_prompt = get_intake_system_prompt(question_texts)
        
        # If user selected orgs, add context about that
        if clickedOrgIds:
            system_prompt += f"\n\nIMPORTANT: The user has selected the following organization IDs: {clickedOrgIds}. Use the extract_responses tool to extract their answers to the intake questions."
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            *conversation_history,
        ]
        
        # Call OpenAI API
        model = "gpt-4"  # or "gpt-4-turbo-preview" for newer models
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=LLMService.TOOLS,
            tool_choice="auto",  # Let the model decide when to use tools
        )
        
        # Extract response
        assistant_message = response.choices[0].message
        message_content = assistant_message.content or ""
        tool_calls = None
        orgs = None
        
        # Handle tool calls
        if assistant_message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in assistant_message.tool_calls
            ]
            
            # Execute tool calls
            tool_results = []
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name == "match_nonprofits":
                    # Execute matching logic
                    matched_orgs = LLMService._match_nonprofits(conversation_history)
                    orgs = matched_orgs
                    
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps([org.dict() for org in matched_orgs]),
                    })
                
                elif function_name == "extract_responses":
                    # Extract responses from conversation
                    question_responses = function_args.get("question_responses", {})
                    # Store these responses (you'll implement this in application service)
                    # For now, just acknowledge
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps({"status": "extracted", "responses": question_responses}),
                    })
            
            # If we have tool results, make a follow-up call to get the final message
            if tool_results:
                messages.append(assistant_message)
                messages.extend(tool_results)
                
                # Get final response
                final_response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=LLMService.TOOLS,
                )
                
                final_message = final_response.choices[0].message
                message_content = final_message.content or message_content
        
        return {
            "message": message_content,
            "model": model,
            "tool_calls": tool_calls,
            "orgs": orgs,
        }

    @staticmethod
    def _match_nonprofits(conversation_history: list[dict]) -> list[OrgSummary]:
        """
        Match nonprofits based on conversation history.
        This is a simplified version - you can enhance with semantic search/embeddings.
        
        For now, returns all orgs converted to OrgSummary format.
        You can implement more sophisticated matching later.
        """
        # Get all organizations
        organizations = org_repository.get_all()
        
        if not organizations:
            # Return empty list if no organizations found
            return []
        
        # Convert Organization to OrgSummary format
        # For now, use organization_name as name, description as description
        # You can enhance this matching logic with embeddings/semantic search
        orgs = [
            OrgSummary(
                id=org.id,
                name=org.organization_name,
                description=org.description or f"{org.program_name} - {org.organization_name}",
            )
            for org in organizations[:3]  # Return top 3 for now
        ]
        
        # TODO: Implement semantic matching based on conversation_history
        # - Use embeddings to match conversation content with org descriptions
        # - Rank by relevance
        # - Return top 3
        
        return orgs


__all__ = ["LLMService"]
