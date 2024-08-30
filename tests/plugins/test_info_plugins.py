import tempfile
import unittest

from PyQt6.QtCore import Qt

from app.collection import props
from app.plugins.info import FileInfoPlugin
from app.views import ModelData
from tests.collection import test_utils


class TestFileInfoPlugin(unittest.TestCase):

    def setUp(self):
        pass
        self.test = 0
        self._info_widget = FileInfoPlugin(None)
        self._property_widget = self._info_widget._property_widget

    def test_create_property_widget(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            db.save()
            fileinfo = db.search(
                '/mnt/dev/medialib/tests/collection/../resources/media/audio/Free_Test_Data_100KB_MP3.mp3', db.paths[0])
            model_data = [ModelData(data=fileinfo.data[0].results, path=fileinfo.data[0].path)]
            self._info_widget.handle_file_click(model_data, fileinfo.columns)
            self.assertEqual(13, self._property_widget.invisibleRootItem().childCount())
            self.assertEqual(0, self._property_widget.invisibleRootItem().child(0).childCount())
            self.assertEqual(7, self._property_widget.invisibleRootItem().child(2).childCount())
            self.assertEqual(props.DB_TAG_GROUP_SYSTEM, self._property_widget.invisibleRootItem().child(2).text(0))

    def test_clear(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            db.save()
            fileinfo = db.search(
                '/mnt/dev/medialib/tests/collection/../resources/media/audio/Free_Test_Data_100KB_MP3.mp3', db.paths[0])
            model_data = [ModelData(data=fileinfo.data[0].results, path=fileinfo.data[0].path)]
            self._info_widget.handle_file_click(model_data, fileinfo.columns)
            self.assertEqual(13, self._property_widget.invisibleRootItem().childCount())
            self.assertEqual(0, self._property_widget.invisibleRootItem().child(0).childCount())
            self.assertTrue(self._property_widget.invisibleRootItem().child(2).childCount() > 0)

            # Actual Test
            self._property_widget.clear()
            self.assertEqual(11, self._property_widget.invisibleRootItem().childCount())
            self.assertEqual(0, self._property_widget.invisibleRootItem().child(0).childCount())
            self.assertEqual(0, self._property_widget.invisibleRootItem().child(2).childCount())

    def test_drag_items(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            db.save()
            fileinfo = db.search(
                '/mnt/dev/medialib/tests/collection/../resources/media/audio/Free_Test_Data_100KB_MP3.mp3', db.paths[0])
            # Setup properties
            model_data = [ModelData(data=fileinfo.data[0].results, path=fileinfo.data[0].path)]
            self._info_widget.handle_file_click(model_data, fileinfo.columns)
            self.assertEqual(13, self._property_widget.invisibleRootItem().childCount())
            root_child_count = self._property_widget.invisibleRootItem().childCount()
            system_added_props = self._property_widget._root_prop_count
            self.assertEqual(0, self._property_widget.invisibleRootItem().child(0).childCount())
            self.assertTrue(self._property_widget.invisibleRootItem().child(2).childCount() > 0)
            test_child_count = self._property_widget.invisibleRootItem().child(2).childCount()
            # Move the child up
            child_moved = self._property_widget.invisibleRootItem().child(2).takeChild(0)
            self._property_widget.invisibleRootItem().addChild(child_moved)
            self.assertEqual(test_child_count - 1, self._property_widget.invisibleRootItem().child(2).childCount())
            self.assertEqual(root_child_count + 1, self._property_widget.invisibleRootItem().childCount())

            self._property_widget.clear()
            # Moved child was preserved
            self.assertEqual(root_child_count + 1 - system_added_props, self._property_widget.invisibleRootItem().childCount())
            self.assertEqual(0, self._property_widget.invisibleRootItem().child(0).childCount())
            self.assertEqual(0, self._property_widget.invisibleRootItem().child(2).childCount())

            # Actual Test
            model_data = [ModelData(data=fileinfo.data[0].results, path=fileinfo.data[0].path)]
            self._info_widget.handle_file_click(model_data, fileinfo.columns)
            # Keys have been reused and no-rebuild has taken palce
            self.assertEqual(test_child_count - 1, self._property_widget.invisibleRootItem().child(2).childCount())
            self.assertEqual(root_child_count + 1, self._property_widget.invisibleRootItem().childCount())

    def test_auto_resize(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            db.save()
            fileinfo = db.search(
                '/mnt/dev/medialib/tests/collection/../resources/media/audio/Free_Test_Data_100KB_MP3.mp3', db.paths[0])
            # Setup properties
            model_data = [ModelData(data=fileinfo.data[0].results, path=fileinfo.data[0].path)]
            self._info_widget.handle_file_click(model_data, fileinfo.columns)
            # Do Test
            width_0 = self._property_widget.columnWidth(0)
            self._property_widget.invisibleRootItem().child(3).setExpanded(True)
            self.assertNotEqual(self._property_widget.columnWidth(0), width_0)

    def test_type_check(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            db.save()
            fileinfo = db.search(
                '/mnt/dev/medialib/tests/collection/../resources/media/audio/Free_Test_Data_100KB_MP3.mp3', db.paths[0])
            # Setup properties
            test_property = "__MY_TEST_PROPERTY"
            fileinfo.data[0].results[0][test_property] = 0
            fileinfo.columns.append(test_property)
            model_data = [ModelData(data=fileinfo.data[0].results, path=fileinfo.data[0].path)]
            # Do Test
            self._info_widget.handle_file_click(model_data, fileinfo.columns)
            self.assertEqual(14, self._property_widget.invisibleRootItem().childCount())
            # Get test prop
            _my_prop = self._property_widget.findItems(test_property,
                                                       Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchCaseSensitive)
            self.assertEqual(1, len(_my_prop))
            self.assertEqual("0 (int)", _my_prop[0].text(1))

    def test_statustip(self):
        self.assertEqual(self._info_widget.statustip, "Provide detailed information about the selected file")

    def test_icon(self):
        self.assertEqual(self._info_widget.icon.name(), "dialog-information")

    def test_shortcut(self):
        self.assertEqual(self._info_widget.shortcut, "F5")

    def test_dockwidget_area(self):
        self.assertEqual(self._info_widget.dockwidget_area, Qt.DockWidgetArea.BottomDockWidgetArea)

    def test_name(self):
        self.assertEqual(self._info_widget.name, "File Information")

    def test_is_visible_on_start(self):
        self.assertEqual(self._info_widget.is_visible_on_start, True)
