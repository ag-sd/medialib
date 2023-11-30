from pathlib import Path

import app
from app.database.exifinfo import ExifInfo
from app.views import ViewType


class Database:
    """
    A Database represents the consolidated list of paths that have data in the db
    """
    DEFAULT_NAME = "Default"

    def __init__(self, is_default, database_path, database_name, paths: list, views: list):
        """
        Set up a new Database with the supplied parameters
        :param is_default: Is the database a default database or not.
        A default database is not saved to disk for later retrieval
        :param database_path: The path on disk where this database is saved. Not applicable for a default database
        :param database_name: The name of this database. Not applicable for a default database
        :param paths: The paths that comprise this database. This field cannot be empty
        :param views: The views that are supported by this database. If a database is a default database, usually all
        views are supported. If it's a saved database that's offline, only the Library view is supported
        :raise ValueError: if paths is empty
        """
        # if len(paths) == 0:
        #     raise ValueError("Paths cannot be empty")
        self._is_default = is_default
        self._database_path = database_path
        self._database_name = database_name if database_name is not None else self.DEFAULT_NAME
        self._paths = paths
        self._views = views
        self._path_cache = {}

    @property
    def is_default(self):
        return self._is_default

    @property
    def name(self):
        return self._database_name

    @property
    def path(self):
        return self._database_path

    @property
    def paths(self):
        return self._paths

    @property
    def views(self):
        return self._views

    @property
    def default_view(self):
        # TODO: Test
        if self._is_default:
            return ViewType.JSON
        return ViewType.CSV

    def add_paths(self, paths: list):
        """
        Adds the supplied paths to the database
        :param paths: The paths to add
        """
        self._paths.extend(path for path in paths if path not in self._paths)

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
        # TODO: Test
        if path not in self._paths:
            raise ValueError(f"{path} was not found in this database")

        if view not in self._views:
            raise ValueError(f"{view} was not supported for this database")

        key = self._create_path_key(path, view)
        if key not in self._path_cache:
            app.logger.debug(f"Exif data for '{key}' not in cache. Adding it")
            if self._is_default:
                info = ExifInfo(path, view.format)
                self._path_cache[key] = info.data
            else:
                raise NotImplementedError("Implement a DB lookup")

        app.logger.debug(f"Returning exif data for '{key}' from cache")
        return self._path_cache[key]

    @staticmethod
    def _create_path_key(path: str, view: ViewType) -> str:
        """
        Creates a key that uniquely identifies this path in the database cache. Cache could be in memory or on disk
        :param path: The path to create the key for
        :param view: The view for this path
        :return: A string of the key that uniquely identifies this path in the database/cache
        """
        path_parts = Path(path).parts
        key = f"{'_'.join(path_parts[1:])}.{view.name.lower()}"
        return key

    @classmethod
    def create_default(cls, paths: list):
        """
        Creates and returns a default database
        :param paths: The paths to add to this database
        :return: A Database object
        """
        return cls(is_default=True, paths=paths, views=[view for view in ViewType],
                   database_path=None, database_name=None, )

    @classmethod
    def open_db(cls, database_path: str):
        """
        Opens and returns a database from the specified path
        :param database_path: The path to the database
        :return: A Database object
        """
        raise NotImplementedError("Not Implemented")


############## NOTES
# To process multiple files, a single call is enough
# exiftool -progress -j -g -struct -w "/mnt/dev/testing/.database/%f.json"  "/home/sheldon/Downloads/20170812 Edward Dye 340.jpg" "/home/sheldon/Downloads/art-of-being/images/slider-img3.jpg" "/home/sheldon/Desktop/2023/202306__/IMG_5727.JPG"
# To process dirs, a call per dir is required, else the tool writes out one file per file found in the dir
# exiftool -progress -j -g -struct "/home/sheldon/Downloads/art-of-being/images" > "/mnt/dev/testing/.database/images.json"



