"""Main FastAPI application for the Permission Control Service.

This module initializes and configures the FastAPI application.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import router
from src.database.connection import get_database, close_database


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------
# Lifespan context manager for startup/shutdown
# -------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Permission Control Service...")

    # Initialize database connection
    try:
        db = get_database()
        db.connect()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Permission Control Service...")
    close_database()
    logger.info("Database connection closed")


# -------------------------------------------------------------------------
# Create FastAPI application
# -------------------------------------------------------------------------

app = FastAPI(
    title="Permission Control Service",
    description="Policy-based permission control system for document management",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# -------------------------------------------------------------------------
# CORS middleware
# -------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------------
# Exception handlers
# -------------------------------------------------------------------------


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions.

    Args:
        request: The request that caused the exception
        exc: The exception that was raised

    Returns:
        JSONResponse with error details
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An internal server error occurred",
        },
    )


# -------------------------------------------------------------------------
# Request logging middleware
# -------------------------------------------------------------------------


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all HTTP requests.

    Args:
        request: The incoming request
        call_next: The next middleware or route handler

    Returns:
        The response from the next handler
    """
    logger.info(f"{request.method} {request.url.path}")

    response = await call_next(request)

    logger.info(f"{request.method} {request.url.path} - Status: {response.status_code}")

    return response


# -------------------------------------------------------------------------
# Register routers
# -------------------------------------------------------------------------

app.include_router(router, prefix="/api/v1", tags=["permissions"])


# -------------------------------------------------------------------------
# Root endpoint
# -------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirects to API documentation.

    Returns:
        Redirect to /docs
    """
    return {
        "message": "Permission Control Service",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/api/v1/health",
    }


# -------------------------------------------------------------------------
# Run with uvicorn (for local development)
# -------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (development only)
        log_level="info",
    )
