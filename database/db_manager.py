"""Database management for storing job postings, skills, and their relationships."""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Optional, Sequence

from models import JobPosting

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database connections and operations for job market analytics."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Establish a connection to the SQLite database and enable foreign keys."""
        if not self.connection:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys = ON;")
        return self.connection

    def close(self) -> None:
        """Close the database connection if open."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def __enter__(self) -> "DatabaseManager":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.connection:
            if exc_type is None:
                self.connection.commit()
            else:
                self.connection.rollback()
        self.close()

    def upsert_posting(self, posting: JobPosting, skills: Optional[Sequence[str]] = None) -> int:
        """Insert a new posting or update an existing one based on URL.

        Also updates the associated skills in the posting_skills junction table.
        """
        conn = self.connect()
        cursor = conn.cursor()

        posting_dict = posting.to_dict()

        query = """
            INSERT INTO postings (
                source, external_id, title, company, location,
                salary, url, posted_date, description, raw_data, updated_at
            ) VALUES (
                :source, :external_id, :title, :company, :location,
                :salary, :url, :posted_date, :description, :raw_data, CURRENT_TIMESTAMP
            )
            ON CONFLICT(url) DO UPDATE SET
                source=excluded.source,
                external_id=excluded.external_id,
                title=excluded.title,
                company=excluded.company,
                location=excluded.location,
                salary=excluded.salary,
                posted_date=excluded.posted_date,
                description=excluded.description,
                raw_data=excluded.raw_data,
                updated_at=CURRENT_TIMESTAMP
            RETURNING id;
        """

        cursor.execute(query, posting_dict)
        posting_id = cursor.fetchone()["id"]

        if skills is not None:
            self._replace_skills(posting_id, skills)

        conn.commit()
        return posting_id

    def upsert_postings(self, postings: Sequence[tuple[JobPosting, Sequence[str]]]) -> int:
        """Batch upsert multiple postings and their associated skills."""
        conn = self.connect()
        count = 0
        try:
            for posting, skills in postings:
                self.upsert_posting(posting, skills)
                count += 1
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed batch upsert: {e}")
            raise
        return count

    def get_posting_by_url(self, url: str) -> Optional[dict[str, Any]]:
        """Retrieve a posting dictionary by its URL."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM postings WHERE url = ?", (url,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_skills_for_posting(self, posting_id: int) -> list[str]:
        """Retrieve skill names associated with a specific posting ID."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.name 
            FROM skills s
            JOIN posting_skills ps ON s.id = ps.skill_id
            WHERE ps.posting_id = ?
            ORDER BY s.name ASC
            """,
            (posting_id,),
        )
        return [row[0] for row in cursor.fetchall()]

    def _replace_skills(self, posting_id: int, skills: Sequence[str]) -> None:
        """Clear existing skill relationships and insert new skill connections."""
        conn = self.connect()
        cursor = conn.cursor()

        # Delete existing associations
        cursor.execute("DELETE FROM posting_skills WHERE posting_id = ?", (posting_id,))

        # Clean and deduplicate skill names
        clean_skills = sorted(list({s.strip().lower() for s in skills if s and s.strip()}))
        if not clean_skills:
            return

        # 1. Ensure skills exist in master table
        cursor.executemany(
            "INSERT OR IGNORE INTO skills (name) VALUES (?)",
            [(s,) for s in clean_skills],
        )

        # 2. Get skill IDs
        placeholders = ",".join("?" for _ in clean_skills)
        cursor.execute(
            f"SELECT id, name FROM skills WHERE name IN ({placeholders})",
            clean_skills,
        )
        skill_map = {row["name"]: row["id"] for row in cursor.fetchall()}

        # 3. Insert relationships into bridge table
        skill_links = [(posting_id, skill_map[s]) for s in clean_skills if s in skill_map]
        cursor.executemany(
            "INSERT OR IGNORE INTO posting_skills (posting_id, skill_id) VALUES (?, ?)",
            skill_links,
        )

    def get_co_occurrences(self, min_frequency: int = 1) -> list[dict[str, Any]]:
        """Calculate skill co-occurrences across all postings."""
        conn = self.connect()
        cursor = conn.cursor()

        query = """
            SELECT 
                s1.name AS skill_a,
                s2.name AS skill_b,
                COUNT(*) AS weight
            FROM posting_skills ps1
            JOIN posting_skills ps2 ON ps1.posting_id = ps2.posting_id AND ps1.skill_id < ps2.skill_id
            JOIN skills s1 ON ps1.skill_id = s1.id
            JOIN skills s2 ON ps2.skill_id = s2.id
            GROUP BY s1.name, s2.name
            HAVING weight >= ?
            ORDER BY weight DESC;
        """

        cursor.execute(query, (min_frequency,))
        return [dict(row) for row in cursor.fetchall()]

    def get_normalized_co_occurrences(self, min_jaccard: float = 0.0) -> list[dict[str, Any]]:
        """Calculate Jaccard similarity between skills based on co-occurrence."""
        conn = self.connect()
        cursor = conn.cursor()

        query = """
            WITH skill_counts AS (
                SELECT skill_id, COUNT(posting_id) AS total_postings
                FROM posting_skills
                GROUP BY skill_id
            ),
            co_occurrences AS (
                SELECT 
                    ps1.skill_id AS skill_a_id,
                    ps2.skill_id AS skill_b_id,
                    COUNT(ps1.posting_id) AS intersection_count
                FROM posting_skills ps1
                JOIN posting_skills ps2 ON ps1.posting_id = ps2.posting_id AND ps1.skill_id < ps2.skill_id
                GROUP BY ps1.skill_id, ps2.skill_id
            )
            SELECT 
                sa.name AS source,
                sb.name AS target,
                co.intersection_count,
                sc1.total_postings AS count_a,
                sc2.total_postings AS count_b,
                CAST(co.intersection_count AS FLOAT) / 
                    (sc1.total_postings + sc2.total_postings - co.intersection_count) AS jaccard
            FROM co_occurrences co
            JOIN skills sa ON co.skill_a_id = sa.id
            JOIN skills sb ON co.skill_b_id = sb.id
            JOIN skill_counts sc1 ON co.skill_a_id = sc1.skill_id
            JOIN skill_counts sc2 ON co.skill_b_id = sc2.skill_id
            WHERE CAST(co.intersection_count AS FLOAT) / 
                (sc1.total_postings + sc2.total_postings - co.intersection_count) >= ?
            ORDER BY jaccard DESC;
        """

        cursor.execute(query, (min_jaccard,))
        return [dict(row) for row in cursor.fetchall()]