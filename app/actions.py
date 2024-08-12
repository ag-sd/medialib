import logging
from enum import StrEnum
from functools import partial

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QActionGroup
from PyQt6.QtWidgets import QMenuBar, QMenu, QWidgetAction, QCheckBox

import app
from app import views, appsettings
from app.database import props
from app.database.ds import Database, HasDatabaseDisplaySupport
from app.database.props import DBType
from app.views import ViewType


def _create_action(parent, name, func=None, shortcut=None, tooltip=None, icon=None, checked=None, enabled=True,
                   widget=None):
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
    :param widget: If a widget is provided, this function will create a QWidgetAction instead of a QAction
    :return: A QAction object representing this action
    """
    # TODO: Test
    if widget is not None:
        action = QWidgetAction(parent)
    else:
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
    if checked is not None:
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


def _clear_menu(_menu: QMenu | QActionGroup):
    """
    Removes all entries from a menu
    Args:
        _menu: The menu to clear

    """
    for action in list(_menu.actions()):
        _menu.removeAction(action)


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
    BOOKMARK = "Add or Remove Favorite"
    OPEN_DB = "Open Database..."
    SHUT_DB = "Close Database"
    PATH_CHANGE = "Path Change"
    OPEN_SEARCH = "Search this Database"
    SHUT_SEARCH = "Close Search"


class ViewAction(StrEnum):
    VIEW = "View"
    FIELD = "Field"


class ViewMenu(QMenu, HasDatabaseDisplaySupport):
    view_event = pyqtSignal(StrEnum, "PyQt_PyObject")

    _PROP_FIELD_ID = "field-ids"

    def show_database(self, database: Database):
        self._update_all_fields_menu(database)
        self._update_presets_menu(database)

    def shut_database(self):
        _clear_menu(self._view_menu_presets)
        _clear_menu(self._view_menu_all_fields)
        _clear_menu(self._presets_group)
        self._hidden_tags = set()
        self._all_tags = []
        self._tag_checkboxes = {}

    def update_available_views(self, available_views: list):
        for action in self.actions():
            if action.property("view-action") is not None:
                action.setEnabled(action.text() in available_views)

    def __init__(self, parent):
        super().__init__("&View", parent=parent)
        self._combo_stylesheet = f"padding: {self.fontMetrics().horizontalAdvance('  ')}px; text-align:left;"
        self._hidden_tags = set()
        self._all_tags = []
        self._tag_checkboxes = {}
        self._view_menu_all_fields = QMenu("All Fields", self)
        self._view_menu_presets = QMenu("Preset Views", self)
        self._presets_group = QActionGroup(self._view_menu_presets)
        self._presets_group.setExclusive(True)
        self._init_default_menu()

    def _init_default_menu(self):
        for i, v in enumerate(ViewType):
            view_action = _create_action(self, v.name, func=self._raise_view_event, icon=v.icon,
                                         shortcut=f"Alt+Shift+{i + 1}", tooltip=v.description)
            view_action.setProperty("view-action", True)
            self.addAction(view_action)

        self.addSeparator()

        self.addMenu(self._view_menu_all_fields)
        self.addMenu(self._view_menu_presets)

    def _create_checkbox(self, text, parent, field_name):
        cb = QCheckBox(text, parent)
        cb.setToolTip(f"Show/Hide {text} in the view")
        cb.setStyleSheet(self._combo_stylesheet)
        cb.clicked.connect(partial(self._checkbox_click_event, cb))
        cb.setProperty(self._PROP_FIELD_ID, field_name)
        cb.setChecked(True)
        self._tag_checkboxes[field_name] = cb
        return cb

    def _update_all_fields_menu(self, db: Database):
        orphan_fields_added = False
        tag_groups = {}
        for key in db.tags:
            self._all_tags.append(key)
            tokens = key.split(":")
            if len(tokens) == 1:
                cb = self._create_checkbox(key, self._view_menu_all_fields, tokens[0])
                self._add_menu_item(self._view_menu_all_fields, cb)
                orphan_fields_added = True
            elif len(tokens) == 2:
                if tokens[0] not in tag_groups:
                    tag_groups[tokens[0]] = []
                tag_groups[tokens[0]].append(tokens[1])
            else:
                app.logger.warning(f"Unhandled field {key} will not be shown in the view")

        if orphan_fields_added:
            self._view_menu_all_fields.addSeparator()

        for group, items in sorted(tag_groups.items()):
            group_menu = QMenu(group, parent=self._view_menu_all_fields)
            for key in sorted(items):
                field_name = f"{group}:{key}"
                cb = self._create_checkbox(key, self._view_menu_all_fields, field_name)
                self._add_menu_item(group_menu, cb)
            self._view_menu_all_fields.addMenu(group_menu)

    def _update_presets_menu(self, db: Database):
        self._create_preset("Basic Fields", "Show basic file information", props.get_basic_fields(), db)
        self._create_preset("Image Fields", "Show image file information", props.get_image_fields(), db)
        self._create_preset("All Fields", "Show all available file information", set(self._all_tags), db)

    def _create_preset(self, name: str, tooltip: str, fields: set, database: Database):
        # Remove fields from the presets that are not in this database
        filtered_fields = [f for f in fields if f in database.tags]
        if len(filtered_fields) > 0:
            action = _create_action(self._view_menu_presets, name, self._preset_clicked_event, tooltip=tooltip,
                                    checked=False)
            action.setProperty(self._PROP_FIELD_ID, filtered_fields)
            self._view_menu_presets.addAction(action)
            self._presets_group.addAction(action)
        else:
            app.logger.debug(f"{name} will not be shown as none of the fields are in this database")

    def _raise_view_event(self, event):
        self.view_event.emit(ViewAction.VIEW, ViewType[event])

    def _preset_clicked_event(self, preset_name):
        menu_item = _find_action(preset_name, self._view_menu_presets.actions())
        fields = menu_item.property(self._PROP_FIELD_ID)
        if fields is not None:
            self._hidden_tags.clear()
            for f in self._all_tags:
                if f not in fields:
                    self._hidden_tags.add(f)
                    self._tag_checkboxes[f].setChecked(False)
                else:
                    self._tag_checkboxes[f].setChecked(True)

            # raise the event
            self._raise_field_change_event()

    def _checkbox_click_event(self, field):
        field_id = field.property(self._PROP_FIELD_ID)
        if field.isChecked():
            logging.debug(f"{field_id} was checked by user.")
            self._hidden_tags.remove(field_id)
        else:
            logging.debug(f"{field_id} was un-checked by user.")
            self._hidden_tags.add(field_id)
        self._raise_field_change_event()

    def _raise_field_change_event(self):
        self.view_event.emit(ViewAction.FIELD, [f for f in self._all_tags if f not in self._hidden_tags])

    @staticmethod
    def _add_menu_item(parent: QMenu, widget):
        _action = _create_action(parent, "", tooltip=widget.toolTip(), widget=widget)
        _action.setDefaultWidget(widget)
        parent.addAction(_action)


class DatabaseMenu(QMenu, HasDatabaseDisplaySupport):
    database_event = pyqtSignal(DBAction, "PyQt_PyObject")

    _MENU_DB_PATHS = "Database Paths"
    _MENU_DB_HISTORY = "Recently Opened"
    _MENU_DB_BOOKMARKS = "Favorites"

    def show_database(self, database: Database):
        # You can only save to an existing database. Default databases need to be 'saved as'
        self._save.setEnabled(not database.type == DBType.IN_MEMORY)
        self._save_as.setEnabled(True)
        self._reset.setEnabled(not database.type == DBType.IN_MEMORY)
        self._refresh.setEnabled(True)
        self._selective_refresh.setEnabled(True)
        self._add_bookmark.setEnabled(not database.type == DBType.IN_MEMORY)
        self._shut_db.setEnabled(True)
        self._open_search.setEnabled(not database.type == DBType.IN_MEMORY)
        self._shut_search.setEnabled(False)
        self._paths_menu.setEnabled(True)

        _clear_menu(self._paths_menu)
        for count, item in enumerate(database.paths):
            self._paths_menu.addAction(_create_action(self, item, func=self._paths_change_event,
                                                      icon=views.get_mime_type_icon_name(item),
                                                      shortcut=f"Ctrl+{count + 1}" if count < 9 else None, checked=True)
                                       )

    def shut_database(self):
        self._save.setEnabled(False)
        self._save_as.setEnabled(False)
        self._reset.setEnabled(False)
        self._refresh.setEnabled(False)
        self._selective_refresh.setEnabled(False)
        self._add_bookmark.setEnabled(False)
        self._shut_db.setEnabled(False)
        self._open_search.setEnabled(False)
        self._shut_search.setEnabled(False)
        _clear_menu(self._paths_menu)
        self._paths_menu.setEnabled(False)

        # Raise Cleanup Events
        self.database_event.emit(DBAction.PATH_CHANGE, [])
        self.database_event.emit(DBAction.SHUT_SEARCH, None)

    @property
    def selected_paths(self) -> list:
        paths = []
        for item in self._paths_menu.actions():
            if item.isChecked():
                paths.append(item.text())
        return paths

    def update_recents(self, recents: list):
        self._update_db_list(self._history_menu, sub_items=recents, icon_name="folder-open-recent")

    def update_bookmarks(self, bookmarks: list):
        self._update_db_list(self._bookmarks_menu, sub_items=bookmarks, icon_name="bookmarks")

    def __init__(self, parent):
        super().__init__("&Database", parent=parent)

        self._save = _create_action(self, DBAction.SAVE, shortcut="Ctrl+S", icon="document-save",
                                    tooltip="Save the exif data of all open paths to the DB",
                                    func=self._db_event, enabled=False)
        self._save_as = _create_action(self, DBAction.SAVE_AS, shortcut="Ctrl+Shift+S", icon="document-save-as",
                                       tooltip="Save the exif data of all open paths to the DB",
                                       func=self._db_event, enabled=False)
        self._shut_db = _create_action(self, DBAction.SHUT_DB, shortcut="Ctrl+W", icon="document-close",
                                       tooltip="Close the database, saving it if required",
                                       func=self._db_event, enabled=False)
        self._shut_search = _create_action(self, DBAction.SHUT_SEARCH, shortcut="Ctrl+Shift+W", enabled=False,
                                           tooltip="Close the search results and switch back to database browsing",
                                           func=self._db_search_event, icon="view-close-symbolic")
        self._open_search = _create_action(self, DBAction.OPEN_SEARCH, shortcut="F3", enabled=False,
                                           tooltip="Start Searching this database using SQL statements",
                                           func=self._db_search_event, icon="folder-saved-search")
        self._refresh = _create_action(self, DBAction.REFRESH, shortcut="F5", icon="view-refresh",
                                       tooltip="Reload the exif data for the all the database paths from disk",
                                       func=self._db_event, enabled=False)
        self._selective_refresh = _create_action(self, DBAction.REFRESH_SELECTED, shortcut="Shift+F5",
                                                 icon="view-refresh", func=self._selective_refresh_event, enabled=False,
                                                 tooltip="Reload the exif data for the the selected "
                                                         "database paths from disk")
        self._reset = _create_action(self, DBAction.RESET, icon="view-restore",
                                     tooltip="Reset this database",
                                     func=self._db_event, enabled=False)
        self._add_bookmark = _create_action(self, DBAction.BOOKMARK, icon="bookmark",
                                            tooltip="Add or remove this database from favorites",
                                            func=self._db_event, enabled=False)
        self._open_db = _create_action(self, DBAction.OPEN_DB, shortcut="Ctrl+D",
                                       icon="database-open", func=self._db_event,
                                       tooltip="Open a non registered private database")

        self._paths_menu = QMenu(self._MENU_DB_PATHS, self)
        self._paths_menu.setIcon(QIcon.fromTheme("database-paths"))
        self._history_menu = QMenu(self._MENU_DB_HISTORY, self)
        self._history_menu.setIcon(QIcon.fromTheme("folder-open-recent"))
        self._bookmarks_menu = QMenu(self._MENU_DB_BOOKMARKS, self)
        self._bookmarks_menu.setIcon(QIcon.fromTheme("bookmark"))

        self._create_menu()

    def _create_menu(self):
        self.addAction(self._save)
        self.addAction(self._save_as)
        self.addAction(self._shut_db)
        self.addSeparator()
        self.addAction(self._open_search)
        self.addAction(self._shut_search)
        self.addSeparator()
        self.addAction(self._refresh)
        self.addAction(self._selective_refresh)
        self.addAction(self._reset)
        self.addAction(self._add_bookmark)
        self.addSeparator()
        self.addMenu(self._paths_menu)
        self.addSeparator()
        self.addAction(self._open_db)
        self.addSeparator()
        self.addMenu(self._history_menu)
        self.addMenu(self._bookmarks_menu)

    def _update_db_list(self, menu: QMenu, sub_items: list, icon_name: str):
        _clear_menu(menu)
        for path in sub_items:
            menu.addAction(_create_action(self, path, func=self._open_db_event, icon=icon_name))

    def _paths_change_event(self, _):
        self.database_event.emit(DBAction.PATH_CHANGE, self.selected_paths)

    def _open_db_event(self, db_to_open):
        self.database_event.emit(DBAction.OPEN_DB, db_to_open)

    def _db_event(self, action):
        self.database_event.emit(DBAction(action), None)

    def _selective_refresh_event(self, _):
        self.database_event.emit(DBAction.REFRESH_SELECTED, self.selected_paths)

    def _db_search_event(self, event):
        match event:
            case DBAction.OPEN_SEARCH:
                self.database_event.emit(DBAction.OPEN_SEARCH, self.selected_paths)
                self._set_searching_available(False)
            case DBAction.SHUT_SEARCH:
                self.database_event.emit(DBAction.SHUT_SEARCH, self.selected_paths)
                self._set_searching_available(True)
            case _:
                app.logger.warning(f"Unexpected event {event} received")

    def _set_searching_available(self, value: bool):
        self._open_search.setEnabled(value)
        self._shut_search.setEnabled(not value)


class HelpMenu(QMenu):
    help_event = pyqtSignal(MediaLibAction)

    LOG_DEBUG = "DEBUG"
    LOG_INFO = "INFO"
    LOG_WARNING = "WARNING"
    LOG_ERROR = "ERROR"

    def __init__(self, parent):
        super().__init__("&Help", parent)
        self._log_menu = QMenu("Set Application Log Level", parent)
        self._log_menu.setIcon(QIcon.fromTheme("text-x-generic"))
        self._log_level_group = QActionGroup(self._log_menu)

        self._debug = _create_action(parent, self.LOG_DEBUG, self._log_level_changed,
                                     tooltip="Display all application logs", checked=False)
        self._info = _create_action(parent, self.LOG_INFO, self._log_level_changed,
                                    tooltip="Do not show debug logs", checked=False)
        self._warning = _create_action(parent, self.LOG_WARNING, self._log_level_changed,
                                       tooltip="Display warnings and errors only", checked=False)
        self._error = _create_action(parent, self.LOG_ERROR, self._log_level_changed,
                                     tooltip="Only show application errors", checked=False)
        self._create_menu()

    def _create_menu(self):
        self._log_level_group.setExclusive(True)
        self._log_level_group.addAction(self._debug)
        self._log_level_group.addAction(self._info)
        self._log_level_group.addAction(self._warning)
        self._log_level_group.addAction(self._error)

        self._log_menu.addActions([self._debug, self._info, self._warning, self._error])
        self.set_application_log_level(appsettings.get_log_level())

        self.addAction(_create_action(self, MediaLibAction.OPEN_GIT, self._raise_menu_event,
                                      icon="folder-git", tooltip="Visit this project on GitHub"))
        self.addMenu(self._log_menu)
        self.addSeparator()
        self.addAction(_create_action(self, MediaLibAction.ABOUT, self._raise_menu_event, icon="help-about",
                                      tooltip="About this application"))

    def _raise_menu_event(self, action):
        self.help_event.emit(MediaLibAction(action))

    def _log_level_changed(self, log_level):
        match log_level:
            case self.LOG_ERROR:
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


class FileMenu(QMenu):
    file_event = pyqtSignal(MediaLibAction)

    def __init__(self, parent):
        super().__init__("&File", parent)
        self.addAction(_create_action(self, MediaLibAction.OPEN_FILE, shortcut="Ctrl+O", func=self._raise_menu_event,
                                      icon="document-open", tooltip="Open a file to view its exif data"))
        self.addAction(_create_action(self, MediaLibAction.OPEN_PATH, shortcut="Ctrl+D", func=self._raise_menu_event,
                                      tooltip="Open a directory to view info of all supported files in it",
                                      icon="document-open-folder"))
        self.addSeparator()
        self.addAction(_create_action(self, MediaLibAction.SETTINGS, func=self._raise_menu_event, shortcut="Ctrl+,",
                                      icon="preferences-system", tooltip=f"Open {app.__NAME__} Preferences"))
        self.addSeparator()
        self.addAction(_create_action(self, MediaLibAction.APP_EXIT, func=self._raise_menu_event,
                                      shortcut="Ctrl+Q", icon="application-exit", tooltip=f"Quit {app.__NAME__}"))

    def _raise_menu_event(self, action):
        self.file_event.emit(MediaLibAction(action))


class AppMenuBar(QMenuBar, HasDatabaseDisplaySupport):
    view_event = pyqtSignal(ViewAction, "PyQt_PyObject")
    db_event = pyqtSignal(DBAction, "PyQt_PyObject")
    medialib_event = pyqtSignal(MediaLibAction)

    def __init__(self, plugins: list):
        super().__init__()
        self._db_menu = DatabaseMenu(self)
        self._db_menu.database_event.connect(self.db_event)
        self._view_menu = ViewMenu(self)
        self._view_menu.view_event.connect(self.view_event)
        self._help_menu = HelpMenu(self)
        self._help_menu.help_event.connect(self.medialib_event)
        self._file_menu = FileMenu(self)
        self._file_menu.file_event.connect(self.medialib_event)

        self.addMenu(self._file_menu)
        self.addMenu(self._db_menu)
        self.addMenu(self._view_menu)
        if len(plugins) > 0:
            self.addMenu(self._create_window_menu(plugins))
        self.addMenu(self._help_menu)

    def update_recents(self, recents: list):
        self._db_menu.update_recents(recents)

    def update_bookmarks(self, bookmarks: list):
        self._db_menu.update_bookmarks(bookmarks)

    def show_database(self, database: Database):
        self._view_menu.show_database(database)
        self._db_menu.show_database(database)

    def shut_database(self):
        self._view_menu.shut_database()
        self._db_menu.shut_database()

    def get_selected_database_paths(self):
        return self._db_menu.selected_paths

    def update_available_views(self, available_views: list):
        self._view_menu.update_available_views(available_views)

    def _create_window_menu(self, plugins: list):
        window_menu = QMenu("&Window", self)

        for plugin in plugins:
            pl_action = plugin.toggleViewAction()
            pl_action.setToolTip(plugin.statustip)
            pl_action.setShortcut(plugin.shortcut)
            pl_action.setIcon(plugin.icon)
            window_menu.addAction(pl_action)

        return window_menu
