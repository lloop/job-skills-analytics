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

CREATE TABLE IF NOT EXISTS posting_skills (
    job_id INTEGER NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
    skill TEXT NOT NULL,
    PRIMARY KEY (job_id, skill)
);

CREATE INDEX IF NOT EXISTS idx_posting_skills_skill ON posting_skills(skill);
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
        self.connection.execute("DELETE FROM posting_skills WHERE job_id = ?", (job_id,))
        unique_skills = {(skill.strip(),) for skill in skills if skill and skill.strip()}
        self.connection.executemany(
            "INSERT INTO posting_skills (job_id, skill) VALUES (?, ?)",
            [(job_id, skill) for skill, in unique_skills],
        )
            
    def get_skill_co_occurrences(self, min_count: int = 2) -> list[sqlite3.Row]:
        """Fetch raw co-occurrence counts for skill pairs appearing together at least `min_count` times."""
        query = """
            SELECT 
                s1.skill AS skill_a, 
                s2.skill AS skill_b, 
                COUNT(*) AS pair_count
            FROM posting_skills s1
            JOIN posting_skills s2 
                ON s1.job_id = s2.job_id 
                AND s1.skill < s2.skill
            GROUP BY s1.skill, s2.skill
            HAVING pair_count >= ?
            ORDER BY pair_count DESC;
        """
        return self.connection.execute(query, (min_count,)).fetchall()

    def get_normalized_co_occurrences(self, min_count: int = 2) -> list[dict[str, Any]]:
        """Calculate Jaccard Similarity weights between skill pairs.
        
        Jaccard = Count(A ∩ B) / (Count(A) + Count(B) - Count(A ∩ B))
        """
        query = """
            WITH skill_counts AS (
                SELECT skill, COUNT(*) AS total_count
                FROM posting_skills
                GROUP BY skill
            ),
            pair_counts AS (
                SELECT 
                    s1.skill AS skill_a, 
                    s2.skill AS skill_b, 
                    COUNT(*) AS intersection_count
                FROM posting_skills s1
                JOIN posting_skills s2 
                    ON s1.job_id = s2.job_id 
                    AND s1.skill < s2.skill
                GROUP BY s1.skill, s2.skill
                HAVING intersection_count >= ?
            )
            SELECT 
                p.skill_a,
                p.skill_b,
                p.intersection_count,
                ca.total_count AS count_a,
                cb.total_count AS count_b,
                ROUND(
                    CAST(p.intersection_count AS REAL) / 
                    (ca.total_count + cb.total_count - p.intersection_count), 4
                ) AS jaccard_index
            FROM pair_counts p
            JOIN skill_counts ca ON p.skill_a = ca.skill
            JOIN skill_counts cb ON p.skill_b = cb.skill
            ORDER BY jaccard_index DESC;
        """
        cursor = self.connection.execute(query, (min_count,))
        return [dict(row) for row in cursor.fetchall()]

    def get_network_edge_list(self, min_jaccard: float = 0.1) -> list[tuple[str, str, float]]:
        """Return an edge list format (source, target, weight) ready for NetworkX graphs."""
        co_occurrences = self.get_normalized_co_occurrences(min_count=1)
        return [
            (row["skill_a"], row["skill_b"], row["jaccard_index"])
            for row in co_occurrences
            if row["jaccard_index"] >= min_jaccard
        ]



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
