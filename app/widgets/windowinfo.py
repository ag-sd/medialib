from abc import abstractmethod

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication


class WindowInfo:
    @property
    @abstractmethod
    def statustip(self) -> str:
        raise NotImplemented

    @property
    def shortcut(self) -> str:
        return ""

    @property
    def icon(self) -> QIcon:
        return QApplication.windowIcon()
