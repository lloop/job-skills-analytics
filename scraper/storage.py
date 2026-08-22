import sqlite3
from pathlib import Path
from config import DATABASE_PATH
from typing import Sequence
from .parser import JobPosting


def init_db(db_path: str | Path = DATABASE_PATH) -> None:
    """Initialize relational SQLite database schema for postings and skills."""
    
    path = Path(db_path)
    # Ensure directory exists before connecting
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS postings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                salary TEXT,
                description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS posting_skills (
                posting_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                PRIMARY KEY (posting_id, skill_id),
                FOREIGN KEY (posting_id) REFERENCES postings(id) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
            );
            """
        )
        conn.commit()


def save_postings(postings: Sequence[JobPosting], db_path: str | Path = DATABASE_PATH) -> int:
    """Insert postings and their tags into the SQLite database."""
    if not postings:
        return 0

    init_db(db_path)
    new_inserted = 0

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()

        for p in postings:
            # 1. Insert posting metadata
            cursor.execute(
                """
                INSERT OR IGNORE INTO postings (url, title, company, salary, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                (p.url, p.title, p.company, p.salary, p.description),
            )
            
            if cursor.rowcount > 0:
                new_inserted += 1

            # Fetch posting_id for linking tags
            cursor.execute("SELECT id FROM postings WHERE url = ?", (p.url,))
            posting_row = cursor.fetchone()
            if not posting_row:
                continue
            posting_id = posting_row[0]

            # 2. Insert tags and establish relationships
            for tag in p.tags:
                tag_cleaned = tag.strip().lower()
                if not tag_cleaned:
                    continue

                cursor.execute(
                    "INSERT OR IGNORE INTO skills (name) VALUES (?)",
                    (tag_cleaned,),
                )
                cursor.execute("SELECT id FROM skills WHERE name = ?", (tag_cleaned,))
                skill_id = cursor.fetchone()[0]

                cursor.execute(
                    "INSERT OR IGNORE INTO posting_skills (posting_id, skill_id) VALUES (?, ?)",
                    (posting_id, skill_id),
                )

        conn.commit()

    return new_inserted