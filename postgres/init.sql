-- -- Load dblink extension if needed
-- CREATE EXTENSION IF NOT EXISTS dblink;

-- -- Ensure the database exists
-- DO $$ BEGIN
--    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'news_db') THEN
--       EXECUTE 'CREATE DATABASE news_db';
--    END IF;
-- END $$;

-- -- Connect to the newly created database
-- \connect news_db

-- Grant privileges
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;

-- Create articles table
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    main_keyword VARCHAR NOT NULL DEFAULT 'default_keyword',
    naver_link VARCHAR NOT NULL,
    original_link VARCHAR,
    title VARCHAR NOT NULL,
    description TEXT,
    publisher VARCHAR,
    publisher_domain VARCHAR,
    published_at TIMESTAMP WITH TIME ZONE,
    published_date VARCHAR,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_naver_news BOOLEAN DEFAULT TRUE,
    is_test BOOLEAN NOT NULL DEFAULT TRUE,
    is_api_collection BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (main_keyword, naver_link)
);

-- Create contents table
CREATE TABLE IF NOT EXISTS contents (
    id SERIAL PRIMARY KEY,
    article_id INTEGER UNIQUE REFERENCES articles(id),
    title VARCHAR,
    content TEXT,
    subheadings TEXT[],
    reporter VARCHAR,
    media VARCHAR,
    published_at TIMESTAMP WITH TIME ZONE,
    modified_at TIMESTAMP WITH TIME ZONE,
    category VARCHAR,
    images JSONB,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create comments table
CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES articles(id),
    comment_no VARCHAR,
    parent_comment_no VARCHAR,
    content TEXT,
    username VARCHAR,
    profile_url VARCHAR,
    timestamp TIMESTAMP WITH TIME ZONE,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    likes INTEGER DEFAULT 0,
    dislikes INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    is_reply BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    delete_type VARCHAR
);

-- Create comment_stats table
CREATE TABLE IF NOT EXISTS comment_stats (
    id SERIAL PRIMARY KEY,
    comment_id INTEGER UNIQUE REFERENCES comments(id),
    current_count INTEGER DEFAULT 0,
    user_deleted_count INTEGER DEFAULT 0,
    admin_deleted_count INTEGER DEFAULT 0,
    gender_ratio JSONB DEFAULT '{"male": 0, "female": 0}',
    age_distribution JSONB DEFAULT '{
        "10s": 0, 
        "20s": 0, 
        "30s": 0, 
        "40s": 0, 
        "50s": 0, 
        "60s_above": 0
    }',
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create article_stats table
CREATE TABLE IF NOT EXISTS article_stats (
    id SERIAL PRIMARY KEY,
    article_id INTEGER UNIQUE REFERENCES articles(id),
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    dislike_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at);
CREATE INDEX IF NOT EXISTS idx_articles_publisher ON articles(publisher);
CREATE INDEX IF NOT EXISTS idx_comments_article_id ON comments(article_id);
CREATE INDEX IF NOT EXISTS idx_comments_timestamp ON comments(timestamp);
