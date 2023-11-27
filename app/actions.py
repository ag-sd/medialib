from enum import StrEnum
from functools import partial

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenuBar, QMenu

import app
from app import views
from app.database.Database import Database
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
    action = QAction(name, parent)
    if shortcut is not None:
        action.setShortcut(shortcut)
    if tooltip is not None:
        if shortcut is not None:
            tooltip = f"{tooltip} ({shortcut})"
        action.setToolTip(tooltip)
    if func:
        action.triggered.connect(partial(func, name))
    if icon is not None:
        action.setIcon(QIcon.fromTheme(icon))
    if checked is not None:
        action.setCheckable(True)
        action.setChecked(checked)
    return action


def _find_action(text, actions):
    """
    BFS search of the menu for a particular action. Caller can cast it to a menu if required
    :param text: action text to search for
    :return:
    """
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
    OPEN_FILE = "Open File"
    OPEN_PATH = "Open Directory"
    OPEN_DB = "Open Database"
    APP_EXIT = "Exit"
    OPEN_GIT = "Go to Project on GitHub"
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

    def __init__(self, database: Database):
        super().__init__()
        self.db_menu = self._create_database_menu(database)
        self.view_menu = self._create_view_menu(database)
        self.addMenu(self._create_file_menu())
        self.addMenu(self.db_menu)
        self.addMenu(self.view_menu)
        self.addMenu(self._create_help_menu())

    def add_db_path(self, item):
        """
        Adds a new path tho the database path menu, if this path does not exist already
        :param item: The path to add
        """
        self._add_path(self.db_menu, item)

    def _create_view_menu(self, database: Database):
        view_menu = QMenu("&View", self)
        for i, v in enumerate(database.views):
            view_menu.addAction(_create_action(self, v.name, func=self.raise_view_event, icon=self.__view_icons__[v],
                                               shortcut=f"Ctrl+Alt+{i + 1}"))

        return view_menu

    def _create_database_menu(self, database: Database):
        db_menu = QMenu("&Database", self)
        db_menu.addAction(_create_action(self, "Save", shortcut="Ctrl+S", icon="document-save",
                                         tooltip="Save the exif data of all open paths to the DB",
                                         func=self.raise_db_event))
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
        db_menu.addAction(_create_action(self, "Open DB Registry", shortcut="Ctrl+Shift+O",
                                         icon="document-open-folder", func=self.raise_db_event,
                                         tooltip="Save the exif data of the current paths to the DB"))
        db_menu.addSeparator()
        for path in database.paths:
            self._add_path(db_menu, path)
        return db_menu

    def _add_path(self, menu: QMenu, path: str):
        """
        Appends a new path tho the given menu, if this path does not exist already
        :param path: The path to add
        :param menu: The menu to add the path to
        """
        print(len(menu.actions()))
        existing = _find_action(path, menu.actions())
        if existing is not None:
            app.logger.warning(f"{path} already exists in this database.")
            return
        menu.addAction(_create_action(self, path, func=self.raise_path_change,
                                      icon=views.get_mime_type_icon_name(path)))

    def _create_file_menu(self):
        file_menu = QMenu("&File", self)
        file_menu.addAction(_create_action(self, MediaLibAction.OPEN_FILE, shortcut="Ctrl+O",
                                           func=self.raise_menu_event, icon="document-open",
                                           tooltip="Open a file to view its exif data"))
        file_menu.addAction(_create_action(self, MediaLibAction.OPEN_PATH, shortcut="Ctrl+D",
                                           icon="document-open-folder", func=self.raise_menu_event,
                                           tooltip="Open a directory to view info of all supported files in it"))
        file_menu.addAction(_create_action(self, MediaLibAction.OPEN_DB, shortcut="Ctrl+D",
                                           icon="document-open-folder", func=self.raise_menu_event,
                                           tooltip="Open a directory to view info of all supported files in it"))
        file_menu.addSeparator()
        file_menu.addAction(_create_action(self, MediaLibAction.APP_EXIT, func=self.raise_menu_event,
                                           shortcut="Ctrl+Q", icon="application-exit"))
        return file_menu

    def _create_help_menu(self):
        help_menu = QMenu("&Help", self)
        help_menu.addAction(_create_action(self, MediaLibAction.OPEN_GIT, self.raise_menu_event,
                                           icon="folder-git", tooltip="About this application"))
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
