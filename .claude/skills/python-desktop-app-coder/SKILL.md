---
name: python-desktop-app-coder
description: Use this skill when building, maintaining, or testing Python desktop applications with PyQt6/PyQt5/PySide6. Activates for tasks involving Qt widgets, signals/slots, Qt threading, desktop UI architecture, pytest-qt testing, or QAbstractItemModel implementations.
---

# Python Desktop Application Development with PyQt6

This skill provides patterns and best practices for building professional Python desktop applications using PyQt6, based on proven patterns from production applications.

## 1. Architecture Principles

### Layer Separation

Structure your application in distinct layers to maintain separation of concerns:

```
┌─────────────────────────────────────┐
│  Presentation (PyQt6 Views/Models)  │  UI widgets, Qt models, delegates
├─────────────────────────────────────┤
│  Business Logic (Actions, Tasks)    │  Application logic, task management
├─────────────────────────────────────┤
│  Data Layer (Collections, Cache)    │  Data access, caching, persistence
├─────────────────────────────────────┤
│  External (CLI tools, databases)    │  External process/service wrappers
└─────────────────────────────────────┘
```

**Key principles:**
- Presentation layer only handles display and user input
- Business logic is testable without Qt dependencies
- Data layer abstracts storage implementation
- External wrappers isolate third-party dependencies

### Testability First

- Use **dataclasses** for pure data structures (no Qt dependencies)
- Separate **builders** from Qt models—builders transform data, models render it
- Keep business logic in plain Python classes that can be unit tested

### Signal Flow

- Use hierarchical event routing with domain objects
- Main window connects high-level signals; managers handle details
- Pass domain objects (not raw data) through signals for type safety

---

## 2. Threading & Concurrency

### The QRunnable + QThreadPool Pattern (NOT QThread)

For background tasks, use `QRunnable` with `QThreadPool`. This pattern is simpler and more efficient than subclassing `QThread`.

**Critical insight:** `QRunnable` cannot have signals directly. Compose a `QObject` inside your `QRunnable` to emit signals.

### TaskWorker Pattern

```python
from dataclasses import dataclass
from enum import StrEnum
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool


class TaskStatus(StrEnum):
    STARTED = "STARTED"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class Task:
    id: str
    args: dict
    status: TaskStatus
    time_taken: float
    result: ...
    error: ...


class TaskWorkerSignals(QObject):
    """QObject to hold signals - QRunnable cannot have signals directly."""
    status = pyqtSignal("PyQt_PyObject")
    thread_complete = pyqtSignal("PyQt_PyObject")


class TaskWorker(QRunnable):
    """Background task executor using QThreadPool."""

    def __init__(self, task_name: str, function, **kwargs):
        super().__init__()
        self._function = function
        self._kwargs = kwargs
        self._id = task_name
        self.signals = TaskWorkerSignals()  # Composed QObject for signals

    def run(self):
        """Execute the task in a background thread."""
        import datetime
        start_time = datetime.datetime.now()
        try:
            result = self._function(**self._kwargs)
            status = TaskStatus.COMPLETED
            error = None
        except Exception as e:
            result = None
            status = TaskStatus.FAILED
            error = e
        finally:
            runtime = (datetime.datetime.now() - start_time).total_seconds()
            self.signals.thread_complete.emit(
                Task(id=self._id, status=status, time_taken=runtime,
                     result=result, error=error, args=self._kwargs)
            )
```

### TaskManager Pattern

A centralized manager that tracks tasks and provides progress UI:

```python
import queue
from PyQt6.QtWidgets import QWidget, QProgressBar, QHBoxLayout


class TaskManager(QWidget):
    """Manages background tasks with progress indication."""
    work_complete = pyqtSignal(Task)

    def __init__(self, parent):
        super().__init__(parent=parent)
        self._tasks_queue = queue.Queue()
        self._progressbar = QProgressBar()
        self._progressbar.setMinimum(0)
        self._progressbar.setMaximum(0)  # Indeterminate progress
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._progressbar)
        self._progressbar.setVisible(False)
        self.setLayout(layout)

    def _thread_complete(self, task: Task):
        self._tasks_queue.get()
        if self._tasks_queue.qsize() == 0:
            self._progressbar.setVisible(False)
        self.work_complete.emit(task)

    def start_task(self, task_name: str, work_func, kwargs: dict = None):
        """Start a background task."""
        worker = TaskWorker(task_name, work_func, **(kwargs or {}))
        worker.signals.thread_complete.connect(self._thread_complete)
        self._tasks_queue.put(worker)
        self._progressbar.setVisible(True)
        QThreadPool.globalInstance().start(worker)

    @property
    def active_tasks(self) -> int:
        return self._tasks_queue.qsize()
```

### Anti-pattern: Never emit signals directly from QRunnable

```python
# WRONG - QRunnable cannot have signals
class BadWorker(QRunnable):
    finished = pyqtSignal()  # This won't work!

# CORRECT - Use composed QObject
class GoodWorker(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = TaskWorkerSignals()  # QObject holds the signals
```

---

## 3. Model/View Architecture

### ViewItem Dataclass

Use a pure Python dataclass for your tree/list data structure:

```python
from dataclasses import dataclass, field
from typing import Optional, Any
from PyQt6.QtGui import QIcon


@dataclass
class ViewItem:
    """Pure Python tree node - no Qt model dependencies."""
    icon: QIcon | None
    parent: Optional['ViewItem']
    data: dict | None
    row: int = 0
    text: str = ""
    _children: list = field(default_factory=list)

    @property
    def children(self) -> list:
        return self._children

    @property
    def is_leaf_item(self) -> bool:
        return self.row_count == 0 and self.data is not None

    @property
    def row_count(self) -> int:
        return len(self._children)

    @property
    def display_text(self) -> str:
        s = "items" if self.row_count != 1 else "item"
        return f"{self.text}  ({self.row_count} {s})"

    def add_child(self, child: 'ViewItem'):
        child.parent = self
        child.row = self.row_count
        self._children.append(child)
```

### Builder Pattern

Separate data transformation from Qt rendering:

```python
from abc import abstractmethod


class ModelBuilder:
    """Base class for data transformation builders."""

    @abstractmethod
    def build(self, **kwargs) -> Any:
        raise NotImplementedError


class BaseViewBuilder(ModelBuilder):
    """Transforms raw data into flat ViewItem list."""

    def __init__(self):
        self._model_data: list = []
        self._collection_paths: list = []

    @property
    def data(self) -> list:
        return self._model_data

    def build(self, **kwargs):
        _flat_list = []
        for item in kwargs["model_data"]:
            # Transform each data item into a ViewItem
            view_item = ViewItem(
                icon=self._get_icon(item),
                parent=None,
                data=item.data
            )
            _flat_list.append(view_item)
        self._model_data = _flat_list


class GroupTreeItemBuilder(ModelBuilder):
    """Builds hierarchical tree grouped by specified fields."""

    def build(self, **kwargs) -> ViewItem:
        return self._build_tree("", kwargs["group_by"], kwargs["view_items"])

    def _build_tree(self, group_path: str, grouping: list,
                    data: list, grouping_index: int = 0) -> ViewItem:
        current_node = ViewItem(icon=None, parent=None, data=None, text=group_path)

        if grouping_index < len(grouping):
            group = grouping[grouping_index]
            keys = {}
            for item in data:
                key = item.data.get(group, "N/A")
                if key not in keys:
                    keys[key] = []
                keys[key].append(item)

            for key, value in keys.items():
                child = self._build_tree(key, grouping, value, grouping_index + 1)
                current_node.add_child(child)
        else:
            for item in data:
                current_node.add_child(item)

        return current_node
```

### Qt Models with internalPointer()

For tree models, use `internalPointer()` to store your `ViewItem`:

```python
from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt


class TreeModel(QAbstractItemModel):
    """Qt tree model backed by ViewItem hierarchy."""

    def __init__(self, root_node: ViewItem, fields: list):
        super().__init__()
        self._root_node = root_node
        self._fields = fields

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return parent.internalPointer().row_count
        return self._root_node.row_count

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._fields)

    def index(self, row: int, column: int, parent=QModelIndex()) -> QModelIndex:
        if not parent.isValid():
            node = self._root_node
        else:
            node = parent.internalPointer()

        if 0 <= row < node.row_count:
            child = node.children[row]
            return self.createIndex(row, column, child)  # Store ViewItem
        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        if index.isValid():
            parent = index.internalPointer().parent
            if parent:
                return self.createIndex(parent.row, 0, parent)
        return QModelIndex()

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        node = index.internalPointer()

        if role == Qt.ItemDataRole.DisplayRole:
            if not node.is_leaf_item:
                return node.display_text if index.column() == 0 else None
            key = self._fields[index.column()]
            return node.data.get(key)

        elif role == Qt.ItemDataRole.DecorationRole and index.column() == 0:
            return node.icon

        elif role == Qt.ItemDataRole.UserRole:
            return node  # Return full ViewItem for selection handling

        return None
```

### QPersistentModelIndex Caching

For large datasets, cache `QStandardItem` objects:

```python
from PyQt6.QtCore import QPersistentModelIndex
from PyQt6.QtGui import QStandardItem


class TableModel(QAbstractTableModel):
    def __init__(self, items: list, fields: list):
        super().__init__()
        self._data = items
        self._fields = fields
        self._cache = {}  # QPersistentModelIndex -> QStandardItem

    def item(self, index: QModelIndex) -> QStandardItem:
        if not index.isValid():
            return None

        p_index = QPersistentModelIndex(index)
        item = self._cache.get(p_index)

        if item is None:
            # Create and cache the item
            row_data = self._data[index.row()]
            col_key = self._fields[index.column()]
            item = QStandardItem(str(row_data.data.get(col_key, "")))
            self._cache[p_index] = item

        return item
```

---

## 4. View Composition

### Mixin Pattern for Protocol Adherence

Define a protocol (abstract base) and use mixins:

```python
from abc import abstractmethod
from PyQt6.QtCore import pyqtSignal, QSortFilterProxyModel
from PyQt6.QtWidgets import QAbstractItemView, QTableView, QTreeView


class View(QAbstractItemView):
    """Protocol for all data views."""
    item_click = pyqtSignal(dict, "PyQt_PyObject", str)

    @abstractmethod
    def show_data(self, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def clear(self):
        raise NotImplementedError

    @abstractmethod
    def item_proxy_model(self) -> QSortFilterProxyModel:
        raise NotImplementedError

    def find_text(self, text: str):
        """Filter view by text pattern."""
        from PyQt6.QtCore import QRegularExpression
        regex = QRegularExpression(
            text, QRegularExpression.PatternOption.CaseInsensitiveOption
        )
        self.item_proxy_model().setFilterRegularExpression(regex)


class TableView(QTableView, View):
    """Table view with View protocol mixin."""
    item_click = pyqtSignal(dict, "PyQt_PyObject", str)

    def __init__(self, parent):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSortingEnabled(True)
        self.clicked.connect(self._clicked)

    def show_data(self, **kwargs):
        model = TableModel(kwargs["view_items"], kwargs["fields"])
        proxy = self._create_proxy_model(self, model)
        self.setModel(proxy)

    def clear(self):
        self.setModel(None)

    def item_proxy_model(self) -> QSortFilterProxyModel:
        return self.model()
```

### Custom Delegates

Use `QStyledItemDelegate` for custom rendering:

```python
from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtGui import QPen, QPalette


class SpanDelegate(QStyledItemDelegate):
    """Draw separator lines under group headers."""

    def __init__(self, parent):
        super().__init__(parent=parent)
        color = QPalette().color(QPalette.ColorGroup.Normal, QPalette.ColorRole.Text)
        color.setAlpha(75)
        self._pen = QPen(color)

    def paint(self, painter, option, index):
        super().paint(painter, option, index)

        # Get the actual data item
        model = self.parent().item_proxy_model()
        source_index = model.mapToSource(index)
        data = model.sourceModel().data(source_index, Qt.ItemDataRole.UserRole)

        # Draw line under non-leaf items
        if not data.is_leaf_item:
            painter.save()
            painter.setPen(self._pen)
            painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
            painter.restore()
```

### Row Spanning for Group Headers

Use `setFirstColumnSpanned()` in tree views:

```python
class SpanningTreeView(QTreeView, View):
    def drawRow(self, painter, options, index):
        if index.isValid():
            item = self.model().data(index, Qt.ItemDataRole.UserRole)
            if not item.is_leaf_item:
                self.setFirstColumnSpanned(
                    index.row(),
                    self.model().parent(index),
                    True
                )
        super().drawRow(painter, options, index)
```

### Selection Handling with Proxy Models

Always map proxy indices to source indices:

```python
def get_selected_items(self) -> list:
    """Extract selected items, handling proxy model mapping."""
    selection = []
    for proxy_index in self.selectionModel().selectedRows():
        source_index = self.item_proxy_model().mapToSource(proxy_index)
        item = self.item_proxy_model().sourceModel().data(
            source_index, Qt.ItemDataRole.UserRole
        )
        if isinstance(item, ViewItem) and item.is_leaf_item:
            selection.append(item.data)
    return selection
```

---

## 5. Signal/Slot Best Practices

### Naming Conventions

- **Signals are nouns** describing what happened: `work_complete`, `item_click`, `data_loaded`
- **Slots are verbs** describing the action: `_on_item_clicked`, `_handle_completion`, `_update_view`

```python
class TaskManager(QWidget):
    # Signals (nouns - what happened)
    work_complete = pyqtSignal(Task)
    status_changed = pyqtSignal(str)

    # Slots (verbs - what to do)
    def _on_thread_complete(self, task: Task):
        pass

    def _handle_status_update(self, message: str):
        pass
```

### Type Safety with PyQt_PyObject

Use `"PyQt_PyObject"` for custom Python objects in signals:

```python
from PyQt6.QtCore import pyqtSignal

class MyWidget(QWidget):
    # For custom Python objects, use PyQt_PyObject
    item_selected = pyqtSignal("PyQt_PyObject")  # Will pass any Python object
    data_loaded = pyqtSignal("PyQt_PyObject", str)  # Object + string

    # For standard types, use the type directly
    count_changed = pyqtSignal(int)
    text_updated = pyqtSignal(str)
```

### Connection Hierarchy

- **Main window** connects high-level orchestration signals
- **Managers** connect to their domain-specific components
- **Widgets** emit signals upward; they don't know their parents

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.task_manager = TaskManager(self)
        self.view_manager = ViewManager(self)

        # Main window orchestrates high-level flow
        self.task_manager.work_complete.connect(self._on_work_complete)
        self.view_manager.item_selected.connect(self._on_item_selected)

    def _on_work_complete(self, task: Task):
        # Dispatch to appropriate manager
        self.view_manager.update_data(task.result)
```

### Thread Safety

Qt automatically marshals signals across threads:

```python
# Signal emitted from background thread (TaskWorker.run)
self.signals.thread_complete.emit(task)

# Connected slot runs in the receiver's thread (main thread)
task_manager.work_complete.connect(self._update_ui)  # Safe!
```

---

## 6. Testing with pytest-qt

### QApplication Singleton

Qt requires exactly one `QApplication` instance. Create it once at test module import:

```python
# tests/__init__.py
import sys
from PyQt6.QtWidgets import QApplication

# Single instance for all tests - Qt requires exactly one
test_app = QApplication(sys.argv)
```

### Test Organization Strategy

1. **Unit tests for dataclasses/builders** - No Qt dependencies
2. **Integration tests for models** - Test with mock data
3. **Widget tests with qtbot** - Full UI interaction

```python
import unittest
import tempfile

class TestViewItem(unittest.TestCase):
    """Unit tests - no Qt dependencies needed."""

    def test_display_text_singular(self):
        parent = ViewItem(icon=None, text="Group", parent=None, data=None)
        child = ViewItem(icon=None, text="Item", parent=None, data={})
        parent.add_child(child)

        self.assertEqual("Group  (1 item)", parent.display_text)

    def test_display_text_plural(self):
        parent = ViewItem(icon=None, text="Group", parent=None, data=None)
        parent.add_child(ViewItem(icon=None, text="A", parent=None, data={}))
        parent.add_child(ViewItem(icon=None, text="B", parent=None, data={}))

        self.assertEqual("Group  (2 items)", parent.display_text)

    def test_parent_child_relationship(self):
        parent = ViewItem(icon=None, text="Parent", parent=None, data=None)
        child = ViewItem(icon=None, text="Child", parent=None, data={})
        parent.add_child(child)

        self.assertEqual(parent, child.parent)
        self.assertEqual(0, child.row)
        self.assertEqual(1, parent.row_count)


class TestBaseViewBuilder(unittest.TestCase):
    """Integration tests for builders."""

    def setUp(self):
        self._builder = BaseViewBuilder()

    def test_build_empty(self):
        self._builder.build(model_data=[])
        self.assertEqual(0, len(self._builder.data))

    def test_build_with_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test data...
            self._builder.build(model_data=test_data)
            self.assertGreater(len(self._builder.data), 0)
```

### Signal Testing Pattern

Connect a callback and verify it was called:

```python
class TestFindWidget(unittest.TestCase):
    def setUp(self):
        self._widget = FindWidget(None)

    def test_signal_emission(self):
        received = []

        def callback(text):
            received.append(text)

        self._widget.find_event.connect(callback)
        self._widget._find_text.setText("search term")

        # Verify signal was emitted with correct value
        self.assertEqual(1, len(received))
        self.assertEqual("search term", received[0])
```

### Using pytest-qt's qtbot

```python
import pytest

def test_button_click(qtbot):
    widget = MyWidget()
    qtbot.addWidget(widget)

    # Block and wait for signal
    with qtbot.waitSignal(widget.clicked, timeout=1000):
        qtbot.mouseClick(widget.button, Qt.MouseButton.LeftButton)


def test_keyboard_input(qtbot):
    widget = SearchWidget()
    qtbot.addWidget(widget)

    qtbot.keyClicks(widget.text_input, "hello world")
    assert widget.text_input.text() == "hello world"
```

### Threading Tests

Threading tests are timing-dependent. Mark for manual execution:

```python
import unittest

class TestTaskWorker(unittest.TestCase):

    @unittest.skip("Threading test - run manually")
    def test_background_task_completion(self):
        import time
        results = []

        def work_func():
            time.sleep(0.1)
            return "done"

        worker = TaskWorker("test", work_func)
        worker.signals.thread_complete.connect(lambda t: results.append(t))
        QThreadPool.globalInstance().start(worker)

        # Wait for completion (fragile - timing dependent)
        time.sleep(0.5)
        self.assertEqual(1, len(results))
        self.assertEqual(TaskStatus.COMPLETED, results[0].status)
```

### Test Isolation with tempfile

```python
import tempfile
from pathlib import Path

class TestWithFileSystem(unittest.TestCase):
    def test_file_operations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test files are automatically cleaned up
            test_file = Path(tmpdir) / "test.json"
            test_file.write_text('{"key": "value"}')

            # Run your test...
            result = load_data(test_file)
            self.assertEqual("value", result["key"])
```

### Best Practices Summary

1. **Test builders separately from models** - Builders are pure Python
2. **Test models separately from views** - Models can be tested without UI
3. **Mock external dependencies** - Wrap CLI tools, databases, network
4. **Use tempfile for isolation** - Clean filesystem for each test
5. **Keep widget tests minimal** - Prefer unit tests over UI tests

---

## 7. Common Patterns Cookbook

### Context Menus with QMenu

```python
from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction

class MyTableView(QTableView):
    def __init__(self, parent):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, position):
        menu = QMenu(self)

        open_action = QAction("Open", self)
        open_action.triggered.connect(self._on_open)
        menu.addAction(open_action)

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self._on_delete)
        menu.addAction(delete_action)

        menu.exec(self.viewport().mapToGlobal(position))
```

### Settings Persistence with QSettings

```python
from PyQt6.QtCore import QSettings

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._settings = QSettings("MyCompany", "MyApp")
        self._restore_settings()

    def _restore_settings(self):
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        state = self._settings.value("windowState")
        if state:
            self.restoreState(state)

    def closeEvent(self, event):
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("windowState", self.saveState())
        super().closeEvent(event)
```

### Drag and Drop

```python
class DragDropTreeView(QTreeView):
    def __init__(self, parent):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        paths = [url.toLocalFile() for url in urls]
        self.files_dropped.emit(paths)
```

### Resource Management

```python
from PyQt6.QtGui import QIcon

# Theme icons (uses system theme)
folder_icon = QIcon.fromTheme("folder")
document_icon = QIcon.fromTheme("document")

# Bundled resources (using Qt Resource System)
# First, compile resources: pyrcc6 resources.qrc -o resources_rc.py
from PyQt6.QtCore import QFile
icon = QIcon(":/icons/myicon.png")

# Icon caching for performance
_ICON_CACHE = {}

def get_icon(name: str) -> QIcon:
    if name not in _ICON_CACHE:
        _ICON_CACHE[name] = QIcon.fromTheme(name)
    return _ICON_CACHE[name]
```

### Keyboard Shortcuts

```python
from PyQt6.QtGui import QShortcut, QKeySequence

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Method 1: QShortcut
        shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut.activated.connect(self._show_find)

        # Method 2: QAction with shortcut
        find_action = QAction("Find", self)
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.triggered.connect(self._show_find)
        self.addAction(find_action)
```

---

## 8. Anti-patterns to Avoid

### Blocking the Event Loop

```python
# WRONG - blocks UI
def load_data(self):
    result = slow_operation()  # UI freezes!
    self.update_view(result)

# CORRECT - use TaskManager
def load_data(self):
    self.task_manager.start_task("load", slow_operation, {})

def _on_load_complete(self, task: Task):
    self.update_view(task.result)
```

### Using QThread for Simple Tasks

```python
# WRONG - overcomplicated for simple background work
class MyThread(QThread):
    def run(self):
        result = do_work()

# CORRECT - QRunnable + QThreadPool
worker = TaskWorker("work", do_work)
QThreadPool.globalInstance().start(worker)
```

### Deep Widget Inheritance

```python
# WRONG - deep inheritance chains
class BaseView(QWidget): pass
class DataView(BaseView): pass
class FilterableDataView(DataView): pass
class SortableFilterableDataView(FilterableDataView): pass

# CORRECT - composition and mixins
class View(QAbstractItemView):  # Protocol
    pass

class TableView(QTableView, View):  # Single inheritance + mixin
    def __init__(self, parent):
        super().__init__(parent)
        self._filter = FilterBehavior(self)  # Composition
        self._sorter = SortBehavior(self)
```

### Testing UI When Unit Tests Suffice

```python
# WRONG - UI test for business logic
def test_data_transformation(qtbot):
    widget = MyWidget()
    qtbot.addWidget(widget)
    widget.load_data(test_data)
    # Assert on rendered UI...

# CORRECT - Unit test the builder
def test_data_transformation():
    builder = MyBuilder()
    result = builder.build(model_data=test_data)
    assert len(result.children) == expected_count
```

### Tight Coupling Between Views and Logic

```python
# WRONG - view knows about database
class MyView(QTableView):
    def refresh(self):
        data = self.database.query("SELECT * FROM items")
        self.model().setData(data)

# CORRECT - view receives data via signals
class MyView(QTableView):
    def set_data(self, items: list):
        model = TableModel(items)
        self.setModel(model)

class MainWindow(QMainWindow):
    def _on_data_loaded(self, data):
        self.view.set_data(data)
```

### Not Using Proxy Models

```python
# WRONG - modifying source model for filtering
class MyModel(QAbstractTableModel):
    def filter(self, text):
        self._data = [d for d in self._original if text in d]
        self.layoutChanged.emit()

# CORRECT - use QSortFilterProxyModel
proxy = QSortFilterProxyModel()
proxy.setSourceModel(source_model)
proxy.setFilterRegularExpression(pattern)
view.setModel(proxy)
```

---

## Reference Implementation

This skill is based on patterns from production PyQt6 applications. Key reference files:

- **Threading pattern**: `app/tasks.py` - TaskWorker, TaskManager
- **Model/View pattern**: `app/presentation/models.py` - ViewItem, builders, Qt models
- **View composition**: `app/presentation/views.py` - mixins, delegates, proxy models
- **Test infrastructure**: `tests/__init__.py` - QApplication singleton
- **Test patterns**: `tests/presentation/test_models.py` - builder and model tests
