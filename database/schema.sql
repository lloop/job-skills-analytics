CREATE TABLE IF NOT EXISTS job_postings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    salary TEXT,
    description TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    collected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_skills (
    job_id INTEGER NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
    skill TEXT NOT NULL,
    PRIMARY KEY (job_id, skill)
);

CREATE INDEX IF NOT EXISTS idx_job_skills_skill ON job_skills(skill);
