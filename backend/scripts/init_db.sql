-- scripts/init_db.sql
-- Runs once when PostgreSQL container first starts.
-- Creates extensions needed by HaDir HRMS.

-- UUID generation (used in all tables)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Full-text search (employee name search)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Unaccent for Indonesian name search (handles é, ü etc)
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Optimised JSONB indexing (audit_logs.old_values / new_values)
-- Already built into Postgres 16 — just ensuring available

-- Set timezone for all connections from this database
ALTER DATABASE hadir_db SET timezone TO 'UTC';

-- Comment
COMMENT ON DATABASE hadir_db IS 'HaDir HRMS — Indonesia SaaS HR Platform';
