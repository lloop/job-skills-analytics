CREATE TABLE IF NOT EXISTS postings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    salary TEXT,
    description TEXT NOT NULL,
    collected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS posting_skills (
    posting_id INTEGER NOT NULL REFERENCES postings(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (posting_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_posting_skills_posting ON posting_skills(posting_id);
CREATE INDEX IF NOT EXISTS idx_posting_skills_skill ON posting_skills(skill_id);
