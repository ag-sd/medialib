import tempfile
import unittest

from app.collection import props
from app.collection.ds import Collection, Properties, CorruptedCollectionError
from tests.collection import test_utils


class TestProperties(unittest.TestCase):

    def test_write_db_new_ini_file(self):
        with tempfile.TemporaryDirectory() as db_path:
            db = Collection.create_in_memory(paths=test_utils.get_temp_files(2), save_path=db_path)
            Properties.write(db)

            p_db = Properties.as_collection(db_path)

            self.assertEqual(db.name, p_db.name)
            self.assertEqual(db.save_path, p_db.save_path)
            self.assertEqual(db.paths, p_db.paths)
            self.assertEqual(db.type, p_db.type)
            self.assertEqual(db.created, p_db.created)
            self.assertEqual(db.updated, p_db.updated)

    def test_write_db_existing_ini_file(self):
        with tempfile.TemporaryDirectory() as db_path:
            db = Collection.create_in_memory(paths=test_utils.get_temp_files(2), save_path=db_path)
            Properties.write(db)

            Properties.write(db)

    def test_read_to_collection(self):
        with tempfile.TemporaryDirectory() as db_path:
            db = Collection.create_in_memory(paths=test_utils.get_temp_files(2), save_path=db_path)
            Properties.write(db)

            p_db = Properties.as_collection(db_path)

            self.assertEqual(db.name, p_db.name)
            self.assertEqual(db.save_path, p_db.save_path)
            self.assertEqual(db.paths, p_db.paths)
            self.assertEqual(db.type, p_db.type)
            self.assertEqual(db.created, p_db.created)
            self.assertEqual(db.updated, p_db.updated)

    def test_read_to_dict(self):
        with tempfile.TemporaryDirectory() as db_path:
            db = Collection.create_in_memory(paths=test_utils.get_temp_files(2), save_path=db_path)
            Properties.write(db)

            p_db = Properties.as_dictionary(db_path)

            self.assertEqual(p_db, {
                props.DB_NAME: db.name,
                props.DB_SAVE_PATH: db.save_path,
                props.DB_PATHS: db.paths,
                props.DB_TYPE: db.type,
                props.DB_CREATED: db.created,
                props.DB_UPDATED: db.updated,
                props.DB_TAGS: []
            })

    def test_load_invalid_collection(self):
        with tempfile.TemporaryDirectory() as db_path:
            try:
                Properties.as_collection(db_path)
                self.fail("No collection exists at this path, thus the loader should raise an error")
            except CorruptedCollectionError as e:
                self.assertEqual(str(e), "This collection is corrupt and cannot be opened. "
                                         "See logs for more details")
                pass


