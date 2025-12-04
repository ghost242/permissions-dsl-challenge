"""API routes for the permission control service.

This module implements all HTTP endpoints for the service.
"""

import time
from typing import Union, Optional
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel, Field

from src.database.connection import get_database, DatabaseConnection
from src.database.repository import Repository
from src.components.builder import Builder, PolicyOptions
from src.components.evaluator import Evaluator
from src.models.common import Permission
from src.models.policies import ResourcePolicyDocument


# -------------------------------------------------------------------------
# Response models
# -------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    database: str
    version: str
    timestamp: str


class PolicyCreatedResponse(BaseModel):
    """Response when policy is created/updated."""

    message: str
    resourceId: str
    version: int = 1


class PermissionCheckResponse(BaseModel):
    """Response for permission check."""

    allowed: bool
    message: str
    evaluation_details: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    message: str
    details: Optional[list[str]] = None


# -------------------------------------------------------------------------
# Dependency injection
# -------------------------------------------------------------------------


def get_repository() -> Repository:
    """Get repository instance.

    Returns:
        Repository: Data access repository
    """
    db = get_database()
    return Repository(db)


# -------------------------------------------------------------------------
# Router
# -------------------------------------------------------------------------

router = APIRouter()


# -------------------------------------------------------------------------
# Health check endpoint
# -------------------------------------------------------------------------


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    description="Check if API and database are operational",
)
async def health_check():
    """Health check endpoint.

    Returns service status and database connectivity.
    """
    from datetime import datetime

    db = get_database()
    db_status = "connected" if db.is_connected() else "disconnected"

    if db_status == "disconnected":
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
                "error": "Database connection failed",
            },
        )

    return HealthResponse(
        status="healthy",
        database=db_status,
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


# -------------------------------------------------------------------------
# Fetch resource policy endpoint
# -------------------------------------------------------------------------


@router.get(
    "/resource/policy",
    response_model=ResourcePolicyDocument,
    summary="Fetch policy document for a resource",
    description="Retrieve the complete policy document for a given resource ID",
    responses={
        200: {"description": "Policy document retrieved successfully"},
        400: {"description": "Invalid resourceId format", "model": ErrorResponse},
        404: {"description": "Resource policy not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_resource_policy(
    resourceId: str = Query(
        ...,
        description="Resource URN (e.g., urn:resource:team1:proj1:doc1)",
        regex=r"^urn:resource:[a-zA-Z0-9]+:[a-zA-Z0-9]+:[a-zA-Z0-9]+$",
    ),
    repository: Repository = Depends(get_repository),
):
    """Fetch resource policy document.

    Args:
        resourceId: Resource URN
        repository: Repository instance (injected)

    Returns:
        ResourcePolicyDocument: The policy document

    Raises:
        HTTPException: 400 if invalid format, 404 if not found, 500 on error
    """
    try:
        # Validate URN format
        evaluator = Evaluator()
        team_id, project_id, doc_id = evaluator.extract_urn_components(resourceId)

        if not all([team_id, project_id, doc_id]):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "VALIDATION_ERROR",
                    "message": f"Invalid resourceId format. Expected: urn:resource:{{teamId}}:{{projectId}}:{{docId}}",
                },
            )

        # Fetch policy from database
        policy_doc = repository.get_resource_policy(resourceId)

        if not policy_doc:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NOT_FOUND",
                    "message": f"Resource policy not found for resourceId: {resourceId}",
                },
            )

        return policy_doc

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": "Failed to fetch resource policy",
            },
        )


# -------------------------------------------------------------------------
# Create/update resource policy endpoint
# -------------------------------------------------------------------------


@router.post(
    "/resource/policy",
    response_model=PolicyCreatedResponse,
    status_code=201,
    summary="Create or update resource policy",
    description="Apply or update permission policy for a resource",
    responses={
        201: {"description": "Policy created successfully"},
        400: {"description": "Invalid policy document", "model": ErrorResponse},
        500: {"description": "Failed to save policy", "model": ErrorResponse},
    },
)
async def create_resource_policy(
    policy_input: Union[ResourcePolicyDocument, PolicyOptions] = Body(
        ..., description="Either a complete policy document or simple policy options"
    ),
    repository: Repository = Depends(get_repository),
):
    """Create or update resource policy.

    Accepts either:
    - Full ResourcePolicyDocument with complete policy definition
    - Simple PolicyOptions for quick policy creation

    Args:
        policy_input: Policy document or options
        repository: Repository instance (injected)

    Returns:
        PolicyCreatedResponse: Success message with resourceId

    Raises:
        HTTPException: 400 if invalid, 500 on error
    """
    try:
        # Build policy document using Builder
        builder = Builder()
        policy_doc = builder.build_policy_document(policy_input)

        # Save to database
        repository.save_resource_policy(policy_doc)

        return PolicyCreatedResponse(
            message="Policy created successfully",
            resourceId=policy_doc.resource.resourceId,
            version=1,
        )

    except HTTPException:
        raise
    except Exception as e:
        import logging

        logging.error(f"Failed to save policy: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"Failed to save policy to database: {str(e)}",
            },
        )


# -------------------------------------------------------------------------
# Permission check endpoint
# -------------------------------------------------------------------------


@router.get(
    "/permission-check",
    response_model=PermissionCheckResponse,
    summary="Evaluate if user has permission for action on resource",
    description="Check whether a user has a specific permission on a resource",
    responses={
        200: {"description": "Permission evaluated successfully"},
        400: {"description": "Invalid parameters", "model": ErrorResponse},
        404: {"description": "Resource or user not found", "model": ErrorResponse},
        500: {
            "description": "Internal error during evaluation",
            "model": ErrorResponse,
        },
    },
)
async def check_permission(
    resourceId: str = Query(
        ..., description="Resource URN", example="urn:resource:team1:proj1:doc1"
    ),
    userId: str = Query(..., description="User ID", example="user1"),
    action: Permission = Query(
        ...,
        description="Permission to check (can_view, can_edit, can_delete, can_share)",
        example="can_edit",
    ),
    repository: Repository = Depends(get_repository),
):
    """Evaluate permission for user on resource.

    Args:
        resourceId: Resource URN
        userId: User ID
        action: Permission being requested
        repository: Repository instance (injected)

    Returns:
        PermissionCheckResponse: Evaluation result with allow/deny

    Raises:
        HTTPException: 400/404/500 on errors
    """
    start_time = time.time()

    try:
        # Extract URN components
        evaluator = Evaluator()
        team_id, project_id, doc_id = evaluator.extract_urn_components(resourceId)

        if not all([team_id, project_id, doc_id]):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "VALIDATION_ERROR",
                    "message": f"Invalid resourceId format",
                },
            )

        # Fetch required entities from database
        user = repository.get_user(userId)
        if not user:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NOT_FOUND",
                    "message": f"User not found for userId: {userId}",
                },
            )

        document = repository.get_document(doc_id)
        if not document:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "NOT_FOUND",
                    "message": f"Document not found for resourceId: {resourceId}",
                },
            )

        # Fetch policies
        resource_policy = repository.get_resource_policy(resourceId)
        if not resource_policy:
            raise HTTPException(
                status_code=404,
                detail={"error": "NOT_FOUND", "message": "Resource policy not found"},
            )

        user_policy = repository.get_user_policy(userId)

        # Fetch optional context entities
        team = repository.get_team(team_id)
        project = repository.get_project(project_id)
        team_membership = (
            repository.get_team_membership(userId, team_id) if team else None
        )
        project_membership = (
            repository.get_project_membership(userId, project_id) if project else None
        )

        # Evaluate permission
        result = evaluator.evaluate_permission(
            user=user,
            document=document,
            permission=action,
            resource_policy=resource_policy,
            user_policy=user_policy,
            team=team,
            project=project,
            team_membership=team_membership,
            project_membership=project_membership,
        )

        # Calculate evaluation time
        eval_time_ms = int((time.time() - start_time) * 1000)

        return PermissionCheckResponse(
            allowed=result.allowed,
            message=result.message,
            evaluation_details={
                "matched_policies": result.matched_policies,
                "evaluation_time_ms": eval_time_ms,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": "Failed to evaluate permission",
            },
        )
