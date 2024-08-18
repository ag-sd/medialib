import json
import tempfile
import unittest
from pathlib import Path

from PyQt6.QtCore import Qt

from app import views
from app.database import props
from app.views import JsonView, ModelData, TableView
from tests.database import test_utils


class JsonViewTests(unittest.TestCase):

    def setUp(self):
        self._json_view = JsonView(parent=None)

    def test_lazy_loading_lists(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            model_data = []
            for path in db.paths:
                model_data.append(ModelData(data=db.data(path), path=path))

            self._json_view.set_model(model_data, db.tags)
            self.assertEqual(self._json_view.model().rowCount(), 2)

            audio_path = self._json_view.model().index(0, 0)
            self.assertTrue(self._json_view.model().hasChildren(audio_path))
            self.assertTrue(self._json_view.model().canFetchMore(audio_path))
            self.assertEqual(self._json_view.model().rowCount(audio_path), 0)  # Item has not been expanded yet
            self._json_view.model().fetchMore(audio_path)
            self.assertEqual(self._json_view.model().rowCount(audio_path), 4)  # Item has now been expanded

    def test_lazy_loading_dicts(self):
        test_dict = {
            "X": "Y",
            "A": "B",
            props.FIELD_FILE_NAME: "xx.txt.abc"
        }
        model_data = [ModelData(data=test_dict, path="XXYY")]

        self._json_view.set_model(model_data, ["X", "Y", props.FIELD_FILE_NAME])
        self.assertEqual(self._json_view.model().rowCount(), 1)

        first_item = self._json_view.model().index(0, 0)
        self.assertTrue(self._json_view.model().hasChildren(first_item))
        self.assertTrue(self._json_view.model().canFetchMore(first_item))
        self.assertEqual(self._json_view.model().rowCount(first_item), 0)  # Item has not been expanded yet
        self._json_view.model().fetchMore(first_item)
        # A gets filtered out as it's not in the fields list, so the response only has 2 items
        self.assertEqual(self._json_view.model().rowCount(first_item), 2)

    def test_lazy_loading_str(self):
        model_data = [ModelData(data="HELLO WORLD", path="XXYY")]

        self._json_view.set_model(model_data, ["X", "Y", props.FIELD_FILE_NAME])

        self.assertEqual(self._json_view.model().rowCount(), 1)

    def test_no_data(self):
        model_data = []
        self._json_view.set_model(model_data, ["X", "A", props.FIELD_FILE_NAME])
        self.assertEqual(self._json_view.model().rowCount(), 0)
        self.assertEqual(self._json_view.model().columnCount(), 1)
        self.assertEqual(self._json_view.model().headerData(0, Qt.Orientation.Horizontal),
                         views._NO_DATA_MESSAGE)

    @unittest.skip("Run this test only if you want to actually bring up the UI")
    def test_start_as_gui(self):
        test_file = Path(__file__).parent / "resources" / "sample_users.json"
        test_data = json.loads(test_file.read_text("utf-8"))
        self._json_view.set_model([ModelData(test_data, str(test_file))], None)
        test_utils.launch_widget(self._json_view)


class TableViewTests(unittest.TestCase):
    def setUp(self):
        self._table_view = TableView(parent=None)

    def test_load_database(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            model_data = []
            for path in db.paths:
                model_data.append(ModelData(data=db.data(path), path=path))

            self._table_view.set_model(model_data, db.tags)
            self.assertEqual(self._table_view.model().rowCount(), 6)
            self.assertEqual(self._table_view.model().columnCount(), len(db.tags))

    def test_columnar_view(self):
        test_dict = {
            "X": "Y",
            "A": "B",
            props.FIELD_FILE_NAME: "xx.txt.abc"
        }
        model_data = [ModelData(data=[test_dict], path="XXYY")]
        self._table_view.set_model(model_data, ["X", "A", props.FIELD_FILE_NAME])
        # test_utils.launch_widget(self._table_view)
        self.assertEqual(self._table_view.model().rowCount(), 3)
        self.assertEqual(self._table_view.model().columnCount(), 1)

    def test_no_data(self):
        model_data = []
        self._table_view.set_model(model_data, ["X", "A", props.FIELD_FILE_NAME])
        self.assertEqual(self._table_view.model().rowCount(), 0)
        self.assertEqual(self._table_view.model().columnCount(), 1)
        self.assertEqual(self._table_view.model().headerData(0, Qt.Orientation.Horizontal),
                         views._NO_DATA_MESSAGE)



