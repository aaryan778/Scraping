-- Initial database setup for job scraper
-- This runs automatically when PostgreSQL container starts

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For fuzzy text search

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE jobs_db TO jobscraper;

-- Note: Tables will be created by SQLAlchemy models
