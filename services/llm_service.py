
import json
from typing import Optional

from openai import AsyncOpenAI

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
        # Initialize async OpenAI client
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
        
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
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
        response = await client.chat.completions.create(
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
                    matched_orgs = await LLMService._match_nonprofits(conversation_history)
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
                final_response = await client.chat.completions.create(
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
    async def _match_nonprofits(conversation_history: list[dict]) -> list[OrgSummary]:
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
        
        # Initialize async OpenAI client
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
        
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
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
        
        response = await client.chat.completions.create(
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

    @staticmethod
    async def generate_application_content(
        conversation_history: list[dict],
        intake_questions: list,
        organization_name: str,
    ) -> str:
        """
        Generate application content from conversation history and intake questions.
        
        The content includes:
        - A brief summary of the applicant's situation
        - Question: Answer pairs for questions that can be answered from the conversation
        
        Args:
            conversation_history: List of messages in OpenAI format
            intake_questions: List of IntakeQuestion objects
            organization_name: Name of the organization the application is for
        
        Returns:
            Formatted application content string
        """
        # Initialize async OpenAI client
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
        
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Format conversation history
        conversation_text = format_conversation_history(conversation_history)
        
        # Format intake questions
        questions_text = "\n".join([
            f"{i+1}. {q.question}"
            for i, q in enumerate(intake_questions)
        ])
        
        # Create prompt for generating application content
        application_prompt = f"""Based on the following conversation with an applicant, generate a professional application document for {organization_name}.

CONVERSATION HISTORY:
{conversation_text}

INTAKE QUESTIONS TO ANSWER:
{questions_text}

Please generate an application document that includes:
1. A brief summary (2-3 sentences) of the applicant's situation and what they need help with
2. A section with "Question: Answer" pairs for each intake question that can be answered from the conversation history
3. For questions that cannot be answered from the conversation, you may write "Not discussed" or omit them

Format the response as a clear, professional document suitable for a nonprofit organization to review. Use clear headings and formatting."""

        # Call OpenAI API
        model = "gpt-4"
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates professional application documents for nonprofit organizations based on conversation history.",
                },
                {"role": "user", "content": application_prompt},
            ],
        )
        
        # Extract response content
        application_content = response.choices[0].message.content or ""
        
        if not application_content:
            # Fallback if empty response
            application_content = "Application generated from conversation history. Please review the conversation for details."
        
        return application_content

    @staticmethod
    async def generate_application_summary(conversation_history: list[dict]) -> str:
        """
        Generate a brief summary of the applicant's situation from conversation history.
        
        Args:
            conversation_history: List of messages in OpenAI format
        
        Returns:
            Brief summary string (2-3 sentences)
        """
        # Initialize async OpenAI client
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
        
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Format conversation history
        conversation_text = format_conversation_history(conversation_history)
        
        # Create prompt for generating summary
        summary_prompt = f"""Based on the following conversation, write a brief summary (2-3 sentences) of the person's situation and what they need help with.

CONVERSATION HISTORY:
{conversation_text}

Write a concise, professional summary that captures:
- Their current situation
- What kind of help or services they need
- Any urgent or important details

Keep it to 2-3 sentences."""

        # Call OpenAI API
        model = "gpt-4"
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates concise summaries of people's situations and needs.",
                },
                {"role": "user", "content": summary_prompt},
            ],
        )
        
        # Extract response content
        summary = response.choices[0].message.content or ""
        
        if not summary:
            # Fallback if empty response
            summary = "Summary of applicant's situation and needs."
        
        return summary

    @staticmethod
    async def extract_contact_info(conversation_history: list[dict]) -> dict[str, str]:
        """
        Extract contact information (name, phone, email) from conversation history.
        
        Args:
            conversation_history: List of messages in OpenAI format
        
        Returns:
            Dictionary with 'name', 'phone', and 'email' keys (empty strings if not found)
        """
        # Initialize async OpenAI client
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
        
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Format conversation history
        conversation_text = format_conversation_history(conversation_history)
        
        # Create prompt for extracting contact info
        contact_prompt = f"""Based on the following conversation, extract the person's contact information.

CONVERSATION HISTORY:
{conversation_text}

Extract the following information if mentioned:
- Full name (or first name if that's all that's provided)
- Phone number
- Email address

If any information is not mentioned in the conversation, return an empty string for that field."""

        # Define function for structured output using tool calling
        extract_contact_function = {
            "type": "function",
            "function": {
                "name": "extract_contact_information",
                "description": "Extract contact information (name, phone, email) from the conversation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Full name or first name of the person. Empty string if not mentioned.",
                        },
                        "phone": {
                            "type": "string",
                            "description": "Phone number of the person. Empty string if not mentioned.",
                        },
                        "email": {
                            "type": "string",
                            "description": "Email address of the person. Empty string if not mentioned.",
                        },
                    },
                    "required": ["name", "phone", "email"],
                },
            },
        }

        # Call OpenAI API with tool calling
        model = "gpt-4"
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that extracts contact information from conversations.",
                },
                {"role": "user", "content": contact_prompt},
            ],
            tools=[extract_contact_function],
            tool_choice={"type": "function", "function": {"name": "extract_contact_information"}},
        )
        
        # Extract contact info from tool call
        try:
            tool_call = response.choices[0].message.tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            return {
                "name": function_args.get("name", ""),
                "phone": function_args.get("phone", ""),
                "email": function_args.get("email", ""),
            }
        except (IndexError, KeyError, json.JSONDecodeError, AttributeError) as e:
            # Fallback if tool call extraction fails
            print(f"Error extracting contact info from tool call: {e}")
            return {
                "name": "",
                "phone": "",
                "email": "",
            }


__all__ = ["LLMService"]
