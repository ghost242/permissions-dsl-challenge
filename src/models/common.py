"""Common types and enums for the permissions system."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Permission(str, Enum):
    """Permission types for resources."""

    CAN_VIEW = "can_view"
    CAN_EDIT = "can_edit"
    CAN_DELETE = "can_delete"
    CAN_SHARE = "can_share"


class Effect(str, Enum):
    """Policy effect - allow or deny."""

    ALLOW = "allow"
    DENY = "deny"


class FilterOperator(str, Enum):
    """Operators for filter conditions."""

    EQ = "=="  # Equal
    NE = "!="  # Not equal
    GT = ">"  # Greater than
    GTE = ">="  # Greater than or equal
    LT = "<"  # Less than
    LTE = "<="  # Less than or equal
    NE_NULL = "<>"  # Not null (not equal to null)
    IN = "in"  # In list
    NOT_IN = "not in"  # Not in list
    HAS = "has"  # Contains (for URN matching)
    HAS_NOT = "has not"  # Does not contain


class Filter(BaseModel):
    """Filter condition for policy evaluation."""

    prop: str = Field(
        ...,
        description="Property path to evaluate (e.g., 'user.id', 'document.creatorId')",
    )
    op: FilterOperator = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")

    class Config:
        use_enum_values = True
