from abc import abstractmethod
from dataclasses import dataclass, field

from PyQt6.QtCore import QRegularExpression, QSortFilterProxyModel, pyqtSignal, QAbstractTableModel, \
    QModelIndex, Qt, QVariant, QPersistentModelIndex, QAbstractItemModel, QObject
from PyQt6.QtGui import QStandardItem, QIcon, QBrush, QColor
from PyQt6.QtWidgets import QTableView, QAbstractItemView, QWidget, QVBoxLayout, QTreeView, QLabel

import app
from app.actions import ViewAction, ViewContextMenu
from app.collection import props
from app.collection.ds import Collection, HasCollectionDisplaySupport
from app.plugins.framework import FileData

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


@dataclass
class ViewItem:
    icon: QIcon | None
    parent: ...  # dict | None
    data: dict | None
    row: int = 0
    text: str = ""
    _children: list = field(default_factory=list)
    fetched: int = 0
    file_data: FileData | None = None

    @property
    def display_text(self):
        s = "items" if self.row_count > 1 else "item"
        return f"{self.text}  ({self.row_count} {s})"

    @property
    def children(self):
        return self._children

    @property
    def is_leaf_item(self):
        return self.row_count == 0 and self.data is not None

    @property
    def row_count(self):
        return len(self._children)

    def add_child(self, child):
        child.parent = self
        child.row = self.row_count
        self._children.append(child)


class ViewManager(QWidget, HasCollectionDisplaySupport):
    item_click = pyqtSignal(dict, str)

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

    def contextMenuEvent(self, a0):
        sel = self._current_view.get_all_selected_items()
        file_available = (len(sel) == 1 and
                          props.FIELD_COLLECTION_FILEDATA in sel and
                          sel[props.FIELD_COLLECTION_FILEDATA].sourcefile_available)
        self._context_menu.show_menu(a0, self._file_ops_available, file_available)

    def _item_clicked(self, item_data: dict):
        _path = item_data[props.FIELD_COLLECTION_PATH]
        self.item_click.emit(item_data, _path)

    def show_data(self, model_data: list, fields: list | None, group_by: list | None = None):
        # Preprocess the data and insert the path into every record
        app.logger.debug("Preprocessing data for view")
        self._preprocess(model_data)
        app.logger.debug(f"Preprocessing data for view complete. File ops available = {self._file_ops_available}")
        self._fields = fields
        self._group_by = group_by
        # Create an appropriate view for the data and update the view
        self._load_view()

    def _context_menu_requested_event(self, action, event_args):
        app.logger.debug(f"Context Menu event - {action} -- {event_args}")
        match action:
            case ViewAction.FIELD:
                self._fields = event_args
                app.logger.debug(f"Show fields changed")
                self._load_view()

    def _load_view(self):
        # Create an appropriate view for the data
        if len(self._model_data) == 1:
            app.logger.debug("Will use a Columnar View for the supplied data set")
            view_type = ColumnView
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

        self._current_view.show_data(self._model_data, self._fields, self._group_by)

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


class View(QObject):
    item_click = pyqtSignal(dict, str)

    @abstractmethod
    def show_data(self, view_items: list, fields: list | None, group_by: list | None):
        raise NotImplemented

    @abstractmethod
    def clear(self):
        raise NotImplemented

    @abstractmethod
    def item_model(self):
        raise NotImplemented

    def get_all_selected_items(self):
        selected = self._get_selection_items(self.selectionModel().selectedRows())
        return selected

    @staticmethod
    def _create_proxy_model(parent, model):
        proxy_model = QSortFilterProxyModel(parent)
        proxy_model.setSourceModel(model)
        return proxy_model

    def _clicked(self, index):
        selected = self._get_selection_items([index])
        for sel in selected:
            _path = sel[props.FIELD_COLLECTION_PATH]
            self.item_click.emit(selected[0], _path)

    def _get_selection_items(self, proxy_model_indices: list):
        selection = []
        for index in proxy_model_indices:
            source_index = self.item_model().mapToSource(index)
            item = self.item_model().sourceModel().data(source_index, Qt.ItemDataRole.UserRole)
            if isinstance(item, ViewItem) and item.is_leaf_item:
                selection.append(item.data)
        return selection


class TableView(QTableView, View):
    item_click = pyqtSignal(dict, str)

    def show_data(self, view_items: list, fields: list, group_by: list):
        if group_by is not None:
            raise ValueError("Table view does not support groups")
        p_model = self.TableModel(view_items, fields)
        self.setModel(self._create_proxy_model(self, p_model))

    def clear(self):
        self.setModel(None)

    def item_model(self):
        return self.model()

    # https://stackoverflow.com/questions/57764723/make-an-active-search-with-qlistwidget
    # https://stackoverflow.com/questions/20563826/pyqt-qtableview-search-by-hiding-rows

    class TableModel(QAbstractTableModel):
        def __init__(self, table_items: list, fields: list):
            super().__init__()
            self._exif_data = table_items
            self._exif_cols = fields
            self._QStandardItem_cache = {}

        def rowCount(self, parent: QModelIndex = None) -> int:
            return len(self._exif_data)

        def columnCount(self, parent: QModelIndex = None) -> int:
            return len(self._exif_cols)

        def headerData(self, p_int, p_orientation, role=None):
            if role == Qt.ItemDataRole.DisplayRole and p_orientation == Qt.Orientation.Horizontal:
                return self._exif_cols[p_int]
            return QVariant()

        def data(self, index: QModelIndex, role: int = None):
            item = self.item(index)
            if item is None or isinstance(item, QVariant):
                return QVariant()
            if role == Qt.ItemDataRole.UserRole:
                if 0 <= index.row() < len(self._exif_data):
                    return self._exif_data[index.row()]
                else:
                    return QVariant()
            return item.data(role)

        def item(self, index: QModelIndex):
            if not index.isValid():
                return QVariant()

            p_index = QPersistentModelIndex(index)
            item = self._QStandardItem_cache.get(p_index)
            if item is None:
                row = self._exif_data[index.row()]
                col = self._exif_cols[index.column()]
                if col in row.data:
                    item = QStandardItem(str(row.data[col]))
                    if index.column() == 0 and row.icon:
                        item.setIcon(row.icon)
                if item is not None:
                    self._QStandardItem_cache[p_index] = item
            return item

    def __init__(self, parent):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.verticalHeader().setHighlightSections(False)
        self.verticalHeader().setSectionsMovable(True)
        self.verticalHeader().setSectionsClickable(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setSectionsClickable(True)
        self.setSortingEnabled(True)
        self.clicked.connect(self._clicked)


class ColumnView(TableView):

    def __init__(self, parent):
        super().__init__(parent)
        # Column View does not send back user clicks
        self.clicked.disconnect()
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(True)

    def show_data(self, view_items: list, fields: list, group_by: list):
        if len(view_items) != 1:
            raise ValueError("Column Model can only be shown for single items")
        if group_by is not None:
            raise ValueError("Table view does not support groups")

        p_model = self.ColumnModel(view_items, fields)
        self.setModel(self._create_proxy_model(self, p_model))

    class ColumnModel(QAbstractTableModel):

        def __init__(self, table_items: list, fields: list):
            super().__init__()
            self._exif_data = table_items
            self._exif_cols = fields
            self._QStandardItem_cache = {}

        def rowCount(self, parent=...):
            return len(self._exif_cols)

        def columnCount(self, parent=...):
            return 1

        def headerData(self, section, orientation, role=...):
            if role == Qt.ItemDataRole.DisplayRole:
                if orientation == Qt.Orientation.Vertical:
                    return self._exif_cols[section]
                elif orientation == Qt.Orientation.Horizontal and section == 0:
                    return "Value"
                else:
                    return QVariant()
            return QVariant()

        def data(self, index, role=...):
            item = self.item(index)
            if item is None or isinstance(item, QVariant):
                return QVariant()
            return item.data(role)

        def item(self, index: QModelIndex):
            if not index.isValid():
                return QVariant()

            p_index = QPersistentModelIndex(index)
            item = self._QStandardItem_cache.get(p_index)
            if item is None:
                key = self._exif_cols[index.row()]
                if key in self._exif_data[0].data:
                    item = QStandardItem(str(self._exif_data[0].data[key]))
                else:
                    item = QVariant()
                if item is not None:
                    self._QStandardItem_cache[p_index] = item
            return item


class SpanningTreeview(QTreeView, View):
    item_click = pyqtSignal(dict, str)

    def show_data(self, view_items: list, fields: list | None, group_by: list):
        p_model = self.TreeModel(view_items, fields, group_by)
        proxy_model = self._create_proxy_model(self, p_model)
        proxy_model.setRecursiveFilteringEnabled(True)
        self.setModel(proxy_model)

    def clear(self):
        self.setModel(None)

    def item_model(self):
        return self.model()

    def __init__(self, parent):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)  # Allows for scrolling optimizations.
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.setSortingEnabled(True)
        self.clicked.connect(self._clicked)
        self._grouping = []

    def drawRow(self, painter, options, index):
        if index.isValid():
            item = self.model().data(index, Qt.ItemDataRole.UserRole)
            if not item.is_leaf_item:
                self.setFirstColumnSpanned(index.row(), self.model().parent(index), True)
        super().drawRow(painter, options, index)

    class TreeModel(QAbstractItemModel):
        _NODE_FOLDER = QIcon.fromTheme("folder")
        _GROUP_BG = QBrush(QColor(121, 186, 212, 125))
        _UNKNOWN = "N/A"

        def __init__(self, model_data: list, fields: list, group_by: list):
            super().__init__()
            app.logger.debug("Building tree model")
            self._root_node = self._build_tree("", group_by, model_data)
            app.logger.debug("Model built")
            self._exif_cols = fields

        def rowCount(self, parent=...):
            if parent.isValid():
                return parent.internalPointer().row_count
            return self._root_node.row_count

        def hasChildren(self, parent=...):
            if parent.isValid():
                item = parent.internalPointer()
            else:
                item = self._root_node
            return item.row_count > 0

        def canFetchMore(self, parent):
            if parent.isValid():
                item = parent.internalPointer()
            else:
                item = self._root_node
            return item.row_count > 0

        def columnCount(self, parent=...):
            return len(self._exif_cols)

        def index(self, row, column, parent=...):
            if not parent or not parent.isValid():
                node = self._root_node
            else:
                node = parent.internalPointer()

            if not self.hasIndex(row, column, parent):
                return QModelIndex()

            if 0 <= row < node.row_count:
                child = node.children[row]
                return self.createIndex(row, column, child)
            return QModelIndex()

        def data(self, index, role=...):
            if not index.isValid():
                return None
            node = index.internalPointer()
            column = index.column()
            if role == Qt.ItemDataRole.DisplayRole:
                if not node.is_leaf_item and index.column() > 0:
                    return None
                elif not node.is_leaf_item and index.column() == 0:
                    return node.display_text
                else:
                    key = self._exif_cols[index.column()]
                    if key in node.data:
                        return node.data[key]

            elif role == Qt.ItemDataRole.DecorationRole and index.column() == 0:
                return node.icon

            elif role == Qt.ItemDataRole.BackgroundRole and not node.is_leaf_item:
                return self._GROUP_BG

            elif role == Qt.ItemDataRole.UserRole:
                return node

            return None

        def parent(self, index: QModelIndex):
            if index.isValid():
                parent = index.internalPointer().parent
                if parent:
                    return self.createIndex(parent.row, 0, parent)
            return QModelIndex()

        def headerData(self, section, orientation, role=...):
            if role == Qt.ItemDataRole.DisplayRole:
                if orientation == Qt.Orientation.Horizontal:
                    return self._exif_cols[section]
                elif orientation == Qt.Orientation.Vertical:
                    return QVariant()

        def _build_tree(self, group_path: str, grouping: list, data: list, grouping_index: int = 0):
            current_node = ViewItem(icon=self._NODE_FOLDER, parent=None, data=None, text=group_path)
            if grouping_index < len(grouping):
                group = grouping[grouping_index]
                keys = {}
                for item in data:
                    if group in item.data:
                        key = item.data[group]
                    else:
                        key = self._UNKNOWN

                    if key not in keys:
                        keys[key] = []
                    keys[key].append(item)

                for key, value in keys.items():
                    child_node = self._build_tree(key, grouping, value, grouping_index + 1)
                    current_node.add_child(child_node)
            else:
                for item in data:
                    current_node.add_child(item)
            return current_node

# -----------------------_TESTING CODE------------------------------
# db = Collection.open_db("/mnt/dev/testing/Medialib/threaded-scan/")
# main_model_data = []
# for main_path in db.paths:
#     main_model_data.append(ModelData(data=db.data([main_path]), path=main_path))
#
# ___app = QApplication([])
# view_manager = ViewManager(None)
# view_manager.show_data(main_model_data, db.tags, group_by=["Composite:ImageSize"])
# view_manager.show()
# sys.exit(___app.exec())
