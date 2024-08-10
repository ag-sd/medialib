from abc import abstractmethod

from PyQt6.QtWidgets import QApplication


class WindowInfo:
    @property
    @abstractmethod
    def statustip(self):
        raise NotImplemented

    @property
    def shortcut(self):
        return ""

    @property
    def icon(self):
        return QApplication.windowIcon()
