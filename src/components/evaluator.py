"""Evaluator component for permission evaluation.

This module implements the core permission evaluation logic that determines
whether a user has a specific permission on a resource.
"""

import re
from typing import Any

from src.components.filter_engine import FilterEngine
from src.models.common import Effect, Permission
from src.models.entities import (
    Document,
    Project,
    ProjectMembership,
    Team,
    TeamMembership,
    User,
)
from src.models.policies import ResourcePolicyDocument, UserPolicyDocument


class EvaluationResult:
    """Result of a permission evaluation."""

    def __init__(
        self, allowed: bool, message: str, matched_policies: list[str] | None = None
    ):
        self.allowed = allowed
        self.message = message
        self.matched_policies = matched_policies or []


class Evaluator:
    """Evaluates permissions based on policies and context."""

    def __init__(self):
        self.filter_engine = FilterEngine()

    def evaluate_permission(
        self,
        user: User,
        document: Document,
        permission: Permission,
        resource_policy: ResourcePolicyDocument | None = None,
        user_policy: UserPolicyDocument | None = None,
        team: Team | None = None,
        project: Project | None = None,
        team_membership: TeamMembership | None = None,
        project_membership: ProjectMembership | None = None,
    ) -> EvaluationResult:
        """Evaluate if a user has a specific permission on a document.

        Policy Precedence (highest to lowest):
        1. Explicit DENY policies (from resource or user policies)
        2. Explicit ALLOW policies (from resource or user policies)
        3. Default DENY (if no matching policies found)

        Args:
            user: The user requesting permission
            document: The document being accessed
            permission: The permission being requested
            resource_policy: Optional resource-specific policy document
            user_policy: Optional user-specific policy document
            team: Optional team that owns the project
            project: Optional project that owns the document
            team_membership: Optional user's team membership
            project_membership: Optional user's project membership

        Returns:
            EvaluationResult: The evaluation result with allow/deny decision
        """
        # Check if document is deleted
        if document.is_deleted:
            return EvaluationResult(
                allowed=False, message="Deny: Document is deleted", matched_policies=[]
            )

        # Build evaluation context
        context = self._build_context(
            user=user,
            document=document,
            team=team,
            project=project,
            team_membership=team_membership,
            project_membership=project_membership,
        )

        # Collect all policies
        all_deny_policies = []
        all_allow_policies = []

        # Process resource policies
        if resource_policy:
            for idx, policy in enumerate(resource_policy.policies):
                # Check if this policy applies to the requested permission
                if permission not in policy.permissions:
                    continue

                # Evaluate filter conditions
                if policy.filter:
                    if not self.filter_engine.evaluate_filters(policy.filter, context):
                        continue

                # Policy matches - categorize by effect
                policy_name = policy.description or f"resource_policy_{idx}"
                if policy.effect == Effect.DENY:
                    all_deny_policies.append(policy_name)
                else:
                    all_allow_policies.append(policy_name)

        # Process user policies
        if user_policy:
            for idx, policy in enumerate(user_policy.policies):
                # Check if this policy applies to the requested permission
                if permission not in policy.permissions:
                    continue

                # Evaluate filter conditions
                if policy.filter:
                    if not self.filter_engine.evaluate_filters(policy.filter, context):
                        continue

                # Policy matches - categorize by effect
                policy_name = policy.description or f"user_policy_{idx}"
                if policy.effect == Effect.DENY:
                    all_deny_policies.append(policy_name)
                else:
                    all_allow_policies.append(policy_name)

        # Apply precedence rules:
        # 1. If any DENY policy matched, deny access
        if all_deny_policies:
            return EvaluationResult(
                allowed=False, message="Deny", matched_policies=all_deny_policies
            )

        # 2. If any ALLOW policy matched, allow access
        if all_allow_policies:
            return EvaluationResult(
                allowed=True, message="Allow", matched_policies=all_allow_policies
            )

        # 3. Default deny (no matching policies)
        return EvaluationResult(
            allowed=False, message="Deny: No matching policy found", matched_policies=[]
        )

    def _build_context(
        self,
        user: User,
        document: Document,
        team: Team | None = None,
        project: Project | None = None,
        team_membership: TeamMembership | None = None,
        project_membership: ProjectMembership | None = None,
    ) -> dict[str, Any]:
        """Build evaluation context from entities.

        Args:
            user: User entity
            document: Document entity
            team: Optional team entity
            project: Optional project entity
            team_membership: Optional team membership
            project_membership: Optional project membership

        Returns:
            Dictionary containing all context data for filter evaluation
        """
        context = {
            "user": user.model_dump(),
            "document": document.model_dump(),
        }

        if team:
            context["team"] = team.model_dump()

        if project:
            context["project"] = project.model_dump()

        if team_membership:
            context["teamMembership"] = team_membership.model_dump()

        if project_membership:
            context["projectMembership"] = project_membership.model_dump()

        return context

    @staticmethod
    def extract_urn_components(
        resource_urn: str,
    ) -> tuple[str | None, str | None, str | None]:
        """Extract teamId, projectId, and docId from resource URN.

        Expected format: urn:resource:{teamId}:{projectId}:{docId}

        Args:
            resource_urn: The resource URN string

        Returns:
            Tuple of (teamId, projectId, docId), or (None, None, None) if invalid

        Example:
            >>> extract_urn_components("urn:resource:team1:proj1:doc1")
            ("team1", "proj1", "doc1")
        """
        pattern = r"^urn:resource:([a-zA-Z0-9]+):([a-zA-Z0-9]+):([a-zA-Z0-9]+)$"
        match = re.match(pattern, resource_urn)

        if not match:
            return None, None, None

        return match.group(1), match.group(2), match.group(3)

    @staticmethod
    def build_resource_urn(team_id: str, project_id: str, doc_id: str) -> str:
        """Build a resource URN from component IDs.

        Args:
            team_id: Team ID
            project_id: Project ID
            doc_id: Document ID

        Returns:
            Resource URN string

        Example:
            >>> build_resource_urn("team1", "proj1", "doc1")
            "urn:resource:team1:proj1:doc1"
        """
        return f"urn:resource:{team_id}:{project_id}:{doc_id}"
