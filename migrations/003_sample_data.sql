-- ===============================================================================
-- Migration 003: Sample Data (Optional - for testing)
-- Description: Insert sample data for development and testing
-- Database: SQLite (local) / PostgreSQL (production)
-- ===============================================================================

-- ===============================================================================
-- 1. SAMPLE USERS
-- ===============================================================================

INSERT OR IGNORE INTO users (id, email, name) VALUES
('user1', 'admin@example.com', 'Admin User'),
('user2', 'editor@example.com', 'Editor User'),
('user3', 'viewer@example.com', 'Viewer User'),
('creator1', 'creator@example.com', 'Document Creator');

-- ===============================================================================
-- 2. SAMPLE TEAMS
-- ===============================================================================

INSERT OR IGNORE INTO teams (id, name, plan) VALUES
('team1', 'Pro Team', 'pro'),
('team2', 'Free Team', 'free');

-- ===============================================================================
-- 3. SAMPLE PROJECTS
-- ===============================================================================

INSERT OR IGNORE INTO projects (id, name, team_id, visibility) VALUES
('proj1', 'Main Project', 'team1', 'private'),
('proj2', 'Public Project', 'team1', 'public');

-- ===============================================================================
-- 4. SAMPLE DOCUMENTS
-- ===============================================================================

INSERT OR IGNORE INTO documents (id, title, project_id, creator_id, deleted_at, public_link_enabled) VALUES
('doc1', 'Private Document', 'proj1', 'creator1', NULL, 0),
('doc2', 'Public Link Document', 'proj1', 'creator1', NULL, 1),
('doc3', 'Deleted Document', 'proj1', 'user2', '2025-01-01 00:00:00', 0);

-- ===============================================================================
-- 5. SAMPLE TEAM MEMBERSHIPS
-- ===============================================================================

INSERT OR IGNORE INTO team_memberships (user_id, team_id, role) VALUES
('user1', 'team1', 'admin'),
('user2', 'team1', 'editor'),
('user3', 'team1', 'viewer'),
('creator1', 'team1', 'editor');

-- ===============================================================================
-- 6. SAMPLE PROJECT MEMBERSHIPS
-- ===============================================================================

INSERT OR IGNORE INTO project_memberships (user_id, project_id, role) VALUES
('user2', 'proj1', 'editor'),
('user3', 'proj1', 'viewer');

-- ===============================================================================
-- 7. SAMPLE RESOURCE POLICIES
-- ===============================================================================

INSERT OR IGNORE INTO resource_policies (resource_id, policy_document) VALUES
('urn:resource:team1:proj1:doc1', '{
  "resource": {
    "resourceId": "urn:resource:team1:proj1:doc1",
    "creatorId": "creator1"
  },
  "policies": [
    {
      "description": "Creator has full access",
      "permissions": ["can_view", "can_edit", "can_delete", "can_share"],
      "effect": "allow",
      "filter": [
        {
          "prop": "document.creatorId",
          "op": "==",
          "value": "user.id"
        }
      ]
    },
    {
      "description": "Team admins have full access",
      "permissions": ["can_view", "can_edit", "can_delete", "can_share"],
      "effect": "allow",
      "filter": [
        {
          "prop": "teamMembership.role",
          "op": "==",
          "value": "admin"
        }
      ]
    },
    {
      "description": "Project editors can view and edit",
      "permissions": ["can_view", "can_edit"],
      "effect": "allow",
      "filter": [
        {
          "prop": "projectMembership.role",
          "op": "==",
          "value": "editor"
        }
      ]
    },
    {
      "description": "Project viewers can only view",
      "permissions": ["can_view"],
      "effect": "allow",
      "filter": [
        {
          "prop": "projectMembership.role",
          "op": "==",
          "value": "viewer"
        }
      ]
    }
  ]
}');

INSERT OR IGNORE INTO resource_policies (resource_id, policy_document) VALUES
('urn:resource:team1:proj1:doc2', '{
  "resource": {
    "resourceId": "urn:resource:team1:proj1:doc2",
    "creatorId": "creator1"
  },
  "policies": [
    {
      "description": "Creator has full access",
      "permissions": ["can_view", "can_edit", "can_delete", "can_share"],
      "effect": "allow",
      "filter": [
        {
          "prop": "document.creatorId",
          "op": "==",
          "value": "user.id"
        }
      ]
    },
    {
      "description": "Public link allows view access",
      "permissions": ["can_view"],
      "effect": "allow",
      "filter": [
        {
          "prop": "document.publicLinkEnabled",
          "op": "==",
          "value": true
        }
      ]
    }
  ]
}');

-- ===============================================================================
-- 8. SAMPLE USER POLICIES (Optional)
-- ===============================================================================

INSERT OR IGNORE INTO user_policies (user_id, policy_document) VALUES
('user1', '{
  "policies": [
    {
      "description": "Admin has god mode",
      "permissions": ["can_view", "can_edit", "can_delete", "can_share"],
      "effect": "allow",
      "filter": []
    }
  ]
}');

-- ===============================================================================
-- MIGRATION COMPLETE
-- ===============================================================================
