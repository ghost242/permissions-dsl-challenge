"""Unit tests for Evaluator component.

Tests permission evaluation logic, policy precedence, and URN handling.
"""

from datetime import datetime

import pytest

from src.components.evaluator import EvaluationResult, Evaluator
from src.models.common import Effect, Filter, FilterOperator, Permission
from src.models.entities import (Document, Project, ProjectMembership, Team,
                                 TeamMembership, User)
from src.models.policies import (ResourceInfo, ResourcePolicy,
                                 ResourcePolicyDocument)


class TestURNHandling:
    """Test URN parsing and building."""

    def test_extract_urn_components_valid(self):
        """Test extracting components from valid URN."""
        urn = "urn:resource:team1:proj1:doc1"
        team_id, project_id, doc_id = Evaluator.extract_urn_components(urn)

        assert team_id == "team1"
        assert project_id == "proj1"
        assert doc_id == "doc1"

    def test_extract_urn_components_invalid_format(self):
        """Test extracting components from invalid URN."""
        invalid_urns = [
            "not-a-urn",
            "urn:resource:team1",
            "urn:resource:team1:proj1",
            "resource:team1:proj1:doc1",
        ]

        for urn in invalid_urns:
            team_id, project_id, doc_id = Evaluator.extract_urn_components(urn)
            assert team_id is None
            assert project_id is None
            assert doc_id is None

    def test_build_resource_urn(self):
        """Test building URN from components."""
        urn = Evaluator.build_resource_urn("team1", "proj1", "doc1")
        assert urn == "urn:resource:team1:proj1:doc1"


class TestPolicyPrecedence:
    """Test policy precedence rules (DENY > ALLOW > default DENY)."""

    def setup_method(self):
        """Setup test instances."""
        self.evaluator = Evaluator()
        self.user = User(id="user1", email="test@example.com", name="Test User")
        self.document = Document(
            id="doc1",
            title="Test Doc",
            projectId="proj1",
            creatorId="user2",
            deletedAt=None,
            publicLinkEnabled=False,
        )

    def test_deny_policy_overrides_allow(self):
        """Test that DENY policy takes precedence over ALLOW."""
        # Create policies: one ALLOW, one DENY
        policy_doc = ResourcePolicyDocument(
            resource=ResourceInfo(
                resourceId="urn:resource:team1:proj1:doc1", creatorId="user2"
            ),
            policies=[
                ResourcePolicy(
                    description="Allow all",
                    permissions=[Permission.CAN_VIEW, Permission.CAN_EDIT],
                    effect=Effect.ALLOW,
                    filter=[],  # No filter, always matches
                ),
                ResourcePolicy(
                    description="Deny edit",
                    permissions=[Permission.CAN_EDIT],
                    effect=Effect.DENY,
                    filter=[],  # No filter, always matches
                ),
            ],
        )

        result = self.evaluator.evaluate_permission(
            user=self.user,
            document=self.document,
            permission=Permission.CAN_EDIT,
            resource_policy=policy_doc,
        )

        assert result.allowed is False  # DENY wins
        assert "Deny" in result.message

    def test_allow_policy_grants_access(self):
        """Test that ALLOW policy grants access when no DENY."""
        policy_doc = ResourcePolicyDocument(
            resource=ResourceInfo(
                resourceId="urn:resource:team1:proj1:doc1", creatorId="user2"
            ),
            policies=[
                ResourcePolicy(
                    description="Allow view",
                    permissions=[Permission.CAN_VIEW],
                    effect=Effect.ALLOW,
                    filter=[],
                )
            ],
        )

        result = self.evaluator.evaluate_permission(
            user=self.user,
            document=self.document,
            permission=Permission.CAN_VIEW,
            resource_policy=policy_doc,
        )

        assert result.allowed is True
        assert "Allow" in result.message

    def test_default_deny_when_no_policies(self):
        """Test default DENY when no policies match."""
        policy_doc = ResourcePolicyDocument(
            resource=ResourceInfo(
                resourceId="urn:resource:team1:proj1:doc1", creatorId="user2"
            ),
            policies=[],
        )

        result = self.evaluator.evaluate_permission(
            user=self.user,
            document=self.document,
            permission=Permission.CAN_VIEW,
            resource_policy=policy_doc,
        )

        assert result.allowed is False
        assert "No matching policy" in result.message


class TestContextBuilding:
    """Test context building from entities."""

    def setup_method(self):
        """Setup test instances."""
        self.evaluator = Evaluator()

    def test_build_context_with_all_entities(self):
        """Test building context with all entities."""
        user = User(id="user1", email="test@example.com", name="Test")
        document = Document(
            id="doc1",
            title="Test",
            projectId="proj1",
            creatorId="user1",
            deletedAt=None,
            publicLinkEnabled=False,
        )
        team = Team(id="team1", name="Team", plan="pro")
        project = Project(
            id="proj1", name="Project", teamId="team1", visibility="private"
        )
        team_membership = TeamMembership(userId="user1", teamId="team1", role="admin")
        project_membership = ProjectMembership(
            userId="user1", projectId="proj1", role="editor"
        )

        context = self.evaluator._build_context(
            user=user,
            document=document,
            team=team,
            project=project,
            team_membership=team_membership,
            project_membership=project_membership,
        )

        assert "user" in context
        assert context["user"]["id"] == "user1"
        assert "document" in context
        assert "team" in context
        assert "project" in context
        assert "teamMembership" in context
        assert "projectMembership" in context

    def test_build_context_with_minimal_entities(self):
        """Test building context with only required entities."""
        user = User(id="user1", email="test@example.com", name="Test")
        document = Document(
            id="doc1",
            title="Test",
            projectId="proj1",
            creatorId="user1",
            deletedAt=None,
            publicLinkEnabled=False,
        )

        context = self.evaluator._build_context(user=user, document=document)

        assert "user" in context
        assert "document" in context
        assert "team" not in context
        assert "project" not in context


class TestPermissionEvaluation:
    """Test permission evaluation with various scenarios."""

    def setup_method(self):
        """Setup test instances."""
        self.evaluator = Evaluator()

    def test_evaluate_permission_allow(self):
        """Test permission evaluation that allows access."""
        user = User(id="user1", email="test@example.com", name="Test")
        document = Document(
            id="doc1",
            title="Test",
            projectId="proj1",
            creatorId="user1",
            deletedAt=None,
            publicLinkEnabled=False,
        )

        policy_doc = ResourcePolicyDocument(
            resource=ResourceInfo(
                resourceId="urn:resource:team1:proj1:doc1", creatorId="user1"
            ),
            policies=[
                ResourcePolicy(
                    description="Creator access",
                    permissions=[Permission.CAN_VIEW, Permission.CAN_EDIT],
                    effect=Effect.ALLOW,
                    filter=[
                        Filter(
                            prop="document.creatorId",
                            op=FilterOperator.EQ,
                            value="user.id",
                        )
                    ],
                )
            ],
        )

        result = self.evaluator.evaluate_permission(
            user=user,
            document=document,
            permission=Permission.CAN_VIEW,
            resource_policy=policy_doc,
        )

        assert result.allowed is True

    def test_evaluate_permission_deny(self):
        """Test permission evaluation that denies access."""
        user = User(id="user1", email="test@example.com", name="Test")
        document = Document(
            id="doc1",
            title="Test",
            projectId="proj1",
            creatorId="user2",  # Different creator
            deletedAt=None,
            publicLinkEnabled=False,
        )

        policy_doc = ResourcePolicyDocument(
            resource=ResourceInfo(
                resourceId="urn:resource:team1:proj1:doc1", creatorId="user2"
            ),
            policies=[
                ResourcePolicy(
                    description="Creator only",
                    permissions=[Permission.CAN_VIEW],
                    effect=Effect.ALLOW,
                    filter=[
                        Filter(
                            prop="document.creatorId",
                            op=FilterOperator.EQ,
                            value="user.id",
                        )
                    ],
                )
            ],
        )

        result = self.evaluator.evaluate_permission(
            user=user,
            document=document,
            permission=Permission.CAN_VIEW,
            resource_policy=policy_doc,
        )

        assert result.allowed is False

    def test_evaluate_permission_deleted_document(self):
        """Test that deleted documents deny all access."""
        user = User(id="user1", email="test@example.com", name="Test")
        document = Document(
            id="doc1",
            title="Test",
            projectId="proj1",
            creatorId="user1",
            deletedAt=datetime(2025, 1, 1),  # Deleted
            publicLinkEnabled=False,
        )

        policy_doc = ResourcePolicyDocument(
            resource=ResourceInfo(
                resourceId="urn:resource:team1:proj1:doc1", creatorId="user1"
            ),
            policies=[
                ResourcePolicy(
                    description="Creator access",
                    permissions=[Permission.CAN_VIEW],
                    effect=Effect.ALLOW,
                    filter=[],
                )
            ],
        )

        result = self.evaluator.evaluate_permission(
            user=user,
            document=document,
            permission=Permission.CAN_VIEW,
            resource_policy=policy_doc,
        )

        assert result.allowed is False
        assert "deleted" in result.message.lower()

    def test_evaluate_permission_with_filter_match(self):
        """Test evaluation with matching filter."""
        user = User(id="user1", email="test@example.com", name="Test")
        document = Document(
            id="doc1",
            title="Test",
            projectId="proj1",
            creatorId="user1",
            deletedAt=None,
            publicLinkEnabled=False,
        )
        team_membership = TeamMembership(userId="user1", teamId="team1", role="admin")

        policy_doc = ResourcePolicyDocument(
            resource=ResourceInfo(
                resourceId="urn:resource:team1:proj1:doc1", creatorId="user2"
            ),
            policies=[
                ResourcePolicy(
                    description="Admin access",
                    permissions=[Permission.CAN_VIEW],
                    effect=Effect.ALLOW,
                    filter=[
                        Filter(
                            prop="teamMembership.role",
                            op=FilterOperator.EQ,
                            value="admin",
                        )
                    ],
                )
            ],
        )

        result = self.evaluator.evaluate_permission(
            user=user,
            document=document,
            permission=Permission.CAN_VIEW,
            resource_policy=policy_doc,
            team_membership=team_membership,
        )

        assert result.allowed is True

    def test_evaluate_permission_with_filter_no_match(self):
        """Test evaluation with non-matching filter."""
        user = User(id="user1", email="test@example.com", name="Test")
        document = Document(
            id="doc1",
            title="Test",
            projectId="proj1",
            creatorId="user2",
            deletedAt=None,
            publicLinkEnabled=False,
        )
        team_membership = TeamMembership(userId="user1", teamId="team1", role="viewer")

        policy_doc = ResourcePolicyDocument(
            resource=ResourceInfo(
                resourceId="urn:resource:team1:proj1:doc1", creatorId="user2"
            ),
            policies=[
                ResourcePolicy(
                    description="Admin only",
                    permissions=[Permission.CAN_VIEW],
                    effect=Effect.ALLOW,
                    filter=[
                        Filter(
                            prop="teamMembership.role",
                            op=FilterOperator.EQ,
                            value="admin",
                        )
                    ],
                )
            ],
        )

        result = self.evaluator.evaluate_permission(
            user=user,
            document=document,
            permission=Permission.CAN_VIEW,
            resource_policy=policy_doc,
            team_membership=team_membership,
        )

        assert result.allowed is False
