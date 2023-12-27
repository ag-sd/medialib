import configparser
import datetime
import json
from enum import StrEnum

from app import appsettings
from app.database.ds import Database, DBType


class RegistryFields(StrEnum):
    SAVE_PATH = "save_path"
    PATHS = "paths"
    TYPE = "type"
    CREATED = "created"
    UPDATED = "updated"


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
DEFAULT_DB_NAME = "Default"

############## NOTES
# To process multiple files, a single call is enough
# exiftool -progress -j -g -struct -w "/mnt/dev/testing/.database/%f.json"  "/home/sheldon/Downloads/20170812 Edward Dye 340.jpg" "/home/sheldon/Downloads/art-of-being/images/slider-img3.jpg" "/home/sheldon/Desktop/2023/202306__/IMG_5727.JPG"
# To process dirs, a call per dir is required, else the tool writes out one file per file found in the dir
# exiftool -progress -j -g -struct "/home/sheldon/Downloads/art-of-being/images" > "/mnt/dev/testing/.database/images.json"
