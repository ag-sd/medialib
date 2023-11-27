import app
from app.database.exifinfo import ExifInfo
from app.views import ViewType


class Database:
    def __init__(self, is_default, database_path, database_name, paths: list, views: list):
        self._is_default = is_default
        self._database_path = database_path
        self._database_name = database_name
        self._paths = paths
        self._views = views
        self._path_cache = {}

    @property
    def default_view(self):
        if self._is_default:
            return ViewType.JSON
        return ViewType.CSV

    @property
    def database_name(self):
        return self._database_name

    @property
    def paths(self):
        return self._paths

    @property
    def views(self):
        return self._views

    def get_path_data(self, path: str, view: ViewType) -> str:
        """
        Checks if the path is in cache, if present, returns its data. if missing, and this is a default database,
        extracts the exif info and returns it. If its not a default database, returns the data associated with this path
        :param path: The file to test
        :param view: The view to return
        :return: The data to represent this path
        :raises: ValueError if path is not present in database
        :raises: ValueError if view is not supported for database
        """

        if path not in self._paths:
            raise ValueError(f"{path} was not found in this database")

        if view not in self._views:
            raise ValueError(f"{view} was not supported for this database")

        key = f"{view.name}:{path}"
        if key not in self._path_cache:
            app.logger.debug(f"Exif data for '{key}' not in cache. Adding it")
            if self._is_default:
                info = ExifInfo(path, view.format)
                self._path_cache[key] = info.data
            else:
                raise NotImplementedError("Implement a DB lookup")

        app.logger.debug(f"Returning exif data for '{key}' from cache")
        return self._path_cache[key]

    @classmethod
    def create_default(cls, paths: list):
        """
        Creates and returns a default database
        :param paths: The paths to add to this database
        :return: A Database object
        """
        return cls(is_default=True, paths=paths, views=[view for view in ViewType],
                   database_path="", database_name="Default", )

    @classmethod
    def open_db(cls, database_path: str):
        """
        Opens and returns a database from the specified path
        :param database_path: The path to the database
        :return: A Database object
        """
