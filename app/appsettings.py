from pathlib import Path


def get_registry_dir() -> Path:
    # return Path.home() / ".config" / ".medialib"
    return Path("/mnt/dev/testing") / "Medialib"


def get_registry_db() -> Path:
    return get_registry_dir() / "dbregistry.ini"
