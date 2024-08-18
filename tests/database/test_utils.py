import sys
import tempfile
from pathlib import Path

import app
from app.database.ds import Database, Properties
from tests import test_app


def get_temp_files(count) -> list:
    files = []
    for i in range(count):
        tmp = Path(tempfile.NamedTemporaryFile().name)
        tmp.touch()
        files.append(str(tmp))
    return files


def get_test_paths():
    return [
        str(Path(__file__).parent / ".." / "resources" / "media/audio"),
        str(Path(__file__).parent / ".." / "resources" / "media/image"),
    ]


def create_test_media_db(save_path: str, test_paths: list = get_test_paths()):
    return Database.create_in_memory(test_paths, save_path)


def launch_widget(widget):
    widget.setMinimumSize(500, 1000)
    widget.show()
    sys.exit(test_app.exec())


class CallbackHandler:

    def __init__(self, event, callback=None,expects_callback=True, callback_count=1):
        self._callback_called = False
        self._callback_count = callback_count
        self._callback = callback
        self._expects_callback = expects_callback
        event.connect(self.callback_handler)

    def callback_handler(self, *args):
        app.logger.debug(args)
        if self._callback:
            self._callback(args)
        self._callback_called = True
        self._callback_count -= 1

    @property
    def callback_handled_correctly(self):
        if self._expects_callback:
            return self._callback_called is True and self._callback_count == 0
        else:
            return self._callback_called is False and self._callback_count == 0
