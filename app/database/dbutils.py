import configparser
import datetime
import json
from enum import StrEnum
from pathlib import Path

import app
import appsettings
from app.database.exifinfo import ExifInfo
from app.views import ViewType


class DatabaseType(StrEnum):
    REGISTERED = "Registered"
    UNREGISTERED = "Unregistered"


class Database:
    """
    A Database represents the consolidated list of paths that have data in the db
    """

    def __init__(self, is_default: bool, database_name,
                 database_type: DatabaseType, paths: list, views: list, save_path: str = None,
                 created: str = None, updated: str = None):
        """
        Set up a new Database with the supplied parameters
        :param is_default: Is the database a default database or not.
        A default database is not saved to disk for later retrieval
        :param save_path: The path on disk where this database is saved. Not applicable for a default database
        :param database_name: The name of this database. Not applicable for a default database
        :param database_type: The type of this database
        :param paths: The paths that comprise this database. This field cannot be empty
        :param views: The views that are supported by this database. If a database is a default database, usually all
        views are supported. If it's a saved database that's offline, only the Library view is supported
        :raise ValueError: if paths is empty
        """
        self._is_default = is_default
        self._save_path = save_path
        self._database_name = database_name
        self._paths = paths
        self._views = views
        self._type = database_type
        self._created = created
        self._updated = updated
        self._path_cache = {}
        self.validate_database(self)

    @property
    def is_default(self):
        return self._is_default

    @property
    def type(self):
        return self._type

    @property
    def name(self):
        return self._database_name

    @property
    def save_path(self) -> str:
        return self._save_path

    @property
    def paths(self):
        return self._paths

    @property
    def views(self):
        return self._views

    @property
    def default_view(self):
        return ViewType.TABLE

    @property
    def created(self):
        return self._created

    @property
    def updated(self):
        return self._updated

    def add_paths(self, paths: list):
        """
        Adds the supplied paths to the database
        :param paths: The paths to add
        """
        self._paths.extend(path for path in paths if path not in self._paths)

    def get_path_data(self, path: str, view: ViewType, write_to_file=False) -> str:
        """
        Checks if the path is in cache, if present, returns its data. if missing, and this is a default database,
        extracts the exif info and returns it. If its not a default database, returns the data associated with this path
        :param write_to_file: Whether results of the exiftool should be written to cache
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

            if write_to_file:
                out_file = Path(self.save_path) / key
                app.logger.debug(f"Writing contents of {path} to {out_file}")
            else:
                out_file = None

            info = ExifInfo(path, view.format, output_path=out_file)
            self._path_cache[key] = info.data

        app.logger.debug(f"Returning exif data for '{key}' from cache")
        return self._path_cache[key]

    def save(self):
        """
        Saves this database to the disk based on its configuration
        """
        if self.is_default:
            raise ValueError("A default database cannot be saved")

        # Create the save path
        Path(self.save_path).mkdir(parents=True, exist_ok=True)

        # Validate database
        self.validate_database(self, test_paths=True)

        app.logger.debug(f"Starting to save database {self}")
        # Blow the cache to force a refresh
        self._path_cache = {}
        # STEP : Iterate through each path in the database and write its metadata to disk
        for path in self.paths:
            self.get_path_data(path, ViewType.JSON, write_to_file=True)

    def __repr__(self):
        return f"Database: [Default: {self.is_default}] {self._database_name if not self._is_default else ''}"

    @staticmethod
    def _create_path_key(path: str, view: ViewType) -> str:
        """
        Creates a key that uniquely identifies this path in the database cache. Cache could be in memory or on disk
        :param path: The path to create the key for
        :param view: The view for this path
        :return: A string of the key that uniquely identifies this path in the database/cache
        """
        path_parts = Path(path).parts
        key = f"{'__'.join(path_parts[1:])}.{view.format.name.lower()}"
        return key

    @staticmethod
    def validate_database(database, test_paths: bool = False):
        if database.name == "":
            raise ValueError("A name must be provided for this database")

        if not database.is_default:
            if not database.save_path:
                raise ValueError("Database is missing a valid save path")

            if len(database.paths) == 0:
                raise ValueError("A database must have at least one path")

        if test_paths:
            for path in database.paths:
                if not Path(path).exists():
                    raise ValueError(f"Database path '{path}' is is not a valid location")

    @classmethod
    def create_default(cls, paths: list):
        """
        Creates and returns a default database
        :param paths: The paths to add to this database
        :return: A Database object
        """
        return cls(is_default=True, paths=paths, views=[view for view in ViewType],
                   save_path=None, database_name=DEFAULT_DB_NAME, database_type=DatabaseType.REGISTERED)

    @classmethod
    def open_db(cls, database_path: str):
        """
        Opens and returns a database from the specified path
        :param database_path: The path to the database
        :return: A Database object
        """
        raise NotImplementedError("Not Implemented")


class DatabaseRegistry:
    def __init__(self, registry_file):
        """
        Do not directly call this object.
        :param registry_file: The ini registry file
        """
        _config = configparser.ConfigParser()
        _config.read(registry_file)
        self._registry = _config
        self._registry_file = registry_file

    @property
    def databases(self):
        return self._registry.sections()

    def get(self, database_name: str):
        """
        Get the database from the registry
        :param database_name: The database to get
        :return: The database information as a dict
        :raise: A ValueError if the database was not found in the registry
        """
        if database_name not in self._registry:
            raise ValueError(f"{database_name} was not found in this database")

        db = self._registry[database_name]
        return Database(
            is_default=db.getboolean("is_default"),
            database_name=database_name,
            save_path=None if db["save_path"] == "--" else db["save_path"],
            paths=json.loads(db["paths"]),
            views=self._to_view_types(json.loads(db["views"])),
            database_type=DatabaseType[db["type"]]
        )

    def add(self, database: Database):
        """
        Saves this database to the registry. Note: The changes are not saved until `registry.commit` is called!
        :param database: The database to add
        """
        if database.name in self._registry:
            raise ValueError(f"Database exists in registry. To update an existing database use the update method")

        self._change_section(database, created=str(datetime.datetime.now()))

    def update(self, database: Database):
        """
        Updates an existing database. Note: The changes are not saved until `registry.commit` is called!
        :param database: The database to update
        :raise ValueError if the database does not exist in the registry
        """
        if database.name not in self._registry:
            raise ValueError(f"{database.name} was not found in this database")

        self._change_section(database,
                             created=self._registry[database.name]["created_on"],
                             updated=str(datetime.datetime.now()))

    def delete(self, database_name) -> bool:
        """
        Deletes the database from the registry. Note: The changes are not saved until `registry.commit` is called!
        :param database_name: The database to delete
        :return: True if the database was deleted
        """
        return self._registry.remove_section(database_name)

    def commit(self):
        """
        Commits the database to the disk
        :return:
        """
        with open(self._registry_file, "w") as registry_file:
            self._registry.write(registry_file)

    def _change_section(self, database: Database, created=None, updated=None):
        self._registry[database.name] = {
            "is_default": database.is_default,
            "save_path": str(database.save_path) if database.save_path is not None else "--",
            "paths": json.dumps(database.paths),
            "views": json.dumps(self._from_view_types(database.views)),
            "type": database.type.name,
        }
        if created is not None:
            self._registry[database.name]["created_on"] = created

        if updated is not None:
            self._registry[database.name]["updated_on"] = updated

    @staticmethod
    def _from_view_types(view_types):
        strs = []
        for vt in view_types:
            strs.append(vt.name)
        return strs

    @staticmethod
    def _to_view_types(view_types):
        vts = []
        for vt in view_types:
            vts.append(ViewType[vt])
        return vts


def get_registry():
    return _db_registry


_db_registry = DatabaseRegistry(appsettings.get_registry_db())
DEFAULT_DB_NAME = "Default"

############## NOTES
# To process multiple files, a single call is enough
# exiftool -progress -j -g -struct -w "/mnt/dev/testing/.database/%f.json"  "/home/sheldon/Downloads/20170812 Edward Dye 340.jpg" "/home/sheldon/Downloads/art-of-being/images/slider-img3.jpg" "/home/sheldon/Desktop/2023/202306__/IMG_5727.JPG"
# To process dirs, a call per dir is required, else the tool writes out one file per file found in the dir
# exiftool -progress -j -g -struct "/home/sheldon/Downloads/art-of-being/images" > "/mnt/dev/testing/.database/images.json"
