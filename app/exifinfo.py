import json
import os.path
import shutil
import subprocess
from enum import Enum

import app

EXIFTOOL_APP = "exiftool"


# https://exiftool.org/exiftool_pod.html#Input-output-text-formatting

def test_exiftool():
    exiftool = shutil.which(EXIFTOOL_APP)
    if exiftool is None:
        raise RuntimeError("Exiftool was not found on this system. "
                           "You should install the tool from here: https://exiftool.org/")
    else:
        app.logger.debug(f"Exiftool installed at {exiftool}")


class ExifInfoFormat(Enum):
    HTML = "-h"
    JSON = "-j"
    PHP = "-php"
    XML = "-X"
    TREE = "-j"


class ExifInfo:
    def __init__(self, file, fmt: ExifInfoFormat = ExifInfoFormat.JSON):
        super().__init__()
        test_exiftool()
        self._file = file
        self._format = fmt
        self._raw_data = self._get_exif_data(file)
        self._data = json.loads(self._raw_data)

    @property
    def file(self):
        return self._file

    @property
    def format(self):
        return self._format

    @property
    def raw_data(self):
        return self._raw_data

    @property
    def data(self):
        return self._data

    def _get_exif_data(self, file: str):
        # Check if file exists
        if not os.path.exists(file):
            raise ValueError(f"{file} does not exist. Unable to proceed")

        cmd = self._create_command(file, self._format)
        app.logger.info(f"Exiftool to run with the command: {cmd}")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        app.logger.debug(f"Exiftool command completed. Check returned data")
        proc.check_returncode()
        return proc.stdout

    @staticmethod
    def _create_command(file: str, _format: ExifInfoFormat):
        """
        Creates the exiftool command to run
        :param file: the file to query
        :param _format: the output Format
        :return: the command to execute
        """
        # Create the command
        cmd = [EXIFTOOL_APP, file]
        # Format
        cmd.append(_format.value)
        # Grouping
        cmd.append("-g")
        # Structured
        cmd.append("-struct")
        return cmd
