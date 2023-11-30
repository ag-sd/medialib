import argparse
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QDir, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QApplication, QLabel, QMessageBox, QFileDialog

import app
from app.actions import AppMenuBar, MediaLibAction
from app.database import exifinfo
from app.database.database import Database
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
        else:
            app.logger.warning("Neither a database or paths were provided. App is in reduced feature mode")
            self.database = Database.create_default(paths=[])

        # Current View
        app.logger.debug("Setup current view widgets ...")
        self.current_view_type = self.database.default_view if app_args.view is None else ViewType[
            app_args.view.upper()]
        self.current_view = QWidget()
        self.current_view_type_label = QLabel(self.current_view_type.name)
        self.current_view_type_label.setContentsMargins(15, 0, 15, 0)
        self.current_view_db_name = QLabel(self.database.name)
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
        self.setWindowIcon(QIcon.fromTheme("medialib-icon"))
        # Load the first entry from the database
        if len(self.database.paths) > 0:
            app.logger.debug("Load first path and present data ...")
            self._path_changed(self.database.paths[0])

        # Present App
        self.show()

    def _action_event(self, event):
        app.logger.debug(f"Action triggered {event}")
        match event:
            case MediaLibAction.OPEN_PATH | MediaLibAction.OPEN_FILE:
                paths = self._get_new_path(is_dir=True if event == MediaLibAction.OPEN_PATH else False)
                if len(paths) > 0:
                    app.logger.debug(f"User supplied {len(paths)} additional paths {paths}")
                    # Add to database
                    self.database.add_paths(paths)
                    # Add to DB Menu
                    self.menubar.add_db_paths(paths)
                    # Show the first path
                    self.statusBar().showMessage(f"Scanning {paths[0]}. Please wait...")
                    self._path_changed(paths[0])
                    self.statusBar().showMessage("Ready.", msecs=2000)
                else:
                    app.logger.debug(f"Cancel action clicked, no paths supplied")
            case MediaLibAction.OPEN_GIT:
                app.logger.debug(f"Opening app url {app.__APP_URL__} in default web browser")
                QDesktopServices.openUrl(QUrl(app.__APP_URL__))
            case MediaLibAction.APP_EXIT:
                app.logger.debug(f"Goodbye!")
                self.close()
            case MediaLibAction.ABOUT:
                html = Path(Path(__file__).parent / "resources" / "about.html").read_text()
                QMessageBox.about(self, app.__APP_NAME__,
                                  html.format(APP_NAME=app.__NAME__, APP_URL=app.__APP_URL__,
                                              VERSION=app.__VERSION__, YEAR=datetime.now().year))

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

    def _get_new_path(self, is_dir=False) -> list:
        """
        Sets up a File-Chooser and allows the user to select a file or directory.
        :param is_dir: whether to allow the user to only choose files or dirs
        :return: If a file was selected, returns it
        """
        files = []
        exiftool_file_filter = f"ExifTool Supported Files (*.{' *.'.join(exifinfo.SUPPORTED_FORMATS.split(' '))})"
        if is_dir:
            path = QFileDialog.getExistingDirectory(self, "Select Directory", str(Path.home()),
                                                    QFileDialog.Option.DontUseCustomDirectoryIcons |
                                                    QFileDialog.Option.ShowDirsOnly)
            if path != "":
                files.append(QDir.toNativeSeparators(path))
        else:
            app.logger.debug(f"Filtering for files that match the following extensions {exiftool_file_filter}")
            resp = QFileDialog.getOpenFileNames(self, "Select Files", str(Path.home()), filter=exiftool_file_filter,
                                                options=QFileDialog.Option.DontUseCustomDirectoryIcons)
            if len(resp[0]) > 0:
                for file in resp[0]:
                    files.append(QDir.toNativeSeparators(file))
        return files


class DatabaseSaveModal(QWidget):
    pass


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

    app.logger.debug(f"############################### TESTING CODE HERE ###############################")

    app.logger.debug(f"############################### TESTING CODE HERE ###############################")

    # Prepare and launch GUI
    application = QApplication(sys.argv)
    _ = MediaLibApp(args)
    sys.exit(application.exec())
