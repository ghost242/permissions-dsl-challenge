"""Integration tests for 7 permission scenarios from README.md.

These tests validate the complete system against all documented scenarios.
"""

import pytest
import json


def setup_base_data(test_client):
    """Setup basic entities needed for all scenarios."""
    cursor = test_client.test_db.get_connection().cursor()

    # Users
    cursor.execute("INSERT INTO users (id, email, name) VALUES (?, ?, ?)", ("creator1", "creator@example.com", "Creator"))
    cursor.execute("INSERT INTO users (id, email, name) VALUES (?, ?, ?)", ("admin1", "admin@example.com", "Admin"))
    cursor.execute("INSERT INTO users (id, email, name) VALUES (?, ?, ?)", ("editor1", "editor@example.com", "Editor"))
    cursor.execute("INSERT INTO users (id, email, name) VALUES (?, ?, ?)", ("viewer1", "viewer@example.com", "Viewer"))
    cursor.execute("INSERT INTO users (id, email, name) VALUES (?, ?, ?)", ("stranger", "stranger@example.com", "Stranger"))

    # Teams
    cursor.execute("INSERT INTO teams (id, name, plan) VALUES (?, ?, ?)", ("team1", "Pro Team", "pro"))

    # Projects
    cursor.execute("INSERT INTO projects (id, name, team_id, visibility) VALUES (?, ?, ?, ?)", ("proj1", "Test Project", "team1", "private"))

    test_client.test_db.commit()


class TestScenario1CreatorAccess:
    """Scenario 1: Document creator has full access."""

    def test_scenario_1_creator_has_full_access(self, test_client):
        """
        Scenario 1: Creator has full access

        Given a user who created a document
        When the creator attempts any action
        Then all actions should be allowed
        """
        setup_base_data(test_client)
        cursor = test_client.test_db.get_connection().cursor()

        # Create document
        cursor.execute(
            "INSERT INTO documents (id, title, project_id, creator_id, deleted_at, public_link_enabled) VALUES (?, ?, ?, ?, ?, ?)",
            ("doc1", "Creator Doc", "proj1", "creator1", None, 0)
        )

        # Create policy
        policy_json = json.dumps({
            "resource": {"resourceId": "urn:resource:team1:proj1:doc1", "creatorId": "creator1"},
            "policies": [{
                "description": "Creator has full access",
                "permissions": ["can_view", "can_edit", "can_delete", "can_share"],
                "effect": "allow",
                "filter": [{"prop": "document.creatorId", "op": "==", "value": "user.id"}]
            }]
        })
        cursor.execute("INSERT INTO resource_policies (resource_id, policy_document) VALUES (?, ?)", ("urn:resource:team1:proj1:doc1", policy_json))
        test_client.test_db.commit()

        # Test all permissions
        for action in ["can_view", "can_edit", "can_delete", "can_share"]:
            response = test_client.get(
                "/api/v1/permission-check",
                params={"resourceId": "urn:resource:team1:proj1:doc1", "userId": "creator1", "action": action}
            )
            assert response.status_code == 200, f"Failed for action: {action}"
            assert response.json()["allowed"] is True, f"Creator should have {action}"


class TestScenario2TeamAdminAccess:
    """Scenario 2: Team admin has full access to team documents."""

    def test_scenario_2_team_admin_has_access(self, test_client):
        """
        Scenario 2: Team admin has full access

        Given a team admin
        When admin attempts to access team documents
        Then all actions should be allowed
        """
        setup_base_data(test_client)
        cursor = test_client.test_db.get_connection().cursor()

        # Create document (different creator)
        cursor.execute(
            "INSERT INTO documents (id, title, project_id, creator_id, deleted_at, public_link_enabled) VALUES (?, ?, ?, ?, ?, ?)",
            ("doc2", "Team Doc", "proj1", "creator1", None, 0)
        )

        # Create team membership
        cursor.execute("INSERT INTO team_memberships (user_id, team_id, role) VALUES (?, ?, ?)", ("admin1", "team1", "admin"))

        # Create policy
        policy_json = json.dumps({
            "resource": {"resourceId": "urn:resource:team1:proj1:doc2", "creatorId": "creator1"},
            "policies": [{
                "description": "Team admins have full access",
                "permissions": ["can_view", "can_edit", "can_delete", "can_share"],
                "effect": "allow",
                "filter": [{"prop": "teamMembership.role", "op": "==", "value": "admin"}]
            }]
        })
        cursor.execute("INSERT INTO resource_policies (resource_id, policy_document) VALUES (?, ?)", ("urn:resource:team1:proj1:doc2", policy_json))
        test_client.test_db.commit()

        # Test permissions
        for action in ["can_view", "can_edit", "can_delete", "can_share"]:
            response = test_client.get(
                "/api/v1/permission-check",
                params={"resourceId": "urn:resource:team1:proj1:doc2", "userId": "admin1", "action": action}
            )
            assert response.status_code == 200
            assert response.json()["allowed"] is True, f"Team admin should have {action}"


class TestScenario3ProjectMemberAccess:
    """Scenario 3: Project members have role-based access."""

    def test_scenario_3_project_member_has_access(self, test_client):
        """
        Scenario 3: Project member has role-based access

        Given project members with different roles
        When they attempt various actions
        Then access is granted based on their role
        """
        setup_base_data(test_client)
        cursor = test_client.test_db.get_connection().cursor()

        # Create document
        cursor.execute(
            "INSERT INTO documents (id, title, project_id, creator_id, deleted_at, public_link_enabled) VALUES (?, ?, ?, ?, ?, ?)",
            ("doc3", "Project Doc", "proj1", "creator1", None, 0)
        )

        # Create memberships
        cursor.execute("INSERT INTO project_memberships (user_id, project_id, role) VALUES (?, ?, ?)", ("editor1", "proj1", "editor"))
        cursor.execute("INSERT INTO project_memberships (user_id, project_id, role) VALUES (?, ?, ?)", ("viewer1", "proj1", "viewer"))

        # Create policy
        policy_json = json.dumps({
            "resource": {"resourceId": "urn:resource:team1:proj1:doc3", "creatorId": "creator1"},
            "policies": [
                {
                    "description": "Editors can view and edit",
                    "permissions": ["can_view", "can_edit"],
                    "effect": "allow",
                    "filter": [{"prop": "projectMembership.role", "op": "==", "value": "editor"}]
                },
                {
                    "description": "Viewers can only view",
                    "permissions": ["can_view"],
                    "effect": "allow",
                    "filter": [{"prop": "projectMembership.role", "op": "==", "value": "viewer"}]
                }
            ]
        })
        cursor.execute("INSERT INTO resource_policies (resource_id, policy_document) VALUES (?, ?)", ("urn:resource:team1:proj1:doc3", policy_json))
        test_client.test_db.commit()

        # Test editor permissions
        response = test_client.get("/api/v1/permission-check", params={"resourceId": "urn:resource:team1:proj1:doc3", "userId": "editor1", "action": "can_view"})
        assert response.json()["allowed"] is True, "Editor should view"

        response = test_client.get("/api/v1/permission-check", params={"resourceId": "urn:resource:team1:proj1:doc3", "userId": "editor1", "action": "can_edit"})
        assert response.json()["allowed"] is True, "Editor should edit"

        response = test_client.get("/api/v1/permission-check", params={"resourceId": "urn:resource:team1:proj1:doc3", "userId": "editor1", "action": "can_delete"})
        assert response.json()["allowed"] is False, "Editor should not delete"

        # Test viewer permissions
        response = test_client.get("/api/v1/permission-check", params={"resourceId": "urn:resource:team1:proj1:doc3", "userId": "viewer1", "action": "can_view"})
        assert response.json()["allowed"] is True, "Viewer should view"

        response = test_client.get("/api/v1/permission-check", params={"resourceId": "urn:resource:team1:proj1:doc3", "userId": "viewer1", "action": "can_edit"})
        assert response.json()["allowed"] is False, "Viewer should not edit"


class TestScenario4PublicLinkAccess:
    """Scenario 4: Public link allows view access."""

    def test_scenario_4_public_link_enabled(self, test_client):
        """
        Scenario 4: Public link allows view access

        Given a document with publicLinkEnabled=true
        When anyone attempts to view
        Then view access is granted
        """
        setup_base_data(test_client)
        cursor = test_client.test_db.get_connection().cursor()

        # Create document with public link enabled
        cursor.execute(
            "INSERT INTO documents (id, title, project_id, creator_id, deleted_at, public_link_enabled) VALUES (?, ?, ?, ?, ?, ?)",
            ("doc4", "Public Doc", "proj1", "creator1", None, 1)  # public_link_enabled = 1
        )

        # Create policy
        policy_json = json.dumps({
            "resource": {"resourceId": "urn:resource:team1:proj1:doc4", "creatorId": "creator1"},
            "policies": [{
                "description": "Public link allows view",
                "permissions": ["can_view"],
                "effect": "allow",
                "filter": [{"prop": "document.publicLinkEnabled", "op": "==", "value": True}]
            }]
        })
        cursor.execute("INSERT INTO resource_policies (resource_id, policy_document) VALUES (?, ?)", ("urn:resource:team1:proj1:doc4", policy_json))
        test_client.test_db.commit()

        # Test stranger can view
        response = test_client.get("/api/v1/permission-check", params={"resourceId": "urn:resource:team1:proj1:doc4", "userId": "stranger", "action": "can_view"})
        assert response.json()["allowed"] is True, "Public link should allow view"

        # But not edit
        response = test_client.get("/api/v1/permission-check", params={"resourceId": "urn:resource:team1:proj1:doc4", "userId": "stranger", "action": "can_edit"})
        assert response.json()["allowed"] is False, "Public link should not allow edit"


class TestScenario5DeletedDocumentDenied:
    """Scenario 5: Deleted documents deny all access."""

    def test_scenario_5_deleted_document_denied(self, test_client):
        """
        Scenario 5: Deleted document denies all access

        Given a deleted document
        When anyone (even creator) attempts to access
        Then all access is denied
        """
        setup_base_data(test_client)
        cursor = test_client.test_db.get_connection().cursor()

        # Create deleted document
        cursor.execute(
            "INSERT INTO documents (id, title, project_id, creator_id, deleted_at, public_link_enabled) VALUES (?, ?, ?, ?, ?, ?)",
            ("doc5", "Deleted Doc", "proj1", "creator1", "2025-01-01 00:00:00", 0)
        )

        # Create policy (even with creator access)
        policy_json = json.dumps({
            "resource": {"resourceId": "urn:resource:team1:proj1:doc5", "creatorId": "creator1"},
            "policies": [{
                "description": "Creator access",
                "permissions": ["can_view", "can_edit", "can_delete", "can_share"],
                "effect": "allow",
                "filter": [{"prop": "document.creatorId", "op": "==", "value": "user.id"}]
            }]
        })
        cursor.execute("INSERT INTO resource_policies (resource_id, policy_document) VALUES (?, ?)", ("urn:resource:team1:proj1:doc5", policy_json))
        test_client.test_db.commit()

        # Test all permissions denied
        for action in ["can_view", "can_edit", "can_delete", "can_share"]:
            response = test_client.get("/api/v1/permission-check", params={"resourceId": "urn:resource:team1:proj1:doc5", "userId": "creator1", "action": action})
            assert response.json()["allowed"] is False, f"Deleted doc should deny {action}"


class TestScenario6ExplicitDenyOverride:
    """Scenario 6: Explicit DENY overrides ALLOW."""

    def test_scenario_6_explicit_deny_overrides_allow(self, test_client):
        """
        Scenario 6: Explicit DENY overrides ALLOW

        Given both ALLOW and DENY policies
        When evaluating permission
        Then DENY takes precedence
        """
        setup_base_data(test_client)
        cursor = test_client.test_db.get_connection().cursor()

        # Create document
        cursor.execute(
            "INSERT INTO documents (id, title, project_id, creator_id, deleted_at, public_link_enabled) VALUES (?, ?, ?, ?, ?, ?)",
            ("doc6", "Conflict Doc", "proj1", "creator1", None, 0)
        )

        # Create memberships
        cursor.execute("INSERT INTO team_memberships (user_id, team_id, role) VALUES (?, ?, ?)", ("editor1", "team1", "editor"))

        # Create policy with both ALLOW and DENY
        policy_json = json.dumps({
            "resource": {"resourceId": "urn:resource:team1:proj1:doc6", "creatorId": "creator1"},
            "policies": [
                {
                    "description": "Allow editors to edit",
                    "permissions": ["can_view", "can_edit"],
                    "effect": "allow",
                    "filter": [{"prop": "teamMembership.role", "op": "==", "value": "editor"}]
                },
                {
                    "description": "Explicitly deny editor1",
                    "permissions": ["can_edit"],
                    "effect": "deny",
                    "filter": [{"prop": "user.id", "op": "==", "value": "editor1"}]
                }
            ]
        })
        cursor.execute("INSERT INTO resource_policies (resource_id, policy_document) VALUES (?, ?)", ("urn:resource:team1:proj1:doc6", policy_json))
        test_client.test_db.commit()

        # Test: view is allowed (no deny for view)
        response = test_client.get("/api/v1/permission-check", params={"resourceId": "urn:resource:team1:proj1:doc6", "userId": "editor1", "action": "can_view"})
        assert response.json()["allowed"] is True, "View should be allowed (no DENY)"

        # Test: edit is denied (DENY overrides ALLOW)
        response = test_client.get("/api/v1/permission-check", params={"resourceId": "urn:resource:team1:proj1:doc6", "userId": "editor1", "action": "can_edit"})
        assert response.json()["allowed"] is False, "Edit should be denied (DENY > ALLOW)"


class TestScenario7DefaultDeny:
    """Scenario 7: No permission results in default DENY."""

    def test_scenario_7_no_permission_default_deny(self, test_client):
        """
        Scenario 7: Default DENY when no policies match

        Given a user with no matching policies
        When attempting any action
        Then access is denied by default
        """
        setup_base_data(test_client)
        cursor = test_client.test_db.get_connection().cursor()

        # Create document
        cursor.execute(
            "INSERT INTO documents (id, title, project_id, creator_id, deleted_at, public_link_enabled) VALUES (?, ?, ?, ?, ?, ?)",
            ("doc7", "Restricted Doc", "proj1", "creator1", None, 0)
        )

        # Create policy (only for creator)
        policy_json = json.dumps({
            "resource": {"resourceId": "urn:resource:team1:proj1:doc7", "creatorId": "creator1"},
            "policies": [{
                "description": "Only creator",
                "permissions": ["can_view", "can_edit", "can_delete", "can_share"],
                "effect": "allow",
                "filter": [{"prop": "document.creatorId", "op": "==", "value": "user.id"}]
            }]
        })
        cursor.execute("INSERT INTO resource_policies (resource_id, policy_document) VALUES (?, ?)", ("urn:resource:team1:proj1:doc7", policy_json))
        test_client.test_db.commit()

        # Test stranger has no access (default DENY)
        for action in ["can_view", "can_edit", "can_delete", "can_share"]:
            response = test_client.get("/api/v1/permission-check", params={"resourceId": "urn:resource:team1:proj1:doc7", "userId": "stranger", "action": action})
            assert response.json()["allowed"] is False, f"Stranger should not have {action} (default DENY)"
