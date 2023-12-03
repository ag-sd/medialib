import shutil
import subprocess
import tempfile
from enum import Enum, StrEnum
from pathlib import Path

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
    ext = Path(file).suffix
    return SUPPORTED_FORMATS.find(ext[1:].upper()) >= 0


class ExifInfoFormat(Enum):
    CSV = "csv", ["-j", "-G1", "-r"]
    PHP = "php", ["-php", "-g", "-struct", "-r"]
    XML = "xml", ["-X", "-g", "-struct", "-r"]
    HTML = "html", ["-h", "-g", "-struct", "-r"]
    JSON = "json", ["-j", "-g", "-struct", "-r"]

    def __init__(self, _, args: list):
        self._args = args

    @property
    def args(self):
        return self._args


class ExifInfoStatus(StrEnum):
    READY = "Ready"
    WAITING = "Waiting"


class ExifInfo:
    DATA_ENCODING = "utf-8"

    def __init__(self, file, fmt: ExifInfoFormat = ExifInfoFormat.JSON, output_path: str | None = None):
        super().__init__()
        test_exiftool()
        self._file = file
        self._format = fmt
        self._cmd = self._create_command(file, fmt)
        if output_path is None:
            self._output_file = tempfile.NamedTemporaryFile().name
        else:
            self._output_file = output_path
        self._status = self._capture_exif_data(file, self._cmd, self._output_file)
        self._data = ""

    @property
    def file(self):
        return self._file

    @property
    def format(self):
        return self._format

    @property
    def data(self):
        if self._data == "":
            app.logger.debug(f"Loading data from file {self._output_file}")
            self._data = Path(self._output_file).read_text(encoding=self.DATA_ENCODING)
        return self._data

    @property
    def command(self):
        return self._cmd

    @property
    def output_file(self):
        return self._output_file

    @staticmethod
    def _capture_exif_data(file: str, cmd: list, output_file: str) -> ExifInfoStatus:
        p_file = Path(file)
        if not p_file.exists():
            raise ValueError(f"Input {file} does not exist. Unable to proceed")

        # Check if file is supported
        if p_file.is_file() and not is_supported(file):
            raise ValueError(f"Input {file} is not in the list of supported formats.\n{SUPPORTED_FORMATS}")

        app.logger.info(f"Exiftool to run with the command: {cmd}")

        output_file_obj = Path(output_file)
        if not output_file_obj.exists():
            app.logger.debug(f"{output_file_obj} does not exist. It will be created")
        else:
            app.logger.warning(f"{output_file_obj} exists and will be overwritten")
            output_file_obj.unlink(missing_ok=False)

        # Write to output file
        app.logger.debug(f"Writing output to file {output_file}")
        with output_file_obj.open("w", encoding=ExifInfo.DATA_ENCODING) as f_out:
            proc = subprocess.run(cmd, stdout=f_out, text=True)
            # proc.check_returncode()
        app.logger.debug(f"Exiftool command completed. Check returned data")
        return ExifInfoStatus.READY

    @staticmethod
    def _create_command(file: str, _format: ExifInfoFormat):
        """
        Creates the exiftool command to run
        :param file: the file to query
        :param _format: the output Format
        :return: the command to execute
        """
        # TODO: Test
        # Create the command
        cmd = [EXIFTOOL_APP, file]
        # Format
        cmd.extend(_format.args)

        return cmd


if __name__ == '__main__':
    print(SUPPORTED_FORMATS)
    print(" *.".join(SUPPORTED_FORMATS.split(" ")))
    print(f"ExifTool Supported Files (*.{' *.'.join(SUPPORTED_FORMATS.split(' '))})")
