"""SQLite storage for job postings and their skills."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
SCHEMA = SCHEMA_PATH.read_text()


class DatabaseManager:
    """Manage job data with URL-based deduplication and batch writes."""

    def __init__(self, database_path: str | Path = "jobs.sqlite3") -> None:
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
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
            posting_id = self._upsert(posting_data)
            self._replace_skills(posting_id, skills)
        return posting_id

    def upsert_postings(self, postings: Iterable[tuple[Any, Iterable[str]]]) -> int:
        """Upsert a batch and return the number of processed postings."""
        processed = 0
        with self.connection:
            for posting, skills in postings:
                posting_id = self._upsert(_posting_values(posting))
                self._replace_skills(posting_id, skills)
                processed += 1
        return processed

    def fetch_posting(self, url: str) -> sqlite3.Row | None:
        """Return the posting for a URL, or ``None`` when it is missing."""
        return self.connection.execute(
            "SELECT * FROM postings WHERE url = ?", (url,)
        ).fetchone()

    def fetch_skills(self, posting_id: int) -> list[str]:
        """Return the skill names linked to a posting, sorted alphabetically."""
        rows = self.connection.execute(
            """SELECT s.name
            FROM posting_skills ps
            JOIN skills s ON s.id = ps.skill_id
            WHERE ps.posting_id = ?
            ORDER BY s.name""",
            (posting_id,),
        ).fetchall()
        return [row["name"] for row in rows]

    def close(self) -> None:
        """Close the SQLite connection."""
        self.connection.close()

    def __enter__(self) -> DatabaseManager:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _upsert(self, posting: dict[str, str | None]) -> int:
        cursor = self.connection.execute(
            """INSERT INTO postings (title, company, salary, description, url)
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

    def _replace_skills(self, posting_id: int, skills: Iterable[str]) -> None:
        self.connection.execute(
            "DELETE FROM posting_skills WHERE posting_id = ?", (posting_id,)
        )
        unique_skills = {normalize_skill(skill) for skill in skills if normalize_skill(skill)}
        self.connection.executemany(
            "INSERT OR IGNORE INTO skills (name) VALUES (?)",
            [(skill,) for skill in unique_skills],
        )
        self.connection.executemany(
            """INSERT OR IGNORE INTO posting_skills (posting_id, skill_id)
            SELECT ?, id FROM skills WHERE name = ?""",
            [(posting_id, skill) for skill in unique_skills],
        )

    def get_skill_co_occurrences(self, min_count: int = 2) -> list[sqlite3.Row]:
        """Fetch co-occurrence counts for pairs seen together at least `min_count` times."""
        query = """
            SELECT
                s1.name AS skill_a,
                s2.name AS skill_b,
                COUNT(*) AS pair_count
            FROM posting_skills ps1
            JOIN posting_skills ps2
                ON ps1.posting_id = ps2.posting_id
                AND ps1.skill_id < ps2.skill_id
            JOIN skills s1 ON s1.id = ps1.skill_id
            JOIN skills s2 ON s2.id = ps2.skill_id
            GROUP BY s1.name, s2.name
            HAVING pair_count >= ?
            ORDER BY pair_count DESC;
        """
        return self.connection.execute(query, (min_count,)).fetchall()

    def get_normalized_co_occurrences(self, min_count: int = 1) -> list[dict[str, Any]]:
        """Compute the pairwise Jaccard index for skill co-occurrences."""
        query = """
        WITH skill_counts AS (
            SELECT skill_id, COUNT(DISTINCT posting_id) AS total_postings
            FROM posting_skills
            GROUP BY skill_id
        ),
        co_occurrences AS (
            SELECT
                ps1.skill_id AS skill_a_id,
                ps2.skill_id AS skill_b_id,
                COUNT(DISTINCT ps1.posting_id) AS shared_postings
            FROM posting_skills ps1
            JOIN posting_skills ps2
                ON ps1.posting_id = ps2.posting_id
                AND ps1.skill_id < ps2.skill_id
            GROUP BY ps1.skill_id, ps2.skill_id
            HAVING shared_postings >= ?
        )
        SELECT
            s1.name AS skill_a,
            s2.name AS skill_b,
            c.shared_postings,
            CAST(c.shared_postings AS FLOAT)
                / (sc1.total_postings + sc2.total_postings - c.shared_postings) AS jaccard_index
        FROM co_occurrences c
        JOIN skills s1 ON c.skill_a_id = s1.id
        JOIN skills s2 ON c.skill_b_id = s2.id
        JOIN skill_counts sc1 ON c.skill_a_id = sc1.skill_id
        JOIN skill_counts sc2 ON c.skill_b_id = sc2.skill_id
        ORDER BY jaccard_index DESC;
        """
        rows = self.connection.execute(query, (min_count,)).fetchall()
        return [dict(row) for row in rows]

    def get_network_edge_list(self, min_jaccard: float = 0.1) -> list[tuple[str, str, float]]:
        """Return an edge list (source, target, weight) ready for graph rendering."""
        co_occurrences = self.get_normalized_co_occurrences(min_count=1)
        return [
            (row["skill_a"], row["skill_b"], row["jaccard_index"])
            for row in co_occurrences
            if row["jaccard_index"] >= min_jaccard
        ]


def normalize_skill(skill: str) -> str:
    """Return the canonical stored form of a skill name."""
    return skill.strip().lower()


def _posting_values(posting: Any) -> dict[str, str | None]:
    """Read posting fields from a mapping or an object with matching attributes."""
    if isinstance(posting, Mapping):
        def get_value(key: str) -> Any:
            return posting.get(key)
    else:
        def get_value(key: str) -> Any:
            return getattr(posting, key, None)

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
