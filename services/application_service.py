from typing import Optional
from uuid import UUID

from models.application import Application
from models.application_draft import ApplicationDraft
from models.intake_question import IntakeQuestion
from models.org import OrgSummary
from repos import application_repository, intake_question_repository, org_repository
from services.llm_service import LLMService


class ApplicationService:
    """
    Handles application creation logic:
    - Generates application drafts from conversation history
    - Creates application records for selected organizations
    """

    @staticmethod
    async def create_application_draft(
        organization_ids: list[int],
        conversation_history: list[dict],
    ) -> ApplicationDraft:
        """
        Create an application draft for the given organization IDs.
        Generates content for each organization but doesn't save to database.
        
        Args:
            organization_ids: List of organization IDs to create drafts for
            conversation_history: Full conversation history in OpenAI format
        
        Returns:
            ApplicationDraft with summary and content for each organization
        """
        # Get all intake questions (not filtered by org - answer all questions)
        intake_questions = intake_question_repository.get_all()
        
        # Get all organizations to validate IDs and get their details
        all_orgs = org_repository.get_all()
        org_dict = {org.id: org for org in all_orgs}
        
        # Extract contact information from conversation
        contact_info = await LLMService.extract_contact_info(conversation_history)
        
        # Generate ONE unified application content that answers ALL intake questions
        # (not org-specific - answers as many questions as possible from conversation)
        # This will be stored in the summary field for the frontend
        application_content = await LLMService.generate_application_content(
            conversation_history=conversation_history,
            intake_questions=intake_questions,  # All questions, not filtered
            organization_name="selected organizations",  # Generic since it's for all orgs
        )
        
        # Build list of organization summaries
        org_summaries = []
        
        for org_id in organization_ids:
            # Validate organization exists
            if org_id not in org_dict:
                print(f"Warning: Organization {org_id} not found, skipping draft creation")
                continue
            
            organization = org_dict[org_id]
            
            # Add org summary for response
            org_summaries.append(
                OrgSummary(
                    id=organization.id,
                    name=organization.organization_name,
                    description=organization.description or f"{organization.program_name} - {organization.organization_name}",
                )
            )
        
        return ApplicationDraft(
            name=contact_info.get("name", ""),
            phone=contact_info.get("phone", ""),
            email=contact_info.get("email"),
            summary=application_content,
            organizations=org_summaries,
        )

    @staticmethod
    async def create_applications(
        user_id: UUID,
        organization_ids: list[int],
        application_draft: Optional[ApplicationDraft] = None,
    ) -> list[Application]:
        """
        Create applications for the given organization IDs.
        
        Uses the application_draft if provided (which may have been modified by the user),
        otherwise falls back to generating from conversation history.
        
        Args:
            user_id: The user creating the applications
            organization_ids: List of organization IDs to create applications for
            application_draft: Optional draft containing user-modified application content
        
        Returns:
            List of created Application objects
        """
        # Get all organizations to validate IDs and get their details
        all_orgs = org_repository.get_all()
        org_dict = {org.id: org for org in all_orgs}
        
        created_applications = []
        
        # Use application content from draft if provided (user may have modified it)
        if not application_draft:
            raise ValueError("application_draft is required when creating applications")
        
        # Build application content with contact information from the draft
        # The user may have modified name, phone, email, or the summary content
        contact_section = ""
        if application_draft.name or application_draft.phone or application_draft.email:
            contact_section = "CONTACT INFORMATION:\n"
            if application_draft.name:
                contact_section += f"Name: {application_draft.name}\n"
            if application_draft.phone:
                contact_section += f"Phone: {application_draft.phone}\n"
            if application_draft.email:
                contact_section += f"Email: {application_draft.email}\n"
            contact_section += "\n"
        
        # Combine contact info with the modified application content
        application_content = contact_section + application_draft.summary
        
        # Create an application for each selected organization
        for org_id in organization_ids:
            # Validate organization exists
            if org_id not in org_dict:
                print(f"Warning: Organization {org_id} not found, skipping application creation")
                continue
            
            # Create application record with the draft content (including any user modifications)
            application = application_repository.create(
                user_id=user_id,
                organization_id=org_id,
                content=application_content,
            )
            
            created_applications.append(application)
        
        return created_applications

    @staticmethod
    async def get_user_applications(user_id: UUID) -> list[Application]:
        return application_repository.get_by_user_id(user_id)

    @staticmethod
    async def get_organization_applications(organization_id: int) -> list[Application]:
        return application_repository.get_by_organization_id(organization_id)

__all__ = ["ApplicationService"]

