-- ===============================================================================
-- Migration 001: Initial Schema
-- Description: Create all core tables for the permission control system
-- Database: SQLite (local) / PostgreSQL (production)
-- ===============================================================================

-- ===============================================================================
-- 1. USERS TABLE
-- ===============================================================================

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ===============================================================================
-- 2. TEAMS TABLE
-- ===============================================================================

CREATE TABLE IF NOT EXISTS teams (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(50) NOT NULL CHECK (plan IN ('free', 'pro', 'enterprise')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ===============================================================================
-- 3. PROJECTS TABLE
-- ===============================================================================

CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    team_id VARCHAR(255) NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    visibility VARCHAR(50) NOT NULL CHECK (visibility IN ('private', 'public')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ===============================================================================
-- 4. DOCUMENTS TABLE
-- ===============================================================================

CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    project_id VARCHAR(255) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    creator_id VARCHAR(255) REFERENCES users(id) ON DELETE SET NULL,
    deleted_at TIMESTAMP NULL,
    public_link_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ===============================================================================
-- 5. TEAM_MEMBERSHIPS TABLE (Many-to-Many: Users ↔ Teams)
-- ===============================================================================

CREATE TABLE IF NOT EXISTS team_memberships (
    user_id VARCHAR(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_id VARCHAR(255) NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('viewer', 'editor', 'admin')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, team_id)
);

-- ===============================================================================
-- 6. PROJECT_MEMBERSHIPS TABLE (Many-to-Many: Users ↔ Projects)
-- ===============================================================================

CREATE TABLE IF NOT EXISTS project_memberships (
    user_id VARCHAR(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id VARCHAR(255) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('viewer', 'editor', 'admin')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, project_id)
);

-- ===============================================================================
-- 7. RESOURCE_POLICIES TABLE (Policy documents for resources)
-- ===============================================================================

CREATE TABLE IF NOT EXISTS resource_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id VARCHAR(500) NOT NULL UNIQUE,
    policy_document TEXT NOT NULL,  -- TEXT for SQLite, JSONB for PostgreSQL
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ===============================================================================
-- 8. USER_POLICIES TABLE (Policy documents for users)
-- ===============================================================================

CREATE TABLE IF NOT EXISTS user_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(255) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    policy_document TEXT NOT NULL,  -- TEXT for SQLite, JSONB for PostgreSQL
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ===============================================================================
-- MIGRATION COMPLETE
-- ===============================================================================
