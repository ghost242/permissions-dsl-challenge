"""Entity models for the permissions system.

These models match the specifications from README.md
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Role(str, Enum):
    """User roles in a team or project."""
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"


class PlanType(str, Enum):
    """Plan types for teams."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Visibility(str, Enum):
    """Project visibility types."""
    PRIVATE = "private"
    PUBLIC = "public"


class User(BaseModel):
    """User entity - matches README.md specification."""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User name")

    class Config:
        use_enum_values = True


class Team(BaseModel):
    """Team entity - matches README.md specification."""
    id: str = Field(..., description="Team ID")
    name: str = Field(..., description="Team name")
    plan: PlanType = Field(..., description="Team plan type (free, pro, enterprise)")

    class Config:
        use_enum_values = True


class Project(BaseModel):
    """Project entity - matches README.md specification."""
    id: str = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")
    teamId: str = Field(..., description="Team ID this project belongs to", alias="teamId")
    visibility: Visibility = Field(..., description="Project visibility (private or public)")

    class Config:
        use_enum_values = True
        populate_by_name = True


class Document(BaseModel):
    """Document entity - matches README.md specification."""
    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    projectId: str = Field(..., description="Project ID", alias="projectId")
    creatorId: str = Field(..., description="Creator user ID", alias="creatorId")
    deletedAt: Optional[datetime] = Field(default=None, description="Deletion timestamp, None if not deleted", alias="deletedAt")
    publicLinkEnabled: bool = Field(default=False, description="Whether public link is enabled", alias="publicLinkEnabled")

    @property
    def is_deleted(self) -> bool:
        """Check if the document is deleted."""
        return self.deletedAt is not None

    class Config:
        use_enum_values = True
        populate_by_name = True


class TeamMembership(BaseModel):
    """Team membership entity - matches README.md specification."""
    userId: str = Field(..., description="User ID", alias="userId")
    teamId: str = Field(..., description="Team ID", alias="teamId")
    role: Role = Field(..., description="User role in team (viewer, editor, admin)")

    class Config:
        use_enum_values = True
        populate_by_name = True


class ProjectMembership(BaseModel):
    """Project membership entity - matches README.md specification."""
    userId: str = Field(..., description="User ID", alias="userId")
    projectId: str = Field(..., description="Project ID", alias="projectId")
    role: Role = Field(..., description="User role in project (viewer, editor, admin)")

    class Config:
        use_enum_values = True
        populate_by_name = True
