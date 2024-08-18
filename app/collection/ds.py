import configparser
import datetime
import json
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path

import app
from app.collection import indexer, props
from app.collection.exifinfo import ExifInfo
from app.collection.props import DBType


class CollectionNotFoundError(Exception):
    def __init__(self):
        super().__init__("This collection was not found!")


class CorruptedCollectionError(Exception):
    def __init__(self):
        super().__init__("This collection is corrupt and cannot be opened. See logs for more details")


class CollectionQueryError(Exception):
    def __init__(self, root_exception: Exception):
        super().__init__(f"Query failed. Inner error is:\n {root_exception}")


@dataclass
class SearchResult:
    path: str
    results: list


@dataclass
class SearchResults:
    data: list[SearchResult]
    columns: list
    query: str
    searched_paths: list


class Collection:
    """
    A Collection represents the consolidated list of paths that have data in the db
    """

    def __init__(self, collection_type: DBType, collection_name: str, paths: list, save_path: str | None,
                 created: str, updated: str, tags=None):
        """
        Set up a new Collection with the supplied parameters
        :param save_path: The path on disk where this collection is saved. Not applicable for a default collection
        :param collection_name: The name of this collection. Not applicable for a default collection
        :param collection_type: The type of this collection
        :param paths: The paths that comprise this collection. This field cannot be empty
        :param created: date of creation of this db
        :param updated: date this db was last updated
        :raise ValueError: if paths is empty
        """
        if tags is None:
            tags = []
        self._save_path = save_path
        self._collection_name = collection_name
        self._paths = paths
        self._type = collection_type
        self._created = created
        self._updated = updated
        self._path_cache = {}
        self._tags = tags
        self._validate_collection(self)
        self._is_modified = False

    @property
    def type(self):
        return self._type

    @property
    def name(self):
        return self._collection_name

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

    def set_name(self, name):
        if name is None or name == "" or name == props.DB_DEFAULT_NAME:
            raise ValueError("Invalid name supplied")
        self._collection_name = name

    def query(self, query: str, query_paths: list):
        """
        Queries the collection with the supplied query. The supplied query should be in ANSI SQL
        Args:
            query: The Query to run
            query_paths: The paths on which to run this query

        Returns:
            The data that matches this query

        """
        if self.type == DBType.IN_MEMORY:
            raise CollectionQueryError(TypeError("Cannot query an in-memory collection"))

        app.logger.debug(f"Querying DB index with the following query: {query}")
        search_data = []
        columns = None
        for _path in query_paths:
            disk_cache_file_name = str(self._cache_file_path(self._create_path_key(_path)))
            try:
                results, columns = indexer.query_index(self.save_path, query, disk_cache_file_name)
                search_data.append(SearchResult(results=results, path=_path))
            except Exception as e:
                raise CollectionQueryError(root_exception=e)
        return SearchResults(data=search_data, columns=columns, query=query, searched_paths=query_paths)

    def data(self, path: str, refresh=False):
        """
        Checks if the path is in cache, if present, returns its data. if missing, and this is an in memory collection,
        extracts the exif info and returns it. If it's not in-memory collection, returns the data associated with this
        path from the disk
        Args:
            path: The path to get data for
            refresh: Whether to force a refresh for an on-disk collection

        Returns:
            The data to represent this path

        Raises:
            ValueError if path is not present in collection
            ValueError if view is not supported for collection

        """
        if path not in self._paths:
            raise ValueError(f"{path} was not found in this collection")

        key = self._create_path_key(path)
        if (key not in self._path_cache) or refresh is True:
            if self.type == DBType.IN_MEMORY:
                data = self._get_exif_data(path, key)
            else:
                # Fetch data from disk, add to cache and return it
                # If this path is not present in the db, it's a new path, so add it to the collection and
                # Return its content
                cache_file = self._cache_file_path(key)
                if not cache_file.exists() or (cache_file.exists() and refresh is True):
                    if not cache_file.exists():
                        app.logger.warning(f"{path} was not found in this collection! Will fetch it now...")
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
        Adds the supplied paths to the collection
        :param paths: The paths to add
        """
        self._paths.extend(path for path in paths if path not in self._paths)
        self._is_modified = True

    def save(self, save_path: str = None, db_type: DBType = DBType.ON_DISK):
        """
        Saves this collection to the disk based on its configuration
        """
        # Save path must exist
        if save_path is None and self.save_path is None:
            raise ValueError("Collection is missing a valid save path")

        # Save the save path
        self._save_path = save_path if save_path is not None else self.save_path
        p_save_path = Path(self.save_path)
        # Create the save path
        p_save_path.mkdir(parents=True, exist_ok=True)
        # Capture DB Name
        self._collection_name = p_save_path.name if (self._collection_name is None or
                                                     self._collection_name == props.DB_DEFAULT_NAME) else (
            self._collection_name)

        # Validate collection
        self._validate_collection(self)
        # All paths must exist
        for path in self.paths:
            if not Path(path).exists():
                raise ValueError(f"Path '{path}' is is not a valid location")

        app.logger.debug(f"Starting to save collection {self}")
        # Blow the cache to force subsequent reloads from disk
        self.clear_cache()
        # Set DB Type
        self._type = db_type
        # Iterate through each path in the collection and write its metadata to disk
        for path in self.paths:
            self.data(path, refresh=True)
        # Write Metadata to the collection
        app.logger.info("Writing Metadata...")
        Properties.write(self)
        # Index the Collection
        app.logger.info("Indexing collection...")
        if not indexer.create_index(self.save_path):
            app.logger.exception("Unable to index collection. It cannot be searched!")
            raise ValueError("Unable to index this collection. Please see logs for more details")
        app.logger.info("Done..")
        self._is_modified = False

    def reload(self):
        if self.type == DBType.ON_DISK:
            r_db = Properties.as_dictionary(self.save_path)
            self._collection_name = r_db[props.DB_NAME]
            self._save_path = r_db[props.DB_SAVE_PATH]
            self._paths = r_db[props.DB_PATHS]
            self._type = r_db[props.DB_TYPE]
            self._created = r_db[props.DB_CREATED]
            self._updated = r_db[props.DB_UPDATED]
            self._tags = r_db[props.DB_TAGS]
            self._is_modified = False
        else:
            app.logger.error("Unable to reload an in-memory collection!")

    def __repr__(self):
        return f"Collection: [Type: {self.type}] {self._collection_name}"

    @staticmethod
    def _validate_collection(collection):
        if collection.name == "":
            raise ValueError("A name must be provided for this collection")
        if len(collection.paths) == 0:
            raise ValueError("Collection must have at least one path")

    @staticmethod
    def _get_exif_data(path: str, key: str, save_file=None):
        app.logger.debug(f"Fetching data from exiftool for path {key}")
        path_info = ExifInfo(path, save_file=save_file)
        return path_info.data

    @staticmethod
    def _create_path_key(path: str) -> str:
        """
        Creates a key that uniquely identifies this path in the collection cache. Cache could be in memory or on disk
        :param path: The path to create the key for
        :return: A string of the key that uniquely identifies this path in the collection/cache
        """
        path_parts = Path(path).parts
        key = f"{'__'.join(path_parts[1:])}.json"
        return key

    def _cache_file_path(self, key: str) -> Path:
        return Path(self.save_path) / key

    def _update_tags(self, _path):
        current_tags = dict.fromkeys(self._tags)
        for entry in self._path_cache[self._create_path_key(_path)]:
            current_tags.update(dict.fromkeys(entry.keys()))
        self._tags = list(current_tags)

    @classmethod
    def create_in_memory(cls, paths: list, save_path=None):
        """
        Creates and returns a default collection
        :param paths: The paths to add to this collection
        :param save_path: The path this db will be eventually saved to (optional)
        :return: A Collection object
        """
        return cls(DBType.IN_MEMORY, props.DB_DEFAULT_NAME, paths, save_path=save_path,
                   created=str(datetime.datetime.now()), updated=str(datetime.datetime.now()))

    @classmethod
    def open_db(cls, collection_path: str):
        """
        Opens and returns a collection from the specified path
        :param collection_path: The path to the collection
        :return: A Collection object
        """
        db_path = Path(collection_path)
        if not db_path.exists():
            raise CollectionNotFoundError

        return cls(**Properties.as_dictionary(collection_path))


class Properties:

    @staticmethod
    def as_collection(collection_path: str) -> Collection:
        """
        Get the collection details from the property file
        :return: The collection information as a db object
        """
        config_file = Properties._get_config_file(collection_path)
        if not Path(config_file).exists():
            raise CorruptedCollectionError
        config = configparser.ConfigParser()
        config.read(Properties._get_config_file(collection_path))
        Properties._test_version(config)

        db = config[props.S_COLLECTION]
        return Collection(
            collection_name=db[props.DB_NAME],
            save_path=str(collection_path),
            paths=json.loads(db[props.DB_PATHS]),
            collection_type=DBType[db[props.DB_TYPE]],
            created=db[props.DB_CREATED] if props.DB_CREATED in db else None,
            updated=db[props.DB_UPDATED] if props.DB_UPDATED in db else None,
            tags=json.loads(db[props.DB_TAGS])
        )

    @staticmethod
    def as_dictionary(collection_path: str) -> dict:
        """
        Get the collection details from the property file
        :return: The collection information as a db object
        """
        config = configparser.ConfigParser()
        config.read(Properties._get_config_file(collection_path))
        Properties._test_version(config)

        db = config[props.S_COLLECTION]
        return {
            props.DB_NAME: db[props.DB_NAME],
            props.DB_SAVE_PATH: str(collection_path),
            props.DB_PATHS: json.loads(db[props.DB_PATHS]),
            props.DB_TYPE: DBType[db[props.DB_TYPE]],
            props.DB_CREATED: db[props.DB_CREATED] if props.DB_CREATED in db else None,
            props.DB_UPDATED: db[props.DB_UPDATED] if props.DB_UPDATED in db else None,
            props.DB_TAGS: json.loads(db[props.DB_TAGS])
        }

    @staticmethod
    def write(collection: Collection):
        """
        Updates existing collection properties or creates if they do not exist
        """
        config_file = Properties._get_config_file(collection.save_path)
        config = configparser.ConfigParser()
        config.read(config_file)

        Properties._test_version(config)

        Properties._write_version(config, app.__VERSION__)
        Properties._write_collection(config, collection)
        with open(config_file, "w+") as out_file:
            config.write(out_file)

    @staticmethod
    def _write_version(config: configparser.ConfigParser, version: str):
        config[props.S_VERSION] = {
            props.V_VERSION: version
        }

    @staticmethod
    def _write_collection(config: configparser.ConfigParser, collection: Collection):
        config[props.S_COLLECTION] = {
            props.DB_NAME: collection.name,
            props.DB_SAVE_PATH: collection.save_path,
            props.DB_PATHS: json.dumps(collection.paths),
            props.DB_TYPE: collection.type.name,
            props.DB_CREATED: collection.created,
            props.DB_UPDATED: collection.updated,
            props.DB_TAGS: json.dumps(collection.tags)
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


class HasCollectionDisplaySupport:

    @abstractmethod
    def show_collection(self, collection: Collection):
        raise NotImplemented

    @abstractmethod
    def shut_collection(self):
        raise NotImplemented
