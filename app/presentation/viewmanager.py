from PyQt6.QtCore import pyqtSignal, QSortFilterProxyModel, QRegularExpression
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

import app
from app.actions import ViewContextMenu, ViewContextMenuAction
from app.collection import props
from app.collection.ds import HasCollectionDisplaySupport, Collection
from app.plugins.framework import FileData
from app.presentation.models import ViewItem
from app.presentation.views import View, ColumnView, TableView, SpanningTreeview, FileSystemTreeView

_MIME_ICON_CACHE = {}


def get_mime_type_icon(mime_type_icon_name: str, use_fallback_icon=True):
    if mime_type_icon_name not in _MIME_ICON_CACHE:
        mime_icon = QIcon.fromTheme(mime_type_icon_name)
        if mime_icon is None and use_fallback_icon:
            # Icon was not found, so let's return a generic icon
            app.logger.debug(f"Adding icon for {mime_type_icon_name} to cache")
            if mime_type_icon_name == "text-x-generic":
                app.logger.warning(f"Icon for {mime_type_icon_name} was not found, will return None")
                return None
            return get_mime_type_icon("text-x-generic")
        _MIME_ICON_CACHE[mime_type_icon_name] = mime_icon
    return _MIME_ICON_CACHE[mime_type_icon_name]


class ViewManager(QWidget, HasCollectionDisplaySupport):
    item_click = pyqtSignal(dict, "PyQt_PyObject", str)

    def __init__(self, parent):
        super().__init__(parent=parent)
        self._proxy_model: QSortFilterProxyModel = None
        self._model_data: list = []
        self._fields: list = []
        self._group_by: list = []
        self._collection_paths: list = []
        self._context_menu: ViewContextMenu = ViewContextMenu(self)
        self._current_view = QWidget()
        self._view_layout = QVBoxLayout()
        self._view_layout.setContentsMargins(0, 0, 0, 0)
        self._view_layout.addWidget(self._current_view)
        self.setLayout(self._view_layout)
        self._view_details = QLabel(self)
        self._context_menu.view_event.connect(self._context_menu_requested_event)

    @property
    def view_details_label(self):
        return self._view_details

    def show_collection(self, collection: Collection):
        self._context_menu.show_collection(collection)

    def shut_collection(self):
        if isinstance(self._current_view, View):
            self._current_view.clear()
        self._context_menu.shut_collection()

    def find_text(self, text):
        re = QRegularExpression(text, QRegularExpression.PatternOption.CaseInsensitiveOption)
        if self._proxy_model:
            self._proxy_model.setFilterRegularExpression(re)

    def show_data(self, model_data: list, fields: list | None, group_by: list | None = None):
        # Preprocess the data and insert the path into every record
        app.logger.debug("Preprocessing data for view")
        self._preprocess(model_data)
        app.logger.debug(f"Preprocessing data for view complete. File ops available = {self._file_ops_available}")
        self._fields = fields
        self._group_by = group_by
        self._context_menu.set_available_fields(fields)
        # Create an appropriate view for the data and update the view
        self._load_view()

    def contextMenuEvent(self, a0):
        sel = self._current_view.get_all_selected_items()
        file_available = (len(sel) == 1 and
                          props.FIELD_COLLECTION_FILEDATA in sel and
                          sel[props.FIELD_COLLECTION_FILEDATA].sourcefile_available)
        self._context_menu.show_menu(a0, self._file_ops_available, file_available)

    def _item_clicked(self, item_data: dict, file_data: FileData, collection_path: str):
        self.item_click.emit(item_data, file_data, collection_path)

    def _context_menu_requested_event(self, action, event_args):
        app.logger.debug(f"Context Menu event - {action} -- {event_args}")
        match action:
            case ViewContextMenuAction.COLUMN:
                self._fields = event_args
                self._load_view()
            case ViewContextMenuAction.GROUP_BY:
                self._group_by = event_args
                self._load_view()
            case ViewContextMenuAction.FS_VIEW:
                self._load_view()

    def _load_view(self):
        # Create an appropriate view for the data
        if len(self._model_data) == 1:
            app.logger.debug("Will use a Columnar View for the supplied data set")
            view_type = ColumnView
        elif self._context_menu.is_fs_view_requested() and self._file_ops_available:
            app.logger.debug("Filesystem view requested. Will use that")
            view_type = FileSystemTreeView
        elif not self._group_by or len(self._group_by) == 0:
            app.logger.debug("Will use a Table View for the supplied data set")
            view_type = TableView
        else:
            app.logger.debug("Will use a Spanning Treeview for the supplied data set")
            view_type = SpanningTreeview

        # If the selected view is already being shown, recycle it otherwise create it
        if isinstance(self._current_view, view_type):
            self._current_view.clear()
        else:
            view = view_type(parent=self)
            view.item_click.connect(self._item_clicked)
            self._view_layout.replaceWidget(self._current_view, view)
            del self._current_view
            self._current_view = view

        self._current_view.show_data(view_items=self._model_data, fields=self._fields, group_by=self._group_by)

        view_details = f"{len(self._collection_paths)} path{'s' if len(self._collection_paths) > 1 else ''} displayed"
        row_count = f". {len(self._model_data)} items"
        view_details = f"{view_details}{row_count}"
        self._view_details.setText(view_details)
        app.logger.debug(view_details)

    def _preprocess(self, model_data: list):
        _flat_list = []
        _collection_paths = []
        _file_ops_available = True
        for item in model_data:
            _path = item.path
            _collection_paths.append(_path)
            for entry in item.data:
                file_data = FileData.from_dict(entry, _path)
                icon = None
                if file_data is not None:
                    icon = get_mime_type_icon(file_data.mime_type)
                # Add the path to each entry
                entry[props.FIELD_COLLECTION_PATH] = _path
                entry[props.FIELD_COLLECTION_FILEDATA] = file_data
                _file_ops_available = _file_ops_available and file_data is not None
                _flat_list.append(ViewItem(icon=icon, parent=None, data=entry))
        self._model_data = _flat_list
        self._collection_paths = _collection_paths
        self._file_ops_available = _file_ops_available
