from typing import Optional
from uuid import UUID

from models.application import Application
from models.application_draft import ApplicationDraft
from models.org import OrgSummary
from prompts.intake import get_intake_questions
from repos import application_repository, org_repository
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
        # Get all essential information fields (from prompts/intake.py - same fields used in system prompt)
        intake_questions = get_intake_questions()
        
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
    async def get_user_applications(user_id: UUID) -> list[dict]:
        """
        Get all applications for a user with organization details.
        
        Returns list of dicts with 'application' and 'organization' keys.
        """
        # Get applications with joined organization data
        applications_data = application_repository.get_by_user_id_with_orgs(user_id)
        
        result = []
        for app_data in applications_data:
            # Extract organization data from the joined response
            # Supabase returns joined data in a nested structure
            org_data = app_data.get("services")
            if not org_data:
                # If join failed, skip this application
                continue
            
            # Handle case where services might be a list (if multiple matches) or a dict
            if isinstance(org_data, list) and len(org_data) > 0:
                org_data = org_data[0]
            elif not isinstance(org_data, dict):
                continue
            
            # Create Application model
            application = Application(
                id=app_data["id"],
                user_id=app_data["user_id"],
                organization_id=app_data["organization_id"],
                urgent=app_data.get("urgent", False),
                content=app_data["content"],
                submitted_at=app_data["submitted_at"],
                opened_at=app_data.get("opened_at"),
                accepted_at=app_data.get("accepted_at"),
                denied_at=app_data.get("denied_at"),
            )
            
            # Create OrgSummary from organization data
            organization = OrgSummary(
                id=org_data.get("id"),
                name=org_data.get("organization_name", ""),
                description=org_data.get("description") or f"{org_data.get('program_name', '')} - {org_data.get('organization_name', '')}",
            )
            
            # Return dict with both application and organization
            result.append({
                "application": application,
                "organization": organization,
            })
        
        return result

    @staticmethod
    async def get_organization_applications(organization_id: int) -> list[Application]:
        return application_repository.get_by_organization_id(organization_id)

__all__ = ["ApplicationService"]

