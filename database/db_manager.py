"""Standalone SQLite storage for job postings and parsed skills."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

SCHEMA = """
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
"""


class DatabaseManager:
    """Manage job data with URL-based deduplication and batch writes."""

    def __init__(self, database_path: str | Path = "jobs.sqlite3") -> None:
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.initialize()

    def initialize(self) -> None:
        """Create the database schema if it does not already exist."""
        with self.connection:
            self.connection.executescript(SCHEMA)

    def upsert_posting(self, posting: Any, skills: Iterable[str] = ()) -> int:
        """Insert or update one posting, returning its database ID."""
        posting_data = _posting_values(posting)
        with self.connection:
            job_id = self._upsert(posting_data)
            self._replace_skills(job_id, skills)
        return job_id

    def add_posting(self, posting: Any, skills: Iterable[str] = ()) -> int:
        """Backward-compatible alias for :meth:`upsert_posting`."""
        return self.upsert_posting(posting, skills)

    def upsert_postings(self, postings: Iterable[tuple[Any, Iterable[str]]]) -> int:
        """Upsert a batch and return the number of processed postings."""
        processed = 0
        with self.connection:
            for posting, skills in postings:
                job_id = self._upsert(_posting_values(posting))
                self._replace_skills(job_id, skills)
                processed += 1
        return processed

    def fetch_posting(self, url: str) -> sqlite3.Row | None:
        """Return the posting for a URL, or ``None`` when it is missing."""
        return self.connection.execute(
            "SELECT * FROM job_postings WHERE url = ?", (url,)
        ).fetchone()

    def close(self) -> None:
        """Close the SQLite connection."""
        self.connection.close()

    def __enter__(self) -> DatabaseManager:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _upsert(self, posting: dict[str, str | None]) -> int:
        cursor = self.connection.execute(
            """INSERT INTO job_postings (title, company, salary, description, url)
            VALUES (:title, :company, :salary, :description, :url)
            ON CONFLICT(url) DO UPDATE SET
                title = excluded.title,
                company = excluded.company,
                salary = excluded.salary,
                description = excluded.description,
                collected_at = CURRENT_TIMESTAMP
            RETURNING id""",
            posting,
        )
        return int(cursor.fetchone()["id"])

    def _replace_skills(self, job_id: int, skills: Iterable[str]) -> None:
        self.connection.execute("DELETE FROM job_skills WHERE job_id = ?", (job_id,))
        unique_skills = {(skill.strip(),) for skill in skills if skill and skill.strip()}
        self.connection.executemany(
            "INSERT INTO job_skills (job_id, skill) VALUES (?, ?)",
            [(job_id, skill) for skill, in unique_skills],
        )


def _posting_values(posting: Any) -> dict[str, str | None]:
    """Read posting fields from a mapping or an object with matching attributes."""
    if isinstance(posting, Mapping):
        get_value = posting.get
    else:
        get_value = lambda key, default=None: getattr(posting, key, default)

    values = {
        "title": get_value("title"),
        "company": get_value("company"),
        "salary": get_value("salary"),
        "description": get_value("description"),
        "url": get_value("url"),
    }
    missing = [key for key in ("title", "company", "description", "url") if not values[key]]
    if missing:
        raise ValueError(f"Posting is missing required fields: {', '.join(missing)}")
    return {key: None if value is None else str(value).strip() for key, value in values.items()}
