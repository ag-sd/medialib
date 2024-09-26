from PyQt6.QtCore import pyqtSignal, QSortFilterProxyModel, QRegularExpression
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

import app
from app.actions import ViewContextMenu, ViewContextMenuAction
from app.collection import props
from app.collection.ds import HasCollectionDisplaySupport, Collection
from app.plugins.framework import FileData
from app.presentation.models import BaseViewBuilder
from app.presentation.views import View, ColumnView, TableView, SpanningTreeview, FileSystemTreeView


class ViewManager(QWidget, HasCollectionDisplaySupport):
    item_click = pyqtSignal(dict, "PyQt_PyObject", str)

    def __init__(self, parent):
        super().__init__(parent=parent)
        self._proxy_model: QSortFilterProxyModel = None
        self._base_view = BaseViewBuilder()
        self._fields: list = []
        self._group_by: list = []
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
        self._current_view.find_text(text)

    def show_data(self, model_data: list, fields: list | None, group_by: list | None = None):
        # Preprocess the data and insert the path into every record
        app.logger.debug("Preprocessing data for view")
        self._base_view.build(model_data=model_data)
        app.logger.debug(f"Preprocessing data for view complete. "
                         f"File ops available = {self._base_view.is_file_ops_available}")
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
        self._context_menu.show_menu(a0, self._base_view.is_file_ops_available, file_available)

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
            case ViewContextMenuAction.EXPORT:
                self._current_view.to_dataset()

    def _load_view(self):
        # Create an appropriate view for the data
        if len(self._base_view.data) == 1:
            app.logger.debug("Will use a Columnar View for the supplied data set")
            view_type = ColumnView
        elif self._context_menu.is_fs_view_requested() and self._base_view.is_file_ops_available:
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

        self._current_view.show_data(view_items=self._base_view.data, fields=self._fields, group_by=self._group_by)

        view_details = f"{len(self._base_view.collection_paths)} path{'s' if len(self._base_view.collection_paths) > 1 else ''} displayed"
        row_count = f". {len(self._base_view.data)} items"
        view_details = f"{view_details}{row_count}"
        self._view_details.setText(view_details)
        app.logger.debug(view_details)
