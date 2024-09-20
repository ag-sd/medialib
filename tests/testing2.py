import sys
import tempfile
from dataclasses import dataclass
from typing import override

from PyQt6.QtCore import QRegularExpression, QAbstractItemModel, QModelIndex, Qt, QVariant
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QLineEdit, QTreeView, QWidget, QVBoxLayout

from app.views import ModelData, get_mime_type_icon
from tests.collection import test_utils


@dataclass
class TableNode:
    text: str
    icon: QIcon | None
    parent: ...  # dict | None
    children: list  # list of parent keys | list of dicts representing leaves | []


@dataclass
class TableLeaf:
    icon: QIcon | None
    data: ...


# class TableModelV2(QAbstractItemModel):
#     _UNKNOWN = "N/A"
#     _PATH = "MediaLib:Path"
#
#     def __init__(self, model_data: list, fields: list, group_key: list):
#         super().__init__()
#         print(fields)
#         self._orientation = self._orientation(model_data)
#         self._exif_cols = fields
#         self._group_key = group_key
#         self._root_node = self._build_grouping_model(self._flatten(model_data), self._group_key)
#
#     # @override
#     # def index(self, row, column, parent=...):
#     #     if not self.hasIndex(row, column, parent):
#     #         return QModelIndex()
#     #
#     #     if not parent.isValid():
#     #         parent_node = self._root_node
#     #     else:
#     #         parent_node = parent.internalPointer()
#     #
#     #     if row < len(parent_node.children):
#     #         item = parent_node.children[row]
#     #         key = self._exif_cols[column]
#     #         # TODO: Improve this logic
#     #         if isinstance(item, TableNode) and column > 0:
#     #             return QModelIndex()
#     #         elif isinstance(item, TableNode) and column == 0:
#     #             return self.createIndex(row, column, item)
#     #         elif isinstance(item, TableLeaf) and key in item.data:
#     #             value = item.data[key]
#     #             return self.createIndex(row, column, value)
#     #         else:
#     #             return QModelIndex()
#     #     else:
#     #         return QModelIndex()
#
#     # @override
#     # def data(self, index, role=...):
#     #     if not index.isValid():
#     #         return QVariant()
#     #     # p_index = QPersistentModelIndex(index)
#     #     # item = self._QStandardItem_cache.get(p_index)
#     #     # if item is not None:
#     #     #     return item
#     #     item = index.internalPointer()
#     #     if role == Qt.ItemDataRole.DisplayRole:
#     #         row = index.row()
#     #         column = index.column()
#     #         if isinstance(item, TableNode) and column > 0:
#     #             return QVariant()
#     #         elif isinstance(item, TableNode) and column == 0:
#     #             return item.text
#     #         elif isinstance(item, TableLeaf) and column < len(self._exif_cols):
#     #             value = TableLeaf.data[column]
#     #             return str(value)
#     #         else:
#     #             return str(item)
#     #     return QVariant()
#
#     # @override
#     # def parent(self, index):
#     #     if not index.isValid():
#     #         return QModelIndex()
#     #
#     #     child = index.internalPointer()
#     #     parent = child.parent
#     #
#     #     if parent == self._root_node:
#     #         return QModelIndex()
#     #
#     #     return self.createIndex(0, 0, parent)
#
#     @override
#     def rowCount(self, parent: QModelIndex = None) -> int:
#         return 0
#         # if self.orientation == Qt.Orientation.Horizontal:
#         #     if not parent.isValid():
#         #         parent_node = self._root_node
#         #     else:
#         #         parent_node = parent.internalPointer()
#         #     if isinstance(parent_node, TableNode):
#         #         return len(parent_node.children)
#         #     else:
#         #         return 0
#         # else:
#         #     return len(self._exif_cols)
#
#     @override
#     def columnCount(self, parent: QModelIndex = None) -> int:
#         if self.orientation == Qt.Orientation.Horizontal:
#             return len(self._exif_cols)
#         else:
#             return 2
#
#     # @override
#     # def canFetchMore(self, index):
#     #     if not index.isValid():
#     #         return False
#     #     item = index.internalPointer()
#     #     return False
#
#     @override
#     def headerData(self, p_int, p_orientation, role=None):
#         if role == Qt.ItemDataRole.DisplayRole:
#             if self.orientation == Qt.Orientation.Horizontal:
#                 if p_orientation == Qt.Orientation.Horizontal and p_int >= 0:
#                     return self._exif_cols[p_int]
#                 elif p_orientation == Qt.Orientation.Vertical:
#                     return QVariant()
#             else:
#                 if p_orientation == Qt.Orientation.Horizontal:
#                     return QVariant()
#                 elif p_orientation == Qt.Orientation.Vertical:
#                     return self._exif_cols[p_int]
#
#     @property
#     def orientation(self):
#         return self._orientation
#
#     @staticmethod
#     def _orientation(model_data: list) -> Qt.Orientation:
#         if len(model_data) == 1:
#             if len(model_data[0].data) == 1:
#                 print("app.logger.debug --- Displaying in Vertical Mode")
#                 return Qt.Orientation.Vertical
#         print("app.logger.debug --- Displaying in Horizontal Mode")
#         return Qt.Orientation.Horizontal
#
#     @staticmethod
#     def _flatten(model_data: list):
#         _flat_list = []
#         for item in model_data:
#             for _path, entries in item.data.items():
#                 for entry in entries:
#                     _flat_list.append(entry)
#         return _flat_list
#
#     @staticmethod
#     # TODO: Move to separate helper class to make testing easier
#     def _build_grouping_model(data: list, group_key: list):
#         def add_item(_container: dict, _path: list, _item: dict):
#             _group = _path.pop()
#             if len(_path) == 0:
#                 # leaf item
#                 if _group not in _container:
#                     _container[_group] = []
#                 file_data = None  # TODO:FileData.from_dict(item, item[TableModel._PATH])
#                 icon = None
#                 if file_data is not None:
#                     icon = get_mime_type_icon(file_data.mime_type)
#                 _container[_group].append(TableLeaf(icon=icon, data=_item))
#             else:
#                 if _group not in _container:
#                     _container[_group] = {}
#                 add_item(_container[_group], _path, _item)
#
#         def create_table_node(node_name: str, node_data: ...):
#             if isinstance(node_data, dict):
#                 parent_node = TableNode(node_name, icon=None, parent=None, children=[])
#                 for sub_key, sub_data in node_data.items():
#                     sub_node = create_table_node(node_name=sub_key, node_data=sub_data)
#                     parent_node.children.append(sub_node)
#                     sub_node.parent = parent_node
#                 return parent_node
#             elif isinstance(node_data, list):
#                 return TableNode(node_name, icon=None, parent=None, children=node_data)
#
#         model = {}
#         if len(group_key) == 0:
#             pass
#
#         for item in data:
#             path = []
#             # Check if each grouping is available in the item and build item specific path
#             for group in group_key:
#                 if group in item:
#                     path.insert(0, item[group])
#                 else:
#                     path.insert(0, TableModelV2._UNKNOWN)
#             # Once path is built, add item to model
#             add_item(model, path, item)
#
#         # Convert the dictionary model to a Tree Model for indexed access
#         return create_table_node("", model)


def line_edit_change():
    if len(line_edit.text()) > 3 or len(line_edit.text()) == 0:
        re = QRegularExpression(line_edit.text(), QRegularExpression.PatternOption.CaseInsensitiveOption)
        if _proxy_model:
            _proxy_model.setFilterRegularExpression(re)


app = QApplication(sys.argv)
line_edit = QLineEdit()
line_edit.textChanged.connect(line_edit_change)
view = QTreeView()
view.setAlternatingRowColors(True)
view.setUniformRowHeights(True)  # Allows for scrolling optimizations.
view.setSortingEnabled(True)
# view.setModel(_proxy_model)
view.setWindowTitle("Simple Tree Model")

widget = QWidget()
layout = QVBoxLayout()
layout.addWidget(view)
layout.addWidget(line_edit)
widget.setLayout(layout)
widget.setMinimumWidth(600)
widget.setMinimumHeight(800)

# with tempfile.TemporaryDirectory() as db_path:
#     test_paths = test_utils.get_test_paths()
#     db = test_utils.create_test_media_db(db_path, test_paths)
#     main_model_data = []
#     for path in db.paths:
#         for _path, entry in db.data([path]).items():
#             main_model_data.append(ModelData(data=entry, path=_path))
#
# tm = TableModelV2(main_model_data, db.tags[20:32], [])

widget.show()
sys.exit(app.exec())
