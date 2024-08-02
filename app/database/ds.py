import configparser
import datetime
import json
from abc import abstractmethod
from pathlib import Path

import app
from app.database import indexer, props
from app.database.exifinfo import ExifInfo
from app.database.props import DBType
from app.views import ViewType


class DatabaseNotFoundException(Exception):
    def __init__(self):
        super().__init__("This database was not found!")


class CorruptedDatabaseException(Exception):
    def __init__(self):
        super().__init__("This database is corrupt and cannot be opened. See logs for more details")


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
        self._is_modified = False

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

    @property
    def is_modified(self):
        return self._is_modified

    def clear_cache(self):
        app.logger.debug("Clearing Cache...")
        self._path_cache = {}

    def data(self, path: str, refresh=False):
        """
        Checks if the path is in cache, if present, returns its data. if missing, and this is an in memory database,
        extracts the exif info and returns it. If it's not in-memory database, returns the data associated with this
        path from the disk
        Args:
            path: The path to get data for
            refresh: Whether to force a refresh for an on-disk database

        Returns:
            The data to represent this path

        Raises:
            ValueError if path is not present in database
            ValueError if view is not supported for database

        """
        if path not in self._paths:
            raise ValueError(f"{path} was not found in this database")

        key = self._create_path_key(path)
        if (key not in self._path_cache) or refresh is True:
            if self.type == DBType.IN_MEMORY:
                data = self._get_exif_data(path, key)
            else:
                # Fetch data from disk, add to cache and return it
                # If this path is not present in the db, it's a new path, so add it to the database and
                # Return its content
                cache_file = Path(self.save_path) / key
                if not cache_file.exists() or (cache_file.exists() and refresh is True):
                    if not cache_file.exists():
                        app.logger.warning(f"{path} was not found in this database! Will fetch it now...")
                    app.logger.debug(f"Fetching contents of {path} to {cache_file}")
                    data = self._get_exif_data(path, key, save_file=cache_file)
                else:
                    app.logger.debug(f"Fetching data from disk for path {key}")
                    data = cache_file.read_text(encoding=ExifInfo.DATA_ENCODING)
                if data == "":
                    app.logger.warning(f"{key} has no exif data.")
                    data = "[]"
            self._path_cache[key] = json.loads(data)
            self._update_tags(path)

        app.logger.debug(f"Returning exif data for '{key}' from cache")
        return self._path_cache[key]

    def add_paths(self, paths: list):
        """
        Adds the supplied paths to the database
        :param paths: The paths to add
        """
        self._paths.extend(path for path in paths if path not in self._paths)
        self._is_modified = True

    def save(self, save_path: str = None, db_type: DBType = DBType.ON_DISK):
        """
        Saves this database to the disk based on its configuration
        """
        # Save path must exist
        if save_path is None:
            save_path = self.save_path

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
        # Blow the cache to force subsequent reloads from disk
        self.clear_cache()
        # Iterate through each path in the database and write its metadata to disk
        for path in self.paths:
            self.data(path, refresh=True)
        # Set DB Type
        self._type = db_type
        # Write Metadata to the database
        app.logger.info("Writing Metadata...")
        Properties.write(self)
        # Index the Database
        app.logger.info("Indexing database...")
        if not indexer.create_index(self.save_path):
            app.logger.exception("Unable to index database. It cannot be searched!")
            raise ValueError("Unable to index this database. Please see logs for more details")
        app.logger.info("Done..")
        self._is_modified = False

    def reload(self):
        if self.type == DBType.ON_DISK:
            r_db = Properties.as_dictionary(self.save_path)
            self._database_name = r_db[props.DB_NAME]
            self._save_path = r_db[props.DB_SAVE_PATH]
            self._paths = r_db[props.DB_PATHS]
            self._type = r_db[props.DB_TYPE]
            self._created = r_db[props.DB_CREATED]
            self._updated = r_db[props.DB_UPDATED]
            self._tags = r_db[props.DB_TAGS]
            self._is_modified = False
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
    def _get_exif_data(path: str, key: str, save_file=None):
        app.logger.debug(f"Fetching data from exiftool for path {key}")
        path_info = ExifInfo(path, save_file=save_file)
        return path_info.data

    @staticmethod
    def _create_path_key(path: str) -> str:
        """
        Creates a key that uniquely identifies this path in the database cache. Cache could be in memory or on disk
        :param path: The path to create the key for
        :return: A string of the key that uniquely identifies this path in the database/cache
        """
        path_parts = Path(path).parts
        key = f"{'__'.join(path_parts[1:])}.{ViewType.JSON.name.lower()}"
        return key

    def _update_tags(self, _path):
        current_tags = dict.fromkeys(self._tags)
        for entry in self._path_cache[self._create_path_key(_path)]:
            current_tags.update(dict.fromkeys(entry.keys()))
        self._tags = list(current_tags)

    @classmethod
    def create_in_memory(cls, paths: list, save_path=None):
        """
        Creates and returns a default database
        :param paths: The paths to add to this database
        :param save_path: The path this db will be eventually saved to (optional)
        :return: A Database object
        """
        return cls(DBType.IN_MEMORY, props.DB_DEFAULT_NAME, paths, save_path=save_path,
                   created=str(datetime.datetime.now()), updated=str(datetime.datetime.now()))

    @classmethod
    def open_db(cls, database_path: str):
        """
        Opens and returns a database from the specified path
        :param database_path: The path to the database
        :return: A Database object
        """
        db_path = Path(database_path)
        if not db_path.exists():
            raise DatabaseNotFoundException

        return cls(**Properties.as_dictionary(database_path))


class Properties:

    @staticmethod
    def as_database(database_path: str) -> Database:
        """
        Get the database details from the property file
        :return: The database information as a db object
        """
        config_file = Properties._get_config_file(database_path)
        if not Path(config_file).exists():
            raise CorruptedDatabaseException
        config = configparser.ConfigParser()
        config.read(Properties._get_config_file(database_path))
        Properties._test_version(config)

        db = config[props.S_DATABASE]
        return Database(
            db_name=db[props.DB_NAME],
            save_path=str(database_path),
            paths=json.loads(db[props.DB_PATHS]),
            db_type=DBType[db[props.DB_TYPE]],
            created=db[props.DB_CREATED] if props.DB_CREATED in db else None,
            updated=db[props.DB_UPDATED] if props.DB_UPDATED in db else None,
            tags=json.loads(db[props.DB_TAGS])
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

        db = config[props.S_DATABASE]
        return {
            props.DB_NAME: db[props.DB_NAME],
            props.DB_SAVE_PATH: str(database_path),
            props.DB_PATHS: json.loads(db[props.DB_PATHS]),
            props.DB_TYPE: DBType[db[props.DB_TYPE]],
            props.DB_CREATED: db[props.DB_CREATED] if props.DB_CREATED in db else None,
            props.DB_UPDATED: db[props.DB_UPDATED] if props.DB_UPDATED in db else None,
            props.DB_TAGS: json.loads(db[props.DB_TAGS])
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
        config[props.S_VERSION] = {
            props.V_VERSION: version
        }

    @staticmethod
    def _write_database(config: configparser.ConfigParser, database: Database):
        config[props.S_DATABASE] = {
            props.DB_NAME: database.name,
            props.DB_SAVE_PATH: database.save_path,
            props.DB_PATHS: json.dumps(database.paths),
            props.DB_TYPE: database.type.name,
            props.DB_CREATED: database.created,
            props.DB_UPDATED: database.updated,
            props.DB_TAGS: json.dumps(database.tags)
        }

    @staticmethod
    def _test_version(parser: configparser.ConfigParser) -> bool:
        if props.S_VERSION in parser:
            file_version = parser[props.S_VERSION]
            app.logger.warning(f"Version test for {file_version} skipped!")
        return True

    @staticmethod
    def _get_config_file(db_path: str) -> str:
        config_file = Path(db_path) / f"{props.PROPERTIES_FILE}.ini"
        return str(config_file)


class HasDatabaseDisplaySupport:

    @abstractmethod
    def show_database(self, database: Database):
        raise NotImplemented

    @abstractmethod
    def shut_database(self):
        raise NotImplemented
