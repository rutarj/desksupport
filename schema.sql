DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS provisioning_log;
DROP TABLE IF EXISTS kb_articles;

CREATE TABLE kb_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    source_policy TEXT,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Draft',
    version INTEGER NOT NULL DEFAULT 1,
    view_count INTEGER NOT NULL DEFAULT 0,
    helpful_votes INTEGER NOT NULL DEFAULT 0,
    unhelpful_votes INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_name TEXT NOT NULL,
    department TEXT NOT NULL,
    category TEXT NOT NULL,
    priority TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Open',
    assigned_to TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    article_id INTEGER,
    first_contact INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (article_id) REFERENCES kb_articles(id)
);

CREATE TABLE provisioning_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    target TEXT NOT NULL,
    detail TEXT NOT NULL,
    status TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
