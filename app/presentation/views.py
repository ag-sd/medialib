from abc import abstractmethod

import tablib
from PyQt6.QtCore import pyqtSignal, QSortFilterProxyModel, Qt, QRegularExpression
from PyQt6.QtGui import QPalette, QPen
from PyQt6.QtWidgets import QAbstractItemView, QTableView, QTreeView, QStyledItemDelegate

from app.collection import props
from app.presentation.models import ColumnModel, TableModel, ViewItem, TreeModel, GroupTreeItemBuilder, \
    FileSystemModelBuilder


class View(QAbstractItemView):
    item_click = pyqtSignal(dict, "PyQt_PyObject", str)

    @abstractmethod
    def show_data(self, **kwargs):
        raise NotImplemented

    @abstractmethod
    def clear(self):
        raise NotImplemented

    @abstractmethod
    def item_proxy_model(self) -> QSortFilterProxyModel:
        raise NotImplemented

    def find_text(self, text):
        re = QRegularExpression(text, QRegularExpression.PatternOption.CaseInsensitiveOption)
        self.item_proxy_model().setFilterRegularExpression(re)

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
            file_data = None
            if props.FIELD_COLLECTION_FILEDATA in sel:
                file_data = sel[props.FIELD_COLLECTION_FILEDATA]
            self.item_click.emit(sel, file_data, sel[props.FIELD_COLLECTION_PATH])

    def _get_selection_items(self, proxy_model_indices: list):
        selection = []
        for index in proxy_model_indices:
            source_index = self.item_proxy_model().mapToSource(index)
            item = self.item_proxy_model().sourceModel().data(source_index, Qt.ItemDataRole.UserRole)
            if isinstance(item, ViewItem) and item.is_leaf_item:
                selection.append(item.data)
        return selection

    def to_dataset(self):
        headers = []
        for i in range(0, self.item_proxy_model().columnCount()):
            headers.append(self.item_proxy_model().headerData(i, Qt.Orientation.Horizontal))

        data = tablib.Dataset(headers=headers)
        print(data.export("csv"))
        print(self.item_proxy_model().rowCount())


class TableView(QTableView, View):
    item_click = pyqtSignal(dict, "PyQt_PyObject", str)

    def show_data(self, **kwargs):
        group_by = kwargs["group_by"]
        if group_by is not None and len(group_by) > 0:
            raise ValueError("Table view does not support groups")
        p_model = TableModel(kwargs["view_items"], kwargs["fields"])
        self.setModel(self._create_proxy_model(self, p_model))
        self.resizeColumnToContents(0)

    def clear(self):
        self.setModel(None)

    def item_proxy_model(self):
        return self.model()

    # https://stackoverflow.com/questions/57764723/make-an-active-search-with-qlistwidget
    # https://stackoverflow.com/questions/20563826/pyqt-qtableview-search-by-hiding-rows

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

    def show_data(self, **kwargs):
        view_items = kwargs["view_items"]
        p_model = ColumnModel(view_items, kwargs["fields"])
        self.setModel(self._create_proxy_model(self, p_model))
        self.resizeColumnToContents(0)


class SpanDelegate(QStyledItemDelegate):

    def __init__(self, parent):
        super().__init__(parent=parent)
        color = QPalette().color(QPalette.ColorGroup.Normal, QPalette.ColorRole.Text)
        color.setAlpha(75)
        self._pen = QPen(color)

    def paint(self, painter, option, index):
        model = self.parent().item_proxy_model()
        source_index = model.mapToSource(index)
        data = model.sourceModel().data(source_index, Qt.ItemDataRole.UserRole)
        super().paint(painter, option, index)
        if not data.is_leaf_item:
            painter.save()
            painter.setPen(self._pen)
            painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
            painter.restore()


class SpanningTreeview(QTreeView, View):
    # TODO: Draw line under groups and paths
    # https://stackoverflow.com/questions/76822541/how-do-i-put-a-bold-line-under-certain-rows-in-a-qtabwidget

    item_click = pyqtSignal(dict, "PyQt_PyObject", str)

    def show_data(self, **kwargs):
        p_model = TreeModel(GroupTreeItemBuilder().build(**kwargs), kwargs["fields"])
        proxy_model = self._create_proxy_model(self, p_model)
        proxy_model.setRecursiveFilteringEnabled(True)
        self.setModel(proxy_model)
        self.resizeColumnToContents(0)

    def clear(self):
        self.setModel(None)

    def item_proxy_model(self):
        return self.model()

    def __init__(self, parent):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)  # Allows for scrolling optimizations.
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.setSortingEnabled(True)
        self.clicked.connect(self._clicked)
        self.setItemDelegate(SpanDelegate(self))
        self._grouping = []

    def drawRow(self, painter, options, index):
        if index.isValid():
            item = self.model().data(index, Qt.ItemDataRole.UserRole)
            if not item.is_leaf_item:
                self.setFirstColumnSpanned(index.row(), self.model().parent(index), True)
        super().drawRow(painter, options, index)


class FileSystemTreeView(SpanningTreeview):

    def show_data(self, **kwargs):
        p_model = TreeModel(FileSystemModelBuilder().build(**kwargs), kwargs["fields"])
        proxy_model = self._create_proxy_model(self, p_model)
        proxy_model.setRecursiveFilteringEnabled(True)
        self.setModel(proxy_model)
        self.resizeColumnToContents(0)
