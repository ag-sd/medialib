import logging
import tempfile
import unittest

from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QAction, QKeyEvent
from PyQt6.QtWidgets import QWidget, QWidgetAction, QDockWidget, QMenu

import app
from app import actions, apputils, appsettings
from app.actions import HelpMenu, MediaLibAction, FileMenu, CollectionMenu, DBAction, AppMenuBar, ViewContextMenu, \
    ViewContextMenuAction
from app.plugins.framework import WindowInfo
from tests.collection import test_utils
from tests.collection.test_utils import CallbackHandler


class TestActions(unittest.TestCase):

    # https://github.com/jmcgeheeiv/pyqttestexample/blob/master/src/MargaritaMixerTest.py

    def test_create_action_missing_fields(self):
        i1 = apputils.create_action(None, "Test1")
        self.assertTrue(i1.text() == "Test1")

    def test_tooltip_and_shortcut(self):
        # If action has tooltip and shortcut, these are set at multiple places
        i2 = apputils.create_action(None, "Test2", func=None, shortcut="X", tooltip="TOOLTIP")
        self.assertTrue(i2.toolTip() == "TOOLTIP (X)")
        self.assertTrue(i2.toolTip() == "TOOLTIP (X)")
        self.assertTrue(i2.statusTip() == "TOOLTIP (X)")
        self.assertTrue(i2.shortcut() == "X")

    def test_no_tooltip(self):
        # If no shortcut is set, the tooltip does not show this
        i2 = apputils.create_action(None, "Test2", func=None, shortcut=None, tooltip="TOOLTIP")
        self.assertTrue(i2.toolTip() == "TOOLTIP")
        self.assertTrue(i2.toolTip() == "TOOLTIP")
        self.assertTrue(i2.statusTip() == "TOOLTIP")
        self.assertTrue(i2.shortcut().isEmpty())
        self.assertIsInstance(i2, QAction)

    def test_widget_action_creation(self):
        # If a widget is supplied, the action returned is a widget action
        i2 = apputils.create_action(None, "Test2", func=None, shortcut=None, tooltip="TOOLTIP",
                                    widget=QWidget())
        self.assertIsInstance(i2, QWidgetAction)


class TestViewMenu(unittest.TestCase):

    def setUp(self):
        self._view_menu = ViewContextMenu(None)

    def test_init_menu(self):
        _actions = list(self._view_menu.actions())
        self.assertEqual(_actions[0].text(), ViewContextMenuAction.OPEN)
        self.assertEqual(_actions[1].text(), ViewContextMenuAction.EXPLORE)
        self.assertEqual(_actions[2].text(), ViewContextMenuAction.FS_VIEW)
        self.assertTrue(_actions[3].isSeparator())
        self.assertEqual(_actions[4].text(), "Columns")
        self.assertEqual(_actions[5].text(), "Group By")
        self.assertEqual(_actions[6].text(), "Preset Views")
        self.assertTrue(_actions[7].isSeparator())
        self.assertEqual(_actions[8].text(), ViewContextMenuAction.EXPORT)

        self.assertEqual(len(_actions), 9)

    def test_show_collection_image_files(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            # Image File
            db = test_utils.create_test_media_db(db_path, test_paths[:1])
            db.save()
            self._view_menu.show_collection(db)
            # Available fields count will be different
            self.assertEqual(len(list(self._view_menu._vm_columns.actions())), 8)
            # Presets are available
            self.assertEqual(len(list(self._view_menu._vm_presets.actions())), 2)

    def test_show_collection_audio_files(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            # Audio File
            db = test_utils.create_test_media_db(db_path, test_paths[1:])
            db.save()
            self._view_menu.show_collection(db)
            # Available fields count will be different
            self.assertEqual(len(list(self._view_menu._vm_columns.actions())), 11)
            # Presets are available
            self.assertEqual(len(list(self._view_menu._vm_presets.actions())), 2)

    def test_shut_collection(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            # Audio File
            db = test_utils.create_test_media_db(db_path, test_paths[1:])
            db.save()
            self._view_menu.show_collection(db)
            self._view_menu.shut_collection()
            # Fields is disabled
            self.assertFalse(self._view_menu._vm_columns.isEnabled())
            self.assertFalse(self._view_menu._vm_presets.isEnabled())
            self.assertFalse(self._view_menu._vm_groupby.isEnabled())
            self.assertFalse(self._view_menu._view_fs.isChecked())


class TestHelpMenu(unittest.TestCase):

    def setUp(self):
        self._help_menu = HelpMenu(None)
        self._log_level = app.logger.level

    def tearDown(self):
        app.logger.setLevel(self._log_level)

    def test_init_menu(self):
        _actions = list(self._help_menu.actions())
        self.assertEqual(_actions[0].text(), MediaLibAction.OPEN_GIT)
        self.assertEqual(_actions[1].text(), "Set Application Log Level")
        self.assertTrue(_actions[2].isSeparator())
        self.assertEqual(_actions[3].text(), MediaLibAction.ABOUT)

        self.assertEqual(len(_actions), 4)

    def test_log_level_change_w(self):
        self._help_menu._log_level_changed(self._help_menu.LOG_WARNING)
        self.assertEqual(logging.WARNING, app.logger.level)

    def test_log_level_change_i(self):
        self._help_menu._log_level_changed(self._help_menu.LOG_INFO)
        self.assertEqual(logging.INFO, app.logger.level)

    def test_log_level_change_d(self):
        self._help_menu._log_level_changed(self._help_menu.LOG_DEBUG)
        self.assertEqual(logging.DEBUG, app.logger.level)

    def test_log_level_change_e(self):
        self._help_menu._log_level_changed(self._help_menu.LOG_ERROR)
        self.assertEqual(logging.ERROR, app.logger.level)

    def test_set_log_level_session(self):
        self._help_menu.set_application_log_level(logging.ERROR, False)
        self.assertEqual(logging.ERROR, app.logger.level)
        self.assertEqual(self._log_level, appsettings.get_log_level())


class TestFileMenu(unittest.TestCase):

    def setUp(self):
        self._file_menu = FileMenu(None)

    def test_init_menu(self):
        _actions = list(self._file_menu.actions())
        self.assertEqual(_actions[0].text(), MediaLibAction.OPEN_FILE)
        self.assertEqual(_actions[1].text(), MediaLibAction.OPEN_PATH)
        self.assertTrue(_actions[2].isSeparator())
        self.assertEqual(_actions[3].text(), MediaLibAction.SETTINGS)
        self.assertTrue(_actions[4].isSeparator())
        self.assertEqual(_actions[5].text(), MediaLibAction.APP_EXIT)

        self.assertEqual(len(_actions), 6)

    def test_find_actions(self):
        self.assertTrue(actions._find_action(MediaLibAction.OPEN_FILE, self._file_menu.actions()) is not None)
        self.assertTrue(actions._find_action(MediaLibAction.OPEN_PATH, self._file_menu.actions()) is not None)

        self.assertTrue(actions._find_action(MediaLibAction.OPEN_GIT, self._file_menu.actions()) is None)


class TestCollectionMenu(unittest.TestCase):

    def setUp(self):
        self._db_menu = CollectionMenu(None)
        self._callback_handled = False
        self._callback_counter = 0

    def test_init_menu(self):
        _actions = list(self._db_menu.actions())
        self.assertEqual(_actions[0].text(), DBAction.SAVE)
        self.assertEqual(_actions[1].text(), DBAction.SAVE_AS)
        self.assertEqual(_actions[2].text(), DBAction.SHUT_DB)
        self.assertTrue(_actions[3].isSeparator())
        self.assertEqual(_actions[4].text(), DBAction.REFRESH)
        self.assertEqual(_actions[5].text(), DBAction.REFRESH_SELECTED)
        self.assertEqual(_actions[6].text(), DBAction.RESET)
        self.assertEqual(_actions[7].text(), DBAction.REINDEX_COLLECTION)
        self.assertTrue(_actions[8].isSeparator())
        self.assertEqual(_actions[9].text(), CollectionMenu._MENU_DB_PATHS)
        self.assertTrue(_actions[10].isSeparator())
        self.assertEqual(_actions[11].text(), DBAction.OPEN_DB)
        self.assertEqual(_actions[12].text(), DBAction.OPEN_PRIVATE_DB)
        self.assertTrue(_actions[13].isSeparator())
        self.assertEqual(_actions[14].text(), CollectionMenu._MENU_DB_HISTORY)
        self.assertEqual(_actions[15].text(), CollectionMenu._MENU_DB_BOOKMARKS)
        self.assertEqual(_actions[16].text(), DBAction.BOOKMARK)

        self.assertEqual(len(_actions), 17)
        self.assertFalse(_actions[12].isVisible())

    def test_open_private_collection_option(self):
        _actions = list(self._db_menu.actions())
        self.assertFalse(_actions[12].isVisible())
        self._db_menu.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Control, Qt.KeyboardModifier.NoModifier))
        self.assertTrue(_actions[12].isVisible())

    def test_open_collection_on_disk(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            db.save()
            self._db_menu.show_collection(db)
            self.assertTrue(_find_action(DBAction.SAVE, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.SAVE_AS, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.RESET, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.REFRESH, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.REFRESH_SELECTED, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.BOOKMARK, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.SHUT_DB, self._db_menu).isEnabled())
            self.assertTrue(self._db_menu._paths_menu.isEnabled())

            self.assertEqual(len(self._db_menu._paths_menu.actions()), len(test_paths))

    def test_open_private_collection_on_disk(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            db.save()
            db.is_private = True
            self._db_menu.show_collection(db)
            self.assertTrue(_find_action(DBAction.SAVE, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.SAVE_AS, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.RESET, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.REFRESH, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.REFRESH_SELECTED, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.BOOKMARK, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.SHUT_DB, self._db_menu).isEnabled())
            self.assertTrue(self._db_menu._paths_menu.isEnabled())

            self.assertEqual(len(self._db_menu._paths_menu.actions()), len(test_paths))

    def test_open_private_collection_in_memory(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            db.is_private = True
            self._db_menu.show_collection(db)
            self.assertFalse(_find_action(DBAction.SAVE, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.SAVE_AS, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.RESET, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.REFRESH, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.REFRESH_SELECTED, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.BOOKMARK, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.SHUT_DB, self._db_menu).isEnabled())
            self.assertTrue(self._db_menu._paths_menu.isEnabled())

            self.assertEqual(len(self._db_menu._paths_menu.actions()), len(test_paths))

    def test_shut_collection_on_disk(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            db.save()
            self._db_menu.show_collection(db)
            self.assertEqual(len(self._db_menu._paths_menu.actions()), len(test_paths))

            # Test
            self._db_menu.shut_collection()
            self.assertFalse(_find_action(DBAction.SAVE, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.SAVE_AS, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.RESET, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.REFRESH, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.REFRESH_SELECTED, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.BOOKMARK, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.SHUT_DB, self._db_menu).isEnabled())
            self.assertFalse(self._db_menu._paths_menu.isEnabled())

            self.assertEqual(len(self._db_menu._paths_menu.actions()), 0)

    def test_open_collection_in_mem(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_temp_files(20)
            db = test_utils.create_test_media_db(db_path, test_paths)

            self._db_menu.show_collection(db)
            self.assertFalse(_find_action(DBAction.SAVE, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.SAVE_AS, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.RESET, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.REFRESH, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.REFRESH_SELECTED, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.BOOKMARK, self._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.SHUT_DB, self._db_menu).isEnabled())
            self.assertTrue(self._db_menu._paths_menu.isEnabled())

            self.assertEqual(len(self._db_menu._paths_menu.actions()), len(test_paths))

    def test_shut_collection_in_mem(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_temp_files(20)
            db = test_utils.create_test_media_db(db_path, test_paths)
            self._db_menu.show_collection(db)
            self.assertEqual(len(self._db_menu._paths_menu.actions()), len(test_paths))

            # Test
            self._db_menu.shut_collection()
            self.assertFalse(_find_action(DBAction.SAVE, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.SAVE_AS, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.RESET, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.REFRESH, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.REFRESH_SELECTED, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.BOOKMARK, self._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.SHUT_DB, self._db_menu).isEnabled())
            self.assertFalse(self._db_menu._paths_menu.isEnabled())

            self.assertEqual(len(self._db_menu._paths_menu.actions()), 0)

    def test_selected_paths(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_temp_files(7)
            db = test_utils.create_test_media_db(db_path, test_paths)
            self._db_menu.show_collection(db)
            self.assertEqual(self._db_menu.selected_paths, test_paths)

    def test_update_recents(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_temp_files(7)
            db = test_utils.create_test_media_db(db_path, test_paths)
            self._db_menu.show_collection(db)
            self.assertEqual(len(self._db_menu._history_menu.actions()), 0)
            self._db_menu.update_recents(test_utils.get_temp_files(3))
            self.assertEqual(len(self._db_menu._history_menu.actions()), 3)

    def test_update_bookmarks(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_temp_files(5)
            db = test_utils.create_test_media_db(db_path, test_paths)
            self._db_menu.show_collection(db)
            self.assertEqual(len(self._db_menu._bookmarks_menu.actions()), 0)
            self._db_menu.update_bookmarks(test_utils.get_temp_files(4))
            self.assertEqual(len(self._db_menu._bookmarks_menu.actions()), 4)

    def test_path_change_event(self):
        def cb_func(action, event_args):
            self.assertEqual(action, DBAction.PATH_CHANGE)
            self.assertEqual(len(event_args), 5)
            self._callback_handled = True

        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_temp_files(6)
            db = test_utils.create_test_media_db(db_path, test_paths)
            self._db_menu.show_collection(db)
            self.assertEqual(len(self._db_menu._paths_menu.actions()), 6)
            self._db_menu.collection_event.connect(cb_func)
            self._db_menu._paths_menu.actions()[0].trigger()
            self.assertTrue(self._callback_handled)

    def test_open_db_event(self):
        hist_paths = test_utils.get_temp_files(3)

        def cb_func(action, event_args):
            self.assertEqual(action, DBAction.OPEN_DB)
            self.assertEqual(event_args, hist_paths[0])
            self._callback_handled = True

        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_temp_files(7)
            db = test_utils.create_test_media_db(db_path, test_paths)
            self._db_menu.show_collection(db)
            self.assertEqual(len(self._db_menu._history_menu.actions()), 0)

            self._db_menu.update_recents(hist_paths)
            self.assertEqual(len(self._db_menu._history_menu.actions()), 3)
            self._db_menu.collection_event.connect(cb_func)
            self._db_menu._history_menu.actions()[0].trigger()
            self.assertTrue(self._callback_handled)

    def test_general_db_event(self):
        self._callback_counter = 3

        def cb_func(_, __):
            self._callback_counter -= 1
            self._callback_handled = self._callback_counter == 0

        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_temp_files(9)
            db = test_utils.create_test_media_db(db_path, test_paths)
            self._db_menu.show_collection(db)
            self._db_menu.collection_event.connect(cb_func)
            _find_action(DBAction.SAVE_AS, self._db_menu).trigger()  # Will trigger
            _find_action(DBAction.SAVE, self._db_menu).trigger()  # Will not trigger as it's disabled for in-memory db
            _find_action(DBAction.SHUT_DB, self._db_menu).trigger()  # Will trigger
            _find_action(DBAction.REFRESH, self._db_menu).trigger()  # Will trigger
            self.assertTrue(self._callback_handled)
            self.assertEqual(self._callback_counter, 0)

    def test_selective_refresh_event(self):
        test_paths = test_utils.get_temp_files(7)

        def cb_func(action, event_args):
            self.assertEqual(action, DBAction.REFRESH_SELECTED)
            self.assertEqual(len(event_args), len(test_paths))
            self._callback_handled = True

        with tempfile.TemporaryDirectory() as db_path:
            db = test_utils.create_test_media_db(db_path, test_paths)
            self._db_menu.show_collection(db)
            self._db_menu.collection_event.connect(cb_func)
            _find_action(DBAction.REFRESH_SELECTED, self._db_menu).trigger()
            self.assertTrue(self._callback_handled)

    def _find_action(self, action_name):
        return actions._find_action(action_name, self._db_menu.actions())


class TestAppMenuBar(unittest.TestCase):

    def setUp(self):
        self._menu = AppMenuBar()

    def test_update_recents(self):
        self._menu.update_recents(["1", "2", "4"])
        self.assertEqual(3, len(self._menu._db_menu._history_menu.actions()))

    def test_update_bookmarks(self):
        self._menu.update_bookmarks(["1", "2", "4"])
        self.assertEqual(3, len(self._menu._db_menu._bookmarks_menu.actions()))

    def test_show_collection(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            # Image File
            db = test_utils.create_test_media_db(db_path, test_paths)
            db.save()

            self._menu.show_collection(db)

            self.assertTrue(_find_action(DBAction.SAVE, self._menu._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.SAVE_AS, self._menu._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.RESET, self._menu._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.REFRESH, self._menu._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.REFRESH_SELECTED, self._menu._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.BOOKMARK, self._menu._db_menu).isEnabled())
            self.assertTrue(_find_action(DBAction.SHUT_DB, self._menu._db_menu).isEnabled())
            self.assertTrue(self._menu._db_menu._paths_menu.isEnabled())
            self.assertEqual(len(self._menu._db_menu._paths_menu.actions()), len(test_paths))

    def test_shut_collection(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            # Image File
            db = test_utils.create_test_media_db(db_path, test_paths)
            db.save()

            self._menu.show_collection(db)
            self.assertEqual(len(self._menu._db_menu._paths_menu.actions()), len(test_paths))

            # Actual Test
            self._menu.shut_collection()
            self.assertFalse(_find_action(DBAction.SAVE, self._menu._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.SAVE_AS, self._menu._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.RESET, self._menu._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.REFRESH, self._menu._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.REFRESH_SELECTED, self._menu._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.BOOKMARK, self._menu._db_menu).isEnabled())
            self.assertFalse(_find_action(DBAction.SHUT_DB, self._menu._db_menu).isEnabled())
            self.assertFalse(self._menu._db_menu._paths_menu.isEnabled())
            self.assertEqual(len(self._menu._db_menu._paths_menu.actions()), 0)

    def test_get_selected_paths(self):
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            # Image File
            db = test_utils.create_test_media_db(db_path, test_paths)
            db.save()

            self._menu.show_collection(db)
            self.assertEqual(2, len(self._menu.get_selected_collection_paths()))

    def test_set_log_level_session(self):
        og_log_level = app.logger.level
        self._menu.set_application_log_level(logging.ERROR, True)
        self.assertEqual(logging.ERROR, app.logger.level)
        self.assertEqual(og_log_level, appsettings.get_log_level())

    def test_register_plugin(self):
        class DummyPl(QDockWidget, WindowInfo):
            @property
            def dockwidget_area(self):
                return Qt.DockWidgetArea.RightDockWidgetArea

            @property
            def name(self) -> str:
                return "Test Plugin"

            @property
            def statustip(self) -> str:
                return "Test Plugin"

        self.assertEqual(1, len(self._menu._window_menu.children()))
        self._menu.register_plugin(DummyPl())


def _find_action(action_name: str, menu: QMenu):
    return actions._find_action(action_name, menu.actions())
