import argparse
import sys

from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QApplication, QLabel, QMessageBox

import app
from app.actions import AppMenuBar
from app.database import exifinfo
from app.database.Database import Database
from app.views import ViewType


def show_exception(parent, exception: Exception):
    app.logger.exception(exception)
    QMessageBox.critical(parent, "An Error Occurred", str(exception))


class MediaLibApp(QMainWindow):
    def __init__(self, app_args: argparse.Namespace):
        """
        :param app_args: The arguments to start this app
            paths: The paths whose information should be shown
            database: The database to open
            view: The view to start this app with
        """
        super().__init__()
        # Configure database based on input args
        # Check if a database is supplied
        if app_args.database is not None:
            app.logger.info(f"Loading database {app_args.database}")
            # paths = database.paths
            self.database = None
        elif app_args.paths is not None:
            app.logger.info(f"Loading paths {app_args.paths}")
            self.database = Database.create_default(paths=app_args.paths)

        # Current View
        app.logger.debug("Setup current view widgets ...")
        self.current_view_type = self.database.default_view if app_args.view is None else ViewType[app_args.view.upper()]
        self.current_view = QWidget()
        self.current_view_type_label = QLabel(self.current_view_type.name)
        self.current_view_type_label.setContentsMargins(15, 0, 15, 0)
        self.current_view_db_name = QLabel(self.database.database_name)
        self.current_view_path_name = QLabel("")

        self.view_layout = QVBoxLayout()
        self.view_layout.setContentsMargins(2, 2, 2, 2)
        self.view_layout.addWidget(self.current_view)
        self.statusBar().addPermanentWidget(self.current_view_path_name)
        self.statusBar().addPermanentWidget(self.current_view_type_label)
        self.statusBar().addPermanentWidget(self.current_view_db_name)

        # Menu Bar
        app.logger.debug("Configure Menubar ...")
        self.menubar = AppMenuBar(self.database)
        self.menubar.view_changed.connect(self._view_changed)
        self.menubar.medialib_action_selected.connect(self._action_event)
        self.menubar.path_changed.connect(self._path_changed)
        self.setMenuBar(self.menubar)

        # Setup App
        app.logger.debug("Setup app layout ...")
        dummy_widget = QWidget()
        dummy_widget.setLayout(self.view_layout)
        self.setCentralWidget(dummy_widget)
        self.setWindowTitle(app.__APP_NAME__)
        self.setMinimumWidth(768)
        self.setMinimumHeight(768)

        # Load the first entry from the database
        if len(self.database.paths) > 0:
            app.logger.debug("Load first path and present data ...")
            self._path_changed(self.database.paths[0])

        # Present App
        self.show()

    def _action_event(self, event):
        app.logger.debug(f"Action triggered {event}")

    def _path_changed(self, path):
        def swap_view(new_view):
            self.view_layout.replaceWidget(self.current_view, new_view)
            del self.current_view
            self.current_view = new_view

        try:
            app.logger.debug(f"Selection changed to {path}")
            swap_view(self.current_view_type.view(self.database.get_path_data(path=path, view=self.current_view_type)))
            self.current_view_path_name.setText(path)
        except Exception as exception:
            show_exception(self, exception)

    def _view_changed(self, view: ViewType):
        app.logger.debug(f"View changed {view}")
        self.current_view_type = view
        self.current_view_type_label.setText(view.name)
        # If a path is being viewed, reload it
        if self.current_view_path_name.text() != "":
            self._path_changed(self.current_view_path_name.text())


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
    _ = MediaLibApp(args)
    sys.exit(application.exec())
