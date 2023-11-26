from enum import Enum
from functools import partial

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenuBar, QMenu

import app
from app.views import views
from app.views.views import ViewType


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


class MediaLibAction(Enum):
    OPEN_FILE = "Open File"
    OPEN_PATH = "Open Directory"
    APP_EXIT = "Exit"
    OPEN_GIT = "Go to Project on GitHub"
    ABOUT = "About"


class AppMenuBar(QMenuBar):
    view_changed = pyqtSignal(ViewType)
    path_changed = pyqtSignal(str)
    medialib_action_selected = pyqtSignal(MediaLibAction)
    database_action_selected = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.db_menu = self._create_database_menu()
        self.addMenu(self._create_file_menu())
        self.addMenu(self.db_menu)
        self.addMenu(self._create_view_menu())
        self.addMenu(self._create_help_menu())

    def add_db_path(self, item):
        existing = _find_action(item, self.db_menu.actions())
        if existing is not None:
            app.logger.warning(f"{item} already exists in this database.")
            return
        self.db_menu.addAction(_create_action(self, item, func=self.raise_path_change,
                                              icon=views.get_mime_type_icon_name(item)))

    def _create_view_menu(self):
        view_menu = QMenu("&View", self)
        view_menu.addSeparator()
        view_menu.addAction(
            _create_action(self, ViewType.JSON.name, func=self.raise_view_event, icon="application-json"))
        view_menu.addAction(_create_action(self, ViewType.HTML.name, func=self.raise_view_event, icon="text-html"))
        view_menu.addAction(
            _create_action(self, ViewType.PHP.name, func=self.raise_view_event, icon="application-x-php"))
        view_menu.addAction(_create_action(self, ViewType.XML.name, func=self.raise_view_event, icon="application-xml"))
        view_menu.addAction(_create_action(self, ViewType.CSV.name, func=self.raise_view_event, icon="text-csv"))
        return view_menu

    def _create_database_menu(self):
        db_menu = QMenu("&Database", self)
        db_menu.addAction(_create_action(self, "Add all open paths to DB", shortcut="Ctrl+Shift+S", icon="list-add",
                                         tooltip="Save the exif data of all open paths to the DB",
                                         func=self.raise_db_event))
        db_menu.addAction(_create_action(self, "Add current path to DB", shortcut="Ctrl+S", icon="folder-add",
                                         tooltip="Save the exif data of the current paths to the DB",
                                         func=self.raise_db_event))
        db_menu.addSeparator()
        db_menu.addAction(_create_action(self, "Open DB Browser", shortcut="Ctrl+Shift+O",
                                         icon="document-open-folder", func=self.raise_db_event,
                                         tooltip="Save the exif data of the current paths to the DB"))
        db_menu.addSeparator()
        return db_menu

    def _create_file_menu(self):
        file_menu = QMenu("&File", self)
        file_menu.addAction(_create_action(self, MediaLibAction.OPEN_FILE.name, shortcut="Ctrl+O",
                                           func=self.raise_menu_event, icon="document-open",
                                           tooltip="Open a file to view its exif data"))
        file_menu.addAction(_create_action(self, MediaLibAction.OPEN_PATH.name, shortcut="Ctrl+D",
                                           icon="document-open-folder", func=self.raise_menu_event,
                                           tooltip="Open a directory to view info of all supported files in it"))
        file_menu.addSeparator()
        file_menu.addAction(_create_action(self, MediaLibAction.APP_EXIT.name, func=self.raise_menu_event,
                                           shortcut="Ctrl+Q", icon="application-exit"))
        return file_menu

    def _create_help_menu(self):
        help_menu = QMenu("&Help", self)
        help_menu.addAction(_create_action(self, MediaLibAction.OPEN_GIT.name, self.raise_menu_event,
                                           icon="folder-git", tooltip="About this application"))
        help_menu.addSeparator()
        help_menu.addAction(_create_action(self, MediaLibAction.ABOUT.name, self.raise_menu_event, icon="help-about",
                                           tooltip="About this application"))
        return help_menu

    def raise_view_event(self, event):
        self.view_changed.emit(ViewType[event])

    def raise_menu_event(self, event):
        self.medialib_action_selected.emit(MediaLibAction[event])

    def raise_path_change(self, path_name):
        self.path_changed.emit(path_name)

    def raise_db_event(self, event):
        self.database_action_selected.emit(event)
