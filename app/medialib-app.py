import argparse
import logging
import sys
import threading
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QUrl, Qt, QCoreApplication
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QApplication, QLabel, QMessageBox, QFileDialog, \
    QProgressBar

import app
import apputils
from app import appsettings
from app.actions import AppMenuBar, MediaLibAction, DBAction
from app.database import exifinfo
from app.database.ds import Database, DatabaseNotFoundException, CorruptedDatabaseException
from app.views import ViewType, TableView, ModelData
from database.dbwidgets import DatabaseSearch


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
        self.current_view_type_label.setStyleSheet(
            f"margin-left :{self.current_view_type_label.fontMetrics().horizontalAdvance("  ")}px")
        self.current_view_details = QLabel("")
        self.current_view_details.setStyleSheet(
            f"margin-left :{self.current_view_details.fontMetrics().horizontalAdvance("  ")}px")

        self.db_search = DatabaseSearch()
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.db_search)
        self.db_search.search_event.connect(self._search_text_entered)
        self.db_search.setVisible(False)

        self.view_layout = QVBoxLayout()
        self.view_layout.setContentsMargins(2, 2, 2, 2)
        self.view_layout.addWidget(self.current_view)
        self.statusBar().addPermanentWidget(self.current_view_type_label)
        self.statusBar().addPermanentWidget(self.current_view_details)

        # Menu Bar
        app.logger.debug("Configure Menubar ...")
        self.menubar = AppMenuBar(plugins=[])
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

    def closeEvent(self, event):
        if self.database and self.database.is_modified:
            save_confirm = QMessageBox.question(self, f"Quit {app.__NAME__}",
                                                f"<p><b>The Database has changed</b></p>"
                                                f"Save changes to Database {self.database.name} before closing?")
            if save_confirm == QMessageBox.StandardButton.Yes:
                if self.database.save_path is not None:
                    self.database.save()
                else:
                    self._db_action_event(DBAction.SAVE_AS)
        super().closeEvent(event)

    def reload_database(self):
        app.logger.debug("Load database and present data ...")
        # Update Menubar
        self.menubar.show_database(self.database)
        # Update display
        self.setWindowTitle(f"{self.database.name} : {app.__APP_NAME__}")
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
            case MediaLibAction.LOG_EXCEPTION:
                app.logger.setLevel(logging.ERROR)
            case MediaLibAction.LOG_DEBUG:
                app.logger.setLevel(logging.DEBUG)
            case MediaLibAction.LOG_INFO:
                app.logger.setLevel(logging.INFO)
            case MediaLibAction.LOG_WARNING:
                app.logger.setLevel(logging.WARNING)

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

            case DBAction.SAVE:
                if self.database.save_path is None:
                    app.logger.warning("Unable to save this database as save path is not provided. Requesting one now")
                    self._db_action_event(DBAction.SAVE_AS)
                else:
                    self._do_work_in_thread(self.database.save, title="Saving database please wait...")

            case DBAction.SAVE_AS:
                # First get save location
                save_location = QFileDialog.getExistingDirectory(self, caption=db_action,
                                                                 directory=str(appsettings.get_config_dir()))
                # Then configure the database
                if save_location != "":
                    app.logger.debug(f"DB will be saved to {save_location}")
                    self._do_work_in_thread(self.database.save, kwargs={"save_path": save_location},
                                            title="Saving database please wait...")
                else:
                    app.logger.debug("User canceled save action")

            case DBAction.OPEN_DB:
                # Choose DB to open
                open_location = QFileDialog.getExistingDirectory(self, caption=db_action,
                                                                 directory=str(appsettings.get_config_dir()))
                # Then open it
                if open_location != "":
                    self._open_database(open_location)

            case DBAction.RESET:
                self.reload_database()

            case DBAction.REFRESH:
                self._do_work_in_thread(self._refresh_paths, kwargs={"paths": self.database.paths},
                                        title=f"Refreshing database...", success_msg="Database refreshed successfully")
                self.reload_database()

            case DBAction.REFRESH_SELECTED:
                selected_paths = self.menubar.get_selected_db_paths()
                if len(selected_paths) > 0:
                    self._do_work_in_thread(self._refresh_paths, kwargs={"paths": selected_paths},
                                            title=f"Refreshing {len(selected_paths)} path(s)...",
                                            success_msg="Selected paths were refreshed successfully")
                    self._paths_changed(selected_paths)

            case _:
                app.logger.warning(f"Not Implemented: {db_action}")

    def _refresh_paths(self, paths):
        self.database.clear_cache()
        for path in paths:
            self.database.data(path, refresh=True)

    def _open_database(self, db_path: str):
        try:
            self.database = Database.open_db(db_path)
            self.reload_database()
            recents = appsettings.get_recently_opened_databases()
            appsettings.push_to_list(db_path, recents, appsettings.get_recent_max_size())
            appsettings.set_recently_opened_databases(recents)
            self.menubar.update_recents(recents)

        except (DatabaseNotFoundException, CorruptedDatabaseException) as e:
            apputils.show_exception(self, e)

    def _paths_changed(self, _paths):
        try:
            app.logger.debug(f"Selection changed to {_paths}")
            model_data = []
            for path in _paths:
                self._do_work_in_thread(self.database.data, {"path": str(path)},
                                        title=f"Loading {len(_paths)} paths",
                                        success_msg=f"{len(_paths)} paths were loaded successfully")
                # Data is added to cache, so pick it up from cache
                data = ModelData(json=self.database.data(path=str(path)), path=path)
                model_data.append(data)
            self._display_model_data(model_data, _paths)
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
            self._display_model_data(self.current_view_details.property("model_data"),
                                     self.current_view_details.property("paths"))

    def _display_model_data(self, model_data: list, paths: list):
        view_details = f"{len(paths)} path{'s' if len(paths) > 1 else ''} displayed"
        self.current_view.set_model(model_data)
        self.current_view_details.setText(view_details)
        self.current_view_details.setProperty("model_data", model_data)
        self.current_view_details.setProperty("paths", paths)
        self.current_view_details.setToolTip("\n".join(paths))
        app.logger.debug(view_details)

    def _get_new_path(self, is_dir=False) -> list:
        exiftool_file_filter = f"ExifTool Supported Files (*.{' *.'.join(exifinfo.SUPPORTED_FORMATS.split(' '))})"
        return apputils.get_new_paths(parent=self, is_dir=is_dir, file_filter=exiftool_file_filter)

    def _do_work_in_thread(self, work_func, kwargs=None, title="Working please wait...", pr_min=0, pr_max=0,
                           success_msg="Ready..."):
        progress = QProgressBar()
        progress.setMaximum(pr_max)
        progress.setMinimum(pr_min)
        window_title = self.windowTitle()
        self.setWindowTitle(title)
        self.menubar.setEnabled(False)
        self.statusBar().addWidget(progress)
        self.statusBar().show()
        work_thread = threading.Thread(target=work_func, kwargs=kwargs, daemon=True)
        work_thread.start()
        app.logger.info(f"THREAD:{work_thread.ident} : Started work on "
                        f"function `{work_func.__name__}` with args {kwargs} ...")
        app.logger.info(title)
        while work_thread.is_alive():
            QCoreApplication.processEvents()
        self.statusBar().removeWidget(progress)
        self.setWindowTitle(window_title)
        self.menubar.setEnabled(True)
        self.statusBar().showMessage(success_msg, 5000)
        app.logger.info(f"THREAD:{work_thread.ident} : Work completed : {success_msg}")

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
    group.add_argument("--database", metavar="db", type=str, help="The full path of the database to open")

    parser.add_argument("--view", metavar="v", type=str, default='json', help="Select the view to load")

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
