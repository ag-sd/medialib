import logging
from enum import StrEnum
from functools import partial

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QActionGroup
from PyQt6.QtWidgets import QMenuBar, QMenu

import app
from app import views, appsettings
from app.database.ds import Database
from app.database.props import DBType
from app.views import ViewType


def _create_action(parent, name, func=None, shortcut=None, tooltip=None, icon=None, checked=None, enabled=True):
    """
    Creates an action for use in a Toolbar or Menu
    :param parent: The actions parent
    :param name: The action name
    :param func: The function to call when this action is triggered
    :param shortcut: The keyboard shortcut for this action
    :param tooltip: The tooltip to display when this action is interacted with
    :param icon: The icon to show for this action
    :param checked: Whether the visual cue associated with this action represents a check mark
    :param enabled: Whether the action is enabled once created
    :return: A QAction object representing this action
    """
    # TODO: Test
    action = QAction(name, parent)
    if tooltip and shortcut:
        tooltip = f"{tooltip} ({shortcut})"
    if shortcut:
        action.setShortcut(shortcut)
    if tooltip:
        action.setToolTip(tooltip)
        action.setStatusTip(tooltip)
    if func:
        action.triggered.connect(partial(func, name))
    if icon:
        action.setIcon(QIcon.fromTheme(icon))
    if checked:
        action.setCheckable(True)
        action.setChecked(checked)
    action.setEnabled(enabled)
    return action


def _find_action(text, actions):
    """
    BFS search of the menu for a particular action. Caller can cast it to a menu if required
    :param text: action text to search for
    :return:
    """
    # TODO: Test
    q = list(actions)
    while len(q) > 0:
        action = q.pop(0)
        if action.isSeparator():
            continue
        if action.text() == text:
            return action
        if action.menu() is not None:
            q.extend(action.menu().actions())


class MediaLibAction(StrEnum):
    OPEN_FILE = "Open Files..."
    OPEN_PATH = "Open Directory..."
    APP_EXIT = "Exit"
    OPEN_GIT = "Go to Project on GitHub..."
    ABOUT = "About"
    SETTINGS = "Preferences..."


class DBAction(StrEnum):
    SAVE = "Save..."
    SAVE_AS = "Save As..."
    REFRESH = "Refresh"
    REFRESH_SELECTED = "Refresh Selected Paths"
    RESET = "Reset"
    OPEN_DB = "Open Database..."
    SHUT_DB = "Close Database"
    BOOKMARK = "Add or Remove Favorite"


class LogLevelOptions:
    LOG_DEBUG = "DEBUG"
    LOG_INFO = "INFO"
    LOG_WARNING = "WARNING"
    LOG_EXCEPTION = "EXCEPTION"

    def __init__(self, parent):
        self._debug = _create_action(parent, self.LOG_DEBUG, self._log_level_changed,
                                     tooltip="Display all application logs", checked=False)
        self._info = _create_action(parent, self.LOG_INFO, self._log_level_changed,
                                    tooltip="Do not show debug logs", checked=False)
        self._warning = _create_action(parent, self.LOG_WARNING, self._log_level_changed,
                                       tooltip="Display warnings and errors only", checked=False)
        self._error = _create_action(parent, self.LOG_EXCEPTION, self._log_level_changed,
                                     tooltip="Only show application errors", checked=False)

        self._log_level_group = QActionGroup(parent)
        self._log_level_group.setExclusionPolicy(QActionGroup.ExclusionPolicy.Exclusive)
        self._log_level_group.addAction(self._debug)
        self._log_level_group.addAction(self._info)
        self._log_level_group.addAction(self._warning)
        self._log_level_group.addAction(self._error)

        self._log_menu = QMenu("Set Application Log Level", parent)
        self._log_menu.setIcon(QIcon.fromTheme("text-x-generic"))
        self._log_menu.addActions([self._debug, self._info, self._warning, self._error])
        self.set_application_log_level(appsettings.get_log_level())

    @property
    def log_options_menu(self) -> QMenu:
        return self._log_menu

    def _log_level_changed(self, log_level):
        match log_level:
            case self.LOG_EXCEPTION:
                self.set_application_log_level(logging.ERROR)
            case self.LOG_DEBUG:
                self.set_application_log_level(logging.DEBUG)
            case self.LOG_INFO:
                self.set_application_log_level(logging.INFO)
            case self.LOG_WARNING:
                self.set_application_log_level(logging.WARNING)

    def _set_log_level_menu_option(self, log_level):
        match log_level:
            case logging.DEBUG:
                self._debug.setChecked(True)
            case logging.INFO:
                self._info.setChecked(True)
            case logging.WARNING:
                self._warning.setChecked(True)
            case logging.ERROR:
                self._error.setChecked(True)

    def set_application_log_level(self, log_level):
        app.logger.critical(f"Log level changed to {logging.getLevelName(log_level)}")
        app.logger.setLevel(log_level)
        appsettings.set_log_level(log_level)
        self._set_log_level_menu_option(log_level)


class AppMenuBar(QMenuBar):
    view_changed = pyqtSignal(ViewType)
    paths_changed = pyqtSignal(list)
    open_db_action = pyqtSignal(str)
    medialib_action = pyqtSignal(MediaLibAction)
    database_action = pyqtSignal(DBAction)

    _MENU_DATABASE_PATHS = "Database Paths"
    _MENU_DATABASE_HISTORY = "Recently Opened"
    _MENU_DATABASE_BOOKMARKS = "Favorites"

    def __init__(self, plugins: list):
        super().__init__()
        self._log_level_options = LogLevelOptions(self)
        self.db_menu = self._create_database_menu()
        self.view_menu = self._create_view_menu()
        self.addMenu(self._create_file_menu())
        self.addMenu(self.db_menu)
        self.addMenu(self.view_menu)
        if len(plugins) > 0:
            self.addMenu(self._create_window_menu(plugins))
        self.addMenu(self._create_help_menu())

    def add_db_paths(self, paths):
        # TODO: Test
        """
        Adds new paths to the database path menu, if these paths does not exist already
        :param paths: The paths to add
        """
        paths_menu = _find_action(self._MENU_DATABASE_PATHS, self.db_menu.actions()).menu()
        for item in paths:
            self._add_path(paths_menu, item)

    def get_selected_db_paths(self):
        """
        Returns:
            All the DB paths that are currently selected

        """
        paths_menu = _find_action(self._MENU_DATABASE_PATHS, self.db_menu.actions()).menu()
        q = list(paths_menu.actions())
        selected = []
        while len(q) > 0:
            action = q.pop(0)
            if action.isChecked():
                selected.append(action.text())
        return selected

    def update_recents(self, recents: list):
        self._update_db_list(menu_name=self._MENU_DATABASE_HISTORY, sub_items=recents,
                             icon_name="folder-open-recent")

    def update_bookmarks(self, bookmarks: list):
        self._update_db_list(menu_name=self._MENU_DATABASE_BOOKMARKS, sub_items=bookmarks, icon_name="bookmarks")

    def show_database(self, database: Database):
        # You can only save to an existing database. Default databases need to be 'saved as'
        _find_action(DBAction.SAVE, self.db_menu.actions()).setEnabled(not database.type == DBType.IN_MEMORY)
        _find_action(DBAction.SAVE_AS, self.db_menu.actions()).setEnabled(True)
        _find_action(DBAction.RESET, self.db_menu.actions()).setEnabled(not database.type == DBType.IN_MEMORY)
        _find_action(DBAction.REFRESH, self.db_menu.actions()).setEnabled(True)
        _find_action(DBAction.REFRESH_SELECTED, self.db_menu.actions()).setEnabled(True)
        _find_action(DBAction.BOOKMARK, self.db_menu.actions()).setEnabled(not database.type == DBType.IN_MEMORY)
        _find_action(DBAction.SHUT_DB, self.db_menu.actions()).setEnabled(True)

        paths_menu = _find_action(self._MENU_DATABASE_PATHS, self.db_menu.actions()).menu()
        self._clear_menu(paths_menu)
        self.add_db_paths(database.paths)

    def shut_database(self):
        _find_action(DBAction.SAVE, self.db_menu.actions()).setEnabled(False)
        _find_action(DBAction.SAVE_AS, self.db_menu.actions()).setEnabled(False)
        _find_action(DBAction.RESET, self.db_menu.actions()).setEnabled(False)
        _find_action(DBAction.REFRESH, self.db_menu.actions()).setEnabled(False)
        _find_action(DBAction.REFRESH_SELECTED, self.db_menu.actions()).setEnabled(False)
        _find_action(DBAction.BOOKMARK, self.db_menu.actions()).setEnabled(False)
        _find_action(DBAction.SHUT_DB, self.db_menu.actions()).setEnabled(False)

        paths_menu = _find_action(self._MENU_DATABASE_PATHS, self.db_menu.actions()).menu()
        self._clear_menu(paths_menu)

    def _update_db_list(self, menu_name: str, sub_items: list, icon_name: str):
        _menu = _find_action(menu_name, self.db_menu.actions()).menu()
        if _menu is None:
            raise AttributeError(f"{menu_name} not in this list")

        self._clear_menu(_menu)
        for path in sub_items:
            _menu.addAction(_create_action(self, path, func=self._open_db_event, icon=icon_name))

    @staticmethod
    def _clear_menu(menu):
        # TODO: Test
        for action in list(menu.actions()):
            menu.removeAction(action)

    def _create_view_menu(self):
        # TODO: Test
        view_menu = QMenu("&View", self)

        for i, v in enumerate(ViewType):
            view_menu.addAction(_create_action(self, v.name, func=self._raise_view_event, icon=v.icon,
                                               shortcut=f"Alt+Shift+{i + 1}", tooltip=v.description))

        return view_menu

    def _create_database_menu(self):
        # TODO: Test
        db_menu = QMenu("&Database", self)
        db_menu.addAction(_create_action(self, DBAction.SAVE, shortcut="Ctrl+S", icon="document-save",
                                         tooltip="Save the exif data of all open paths to the DB",
                                         func=self._raise_db_event, enabled=False))
        db_menu.addAction(_create_action(self, DBAction.SAVE_AS, shortcut="Ctrl+Shift+S", icon="document-save-as",
                                         tooltip="Save the exif data of all open paths to the DB",
                                         func=self._raise_db_event, enabled=False))
        db_menu.addAction(_create_action(self, DBAction.SHUT_DB, shortcut="Ctrl+W", icon="document-close",
                                         tooltip="Close the database, saving it if required",
                                         func=self._raise_db_event, enabled=False))
        db_menu.addSeparator()
        db_menu.addAction(_create_action(self, DBAction.REFRESH, shortcut="F5", icon="view-refresh",
                                         tooltip="Reload the exif data for the all the database paths",
                                         func=self._raise_db_event, enabled=False))
        db_menu.addAction(_create_action(self, DBAction.REFRESH_SELECTED, shortcut="Shift+F5", icon="view-refresh",
                                         tooltip="Reload the exif data for the the selected database paths",
                                         func=self._raise_db_event, enabled=False))
        db_menu.addAction(_create_action(self, DBAction.RESET, icon="view-restore",
                                         tooltip="Reset this database",
                                         func=self._raise_db_event, enabled=False))
        db_menu.addAction(_create_action(self, DBAction.BOOKMARK, icon="bookmark",
                                         tooltip="Add or remove this database from favorites",
                                         func=self._raise_db_event, enabled=False))
        db_menu.addSeparator()

        paths_menu = QMenu(self._MENU_DATABASE_PATHS, self)
        paths_menu.setIcon(QIcon.fromTheme("database-paths"))

        db_menu.addMenu(paths_menu)

        db_menu.addSeparator()
        db_menu.addAction(_create_action(self, DBAction.OPEN_DB, shortcut="Ctrl+D",
                                         icon="database-open", func=self._raise_db_event,
                                         tooltip="Open a non registered private database"))

        history_menu = QMenu(self._MENU_DATABASE_HISTORY, self)
        history_menu.setIcon(QIcon.fromTheme("folder-open-recent"))

        bookmarks_menu = QMenu(self._MENU_DATABASE_BOOKMARKS, self)
        bookmarks_menu.setIcon(QIcon.fromTheme("bookmark"))

        db_menu.addSeparator()
        db_menu.addMenu(history_menu)
        db_menu.addMenu(bookmarks_menu)

        return db_menu

    def _add_path(self, menu: QMenu, path: str):
        """
        Appends a new path tho the given menu, if this path does not exist already
        :param path: The path to add
        :param menu: The menu to add the path to
        """
        # TODO: Test
        count = len(menu.actions())
        existing = _find_action(path, menu.actions())
        if existing is not None:
            app.logger.warning(f"{path} already exists in this database.")
            return
        menu.addAction(
            _create_action(self, path, func=self._raise_paths_change, icon=views.get_mime_type_icon_name(path),
                           shortcut=f"Ctrl+{count + 1}" if count < 9 else None, checked=True))

    def _create_file_menu(self):
        # TODO: Test
        file_menu = QMenu("&File", self)
        file_menu.addAction(_create_action(self, MediaLibAction.OPEN_FILE, shortcut="Ctrl+O",
                                           func=self._raise_menu_event, icon="document-open",
                                           tooltip="Open a file to view its exif data"))
        file_menu.addAction(_create_action(self, MediaLibAction.OPEN_PATH, shortcut="Ctrl+D",
                                           func=self._raise_menu_event,
                                           tooltip="Open a directory to view info of all supported files in it",
                                           icon="document-open-folder"))
        file_menu.addSeparator()
        file_menu.addAction(_create_action(self, MediaLibAction.SETTINGS, func=self._raise_menu_event,
                                           shortcut="Ctrl+,", icon="preferences-system",
                                           tooltip=f"Quit {app.__NAME__}"))
        file_menu.addSeparator()
        file_menu.addAction(_create_action(self, MediaLibAction.APP_EXIT, func=self._raise_menu_event,
                                           shortcut="Ctrl+Q", icon="application-exit",
                                           tooltip=f"Quit {app.__NAME__}"))
        return file_menu

    def _create_window_menu(self, plugins: list):
        window_menu = QMenu("&Window", self)

        for plugin in plugins:
            pl_action = plugin.toggleViewAction()
            pl_action.setToolTip(plugin.statustip)
            pl_action.setShortcut(plugin.shortcut)
            pl_action.setIcon(plugin.icon)
            window_menu.addAction(pl_action)

        return window_menu

    def _create_help_menu(self):
        # TODO: Test
        help_menu = QMenu("&Help", self)
        help_menu.addAction(_create_action(self, MediaLibAction.OPEN_GIT, self._raise_menu_event,
                                           icon="folder-git", tooltip="Visit this project on GitHub"))
        help_menu.addMenu(self._log_level_options.log_options_menu)
        help_menu.addSeparator()
        help_menu.addAction(_create_action(self, MediaLibAction.ABOUT, self._raise_menu_event, icon="help-about",
                                           tooltip="About this application"))
        return help_menu

    def _raise_view_event(self, event):
        self.view_changed.emit(ViewType[event])

    def _raise_menu_event(self, action):
        self.medialib_action.emit(MediaLibAction(action))

    def _raise_paths_change(self, _):
        paths = []
        paths_menu = _find_action(self._MENU_DATABASE_PATHS, self.db_menu.actions()).menu()
        for item in paths_menu.actions():
            if item.isChecked():
                paths.append(item.text())

        self.paths_changed.emit(paths)

    def _open_db_event(self, recent):
        self.open_db_action.emit(recent)

    def _raise_db_event(self, action):
        self.database_action.emit(DBAction(action))
