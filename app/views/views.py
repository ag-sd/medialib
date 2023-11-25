import json
from enum import Enum

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase, QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import QTextEdit, QTreeView

from app.exifinfo import ExifInfoFormat, ExifInfo


class TextView(QTextEdit):
    def __init__(self, exif_info: ExifInfo):
        super().__init__()
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.setStyleSheet("QTextEdit{background: #282828; color: #FBF1C7; font-size: 11.5px;}")
        self.setText(exif_info.data)


# class JsonView(QTextEdit):
#     # https://github.com/leixingyu/codeEditor/blob/master/highlighter/jsonHighlight.py
#     def __init__(self, exif_info: ExifInfo):
#         super().__init__()
#         self.setText(exif_info.data)


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


class ViewType(Enum):
    JSON = ExifInfoFormat.JSON, JsonView, "Use JSON (JavaScript Object Notation) formatting for console output"
    HTML = ExifInfoFormat.HTML, HtmlView, "Use HTML table formatting for output."
    PHP = ExifInfoFormat.PHP, TextView, "Format output as a PHP Array."
    XML = ExifInfoFormat.XML, TextView, "Use ExifTool-specific RDF/XML formatting for console output."
    CSV = ExifInfoFormat.CSV, TextView, "Export information in CSV format"

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
