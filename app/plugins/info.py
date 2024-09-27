from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFontDatabase, QBrush, QColor
from PyQt6.QtWidgets import QDockWidget, QTreeView, QTreeWidget, QAbstractItemView, QTreeWidgetItem

import app
from app import apputils
from app.collection import props
from app.plugins.framework import WindowInfo, FileClickHandler, PluginToolBar


class FileInfoPlugin(QDockWidget, WindowInfo, FileClickHandler):
    # https://stackoverflow.com/questions/1290838/best-qt-widget-to-use-for-properties-window
    # https://stackoverflow.com/questions/21283934/qtreewidget-reordering-child-items-by-dragging

    class PropertyWidget(QTreeWidget):
        _GROUP_BG = QBrush(QColor(183, 182, 181, 75))
        _IS_PROPERTY = "IS-PROPERTY"
        _IS_DEFAULT_LOCATION = "IS-DEFAULT-LOCATION"

        def __init__(self, parent):
            super().__init__(parent)
            self.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
            self.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
            self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.setDragEnabled(True)
            self.viewport().setAcceptDrops(True)
            self.setDropIndicatorShown(True)
            self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
            self.setSortingEnabled(False)
            self.setStyleSheet("QTreeWidget {background-color: palette(window);};")
            ft = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
            ft.setPointSizeF(8)
            self.setFont(ft)
            self._tv_groups = {}
            self._root_prop_count = 0
            self.setColumnCount(2)
            self.setAlternatingRowColors(True)
            self.setHeaderLabels(["Property", "Value"])
            self.setHeaderHidden(True)
            self.itemExpanded.connect(self.resize_columns)

        def show_properties(self, file_data: dict, tags: list):
            self.clear()
            # Create tag groups
            groups = apputils.create_tag_groups(tags)
            if props.DB_TAG_GROUP_DEFAULT in groups:
                for key in groups[props.DB_TAG_GROUP_DEFAULT]:
                    if key in file_data:
                        self._add_property(self.invisibleRootItem(), key, file_data[key], index=self._root_prop_count)
                        self._root_prop_count += 1

            # Add the rest of the items
            for group, keys in sorted(groups.items()):
                if group == props.DB_TAG_GROUP_DEFAULT:
                    continue
                if group == props.DB_TAG_GROUP_SYSTEM:
                    group_node = self._get_group_item(group, index=self._root_prop_count)
                    group_node.setExpanded(True)
                else:
                    group_node = self._get_group_item(group)
                group_is_empty = False
                for key in sorted(keys):
                    field_name = f"{group}:{key}"
                    if field_name in file_data:
                        group_is_empty = group_is_empty or file_data[field_name] is None
                        self._add_property(group_node, key, file_data[field_name])
                group = self._get_group_item(group)
                group.setHidden(group_is_empty)
            self.resize_columns("x")

        def resize_columns(self, _):
            self.resizeColumnToContents(0)
            self.header().setStretchLastSection(True)

        def clear(self):
            root_property = []
            for idx in range(0, self.invisibleRootItem().childCount()):
                item = self.invisibleRootItem().child(idx)
                if self._is_system_added(item):
                    root_property.append(item)
                else:
                    # Item is a group. Clear it completely
                    item.takeChildren()

            for item in root_property:
                self.invisibleRootItem().removeChild(item)
            self._root_prop_count = 0

        def _add_property(self, parent: QTreeWidgetItem, key: str, value, index: int = None):
            # The Item may have been dragged around, so check if it exists in the tree already
            items = self.findItems(key, Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchCaseSensitive)
            value = self._get_text(value)
            if len(items) > 0:
                app.logger.debug(f"{key} has been moved. Reusing existing object")
                item = items[0]
                item.setText(1, value)
                item.setToolTip(1, value)
            else:
                item = QTreeWidgetItem([key, value])
                item.setData(0, Qt.ItemDataRole.UserRole, self._IS_PROPERTY)
                item.setToolTip(1, value)
                if parent == self.invisibleRootItem():
                    # A property has been added to the root as part of the db tags, and not as a result of a user drag
                    item.setData(0, Qt.ItemDataRole.UserRole + 1, self._IS_DEFAULT_LOCATION)
                if isinstance(index, int):
                    parent.insertChild(index, item)
                else:
                    parent.addChild(item)

        def _get_group_item(self, name, is_root_item: bool = False, index: int = None) -> QTreeWidgetItem:
            if name not in self._tv_groups:
                item = QTreeWidgetItem([name])
                item.setFirstColumnSpanned(not is_root_item)
                item.setBackground(0, self._GROUP_BG)
                self._tv_groups[name] = item
                if isinstance(index, int):
                    self.invisibleRootItem().insertChild(index, item)
                else:
                    self.invisibleRootItem().addChild(item)

            return self._tv_groups[name]

        @staticmethod
        def _get_text(value):
            if value is None:
                value = ""
            else:
                if not isinstance(value, str):
                    value = f"{str(value)} ({type(value).__name__})"
            return value

        def _is_system_added(self, item: QTreeWidgetItem) -> bool:
            return (item.data(0, Qt.ItemDataRole.UserRole) == self._IS_PROPERTY
                    and item.data(0, Qt.ItemDataRole.UserRole + 1) == self._IS_DEFAULT_LOCATION)

    @property
    def dockwidget_area(self):
        return Qt.DockWidgetArea.RightDockWidgetArea

    @property
    def name(self) -> str:
        return "File Information"

    @property
    def is_visible_on_start(self) -> bool:
        return True

    def handle_file_click(self, file_data: list, fields: list):
        self._property_widget.show_properties(file_data[0].data, fields)

    def windowIcon(self) -> QIcon:
        return self.icon

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setWindowTitle("File Information")
        self._property_widget = self.PropertyWidget(parent)
        self.setWidget(self._property_widget)
        self._toolbar = PluginToolBar(self, self.name)
        self.setTitleBarWidget(self._toolbar)

    @property
    def statustip(self) -> str:
        return "Provide detailed information about the selected file"

    @property
    def icon(self) -> QIcon:
        return QIcon.fromTheme("dialog-information")

    @property
    def shortcut(self) -> str:
        return "F5"
