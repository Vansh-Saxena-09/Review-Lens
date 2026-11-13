import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

class BackendContractTests(unittest.TestCase):
    def test_schema_rejects_blank_review(self):
        from schemas import ReviewInput
        with self.assertRaises(Exception):
            ReviewInput(text="   ")

    def test_schema_rejects_oversized_batch(self):
        from schemas import BatchInput, ReviewInput
        with self.assertRaises(Exception):
            BatchInput(reviews=[ReviewInput(text="ok")] * 501)

    def test_database_round_trip(self):
        import db
        original = db.DB_PATH
        with tempfile.TemporaryDirectory() as temp:
            db.DB_PATH = Path(temp) / "test.sqlite3"
            db.initialize()
            row = db.insert_analysis("safe text", "OR", 0.1, 0.9, None, "test")
            rows, total = db.list_analyses(10, 0)
            self.assertEqual(total, 1)
            self.assertEqual(rows[0]["id"], row["id"])
        db.DB_PATH = original

if __name__ == "__main__":
    unittest.main()
