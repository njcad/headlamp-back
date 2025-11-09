
import json
from typing import Optional

from openai import OpenAI

from config import settings
from models.org import OrgSummary
from prompts.intake import get_intake_system_prompt
from prompts.matching import (
    format_conversation_history,
    format_organizations,
    get_matching_prompt,
)
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
        Match nonprofits based on conversation history using semantic matching.
        
        Uses the matching prompt to analyze the conversation and identify the top 3
        most relevant organizations based on the person's needs and situation.
        
        Args:
            conversation_history: List of messages in OpenAI format
        
        Returns:
            List of top 3 most relevant organizations as OrgSummary objects
        """
        # Get all organizations
        organizations = org_repository.get_all()
        
        if not organizations:
            # Return empty list if no organizations found
            return []
        
        # If we have 3 or fewer organizations, just return all of them
        # (no need for LLM matching when there are so few options)
        if len(organizations) <= 3:
            return [
                OrgSummary(
                    id=org.id,
                    name=org.organization_name,
                    description=org.description or f"{org.program_name} - {org.organization_name}",
                )
                for org in organizations
            ]
        
        # Initialize OpenAI client
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
        
        client = OpenAI(api_key=settings.openai_api_key)
        
        # Format conversation history and organizations
        conversation_text = format_conversation_history(conversation_history)
        orgs_text = format_organizations(organizations)
        
        # Create the matching prompt
        matching_prompt = get_matching_prompt(conversation_text, orgs_text)
        
        # Call OpenAI API to get top 3 org IDs using tool calling
        model = "gpt-4"
        
        # Define function for structured output
        match_function = {
            "type": "function",
            "function": {
                "name": "select_top_organizations",
                "description": "Select the top 3 most relevant organization IDs based on the conversation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "organization_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Array of exactly 3 organization IDs, ranked from most to least relevant. Must return exactly 3 IDs.",
                            "minItems": 3,
                            "maxItems": 3,
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Brief explanation of why these organizations were selected",
                        },
                    },
                    "required": ["organization_ids", "reasoning"],
                },
            },
        }
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at matching people with appropriate nonprofit organizations based on their needs and circumstances.",
                },
                {"role": "user", "content": matching_prompt},
            ],
            tools=[match_function],
            tool_choice={"type": "function", "function": {"name": "select_top_organizations"}},
        )
        
        # Extract organization IDs from tool call
        try:
            tool_call = response.choices[0].message.tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            org_ids = function_args["organization_ids"]
            
            # Validate we got exactly 3 IDs
            if len(org_ids) != 3:
                # Fallback: return first 3 organizations
                org_ids = [org.id for org in organizations[:3]]
        except (IndexError, KeyError, json.JSONDecodeError, AttributeError) as e:
            # Fallback: return first 3 organizations if tool call fails
            print(f"Error extracting tool call: {e}")
            org_ids = [org.id for org in organizations[:3]]
        
        # Create a mapping of org ID to Organization for quick lookup
        org_map = {org.id: org for org in organizations}
        
        # Get the matched organizations in order
        matched_orgs = []
        for org_id in org_ids:
            if org_id in org_map:
                org = org_map[org_id]
                matched_orgs.append(
                    OrgSummary(
                        id=org.id,
                        name=org.organization_name,
                        description=org.description
                        or f"{org.program_name} - {org.organization_name}",
                    )
                )
        
        # If we didn't get 3 valid orgs, fill with remaining orgs (fallback)
        if len(matched_orgs) < 3:
            remaining_ids = set(org_map.keys()) - set(org_ids)
            for org_id in list(remaining_ids)[: 3 - len(matched_orgs)]:
                org = org_map[org_id]
                matched_orgs.append(
                    OrgSummary(
                        id=org.id,
                        name=org.organization_name,
                        description=org.description
                        or f"{org.program_name} - {org.organization_name}",
                    )
                )
        
        return matched_orgs[:3]


__all__ = ["LLMService"]
