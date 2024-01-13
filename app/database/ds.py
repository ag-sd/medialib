import configparser
import datetime
import json
from enum import StrEnum
from pathlib import Path

import app
from app.database.exifinfo import ExifInfo
from app.views import ViewType


class DBType(StrEnum):
    IN_MEMORY = "in-memory"
    ON_DISK = "on-disk"


class Props(StrEnum):
    DB_SAVE_PATH = "save_path"
    DB_PATHS = "paths"
    DB_TYPE = "db_type"
    DB_CREATED = "created"
    DB_UPDATED = "updated"
    DB_TAGS = "tags"
    DB_NAME = "db_name"
    V_VERSION = "version"


DEFAULT_DB_NAME = "default-db"


class Database:
    """
    A Database represents the consolidated list of paths that have data in the db
    """

    def __init__(self, db_type: DBType, db_name: str, paths: list, save_path: str | None, created: str, updated: str,
                 tags=None):
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
        if tags is None:
            tags = []
        self._save_path = save_path
        self._database_name = db_name
        self._paths = paths
        self._type = db_type
        self._created = created
        self._updated = updated
        self._path_cache = {}
        self._tags = tags
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
                app.logger.debug(f"Fetching data from exiftool for path {key}")
                info = ExifInfo(path, view.format)
                self._path_cache[key] = info.data
                self._tags = list(dict.fromkeys(self._tags + info.tags))
            else:
                # Fetch data from disk, add to cache and return it
                app.logger.debug(f"Fetching data from disk for path {key}")
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
        # Save path must exist
        if not save_path:
            raise ValueError("Database is missing a valid save path")
        # Save the save path
        self._save_path = save_path
        p_save_path = Path(self.save_path)
        # Create the save path
        p_save_path.mkdir(parents=True, exist_ok=True)
        # Capture DB Name
        self._database_name = p_save_path.name

        # Validate database
        self._validate_database(self)
        # All paths must exist
        for path in self.paths:
            if not Path(path).exists():
                raise ValueError(f"Path '{path}' is is not a valid location")

        app.logger.debug(f"Starting to save database {self}")
        # Iterate through each path in the database and write its metadata to disk
        for path in self.paths:
            out_file = Path(self.save_path) / self._create_path_key(path, ViewType.JSON)
            app.logger.debug(f"Writing contents of {path} to {out_file}")
            info = ExifInfo(path, ViewType.JSON.format, save_file=str(out_file))
            _ = info.data

        # Blow the cache to force subsequent reloads from disk
        self._path_cache = {}
        # Set DB Type
        self._type = db_type
        # Write Metadata to the database
        Properties.write(self)

    def reload(self):
        if self.type == DBType.ON_DISK:
            r_db = Properties.as_dictionary(self.save_path)
            self._database_name = r_db[Props.DB_NAME]
            self._save_path = r_db[Props.DB_SAVE_PATH]
            self._paths = r_db[Props.DB_PATHS]
            self._type = r_db[Props.DB_TYPE]
            self._created = r_db[Props.DB_CREATED]
            self._updated = r_db[Props.DB_UPDATED]
            self._tags = r_db[Props.DB_TAGS]
        else:
            app.logger.error("Unable to reload an in-memory database!")

    def __repr__(self):
        return f"Database: [Type: {self.type}] {self._database_name}"

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
    def create_in_memory(cls, paths: list, save_path=None):
        """
        Creates and returns a default database
        :param paths: The paths to add to this database
        :param save_path: The path this db will be eventually saved to (optional)
        :return: A Database object
        """
        return cls(DBType.IN_MEMORY, DEFAULT_DB_NAME, paths, save_path=save_path,
                   created=str(datetime.datetime.now()), updated=str(datetime.datetime.now()))

    @classmethod
    def open_db(cls, database_path: str):
        """
        Opens and returns a database from the specified path
        :param database_path: The path to the database
        :return: A Database object
        """
        return cls(**Properties.as_dictionary(database_path))


class Properties:
    S_DATABASE = "database"
    S_VERSION = "version"
    PROPERTIES_FILE = "database"

    @staticmethod
    def as_database(database_path: str) -> Database:
        """
        Get the database details from the property file
        :return: The database information as a db object
        """
        config = configparser.ConfigParser()
        config.read(Properties._get_config_file(database_path))
        Properties._test_version(config)

        db = config[Properties.S_DATABASE]
        return Database(
            db_name=db[Props.DB_NAME],
            save_path=str(database_path),
            paths=json.loads(db[Props.DB_PATHS]),
            db_type=DBType[db[Props.DB_TYPE]],
            created=db[Props.DB_CREATED] if Props.DB_CREATED in db else None,
            updated=db[Props.DB_UPDATED] if Props.DB_UPDATED in db else None,
            tags=json.loads(db[Props.DB_TAGS])
        )

    @staticmethod
    def as_dictionary(database_path: str) -> dict:
        """
        Get the database details from the property file
        :return: The database information as a db object
        """
        config = configparser.ConfigParser()
        config.read(Properties._get_config_file(database_path))
        Properties._test_version(config)

        db = config[Properties.S_DATABASE]
        return {
            Props.DB_NAME: db[Props.DB_NAME],
            Props.DB_SAVE_PATH: str(database_path),
            Props.DB_PATHS: json.loads(db[Props.DB_PATHS]),
            Props.DB_TYPE: DBType[db[Props.DB_TYPE]],
            Props.DB_CREATED: db[Props.DB_CREATED] if Props.DB_CREATED in db else None,
            Props.DB_UPDATED: db[Props.DB_UPDATED] if Props.DB_UPDATED in db else None,
            Props.DB_TAGS: json.loads(db[Props.DB_TAGS])
        }

    @staticmethod
    def write(database: Database):
        """
        Updates existing database properties or creates if they do not exist
        """
        config_file = Properties._get_config_file(database.save_path)
        config = configparser.ConfigParser()
        config.read(config_file)

        Properties._test_version(config)

        Properties._write_version(config, app.__VERSION__)
        Properties._write_database(config, database)
        with open(config_file, "w+") as out_file:
            config.write(out_file)

    @staticmethod
    def _write_version(config: configparser.ConfigParser, version: str):
        config[Properties.S_VERSION] = {
            Props.V_VERSION: version
        }

    @staticmethod
    def _write_database(config: configparser.ConfigParser, database: Database):
        config[Properties.S_DATABASE] = {
            Props.DB_NAME: database.name,
            Props.DB_SAVE_PATH: database.save_path,
            Props.DB_PATHS: json.dumps(database.paths),
            Props.DB_TYPE: database.type.name,
            Props.DB_CREATED: database.created,
            Props.DB_UPDATED: database.updated,
            Props.DB_TAGS: json.dumps(database.tags)
        }

    @staticmethod
    def _test_version(parser: configparser.ConfigParser) -> bool:
        if Properties.S_VERSION in parser:
            file_version = parser[Properties.S_VERSION]
            app.logger.warning(f"Version test for {file_version} skipped!")
        return True

    @staticmethod
    def _get_config_file(db_path: str) -> str:
        return str(Path(db_path) / f"{Properties.PROPERTIES_FILE}.ini")