from abc import abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QMouseEvent, QFontDatabase
from PyQt6.QtWidgets import QApplication, QToolBar, QSizePolicy, QLabel, QDockWidget

from app import apputils
from app.collection import props


@dataclass
class FileData:
    """
    A class that represents a file.
    File Name, Directory and Mime Type are guaranteed to be present
    """
    file_name: str
    directory: str
    file_size: str
    mime_type: str
    root_path: str
    _sourcefile: ... = None

    def __post_init__(self):
        if not isinstance(self.file_name, str):
            raise ValueError("file_name must be set and of type string")
        if not isinstance(self.directory, str):
            raise ValueError("directory must be set and of type string")
        if not isinstance(self.mime_type, str):
            raise ValueError("mime_type must be set and of type string")
        if not isinstance(self.root_path, str):
            raise ValueError("root_path must be set and of type string")
        self._sourcefile = Path(self.directory) / Path(self.file_name)

    @property
    def sourcefile_available(self) -> bool:
        return self._sourcefile.exists()

    @property
    def sourcefile(self) -> Path:
        return self._sourcefile

    @staticmethod
    def from_dict(data: dict, root_path: str = None):
        """
        Attempts to create a FileData class from the data present in the supplied dict
        Args:
            root_path: The path in the collection to which this file belongs
            data: The dict with fields that can constitute a FileData object

        Returns:
            A FileData class representing the file or None if a FileData class cannot be created
        """
        file_name = None
        directory = None
        file_size = "Unavailable"
        if props.FIELD_FILE_NAME in data:
            file_name = data[props.FIELD_FILE_NAME]
        if props.FIELD_FILE_SIZE in data:
            file_size = data[props.FIELD_FILE_SIZE]
        if props.FIELD_DIRECTORY in data:
            directory = data[props.FIELD_DIRECTORY]
        if props.FIELD_SOURCE_FILE in data:
            if file_name is None or directory is None:
                source_path = Path(data[props.FIELD_SOURCE_FILE])
                file_name = source_path.name
                directory = str(source_path.parent)
        if props.FIELD_COLLECTION_PATH in data and root_path is None:
            root_path = data[props.FIELD_COLLECTION_PATH]
        if file_name is not None and directory is not None:
            mime_type = apputils.get_mime_type_icon_name(file_name)
            return FileData(file_name=file_name,
                            directory=directory,
                            file_size=file_size,
                            mime_type=mime_type,
                            root_path=root_path)
        return None


class WindowInfo:

    @property
    def shortcut(self) -> str:
        return ""

    @property
    def icon(self) -> QIcon:
        return QApplication.windowIcon()

    @property
    def is_visible_on_start(self) -> bool:
        return False

    @property
    @abstractmethod
    def dockwidget_area(self):
        raise NotImplemented

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplemented

    @property
    @abstractmethod
    def statustip(self) -> str:
        raise NotImplemented


class PluginToolBar(QToolBar):

    button_clicked = pyqtSignal(str)

    _FLOAT = "Float"
    _CLOSE = "Close"

    def __init__(self, parent: QDockWidget, title: str):
        super().__init__(parent)
        self._parent = parent
        self._float = apputils.create_action(self, self._FLOAT, self._toolbar_event, icon="window")
        self._close = apputils.create_action(self, self._CLOSE, self._toolbar_event, icon="dialog-close")
        self._no_action = apputils.create_action(self, "", enabled=False)
        self.setStyleSheet("QToolBar{padding: 0}")
        self._title = title
        self._init_ui()

    def add_button(self, button_name, icon_name=None, shortcut=None):
        button = apputils.create_action(self, button_name, icon=icon_name, shortcut=shortcut, func=self._toolbar_event)
        self.insertAction(self._no_action, button)

    def _init_ui(self):
        self.setContentsMargins(0, 0, 0, 0)
        self.setIconSize(QSize(14, 14))
        icon = QLabel()
        icon.setPixmap(self._parent.windowIcon().pixmap(22, 22))
        title = QLabel(self._title)
        title.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.TitleFont))
        title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        title.setIndent(5)
        spacer = QLabel(" ")
        self.addWidget(spacer)
        self.addWidget(icon)
        self.addWidget(title)
        self.addAction(self._no_action)
        self.addSeparator()
        self.addAction(self._float)
        self.addAction(self._close)

    def _toolbar_event(self, event_name):
        match event_name:
            case self._FLOAT:
                self._parent.setFloating(not self._parent.isFloating())
            case self._CLOSE:
                self._parent.close()
            case _:
                self.button_clicked.emit(event_name)

    # Mouse events that are not explicitly handled by the title bar widget must be ignored by calling
    # QMouseEvent::ignore(). These events then propagate to the QDockWidget parent, which handles them in the usual
    # manner, moving when the title bar is dragged, docking and undocking when it is double-clicked, etc.
    def mousePressEvent(self, event: QMouseEvent) -> None:
        event.ignore()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        event.ignore()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        event.ignore()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        event.ignore()


class FileClickHandler:

    @abstractmethod
    def handle_file_click(self, file_data: list, fields: list):
        raise NotImplemented


class SearchEventHandler(QObject):
    class SearchType(StrEnum):
        VISUAL = "Visual Search"
        QUERY = "Search Collection Index"

    do_search = pyqtSignal(str, "PyQt_PyObject")
