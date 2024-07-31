import tempfile
import unittest
from pathlib import Path

from app.database.ds import Database, Properties
from app.database.props import DBType
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
        with tempfile.TemporaryDirectory() as db_path:
            db = Database.create_in_memory(paths=self.get_temp_files(2), save_path=db_path)
            Properties.write(db)
            p_db = Database.open_db(db_path)

            self.assertEqual(db.name, p_db.name)
            self.assertEqual(db.save_path, p_db.save_path)
            self.assertEqual(db.paths, p_db.paths)
            self.assertEqual(db.type, p_db.type)
            self.assertEqual(db.created, p_db.created)
            self.assertEqual(db.updated, p_db.updated)

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

        key1 = db._create_path_key("//a/b/c")
        self.assertEqual(key1, "a__b__c.json")

        key2 = db._create_path_key("////a/b/c_d")
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

    def test_tags_lazy_get(self):
        tmp_files = self.get_temp_files(2)
        db = Database.create_in_memory(paths=tmp_files)
        self.assertEqual(db._tags, [])
        db.data(tmp_files[0])
        self.assertEqual(db.tags,
                         ['SourceFile',
                          'ExifTool:ExifToolVersion',
                          'ExifTool:Error',
                          'System:FileName',
                          'System:Directory',
                          'System:FileSize',
                          'System:FileModifyDate',
                          'System:FileAccessDate',
                          'System:FileInodeChangeDate',
                          'System:FilePermissions']
                         )

    @staticmethod
    def get_temp_files(count) -> list:
        files = []
        for i in range(count):
            tmp = Path(tempfile.NamedTemporaryFile().name)
            tmp.touch()
            files.append(str(tmp))
        return files