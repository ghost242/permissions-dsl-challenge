"""Unit tests for Repository (database layer)."""

from src.models.common import Effect, Permission
from src.models.policies import (ResourceInfo, ResourcePolicy,
                                 ResourcePolicyDocument)


class TestUserOperations:
    """Test user CRUD operations."""

    def test_get_user_exists(self, test_db, repository):
        """Test getting existing user."""
        # Insert test user
        cursor = test_db.get_connection().cursor()
        cursor.execute(
            "INSERT INTO users (id, email, name) VALUES (?, ?, ?)",
            ("user1", "test@example.com", "Test User"),
        )
        test_db.commit()

        user = repository.get_user("user1")
        assert user is not None
        assert user.id == "user1"
        assert user.email == "test@example.com"

    def test_get_user_not_found(self, repository):
        """Test getting non-existent user."""
        user = repository.get_user("nonexistent")
        assert user is None


class TestDocumentOperations:
    """Test document CRUD operations."""

    def test_get_document_exists(self, test_db, repository):
        """Test getting existing document."""
        # Setup: Insert user, team, project first
        cursor = test_db.get_connection().cursor()
        cursor.execute(
            "INSERT INTO users (id, email, name) VALUES (?, ?, ?)",
            ("user1", "test@example.com", "Test"),
        )
        cursor.execute(
            "INSERT INTO teams (id, name, plan) VALUES (?, ?, ?)",
            ("team1", "Team", "pro"),
        )
        cursor.execute(
            "INSERT INTO projects (id, name, team_id, visibility) VALUES (?, ?, ?, ?)",
            ("proj1", "Project", "team1", "private"),
        )
        cursor.execute(
            "INSERT INTO documents (id, title, project_id, creator_id, deleted_at, public_link_enabled) VALUES (?, ?, ?, ?, ?, ?)",
            ("doc1", "Test Doc", "proj1", "user1", None, False),
        )
        test_db.commit()

        doc = repository.get_document("doc1")
        assert doc is not None
        assert doc.id == "doc1"
        assert doc.title == "Test Doc"

    def test_get_document_with_soft_delete(self, test_db, repository):
        """Test getting soft-deleted document."""
        cursor = test_db.get_connection().cursor()
        cursor.execute(
            "INSERT INTO users (id, email, name) VALUES (?, ?, ?)",
            ("user1", "test@example.com", "Test"),
        )
        cursor.execute(
            "INSERT INTO teams (id, name, plan) VALUES (?, ?, ?)",
            ("team1", "Team", "pro"),
        )
        cursor.execute(
            "INSERT INTO projects (id, name, team_id, visibility) VALUES (?, ?, ?, ?)",
            ("proj1", "Project", "team1", "private"),
        )
        cursor.execute(
            "INSERT INTO documents (id, title, project_id, creator_id, deleted_at, public_link_enabled) VALUES (?, ?, ?, ?, ?, ?)",
            ("doc1", "Deleted Doc", "proj1", "user1", "2025-01-01 00:00:00", False),
        )
        test_db.commit()

        doc = repository.get_document("doc1")
        assert doc is not None
        assert doc.deletedAt is not None
        assert doc.is_deleted is True


class TestPolicyOperations:
    """Test policy CRUD operations."""

    def test_save_and_get_resource_policy(self, test_db, repository):
        """Test saving and retrieving resource policy."""
        policy_doc = ResourcePolicyDocument(
            resource=ResourceInfo(
                resourceId="urn:resource:team1:proj1:doc1", creatorId="user1"
            ),
            policies=[
                ResourcePolicy(
                    description="Test policy",
                    permissions=[Permission.CAN_VIEW],
                    effect=Effect.ALLOW,
                    filter=[],
                )
            ],
        )

        # Save
        result = repository.save_resource_policy(policy_doc)
        assert result is True

        # Retrieve
        retrieved = repository.get_resource_policy("urn:resource:team1:proj1:doc1")
        assert retrieved is not None
        assert retrieved.resource.resourceId == "urn:resource:team1:proj1:doc1"
        assert len(retrieved.policies) == 1

    def test_get_resource_policy_not_found(self, repository):
        """Test getting non-existent policy."""
        policy = repository.get_resource_policy("urn:resource:nonexistent")
        assert policy is None

    def test_save_resource_policy_update(self, test_db, repository):
        """Test updating existing policy."""
        policy_doc = ResourcePolicyDocument(
            resource=ResourceInfo(
                resourceId="urn:resource:team1:proj1:doc1", creatorId="user1"
            ),
            policies=[
                ResourcePolicy(
                    description="V1",
                    permissions=[Permission.CAN_VIEW],
                    effect=Effect.ALLOW,
                    filter=[],
                )
            ],
        )

        # Save first version
        repository.save_resource_policy(policy_doc)

        # Update with new version
        policy_doc.policies.append(
            ResourcePolicy(
                description="V2",
                permissions=[Permission.CAN_EDIT],
                effect=Effect.ALLOW,
                filter=[],
            )
        )
        repository.save_resource_policy(policy_doc)

        # Retrieve and verify
        retrieved = repository.get_resource_policy("urn:resource:team1:proj1:doc1")
        assert len(retrieved.policies) == 2
