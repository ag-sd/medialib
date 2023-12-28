import tempfile
import unittest
from pathlib import Path

from app.database.ds import Database, DBType
from app.views import ViewType


class TestDatabase(unittest.TestCase):

    def test_create_default_paths_blank(self):
        try:
            Database.create_in_memory(paths=[])
        except ValueError as v:
            self.assertEqual(str(v), "Database must have at least one path")

    def test_create_default_database(self):
        tmp_files = self.get_temp_files(2)
        db = Database.create_in_memory(paths=tmp_files)
        self.assertEqual(db.type, DBType.IN_MEMORY)
        self.assertIsNone(db.save_path)
        self.assertEqual(db.name, "default-db")
        self.assertCountEqual(db.paths, tmp_files)

    def test_open_database(self):
        try:
            Database.open_db("xyz")
        except NotImplementedError as e:
            self.assertTrue(str(e) == "Not Implemented")

    def test_add_paths_dupe(self):
        tmp_files = self.get_temp_files(3)
        db = Database.create_in_memory(paths=tmp_files[:2])
        self.assertCountEqual(db.paths, tmp_files[:2])
        db.add_paths(tmp_files[2:])

        self.assertCountEqual(db.paths, tmp_files)

    def test_key_creation(self):
        # Key = "//a/b/c"
        tmp_files = self.get_temp_files(2)
        db = Database.create_in_memory(paths=tmp_files)

        key1 = db._create_path_key("//a/b/c", ViewType.JSON)
        self.assertEqual(key1, "a__b__c.json")

        key2 = db._create_path_key("////a/b/c_d", ViewType.JSON)
        self.assertEqual(key2, "a__b__c_d.json")

    def test_validation(self):
        # Default DB with no paths
        try:
            Database.create_in_memory(paths=[])
        except ValueError as v:
            self.assertEqual(str(v), "Database must have at least one path")

        tmp_files = self.get_temp_files(2)
        # Non Default with missing save path
        try:
            _ = Database(DBType.ON_DISK, "TEST", paths=tmp_files, created="abc", updated="xyz", save_path=None)
        except ValueError as v1:
            self.assertEqual(str(v1), "Database is missing a valid save path")

        # Non Default db with invalid paths
        try:
            _ = Database(DBType.ON_DISK, "TEST", paths=['a', 'b'], created="abc", updated="xyz",
                         save_path=tempfile.tempdir)
        except ValueError as v2:
            self.assertEqual(str(v2), "Database path 'a' is is not a valid location")

    @staticmethod
    def get_temp_files(count) -> list:
        files = []
        for i in range(count):
            tmp = Path(tempfile.NamedTemporaryFile().name)
            tmp.touch()
            files.append(tmp)
        return files
