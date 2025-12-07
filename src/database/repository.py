"""Data repository for accessing database entities.

This module provides data access methods for all entities in the system.
"""

import json
from datetime import datetime
from typing import Optional

from src.database.connection import DatabaseConnection
from src.models.entities import (Document, Project, ProjectMembership, Team,
                                 TeamMembership, User)
from src.models.policies import ResourcePolicyDocument, UserPolicyDocument


class Repository:
    """Repository for data access operations."""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    # -------------------------------------------------------------------------
    # User operations
    # -------------------------------------------------------------------------

    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID.

        Args:
            user_id: User ID

        Returns:
            User object or None if not found
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, email, name FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return User(
            id=row["id"] if isinstance(row, dict) else row[0],
            email=row["email"] if isinstance(row, dict) else row[1],
            name=row["name"] if isinstance(row, dict) else row[2],
        )

    # -------------------------------------------------------------------------
    # Team operations
    # -------------------------------------------------------------------------

    def get_team(self, team_id: str) -> Optional[Team]:
        """Get a team by ID.

        Args:
            team_id: Team ID

        Returns:
            Team object or None if not found
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, name, plan FROM teams WHERE id = ?", (team_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return Team(
            id=row["id"] if isinstance(row, dict) else row[0],
            name=row["name"] if isinstance(row, dict) else row[1],
            plan=row["plan"] if isinstance(row, dict) else row[2],
        )

    # -------------------------------------------------------------------------
    # Project operations
    # -------------------------------------------------------------------------

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID.

        Args:
            project_id: Project ID

        Returns:
            Project object or None if not found
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, team_id, visibility FROM projects WHERE id = ?",
            (project_id,),
        )
        row = cursor.fetchone()

        if not row:
            return None

        return Project(
            id=row["id"] if isinstance(row, dict) else row[0],
            name=row["name"] if isinstance(row, dict) else row[1],
            teamId=row["team_id"] if isinstance(row, dict) else row[2],
            visibility=row["visibility"] if isinstance(row, dict) else row[3],
        )

    # -------------------------------------------------------------------------
    # Document operations
    # -------------------------------------------------------------------------

    def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID.

        Args:
            document_id: Document ID

        Returns:
            Document object or None if not found
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, title, project_id, creator_id, deleted_at, public_link_enabled
            FROM documents
            WHERE id = ?
            """,
            (document_id,),
        )
        row = cursor.fetchone()

        if not row:
            return None

        deleted_at = None
        deleted_at_raw = row["deleted_at"] if isinstance(row, dict) else row[4]
        if deleted_at_raw:
            deleted_at = (
                datetime.fromisoformat(deleted_at_raw)
                if isinstance(deleted_at_raw, str)
                else deleted_at_raw
            )

        return Document(
            id=row["id"] if isinstance(row, dict) else row[0],
            title=row["title"] if isinstance(row, dict) else row[1],
            projectId=row["project_id"] if isinstance(row, dict) else row[2],
            creatorId=row["creator_id"] if isinstance(row, dict) else row[3],
            deletedAt=deleted_at,
            publicLinkEnabled=bool(
                row["public_link_enabled"] if isinstance(row, dict) else row[5]
            ),
        )

    # -------------------------------------------------------------------------
    # Membership operations
    # -------------------------------------------------------------------------

    def get_team_membership(
        self, user_id: str, team_id: str
    ) -> Optional[TeamMembership]:
        """Get team membership for a user.

        Args:
            user_id: User ID
            team_id: Team ID

        Returns:
            TeamMembership object or None if not found
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id, team_id, role FROM team_memberships WHERE user_id = ? AND team_id = ?",
            (user_id, team_id),
        )
        row = cursor.fetchone()

        if not row:
            return None

        return TeamMembership(
            userId=row["user_id"] if isinstance(row, dict) else row[0],
            teamId=row["team_id"] if isinstance(row, dict) else row[1],
            role=row["role"] if isinstance(row, dict) else row[2],
        )

    def get_project_membership(
        self, user_id: str, project_id: str
    ) -> Optional[ProjectMembership]:
        """Get project membership for a user.

        Args:
            user_id: User ID
            project_id: Project ID

        Returns:
            ProjectMembership object or None if not found
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id, project_id, role FROM project_memberships WHERE user_id = ? AND project_id = ?",
            (user_id, project_id),
        )
        row = cursor.fetchone()

        if not row:
            return None

        return ProjectMembership(
            userId=row["user_id"] if isinstance(row, dict) else row[0],
            projectId=row["project_id"] if isinstance(row, dict) else row[1],
            role=row["role"] if isinstance(row, dict) else row[2],
        )

    # -------------------------------------------------------------------------
    # Policy operations
    # -------------------------------------------------------------------------

    def get_resource_policy(self, resource_id: str) -> Optional[ResourcePolicyDocument]:
        """Get resource policy document by resource ID.

        Args:
            resource_id: Resource URN

        Returns:
            ResourcePolicyDocument or None if not found
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT resource_id, policy_document FROM resource_policies WHERE resource_id = ?",
            (resource_id,),
        )
        row = cursor.fetchone()

        if not row:
            return None

        # Parse policy document (stored as JSON TEXT or JSONB)
        policy_json = row["policy_document"] if isinstance(row, dict) else row[1]

        if isinstance(policy_json, str):
            policy_data = json.loads(policy_json)
        else:
            policy_data = policy_json

        return ResourcePolicyDocument(**policy_data)

    def save_resource_policy(self, policy_doc: ResourcePolicyDocument) -> bool:
        """Save or update resource policy document.

        Args:
            policy_doc: ResourcePolicyDocument to save

        Returns:
            bool: True if successful
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Serialize policy document to JSON
        policy_json = policy_doc.model_dump_json()

        # Check if policy exists
        cursor.execute(
            "SELECT resource_id FROM resource_policies WHERE resource_id = ?",
            (policy_doc.resource.resourceId,),
        )
        exists = cursor.fetchone() is not None

        if exists:
            # Update existing policy
            cursor.execute(
                """
                UPDATE resource_policies
                SET policy_document = ?, updated_at = CURRENT_TIMESTAMP
                WHERE resource_id = ?
                """,
                (policy_json, policy_doc.resource.resourceId),
            )
        else:
            # Insert new policy
            cursor.execute(
                """
                INSERT INTO resource_policies (resource_id, policy_document, created_at, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (policy_doc.resource.resourceId, policy_json),
            )

        self.db.commit()
        return True

    def get_user_policy(self, user_id: str) -> Optional[UserPolicyDocument]:
        """Get user policy document by user ID.

        Args:
            user_id: User ID

        Returns:
            UserPolicyDocument or None if not found
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id, policy_document FROM user_policies WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()

        if not row:
            return None

        # Parse policy document (stored as JSON TEXT or JSONB)
        policy_json = row["policy_document"] if isinstance(row, dict) else row[1]

        if isinstance(policy_json, str):
            policy_data = json.loads(policy_json)
        else:
            policy_data = policy_json

        return UserPolicyDocument(**policy_data)

    def save_user_policy(self, user_id: str, policy_doc: UserPolicyDocument) -> bool:
        """Save or update user policy document.

        Args:
            user_id: User ID
            policy_doc: UserPolicyDocument to save

        Returns:
            bool: True if successful
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Serialize policy document to JSON
        policy_json = policy_doc.model_dump_json()

        # Check if policy exists
        cursor.execute(
            "SELECT user_id FROM user_policies WHERE user_id = ?", (user_id,)
        )
        exists = cursor.fetchone() is not None

        if exists:
            # Update existing policy
            cursor.execute(
                """
                UPDATE user_policies
                SET policy_document = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (policy_json, user_id),
            )
        else:
            # Insert new policy
            cursor.execute(
                """
                INSERT INTO user_policies (user_id, policy_document, created_at, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (user_id, policy_json),
            )

        self.db.commit()
        return True
