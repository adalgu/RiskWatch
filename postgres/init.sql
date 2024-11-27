-- Create user if not exists
-- CREATE USER "postgres" WITH PASSWORD 'password';

-- Create database
CREATE DATABASE news_db;

-- Grant privileges to postgres user (which is created by default)
GRANT ALL PRIVILEGES ON DATABASE news_db TO postgres;

-- Connect to news_db
\c news_db

-- Grant schema privileges to postgres user
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;
