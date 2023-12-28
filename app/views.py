from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, QPersistentModelIndex, QMimeDatabase, \
    QSortFilterProxyModel, QRegularExpression
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt6.QtWidgets import QTreeView, QTableView, QAbstractItemView

import app
from app.database.exifinfo import ExifInfoFormat

_MIME_ICON_CACHE = {}
_mime_database = QMimeDatabase()


def get_mime_type_icon_name(file: str) -> str:
    mime_type = _mime_database.mimeTypeForFile(file)
    return mime_type.iconName()


def get_mime_type_icon(mime_type_icon_name: str):
    # TODO: Test
    if mime_type_icon_name not in _MIME_ICON_CACHE:
        mime_icon = QIcon.fromTheme(mime_type_icon_name)
        if mime_icon is None:
            app.logger.debug(f"Adding icon for {mime_type_icon_name} to cache")
            if mime_type_icon_name == "text-x-generic":
                app.logger.warning(f"Icon for {mime_type_icon_name} was not found, will return None")
                return None
            return get_mime_type_icon("text-x-generic")
        _MIME_ICON_CACHE[mime_type_icon_name] = mime_icon
    return _MIME_ICON_CACHE[mime_type_icon_name]


# class View:
#     def foo(self):
#         print("I am called")

# https://www.qtcentre.org/threads/27005-QTextEdit-find-all
# class TextView(QTextEdit):
#     def __init__(self, str_data: str):
#         super().__init__()
#         self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
#         self.setStyleSheet("QTextEdit{background: #665c54; color: #FBF1C7; font-size: 11.5px;}")
#         self.setText(str_data)


# class HtmlView(QTextEdit):
#     def __init__(self, html_str_data: str):
#         super().__init__()
#         self.setHtml(html_str_data)

@dataclass
class ModelData:
    json: list
    path: str


class ModelManager:
    def __init__(self):
        super().__init__()
        self._proxy_model = None

    @abstractmethod
    def set_model(self, model_data: list):
        raise NotImplemented

    def search(self, search_context):
        re = QRegularExpression(search_context["text"], QRegularExpression.PatternOption.CaseInsensitiveOption)
        self._proxy_model.setFilterRegularExpression(re)

    def _create_proxy_model(self, main_model):
        self._proxy_model = QSortFilterProxyModel(self)
        self._proxy_model.setSourceModel(main_model)
        return self._proxy_model


class JsonView(QTreeView, ModelManager):

    def __init__(self):
        super().__init__()
        self.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)

    def set_model(self, model_data: list):
        p_model = QStandardItemModel()
        p_model.setColumnCount(2)
        p_model.setHeaderData(0, Qt.Orientation.Horizontal, "Key")
        p_model.setHeaderData(1, Qt.Orientation.Horizontal, "Data")
        for data in model_data:
            self._build(p_model.invisibleRootItem(), data.path, data.json)
        self.setModel(self._create_proxy_model(p_model))
        self.expandAll()
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)

    def _build(self, root: QStandardItem, parent: str, data):
        """
        Recursively builds the tree
        :param root: The root to add leaves to
        :param parent: The parent of the current data
        :param data: the data element that should be added to the tree
        """
        if isinstance(data, dict):
            # Iterate Dict by key
            new_root = QStandardItem(parent)
            for key, value in data.items():
                self._build(new_root, key, value)
            root.appendRow(new_root)
        elif isinstance(data, list):
            # Iterate List by index
            new_root = QStandardItem(parent)
            for index, value in enumerate(data):
                self._build(new_root, f"[{index}]", value)
            root.appendRow(new_root)
        else:
            # Key-value pair
            # app.logger.debug(f"Append {parent} -> {data} to {root.text()}")
            root.appendRow([QStandardItem(parent), QStandardItem(str(data))])


class TableView(QTableView, ModelManager):
    # https://stackoverflow.com/questions/57764723/make-an-active-search-with-qlistwidget
    # https://stackoverflow.com/questions/20563826/pyqt-qtableview-search-by-hiding-rows
    class TableModel(QAbstractTableModel):
        def __init__(self, model_data: list):
            super().__init__()
            self._exif_data = []
            self._exif_cols = []
            self._QStandardItem_cache = {}
            self._orientation = self._orientation(model_data)

            all_keys = []
            for data in model_data:
                for entry in data.json:
                    all_keys.extend(list(entry.keys()))
                    self._exif_data.append(entry)
            self._exif_cols = list(dict.fromkeys(all_keys))

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
                else:
                    key = self._exif_cols[index.row()]
                    value = self._exif_data[0][key]
                    item = QStandardItem(str(value))
                self._QStandardItem_cache[p_index] = item
            return item

        @staticmethod
        def _orientation(model_data: list) -> Qt.Orientation:
            if len(model_data) == 1:
                if len(model_data[0].json) == 1:
                    app.logger.debug("Displaying in Vertical Mode")
                    return Qt.Orientation.Vertical
            app.logger.debug("Displaying in Horizontal Mode")
            return Qt.Orientation.Horizontal

    def __init__(self):
        super().__init__()
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        # self.verticalHeader().setDefaultSectionSize(self.verticalHeader().fontMetrics().height() + 3)
        self.verticalHeader().setHighlightSections(False)
        self.verticalHeader().setSectionsMovable(True)
        self.verticalHeader().setSectionsClickable(True)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setSectionsClickable(True)
        self.setSortingEnabled(True)

    def set_model(self, model_data: list):
        p_model = self.TableModel(model_data)
        self.setModel(self._create_proxy_model(p_model))
        # self.resizeColumnsToContents()
        # self.resizeRowsToContents()


class ViewType(Enum):
    TABLE = ExifInfoFormat.JSON, TableView, "text-csv", "Display information as a table"
    JSON = ExifInfoFormat.JSON, JsonView, "application-json", ("Display information in JSON (JavaScript Object "
                                                               "Notation) formatting")

    def __init__(self, exif_format: ExifInfoFormat, view, icon_name: str, description: str):
        self._description = description
        self._exif_format = exif_format
        self._icon_name = icon_name
        self._view = view

    @property
    def description(self):
        return self._description

    @property
    def format(self):
        return self._exif_format

    @property
    def view(self):
        return self._view

    @property
    def icon(self):
        return self._icon_name

