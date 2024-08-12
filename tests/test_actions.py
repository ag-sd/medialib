import tempfile
import unittest

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QWidget, QWidgetAction

from app import actions
from app.actions import ViewMenu, HelpMenu, MediaLibAction, FileMenu
from app.views import ViewType
from tests.database import test_utils
from tests.database.test_utils import CallbackHandler


class TestActions(unittest.TestCase):

    # https://github.com/jmcgeheeiv/pyqttestexample/blob/master/src/MargaritaMixerTest.py

    def test_create_action_missing_fields(self):
        i1 = actions._create_action(None, "Test1")
        self.assertTrue(i1.text() == "Test1")

    def test_tooltip_and_shortcut(self):
        # If action has tooltip and shortcut, these are set at multiple places
        i2 = actions._create_action(None, "Test2", func=None, shortcut="X", tooltip="TOOLTIP")
        self.assertTrue(i2.toolTip() == "TOOLTIP (X)")
        self.assertTrue(i2.toolTip() == "TOOLTIP (X)")
        self.assertTrue(i2.statusTip() == "TOOLTIP (X)")
        self.assertTrue(i2.shortcut() == "X")

    def test_no_tooltip(self):
        # If no shortcut is set, the tooltip does not show this
        i2 = actions._create_action(None, "Test2", func=None, shortcut=None, tooltip="TOOLTIP")
        self.assertTrue(i2.toolTip() == "TOOLTIP")
        self.assertTrue(i2.toolTip() == "TOOLTIP")
        self.assertTrue(i2.statusTip() == "TOOLTIP")
        self.assertTrue(i2.shortcut().isEmpty())
        self.assertIsInstance(i2, QAction)

    def test_widget_action_creation(self):
        # If a widget is supplied, the action returned is a widget action
        i2 = actions._create_action(None, "Test2", func=None, shortcut=None, tooltip="TOOLTIP",
                                    widget=QWidget())
        self.assertIsInstance(i2, QWidgetAction)


class TestViewMenu(unittest.TestCase):

    def setUp(self):
        self._view_menu = ViewMenu(None)

    def test_init_view(self):
        _actions = list(self._view_menu.actions())
        self.assertTrue(_actions[0].property("view-action"))
        self.assertTrue(_actions[1].property("view-action"))
        self.assertTrue(_actions[2].isSeparator())
        self.assertEqual(_actions[3].text(), "All Fields")
        self.assertEqual(_actions[4].text(), "Preset Views")

        self.assertEqual(len(_actions), 5)

    def test_show_database_image_files(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            # Image File
            db = test_utils.create_test_media_db(db_path, test_paths[:1])
            db.save()
            self._view_menu.show_database(db)
            # Available fields count will be different
            self.assertEqual(len(list(self._view_menu._view_menu_all_fields.actions())), 8)
            # Presets are available
            self.assertEqual(len(list(self._view_menu._view_menu_presets.actions())), 3)

    def test_show_database_audio_files(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            # Audio File
            db = test_utils.create_test_media_db(db_path, test_paths[1:])
            db.save()
            self._view_menu.show_database(db)
            # Available fields count will be different
            self.assertEqual(len(list(self._view_menu._view_menu_all_fields.actions())), 11)
            # Presets are available
            self.assertEqual(len(list(self._view_menu._view_menu_presets.actions())), 3)

    def test_shut_database(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            # Audio File
            db = test_utils.create_test_media_db(db_path, test_paths[1:])
            db.save()
            self._view_menu.show_database(db)
            self._view_menu.shut_database()
            # Available fields count will be zero
            self.assertEqual(len(list(self._view_menu._view_menu_all_fields.actions())), 0)
            # Presets are un-available
            self.assertEqual(len(list(self._view_menu._view_menu_presets.actions())), 0)

    def test_update_views_disable(self):
        self._view_menu.update_available_views([])
        self.assertFalse(self._view_menu.actions()[0].isEnabled())
        self.assertFalse(self._view_menu.actions()[1].isEnabled())

    def test_update_views_enable(self):
        self._view_menu.update_available_views([e.name for e in ViewType])
        self.assertTrue(self._view_menu.actions()[0].isEnabled())
        self.assertTrue(self._view_menu.actions()[1].isEnabled())

    # def test_view_event_field_change(self):
    #     def callback():
    #         print("Hello World")
    #
    #     with tempfile.TemporaryDirectory() as db_path:
    #         test_paths = test_utils.get_test_paths()
    #         # Audio File
    #         db = test_utils.create_test_media_db(db_path, test_paths[1:])
    #         db.save()
    #         self._view_menu.show_database(db)
    #         cb = CallbackHandler(self._view_menu.view_event, expects_callback=True, callback=callback)
    #         self._view_menu._view_menu_all_fields.actions()[0].trigger()
    #         self.assertTrue(cb.callback_handled_correctly)
    #
    #
    #

    def test_view_event_raised(self):
        cb = CallbackHandler(self._view_menu.view_event, expects_callback=True, callback_count=2)
        self._view_menu.actions()[0].trigger()
        self._view_menu.actions()[1].trigger()
        self.assertTrue(cb.callback_handled_correctly)


class TestHelpMenu(unittest.TestCase):

    def setUp(self):
        self._help_menu = HelpMenu(None)

    def test_init_view(self):
        _actions = list(self._help_menu.actions())
        self.assertEqual(_actions[0].text(), MediaLibAction.OPEN_GIT)
        self.assertEqual(_actions[1].text(), "Set Application Log Level")
        self.assertTrue(_actions[2].isSeparator())
        self.assertEqual(_actions[3].text(), MediaLibAction.ABOUT)

        self.assertEqual(len(_actions), 4)


class TestFileMenu(unittest.TestCase):

    def setUp(self):
        self._file_menu = FileMenu(None)

    def test_init_view(self):
        _actions = list(self._file_menu.actions())
        self.assertEqual(_actions[0].text(), MediaLibAction.OPEN_FILE)
        self.assertEqual(_actions[1].text(), MediaLibAction.OPEN_PATH)
        self.assertTrue(_actions[2].isSeparator())
        self.assertEqual(_actions[3].text(), MediaLibAction.SETTINGS)
        self.assertTrue(_actions[4].isSeparator())
        self.assertEqual(_actions[5].text(), MediaLibAction.APP_EXIT)

        self.assertEqual(len(_actions), 6)




