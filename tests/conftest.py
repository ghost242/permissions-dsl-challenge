"""Shared test fixtures and configuration.

This module provides common fixtures used across all tests.
"""

import pytest
from fastapi.testclient import TestClient

from src.database.connection import DatabaseConnection, DatabaseConfig
from src.database.repository import Repository
from src.main import app


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing.

    This fixture:
    1. Creates a fresh in-memory database
    2. Runs all migration scripts
    3. Yields the database connection
    4. Cleans up after the test
    """
    # Create in-memory database
    config = DatabaseConfig(db_type="sqlite", sqlite_path=":memory:")
    db = DatabaseConnection(config)
    db.connect()

    # Run migration scripts
    with open("migrations/001_initial_schema.sql") as f:
        db.get_connection().executescript(f.read())

    with open("migrations/002_add_indexes.sql") as f:
        db.get_connection().executescript(f.read())

    db.commit()

    yield db

    # Cleanup
    db.close()


@pytest.fixture
def repository(test_db):
    """Create a repository instance with test database.

    Args:
        test_db: Test database fixture

    Returns:
        Repository: Repository instance connected to test database
    """
    return Repository(test_db)


@pytest.fixture
def test_client(monkeypatch):
    """Create a FastAPI test client with test database.

    This fixture creates a fresh test database for each test and patches
    the database connection singleton to use it.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        TestClient: FastAPI test client
    """
    # Create a fresh test database for this test
    config = DatabaseConfig(db_type="sqlite", sqlite_path=":memory:")
    test_db = DatabaseConnection(config)
    test_db.connect()

    # Run migration scripts to set up schema
    with open("migrations/001_initial_schema.sql") as f:
        test_db.get_connection().executescript(f.read())
    with open("migrations/002_add_indexes.sql") as f:
        test_db.get_connection().executescript(f.read())
    test_db.commit()

    # Patch the global database singleton
    monkeypatch.setattr("src.database.connection._db_connection", test_db)

    # Patch get_database to return our test database
    def mock_get_database():
        return test_db

    monkeypatch.setattr("src.database.connection.get_database", mock_get_database)

    # Patch close_database to prevent closing our test database
    def mock_close_database():
        pass

    monkeypatch.setattr("src.database.connection.close_database", mock_close_database)

    # Patch the test_db.connect() method to prevent re-connecting
    # (which would create a new empty database)
    test_db.connect = lambda: None

    # Create test client with patched database
    with TestClient(app) as client:
        # Attach the database to the client so tests can access it
        client.test_db = test_db
        yield client

    # Cleanup
    test_db.close()


@pytest.fixture
def sample_user():
    """Sample user data for testing."""
    return {"id": "user1", "email": "test@example.com", "name": "Test User"}


@pytest.fixture
def sample_team():
    """Sample team data for testing."""
    return {"id": "team1", "name": "Test Team", "plan": "pro"}


@pytest.fixture
def sample_project(sample_team):
    """Sample project data for testing."""
    return {
        "id": "proj1",
        "name": "Test Project",
        "teamId": sample_team["id"],
        "visibility": "private",
    }


@pytest.fixture
def sample_document(sample_project, sample_user):
    """Sample document data for testing."""
    return {
        "id": "doc1",
        "title": "Test Document",
        "projectId": sample_project["id"],
        "creatorId": sample_user["id"],
        "deletedAt": None,
        "publicLinkEnabled": False,
    }
