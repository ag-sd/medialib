import tempfile
import unittest

from app.database.ds import Database, DatabaseQueryError
from tests.database import test_utils


class TestIndexingAndSearching(unittest.TestCase):

    def test_fail_search_for_virtual_database(self):
        tmp_files = test_utils.get_temp_files(2)
        db = Database.create_in_memory(paths=tmp_files)

        try:
            db.query("select 1 from 1", db.paths)
            self.fail("In memory databases should not be queried")
        except DatabaseQueryError:
            pass

    def test_invalid_query(self):
        with tempfile.TemporaryDirectory() as db_path:
            db = test_utils.create_test_media_db(db_path)
            db.save()
            try:
                db.query("select foo from bar", db.paths)
                self.fail("Invalid query should fail")
            except DatabaseQueryError:
                pass

    def test_for_selective_paths(self):
        with tempfile.TemporaryDirectory() as db_path:
            db = test_utils.create_test_media_db(db_path)
            db.save()
            result = db.query("select * from database", db.paths[:1])
            self.assertEqual(len(result.data), 2)
            self.assertEqual(len(result.columns), 88)

    def test_for_all_paths(self):
        with tempfile.TemporaryDirectory() as db_path:
            db = test_utils.create_test_media_db(db_path)
            db.save()
            result = db.query("select * from database", db.paths)
            self.assertEqual(len(result.data), 6)
            self.assertEqual(len(result.columns), 88)
