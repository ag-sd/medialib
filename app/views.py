from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, QPersistentModelIndex, QSortFilterProxyModel, \
    QRegularExpression, QObject, pyqtSignal
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt6.QtWidgets import QTreeView, QTableView, QAbstractItemView

import app
from app.collection import props
from app.plugins.framework import FileData

_NO_DATA_MESSAGE = "Message: No Data to Show!"

_MIME_ICON_DIRECTORY = "inode-directory"
_MIME_ICON_COLLECTION_ROOT = "folder-library"
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
class ModelReference:
    data: ...
    root: str


class ViewCreationError(Exception):
    def __init__(self, message: str):
        super().__init__(f"The view creation failed with the following message:\n {message}")


class ModelManager(QObject):
    MODELMANAGER_FILE_DATA_ROLE = Qt.ItemDataRole.UserRole + 20

    # Note: Subclasses must explicitly implement this signal
    file_click = pyqtSignal(FileData)

    def __init__(self, parent):
        super().__init__(parent=parent)
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

    def _clicked(self, index):
        source_index = self._proxy_model.mapToSource(index)
        item = self._proxy_model.sourceModel().itemFromIndex(source_index)
        if item is not None:
            file_data = item.data(self.MODELMANAGER_FILE_DATA_ROLE)
            if file_data is not None:
                app.logger.debug(f"Emitting file event {file_data}")
                self.file_click.emit(file_data)

    @staticmethod
    def set_file_data(item: QStandardItem, file_data: FileData):
        item.setData(file_data, ModelManager.MODELMANAGER_FILE_DATA_ROLE)


class FileSystemView(QTreeView, ModelManager):
    """
    Filesystem view is a mix of the JSON view and the Table View
    """

    def set_model(self, model_data: list, fields: list | None):
        p_model = self.LazyJsonModel(model_data, fields, self)
        self.setModel(self._create_proxy_model(p_model))
        for i in range(0, self.model().columnCount()):
            self.resizeColumnToContents(i)

    file_click = pyqtSignal(FileData)

    def __init__(self, parent):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        # self.setShowGrid(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        # self.verticalHeader().setHighlightSections(False)
        # self.verticalHeader().setSectionsMovable(True)
        # self.verticalHeader().setSectionsClickable(True)
        # self.horizontalHeader().setHighlightSections(False)
        # self.horizontalHeader().setSectionsMovable(True)
        # self.horizontalHeader().setSectionsClickable(True)
        self.setSortingEnabled(True)
        self.clicked.connect(self._clicked)

    class LazyJsonModel(QStandardItemModel):
        """
        This is a lazy model and will only build nodes if the user expands something
        """

        def __init__(self, model_data: list, fields: list, parent=None):
            super().__init__(parent)
            self._fields = set(fields)
            self._file_system = {}
            if len(model_data) == 0:
                # No data to show
                self.setColumnCount(1)
                self.setHeaderData(0, Qt.Orientation.Horizontal, _NO_DATA_MESSAGE)
            else:
                self.setColumnCount(len(fields))
                self.setHorizontalHeaderLabels(fields)
                for _node in model_data:
                    self._build_file_hierarchy(reference_path=_node.path, path_data=_node.data)
                    self.invisibleRootItem().appendRow(self._create_directory_row(ModelReference(
                        data=_node.path, root=_node.path), is_collection_root=True))

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
                if isinstance(item_data, ModelReference):
                    item_can_have_children = len(self._file_system[item_data.data]) > 0
                return item.hasChildren() or item_can_have_children
            return super().rowCount(parent)

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
                if isinstance(item_data, ModelReference):
                    child_count = len(self._file_system[item_data.data])
                # If it already has children or does not have children at all, return false
                return not (item.hasChildren() or child_count == 0)
            return super().rowCount(index)

        def fetchMore(self, parent):
            """
            If the parent has children, this method will insert them under the parent if not already done
            Args:
                parent: The node to evaluate for children
            """
            item = self.itemFromIndex(parent)
            if item is not None:
                item_data = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(item_data, ModelReference):
                    children = self._file_system[item_data.data]
                    for key, value in children.items():
                        if isinstance(value, ModelReference):
                            # Item is a directory
                            item.appendRow(self._create_directory_row(value))
                        else:
                            # Item is a file
                            item.appendRow(self._create_file_row(value, item_data.root))
                    return

            super().fetchMore(parent)

        def _build_file_hierarchy(self, path_data: list, reference_path: str, ):
            for record in path_data:
                # Check if the data represents a file_system. In order for a file_system view, a FileData
                # object should be composable from the path data
                file_data = FileData.from_dict(record, reference_path)
                if file_data is None:
                    raise ViewCreationError("Unable to create the view "
                                            "because at least one record does not represent a file")
                self._ensure_path(file_data.directory)
                # Add the record to the file_system
                self._file_system[file_data.directory][file_data.file_name] = record
                # Start capturing the path ancestry
                current_dir = file_data.directory
                while current_dir != reference_path and current_dir != "":
                    p_current_dir = Path(current_dir)
                    dir_name = str(p_current_dir.name)
                    dir_path = str(p_current_dir.parent)
                    self._ensure_path(dir_path)
                    self._file_system[dir_path][dir_name] = ModelReference(str(current_dir), reference_path)
                    current_dir = dir_path

        def _ensure_path(self, path):
            if path not in self._file_system:
                self._file_system[path] = {}

        def _create_file_row(self, file_data: dict, root_path: str):
            row = []
            file_data_obj = FileData.from_dict(file_data, root_path=root_path)
            for col in range(0, self.columnCount()):
                col_name = self.horizontalHeaderItem(col).text()
                if col == 0 and col_name == props.FIELD_SOURCE_FILE:
                    row.append(QStandardItem(file_data_obj.file_name))
                    continue

                if col_name in file_data:
                    row.append(QStandardItem(str(file_data[col_name])))
                else:
                    row.append(QStandardItem(""))

            row[0].setIcon(get_mime_type_icon(file_data_obj.mime_type))
            ModelManager.set_file_data(row[0], file_data_obj)
            return row

        @staticmethod
        def _create_directory_row(directory_data: ModelReference, is_collection_root: bool = False):
            if is_collection_root:
                std_item = QStandardItem(directory_data.data)
                std_item.setIcon(get_mime_type_icon(_MIME_ICON_COLLECTION_ROOT))
            else:
                p_dir_name = Path(directory_data.data)
                std_item = QStandardItem(p_dir_name.name)
                std_item.setIcon(get_mime_type_icon(_MIME_ICON_DIRECTORY))
            std_item.setData(directory_data, Qt.ItemDataRole.UserRole)
            return std_item

        @staticmethod
        def _get_branch(tree, branch):
            if branch not in tree:
                tree[branch] = {}
            return tree[branch]

        @staticmethod
        def _standard_item(text, data, icon: QIcon = None, file_data: FileData = None):
            std_item = QStandardItem(text)
            std_item.setData(data, Qt.ItemDataRole.UserRole)
            if isinstance(icon, QIcon):
                std_item.setIcon(icon)
            ModelManager.set_file_data(std_item, file_data)
            return std_item


class JsonView(QTreeView, ModelManager):
    file_click = pyqtSignal(FileData)

    class LazyJsonModel(QStandardItemModel):
        """
        This is a lazy model and will only build nodes if the user expands something
        """

        def __init__(self, model_data: list, fields: list = None, parent=None):
            super().__init__(parent)
            self._fields = set(fields) if fields is not None else None
            if len(model_data) == 0:
                # No data to show
                self.setColumnCount(1)
                self.setHeaderData(0, Qt.Orientation.Horizontal, _NO_DATA_MESSAGE)
            else:
                self.setColumnCount(2)
                self.setHeaderData(0, Qt.Orientation.Horizontal, "Key")
                self.setHeaderData(1, Qt.Orientation.Horizontal, "Data")
                for _node in model_data:
                    self._add_child(self.invisibleRootItem(), _node.path, _node.data, _node.path,
                                    get_mime_type_icon(_MIME_ICON_COLLECTION_ROOT))

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
                if isinstance(item_data, ModelReference):
                    if isinstance(item_data.data, dict) or isinstance(item_data.data, list):
                        child_count = len(item_data.data)
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
                if isinstance(item_data, ModelReference):
                    if isinstance(item_data.data, dict) or isinstance(item_data.data, list):
                        item_can_have_children = len(item_data.data) > 0
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
                if isinstance(item_data, ModelReference):
                    if isinstance(item_data.data, dict):
                        for key, value in item_data.data.items():
                            if self._fields:
                                if key in self._fields:
                                    self._add_child(item, key, value, item_data.root)
                            else:
                                self._add_child(item, key, value, item_data.root)
                    elif isinstance(item_data.data, list):
                        for index, value in enumerate(item_data.data):
                            self._add_child(item, f"[{index}]", value, item_data.root)
                    return

            super().fetchMore(parent)

        def _add_child(self, root: QStandardItem, key: str, value, root_path: str, icon: QIcon = None):
            if isinstance(value, list):
                # List
                root.appendRow([self._standard_item(key, value, root_path, icon), QStandardItem(f"{len(value)} items")])
            elif isinstance(value, dict):
                # Dictionary
                file_data = FileData.from_dict(value, root_path)
                misc_data = ""
                if file_data is not None:
                    icon = get_mime_type_icon(file_data.mime_type)
                    key = file_data.file_name
                    misc_data = file_data.file_size
                root.appendRow([self._standard_item(key, value, root_path, icon, file_data), QStandardItem(misc_data)])
            else:
                # Node value
                root.appendRow([QStandardItem(key), QStandardItem(str(value))])

        @staticmethod
        def _standard_item(text, data, root_path: str, icon: QIcon = None, file_data: FileData = None):
            std_item = QStandardItem(text)
            std_item.setData(ModelReference(data=data, root=root_path), Qt.ItemDataRole.UserRole)
            if isinstance(icon, QIcon):
                std_item.setIcon(icon)
            ModelManager.set_file_data(std_item, file_data)
            return std_item

    def set_model(self, model_data: list, fields: list | None):
        _source_model = JsonView.LazyJsonModel(model_data, fields, self.parent())
        self.setModel(self._create_proxy_model(_source_model))
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)

    def __init__(self, parent):
        super().__init__(parent)
        self.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.clicked.connect(self._clicked)


class TableView(QTableView, ModelManager):
    # https://stackoverflow.com/questions/57764723/make-an-active-search-with-qlistwidget
    # https://stackoverflow.com/questions/20563826/pyqt-qtableview-search-by-hiding-rows

    file_click = pyqtSignal(FileData)

    class TableModel(QAbstractTableModel):
        def __init__(self, model_data: list, fields: list):
            super().__init__()
            self._exif_data = []
            self._exif_cols = fields
            self._QStandardItem_cache = {}
            self._orientation = self._orientation(model_data)

            for data in model_data:
                for entry in data.data:
                    self._exif_data.append(ModelReference(data=entry, root=data.path))

            if len(self._exif_data) == 0:
                # No data.
                app.logger.info("No data to show.")
                self._exif_cols = [_NO_DATA_MESSAGE]

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

        def itemFromIndex(self, index: QModelIndex):
            return self.item(self.createIndex(index.row(), 0))

        def item(self, index: QModelIndex):
            if not index.isValid():
                return QVariant()

            p_index = QPersistentModelIndex(index)
            item = self._QStandardItem_cache.get(p_index)
            if item is None:
                if self.orientation == Qt.Orientation.Horizontal:
                    row = self._exif_data[index.row()]
                    col = self._exif_cols[index.column()]
                    if col in row.data:
                        item = QStandardItem(str(row.data[col]))
                        if index.column() == 0:
                            file_data = FileData.from_dict(row.data, row.root)
                            if file_data is not None:
                                icon = get_mime_type_icon(file_data.mime_type)
                                item.setIcon(icon)
                                ModelManager.set_file_data(item, file_data)
                else:
                    key = self._exif_cols[index.row()]
                    if key in self._exif_data[0]:
                        item = QStandardItem(str(self._exif_data[0][key]))
                    else:
                        app.logger.warning(f"tag:{key} not present in current dataset. Will cache a null for it")
                        item = QVariant()
                if item is not None:
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
        self.clicked.connect(self._clicked)

    def set_model(self, model_data: list, fields: list):
        p_model = self.TableModel(model_data, fields)
        self.setModel(self._create_proxy_model(p_model))
        if len(fields) < 20 or self.model().rowCount() < 20:
            self.resizeColumnsToContents()


class ViewType(Enum):
    TABLE = TableView, "text-csv", "Display information as a table"
    JSON = JsonView, "application-json", ("Display information in JSON (JavaScript Object "
                                          "Notation) formatting")
    FILE_SYSTEM = FileSystemView, "system-file-manager", "Display information as a File System"

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


import sys
from PyQt6.QtWidgets import QApplication
from app.collection.ds import Collection
test_app = QApplication(sys.argv)
_fs_view = FileSystemView(parent=None)

db = Collection.open_db("/mnt/dev/testing/Medialib/image-picka/")
model_data = []
for path in db.paths:
    model_data.append(ModelData(data=db.data(path), path=path))

_fs_view.set_model(model_data, db.tags)
_fs_view.setMinimumSize(500, 1000)
_fs_view.show()
sys.exit(test_app.exec())


