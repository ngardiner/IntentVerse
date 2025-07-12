-- PostgreSQL initialization script for IntentVerse
-- This script sets up the database with recommended extensions and settings

-- Create extensions that might be useful for IntentVerse
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- For UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- For text search improvements

-- Set recommended PostgreSQL settings for IntentVerse
-- These can be overridden in postgresql.conf if needed

-- Improve performance for small to medium databases
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET track_activity_query_size = 2048;
ALTER SYSTEM SET track_io_timing = on;

-- Optimize for typical web application workload
ALTER SYSTEM SET random_page_cost = 1.1;  -- Assuming SSD storage
ALTER SYSTEM SET effective_cache_size = '256MB';  -- Adjust based on available memory

-- Improve connection handling
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET shared_buffers = '64MB';

-- Enable logging for debugging (can be disabled in production)
ALTER SYSTEM SET log_statement = 'mod';  -- Log all DDL and DML statements
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log slow queries (>1s)

-- Apply the configuration changes
SELECT pg_reload_conf();

-- Create a comment to document the setup
COMMENT ON DATABASE intentverse IS 'IntentVerse application database - PostgreSQL backend';