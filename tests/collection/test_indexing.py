import tempfile
import unittest

from app.collection.ds import Collection, CollectionQueryError
from tests.collection import test_utils


class TestIndexingAndSearching(unittest.TestCase):

    def test_fail_search_for_virtual_database(self):
        tmp_files = test_utils.get_temp_files(2)
        db = Collection.create_in_memory(paths=tmp_files)

        try:
            db.query("select 1 from 1", db.paths)
            self.fail("In memory databases should not be queried")
        except CollectionQueryError:
            pass

    def test_invalid_query(self):
        with tempfile.TemporaryDirectory() as db_path:
            db = test_utils.create_test_media_db(db_path)
            db.save()
            try:
                db.query("select foo from bar", db.paths)
                self.fail("Invalid query should fail")
            except CollectionQueryError:
                pass

    def test_for_selective_paths(self):
        with tempfile.TemporaryDirectory() as db_path:
            db = test_utils.create_test_media_db(db_path)
            db.save()
            result = db.query("select * from collection", db.paths[:1])
            self.assertEqual(len(result.data), 1)
            self.assertEqual(len(result.columns), 88)
            for d in result.data:
                if d.path.endswith("audio"):
                    self.assertEqual(len(d.results), 2)
                elif d.path.endswith("image"):
                    self.assertEqual(len(d.results), 4)
                else:
                    self.fail("Unexpected path!")

    def test_for_all_paths(self):
        with tempfile.TemporaryDirectory() as db_path:
            db = test_utils.create_test_media_db(db_path)
            db.save()
            result = db.query("select * from collection", db.paths)
            # Results will be grouped by paths
            self.assertEqual(len(result.data), len(db.paths))
            self.assertEqual(len(result.columns), 88)
            for d in result.data:
                if d.path.endswith("audio"):
                    self.assertEqual(len(d.results), 2)
                elif d.path.endswith("image"):
                    self.assertEqual(len(d.results), 4)
                else:
                    self.fail("Unexpected path!")
