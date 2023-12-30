import configparser
import datetime
import json
from enum import StrEnum
from pathlib import Path

import app
from app import appsettings
from app.database.exifinfo import ExifInfo
from app.views import ViewType


class DBType(StrEnum):
    IN_MEMORY = "in-memory"
    ON_DISK = "on-disk"


class RegistryFields(StrEnum):
    SAVE_PATH = "save_path"
    PATHS = "paths"
    TYPE = "type"
    CREATED = "created"
    UPDATED = "updated"


DEFAULT_DB_NAME = "default-db"


class Database:
    """
    A Database represents the consolidated list of paths that have data in the db
    """

    def __init__(self, db_type: DBType, db_name: str, paths: list, save_path: str | None, created: str, updated: str):
        """
        Set up a new Database with the supplied parameters
        :param save_path: The path on disk where this database is saved. Not applicable for a default database
        :param db_name: The name of this database. Not applicable for a default database
        :param db_type: The type of this database
        :param paths: The paths that comprise this database. This field cannot be empty
        :param created: date of creation of this db
        :param updated: date this db was last updated
        :raise ValueError: if paths is empty
        """
        self._save_path = save_path
        self._database_name = db_name
        self._paths = paths
        self._type = db_type
        self._created = created
        self._updated = updated
        self._path_cache = {}
        self._tags = []
        self._validate_database(self)

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
    def created(self):
        return self._created

    @property
    def updated(self):
        return self._updated

    @property
    def tags(self):
        return self._tags

    def data(self, path: str, view: ViewType = ViewType.JSON):
        """
        Checks if the path is in cache, if present, returns its data. if missing, and this is a in memory database,
        extracts the exif info and returns it. If it's not in-memory database, returns the data associated with this
        path from the disk
        :param path: The path to get data for
        :param view: The view to return
        :return: The data to represent this path
        :raises: ValueError if path is not present in database
        :raises: ValueError if view is not supported for database
        """
        if path not in self._paths:
            raise ValueError(f"{path} was not found in this database")

        key = self._create_path_key(path, view)
        if key not in self._path_cache:
            if self.type == DBType.IN_MEMORY:
                info = ExifInfo(path, view.format)
                self._path_cache[key] = info.data
                self._tags = list(dict.fromkeys(self._tags + info.tags))
            else:
                # Fetch data from disk, add to cache and return it
                out_file = Path(self.save_path) / key
                self._path_cache[key] = json.loads(out_file.read_text(encoding=ExifInfo.DATA_ENCODING))
                self._tags = list(dict.fromkeys(self._tags + ExifInfo.get_tags(self._path_cache[key])))

        app.logger.debug(f"Returning exif data for '{key}' from cache")
        return self._path_cache[key]

    def add_paths(self, paths: list):
        """
        Adds the supplied paths to the database
        :param paths: The paths to add
        """
        self._paths.extend(path for path in paths if path not in self._paths)

    def save(self, save_path: str, db_type: DBType = DBType.ON_DISK):
        """
        Saves this database to the disk based on its configuration
        """
        self._save_path = save_path
        # Create the save path
        Path(self.save_path).mkdir(parents=True, exist_ok=True)

        # Validate database
        self._validate_database(self)
        # All paths must exist
        for path in self.paths:
            if not Path(path).exists():
                raise ValueError(f"Path '{path}' is is not a valid location")
        # Save path must exist
        if not self.save_path:
            raise ValueError("Database is missing a valid save path")

        app.logger.debug(f"Starting to save database {self}")
        # Iterate through each path in the database and write its metadata to disk
        for path in self.paths:
            out_file = Path(self.save_path) / self._create_path_key(path, ViewType.JSON)
            app.logger.debug(f"Writing contents of {path} to {out_file}")
            info = ExifInfo(path, ViewType.JSON.format, save_file=str(out_file))
            _ = info.data

        # Blow the cache to force subsequent reloads from disk
        self._path_cache = {}
        # Set mode = db type
        self._type = db_type

    def __repr__(self):
        return f"Database: [Type: {self.type}] {self._database_name}"

    # def get_path_data(self, path: str, view: ViewType, ignore_cache: bool = False, write_to_file=False) -> str:
    #     """
    #     Checks if the path is in cache, if present, returns its data. if missing, and this is a default database,
    #     extracts the exif info and returns it. If its not a default database, returns the data associated with this path
    #     :param path: The file to test
    #     :param view: The view to return
    #     :param ignore_cache: If true, will ignore the entry from the cache and reload the path. Once reloaded, will add
    #     it back to the cache for future use
    #     :return: The data to represent this path
    #     :raises: ValueError if path is not present in database
    #     :raises: ValueError if view is not supported for database
    #     """
    #     # TODO: Test
    #     if path not in self._paths:
    #         raise ValueError(f"{path} was not found in this database")
    #
    #     key = self._create_path_key(path, view)
    #     if ignore_cache or key not in self._path_cache:
    #         app.logger.debug(f"Exif data for '{key}' not in cache. Adding it")
    #
    #         if write_to_file:
    #             out_file = Path(self.save_path) / self._create_path_key(path, ViewType.JSON)
    #             app.logger.debug(f"Writing contents of {path} to {out_file}")
    #         else:
    #             out_file = None
    #
    #         info = ExifInfo(path, view.format, save_file=out_file)
    #         self._path_cache[key] = info.data
    #
    #     app.logger.debug(f"Returning exif data for '{key}' from cache")
    #     return self._path_cache[key]

    @staticmethod
    def _validate_database(database):
        if database.name == "":
            raise ValueError("A name must be provided for this database")
        if len(database.paths) == 0:
            raise ValueError("Database must have at least one path")

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

    @classmethod
    def create_in_memory(cls, paths: list, name: str = DEFAULT_DB_NAME):
        """
        Creates and returns a default database
        :param paths: The paths to add to this database
        :param name: The database name
        :return: A Database object
        """
        return cls(DBType.IN_MEMORY, name, paths, save_path=None,
                   created=str(datetime.datetime.now()), updated=str(datetime.datetime.now()))

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
            db_name=database_name,
            save_path=None if db[RegistryFields.SAVE_PATH] == "--" else db[RegistryFields.SAVE_PATH],
            paths=json.loads(db[RegistryFields.PATHS]),
            db_type=DBType[db[RegistryFields.TYPE]],
            created=db[RegistryFields.CREATED] if RegistryFields.CREATED in db else None,
            updated=db[RegistryFields.UPDATED] if RegistryFields.UPDATED in db else None
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
                             created=self._registry[database.name][RegistryFields.CREATED],
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
            RegistryFields.SAVE_PATH: str(database.save_path) if database.save_path is not None else "--",
            RegistryFields.PATHS: json.dumps(database.paths),
            RegistryFields.TYPE: database.type.name,
        }
        if created is not None:
            self._registry[database.name][RegistryFields.CREATED] = created

        if updated is not None:
            self._registry[database.name][RegistryFields.UPDATED] = updated


def get_registry():
    return _db_registry


_db_registry = DatabaseRegistry(appsettings.get_registry_db().name)
