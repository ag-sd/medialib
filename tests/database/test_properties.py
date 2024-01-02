import tempfile
import unittest
from pathlib import Path

from app.database.ds import Database, Properties, Props


class TestProperties(unittest.TestCase):

    def test_write_db_new_ini_file(self):
        with tempfile.TemporaryDirectory() as db_path:
            db = Database.create_in_memory(paths=TestProperties.get_temp_files(2), save_path=db_path)
            Properties.write(db)

            p_db = Properties.as_database(db_path)

            self.assertEqual(db.name, p_db.name)
            self.assertEqual(db.save_path, p_db.save_path)
            self.assertEqual(db.paths, p_db.paths)
            self.assertEqual(db.type, p_db.type)
            self.assertEqual(db.created, p_db.created)
            self.assertEqual(db.updated, p_db.updated)
            self.assertEqual(db.tags, p_db.tags)

    def test_write_db_existing_ini_file(self):
        with tempfile.TemporaryDirectory() as db_path:
            db = Database.create_in_memory(paths=TestProperties.get_temp_files(2), save_path=db_path)
            Properties.write(db)

            Properties.write(db)

    def test_read_to_database(self):
        with tempfile.TemporaryDirectory() as db_path:
            db = Database.create_in_memory(paths=TestProperties.get_temp_files(2), save_path=db_path)
            Properties.write(db)

            p_db = Properties.as_database(db_path)

            self.assertEqual(db.name, p_db.name)
            self.assertEqual(db.save_path, p_db.save_path)
            self.assertEqual(db.paths, p_db.paths)
            self.assertEqual(db.type, p_db.type)
            self.assertEqual(db.created, p_db.created)
            self.assertEqual(db.updated, p_db.updated)
            self.assertEqual(db.tags, p_db.tags)

    def test_read_to_dict(self):
        with tempfile.TemporaryDirectory() as db_path:
            db = Database.create_in_memory(paths=TestProperties.get_temp_files(2), save_path=db_path)
            Properties.write(db)

            p_db = Properties.as_dictionary(db_path)

            self.assertEqual(p_db, {
                Props.DB_NAME: db.name,
                Props.DB_SAVE_PATH: db.save_path,
                Props.DB_PATHS: db.paths,
                Props.DB_TYPE: db.type,
                Props.DB_CREATED: db.created,
                Props.DB_UPDATED: db.updated,
                Props.DB_TAGS: db.tags
            })

    @staticmethod
    def get_temp_files(count) -> list:
        files = []
        for i in range(count):
            tmp = Path(tempfile.NamedTemporaryFile().name)
            tmp.touch()
            files.append(str(tmp))
        return files
