"""Database connection management.

This module handles database connections for both SQLite (local) and PostgreSQL (production).
"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Optional


class DatabaseConfig:
    """Database configuration."""

    def __init__(
        self,
        db_type: str = "sqlite",  # "sqlite" or "postgresql"
        sqlite_path: str = "data/permissions.db",
        postgres_host: Optional[str] = None,
        postgres_port: int = 5432,
        postgres_user: Optional[str] = None,
        postgres_password: Optional[str] = None,
        postgres_database: Optional[str] = None,
    ):
        self.db_type = db_type
        self.sqlite_path = sqlite_path
        self.postgres_host = postgres_host
        self.postgres_port = postgres_port
        self.postgres_user = postgres_user
        self.postgres_password = postgres_password
        self.postgres_database = postgres_database

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create configuration from environment variables.

        Environment variables:
            DB_TYPE: "sqlite" or "postgresql" (default: sqlite)
            SQLITE_PATH: Path to SQLite database file (default: data/permissions.db)
            POSTGRES_HOST: PostgreSQL host
            POSTGRES_PORT: PostgreSQL port (default: 5432)
            POSTGRES_USER: PostgreSQL username
            POSTGRES_PASSWORD: PostgreSQL password
            POSTGRES_DATABASE: PostgreSQL database name
        """
        db_type = os.getenv("DB_TYPE", "sqlite")

        if db_type == "sqlite":
            return cls(
                db_type="sqlite",
                sqlite_path=os.getenv("SQLITE_PATH", "data/permissions.db"),
            )
        else:
            return cls(
                db_type="postgresql",
                postgres_host=os.getenv("POSTGRES_HOST"),
                postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
                postgres_user=os.getenv("POSTGRES_USER"),
                postgres_password=os.getenv("POSTGRES_PASSWORD"),
                postgres_database=os.getenv("POSTGRES_DATABASE"),
            )


class DatabaseConnection:
    """Database connection manager."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection = None

    def connect(self):
        """Establish database connection."""
        if self.config.db_type == "sqlite":
            self._connect_sqlite()
        else:
            self._connect_postgresql()

    def _connect_sqlite(self):
        """Connect to SQLite database."""
        # Ensure directory exists
        db_dir = os.path.dirname(self.config.sqlite_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        # For in-memory databases (testing), allow cross-thread usage
        check_same_thread = self.config.sqlite_path != ":memory:"

        self._connection = sqlite3.connect(
            self.config.sqlite_path, check_same_thread=check_same_thread
        )
        self._connection.row_factory = sqlite3.Row  # Enable column access by name

    def _connect_postgresql(self):
        """Connect to PostgreSQL database."""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError:
            raise ImportError(
                "psycopg2 is required for PostgreSQL connections. "
                "Install it with: pip install psycopg2-binary"
            )

        self._connection = psycopg2.connect(
            host=self.config.postgres_host,
            port=self.config.postgres_port,
            user=self.config.postgres_user,
            password=self.config.postgres_password,
            database=self.config.postgres_database,
            cursor_factory=RealDictCursor,
        )

    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def get_connection(self):
        """Get the database connection."""
        if self._connection is None:
            self.connect()
        return self._connection

    def commit(self):
        """Commit current transaction."""
        if self._connection:
            self._connection.commit()

    def rollback(self):
        """Rollback current transaction."""
        if self._connection:
            self._connection.rollback()

    @contextmanager
    def transaction(self):
        """Context manager for database transactions.

        Usage:
            with db.transaction():
                # Execute queries
                ...
            # Auto-commits on success, rolls back on exception
        """
        try:
            yield self.get_connection()
            self.commit()
        except Exception:
            self.rollback()
            raise

    def is_connected(self) -> bool:
        """Check if database is connected.

        Returns:
            bool: True if connected and operational, False otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return True
        except Exception:
            return False


# Global database connection instance
_db_connection: Optional[DatabaseConnection] = None


def get_database() -> DatabaseConnection:
    """Get the global database connection instance.

    Returns:
        DatabaseConnection: The database connection
    """
    global _db_connection

    if _db_connection is None:
        config = DatabaseConfig.from_env()
        _db_connection = DatabaseConnection(config)

    return _db_connection


def close_database():
    """Close the global database connection."""
    global _db_connection

    if _db_connection:
        _db_connection.close()
        _db_connection = None
