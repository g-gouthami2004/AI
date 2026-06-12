-- Stores session data
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id   TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL,
    created_at   TIMESTAMP DEFAULT NOW()
);

-- Stores every message
CREATE TABLE IF NOT EXISTS chat_messages (
    id           SERIAL PRIMARY KEY,
    session_id   TEXT REFERENCES chat_sessions(session_id),
    sender       TEXT NOT NULL,   -- 'user' or 'ai'
    message_text TEXT NOT NULL,
    created_at   TIMESTAMP DEFAULT NOW()
);