import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QApplication, QMessageBox, QFileDialog

import app
import apputils
from app import appsettings
from app.actions import AppMenuBar, MediaLibAction, DBAction
from app.collection import exifinfo
from app.collection.ds import Collection, CollectionNotFoundError, CorruptedCollectionError, \
    HasCollectionDisplaySupport, \
    CollectionQueryError
from app.plugins import search, info
from app.plugins.framework import SearchEventHandler, FileClickHandler, FileData
from app.presentation.viewmanager import ViewManager
from app.tasks import TaskManager, Task, TaskStatus
from app.presentation.models import ModelData


class MediaLibApp(QMainWindow, HasCollectionDisplaySupport):
    _MLIB_TASK_PATH_CHANGE = "paths-changed"
    _MLIB_TASK_QUERY_SEARCH = "query-search"
    _MLIB_TASK_REFRESH_PATHS = "refresh-paths"
    _MLIB_TASK_SAVE = "save-collection"
    _MLIB_TASK_REINDEX = "reindex-collection"

    _MLIB_UI_STATUS_MESSAGE_TIMEOUT = 5000

    def __init__(self, app_args: argparse.Namespace):
        """
        :param app_args: The arguments to start this app
            paths: The paths whose information should be shown
            collection: The collection to open
        """
        super().__init__()
        # Current View
        app.logger.debug("Setup current view widgets ...")
        self._view_manager = ViewManager(self)
        self._view_manager.item_click.connect(self._file_click)

        self.view_layout = QVBoxLayout()
        self.view_layout.setContentsMargins(0, 0, 0, 0)
        self.view_layout.addWidget(self._view_manager)
        self.statusBar().addPermanentWidget(self._view_manager.view_details_label)

        self._plugins = []
        self._task_manager = TaskManager(self)
        self._task_manager.work_complete.connect(self._background_task_complete_event)
        self.statusBar().addPermanentWidget(self._task_manager)

        # Menu Bar
        app.logger.debug("Configure Menubar ...")
        self.menubar = AppMenuBar()
        # self.menubar.view_event.connect(self._view_event)
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
        self.setCentralWidget(dummy_widget)
        self.setWindowTitle(app.__APP_NAME__)
        self.setMinimumWidth(1200)
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
        while self._task_manager.active_tasks > 0:
            app.logger.info(f"Waiting for {self._task_manager.active_tasks} jobs to finish...")
            time.sleep(1)
        app.logger.debug(f"{app.__APP_NAME__} is exiting. Goodbye!")
        super().closeEvent(event)

    def show_collection(self, collection: Collection):
        app.logger.debug("Load collection and present data ...")
        # Update Menubar
        self.menubar.show_collection(self.collection)
        # Update View
        self._view_manager.show_collection(self.collection)
        # Update Plugins
        for plugin in self._plugins:
            if isinstance(plugin, HasCollectionDisplaySupport):
                plugin.show_collection(self.collection)

        # Update display
        self.setWindowTitle(f"{self.collection.name} : {app.__APP_NAME__}"
                            f"{' !!! PRIVATE !!!' if collection.is_private else ''}")
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
            # Update View
            self._view_manager.shut_collection()
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

            case DBAction.SAVE | DBAction.SAVE_AS:
                save_location = self.collection.save_path
                if save_location is None or db_action == DBAction.SAVE_AS:
                    save_location = QFileDialog.getExistingDirectory(self, caption=db_action,
                                                                     directory=str(appsettings.get_config_dir()))
                if save_location == "":
                    app.logger.debug("User canceled save action")
                    return

                if self._path_validated(save_location):
                    app.logger.debug(f"DB will be saved to {save_location}")
                    self._task_manager.start_task(self._MLIB_TASK_SAVE, self.collection.save,
                                                  {"save_path": save_location})

            case DBAction.OPEN_DB | DBAction.OPEN_PRIVATE_DB:
                self._open_collection(event_args, db_action, is_private=db_action == DBAction.OPEN_PRIVATE_DB)

            case DBAction.SHUT_DB:
                self.shut_collection()

            case DBAction.RESET:
                self.show_collection(self.collection)

            case DBAction.REFRESH:
                self._refresh_paths(self.collection.paths)

            case DBAction.REFRESH_SELECTED:
                if len(event_args) > 0:
                    self._refresh_paths(event_args)

            case DBAction.REINDEX_COLLECTION:
                self._task_manager.start_task(self._MLIB_TASK_REINDEX, self.collection.reindex, {})

            case DBAction.PATH_CHANGE:
                self._paths_changed(_paths=event_args)

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
                                                                      VERSION=app.__VERSION__, YEAR=datetime.now().year,
                                                                      PLUGINS=[p.name for p in self._plugins])
                                  )

    def _background_task_complete_event(self, task: Task):
        # Catch exceptions right up here
        if task.status == TaskStatus.FAILED:
            apputils.show_exception(self, task.error)
            return

        match task.id:
            case self._MLIB_TASK_PATH_CHANGE:
                try:
                    model_data = []
                    for path, result in task.result.items():
                        data = ModelData(data=result, path=path)
                        model_data.append(data)
                    self._display_model_data(model_data, self.collection.tags)
                    self.statusBar().showMessage(f"Data for {task.result.keys()} paths fetched "
                                                 f"in {task.time_taken} seconds.", self._MLIB_UI_STATUS_MESSAGE_TIMEOUT)
                except CollectionQueryError as d:
                    apputils.show_exception(self, d)
                except Exception as exception:
                    apputils.show_exception(self, exception)

            case self._MLIB_TASK_QUERY_SEARCH:
                try:
                    model_data = []
                    for search_result in task.result.data:
                        if len(search_result.results) > 0:
                            model_data.append(ModelData(data=search_result.results, path=search_result.path))
                    self._display_model_data(model_data, task.result.columns)
                    self.statusBar().showMessage(f"Search completed in {task.time_taken} seconds.",
                                                 self._MLIB_UI_STATUS_MESSAGE_TIMEOUT)
                except CollectionQueryError as d:
                    apputils.show_exception(self, d)

            case self._MLIB_TASK_REFRESH_PATHS:
                paths = task.args["paths"]
                self.statusBar().showMessage(f"Path refresh completed for {paths} in {task.time_taken} seconds.",
                                             self._MLIB_UI_STATUS_MESSAGE_TIMEOUT)
                app.logger.info(f"Path refresh completed for {paths} in {task.time_taken} seconds")

            case self._MLIB_TASK_SAVE:
                self.statusBar().showMessage(f"Save collection completed in {task.time_taken} seconds.",
                                             self._MLIB_UI_STATUS_MESSAGE_TIMEOUT)

            case self._MLIB_TASK_REINDEX:
                self.statusBar().showMessage(f"Reindex collection completed in {task.time_taken} seconds.",
                                             self._MLIB_UI_STATUS_MESSAGE_TIMEOUT)

    def register_plugin(self, plugin):
        plugin.setVisible(plugin.is_visible_on_start)
        self.addDockWidget(plugin.dockwidget_area, plugin)

        if isinstance(plugin, SearchEventHandler):
            plugin.do_search.connect(self._plugin__do_search)

        self.menubar.register_plugin(plugin)
        self._plugins.append(plugin)
        app.logger.info(f"Registering plugin {plugin.name} is complete")

    def _plugin__do_search(self, search_scope, search_type):
        match search_type:
            case SearchEventHandler.SearchType.QUERY:
                app.logger.debug("Searching collection with paths provided")
                self._task_manager.start_task(self._MLIB_TASK_QUERY_SEARCH, self.collection.query, {
                    "query": search_scope, "query_paths": self.menubar.get_selected_collection_paths()
                })
            case SearchEventHandler.SearchType.VISUAL:
                app.logger.debug(f"Finding text in visual interface {search_scope}")
                self._view_manager.find_text(search_scope)

    def _refresh_paths(self, paths):
        app.logger.debug(f"Refreshing {len(paths)} path(s)")
        self.collection.clear_cache()
        self._task_manager.start_task(self._MLIB_TASK_REFRESH_PATHS, self.collection.data,
                                      {"paths": paths, "refresh": True})

    def _open_collection(self, db_path: str, db_action: DBAction, is_private: bool = False):
        if db_path is None:
            # Prompt user for a db to open
            # Choose DB to open
            db_path = QFileDialog.getExistingDirectory(self, caption=db_action,
                                                       directory=str(appsettings.get_config_dir()))
        if is_private:
            app.logger.info("Setting log mode to show only critical logs as database is private")
            self.menubar.set_application_log_level(logging.CRITICAL, session_only=True)
        else:
            self.menubar.set_application_log_level(appsettings.get_log_level())
        # Then open the supplied location if its valid
        if self._path_validated(db_path):
            try:
                self.collection = Collection.open_db(db_path)
                self.collection.is_private = is_private
                self.show_collection(self.collection)
                if not is_private:
                    recents = appsettings.get_recently_opened_collections()
                    appsettings.push_to_list(db_path, recents, appsettings.get_recent_max_size())
                    appsettings.set_recently_opened_collections(recents)
                    self.menubar.update_recents(recents)
            except (CollectionNotFoundError, CorruptedCollectionError) as e:
                apputils.show_exception(self, e)

    def _paths_changed(self, _paths):
        app.logger.debug(f"Selection changed to {_paths}")
        if len(_paths) > 0:
            self._task_manager.start_task(self._MLIB_TASK_PATH_CHANGE, self.collection.data, {"paths": _paths})
        else:
            app.logger.debug("Empty path change request will not be submitted to collection")

    def _view_event(self, action, event_args):
        # TODO: Deprecate this and transfer this logic to the view manager
        pass
        # match action:
        #     case ViewAction.VIEW:
        #         view = event_args
        #         app.logger.debug(f"View changed {view}")
        #         new_view = view.view(self)
        #         self.view_layout.replaceWidget(self.current_view, new_view)
        #         del self.current_view
        #         self.current_view = new_view
        #         self.current_view_type = view
        #         self.current_view_type_label.setText(view.name)
        #         # If a path is being viewed, reload it
        #         if self.current_view_details.property("model_data") is not None:
        #             self._display_model_data(self.current_view_details.property("model_data"),
        #                                      self.current_view_details.property("paths"),
        #                                      self.current_view_details.property("fields"))
        #
        #     case ViewAction.FIELD:
        #         fields = event_args
        #         app.logger.debug(f"Show fields changed")
        #         if self.current_view_details.property("model_data") is not None:
        #             self._display_model_data(self.current_view_details.property("model_data"),
        #                                      self.current_view_details.property("paths"),
        #                                      fields)

    def _display_model_data(self, model_data: list, fields: set):
        self._view_manager.show_data(model_data, list(fields))

    def _file_click(self, itemdata: dict, file_data: FileData | None, collection_path: str):
        model_data = None
        if file_data is not None:
            # Query the collection for this file
            file, _ = self.collection.search(str(file_data.sourcefile))
            if file is not None:
                model_data = ModelData(data=file, path=collection_path)
        else:
            model_data = ModelData(data=itemdata, path=collection_path)

        if model_data:
            for plugin in self._plugins:
                if isinstance(plugin, FileClickHandler):
                    plugin.handle_file_click([model_data], self.collection.tags)

    def _get_new_path(self, is_dir=False) -> list:
        exiftool_file_filter = f"ExifTool Supported Files (*.{' *.'.join(exifinfo.SUPPORTED_FORMATS.split(' '))})"
        return apputils.get_new_paths(parent=self, is_dir=is_dir, file_filter=exiftool_file_filter)

    def _path_validated(self, path):
        if path == "" or not Path(path).exists():
            apputils.show_exception(self, ValueError(f"The path `{path}` is not a valid location"))
            return False
        return True


if __name__ == '__main__':
    # Test if Exiftool is installed
    exifinfo.test_exiftool()

    # Check for input arguments
    parser = argparse.ArgumentParser(prog=app.__APP_NAME__, description="Frontend to the excellent exiftool")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--paths", metavar="p", type=str, nargs="*", help="Path(s) to read the exif data from")
    group.add_argument("--collection", metavar="db", type=str, help="The full path of the collection to open")

    parser.add_argument("--disableplugins", metavar="d", type=str, nargs="*", help="Disables the plugin")

    args = parser.parse_args()
    app.logger.debug(f"Input args supplied          paths: {args.paths}")
    app.logger.debug(f"Input args supplied     collection: {args.collection}")
    app.logger.debug(f"Input args supplied disableplugins: {args.disableplugins}")

    app.logger.debug(f"############################### TESTING CODE HERE ###############################")

    app.logger.debug(f"############################### TESTING CODE HERE ###############################")

    # Prepare GUI with database if supplied
    application = QApplication(sys.argv)
    app.logger.debug(f"{app.__APP_NAME__} is starting up")
    medialib_app = MediaLibApp(args)

    # Instantiate necessary plugins
    medialib_app_startup_plugins = [
        search.FindWidget(medialib_app),
        search.QueryWidget(medialib_app),
        info.FileInfoPlugin(medialib_app),
        # info.MapViewer(medialib_app)
    ]
    for medialib_app_startup_plugin in medialib_app_startup_plugins:
        if args.disableplugins and medialib_app_startup_plugin.name in args.disableplugins:
            app.logger.warning(f"{medialib_app_startup_plugin.name} plugin has been disabled by user")
        else:
            medialib_app.register_plugin(medialib_app_startup_plugin)

    # Start App
    sys.exit(application.exec())
