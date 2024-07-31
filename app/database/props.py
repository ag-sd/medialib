from enum import StrEnum


class DBType(StrEnum):
    IN_MEMORY = "in-memory"
    ON_DISK = "on-disk"


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

_FIELDS_BASIC = [
    "SourceFile",
    "System:FileName",
    "System:Directory",
    "System:FileSize",
    "System:FileModifyDate",
    "System:FileAccessDate",
    "System:FileInodeChangeDate",
    "System:FilePermissions",
    "File:FileType",
    "File:FileTypeExtension",
    "File:MIMEType",
]

_FIELDS_IMAGE = _FIELDS_BASIC + [
    "File:ImageWidth",
    "File:ImageHeight",
    "File:EncodingProcess",
    "File:BitsPerSample",
    "File:ColorComponents",
    "File:YCbCrSubSampling",
    "PNG:ImageWidth",
    "PNG:ImageHeight",
    "PNG:BitDepth",
    "PNG:ColorType",
    "PNG:Compression",
    "PNG:Filter",
    "PNG:Interlace",
    "JFIF:JFIFVersion",
    "JFIF:ResolutionUnit",
    "JFIF:XResolution",
    "JFIF:YResolution",
    "IFD0:Make",
    "IFD0:Model",
    "IFD0:Orientation",
    "IFD0:XResolution",
    "IFD0:YResolution",
    "IFD0:ResolutionUnit",
    "IFD0:Software",
    "IFD0:ModifyDate",
    "ExifIFD:ExifImageWidth",
    "ExifIFD:ExifImageHeight",
    "IFD1:Compression",
    "IFD1:XResolution",
    "IFD1:YResolution",
    "IFD1:ResolutionUnit",
    "Composite:ImageSize",
    "Composite:Megapixels",
]


def get_basic_fields():
    return set(_FIELDS_BASIC.copy())


def get_image_fields():
    return set(_FIELDS_IMAGE.copy())
