"""Policy models for the permissions system."""

from pydantic import BaseModel, Field

from .common import Effect, Filter, Permission


class UserPolicy(BaseModel):
    """Individual user policy with filters and permissions."""

    description: str | None = Field(
        None, description="Human-readable policy description"
    )
    filter: list[Filter] | None = Field(
        None, description="Conditions that must be met for this policy to apply"
    )
    permissions: list[Permission] = Field(
        ..., description="List of permissions this policy grants/denies"
    )
    effect: Effect = Field(
        ..., description="Whether this policy allows or denies the permissions"
    )

    class Config:
        use_enum_values = True


class UserPolicyDocument(BaseModel):
    """Complete user policy document containing all policies for a user."""

    policies: list[UserPolicy] = Field(..., description="List of user policies")

    class Config:
        use_enum_values = True


class ResourceInfo(BaseModel):
    """Resource information in policy document."""

    resourceId: str = Field(
        ...,
        description="Resource URN (e.g., urn:resource:{teamId}:{projectId}:{documentId})",
    )
    creatorId: str = Field(..., description="Creator user ID")

    class Config:
        populate_by_name = True


class ResourcePolicy(BaseModel):
    """Individual resource policy with filters and permissions."""

    description: str | None = Field(
        None, description="Human-readable policy description"
    )
    filter: list[Filter] | None = Field(
        None, description="Conditions that must be met for this policy to apply"
    )
    permissions: list[Permission] = Field(
        ..., description="List of permissions this policy grants/denies"
    )
    effect: Effect = Field(
        ..., description="Whether this policy allows or denies the permissions"
    )

    class Config:
        use_enum_values = True


class ResourcePolicyDocument(BaseModel):
    """Complete resource policy document containing resource info and policies."""

    resource: ResourceInfo = Field(..., description="Resource information")
    policies: list[ResourcePolicy] = Field(..., description="List of resource policies")

    class Config:
        use_enum_values = True
