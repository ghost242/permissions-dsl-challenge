"""Integration tests for API endpoints.

Tests all API endpoints with real database and HTTP client.
"""

import pytest
import json


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_check_success(self, test_client):
        """Test health endpoint returns 200 when healthy."""
        response = test_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert "version" in data


class TestPolicyEndpoints:
    """Test policy CRUD endpoints."""

    def test_create_policy_with_options(self, test_client):
        """Test creating policy with simple options."""
        response = test_client.post(
            "/api/v1/resource/policy",
            json={
                "resourceId": "urn:resource:team1:proj1:doc1",
                "action": "can_edit",
                "target": "user123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Policy created successfully"
        assert data["resourceId"] == "urn:resource:team1:proj1:doc1"

    def test_create_policy_with_full_document(self, test_client):
        """Test creating policy with full document."""
        policy_doc = {
            "resource": {
                "resourceId": "urn:resource:team1:proj1:doc2",
                "creatorId": "user1",
            },
            "policies": [
                {
                    "description": "Creator access",
                    "permissions": ["can_view", "can_edit"],
                    "effect": "allow",
                    "filter": [
                        {"prop": "document.creatorId", "op": "==", "value": "user.id"}
                    ],
                }
            ],
        }

        response = test_client.post("/api/v1/resource/policy", json=policy_doc)
        assert response.status_code == 201

    def test_get_policy_success(self, test_client):
        """Test getting existing policy."""
        # First create a policy
        test_client.post(
            "/api/v1/resource/policy",
            json={
                "resourceId": "urn:resource:team1:proj1:doc3",
                "action": "can_view",
                "target": "user1",
            },
        )

        # Then retrieve it
        response = test_client.get(
            "/api/v1/resource/policy",
            params={"resourceId": "urn:resource:team1:proj1:doc3"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["resource"]["resourceId"] == "urn:resource:team1:proj1:doc3"
        assert len(data["policies"]) >= 1

    def test_get_policy_not_found(self, test_client):
        """Test getting non-existent policy."""
        response = test_client.get(
            "/api/v1/resource/policy",
            params={"resourceId": "urn:resource:nonexistent:nonexistent:nonexistent"},
        )

        assert response.status_code == 404

    def test_get_policy_invalid_urn(self, test_client):
        """Test getting policy with invalid URN format."""
        response = test_client.get(
            "/api/v1/resource/policy", params={"resourceId": "invalid-urn"}
        )

        # FastAPI returns 422 for query parameter validation errors
        assert response.status_code == 422


class TestPermissionCheckEndpoint:
    """Test /permission-check endpoint."""

    def setup_test_data(self, test_client):
        """Setup test data in database."""
        cursor = test_client.test_db.get_connection().cursor()

        # Insert entities
        cursor.execute(
            "INSERT INTO users (id, email, name) VALUES (?, ?, ?)",
            ("user1", "test@example.com", "Test User"),
        )
        cursor.execute(
            "INSERT INTO teams (id, name, plan) VALUES (?, ?, ?)",
            ("team1", "Test Team", "pro"),
        )
        cursor.execute(
            "INSERT INTO projects (id, name, team_id, visibility) VALUES (?, ?, ?, ?)",
            ("proj1", "Test Project", "team1", "private"),
        )
        cursor.execute(
            "INSERT INTO documents (id, title, project_id, creator_id, deleted_at, public_link_enabled) VALUES (?, ?, ?, ?, ?, ?)",
            ("doc1", "Test Doc", "proj1", "user1", None, 0),
        )

        # Insert policy
        policy_json = json.dumps(
            {
                "resource": {
                    "resourceId": "urn:resource:team1:proj1:doc1",
                    "creatorId": "user1",
                },
                "policies": [
                    {
                        "description": "Creator has full access",
                        "permissions": [
                            "can_view",
                            "can_edit",
                            "can_delete",
                            "can_share",
                        ],
                        "effect": "allow",
                        "filter": [
                            {
                                "prop": "document.creatorId",
                                "op": "==",
                                "value": "user.id",
                            }
                        ],
                    }
                ],
            }
        )
        cursor.execute(
            "INSERT INTO resource_policies (resource_id, policy_document) VALUES (?, ?)",
            ("urn:resource:team1:proj1:doc1", policy_json),
        )

        test_client.test_db.commit()

    def test_permission_check_allow(self, test_client):
        """Test permission check that allows access."""
        self.setup_test_data(test_client)

        response = test_client.get(
            "/api/v1/permission-check",
            params={
                "resourceId": "urn:resource:team1:proj1:doc1",
                "userId": "user1",
                "action": "can_view",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True
        assert "evaluation_details" in data

    def test_permission_check_deny(self, test_client):
        """Test permission check that denies access."""
        self.setup_test_data(test_client)

        # Insert another user who is not the creator
        cursor = test_client.test_db.get_connection().cursor()
        cursor.execute(
            "INSERT INTO users (id, email, name) VALUES (?, ?, ?)",
            ("user2", "other@example.com", "Other User"),
        )
        test_client.test_db.commit()

        response = test_client.get(
            "/api/v1/permission-check",
            params={
                "resourceId": "urn:resource:team1:proj1:doc1",
                "userId": "user2",  # Different user
                "action": "can_view",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False

    def test_permission_check_missing_user(self, test_client):
        """Test permission check with non-existent user."""
        self.setup_test_data(test_client)

        response = test_client.get(
            "/api/v1/permission-check",
            params={
                "resourceId": "urn:resource:team1:proj1:doc1",
                "userId": "nonexistent",
                "action": "can_view",
            },
        )

        assert response.status_code == 404

    def test_permission_check_invalid_action(self, test_client):
        """Test permission check with invalid action."""
        self.setup_test_data(test_client)

        response = test_client.get(
            "/api/v1/permission-check",
            params={
                "resourceId": "urn:resource:team1:proj1:doc1",
                "userId": "user1",
                "action": "invalid_action",
            },
        )

        assert response.status_code == 422  # Validation error
