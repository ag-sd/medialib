import argparse
import sys
import threading
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QUrl, QCoreApplication, Qt
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QApplication, QLabel, QMessageBox, QFileDialog, \
    QProgressBar, QDockWidget

import app
import apputils
from app import appsettings
from app.actions import AppMenuBar, MediaLibAction, DBAction, ViewAction
from app.collection import exifinfo
from app.collection.ds import Collection, CollectionNotFoundError, CorruptedCollectionError, HasCollectionDisplaySupport, \
    CollectionQueryError
from app.views import ViewType, ModelData, ModelManager
from app.widgets import search


class MediaLibApp(QMainWindow, HasCollectionDisplaySupport):

    def __init__(self, app_args: argparse.Namespace):
        """
        :param app_args: The arguments to start this app
            paths: The paths whose information should be shown
            collection: The collection to open
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

        self.view_layout = QVBoxLayout()
        self.view_layout.setContentsMargins(2, 2, 2, 2)
        self.view_layout.addWidget(self.current_view)
        self.statusBar().addPermanentWidget(self.current_view_type_label)
        self.statusBar().addPermanentWidget(self.current_view_details)

        self._plugins = self._init_plugins()

        # Search
        self._sql_search_widget = None

        # Menu Bar
        app.logger.debug("Configure Menubar ...")
        self.menubar = AppMenuBar(plugins=self._plugins)
        self.menubar.view_event.connect(self._view_event)
        self.menubar.db_event.connect(self._db_event)
        self.menubar.medialib_event.connect(self._medialib_event)
        self.menubar.update_recents(appsettings.get_recently_opened_collections())
        self.menubar.update_bookmarks(appsettings.get_bookmarks())

        self.setMenuBar(self.menubar)

        # Setup App
        app.logger.debug("Setup app layout ...")
        dummy_widget = QWidget()
        dummy_widget.setLayout(self.view_layout)
        # Setup initial view
        self._view_event(ViewAction.VIEW, self.current_view_type)
        self.setCentralWidget(dummy_widget)
        self.setWindowTitle(app.__APP_NAME__)
        self.setMinimumWidth(768)
        self.setMinimumHeight(768)
        self.setWindowIcon(QIcon.fromTheme("medialib-icon"))
        # Present App
        self.show()

        # Configure collection based on input args
        # Check if a collection is supplied
        if app_args.collection is not None:
            app.logger.info(f"Loading collection {app_args.collection}")
            self.collection = Collection.open_db(app_args.collection)
        elif app_args.paths is not None:
            app.logger.info(f"Loading paths {app_args.paths}")
            self.collection = Collection.create_in_memory(paths=app_args.paths)
        else:
            app.logger.warning("Neither a collection or paths were provided. App is in reduced feature mode")
            self.collection = None

        # Load the first entry from the collection
        if self.collection is not None:
            self.show_collection(self.collection)
        app.logger.debug("Startup tasks completed. Ready.")

    def closeEvent(self, event):
        if self.collection:
            self.shut_collection()
        app.logger.debug(f"{app.__APP_NAME__} is exiting. Goodbye!")
        super().closeEvent(event)

    def show_collection(self, collection: Collection):
        app.logger.debug("Load collection and present data ...")
        # Update Menubar
        self.menubar.show_collection(self.collection)
        # Update Search
        if self._sql_search_widget and self._sql_search_widget.isVisible():
            self._sql_search_widget.show_collection(collection)
        # Update Plugins
        for plugin in self._plugins:
            if isinstance(plugin, HasCollectionDisplaySupport):
                plugin.show_collection(self.collection)
        # Update display
        self.setWindowTitle(f"{self.collection.name} : {app.__APP_NAME__}")
        self._paths_changed(self.collection.paths)

    def shut_collection(self):
        if self.collection:
            app.logger.debug("Closing Collection ...")
            # Check if the db needs to be saved
            if self.collection.is_modified:
                save_confirm = QMessageBox.question(self, f"CLose {self.collection.name}",
                                                    f"<p><b>The Collection has changed</b></p>"
                                                    f"Save changes to Collection {self.collection.name} before closing?"
                                                    )
                if save_confirm == QMessageBox.StandardButton.Yes:
                    self._db_event(DBAction.SAVE, None)
            # Update Menubar
            self.menubar.shut_collection()
            # Update Search
            if self._sql_search_widget and self._sql_search_widget.isVisible():
                self._sql_search_widget.shut_collection()
            # Update Plugins
            for plugin in self._plugins:
                if isinstance(plugin, HasCollectionDisplaySupport):
                    plugin.shut_collection()
            # Update display
            self.setWindowTitle(f"{app.__APP_NAME__}")
            self.collection = None

    def _db_event(self, db_action, event_args):
        app.logger.debug(f"DB action triggered {db_action} with args {event_args}")
        match db_action:
            case DBAction.BOOKMARK:
                bookmarks = appsettings.get_bookmarks()
                current_db_is_bookmarked = self.collection.save_path in bookmarks
                if current_db_is_bookmarked:
                    app.logger.info(f"Removing {self.collection.save_path} from bookmarks")
                    bookmarks.remove(self.collection.save_path)
                else:
                    app.logger.info(f"Adding {self.collection.save_path} to bookmarks")
                    bookmarks.append(self.collection.save_path)

                appsettings.set_bookmarks(bookmarks)
                self.menubar.update_bookmarks(bookmarks)

            case DBAction.SAVE:
                if self.collection.save_path is None:
                    app.logger.warning("Unable to save this collection as save path isn't provided. Requesting one now")
                    self._db_event(DBAction.SAVE_AS, event_args)
                else:
                    self._do_work_in_thread(self.collection.save, title="Saving collection please wait...")

            case DBAction.SAVE_AS:
                # First get save location
                save_location = QFileDialog.getExistingDirectory(self, caption=db_action,
                                                                 directory=str(appsettings.get_config_dir()))
                # Then configure the collection
                if save_location != "":
                    app.logger.debug(f"DB will be saved to {save_location}")
                    self._do_work_in_thread(self.collection.save, kwargs={"save_path": save_location},
                                            title="Saving collection please wait...")
                else:
                    app.logger.debug("User canceled save action")

            case DBAction.OPEN_DB:
                if event_args is None:
                    # Prompt user for a db to open
                    # Choose DB to open
                    open_location = QFileDialog.getExistingDirectory(self, caption=db_action,
                                                                     directory=str(appsettings.get_config_dir()))
                else:
                    open_location = event_args
                # Then open the supplied location if its valid
                if open_location != "":
                    self._open_collection(open_location)

            case DBAction.SHUT_DB:
                self.shut_collection()

            case DBAction.RESET:
                self.show_collection(self.collection)

            case DBAction.REFRESH:
                self._do_work_in_thread(self._refresh_paths, kwargs={"paths": self.collection.paths},
                                        title=f"Refreshing collection...",
                                        success_msg="Collection refreshed successfully")
                self.show_collection(self.collection)

            case DBAction.REFRESH_SELECTED:
                selected_paths = event_args
                if len(selected_paths) > 0:
                    self._do_work_in_thread(self._refresh_paths, kwargs={"paths": selected_paths},
                                            title=f"Refreshing {len(selected_paths)} path(s)...",
                                            success_msg="Selected paths were refreshed successfully")
                    self._paths_changed(selected_paths)
            case DBAction.PATH_CHANGE:
                self._paths_changed(_paths=event_args)

            case DBAction.OPEN_SEARCH:
                self._sql_search_widget = search.QueryWidget(self)
                self._sql_search_widget.show_collection(self.collection)
                self._sql_search_widget.query_event.connect(self._sql_search_widget__query_event)
                self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._sql_search_widget)
                self._sql_search_widget.setVisible(True)
                self._sql_search_widget.setFocus()

            case DBAction.SHUT_SEARCH:
                if self._sql_search_widget is not None:
                    self._sql_search_widget.shut_collection()
                    self._sql_search_widget.query_event.disconnect()
                    self.removeDockWidget(self._sql_search_widget)
                    self._sql_search_widget = None
                    self._paths_changed(_paths=self.menubar.get_selected_collection_paths())

            case _:
                app.logger.warning(f"Not Implemented: {db_action}")

    def _medialib_event(self, medialib_action):
        app.logger.debug(f"Medialib event triggered {medialib_action}")
        match medialib_action:
            case MediaLibAction.OPEN_PATH | MediaLibAction.OPEN_FILE:
                paths = self._get_new_path(is_dir=True if medialib_action == MediaLibAction.OPEN_PATH else False)
                if len(paths) > 0:
                    app.logger.debug(f"User supplied {len(paths)} additional paths {paths}")
                    if self.collection is None:
                        # Add to new collection
                        self.collection = Collection.create_in_memory(paths)
                    else:
                        # Add to existing collection
                        self.collection.add_paths(paths)
                    # Load Collection
                    self.show_collection(self.collection)
                    self._paths_changed(self.collection.paths)
                    self.statusBar().showMessage("Ready.", msecs=2000)
                else:
                    app.logger.debug(f"Cancel action clicked, no paths supplied")
            case MediaLibAction.APP_EXIT:
                app.logger.debug(f"Goodbye!")
                self.close()
            case MediaLibAction.OPEN_GIT:
                app.logger.debug(f"Opening app url {app.__APP_URL__} in default web browser")
                QDesktopServices.openUrl(QUrl(app.__APP_URL__))

            case MediaLibAction.ABOUT:
                html = Path(Path(__file__).parent / "resources" / "about.html").read_text()
                QMessageBox.about(self, app.__APP_NAME__, html.format(APP_NAME=app.__NAME__, APP_URL=app.__APP_URL__,
                                                                      VERSION=app.__VERSION__, YEAR=datetime.now().year)
                                  )

    def _init_plugins(self):
        plugins = []

        def _init_plugin(plugin_widget: QDockWidget, area):
            plugin_widget.setVisible(False)
            self.addDockWidget(area, plugin_widget)
            plugins.append(plugin_widget)

        simple_find = search.FindWidget(self)
        simple_find.find_event.connect(self._plugin_simple_find__find_event)
        _init_plugin(simple_find, Qt.DockWidgetArea.TopDockWidgetArea)

        return plugins

    def _plugin_simple_find__find_event(self, text):
        if isinstance(self.current_view, ModelManager):
            app.logger.debug(f"Finding text {text}")
            self.current_view.find_text(text)

    def _sql_search_widget__query_event(self, query):
        app.logger.debug("Searching collection with paths provided")
        try:
            search_paths = self.menubar.get_selected_collection_paths()
            results = self.collection.query(query, search_paths)
            model_data = []
            for search_result in results.data:
                if len(search_result.results) > 0:
                    model_data.append(ModelData(data=search_result.results, path=search_result.path))
            self._display_model_data(model_data, results.searched_paths, results.columns)
        except CollectionQueryError as d:
            apputils.show_exception(self, d)

    def _refresh_paths(self, paths):
        self.collection.clear_cache()
        for path in paths:
            self.collection.data(path, refresh=True)

    def _open_collection(self, db_path: str):
        try:
            self.collection = Collection.open_db(db_path)
            self.show_collection(self.collection)
            recents = appsettings.get_recently_opened_collections()
            appsettings.push_to_list(db_path, recents, appsettings.get_recent_max_size())
            appsettings.set_recently_opened_collections(recents)
            self.menubar.update_recents(recents)

        except (CollectionNotFoundError, CorruptedCollectionError) as e:
            apputils.show_exception(self, e)

    def _paths_changed(self, _paths):
        app.logger.debug(f"Selection changed to {_paths}")
        model_data = []
        try:
            for path in _paths:
                self._do_work_in_thread(self.collection.data, {"path": str(path)},
                                        title=f"Loading {len(_paths)} paths",
                                        success_msg=f"{len(_paths)} paths were loaded successfully")
                # Data is added to cache, so pick it up from cache
                data = ModelData(data=self.collection.data(path=str(path)), path=path)
                model_data.append(data)
            self._display_model_data(model_data, _paths, self.collection.tags)
        except CollectionQueryError as d:
            apputils.show_exception(self, d)
        except Exception as exception:
            apputils.show_exception(self, exception)

    def _view_event(self, action, event_args):
        match action:
            case ViewAction.VIEW:
                view = event_args
                app.logger.debug(f"View changed {view}")
                new_view = view.view(self)
                self.view_layout.replaceWidget(self.current_view, new_view)
                del self.current_view
                self.current_view = new_view
                self.current_view_type = view
                self.current_view_type_label.setText(view.name)
                # If a path is being viewed, reload it
                if self.current_view_details.property("model_data") is not None:
                    self._display_model_data(self.current_view_details.property("model_data"),
                                             self.current_view_details.property("paths"),
                                             self.current_view_details.property("fields"))

            case ViewAction.FIELD:
                fields = event_args
                app.logger.debug(f"Show fields changed")
                if self.current_view_details.property("model_data") is not None:
                    self._display_model_data(self.current_view_details.property("model_data"),
                                             self.current_view_details.property("paths"),
                                             fields)

    def _display_model_data(self, model_data: list, paths: list, fields: set):
        self.current_view.set_model(model_data, fields)
        # Adjust view details
        if len(model_data) > 0:
            view_details = f"{len(paths)} path{'s' if len(paths) > 1 else ''} displayed"
            self.current_view_details.setText(view_details)
            self.current_view_details.setProperty("model_data", model_data)
            self.current_view_details.setProperty("paths", paths)
            self.current_view_details.setProperty("fields", fields)
            self.current_view_details.setToolTip("\n".join(paths))
            app.logger.debug(view_details)
        else:
            # This means the model data was unloaded
            self.current_view_details.setText("")
            self.current_view_details.setProperty("model_data", None)
            self.current_view_details.setProperty("paths", None)
            self.current_view_details.setProperty("fields", None)
            self.current_view_details.setToolTip("")

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


if __name__ == '__main__':
    # Test if Exiftool is installed
    exifinfo.test_exiftool()

    # Check for input arguments
    parser = argparse.ArgumentParser(prog=app.__APP_NAME__, description="Frontend to the excellent exiftool")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--paths", metavar="p", type=str, nargs="*", help="Path(s) to read the exif data from")
    group.add_argument("--collection", metavar="db", type=str, help="The full path of the collection to open")

    parser.add_argument("--view", metavar="v", type=str, default='table', help="Select the view to load")

    args = parser.parse_args()
    app.logger.debug(f"Input args supplied       view: {args.view}")
    app.logger.debug(f"Input args supplied      paths: {args.paths}")
    app.logger.debug(f"Input args supplied collection: {args.collection}")

    app.logger.debug(f"############################### TESTING CODE HERE ###############################")

    app.logger.debug(f"############################### TESTING CODE HERE ###############################")

    # Prepare and launch GUI
    application = QApplication(sys.argv)
    app.logger.debug(f"{app.__APP_NAME__} is starting up")
    _ = MediaLibApp(args)
    sys.exit(application.exec())
