"""SQLite storage for raw job postings and extracted skills."""

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from scraper.parser import JobPosting


class DatabaseManager:
    """Persist job postings and their parsed skills."""

    def __init__(self, database_path: str | Path = "jobs.sqlite3") -> None:
        self.connection = sqlite3.connect(database_path)
        self.connection.execute("PRAGMA foreign_keys = ON")

    def add_posting(self, posting: JobPosting, skills: Iterable[str]) -> None:
        cursor = self.connection.execute(
            """INSERT OR IGNORE INTO job_postings (title, company, salary, description, url)
            VALUES (?, ?, ?, ?, ?)""",
            (posting.title, posting.company, posting.salary, posting.description, posting.url),
        )
        if cursor.rowcount:
            job_id = cursor.lastrowid
            self.connection.executemany(
                "INSERT OR IGNORE INTO job_skills (job_id, skill) VALUES (?, ?)",
                [(job_id, skill) for skill in skills],
            )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
