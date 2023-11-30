from enum import StrEnum
from functools import partial

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenuBar, QMenu

import app
from app import views
from app.database.database import Database
from app.views import ViewType


def _create_action(parent, name, func=None, shortcut=None, tooltip=None, icon=None, checked=None):
    """
    Creates an action for use in a Toolbar or Menu
    :param parent: The actions parent
    :param name: The action name
    :param func: The function to call when this action is triggered
    :param shortcut: The keyboard shortcut for this action
    :param tooltip: The tooltip to display when this action is interacted with
    :param icon: The icon to show for this action
    :param checked: Whether the visual cue associated with this action represents a check mark
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
    OPEN_DB = "Open Database..."
    OPEN_DB_REGISTRY = "Open Database Registry..."
    APP_EXIT = "Exit"
    OPEN_GIT = "Go to Project on GitHub..."
    ABOUT = "About"


class AppMenuBar(QMenuBar):
    view_changed = pyqtSignal(ViewType)
    path_changed = pyqtSignal(str)
    medialib_action_selected = pyqtSignal(MediaLibAction)
    database_action_selected = pyqtSignal(str)

    __view_icons__ = {
        ViewType.JSON: "application-json",
        ViewType.HTML: "text-html",
        ViewType.PHP: "application-x-php",
        ViewType.XML: "application-xml",
        ViewType.CSV: "text-csv",
    }

    _MENU_DATABASE_PATHS = "Database Paths"

    def __init__(self, database: Database):
        super().__init__()
        self.db_menu = self._create_database_menu(database)
        self.view_menu = self._create_view_menu(database)
        self.addMenu(self._create_file_menu())
        self.addMenu(self.db_menu)
        self.addMenu(self.view_menu)
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

    def _create_view_menu(self, database: Database):
        # TODO: Test
        view_menu = QMenu("&View", self)
        for i, v in enumerate(database.views):
            view_menu.addAction(_create_action(self, v.name, func=self.raise_view_event, icon=self.__view_icons__[v],
                                               shortcut=f"Alt+Shift+{i + 1}", tooltip=v.description))

        return view_menu

    def _create_database_menu(self, database: Database):
        # TODO: Test
        db_menu = QMenu("&Database", self)
        save_action = _create_action(self, "Save", shortcut="Ctrl+S", icon="document-save",
                                     tooltip="Save the exif data of all open paths to the DB", func=self.raise_db_event)
        # You can only save to an existing database. Default databases need to be 'saved as'
        save_action.setEnabled(not database.is_default)
        db_menu.addAction(save_action)
        db_menu.addAction(_create_action(self, "Save As", shortcut="Ctrl+Shift+S", icon="document-save-as",
                                         tooltip="Save the exif data of all open paths to the DB",
                                         func=self.raise_db_event))
        db_menu.addAction(_create_action(self, "Refresh", shortcut="F5", icon="view-refresh",
                                         tooltip="Save the exif data of the current paths to the DB",
                                         func=self.raise_db_event))
        db_menu.addAction(_create_action(self, "Reset", icon="view-restore",
                                         tooltip="Reset this database",
                                         func=self.raise_db_event))
        db_menu.addSeparator()

        paths_menu = QMenu(self._MENU_DATABASE_PATHS, self)
        paths_menu.setIcon(QIcon.fromTheme("database-paths"))
        for path in database.paths:
            self._add_path(paths_menu, path)

        db_menu.addMenu(paths_menu)
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
        menu.addAction(_create_action(self, path, func=self.raise_path_change, icon=views.get_mime_type_icon_name(path),
                                      shortcut=f"Ctrl+{count + 1}" if count < 9 else None))

    def _create_file_menu(self):
        # TODO: Test
        file_menu = QMenu("&File", self)
        file_menu.addAction(_create_action(self, MediaLibAction.OPEN_FILE, shortcut="Ctrl+O",
                                           func=self.raise_menu_event, icon="document-open",
                                           tooltip="Open a file to view its exif data"))
        file_menu.addAction(_create_action(self, MediaLibAction.OPEN_PATH, shortcut="Ctrl+D",
                                           func=self.raise_menu_event,
                                           tooltip="Open a directory to view info of all supported files in it",
                                           icon="document-open-folder"))
        file_menu.addSeparator()
        file_menu.addAction(_create_action(self, MediaLibAction.OPEN_DB, shortcut="Ctrl+D",
                                           icon="database-open", func=self.raise_menu_event,
                                           tooltip="Open a non registered private database"))
        file_menu.addAction(_create_action(self, MediaLibAction.OPEN_DB_REGISTRY, shortcut="Ctrl+Shift+O",
                                           icon="database-registry", func=self.raise_db_event,
                                           tooltip="Open the database registry to view public databases"))
        file_menu.addSeparator()
        file_menu.addAction(_create_action(self, MediaLibAction.APP_EXIT, func=self.raise_menu_event,
                                           shortcut="Ctrl+Q", icon="application-exit",
                                           tooltip=f"Quit {app.__NAME__}"))
        return file_menu

    def _create_help_menu(self):
        # TODO: Test
        help_menu = QMenu("&Help", self)
        help_menu.addAction(_create_action(self, MediaLibAction.OPEN_GIT, self.raise_menu_event,
                                           icon="folder-git", tooltip="Visit this project on GitHub"))
        help_menu.addSeparator()
        help_menu.addAction(_create_action(self, MediaLibAction.ABOUT, self.raise_menu_event, icon="help-about",
                                           tooltip="About this application"))
        return help_menu

    def raise_view_event(self, event):
        self.view_changed.emit(ViewType[event])

    def raise_menu_event(self, event):
        self.medialib_action_selected.emit(MediaLibAction(event))

    def raise_path_change(self, path_name):
        self.path_changed.emit(path_name)

    def raise_db_event(self, event):
        self.database_action_selected.emit(event)

