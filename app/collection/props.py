from enum import StrEnum


class DBType(StrEnum):
    IN_MEMORY = "in-memory"
    ON_DISK = "on-disk"


S_COLLECTION = "collection"
S_VERSION = "version"

PROPERTIES_FILE = "collection"

DB_INDEX_FILE = "duck.db"
DB_INDEX_NAME = "collection_index"
DB_SAVE_PATH = "save_path"
DB_PATHS = "paths"
DB_TYPE = "collection_type"
DB_CREATED = "created"
DB_UPDATED = "updated"
DB_TAGS = "tags"
DB_NAME = "collection_name"
DB_DEFAULT_NAME = "default-collection"
DB_TAG_GROUP_DEFAULT = "ROOT"
DB_TAG_GROUP_SYSTEM = "System"

V_VERSION = "version"

EXIFTOOL_APP = "exiftool"
EXIFTOOL_CSV_DELIMITER = "|"

FIELD_SOURCE_FILE = "SourceFile"
FIELD_FILE_NAME = "System:FileName"
FIELD_FILE_SIZE = "System:FileSize"
FIELD_DIRECTORY = "System:Directory"
FIELD_COLLECTION_PATH = "ViewMetadata:Path"
FIELD_COLLECTION_FILEDATA = "ViewMetadata:FileData"

_FIELDS_BASIC = [
    FIELD_SOURCE_FILE,
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
