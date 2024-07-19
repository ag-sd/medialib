from enum import StrEnum

S_DATABASE = "database"
S_VERSION = "version"

PROPERTIES_FILE = "database"

DB_INDEX_FILE = "duck.db"
DB_SAVE_PATH = "save_path"
DB_PATHS = "paths"
DB_TYPE = "db_type"
DB_CREATED = "created"
DB_UPDATED = "updated"
DB_TAGS = "tags"
DB_NAME = "db_name"
DB_DEFAULT_NAME = "default-db"

V_VERSION = "version"

EXIFTOOL_APP = "exiftool"
EXIFTOOL_CSV_DELIMITER = "|"


class DBType(StrEnum):
    IN_MEMORY = "in-memory"
    ON_DISK = "on-disk"


