-- Create user if not exists
CREATE USER "user" WITH PASSWORD 'password';

-- Create database
CREATE DATABASE news_db;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE news_db TO "user";

-- Connect to news_db
\c news_db

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO "user";
