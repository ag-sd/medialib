import argparse
import os.path
import sys
from functools import partial

from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QComboBox, QWidget, QApplication, QHBoxLayout, QToolBar, QMenu, \
    QToolButton, QLabel

import app
from app import exifinfo
from app.exifinfo import ExifInfo
from app.views.views import ViewType


# Syntax Highligting: https://wiki.python.org/moin/PyQt/Python%20syntax%20highlighting
# https://joekuan.wordpress.com/2015/10/02/styling-qt-qtreeview-with-css/
class ExiftoolGUI(QMainWindow):
    def __init__(self, files: list):
        """
        :param files: The files whose information should be shown
        """
        super().__init__()

        self.current_view_type = ViewType.JSON
        self.current_view_label = QLabel(self.current_view_type.name)
        self.current_view_info_cache = {}
        self.current_view = QWidget()
        self.view_layout = QVBoxLayout()
        self.view_layout.addWidget(self.current_view)

        self.file_selector = self._create_file_selector(files)

        self.toolbar = AppToolbar()
        self.toolbar.view_changed.connect(self._view_changed)
        self.toolbar.action_selected.connect(self._action_event)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.file_selector)

        main_layout = QVBoxLayout()
        main_layout.addLayout(actions_layout)
        main_layout.addLayout(self.view_layout)
        main_layout.setContentsMargins(2, 2, 2, 2)

        dummy_widget = QWidget()
        dummy_widget.setLayout(main_layout)
        self.addToolBar(self.toolbar)
        self.statusBar().addPermanentWidget(self.current_view_label)
        self.setCentralWidget(dummy_widget)
        self.setWindowTitle(app.__APP_NAME__)
        self.setMinimumWidth(768)
        self.setMinimumHeight(768)
        self.show()

    def _init_ui(self):
        pass

    def _action_event(self, event):
        app.logger.debug(f"Action triggered {event}")

    def _view_changed(self, view: ViewType):
        app.logger.debug(f"View changed {view}")
        self.current_view_type = view
        self.current_view_label.setText(view.name)
        # Blow the cache out. It needs to be rebuilt
        self.current_view_info_cache = {}
        self._selection_changed(self.file_selector.currentText())

    def _selection_changed(self, text):
        app.logger.debug(f"Selection changed to {text}")
        view = None
        if self.current_view_type == ViewType.CSV:
            # Evaluate all entries
            infos = []
            for i in range(self.file_selector.count()):
                infos.append(self._get_exif_info(file=text))
                view = self.current_view_type.view(infos)
        else:
            view = self.current_view_type.view(self._get_exif_info(file=text))

        self.view_layout.replaceWidget(self.current_view, view)
        del self.current_view
        self.current_view = view

    def _create_file_selector(self, files: list) -> QComboBox:
        """
        Validates the input files and returns a comobobox to select the files
        :param files: to read the exifdata
        :return: a Combobox of valid files
        """

        combo = QComboBox()
        combo.setEditable(False)
        combo.currentTextChanged.connect(self._selection_changed)
        for file in files:
            if os.path.exists(file):
                combo.addItem(file)
            else:
                app.logger.error(f"{file} does not exist. Skipping this file")

        if combo.count() == 0:
            raise ValueError("No valid files were found!")

        return combo

    def _get_exif_info(self, file: str) -> ExifInfo:
        """
        Checks if the file is in cache, if not extracts the exif info and returns it
        :param file: The file to test
        :return: an ExifInfo object for the file
        """
        if file not in self.current_view_info_cache:
            app.logger.debug(f"Exif data for {file} not in cache. Adding it")
            self.current_view_info_cache[file] = ExifInfo(file, self.current_view_type.format)

        app.logger.debug(f"Returning exif data for {file} from cache")
        return self.current_view_info_cache[file]


class AppToolbar(QToolBar):
    view_changed = pyqtSignal(ViewType)
    action_selected = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setIconSize(QSize(30, 30))
        self.open_file = self._create_action("Open File", shortcut="Ctrl+O", func=self.raise_toolbar_event,
                                             tooltip="Open a file to view its exif data", icon="document-open")
        self.open_folder = self._create_action("Open Directory", shortcut="Ctrl+D", icon="document-open-folder",
                                               tooltip="Open a directory to view exif data of all supported files in it",
                                               func=self.raise_toolbar_event)
        self.add_all_to_db = self._create_action("Add all to DB", shortcut="Ctrl+Shift+S", icon="list-add",
                                                 tooltip="Save the exif data of all open files to the DB",
                                                 func=self.raise_toolbar_event)
        self.add_to_db = self._create_action("Add to DB", shortcut="Ctrl+S", icon="folder-add",
                                             tooltip="Save the exif data of the current files to the DB",
                                             func=self.raise_toolbar_event)

        button = QToolButton()
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setMenu(self._create_view_selection_menu())
        button.setIcon(QIcon.fromTheme("view-choose"))

        self.addAction(self.open_file)
        self.addAction(self.open_folder)
        self.addSeparator()
        self.addAction(self.add_to_db)
        self.addAction(self.add_all_to_db)
        self.addSeparator()
        self.addWidget(button)

    def raise_toolbar_event(self, event):
        self.action_selected.emit(event)

    def raise_menu_event(self, event):
        self.view_changed.emit(ViewType[event])

    def _create_view_selection_menu(self):
        menu = QMenu(self)
        menu.addAction(self._create_action(ViewType.JSON.name, func=self.raise_menu_event, icon="application-json"))
        menu.addAction(self._create_action(ViewType.HTML.name, func=self.raise_menu_event, icon="text-html"))
        menu.addAction(self._create_action(ViewType.PHP.name, func=self.raise_menu_event, icon="application-x-php"))
        menu.addAction(self._create_action(ViewType.XML.name, func=self.raise_menu_event, icon="application-xml"))
        menu.addAction(self._create_action(ViewType.CSV.name, func=self.raise_menu_event, icon="text-csv"))

        return menu

    def _create_action(self, name, func=None, shortcut=None, tooltip=None, icon=None, checked=None):
        action = QAction(name, self)
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tooltip is not None:
            if shortcut is not None:
                tooltip = f"{tooltip} ({shortcut})"
            action.setToolTip(tooltip)
        if func:
            action.triggered.connect(partial(func, name))
        if icon is not None:
            action.setIcon(QIcon.fromTheme(icon))
        if checked is not None:
            action.setCheckable(True)
            action.setChecked(checked)
        return action


if __name__ == '__main__':
    # Test if Exiftool is installed
    exifinfo.test_exiftool()

    # Check for input arguments
    parser = argparse.ArgumentParser(prog=app.__APP_NAME__, description="Frontend to the excellent exiftool")
    parser.add_argument("files", metavar="f", type=str, nargs="*", help="file(s) to read the exif data from")
    args = parser.parse_args()
    app.logger.debug(f"Input args supplied {args.files}")

    # Prepare and launch GUI
    application = QApplication(sys.argv)
    exiftoolgui = ExiftoolGUI(args.files)
    sys.exit(application.exec())
