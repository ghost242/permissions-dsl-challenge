"""Unit tests for Builder component."""

import pytest
from src.components.builder import Builder, PolicyOptions
from src.models.common import Permission, Effect
from src.models.policies import ResourcePolicyDocument


class TestPolicyBuilding:
    """Test policy document building."""

    def setup_method(self):
        """Setup test instance."""
        self.builder = Builder()

    def test_build_from_policy_options(self):
        """Test building from simple PolicyOptions."""
        options = PolicyOptions(
            resourceId="urn:resource:team1:proj1:doc1",
            action=Permission.CAN_EDIT,
            target="user123"
        )

        result = self.builder.build_policy_document(options, creator_id="creator1")

        assert isinstance(result, ResourcePolicyDocument)
        assert result.resource.resourceId == "urn:resource:team1:proj1:doc1"
        assert len(result.policies) == 1
        assert Permission.CAN_EDIT in result.policies[0].permissions
        assert result.policies[0].effect == Effect.ALLOW

    def test_build_from_full_document(self):
        """Test that full documents pass through unchanged."""
        doc = ResourcePolicyDocument(
            resource={"resourceId": "urn:resource:team1:proj1:doc1", "creatorId": "user1"},
            policies=[]
        )

        result = self.builder.build_policy_document(doc)
        assert result == doc

    def test_create_creator_policy(self):
        """Test creating default creator policy."""
        policy_doc = self.builder.create_creator_policy("urn:resource:team1:proj1:doc1", "user1")

        assert len(policy_doc.policies) == 1
        policy = policy_doc.policies[0]
        assert Permission.CAN_VIEW in policy.permissions
        assert Permission.CAN_EDIT in policy.permissions
        assert Permission.CAN_DELETE in policy.permissions
        assert Permission.CAN_SHARE in policy.permissions
        assert policy.effect == Effect.ALLOW

    def test_create_team_admin_policy(self):
        """Test creating team admin policy."""
        policy_doc = self.builder.create_team_admin_policy("urn:resource:team1:proj1:doc1", "user1")

        policy = policy_doc.policies[0]
        assert "admin" in policy.description.lower()
        assert len(policy.filter) > 0

    def test_create_public_view_policy(self):
        """Test creating public view policy."""
        policy_doc = self.builder.create_public_view_policy("urn:resource:team1:proj1:doc1", "user1")

        policy = policy_doc.policies[0]
        assert Permission.CAN_VIEW in policy.permissions
        assert len(policy.permissions) == 1  # Only view
        assert policy.effect == Effect.ALLOW
