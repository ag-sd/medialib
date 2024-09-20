import sys
from dataclasses import dataclass, field
from typing import override

from PyQt6.QtCore import QAbstractItemModel, Qt, QModelIndex, QVariant, QSortFilterProxyModel, QRegularExpression
from PyQt6.QtGui import QIcon, QBrush, QColor
from PyQt6.QtWidgets import QLineEdit, QTreeView, QWidget, QVBoxLayout, QApplication

from app.collection.ds import Collection
from app.plugins.framework import FileData
from app.views import get_mime_type_icon, ModelData


@dataclass
class TableNode:
    icon: QIcon | None
    parent: ...  # dict | None
    children: list
    data: dict


@dataclass
class TableLeaf:
    icon: QIcon | None
    data: ...


# https://gist.github.com/nbassler/342fc56c42df27239fa5276b79fca8e6
@dataclass
class TableItem:
    icon: QIcon | None
    parent: ...  # dict | None
    data: dict | None
    row: int = 0
    text: str = ""
    _children: list = field(default_factory=list)
    fetched: int = 0

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


class TreeModel(QAbstractItemModel):
    _NODE_FOLDER = QIcon.fromTheme("folder")
    _GROUP_BG = QBrush(QColor(195, 195, 195, 125))
    _UNKNOWN = "N/A"
    _PATH = "MediaLib:Path"

    def __init__(self, model_data: list, fields: list, grouping: list):
        super().__init__()
        print("DEBUG - building tree model")
        self._root_node = self._build_tree("", grouping, self._flatten(model_data))
        print("Tree Model built")
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

        # elif role == Qt.ItemDataRole.BackgroundRole and not node.is_leaf_item:
        #     return self._GROUP_BG

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

    @staticmethod
    def _flatten(model_data: list):
        _flat_list = []
        for item in model_data:
            for _path, entries in item.data.items():
                for entry in entries:
                    file_data = FileData.from_dict(entry, _path)
                    icon = None
                    if file_data is not None:
                        icon = get_mime_type_icon(file_data.mime_type)
                    _flat_list.append(TableItem(icon=icon, parent=None, data=entry))
        return _flat_list

    def _build_tree(self, group_path: str, grouping: list, data: list, grouping_index: int = 0):
        current_node = TableItem(icon=self._NODE_FOLDER, parent=None, data=None, text=group_path)
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


class SpanningTreeview(QTreeView):

    def __init__(self):
        super().__init__()

    def drawRow(self, painter, options, index):
        if index.isValid():
            item = self.model().data(index, Qt.ItemDataRole.UserRole)
            if not item.is_leaf_item:
                self.setFirstColumnSpanned(index.row(), self.model().parent(index), True)
        super().drawRow(painter, options, index)


# --------------------------------------------------
def line_edit_change():
    if len(line_edit.text()) > 3 or len(line_edit.text()) == 0:
        re = QRegularExpression(line_edit.text(), QRegularExpression.PatternOption.CaseInsensitiveOption)
        if _proxy_model:
            _proxy_model.setFilterRegularExpression(re)


db = Collection.open_db("/mnt/dev/testing/Medialib/threaded-scan/")
app = QApplication(sys.argv)
main_model_data = []
for main_path in db.paths:
    main_data = db.data([main_path])
    for main__path, main_entries in main_data.items():
        for main_entry in main_entries:
            # Add path to the entry
            main_entry[TreeModel._PATH] = main__path
    main_model_data.append(ModelData(data=main_data, path=main_path))
# something after tag 14 is crashing the view
tm = TreeModel(main_model_data, db.tags, ["File:FileType", "ABC", TreeModel._PATH])  # TableModelV3._PATH, "File:FileType"
line_edit = QLineEdit()
line_edit.textChanged.connect(line_edit_change)
view = SpanningTreeview()
view.setAlternatingRowColors(True)
view.setUniformRowHeights(True)  # Allows for scrolling optimizations.
_proxy_model = QSortFilterProxyModel(view)
_proxy_model.setRecursiveFilteringEnabled(True)
_proxy_model.setSourceModel(tm)
view.setSortingEnabled(True)
view.setModel(_proxy_model)
view.setWindowTitle("Simple Tree Model")

widget = QWidget()
layout = QVBoxLayout()
layout.addWidget(view)
layout.addWidget(line_edit)
widget.setLayout(layout)
widget.setMinimumWidth(600)
widget.setMinimumHeight(800)

widget.show()
sys.exit(app.exec())
