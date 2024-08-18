import tempfile
import unittest

from app.collection import props
from app.collection.ds import Collection, Properties, CollectionNotFoundError
from app.collection.props import DBType
from tests.collection import test_utils


class TestCollection(unittest.TestCase):

    def test_create_default_paths_blank(self):
        try:
            Collection.create_in_memory(paths=[])
        except ValueError as v:
            self.assertEqual(str(v), "Collection must have at least one path")

    def test_create_default_collection(self):
        tmp_files = test_utils.get_temp_files(2)
        db = Collection.create_in_memory(paths=tmp_files)
        self.assertEqual(db.type, DBType.IN_MEMORY)
        self.assertIsNone(db.save_path)
        self.assertEqual(db.name, "default-collection")
        self.assertCountEqual(db.paths, tmp_files)

    def test_open_collection(self):
        with tempfile.TemporaryDirectory() as db_path:
            db = Collection.create_in_memory(paths=test_utils.get_temp_files(2), save_path=db_path)
            Properties.write(db)
            p_db = Collection.open_db(db_path)

            self.assertEqual(db.name, p_db.name)
            self.assertEqual(db.save_path, p_db.save_path)
            self.assertEqual(db.paths, p_db.paths)
            self.assertEqual(db.type, p_db.type)
            self.assertEqual(db.created, p_db.created)
            self.assertEqual(db.updated, p_db.updated)

    def test_save_collection(self):
        with tempfile.TemporaryDirectory() as db_path:
            db = test_utils.create_test_media_db(db_path)
            db.save()

            p_db = Collection.open_db(db.save_path)
            self.assertEqual(db.name, p_db.name)
            self.assertEqual(db.save_path, p_db.save_path)
            self.assertEqual(db.paths, p_db.paths)
            self.assertEqual(db.type, p_db.type)
            self.assertEqual(db.created, p_db.created)
            self.assertEqual(db.updated, p_db.updated)

    def test_add_paths_dupe(self):
        tmp_files = test_utils.get_temp_files(3)
        db = Collection.create_in_memory(paths=tmp_files[:2])
        self.assertCountEqual(db.paths, tmp_files[:2])
        db.add_paths(tmp_files[2:])

        self.assertCountEqual(db.paths, tmp_files)

    def test_key_creation(self):
        # Key = "//a/b/c"
        tmp_files = test_utils.get_temp_files(2)
        db = Collection.create_in_memory(paths=tmp_files)

        key1 = db._create_path_key("//a/b/c")
        self.assertEqual(key1, "a__b__c.json")

        key2 = db._create_path_key("////a/b/c_d")
        self.assertEqual(key2, "a__b__c_d.json")

    def test_validation(self):
        # Default DB with no paths
        try:
            Collection.create_in_memory(paths=[])
        except ValueError as v:
            self.assertEqual(str(v), "Collection must have at least one path")

        tmp_files = test_utils.get_temp_files(2)
        # Non Default with missing save path
        try:
            _ = Collection(DBType.ON_DISK, "TEST", paths=tmp_files, created="abc", updated="xyz", save_path=None)
        except ValueError as v1:
            self.assertEqual(str(v1), "Collection is missing a valid save path")

        # Non Default db with invalid paths
        try:
            _ = Collection(DBType.ON_DISK, "TEST", paths=['a', 'b'], created="abc", updated="xyz",
                           save_path=tempfile.tempdir)
        except ValueError as v2:
            self.assertEqual(str(v2), "Collection path 'a' is is not a valid location")

    def test_tags_lazy_get(self):
        tmp_files = test_utils.get_temp_files(2)
        db = Collection.create_in_memory(paths=tmp_files)
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

    def test_collection_not_found(self):
        try:
            _ = Collection.open_db("foo/bar")
            self.fail("This should throw an error")
        except CollectionNotFoundError:
            pass

    def test_collection_modification(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths[:1])
            self.assertFalse(db.is_modified)
            db.add_paths(test_paths[1:])
            self.assertTrue(db.is_modified)
            db.save()
            self.assertFalse(db.is_modified)

    def test_invalid_db_path(self):
        with tempfile.TemporaryDirectory() as db_path:
            paths = test_utils.get_temp_files(2)
            db = Collection.create_in_memory(paths[:1], save_path=db_path)
            try:
                db.data(paths[1])
                self.fail("Request should fail as this path does not exist in the collection")
            except ValueError:
                pass

    def test_db_data_fetch_from_disk(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths[:1])
            db.save()
            db.clear_cache()
            _ = db.data(test_paths[0])

    def test_db_data_new_path_added(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths[:1])
            db.save()
            db.add_paths(test_paths[1:])
            _ = db.data(test_paths[1])

    def test_db_data_path_non_existent(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths[:1])
            ne_path = f"{test_paths[0]}__"
            db.add_paths([ne_path])
            try:
                db.data(ne_path)
            except ValueError:
                pass

    def test_db_empty_dir(self):
        with tempfile.TemporaryDirectory() as db_path:
            with tempfile.TemporaryDirectory() as empty_path:
                db = test_utils.create_test_media_db(db_path, [empty_path])
                data = db.data(empty_path)
                self.assertEqual(data, [])

    def test_save_db_invalid_save_path(self):
        test_paths = test_utils.get_test_paths()
        db = test_utils.create_test_media_db("/1/2/3", test_paths[:1])
        try:
            db.save()
            self.fail("System cannot create a dir at the supplied save_path")
        except FileExistsError:
            pass
        except OSError:
            pass

    def test_save_db_no_path(self):
        test_paths = test_utils.get_test_paths()
        db = test_utils.create_test_media_db(None, test_paths[:1])
        try:
            db.save()
            self.fail("System cannot create a dir at the supplied save_path")
        except ValueError:
            pass

    def test_reload_in_memory(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths[:1])
            db.reload()

    def test_reload_saved(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths[:1])
            db.save()
            db.reload()

    def test_save_no_name(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths[:1])
            try:
                db.set_name("")
                self.fail("Cannot set this name for the collection")
            except ValueError:
                pass

            try:
                db.set_name(props.DB_DEFAULT_NAME)
                self.fail("Cannot set this name for the collection")
            except ValueError:
                pass

            db.set_name("Foo")
