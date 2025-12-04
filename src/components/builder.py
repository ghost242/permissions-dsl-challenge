"""Builder component for generating policy documents.

This module provides functionality to build complete policy documents from
simple options or to validate and process full policy documents.
"""

from typing import Union, Optional
from pydantic import BaseModel, Field
from src.models.common import Permission, Effect, Filter, FilterOperator
from src.models.policies import ResourcePolicyDocument, ResourcePolicy, ResourceInfo


class PolicyOptions(BaseModel):
    """Simplified input format for creating policies.

    This allows users to create policies without writing full policy documents.
    """
    resourceId: str = Field(..., description="Resource URN (e.g., urn:resource:team1:proj1:doc1)")
    action: Permission = Field(..., description="Permission to grant (can_view, can_edit, can_delete, can_share)")
    target: str = Field(..., description="Target user ID to grant permission to")
    effect: Effect = Field(default=Effect.ALLOW, description="Effect (allow or deny), defaults to allow")

    class Config:
        use_enum_values = True


class Builder:
    """Builds policy documents from simple options or validates full documents."""

    def build_policy_document(
        self,
        input_data: Union[ResourcePolicyDocument, PolicyOptions],
        creator_id: Optional[str] = None
    ) -> ResourcePolicyDocument:
        """Build or validate a policy document.

        If input is PolicyOptions (simple format), generates a complete policy document.
        If input is ResourcePolicyDocument (full format), validates and returns it.

        Args:
            input_data: Either PolicyOptions (simple) or ResourcePolicyDocument (full)
            creator_id: Optional creator ID (only needed if not in resourceId extraction)

        Returns:
            Complete ResourcePolicyDocument

        Example:
            Simple format:
                options = PolicyOptions(
                    resourceId="urn:resource:team1:proj1:doc1",
                    action="can_edit",
                    target="user123"
                )
                doc = builder.build_policy_document(options)

            Full format:
                doc = ResourcePolicyDocument(
                    resource=ResourceInfo(resourceId="...", creatorId="..."),
                    policies=[...]
                )
                validated_doc = builder.build_policy_document(doc)
        """
        # If already a full document, return it (already validated by Pydantic)
        if isinstance(input_data, ResourcePolicyDocument):
            return input_data

        # Build from simple options
        return self._build_from_options(input_data, creator_id)

    def _build_from_options(self, options: PolicyOptions, creator_id: Optional[str] = None) -> ResourcePolicyDocument:
        """Build a complete policy document from simple options.

        Creates a policy that grants the specified permission to the target user.

        Args:
            options: Simple policy options
            creator_id: Optional creator ID

        Returns:
            Complete ResourcePolicyDocument
        """
        # Extract creator ID from context or use provided
        # In a real implementation, this might come from the request context
        if creator_id is None:
            creator_id = "unknown"

        # Build resource info
        resource_info = ResourceInfo(
            resourceId=options.resourceId,
            creatorId=creator_id
        )

        # Build filter condition to match the target user
        filter_condition = Filter(
            prop="user.id",
            op=FilterOperator.EQ,
            value=options.target
        )

        # Build the policy
        # Handle both enum and string values (Pydantic may convert to string with use_enum_values)
        action_str = options.action.value if hasattr(options.action, 'value') else options.action
        action_perm = options.action if isinstance(options.action, Permission) else Permission(options.action)

        policy = ResourcePolicy(
            description=f"Grant {action_str} permission to user {options.target}",
            permissions=[action_perm],
            effect=options.effect,
            filter=[filter_condition]
        )

        # Build complete document
        return ResourcePolicyDocument(
            resource=resource_info,
            policies=[policy]
        )

    def merge_policies(
        self,
        existing_doc: Optional[ResourcePolicyDocument],
        new_doc: ResourcePolicyDocument
    ) -> ResourcePolicyDocument:
        """Merge new policies with existing policy document.

        Args:
            existing_doc: Existing policy document (or None if creating new)
            new_doc: New policy document to merge

        Returns:
            Merged policy document
        """
        if existing_doc is None:
            return new_doc

        # Merge policies (append new ones)
        merged_policies = existing_doc.policies + new_doc.policies

        # Return updated document
        return ResourcePolicyDocument(
            resource=existing_doc.resource,
            policies=merged_policies
        )

    def create_creator_policy(self, resource_id: str, creator_id: str) -> ResourcePolicyDocument:
        """Create a default policy granting full access to the creator.

        This is useful for initializing policies when a new resource is created.

        Args:
            resource_id: Resource URN
            creator_id: Creator user ID

        Returns:
            Policy document with full creator access
        """
        resource_info = ResourceInfo(
            resourceId=resource_id,
            creatorId=creator_id
        )

        # Filter: document.creatorId == user.id
        filter_condition = Filter(
            prop="document.creatorId",
            op=FilterOperator.EQ,
            value="user.id"
        )

        # Policy granting all permissions to creator
        creator_policy = ResourcePolicy(
            description="Creator has full access",
            permissions=[
                Permission.CAN_VIEW,
                Permission.CAN_EDIT,
                Permission.CAN_DELETE,
                Permission.CAN_SHARE
            ],
            effect=Effect.ALLOW,
            filter=[filter_condition]
        )

        return ResourcePolicyDocument(
            resource=resource_info,
            policies=[creator_policy]
        )

    def create_team_admin_policy(self, resource_id: str, creator_id: str) -> ResourcePolicyDocument:
        """Create a policy granting full access to team admins.

        Args:
            resource_id: Resource URN
            creator_id: Creator user ID

        Returns:
            Policy document with team admin access
        """
        resource_info = ResourceInfo(
            resourceId=resource_id,
            creatorId=creator_id
        )

        # Filter: teamMembership.role == "admin"
        filter_condition = Filter(
            prop="teamMembership.role",
            op=FilterOperator.EQ,
            value="admin"
        )

        # Policy granting all permissions to team admins
        admin_policy = ResourcePolicy(
            description="Team admins have full access",
            permissions=[
                Permission.CAN_VIEW,
                Permission.CAN_EDIT,
                Permission.CAN_DELETE,
                Permission.CAN_SHARE
            ],
            effect=Effect.ALLOW,
            filter=[filter_condition]
        )

        return ResourcePolicyDocument(
            resource=resource_info,
            policies=[admin_policy]
        )

    def create_public_view_policy(self, resource_id: str, creator_id: str) -> ResourcePolicyDocument:
        """Create a policy allowing public view access when public link is enabled.

        Args:
            resource_id: Resource URN
            creator_id: Creator user ID

        Returns:
            Policy document with public view access
        """
        resource_info = ResourceInfo(
            resourceId=resource_id,
            creatorId=creator_id
        )

        # Filter: document.publicLinkEnabled == true
        filter_condition = Filter(
            prop="document.publicLinkEnabled",
            op=FilterOperator.EQ,
            value=True
        )

        # Policy granting view permission when public link enabled
        public_policy = ResourcePolicy(
            description="Public view access when link is enabled",
            permissions=[Permission.CAN_VIEW],
            effect=Effect.ALLOW,
            filter=[filter_condition]
        )

        return ResourcePolicyDocument(
            resource=resource_info,
            policies=[public_policy]
        )
