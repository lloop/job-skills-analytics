"""Persist scraped postings through the shared database layer."""

from collections.abc import Sequence
from pathlib import Path

from config import DATABASE_PATH
from database.db_manager import DatabaseManager

from .parser import JobPosting


def init_db(db_path: str | Path = DATABASE_PATH) -> None:
    """Create the database file and schema if they do not exist yet."""
    DatabaseManager(db_path).close()


def save_postings(postings: Sequence[JobPosting], db_path: str | Path = DATABASE_PATH) -> int:
    """Store postings with their tags, returning how many URLs were new."""
    if not postings:
        return 0

    new_inserted = 0
    with DatabaseManager(db_path) as db:
        for posting in postings:
            is_new = db.fetch_posting(posting.url) is None
            db.upsert_posting(posting, skills=posting.tags)
            if is_new:
                new_inserted += 1

    return new_inserted
