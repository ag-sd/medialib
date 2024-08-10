import tempfile
from pathlib import Path

from app.database.ds import Database, Properties


def get_temp_files(count) -> list:
    files = []
    for i in range(count):
        tmp = Path(tempfile.NamedTemporaryFile().name)
        tmp.touch()
        files.append(str(tmp))
    return files


def get_saved_db(save_path, num_files):
    db = Database.create_in_memory(paths=get_temp_files(num_files), save_path=save_path)
    Properties.write(db)
    return Properties.as_database(save_path)


def get_test_paths():
    return [
        str(Path(__file__).parent / ".." / "resources" / "media/audio"),
        str(Path(__file__).parent / ".." / "resources" / "media/image"),
    ]


def create_test_media_db(save_path: str, test_paths: list = get_test_paths()):
    return Database.create_in_memory(test_paths, save_path)
