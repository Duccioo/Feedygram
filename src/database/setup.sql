PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS user (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    firstname TEXT NOT NULL,
    lastname TEXT,
    language TEXT,
    is_bot INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS web (
    url TEXT PRIMARY KEY,
    last_title TEXT NOT NULL,
    last_updated TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS web_user (
    url TEXT,
    telegram_id INTEGER,
    alias TEXT NOT NULL,
    telegraph INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (url, telegram_id),
    FOREIGN KEY(url) REFERENCES web(url) ON DELETE CASCADE,
    FOREIGN KEY(telegram_id) REFERENCES user(telegram_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_web_user_alias ON web_user(alias);
CREATE INDEX IF NOT EXISTS idx_web_last_updated ON web(last_updated);