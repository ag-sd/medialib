import sys
from dataclasses import dataclass
from typing import override

from PyQt6.QtCore import QAbstractItemModel, Qt, QModelIndex, QSortFilterProxyModel, QRegularExpression, QVariant
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QTreeView, QLineEdit, QWidget, QVBoxLayout

from app.collection.ds import Collection
from app.views import ModelData, get_mime_type_icon

d = {'Users': {'files': [{'filename': 'file.txt', 'size': 1234, 'modified': 'blah'},
                         {'filename': 'file2.txt', 'size': 1234, 'modified': 'blah'},
                         {'filename': 'file3.txt', 'size': 1234, 'modified': 'blah'}],
               'manu': {'files': [{'filename': 'file.txt', 'size': 1234, 'modified': 'blah'},
                                  {'filename': 'file2.txt', 'size': 1234, 'modified': 'blah'},
                                  {'filename': 'file3.txt', 'size': 1234, 'modified': 'blah'}],
                        },
               },
     'Applications': {'files': [{'filename': 'file.txt', 'size': 1234, 'modified': 'blah'},
                                {'filename': 'file2.txt', 'size': 1234, 'modified': 'blah'},
                                {'filename': 'file3.txt', 'size': 1234, 'modified': 'blah'}]
                      }
     }

for i in range(0, 50):
    d['Users']['manu'][f'Documents-{i}'] = {'files': []}
    for j in range(0, 50):
        d['Users']['manu'][f'Documents-{i}']['files'].append(
            {'filename': f'file-{j}.txt', 'size': 1234, 'modified': 'blah'})

selected = set()


class FileItem:
    def __init__(self, filename, modified, size, parent=None):
        self.parentItem = parent
        self.itemData = [filename, modified, size]
        self.checkedState = False

    def childCount(self):
        return 0

    def columnCount(self):
        return 3

    def data(self, column):
        return self.itemData[column]

    def parent(self):
        return self.parentItem

    def row(self):
        return self.parentItem.childItems.index(self)

    def setCheckedState(self, value):
        if value == 2:
            self.checkedState = True
            selected.add('/'.join(self.parentItem.path) + '/' + self.itemData[0])
        else:
            self.checkedState = False
            selected.remove('/'.join(self.parentItem.path) + '/' + self.itemData[0])
        print(selected)

    def getCheckedState(self):
        if self.checkedState:
            return Qt.CheckState.Checked
        else:
            return Qt.CheckState.Unchecked


def get_dict_from_path(path):
    current_level = d
    for folder in path:
        current_level = current_level[folder]

    return current_level


class FolderItem():
    def __init__(self, path=[], parent=None):
        self.parentItem = parent
        self.path = path
        self.checkedState = False
        self.childItems = []

        if self.path:
            folder_content = get_dict_from_path(self.path)
            if folder_content.get('files', False):
                self.n_children = len(folder_content['files']) + len(folder_content) - 1
            else:
                self.n_children = len(folder_content)
        else:
            self.n_children = len(d)  # TODO: handle files at root level

        self.is_loaded = False

    def load_children(self):
        self.childItems = []
        if self.path:
            child_dirs = []
            folder_content = get_dict_from_path(self.path)
            for folder in folder_content.keys():
                if folder == 'files':
                    for file in folder_content['files']:
                        self.childItems.append(FileItem(file['filename'], file['modified'], file['size'], parent=self))
                else:
                    child_dirs.append(folder)
        else:  # special case of root node. TODO: handle files at root level
            child_dirs = d.keys()

        for child_dir in child_dirs:
            child_path = self.path + [child_dir]
            self.childItems.append(FolderItem(path=child_path, parent=self))
        self.is_loaded = True

    def child(self, row):
        if row < len(self.childItems):
            return self.childItems[row]
        else:
            print(f"invalid row {row} for {self.path}")
            return None

    def childCount(self):
        return self.n_children

    def columnCount(self):
        return 3

    def setCheckedState(self, value):
        if value == 2:
            self.checkedState = True
            selected.add('/'.join(self.path))
        else:
            self.checkedState = False
            selected.remove('/'.join(self.path))
        print(selected)

    def getCheckedState(self):
        if self.checkedState:
            return Qt.CheckState.Checked
        else:
            return Qt.CheckState.Unchecked

    def data(self, column):
        if column == 0 and self.path:
            return self.path[-1]
        else:
            return None

    def parent(self):
        return self.parentItem

    def row(self):
        if self.parentItem:
            return self.parentItem.childItems.index(self)

        return 0


class TreeModel_DEMO(QAbstractItemModel):
    column_names = ['Name', 'Modified', 'Size']

    def __init__(self, parent=None):
        super(TreeModel_DEMO, self).__init__(parent)

        self.rootItem = FolderItem(path=[])
        self.rootItem.load_children()

    def columnCount(self, parent):
        return 3

    def data(self, index, role):
        if not index.isValid():
            return QVariant()

        item = index.internalPointer()

        if role == Qt.ItemDataRole.DisplayRole:
            print(item.data(index.column()))
            return item.data(index.column())
        elif role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            return item.getCheckedState()
        else:
            return QVariant()

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.CheckStateRole:
            item = index.internalPointer()
            item.setCheckedState(value)

        return True

    def canFetchMore(self, index):
        if not index.isValid():
            return False
        item = index.internalPointer()
        return not item.is_loaded

    def fetchMore(self, index):
        item = index.internalPointer()
        item.load_children()

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable

    def headerData(self, section, orientation, role):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.column_names[section]

        return None

    def index(self, row, column, parent=...):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent=...):
        if parent.column() > 0:
            return 0

        print(f"RC for {parent.data(Qt.ItemDataRole.DisplayRole)}")
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()


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


class TableModel(QAbstractItemModel):
    # TODO: Add to props
    # TODO: Add to indexer with SHA
    _PATH = "MediaLib:Path"
    _UNKNOWN = "N/A"

    def __init__(self, model_data: list, fields: list):
        super().__init__()
        test_data = [
            {"a": 1, "b": 2, "c": 3},
            {"a": 4, "b": 5, "c": 6}
        ]
        self._QStandardItem_cache = {}
        # TODO: Move this to constructor
        self._group_key = ["a", "c"]
        self._orientation = self._orientation(model_data)
        # self._exif_cols = fields
        self._exif_cols = ["a", "b", "c"]
        # self._data_model = self._build_grouping_model(self._flatten(model_data), self._group_key)
        self._data_model = self._build_grouping_model(test_data, self._group_key)
        self._root_node = self._create_table_node(self._data_model)

    @property
    def orientation(self):
        return self._orientation

    def columnCount(self, parent: QModelIndex = None) -> int:
        if self.orientation == Qt.Orientation.Horizontal:
            return len(self._exif_cols)
        else:
            return 2

    def rowCount(self, parent: QModelIndex = None) -> int:
        if self.orientation == Qt.Orientation.Horizontal:
            if not parent.isValid():
                parent_node = self._root_node
            else:
                parent_node = parent.internalPointer()
            return len(parent_node.children)
        else:
            return len(self._exif_cols)

    def index(self, row, column, parent=...):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent_node = self._root_node
        else:
            parent_node = parent.internalPointer()

        if row < len(parent_node.children):
            item_data = parent_node.data[parent_node.children[row]]
            if isinstance(item_data, TableLeaf):
                print(f"{row} - {column} - Value: {TableLeaf.data[column]}")
            elif column == 0:
                item = self._create_table_node(data=parent_node.data[parent_node.children[row]],
                                               text=parent_node.children[row], parent=parent_node)
                return self.createIndex(row, column, item)
            else:
                # TODO: If column = 1: Show the folder size
                return QModelIndex()
        else:
            return QModelIndex()

    def data(self, index, role=...):
        if not index.isValid():
            return QVariant()

        item = index.internalPointer()

        if role == Qt.ItemDataRole.DisplayRole:
            if isinstance(item, dict):
                if index.column() == 0:
                    key = list(item.keys())[index.row()]
                    return key
                else:
                    return "InternThis"
            else:
                return QVariant()
        else:
            return QVariant()

    # def parent(self, index):
    #     if not index.isValid():
    #         return QModelIndex()
    #
    #     child = index.internalPointer()
    #     parentItem = childItem.parent()
    #
    #     if parentItem == self.rootItem:
    #         return QModelIndex()
    #
    #     return self.createIndex(parentItem.row(), 0, parentItem)

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

    @staticmethod
    def _create_table_node(data, parent: ... = None, text: str = None):
        if parent is None:
            # Root Node
            if isinstance(data, list):
                # No Grouping
                # TODO: Icon = Folder
                return TableNode(parent=None, text="", icon=None, children=data, data=data, path="/")
            elif isinstance(data, dict):
                # Some Grouping
                # TODO: Icon = Folder
                return TableNode(parent=None, text="", icon=None, children=list(data.keys()), data=data, path="/")
        else:
            if isinstance(data, dict):
                # TODO: Icon = Folder
                return TableNode(parent=parent, text=text, icon=None, children=list(data.keys()), data=data, path="/")
            else:
                print(data)
                return QVariant()

    @staticmethod
    def _orientation(model_data: list) -> Qt.Orientation:
        if len(model_data) == 1:
            if len(model_data[0].data) == 1:
                print("app.logger.debug --- Displaying in Vertical Mode")
                return Qt.Orientation.Vertical
        print("app.logger.debug --- Displaying in Horizontal Mode")
        return Qt.Orientation.Horizontal

    @staticmethod
    def _build_grouping_model(data: list, group_key: list):
        def add_item(_container: dict, _path: list, _item: dict):
            _group = _path.pop()
            if len(_path) == 0:
                # leaf item
                if _group not in _container:
                    _container[_group] = []
                file_data = None  # TODO:FileData.from_dict(item, item[TableModel._PATH])
                icon = None
                if file_data is not None:
                    icon = get_mime_type_icon(file_data.mime_type)
                _container[_group].append(TableLeaf(icon=icon, data=item))
            else:
                if _group not in _container:
                    _container[_group] = {}
                add_item(_container[_group], _path, _item)

        model = {}
        for item in data:
            path = []
            # Check if each grouping is available in the item and build item specific path
            for group in group_key:
                if group in item:
                    path.insert(0, item[group])
                else:
                    path.insert(0, TableModel._UNKNOWN)
            # Once path is built, add item to model
            add_item(model, path, item)
        return model

    @staticmethod
    def _flatten(model_data: list):
        _flat_list = []
        for item in model_data:
            for _path, entries in item.data.items():
                for entry in entries:
                    _flat_list.append(entry)
        return _flat_list


class TableModelV2(QAbstractItemModel):
    _UNKNOWN = "N/A"
    _PATH = "MediaLib:Path"

    def __init__(self, model_data: list, fields: list, group_key: list):
        super().__init__()
        print(fields)
        self._orientation = self._orientation(model_data)
        self._exif_cols = fields
        self._group_key = group_key
        self._root_node = self._build_grouping_model(self._flatten(model_data), self._group_key)

    # @override
    # def index(self, row, column, parent=...):
    #     if not self.hasIndex(row, column, parent):
    #         return QModelIndex()
    #
    #     if not parent.isValid():
    #         parent_node = self._root_node
    #     else:
    #         parent_node = parent.internalPointer()
    #
    #     if row < len(parent_node.children):
    #         item = parent_node.children[row]
    #         key = self._exif_cols[column]
    #         # TODO: Improve this logic
    #         if isinstance(item, TableNode) and column > 0:
    #             return QModelIndex()
    #         elif isinstance(item, TableNode) and column == 0:
    #             return self.createIndex(row, column, item)
    #         elif isinstance(item, TableLeaf) and key in item.data:
    #             value = item.data[key]
    #             return self.createIndex(row, column, value)
    #         else:
    #             return QModelIndex()
    #     else:
    #         return QModelIndex()

    # @override
    # def data(self, index, role=...):
    #     if not index.isValid():
    #         return QVariant()
    #     # p_index = QPersistentModelIndex(index)
    #     # item = self._QStandardItem_cache.get(p_index)
    #     # if item is not None:
    #     #     return item
    #     item = index.internalPointer()
    #     if role == Qt.ItemDataRole.DisplayRole:
    #         row = index.row()
    #         column = index.column()
    #         if isinstance(item, TableNode) and column > 0:
    #             return QVariant()
    #         elif isinstance(item, TableNode) and column == 0:
    #             return item.text
    #         elif isinstance(item, TableLeaf) and column < len(self._exif_cols):
    #             value = TableLeaf.data[column]
    #             return str(value)
    #         else:
    #             return str(item)
    #     return QVariant()

    # @override
    # def parent(self, index):
    #     if not index.isValid():
    #         return QModelIndex()
    #
    #     child = index.internalPointer()
    #     parent = child.parent
    #
    #     if parent == self._root_node:
    #         return QModelIndex()
    #
    #     return self.createIndex(0, 0, parent)

    @override
    def rowCount(self, parent: QModelIndex = None) -> int:
        return 0
        # if self.orientation == Qt.Orientation.Horizontal:
        #     if not parent.isValid():
        #         parent_node = self._root_node
        #     else:
        #         parent_node = parent.internalPointer()
        #     if isinstance(parent_node, TableNode):
        #         return len(parent_node.children)
        #     else:
        #         return 0
        # else:
        #     return len(self._exif_cols)

    @override
    def columnCount(self, parent: QModelIndex = None) -> int:
        if self.orientation == Qt.Orientation.Horizontal:
            return len(self._exif_cols)
        else:
            return 2

    # @override
    # def canFetchMore(self, index):
    #     if not index.isValid():
    #         return False
    #     item = index.internalPointer()
    #     return False

    @override
    def headerData(self, p_int, p_orientation, role=None):
        if role == Qt.ItemDataRole.DisplayRole:
            if self.orientation == Qt.Orientation.Horizontal:
                if p_orientation == Qt.Orientation.Horizontal and p_int >= 0:
                    return self._exif_cols[p_int]
                elif p_orientation == Qt.Orientation.Vertical:
                    return QVariant()
            else:
                if p_orientation == Qt.Orientation.Horizontal:
                    return QVariant()
                elif p_orientation == Qt.Orientation.Vertical:
                    return self._exif_cols[p_int]

    @property
    def orientation(self):
        return self._orientation

    @staticmethod
    def _orientation(model_data: list) -> Qt.Orientation:
        if len(model_data) == 1:
            if len(model_data[0].data) == 1:
                print("app.logger.debug --- Displaying in Vertical Mode")
                return Qt.Orientation.Vertical
        print("app.logger.debug --- Displaying in Horizontal Mode")
        return Qt.Orientation.Horizontal

    @staticmethod
    def _flatten(model_data: list):
        _flat_list = []
        for item in model_data:
            for _path, entries in item.data.items():
                for entry in entries:
                    _flat_list.append(entry)
        return _flat_list

    @staticmethod
    # TODO: Move to separate helper class to make testing easier
    def _build_grouping_model(data: list, group_key: list):
        def add_item(_container: dict, _path: list, _item: dict):
            _group = _path.pop()
            if len(_path) == 0:
                # leaf item
                if _group not in _container:
                    _container[_group] = []
                file_data = None  # TODO:FileData.from_dict(item, item[TableModel._PATH])
                icon = None
                if file_data is not None:
                    icon = get_mime_type_icon(file_data.mime_type)
                _container[_group].append(TableLeaf(icon=icon, data=_item))
            else:
                if _group not in _container:
                    _container[_group] = {}
                add_item(_container[_group], _path, _item)

        def create_table_node(node_name: str, node_data: ...):
            if isinstance(node_data, dict):
                parent_node = TableNode(node_name, icon=None, parent=None, children=[])
                for sub_key, sub_data in node_data.items():
                    sub_node = create_table_node(node_name=sub_key, node_data=sub_data)
                    parent_node.children.append(sub_node)
                    sub_node.parent = parent_node
                return parent_node
            elif isinstance(node_data, list):
                return TableNode(node_name, icon=None, parent=None, children=node_data)

        model = {}
        if len(group_key) == 0:
            pass

        for item in data:
            path = []
            # Check if each grouping is available in the item and build item specific path
            for group in group_key:
                if group in item:
                    path.insert(0, item[group])
                else:
                    path.insert(0, TableModelV2._UNKNOWN)
            # Once path is built, add item to model
            add_item(model, path, item)

        # Convert the dictionary model to a Tree Model for indexed access
        return create_table_node("", model)


if __name__ == '__main__':
    def line_edit_change():
        if len(line_edit.text()) > 3 or len(line_edit.text()) == 0:
            re = QRegularExpression(line_edit.text(), QRegularExpression.PatternOption.CaseInsensitiveOption)
            if _proxy_model:
                _proxy_model.setFilterRegularExpression(re)


    app = QApplication(sys.argv)
    db = Collection.open_db("/mnt/documents/dev/testing/07-24-Test-Images/")
    main_model_data = []
    for main_path in db.paths:
        main_data = db.data([main_path])
        for main__path, main_entries in main_data.items():
            for main_entry in main_entries:
                # Add path to the entry
                main_entry[TableModelV2._PATH] = main__path
        main_model_data.append(ModelData(data=main_data, path=main_path))
    # something after tag 14 is crashing the view
    tm = TableModelV2(main_model_data, db.tags[20:32], [])

    test = [
        {"a": 1, "b": 2, "c": 3},
        {"a": 4, "b": 5, "c": 6}
    ]

    line_edit = QLineEdit()
    line_edit.textChanged.connect(line_edit_change)
    view = QTreeView()
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
