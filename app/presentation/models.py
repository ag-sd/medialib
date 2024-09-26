from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt, QVariant, QAbstractTableModel, QPersistentModelIndex
from PyQt6.QtGui import QPalette, QStandardItem, QIcon

import app
from app.collection import props
from app.plugins.framework import FileData


_GROUP_BG = QPalette().color(QPalette.ColorGroup.Normal, QPalette.ColorRole.Window)
_GROUP_BG.setAlpha(8)

_ICON_FOLDER = QIcon.fromTheme("folder")
_UNKNOWN = "N/A"

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
class ModelData:
    data: ...
    path: str


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
        s = "items" if self.row_count != 1 else "item"
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


class ModelBuilder:
    @abstractmethod
    def build(self, **kwargs):
        raise NotImplemented


class BaseViewBuilder(ModelBuilder):

    def __init__(self):
        self._model_data: list = []
        self._collection_paths: list = []
        self._file_ops_available = False

    @property
    def data(self):
        return self._model_data

    @property
    def collection_paths(self):
        return self._collection_paths

    @property
    def is_file_ops_available(self):
        return self._file_ops_available

    def build(self, **kwargs):
        _flat_list = []
        _collection_paths = []
        _file_ops_available = len(kwargs["model_data"]) > 0  # False if no data
        for item in kwargs["model_data"]:
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


class FileSystemModelBuilder(ModelBuilder):
    def build(self, **kwargs):
        dir_map = {}
        dir_groups = self._group_by_path(kwargs["view_items"])
        for _dir in dir_groups:
            self._add_to_dir_map(list(Path(_dir).parts), dir_map, "")
            # At this point, the current _dir is guaranteed to exist in the tree. So add all children to it
            for item in dir_groups[_dir]:
                dir_map[_dir].add_child(item)
        return next(iter(dir_map.values()))

    def _add_to_dir_map(self, dir_components: list, dir_map: dict, parent_path: str):
        component = dir_components.pop(0)
        current_path = str(Path(parent_path).joinpath(component))
        if current_path not in dir_map:
            item = ViewItem(icon=_ICON_FOLDER, parent=None, data=None, text=component)
            if parent_path != "":
                dir_map[parent_path].add_child(item)
            dir_map[current_path] = item
        if len(dir_components) > 0:
            self._add_to_dir_map(dir_components, dir_map, current_path)

    @staticmethod
    def _group_by_path(model_data: list):
        _flat_list = {}

        for item in model_data:
            file_data = item.data[props.FIELD_COLLECTION_FILEDATA]
            if file_data.directory not in _flat_list:
                _flat_list[file_data.directory] = []
            _flat_list[file_data.directory].append(item)
        return _flat_list


class GroupTreeItemBuilder(ModelBuilder):
    def build(self, **kwargs):
        return self._build_tree("", kwargs["group_by"], kwargs["view_items"])

    def _build_tree(self, group_path: str, grouping: list, data: list, grouping_index: int = 0):
        current_node = ViewItem(icon=_ICON_FOLDER, parent=None, data=None, text=group_path)
        if grouping_index < len(grouping):
            group = grouping[grouping_index]
            keys = {}
            for item in data:
                if group in item.data:
                    key = item.data[group]
                else:
                    key = _UNKNOWN

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


class TreeModel(QAbstractItemModel):

    def __init__(self, root_node: ViewItem, fields: list):
        super().__init__()
        app.logger.debug("Building tree model")
        self._root_node = root_node
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
            return _GROUP_BG

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
