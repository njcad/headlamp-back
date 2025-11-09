"""Prompt for matching nonprofits based on conversation history."""


def get_matching_prompt(conversation_text: str, orgs_text: str) -> str:
    """
    Generate the prompt for matching nonprofits to a person's needs.
    
    Args:
        conversation_text: Formatted conversation history as text
        orgs_text: Formatted list of available organizations with details
    
    Returns:
        Matching prompt string
    """
    return f"""Based on the following conversation with a person seeking help, identify the top 3 most relevant nonprofit organizations from the list below.

CONVERSATION:
{conversation_text}

AVAILABLE ORGANIZATIONS:
{orgs_text}

Analyze the person's needs, situation, and what they're looking for. Then select the 3 organizations that would be most helpful for them. Consider:
- How well the organization's services match their needs
- The type of help they're seeking
- Any specific requirements or circumstances mentioned
- The organization's description and program focus

Return the IDs of the top 3 most relevant organizations, ranked from most to least relevant."""


def format_organizations(organizations: list) -> str:
    """
    Format a list of Organization objects into text for the prompt.
    
    Args:
        organizations: List of Organization model instances
    
    Returns:
        Formatted text string with organization details
    """
    return "\n\n".join([
        f"ID: {org.id}\n"
        f"Organization: {org.organization_name}\n"
        f"Program: {org.program_name}\n"
        f"Description: {org.description or 'No description available'}\n"
        f"Services: {', '.join([str(qid) for qid in org.intake_question_ids]) if org.intake_question_ids else 'N/A'}"
        for org in organizations
    ])


def format_conversation_history(conversation_history: list[dict]) -> str:
    """
    Format conversation history into readable text.
    
    Args:
        conversation_history: List of messages in OpenAI format
    
    Returns:
        Formatted conversation text
    """
    return "\n".join([
        f"{msg['role'].title()}: {msg['content']}"
        for msg in conversation_history
    ])


__all__ = ["get_matching_prompt", "format_organizations", "format_conversation_history"]

