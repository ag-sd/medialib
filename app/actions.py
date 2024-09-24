import logging
from enum import StrEnum
from functools import partial

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QActionGroup, QContextMenuEvent
from PyQt6.QtWidgets import QMenuBar, QMenu, QCheckBox

import app
from app import appsettings, apputils
from app.collection import props
from app.collection.ds import Collection, HasCollectionDisplaySupport
from app.collection.props import DBType


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
    REINDEX_COLLECTION = "Re-index"
    RESET = "Reset"
    BOOKMARK = "Add or Remove Favorite"
    OPEN_DB = "Open..."
    OPEN_PRIVATE_DB = "Open Private Collection..."
    SHUT_DB = "Close"
    PATH_CHANGE = "Path Change"


class ViewContextMenuAction(StrEnum):
    VIEW = "View"
    COLUMN = "Column"
    GROUP_BY = "Group By"
    OPEN = "Open File"
    EXPLORE = "Open in Explorer..."
    FS_VIEW = "File System View"
    EXPORT = "Export data..."


class ViewContextMenu(QMenu, HasCollectionDisplaySupport):
    view_event = pyqtSignal(StrEnum, "PyQt_PyObject")

    _PROP_FIELD_ID = "field-ids"
    _PROP_SOURCE = "source"

    def show_collection(self, collection: Collection):
        # Now Build the new menus
        self._update_presets_menu(collection)
        self._show_field_selection(collection.tags, self._vm_columns, True, ViewContextMenuAction.COLUMN)
        self._show_field_selection(collection.tags, self._vm_groupby, False, ViewContextMenuAction.GROUP_BY)
        self._vm_presets.setEnabled(True)
        self._vm_columns.setEnabled(True)
        self._vm_groupby.setEnabled(True)
        self._hidden_tags = set()
        self._all_tags = collection.tags
        self._group_by = []
        self._tag_checkboxes = {}

    def shut_collection(self):
        self._vm_presets.setEnabled(False)
        self._vm_columns.setEnabled(False)
        self._vm_groupby.setEnabled(False)
        self._view_fs.setChecked(False)
        self._hidden_tags = set()
        self._all_tags = []
        self._group_by = []
        self._tag_checkboxes = {}

    def show_menu(self, cm_args: QContextMenuEvent, file_ops: bool, file_exists: bool):
        self._open.setVisible(file_ops)
        self._open.setEnabled(file_exists)
        self._explore.setVisible(file_ops)
        self._explore.setEnabled(file_exists)
        self._view_fs.setVisible(file_ops)
        self._view_fs.setEnabled(file_ops)
        if not file_ops and self._view_fs.isChecked():
            self._view_fs.setChecked(False)
        self.exec(cm_args.globalPos())

    def set_available_fields(self, available_fields: list):
        self._all_tags = available_fields

    def is_fs_view_requested(self):
        return self._view_fs.isEnabled() and self._view_fs.isChecked()

    def _show_field_selection(self, fields: list, reference_menu: QMenu, items_enabled: bool, event_source: ViewContextMenuAction):
        reference_menu.clear()
        groups = apputils.create_tag_groups(fields)
        if props.DB_TAG_GROUP_DEFAULT in groups:
            for key in groups[props.DB_TAG_GROUP_DEFAULT]:
                cb = self._create_checkbox(key, reference_menu, key, event_source, checked=items_enabled)
                self._add_menu_item(reference_menu, cb)
            reference_menu.addSeparator()
            del groups[props.DB_TAG_GROUP_DEFAULT]

        for group, items in sorted(groups.items()):
            group_menu = QMenu(group, parent=reference_menu)
            for key in sorted(items):
                field_name = f"{group}:{key}"
                cb = self._create_checkbox(key, reference_menu, field_name, event_source, checked=items_enabled)
                self._add_menu_item(group_menu, cb)
            reference_menu.addMenu(group_menu)

    def __init__(self, parent):
        super().__init__("&View", parent=parent)
        self._combo_stylesheet = f"padding: {self.fontMetrics().horizontalAdvance('  ')}px; text-align:left;"
        self._hidden_tags = set()
        self._all_tags = []
        self._group_by = []
        self._tag_checkboxes = {}
        self._vm_columns = QMenu("Columns", self)
        self._vm_columns.setIcon(QIcon.fromTheme("view-file-columns"))
        self._vm_presets = QMenu("Preset Views", self)
        self._vm_presets.setIcon(QIcon.fromTheme("document-save"))
        self._vm_groupby = QMenu("Group By", self)
        self._vm_groupby.setIcon(QIcon.fromTheme("view-list-tree"))
        self._presets_group = QActionGroup(self._vm_presets)
        self._presets_group.setExclusive(True)
        self._open = apputils.create_action(self, ViewContextMenuAction.OPEN, icon="document-open",
                                            tooltip="Open in default application",
                                            func=self._raise_view_event, enabled=False)
        self._explore = apputils.create_action(self, ViewContextMenuAction.EXPLORE, icon="system-file-manager",
                                               tooltip="Open in shell explorer",
                                               func=self._raise_view_event, enabled=False)
        self._view_fs = apputils.create_action(self, ViewContextMenuAction.FS_VIEW, icon="view-list-tree",
                                               tooltip="View results in file hierarchy",
                                               func=self._raise_view_event, enabled=False, checked=False)
        self._export = apputils.create_action(self, ViewContextMenuAction.EXPORT, icon="document-export",
                                              tooltip="Export data to file",
                                              func=self._raise_view_event, enabled=True)

        self._init_default_menu()

    def _init_default_menu(self):
        self.addAction(self._open)
        self.addAction(self._explore)
        self.addAction(self._view_fs)
        self.addSeparator()
        self.addMenu(self._vm_columns)
        self.addMenu(self._vm_groupby)
        self.addMenu(self._vm_presets)
        self.addSeparator()
        self.addAction(self._export)

    def _create_checkbox(self, text, parent, field_name, source, checked=False):
        cb = QCheckBox(text, parent)
        cb.setToolTip(f"Show/Hide {text} in the view")
        cb.setStyleSheet(self._combo_stylesheet)
        cb.clicked.connect(partial(self._checkbox_click_event, cb))
        cb.setProperty(self._PROP_FIELD_ID, field_name)
        cb.setProperty(self._PROP_SOURCE, source)
        cb.setChecked(checked)
        self._tag_checkboxes[field_name] = cb
        return cb

    def _update_presets_menu(self, db: Collection):
        self._vm_presets.clear()
        self._create_preset("Basic Fields", "Show basic file information", props.get_basic_fields(), db)
        self._create_preset("Image Fields", "Show image file information", props.get_image_fields(), db)
        self._create_preset("All Fields", "Show all available file information", set(self._all_tags), db)

    def _create_preset(self, name: str, tooltip: str, fields: set, collection: Collection):
        # Remove fields from the presets that are not in this collection
        filtered_fields = [f for f in fields if f in collection.tags]
        if len(filtered_fields) > 0:
            action = apputils.create_action(self._vm_presets, name, self._preset_clicked_event, tooltip=tooltip,
                                            checked=False)
            action.setProperty(self._PROP_FIELD_ID, filtered_fields)
            self._vm_presets.addAction(action)
            self._presets_group.addAction(action)
        else:
            app.logger.debug(f"{name} will not be shown as none of the fields are in this collection")

    def _raise_view_event(self, event):
        self.view_event.emit(event, None)

    def _preset_clicked_event(self, preset_name):
        menu_item = _find_action(preset_name, self._vm_presets.actions())
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
        source = field.property(self._PROP_SOURCE)

        match source:
            case ViewContextMenuAction.GROUP_BY:
                if field.isChecked():
                    logging.debug(f"{field_id} was added to group-by by user.")
                    self._group_by.append(field_id)
                else:
                    logging.debug(f"{field_id} was removed from group-by by user.")
                    self._group_by.remove(field_id)
                self.view_event.emit(ViewContextMenuAction.GROUP_BY, self._group_by)
            case ViewContextMenuAction.COLUMN:
                if field.isChecked():
                    logging.debug(f"{field_id} was checked by user.")
                    self._hidden_tags.remove(field_id)
                else:
                    logging.debug(f"{field_id} was un-checked by user.")
                    self._hidden_tags.add(field_id)
                self.view_event.emit(ViewContextMenuAction.COLUMN, [f for f in self._all_tags if f not in self._hidden_tags])

    @staticmethod
    def _add_menu_item(parent: QMenu, widget):
        _action = apputils.create_action(parent, "", tooltip=widget.toolTip(), widget=widget)
        _action.setDefaultWidget(widget)
        parent.addAction(_action)


class CollectionMenu(QMenu, HasCollectionDisplaySupport):
    collection_event = pyqtSignal(DBAction, "PyQt_PyObject")

    _MENU_DB_PATHS = "Collection Paths"
    _MENU_DB_HISTORY = "Recently Opened"
    _MENU_DB_BOOKMARKS = "Favorites"

    def show_collection(self, collection: Collection):
        # You can only save to an existing collection. Default collections need to be 'saved as'
        self._save.setEnabled(not collection.type == DBType.IN_MEMORY)
        self._reset.setEnabled(not collection.type == DBType.IN_MEMORY)
        self._add_bookmark.setEnabled(not (collection.type == DBType.IN_MEMORY or collection.is_private))
        self._save_as.setEnabled(True)
        self._refresh.setEnabled(True)
        self._reindex.setEnabled(True)
        self._selective_refresh.setEnabled(True)
        self._shut_db.setEnabled(True)
        self._paths_menu.setEnabled(True)

        _clear_menu(self._paths_menu)
        for count, item in enumerate(collection.paths):
            self._paths_menu.addAction(apputils.create_action(self, item, func=self._paths_change_event,
                                                              icon=apputils.get_mime_type_icon_name(item),
                                                              shortcut=f"Ctrl+{count + 1}" if count < 9 else None,
                                                              checked=True)
                                       )

    def shut_collection(self):
        self._save.setEnabled(False)
        self._save_as.setEnabled(False)
        self._reset.setEnabled(False)
        self._refresh.setEnabled(False)
        self._reindex.setEnabled(False)
        self._selective_refresh.setEnabled(False)
        self._add_bookmark.setEnabled(False)
        self._shut_db.setEnabled(False)
        _clear_menu(self._paths_menu)
        self._paths_menu.setEnabled(False)

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
        super().__init__("&Collection", parent=parent)

        self._save = apputils.create_action(self, DBAction.SAVE, shortcut="Ctrl+S", icon="document-save",
                                            tooltip="Save the exif data of all open paths to the DB",
                                            func=self._db_event, enabled=False)
        self._save_as = apputils.create_action(self, DBAction.SAVE_AS, shortcut="Ctrl+Shift+S", icon="document-save-as",
                                               tooltip="Save the exif data of all open paths to the DB",
                                               func=self._db_event, enabled=False)
        self._shut_db = apputils.create_action(self, DBAction.SHUT_DB, shortcut="Ctrl+W", icon="document-close",
                                               tooltip="Close the collection, saving it if required",
                                               func=self._db_event, enabled=False)
        self._refresh = apputils.create_action(self, DBAction.REFRESH, shortcut="F5", icon="view-refresh",
                                               tooltip="Reload the exif data for the all the collection paths from disk",
                                               func=self._db_event, enabled=False)
        self._selective_refresh = apputils.create_action(self, DBAction.REFRESH_SELECTED, shortcut="Shift+F5",
                                                         icon="view-refresh", func=self._selective_refresh_event,
                                                         enabled=False,
                                                         tooltip="Reload the exif data for the the selected "
                                                                 "collection paths from disk")
        self._reindex = apputils.create_action(self, DBAction.REINDEX_COLLECTION, shortcut=None, icon="view-refresh",
                                               tooltip="Reindex this collection for faster searches",
                                               func=self._db_event, enabled=False)
        self._reset = apputils.create_action(self, DBAction.RESET, icon="view-restore",
                                             tooltip="Reset this collection",
                                             func=self._db_event, enabled=False)
        self._add_bookmark = apputils.create_action(self, DBAction.BOOKMARK, icon="bookmark",
                                                    tooltip="Add or remove this collection from favorites",
                                                    func=self._db_event, enabled=False)
        self._open_db = apputils.create_action(self, DBAction.OPEN_DB, shortcut="Ctrl+D",
                                               icon="collection-open", func=self._db_event,
                                               tooltip="Open a collection")
        self._open_private_db = apputils.create_action(self, DBAction.OPEN_PRIVATE_DB, shortcut=None,
                                                       icon="collection-open", func=self._db_event,
                                                       tooltip="Open a collection which will not be recorded")
        self._open_private_db.setVisible(False)

        self._paths_menu = QMenu(self._MENU_DB_PATHS, self)
        self._paths_menu.setIcon(QIcon.fromTheme("collection-paths"))
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
        self.addAction(self._refresh)
        self.addAction(self._selective_refresh)
        self.addAction(self._reset)
        self.addAction(self._reindex)
        self.addSeparator()
        self.addMenu(self._paths_menu)
        self.addSeparator()
        self.addAction(self._open_db)
        self.addAction(self._open_private_db)
        self.addSeparator()
        self.addMenu(self._history_menu)
        self.addMenu(self._bookmarks_menu)
        self.addAction(self._add_bookmark)

    def _update_db_list(self, menu: QMenu, sub_items: list, icon_name: str):
        _clear_menu(menu)
        for path in sub_items:
            menu.addAction(apputils.create_action(self, path, func=self._open_db_event, icon=icon_name))

    def _paths_change_event(self, _):
        self.collection_event.emit(DBAction.PATH_CHANGE, self.selected_paths)

    def _open_db_event(self, db_to_open):
        self.collection_event.emit(DBAction.OPEN_DB, db_to_open)

    def _db_event(self, action):
        self.collection_event.emit(DBAction(action), None)

    def _selective_refresh_event(self, _):
        self.collection_event.emit(DBAction.REFRESH_SELECTED, self.selected_paths)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self._open_private_db.setVisible(True)

    def hideEvent(self, a0):
        self._open_private_db.setVisible(False)


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

        self._debug = apputils.create_action(parent, self.LOG_DEBUG, self._log_level_changed,
                                             tooltip="Display all application logs", checked=False)
        self._info = apputils.create_action(parent, self.LOG_INFO, self._log_level_changed,
                                            tooltip="Do not show debug logs", checked=False)
        self._warning = apputils.create_action(parent, self.LOG_WARNING, self._log_level_changed,
                                               tooltip="Display warnings and errors only", checked=False)
        self._error = apputils.create_action(parent, self.LOG_ERROR, self._log_level_changed,
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

        self.addAction(apputils.create_action(self, MediaLibAction.OPEN_GIT, self._raise_menu_event,
                                              icon="folder-git", tooltip="Visit this project on GitHub"))
        self.addMenu(self._log_menu)
        self.addSeparator()
        self.addAction(apputils.create_action(self, MediaLibAction.ABOUT, self._raise_menu_event, icon="help-about",
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

    def set_application_log_level(self, log_level, save_setting: bool = True):
        app.logger.critical(f"Log level changed to {logging.getLevelName(log_level)}")
        app.logger.setLevel(log_level)
        if save_setting:
            appsettings.set_log_level(log_level)
        self._set_log_level_menu_option(log_level)


class FileMenu(QMenu):
    file_event = pyqtSignal(MediaLibAction)

    def __init__(self, parent):
        super().__init__("&File", parent)
        self.addAction(
            apputils.create_action(self, MediaLibAction.OPEN_FILE, shortcut="Ctrl+O", func=self._raise_menu_event,
                                   icon="document-open", tooltip="Open a file to view its exif data"))
        self.addAction(
            apputils.create_action(self, MediaLibAction.OPEN_PATH, shortcut="Ctrl+D", func=self._raise_menu_event,
                                   tooltip="Open a directory to view info of all supported files in it",
                                   icon="document-open-folder"))
        self.addSeparator()
        self.addAction(
            apputils.create_action(self, MediaLibAction.SETTINGS, func=self._raise_menu_event, shortcut="Ctrl+,",
                                   icon="preferences-system", tooltip=f"Open {app.__NAME__} Preferences"))
        self.addSeparator()
        self.addAction(apputils.create_action(self, MediaLibAction.APP_EXIT, func=self._raise_menu_event,
                                              shortcut="Ctrl+Q", icon="application-exit",
                                              tooltip=f"Quit {app.__NAME__}"))

    def _raise_menu_event(self, action):
        self.file_event.emit(MediaLibAction(action))


class AppMenuBar(QMenuBar, HasCollectionDisplaySupport):
    view_event = pyqtSignal(ViewContextMenuAction, "PyQt_PyObject")
    db_event = pyqtSignal(DBAction, "PyQt_PyObject")
    medialib_event = pyqtSignal(MediaLibAction)

    def __init__(self):
        super().__init__()
        self._db_menu = CollectionMenu(self)
        self._db_menu.collection_event.connect(self.db_event)
        self._help_menu = HelpMenu(self)
        self._help_menu.help_event.connect(self.medialib_event)
        self._file_menu = FileMenu(self)
        self._file_menu.file_event.connect(self.medialib_event)
        self._window_menu = QMenu("&Window", self)

        self.addMenu(self._file_menu)
        self.addMenu(self._db_menu)
        self.addMenu(self._window_menu)
        self.addMenu(self._help_menu)

    def update_recents(self, recents: list):
        self._db_menu.update_recents(recents)

    def update_bookmarks(self, bookmarks: list):
        self._db_menu.update_bookmarks(bookmarks)

    def show_collection(self, collection: Collection):
        self._db_menu.show_collection(collection)

    def shut_collection(self):
        self._db_menu.shut_collection()

    def get_selected_collection_paths(self):
        return self._db_menu.selected_paths

    def set_application_log_level(self, log_level, session_only: bool = True):
        self._help_menu.set_application_log_level(log_level, not session_only)

    def register_plugin(self, plugin):
        pl_action = plugin.toggleViewAction()
        pl_action.setToolTip(plugin.statustip)
        pl_action.setShortcut(plugin.shortcut)
        pl_action.setIcon(plugin.icon)
        self._window_menu.addAction(pl_action)
