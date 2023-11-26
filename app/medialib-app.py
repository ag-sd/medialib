import argparse
import sys

from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QApplication, QLabel

import app
from app.actions import AppMenuBar
from app.mediainfo import exifinfo
from app.mediainfo.exifinfo import ExifInfo
from app.views.views import ViewType


# Syntax Highligting: https://wiki.python.org/moin/PyQt/Python%20syntax%20highlighting
# https://joekuan.wordpress.com/2015/10/02/styling-qt-qtreeview-with-css/
class MediaLibApp(QMainWindow):
    def __init__(self, app_args: argparse.Namespace):
        """
        :param app_args: The arguments to start this app
            paths: The paths whose information should be shown
            database: The database to open
            view: The default view to start this app with

        """
        super().__init__()
        # Current View
        app.logger.debug("Setup current view widgets ...")
        self.current_view_type = ViewType[app_args.view.upper()]
        self.current_view_info_cache = {}
        self.current_view = QWidget()
        self.current_view_type_label = QLabel(self.current_view_type.name)
        self.current_view_path_name = QLabel("ccc")
        self.view_layout = QVBoxLayout()
        self.view_layout.setContentsMargins(2, 2, 2, 2)
        self.view_layout.addWidget(self.current_view)
        self.statusBar().addPermanentWidget(self.current_view_path_name)
        self.statusBar().addPermanentWidget(self.current_view_type_label)

        # Check if a database is supplied
        if app_args.database is not None:
            app.logger.info(f"Loading database {app_args.database}")
            # paths = database.paths
        elif app_args.paths is not None:
            app.logger.info(f"Loading paths {app_args.paths}")
            paths = app_args.paths

        # Menu Bar
        app.logger.debug("Configure Menubar ...")
        self.menubar = AppMenuBar()
        self.menubar.view_changed.connect(self._view_changed)
        self.menubar.medialib_action_selected.connect(self._action_event)
        self.menubar.path_changed.connect(self._path_changed)
        for item in paths:
            self.menubar.add_db_path(item)
        self.setMenuBar(self.menubar)

        # Setup App
        app.logger.debug("Setup app layout ...")
        dummy_widget = QWidget()
        dummy_widget.setLayout(self.view_layout)
        self.setCentralWidget(dummy_widget)
        self.setWindowTitle(app.__APP_NAME__)
        self.setMinimumWidth(768)
        self.setMinimumHeight(768)

        # Load the first entry
        if len(paths) > 0:
            app.logger.debug("Load first path and present data ...")
            self._path_changed(paths[0])

        # Present App
        self.show()

    def _action_event(self, event):
        app.logger.debug(f"Action triggered {event}")

    def _path_changed(self, path):
        def swap_view(new_view):
            self.view_layout.replaceWidget(self.current_view, new_view)
            del self.current_view
            self.current_view = new_view

        app.logger.debug(f"Selection changed to {path}")
        swap_view(self.current_view_type.view(self._get_exif_info(path=path)))
        self.current_view_path_name.setText(path)

    def _view_changed(self, view: ViewType):
        app.logger.debug(f"View changed {view}")
        self.current_view_type = view
        self.current_view_type_label.setText(view.name)
        # Blow the cache out. It needs to be rebuilt
        self.current_view_info_cache = {}
        # If a path is being viewed, reload it
        if self.current_view_path_name.text() != "":
            self._path_changed(self.current_view_path_name.text())

    def _get_exif_info(self, path: str) -> ExifInfo:
        """
        Checks if the file is in cache, if not extracts the exif info and returns it
        :param path: The file to test
        :return: an ExifInfo object for the file
        """
        if path not in self.current_view_info_cache:
            app.logger.debug(f"Exif data for {path} not in cache. Adding it")
            self.current_view_info_cache[path] = ExifInfo(path, self.current_view_type.format)

        app.logger.debug(f"Returning exif data for {path} from cache")
        return self.current_view_info_cache[path]


if __name__ == '__main__':
    # Test if Exiftool is installed
    exifinfo.test_exiftool()

    # Check for input arguments
    parser = argparse.ArgumentParser(prog=app.__APP_NAME__, description="Frontend to the excellent exiftool")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--paths", metavar="p", type=str, nargs="*", help="Path(s) to read the exif data from")
    group.add_argument("--database", metavar="db", type=str, nargs=1, help="The full path of the database to open")

    parser.add_argument("--view", metavar="v", type=str, nargs='?', default='json', help="Select the view to load")

    args = parser.parse_args()
    app.logger.debug(f"Input args supplied     view: {args.view}")
    app.logger.debug(f"Input args supplied    paths: {args.paths}")
    app.logger.debug(f"Input args supplied database: {args.database}")

    # Prepare and launch GUI
    application = QApplication(sys.argv)
    app = MediaLibApp(args)
    sys.exit(application.exec())
