from abc import abstractmethod

from PyQt6.QtWidgets import QApplication

from app.database.ds import Database


class WindowInfo:
    @property
    @abstractmethod
    def statustip(self):
        raise NotImplemented

    @abstractmethod
    def show_database(self, database: Database):
        raise NotImplemented

    @abstractmethod
    def shut_database(self):
        raise NotImplemented

    @property
    def shortcut(self):
        return ""

    @property
    def icon(self):
        return QApplication.windowIcon()