import unittest
from database.db_manager import DatabaseManager, _posting_values
from scraper.parser import JobPosting


class TestDatabaseManager(unittest.TestCase):

    def setUp(self) -> None:
        """Instantiate an in-memory database for isolation."""
        self.db = DatabaseManager(":memory:")

        self.sample_posting = JobPosting(
            title="Backend Engineer",
            company="TechCorp",
            salary="$120,000",
            description="Build scalable APIs.",
            url="https://example.com/job/1",
            tags=("python", "docker"),
        )

    def tearDown(self) -> None:
        """Close the database connection after each test."""
        self.db.close()

    def test_schema_initialization(self) -> None:
        """Verify job_postings, posting_skills, and index are initialized."""
        cursor = self.db.connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        )
        tables = [row["name"] for row in cursor.fetchall()]

        self.assertIn("job_postings", tables)
        self.assertIn("posting_skills", tables)

    def test_upsert_posting_inserts_new_record_and_skills(self) -> None:
        """Verify inserting a new posting saves posting and skill records."""
        job_id = self.db.upsert_posting(self.sample_posting, skills=["python", "docker", ""])

        self.assertIsInstance(job_id, int)

        # Check job posting record
        row = self.db.fetch_posting("https://example.com/job/1")
        self.assertIsNotNone(row)
        self.assertEqual(row["title"], "Backend Engineer")
        self.assertEqual(row["company"], "TechCorp")

        # Check skills table (empty skill "" should be ignored)
        cursor = self.db.connection.execute(
            "SELECT skill FROM posting_skills WHERE job_id = ? ORDER BY skill", (job_id,)
        )
        skills = [r["skill"] for r in cursor.fetchall()]
        self.assertEqual(skills, ["docker", "python"])

    def test_upsert_posting_updates_existing_record_and_replaces_skills(self) -> None:
        """Verify ON CONFLICT(url) updates posting details and replaces old skills."""
        job_id_1 = self.db.upsert_posting(self.sample_posting, skills=["python", "flask"])

        updated_posting = JobPosting(
            title="Senior Backend Engineer",
            company="TechCorp",
            salary="$140,000",
            description="Build scalable microservices.",
            url="https://example.com/job/1",
            tags=("python", "fastapi"),
        )

        job_id_2 = self.db.upsert_posting(updated_posting, skills=["python", "fastapi"])

        # IDs should match
        self.assertEqual(job_id_1, job_id_2)

        # Record should be updated
        row = self.db.fetch_posting("https://example.com/job/1")
        self.assertEqual(row["title"], "Senior Backend Engineer")
        self.assertEqual(row["salary"], "$140,000")

        # Skills should be replaced with new set
        cursor = self.db.connection.execute(
            "SELECT skill FROM posting_skills WHERE job_id = ? ORDER BY skill", (job_id_2,)
        )
        skills = [r["skill"] for r in cursor.fetchall()]
        self.assertEqual(skills, ["fastapi", "python"])

    def test_upsert_postings_batch(self) -> None:
        """Verify batch upserting multiple postings."""
        posting2 = JobPosting(
            title="Frontend Engineer",
            company="DesignCo",
            salary=None,
            description="Build UI components.",
            url="https://example.com/job/2",
        )

        batch = [
            (self.sample_posting, ["python"]),
            (posting2, ["react", "typescript"]),
        ]

        processed_count = self.db.upsert_postings(batch)
        self.assertEqual(processed_count, 2)

        cursor = self.db.connection.execute("SELECT COUNT(*) as count FROM job_postings")
        self.assertEqual(cursor.fetchone()["count"], 2)

    def test_context_manager(self) -> None:
        """Verify DatabaseManager functions as a context manager."""
        with DatabaseManager(":memory:") as db:
            job_id = db.upsert_posting(self.sample_posting, skills=["python"])
            self.assertGreater(job_id, 0)

    def test_posting_values_dict_and_object_support(self) -> None:
        """Verify _posting_values extracts values from dataclasses/objects and dicts."""
        # Test object/dataclass
        obj_res = _posting_values(self.sample_posting)
        self.assertEqual(obj_res["title"], "Backend Engineer")

        # Test dictionary mapping
        dict_input = {
            "title": " Data Scientist ",
            "company": " DataInc ",
            "salary": None,
            "description": " ML models ",
            "url": " https://example.com/job/3 ",
        }
        dict_res = _posting_values(dict_input)
        self.assertEqual(dict_res["title"], "Data Scientist")
        self.assertIsNone(dict_res["salary"])

    def test_posting_values_raises_value_error_on_missing_fields(self) -> None:
        """Verify _posting_values raises ValueError when required fields are missing."""
        invalid_posting = {"title": "Engineer", "company": "Co"}  # missing url & description

        with self.assertRaises(ValueError) as ctx:
            _posting_values(invalid_posting)

        self.assertIn("Posting is missing required fields", str(ctx.exception))
        
    def test_get_normalized_co_occurrences(self) -> None:
        """Verify Jaccard index calculation for co-occurring skills."""
        # Setup: Job 1 has (python, docker, aws), Job 2 has (python, docker)
        p1 = JobPosting("Dev 1", "Co1", None, "Desc", "https://ex.com/1")
        p2 = JobPosting("Dev 2", "Co2", None, "Desc", "https://ex.com/2")

        self.db.upsert_posting(p1, skills=["python", "docker", "aws"])
        self.db.upsert_posting(p2, skills=["python", "docker"])

        # Execution
        results = self.db.get_normalized_co_occurrences(min_count=1)

        # 'docker' and 'python' both appear in 2 postings together
        # Jaccard = 2 / (2 + 2 - 2) = 1.0
        top_pair = next(
            r for r in results 
            if set([r["skill_a"], r["skill_b"]]) == {"docker", "python"}
        )
        self.assertEqual(top_pair["intersection_count"], 2)
        self.assertEqual(top_pair["jaccard_index"], 1.0)

        # 'aws' and 'python': Intersection = 1, Total(aws)=1, Total(python)=2
        # Jaccard = 1 / (1 + 2 - 1) = 0.5
        aws_python_pair = next(
            r for r in results 
            if set([r["skill_a"], r["skill_b"]]) == {"aws", "python"}
        )
        self.assertEqual(aws_python_pair["jaccard_index"], 0.5)


if __name__ == "__main__":
    unittest.main()