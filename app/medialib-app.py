import argparse
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QApplication, QLabel, QMessageBox, QDialog, QFileDialog

import app
import apputils
from app import appsettings
from app.actions import AppMenuBar, MediaLibAction, DBAction
from app.database import exifinfo
from app.database.ds import Database
from app.views import ViewType, TableView, ModelData
from database.dbwidgets import DatabaseSearch, DatabasePropertyDialog


class MediaLibApp(QMainWindow):
    def __init__(self, app_args: argparse.Namespace):
        """
        :param app_args: The arguments to start this app
            paths: The paths whose information should be shown
            database: The database to open
            view: The view to start this app with
        """
        super().__init__()
        # Current View
        app.logger.debug("Setup current view widgets ...")
        self.current_view_type = ViewType.TABLE if app_args.view is None else ViewType[app_args.view.upper()]
        self.current_view = QWidget()
        self.current_view_type_label = QLabel(self.current_view_type.name)
        self.current_view_db_name = QLabel("")
        self.current_view_details = QLabel("")

        self.db_search = DatabaseSearch()
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.db_search)
        self.db_search.search_event.connect(self._search_text_entered)
        self.db_search.setVisible(False)

        self.view_layout = QVBoxLayout()
        self.view_layout.setContentsMargins(2, 2, 2, 2)
        self.view_layout.addWidget(self.current_view)
        self.statusBar().addPermanentWidget(self.current_view_type_label)
        self.statusBar().addPermanentWidget(self.current_view_details)
        self.statusBar().addPermanentWidget(self.current_view_db_name)

        # Menu Bar
        app.logger.debug("Configure Menubar ...")
        self.menubar = AppMenuBar(plugins=[self.db_search])
        self.menubar.update_recents(appsettings.get_recently_opened_databases())
        self.menubar.update_bookmarks(appsettings.get_bookmarks())
        self.menubar.view_changed.connect(self._view_changed)
        self.menubar.paths_changed.connect(self._paths_changed)
        self.menubar.medialib_action.connect(self._action_event)
        self.menubar.database_action.connect(self._db_action_event)
        self.menubar.open_db_action.connect(self._open_database)
        self.setMenuBar(self.menubar)

        # Setup App
        app.logger.debug("Setup app layout ...")
        dummy_widget = QWidget()
        dummy_widget.setLayout(self.view_layout)
        # Setup initial view
        self._view_changed(self.current_view_type)
        self.setCentralWidget(dummy_widget)
        self.setWindowTitle(app.__APP_NAME__)
        self.setMinimumWidth(768)
        self.setMinimumHeight(768)
        self.setWindowIcon(QIcon.fromTheme("medialib-icon"))
        # Present App
        self.show()

        # Configure database based on input args
        # Check if a database is supplied
        if app_args.database is not None:
            app.logger.info(f"Loading database {app_args.database}")
            self.database = Database.open_db(app_args.database)
        elif app_args.paths is not None:
            app.logger.info(f"Loading paths {app_args.paths}")
            self.database = Database.create_in_memory(paths=app_args.paths)
        else:
            app.logger.warning("Neither a database or paths were provided. App is in reduced feature mode")
            self.database = None

        # Load the first entry from the database
        if self.database is not None:
            self.reload_database()

    def reload_database(self):
        app.logger.debug("Load database and present data ...")
        # Update Menubar
        self.menubar.show_database(self.database)
        # Update display
        self.current_view_db_name.setText(self.database.name)
        self._paths_changed(self.database.paths)

    def _action_event(self, event: MediaLibAction):
        app.logger.debug(f"Action triggered {event}")
        match event:
            case MediaLibAction.OPEN_PATH | MediaLibAction.OPEN_FILE:
                paths = self._get_new_path(is_dir=True if event == MediaLibAction.OPEN_PATH else False)
                if len(paths) > 0:
                    app.logger.debug(f"User supplied {len(paths)} additional paths {paths}")
                    if self.database is None:
                        # Add to new database
                        self.database = Database.create_in_memory(paths)
                        # Load Database
                        self.reload_database()
                    else:
                        # Add to existing database
                        self.database.add_paths(paths)
                        # Add to DB Menu
                        self.menubar.add_db_paths(paths)
                    self._paths_changed(self.database.paths)
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

    def _db_action_event(self, db_action):
        app.logger.debug(f"DB action triggered {db_action}")
        match db_action:
            case DBAction.BOOKMARK:
                bookmarks = appsettings.get_bookmarks()
                current_db_is_bookmarked = self.database.save_path in bookmarks
                if current_db_is_bookmarked:
                    app.logger.info(f"Removing {self.database.save_path} from bookmarks")
                    bookmarks.remove(self.database.save_path)
                else:
                    app.logger.info(f"Adding {self.database.save_path} to bookmarks")
                    bookmarks.append(self.database.save_path)

                appsettings.set_bookmarks(bookmarks)
                self.menubar.update_bookmarks(bookmarks)

            case DBAction.SAVE | DBAction.SAVE_AS:
                # First get save location
                save_location = QFileDialog.getExistingDirectory(self, caption=db_action,
                                                                 directory=str(appsettings.get_config_dir()))
                # Then configure the database
                if save_location != "":
                    app.logger.debug(f"DB will be saved to {save_location}")
                    db_props = DatabasePropertyDialog()
                    db_props.set_database(self.database)
                    response_code = db_props.exec()
                    if response_code == QDialog.DialogCode.Accepted:
                        app.logger.debug("User triggered a save")
                        # Finally, save it
                        self.database.save(save_location)
                        app.logger.info(f"Complete")
                    else:
                        app.logger.debug("User canceled path selection action")
                else:
                    app.logger.debug("User canceled save action")

            case DBAction.OPEN_DB:
                # Choose DB to open
                open_location = QFileDialog.getExistingDirectory(self, caption=db_action,
                                                                 directory=str(appsettings.get_config_dir()))
                # Then open it
                if open_location != "":
                    self._open_database(open_location)

    def _open_database(self, db_path: str):
        try:
            self.database = Database.open_db(db_path)
            self.reload_database()
            recents = appsettings.get_recently_opened_databases()
            appsettings.push_to_list(db_path, recents, appsettings.get_recent_max_size())
            appsettings.set_recently_opened_databases(recents)
            self.menubar.update_recents(recents)

        except Exception as exception:
            apputils.show_exception(self, exception)

    def _paths_changed(self, _paths):
        try:
            app.logger.debug(f"Selection changed to {_paths}")
            model_data = []
            for path in _paths:
                model_data.append(ModelData(
                    json=self.database.data(path=str(path), view=self.current_view_type),
                    path=path))
            self._display_model_data(model_data)
        except Exception as exception:
            apputils.show_exception(self, exception)

    def _view_changed(self, view: ViewType):
        app.logger.debug(f"View changed {view}")
        new_view = view.view()
        self.view_layout.replaceWidget(self.current_view, new_view)
        del self.current_view
        self.current_view = new_view
        self.current_view_type = view
        self.current_view_type_label.setText(view.name)
        # If a path is being viewed, reload it
        if self.current_view_details.property("model_data") is not None:
            self._display_model_data(self.current_view_details.property("model_data"))

    def _display_model_data(self, model_data: list):
        view_details = f"data for {len(model_data)} path{'s' if len(model_data) > 1 else ''} in"
        self.current_view.set_model(model_data, self.database.tags)
        self.current_view_details.setText(view_details)
        self.current_view_details.setProperty("model_data", model_data)
        app.logger.debug(view_details)

    def _get_new_path(self, is_dir=False) -> list:
        exiftool_file_filter = f"ExifTool Supported Files (*.{' *.'.join(exifinfo.SUPPORTED_FORMATS.split(' '))})"
        return apputils.get_new_paths(parent=self, is_dir=is_dir, file_filter=exiftool_file_filter)

    def _search_text_entered(self, search_context):
        if isinstance(self.current_view, TableView):
            self.current_view.search(search_context)


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
