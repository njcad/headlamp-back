from repos.supabase import get_supabase_client
from models.intake_question import IntakeQuestion


def get_all() -> list[IntakeQuestion]:
    """Retrieve all intake questions from the database."""
    client = get_supabase_client()
    
    response = client.table("intake_questions").select("*").order("id").execute()
    
    return [IntakeQuestion(**row) for row in response.data]


__all__ = ["get_all"]

