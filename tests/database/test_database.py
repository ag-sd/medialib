import unittest

from app.database.database import Database
from views import ViewType


class TestDatabase(unittest.TestCase):

    def test_create_default_paths_blank(self):
        try:
            Database.create_default(paths=[])
        except ValueError as v:
            self.assertTrue(str(v) == "Paths cannot be empty")

    def test_create_default_database(self):
        db = Database.create_default(paths=["a", "b", "c"])
        self.assertTrue(db.is_default)
        self.assertIsNone(db.path)
        self.assertEqual(db.name, Database.DEFAULT_NAME)
        self.assertCountEqual(db.paths, ["a", "b", "c"])
        self.assertEqual(db.default_view.name, ViewType.JSON.name)
        self.assertEqual(len(db.views), 5)

    def test_open_database(self):
        try:
            Database.open_db("xyz")
        except NotImplementedError as e:
            self.assertTrue(str(e) == "Not Implemented")

    def test_add_paths_dupe(self):
        db = Database.create_default(paths=["a", "b", "c"])
        self.assertCountEqual(db.paths, ["a", "b", "c"])
        db.add_paths(["c", "d"])

        self.assertCountEqual(db.paths, ["a", "b", "c", "d"])

    def test_key_creation(self):
        # Key = "//a/b/c"
        db = Database.create_default(paths=[1, 2, 3])

        key1 = db._create_path_key("//a/b/c", ViewType.JSON)
        self.assertEqual(key1, "a_b_c.json")

        key2 = db._create_path_key("////a/b/c_d", ViewType.JSON)
        self.assertEqual(key2, "a_b_c_d.json")

    # def test_cache_lookup_hit(self):
    #     db = Database.create_default(paths=["//foo/ba_r.jpeg"])
    #     db._path_cache["foo_bar.jpeg.json"] = "baz"
    #
    #     data = db.get_path_data("//foo/ba_r.jpeg", view=ViewType.JSON)
    #     self.assertTrue(data, "baz")


