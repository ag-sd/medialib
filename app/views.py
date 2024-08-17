from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, QPersistentModelIndex, QMimeDatabase, \
    QSortFilterProxyModel, QRegularExpression
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt6.QtWidgets import QTreeView, QTableView, QAbstractItemView

import app
from app.database import props

_MIME_ICON_CACHE = {}
_mime_database = QMimeDatabase()


def get_mime_type_icon_name(file: str) -> str:
    mime_type = _mime_database.mimeTypeForFile(file)
    return mime_type.iconName()


def get_mime_type_icon(mime_type_icon_name: str, use_fallback_icon=True):
    # TODO: Test
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
class ModelData:
    data: list
    path: str


class ModelManager:
    def __init__(self):
        super().__init__()
        self._proxy_model = None

    @abstractmethod
    def set_model(self, model_data: list, fields: list | None):
        raise NotImplemented

    def find_text(self, text):
        re = QRegularExpression(text, QRegularExpression.PatternOption.CaseInsensitiveOption)
        if self._proxy_model:
            self._proxy_model.setFilterRegularExpression(re)

    def _create_proxy_model(self, main_model):
        self._proxy_model = QSortFilterProxyModel(self)
        self._proxy_model.setSourceModel(main_model)
        return self._proxy_model


class JsonView(QTreeView, ModelManager):
    class LazyJsonModel(QStandardItemModel):
        """
        This is a lazy model and will only build nodes if the user expands something
        """

        def __init__(self, model_data: list, fields: list = None, parent=None):
            super().__init__(parent)
            self._fields = set(fields) if fields is not None else None
            self.setColumnCount(2)
            self.setHeaderData(0, Qt.Orientation.Horizontal, "Key")
            self.setHeaderData(1, Qt.Orientation.Horizontal, "Data")
            for _node in model_data:
                self._add_child(self.invisibleRootItem(), _node.path, _node.data,
                                get_mime_type_icon(get_mime_type_icon_name(_node.path)))

        def canFetchMore(self, index: QModelIndex):
            """
            Returns true if the item referenced by the index has children, but hasn't been built
            Args:
                index: The item to evaluate
            Returns:
                If item already has children or does not have children at all, return false
            """
            item = self.itemFromIndex(index)
            if item is not None:
                item_data = item.data(Qt.ItemDataRole.UserRole)
                child_count = 0
                if item_data is not None:
                    if isinstance(item_data, dict) or isinstance(item_data, list):
                        child_count = len(item_data)
                # If it already has children or does not have children at all, return false
                return not (item.hasChildren() or child_count == 0)
            return super().rowCount(index)

        def rowCount(self, parent: QModelIndex = ...):
            """
            Returns the row count, if this node has been built, otherwise this function returns 0. If the
            model receives a 0 from this method, it will then call methods to add the children
            Args:
                parent: The node to evaluate
            Returns:
                The current count of children **that are already present under the parent**
            """
            item = self.itemFromIndex(parent)
            if item is not None:
                if item.hasChildren():
                    return item.rowCount()
                else:
                    return 0
            else:
                return super().rowCount(parent)

        def hasChildren(self, parent: QModelIndex = ...):
            """
            Checks if the parent is already built or can be built and returns true if the parent has
            children, or if it can have children, but they havent been added yet.
            Args:
                parent: The node to evaluate
            Returns:
                True if the parent has children or can have children, False otherwise
            """
            item = self.itemFromIndex(parent)
            if item is not None:
                item_data = item.data(Qt.ItemDataRole.UserRole)
                item_can_have_children = False
                if item_data is not None:
                    if isinstance(item_data, dict) or isinstance(item_data, list):
                        item_can_have_children = len(item_data) > 0
                return item.hasChildren() or item_can_have_children
            return super().rowCount(parent)

        def fetchMore(self, parent):
            """
            If the parent has children, this method will insert them under the parent if not already done
            Args:
                parent: The node to evaluate for children
            """
            item = self.itemFromIndex(parent)
            if item is not None:
                item_data = item.data(Qt.ItemDataRole.UserRole)
                if item_data is not None:
                    if isinstance(item_data, dict):
                        for key, value in item_data.items():
                            if self._fields:
                                if key in self._fields:
                                    self._add_child(item, key, value)
                            else:
                                self._add_child(item, key, value)
                    elif isinstance(item_data, list):
                        for index, value in enumerate(item_data):
                            self._add_child(item, f"[{index}]", value)
                    return

            super().fetchMore(parent)

        def _add_child(self, root: QStandardItem, key: str, value, icon=None):
            if isinstance(value, list):
                # List
                root.appendRow([self._standard_item(key, value, icon), QStandardItem(f"{len(value)} items")])
            elif isinstance(value, dict):
                # Dictionary
                if props.FIELD_FILE_NAME in value:
                    icon = get_mime_type_icon(get_mime_type_icon_name(value[props.FIELD_FILE_NAME]))
                    key = value[props.FIELD_FILE_NAME]
                data_field = value[props.FIELD_FILE_SIZE] if props.FIELD_FILE_SIZE in value else ""
                root.appendRow([self._standard_item(key, value, icon), QStandardItem(data_field)])
            else:
                # Node value
                root.appendRow([QStandardItem(key), QStandardItem(str(value))])

        @staticmethod
        def _standard_item(text, data, icon=None):
            std_item = QStandardItem(text)
            std_item.setData(data, Qt.ItemDataRole.UserRole)
            if icon:
                std_item.setIcon(icon)
            return std_item

    def set_model(self, model_data: list, fields: list | None):
        self.setModel(self._create_proxy_model(JsonView.LazyJsonModel(model_data, fields, self.parent())))
        self.resizeColumnToContents(0)

    def __init__(self, parent):
        super().__init__(parent)
        self.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)


class TableView(QTableView, ModelManager):
    # https://stackoverflow.com/questions/57764723/make-an-active-search-with-qlistwidget
    # https://stackoverflow.com/questions/20563826/pyqt-qtableview-search-by-hiding-rows
    class TableModel(QAbstractTableModel):
        def __init__(self, model_data: list, fields: list):
            super().__init__()
            self._exif_data = []
            self._exif_cols = fields
            self._QStandardItem_cache = {}
            self._orientation = self._orientation(model_data)

            for data in model_data:
                for entry in data.data:
                    self._exif_data.append(entry)

        @property
        def orientation(self):
            return self._orientation

        def rowCount(self, parent: QModelIndex = None) -> int:
            if self.orientation == Qt.Orientation.Horizontal:
                return len(self._exif_data)
            else:
                return len(self._exif_cols)

        def columnCount(self, parent: QModelIndex = None) -> int:
            if self.orientation == Qt.Orientation.Horizontal:
                return len(self._exif_cols)
            else:
                return 1

        def headerData(self, p_int, p_orientation, role=None):
            if role == Qt.ItemDataRole.DisplayRole:
                if self.orientation == Qt.Orientation.Horizontal:
                    if p_orientation == Qt.Orientation.Horizontal:
                        return self._exif_cols[p_int]
                    elif p_orientation == Qt.Orientation.Vertical:
                        return QVariant()
                else:
                    if p_orientation == Qt.Orientation.Horizontal:
                        return QVariant()
                    elif p_orientation == Qt.Orientation.Vertical:
                        return self._exif_cols[p_int]

        def data(self, index: QModelIndex, role: int = None):
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
                if self.orientation == Qt.Orientation.Horizontal:
                    row = self._exif_data[index.row()]
                    col = self._exif_cols[index.column()]
                    if col in row:
                        item = QStandardItem(str(row[col]))
                        if index.column() == 0 and props.FIELD_FILE_NAME in row:
                            icon = get_mime_type_icon(get_mime_type_icon_name(row[props.FIELD_FILE_NAME]))
                            item.setIcon(icon)
                else:
                    key = self._exif_cols[index.row()]
                    if key in self._exif_data[0]:
                        item = QStandardItem(str(self._exif_data[0][key]))
                    else:
                        app.logger.warning(f"tag:{key} not present in current dataset. Will cache a null for it")
                        item = QVariant()
                self._QStandardItem_cache[p_index] = item
            return item

        @staticmethod
        def _orientation(model_data: list) -> Qt.Orientation:
            if len(model_data) == 1:
                if len(model_data[0].data) == 1:
                    app.logger.debug("Displaying in Vertical Mode")
                    return Qt.Orientation.Vertical
            app.logger.debug("Displaying in Horizontal Mode")
            return Qt.Orientation.Horizontal

    def __init__(self, parent):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.verticalHeader().setHighlightSections(False)
        self.verticalHeader().setSectionsMovable(True)
        self.verticalHeader().setSectionsClickable(True)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setSectionsClickable(True)
        self.setSortingEnabled(True)

    def set_model(self, model_data: list, fields: list):
        p_model = self.TableModel(model_data, fields)
        self.setModel(self._create_proxy_model(p_model))
        if len(fields) < 20:
            self.resizeColumnsToContents()


class ViewType(Enum):
    TABLE = TableView, "text-csv", "Display information as a table"
    JSON = JsonView, "application-json", ("Display information in JSON (JavaScript Object "
                                          "Notation) formatting")

    def __init__(self, view, icon_name: str, description: str):
        self._description = description
        self._icon_name = icon_name
        self._view = view

    @property
    def description(self):
        return self._description

    @property
    def view(self):
        return self._view

    @property
    def icon(self):
        return self._icon_name
