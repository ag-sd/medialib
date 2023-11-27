import os.path
import shutil
import subprocess
from enum import Enum

import app

# https://exiftool.org/exiftool_pod.html#Input-output-text-formatting
EXIFTOOL_APP = "exiftool"


def test_exiftool():
    exiftool = shutil.which(EXIFTOOL_APP)
    if exiftool is None:
        raise RuntimeError("Exiftool was not found on this system. "
                           "You should install the tool from here: https://exiftool.org/")


# Get supported formats
test_exiftool()
listf_proc = subprocess.run([EXIFTOOL_APP, "-listf"], capture_output=True, text=True)
listf_proc.check_returncode()
SUPPORTED_FORMATS = listf_proc.stdout.split(":")[1].replace("\n", '').replace("  ", ' ').strip().upper()


def is_supported(file: str) -> bool:
    """
    Checks the input file to determine if exiftool supports it
    :param file: The file to test
    :return: true if the file is supported, false otherwise
    """
    _, ext = os.path.splitext(file)
    return SUPPORTED_FORMATS.find(ext[1:].upper()) >= 0


class ExifInfoFormat(Enum):
    HTML = "htm", ["-h", "-g", "-struct"]
    JSON = "json", ["-j", "-g", "-struct"]
    PHP = "php", ["-php", "-g", "-struct"]
    XML = "xml", ["-X", "-g", "-struct"]
    CSV = "csv", ["-j", "-G1"]

    def __init__(self, _, args: list):
        self._args = args

    @property
    def args(self):
        return self._args


class ExifInfo:
    def __init__(self, file, fmt: ExifInfoFormat = ExifInfoFormat.JSON):
        super().__init__()
        test_exiftool()
        self._file = file
        self._format = fmt
        self._cmd = self._create_command(file, fmt)
        self._data = self._get_exif_data(file, self._cmd)

    @property
    def file(self):
        return self._file

    @property
    def format(self):
        return self._format

    @property
    def data(self):
        return self._data

    @property
    def command(self):
        return self._cmd

    @staticmethod
    def _get_exif_data(file: str, cmd: list):
        # Check if file is supported
        if not is_supported(file):
            raise ValueError(f"{file} is not in the list of supported formats.\n{SUPPORTED_FORMATS}")

        # Check if file exists
        if not os.path.exists(file):
            raise ValueError(f"{file} does not exist. Unable to proceed")

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
        cmd.extend(_format.args)

        return cmd
