import sqlite3
import tempfile
import unittest
from pathlib import Path

from scraper.parser import JobPosting
from scraper.storage import init_db, save_postings


class TestStorage(unittest.TestCase):

    def setUp(self) -> None:
        """Create a temporary directory before each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = Path(self.temp_dir.name) / "nested_dir" / "test_jobs.sqlite3"

        self.sample_postings = [
            JobPosting(
                title="Python Software Engineer",
                company="TechCorp",
                salary="$120k",
                description="Develop backend services.",
                url="https://example.com/job/1",
                tags=("python", "docker", "sql"),
            ),
            JobPosting(
                title="Data Scientist",
                company="DataInc",
                salary=None,
                description="Analyze large datasets.",
                url="https://example.com/job/2",
                tags=("python", "pandas", "machine learning"),
            ),
        ]

    def tearDown(self) -> None:
        """Clean up the temporary directory after each test."""
        self.temp_dir.cleanup()

    def test_init_db_creates_directory_and_tables(self) -> None:
        """Verify init_db creates nested directories and expected relational tables."""
        init_db(db_path=self.test_db_path)

        # 1. Check if directory and file were created
        self.assertTrue(self.test_db_path.exists())

        # 2. Check if tables exist in the database
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
            )
            tables = [row[0] for row in cursor.fetchall()]

            self.assertIn("postings", tables)
            self.assertIn("skills", tables)
            self.assertIn("posting_skills", tables)

    def test_save_postings_populates_relational_tables(self) -> None:
        """Verify postings, skills, and junction records are correctly inserted."""
        inserted_count = save_postings(self.sample_postings, db_path=self.test_db_path)

        self.assertEqual(inserted_count, 2)

        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()

            # Verify postings count
            cursor.execute("SELECT COUNT(*) FROM postings")
            self.assertEqual(cursor.fetchone()[0], 2)

            # Verify unique skills count ('python' appears in both, so 5 unique skills total)
            cursor.execute("SELECT COUNT(*) FROM skills")
            self.assertEqual(cursor.fetchone()[0], 5)

            # Verify relationships in posting_skills (3 tags + 3 tags = 6 rows)
            cursor.execute("SELECT COUNT(*) FROM posting_skills")
            self.assertEqual(cursor.fetchone()[0], 6)

    def test_save_postings_handles_duplicates(self) -> None:
        """Verify re-inserting identical postings avoids duplicate entries."""
        # First save
        first_insert = save_postings(self.sample_postings, db_path=self.test_db_path)
        self.assertEqual(first_insert, 2)

        # Attempt second save with same URLs
        second_insert = save_postings(self.sample_postings, db_path=self.test_db_path)
        self.assertEqual(second_insert, 0)

        # Database counts should remain unchanged
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM postings")
            self.assertEqual(cursor.fetchone()[0], 2)


if __name__ == "__main__":
    unittest.main()