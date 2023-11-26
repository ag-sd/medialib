import json
from enum import Enum

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, QPersistentModelIndex, QMimeDatabase
from PyQt6.QtGui import QFontDatabase, QStandardItemModel, QStandardItem, QIcon
from PyQt6.QtWidgets import QTextEdit, QTreeView, QTableView, QAbstractItemView

import app
from app.mediainfo.exifinfo import ExifInfoFormat, ExifInfo

_MIME_ICON_CACHE = {}
_mime_database = QMimeDatabase()


def get_mime_type_icon_name(file: str) -> str:
    mime_type = _mime_database.mimeTypeForFile(file)
    return mime_type.iconName()


def get_mime_type_icon(mime_type_icon_name: str):
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


class TextView(QTextEdit):
    def __init__(self, exif_info: ExifInfo):
        super().__init__()
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.setStyleSheet("QTextEdit{background: #665c54; color: #FBF1C7; font-size: 11.5px;}")
        self.setText(exif_info.data)


class HtmlView(QTextEdit):
    def __init__(self, exif_info: ExifInfo):
        super().__init__()
        self.setHtml(exif_info.data)


class JsonView(QTreeView):
    def __init__(self, exif_info: ExifInfo):
        super().__init__()
        self.exif_info = exif_info
        self.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)

        model = QStandardItemModel()
        model.setColumnCount(2)
        model.setHeaderData(0, Qt.Orientation.Horizontal, "Key")
        model.setHeaderData(1, Qt.Orientation.Horizontal, "Data")
        self._build(model.invisibleRootItem(), "EXIFDATA", json.loads(exif_info.data))
        self.setModel(model)
        self.expandAll()
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)

    def _build(self, root: QStandardItem, parent: str, data):
        """
        Recursively builds the tree
        :param root: The root to add leaves to
        :param parent: The parent of the current data
        :param data: the data eliment that should be added to the tree
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


class TableView(QTableView):
    class DataModel(QAbstractTableModel):
        def __init__(self, exif_infos: list):
            super().__init__()
            self._exif_data = []
            self._exif_cols = []
            self._QStandardItem_cache = {}

            all_keys = []
            for info in exif_infos:
                json_data = json.loads(info.data)
                for entry in json_data:
                    all_keys.extend(list(entry.keys()))
                    self._exif_data.append(entry)
            self._exif_cols = list(dict.fromkeys(all_keys))

        def rowCount(self, parent: QModelIndex = None) -> int:
            return len(self._exif_data)

        def columnCount(self, parent: QModelIndex = None) -> int:
            return len(self._exif_cols)

        def headerData(self, p_int, orientation, role=None):
            if role == Qt.ItemDataRole.DisplayRole:
                if orientation == Qt.Orientation.Horizontal:
                    return self._exif_cols[p_int]
                elif orientation == Qt.Orientation.Vertical:
                    return p_int

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
                row = self._exif_data[index.row()]
                col = self._exif_cols[index.column()]
                if col in row:
                    item = QStandardItem(str(row[col]))
                    self._QStandardItem_cache[p_index] = item
            return item

    def __init__(self, exif_info: ExifInfo):
        super().__init__()
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.verticalHeader().setDefaultSectionSize(self.verticalHeader().fontMetrics().height() + 3)
        self.verticalHeader().hide()
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setSectionsMovable(True)
        # self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().setSectionsClickable(True)
        self.setSortingEnabled(True)
        self.setModel(self.DataModel([exif_info]))


class ViewType(Enum):
    CSV = ExifInfoFormat.CSV, TableView, "Export information in CSV format"
    JSON = ExifInfoFormat.JSON, JsonView, "Use JSON (JavaScript Object Notation) formatting for console output"
    HTML = ExifInfoFormat.HTML, HtmlView, "Use HTML table formatting for output."
    PHP = ExifInfoFormat.PHP, TextView, "Format output as a PHP Array."
    XML = ExifInfoFormat.XML, TextView, "Use ExifTool-specific RDF/XML formatting for console output."

    def __init__(self, exif_format: ExifInfoFormat, view, description: str):
        self._description = description
        self._exif_format = exif_format
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
