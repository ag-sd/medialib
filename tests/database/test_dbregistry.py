import tempfile
import unittest
from pathlib import Path

from app.database.ds import DatabaseRegistry, Database


class TestDbRegistry(unittest.TestCase):

    def test_add_db(self):
        reg_mock = self.create_mock_registry()
        tmp_files = self.get_temp_files(2)
        db = Database.create_in_memory(paths=tmp_files)
        reg_mock.add(db)
        self.assertEqual(reg_mock.databases, [db.name])
        reg_mock.commit()

    def test_add_existing(self):
        reg_mock = self.create_mock_registry()
        tmp_files = self.get_temp_files(2)
        db = Database.create_in_memory(paths=tmp_files)
        reg_mock.add(db)
        self.assertEqual(reg_mock.databases, [db.name])

        try:
            reg_mock.add(db)
            self.fail("This should fail as you cannot add an exisitng db")
        except ValueError as v:
            self.assertEqual(str(v), "Database exists in registry. "
                                     "To update an existing database use the update method")

    def test_get_non_existing(self):
        reg_mock = self.create_mock_registry()

        try:
            reg_mock.get("test")
            self.fail("This should fail as this db does not exist in the registry")
        except ValueError as v:
            self.assertEqual(str(v), "test was not found in this database")

    def test_get_existing(self):
        reg_mock = self.create_mock_registry()
        tmp_files = self.get_temp_files(2)
        db = Database.create_in_memory(paths=tmp_files)
        reg_mock.add(db)

        reg_db = reg_mock.get(db.name)
        self.assertEqual(db.name, reg_db.name)
        self.assertEqual(db.save_path, reg_db.save_path)
        self.assertEqual(db.paths, reg_db.paths)
        self.assertEqual(db.type, reg_db.type)
        self.assertIsNone(reg_db.updated)
        self.assertIsNotNone(reg_db.created)

    def test_update_non_existing(self):
        reg_mock = self.create_mock_registry()
        tmp_files = self.get_temp_files(2)
        db = Database.create_in_memory(paths=tmp_files)

        try:
            reg_mock.update(db)
            self.fail("This should fail as this db does not exist in the registry")
        except ValueError as v:
            self.assertEqual(str(v), "default-db was not found in this database")

    def test_update_existing(self):
        reg_mock = self.create_mock_registry()
        tmp_files = self.get_temp_files(3)
        db = Database.create_in_memory(paths=tmp_files[:2])
        reg_mock.add(db)

        db.add_paths(tmp_files[2:])
        reg_mock.update(db)

        reg_db = reg_mock.get(db.name)
        self.assertEqual(db.name, reg_db.name)
        self.assertEqual(db.save_path, reg_db.save_path)
        self.assertEqual(db.paths, reg_db.paths)
        self.assertEqual(db.type, reg_db.type)
        self.assertIsNotNone(reg_db.created)
        self.assertIsNotNone(reg_db.updated)

    def test_delete_non_existing(self):
        reg_mock = self.create_mock_registry()
        self.assertFalse(reg_mock.delete("test"))

    def test_delete_existing(self):
        reg_mock = self.create_mock_registry()
        tmp_files = self.get_temp_files(2)
        db = Database.create_in_memory(paths=tmp_files)
        reg_mock.add(db)
        self.assertTrue(reg_mock.delete(db.name))

    def test_commit(self):
        reg_mock = self.create_mock_registry()
        tmp_files = self.get_temp_files(2)
        db = Database.create_in_memory(paths=tmp_files)
        reg_mock.add(db)
        reg_mock.commit()

        new_mock = DatabaseRegistry(reg_mock._registry_file)
        reg_db = new_mock.get(db.name)
        self.assertEqual(db.name, reg_db.name)
        self.assertEqual(db.save_path, reg_db.save_path)
        self.assertEqual(db.paths, reg_db.paths)
        self.assertEqual(db.type, reg_db.type)
        self.assertIsNone(reg_db.updated)
        self.assertIsNotNone(reg_db.created)

    @staticmethod
    def create_mock_registry() -> DatabaseRegistry:
        file = tempfile.NamedTemporaryFile().name
        print(file)
        return DatabaseRegistry(file)

    @staticmethod
    def get_temp_files(count) -> list:
        files = []
        for i in range(count):
            tmp = Path(tempfile.NamedTemporaryFile().name)
            tmp.touch()
            files.append(str(tmp))
        return files
