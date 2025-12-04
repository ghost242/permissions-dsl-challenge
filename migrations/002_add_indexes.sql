-- ===============================================================================
-- Migration 002: Add Performance Indexes
-- Description: Create indexes on frequently queried columns
-- Database: SQLite (local) / PostgreSQL (production)
-- ===============================================================================

-- ===============================================================================
-- USERS INDEXES
-- ===============================================================================

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ===============================================================================
-- PROJECTS INDEXES
-- ===============================================================================

CREATE INDEX IF NOT EXISTS idx_projects_team_id ON projects(team_id);
CREATE INDEX IF NOT EXISTS idx_projects_visibility ON projects(visibility);

-- ===============================================================================
-- DOCUMENTS INDEXES
-- ===============================================================================

CREATE INDEX IF NOT EXISTS idx_documents_project_id ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_creator_id ON documents(creator_id);
CREATE INDEX IF NOT EXISTS idx_documents_deleted_at ON documents(deleted_at);
CREATE INDEX IF NOT EXISTS idx_documents_public_link_enabled ON documents(public_link_enabled);

-- ===============================================================================
-- TEAM_MEMBERSHIPS INDEXES
-- ===============================================================================

CREATE INDEX IF NOT EXISTS idx_team_memberships_team_id ON team_memberships(team_id);
CREATE INDEX IF NOT EXISTS idx_team_memberships_role ON team_memberships(role);

-- ===============================================================================
-- PROJECT_MEMBERSHIPS INDEXES
-- ===============================================================================

CREATE INDEX IF NOT EXISTS idx_project_memberships_project_id ON project_memberships(project_id);
CREATE INDEX IF NOT EXISTS idx_project_memberships_role ON project_memberships(role);

-- ===============================================================================
-- RESOURCE_POLICIES INDEXES
-- ===============================================================================

CREATE INDEX IF NOT EXISTS idx_resource_policies_resource_id ON resource_policies(resource_id);

-- ===============================================================================
-- USER_POLICIES INDEXES
-- ===============================================================================

CREATE INDEX IF NOT EXISTS idx_user_policies_user_id ON user_policies(user_id);

-- ===============================================================================
-- NOTE: GIN indexes for JSONB (PostgreSQL only)
-- ===============================================================================
-- For PostgreSQL, add these manually:
-- CREATE INDEX idx_resource_policies_document ON resource_policies USING GIN (policy_document);
-- CREATE INDEX idx_user_policies_document ON user_policies USING GIN (policy_document);

-- ===============================================================================
-- MIGRATION COMPLETE
-- ===============================================================================
