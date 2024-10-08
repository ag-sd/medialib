import tempfile
import unittest

from app.presentation.models import ViewItem, ModelData, BaseViewBuilder, FileSystemModelBuilder, GroupTreeItemBuilder
from tests.collection import test_utils
from pathlib import Path


class TestViewItem(unittest.TestCase):

    def test_display_text(self):
        item1 = ViewItem(icon=None, text="Foo", parent=None, data={}, file_data=None)
        item2 = ViewItem(icon=None, text="Bar", parent=None, data={}, file_data=None)
        item3 = ViewItem(icon=None, text="Baz", parent=None, data={}, file_data=None)

        self.assertEqual("Foo  (0 items)", item1.display_text)

        item1.add_child(item2)
        self.assertEqual("Foo  (1 item)", item1.display_text)

        item1.add_child(item3)
        self.assertEqual("Foo  (2 items)", item1.display_text)

    def test_children(self):
        item1 = ViewItem(icon=None, text="Foo", parent=None, data={}, file_data=None)
        item2 = ViewItem(icon=None, text="Bar", parent=None, data={}, file_data=None)
        item3 = ViewItem(icon=None, text="Baz", parent=None, data={}, file_data=None)

        item1.add_child(item2)
        item1.add_child(item3)

        self.assertEqual(2, item1.row_count)
        self.assertEqual(item1, item2.parent)
        self.assertEqual(item1, item3.parent)
        self.assertEqual(0, item2.row)
        self.assertEqual(1, item3.row)

        self.assertEqual(2, len(item1.children))

    def test_leaf_item(self):
        item1 = ViewItem(icon=None, text="Foo", parent=None, data={}, file_data=None)
        item2 = ViewItem(icon=None, text="Bar", parent=None, data={}, file_data=None)
        item3 = ViewItem(icon=None, text="Baz", parent=None, data={}, file_data=None)

        item1.add_child(item2)
        item1.add_child(item3)

        self.assertTrue(item2.is_leaf_item)
        self.assertTrue(item3.is_leaf_item)
        self.assertFalse(item1.is_leaf_item)


class TestViewManagerPreprocessor(unittest.TestCase):

    def setUp(self):
        self._base_view = BaseViewBuilder()

    def test_buildBaseView(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            model_data = []
            for path in db.paths:
                for _path, entry in db.data([path]).items():
                    model_data.append(ModelData(data=entry, path=_path))

            self._base_view.build(model_data=model_data)
            self.assertListEqual(test_paths, self._base_view.collection_paths)
            self.assertEqual(6, len(self._base_view.data))
            self.assertTrue(self._base_view.is_file_ops_available)

    def test_buildBaseView_empty(self):
        self._base_view.build(model_data=[])
        self.assertListEqual([], self._base_view.collection_paths)
        self.assertEqual(0, len(self._base_view.data))
        self.assertFalse(self._base_view.is_file_ops_available)


class TestFileSystemModelBuilder(unittest.TestCase):

    def setUp(self):
        self._builder = FileSystemModelBuilder()

    def _test_nodes(self, path_components, root_node, expected_count):
        part = path_components.pop(0)
        self.assertEqual(part, root_node.text)
        if len(path_components) > 0:
            self._test_nodes(path_components, root_node.children[0], expected_count)
        else:
            self.assertEqual(expected_count, root_node.row_count)

    def test_buildFs(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            model_data = []
            for path in db.paths:
                for _path, entry in db.data([path]).items():
                    model_data.append(ModelData(data=entry, path=_path))
            base_view = BaseViewBuilder()
            base_view.build(model_data=model_data)
            result = self._builder.build(view_items=base_view.data)
            self._test_nodes(list(Path(test_paths[0]).parts), result, 2)


class TestGroupTreeItemBuilder(unittest.TestCase):

    def setUp(self):
        self._builder = GroupTreeItemBuilder()

    def test_buildGTOneLevel(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            model_data = []
            for path in db.paths:
                for _path, entry in db.data([path]).items():
                    model_data.append(ModelData(data=entry, path=_path))
            base_view = BaseViewBuilder()
            base_view.build(model_data=model_data)
            result = self._builder.build(view_items=base_view.data, group_by=["File:FileType"])
            expected_groups = {"MP3", "OGG", "GIF", "JPEG", "PNG", "TIFF"}
            for i in range(0, result.row_count):
                group = result.children[i].text
                self.assertTrue(group in expected_groups)
                expected_groups.remove(group)
            self.assertEqual(0, len(expected_groups))

    def test_group_unknown(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            model_data = []
            for path in db.paths:
                for _path, entry in db.data([path]).items():
                    model_data.append(ModelData(data=entry, path=_path))
            base_view = BaseViewBuilder()
            base_view.build(model_data=model_data)
            result = self._builder.build(view_items=base_view.data, group_by=["File:FileTypeXCX"])
            expected_groups = {"N/A"}
            for i in range(0, result.row_count):
                group = result.children[i].text
                self.assertTrue(group in expected_groups)
                expected_groups.remove(group)
            self.assertEqual(0, len(expected_groups))

# class JsonViewTests(unittest.TestCase):
#
#     def setUp(self):
#         self._json_view = JsonView(parent=None)
#
#     def test_lazy_loading_lists(self):
#         with tempfile.TemporaryDirectory() as db_path:
#             test_paths = test_utils.get_test_paths()
#             db = test_utils.create_test_media_db(db_path, test_paths)
#             model_data = []
#             for path in db.paths:
#                 for _path, entry in db.data([path]).items():
#                     model_data.append(ModelData(data=entry, path=_path))
#
#             self._json_view.set_model(model_data, db.tags)
#             self.assertEqual(self._json_view.model().rowCount(), 2)
#
#             audio_path = self._json_view.model().index(0, 0)
#             self.assertTrue(self._json_view.model().hasChildren(audio_path))
#             self.assertTrue(self._json_view.model().canFetchMore(audio_path))
#             self.assertEqual(self._json_view.model().rowCount(audio_path), 0)  # Item has not been expanded yet
#             self._json_view.model().fetchMore(audio_path)
#             self.assertEqual(self._json_view.model().rowCount(audio_path), 4)  # Item has now been expanded
#
#     def test_lazy_loading_dicts(self):
#         test_dict = {
#             "X": "Y",
#             "A": "B",
#             props.FIELD_FILE_NAME: "xx.txt.abc"
#         }
#         model_data = [ModelData(data=test_dict, path="XXYY")]
#
#         self._json_view.set_model(model_data, ["X", "Y", props.FIELD_FILE_NAME])
#         self.assertEqual(self._json_view.model().rowCount(), 1)
#
#         first_item = self._json_view.model().index(0, 0)
#         self.assertTrue(self._json_view.model().hasChildren(first_item))
#         self.assertTrue(self._json_view.model().canFetchMore(first_item))
#         self.assertEqual(self._json_view.model().rowCount(first_item), 0)  # Item has not been expanded yet
#         self._json_view.model().fetchMore(first_item)
#         # A gets filtered out as it's not in the fields list, so the response only has 2 items
#         self.assertEqual(self._json_view.model().rowCount(first_item), 2)
#
#     def test_lazy_loading_str(self):
#         model_data = [ModelData(data="HELLO WORLD", path="XXYY")]
#
#         self._json_view.set_model(model_data, ["X", "Y", props.FIELD_FILE_NAME])
#
#         self.assertEqual(self._json_view.model().rowCount(), 1)
#
#     def test_no_data(self):
#         model_data = []
#         self._json_view.set_model(model_data, ["X", "A", props.FIELD_FILE_NAME])
#         self.assertEqual(self._json_view.model().rowCount(), 0)
#         self.assertEqual(self._json_view.model().columnCount(), 1)
#         self.assertEqual(self._json_view.model().headerData(0, Qt.Orientation.Horizontal),
#                          views._NO_DATA_MESSAGE)
#
#     # @unittest.skip("Run this test only if you want to actually bring up the UI")
#     def test_start_as_gui(self):
#         test_file = Path(__file__).parent / "resources" / "sample_users.json"
#         test_data = json.loads(test_file.read_text("utf-8"))
#         self._json_view.set_model([ModelData(test_data, str(test_file))], None)
#         # test_utils.launch_widget(self._json_view)


# class FileSystemViewTests(unittest.TestCase):
#     def setUp(self):
#         self._fs_view = FileSystemView(parent=None)
#
#     def test_lazy_loading(self):
#         with tempfile.TemporaryDirectory() as db_path:
#             test_paths = test_utils.get_test_paths()
#             db = test_utils.create_test_media_db(db_path, test_paths)
#             model_data = []
#             for path in db.paths:
#                 for _path, entry in db.data([path]).items():
#                     model_data.append(ModelData(data=entry, path=_path))
#
#             self._fs_view.set_model(model_data, db.tags)
#             self.assertEqual(self._fs_view.model().rowCount(), 2)
#             audio_path = self._fs_view.model().index(0, 0)
#             self.assertTrue(self._fs_view.model().hasChildren(audio_path))
#             self.assertTrue(self._fs_view.model().canFetchMore(audio_path))
#             self.assertEqual(self._fs_view.model().rowCount(audio_path), 0)  # Item has not been expanded yet
#             self._fs_view.model().fetchMore(audio_path)
#             self.assertEqual(self._fs_view.model().rowCount(audio_path), 4)  # Item has now been expanded
#
#     def test_lazy_loading_deeper_hierarchy(self):
#         with tempfile.TemporaryDirectory() as db_path:
#             test_paths = test_utils.get_test_root()
#             db = test_utils.create_test_media_db(db_path, test_paths)
#             model_data = []
#             for path in db.paths:
#                 for _path, entry in db.data([path]).items():
#                     model_data.append(ModelData(data=entry, path=_path))
#
#             self._fs_view.set_model(model_data, db.tags)
#             self.assertEqual(self._fs_view.model().rowCount(), 1)
#             root_path = self._fs_view.model().index(0, 0)
#             self.assertTrue(self._fs_view.model().hasChildren(root_path))
#             self.assertTrue(self._fs_view.model().canFetchMore(root_path))
#             self.assertEqual(self._fs_view.model().rowCount(root_path), 0)  # Item has not been expanded yet
#             self._fs_view.model().fetchMore(root_path)
#             self.assertEqual(self._fs_view.model().rowCount(root_path), 2)  # Item has now been expanded
#
#     def test_no_data(self):
#         model_data = []
#         self._fs_view.set_model(model_data, ["X", "A", props.FIELD_FILE_NAME])
#         self.assertEqual(self._fs_view.model().rowCount(), 0)
#         self.assertEqual(self._fs_view.model().columnCount(), 1)
#         self.assertEqual(self._fs_view.model().headerData(0, Qt.Orientation.Horizontal),
#                          views._NO_DATA_MESSAGE)
#
#
# class TableViewTests(unittest.TestCase):
#     def setUp(self):
#         self._table_view = TableView(parent=None)
#
#     def test_load_database(self):
#         with tempfile.TemporaryDirectory() as db_path:
#             test_paths = test_utils.get_test_paths()
#             db = test_utils.create_test_media_db(db_path, test_paths)
#             model_data = []
#             for path in db.paths:
#                 for _path, entry in db.data([path]).items():
#                     model_data.append(ModelData(data=entry, path=_path))
#
#             self._table_view.set_model(model_data, db.tags)
#             self.assertEqual(self._table_view.model().rowCount(), 6)
#             self.assertEqual(self._table_view.model().columnCount(), len(db.tags))
#
#     def test_columnar_view(self):
#         test_dict = {
#             "X": "Y",
#             "A": "B",
#             props.FIELD_FILE_NAME: "xx.txt.abc"
#         }
#         model_data = [ModelData(data=[test_dict], path="XXYY")]
#         self._table_view.set_model(model_data, ["X", "A", props.FIELD_FILE_NAME])
#         # test_utils.launch_widget(self._table_view)
#         self.assertEqual(self._table_view.model().rowCount(), 3)
#         self.assertEqual(self._table_view.model().columnCount(), 1)
#
#     def test_no_data(self):
#         model_data = []
#         self._table_view.set_model(model_data, ["X", "A", props.FIELD_FILE_NAME])
#         self.assertEqual(self._table_view.model().rowCount(), 0)
#         self.assertEqual(self._table_view.model().columnCount(), 1)
#         self.assertEqual(self._table_view.model().headerData(0, Qt.Orientation.Horizontal),
#                          views._NO_DATA_MESSAGE)
