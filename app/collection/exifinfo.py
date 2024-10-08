import os
import shutil
import subprocess
import tempfile
from enum import Enum, StrEnum
from pathlib import Path

import app
from app.collection import props

# https://exiftool.org/exiftool_pod.html#Input-output-text-formatting


def test_exiftool():
    exiftool = shutil.which(props.EXIFTOOL_APP)
    if exiftool is None:
        raise RuntimeError("Exiftool was not found on this system. "
                           "You should install the tool from here: https://exiftool.org/")


# Get supported formats
test_exiftool()
listf_proc = subprocess.run([props.EXIFTOOL_APP, "-listf"], capture_output=True, text=True)
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


class _ExifInfoFormat(Enum):
    CSV = "csv", ["-csv", "-G1", "-r", f"-csvDelim {props.EXIFTOOL_CSV_DELIMITER}"]
    JSON = "json", ["-j", "-G1", "-r"]
    XML = "xml", ["-X", "-g", "-struct", "-r"]
    HTML = "html", ["-h", "-g", "-struct", "-r"]

    def __init__(self, _, args: list):
        self._args = args

    @property
    def args(self):
        return self._args


class ExifInfoStatus(StrEnum):
    READY = "Ready"
    WORKING = "Working"
    INITIALIZED = "Initialized"


class ExifInfo:
    DATA_ENCODING = "utf-8"

    def __init__(self, file, save_file: str | None = None):
        super().__init__()
        test_exiftool()
        self._file = file
        self._format = _ExifInfoFormat.JSON
        self._cmd = self._create_command(file, _ExifInfoFormat.JSON)
        self._status = ExifInfoStatus.INITIALIZED
        self._save_file = save_file
        self._data = None
        self._tags = None
        self._capture_exif_data(file, self._cmd, self._save_file)

    @property
    def file(self):
        return self._file

    @property
    def status(self):
        return self._status

    @property
    def data(self):
        match self.status:
            case ExifInfoStatus.WORKING:
                # If service is still working, raise an error
                raise ValueError("Service is not ready to return data")
            case ExifInfoStatus.READY:
                # If service is ready to return data
                if self._save_file is not None and self._data is None:
                    # Data has to be loaded into memory from disk
                    app.logger.debug(f"Loading data from file {self._save_file}")
                    self._data = Path(self._save_file).read_text(encoding=self.DATA_ENCODING)
                return self._data
            case ExifInfoStatus.INITIALIZED:
                # First time data fetch
                self._status = self._capture_exif_data(self._file, self._cmd, self._save_file)
                # Rerun all property checks and return the data
                return self.data

    @property
    def command(self):
        return self._cmd

    def _capture_exif_data(self, file: str, cmd: list, output_file: str) -> ExifInfoStatus:
        p_file = Path(file)
        if not p_file.exists():
            raise ValueError(f"Input {file} does not exist. Unable to proceed")

        # Check if file is supported
        if p_file.is_file() and not is_supported(file):
            raise ValueError(f"Input {file} is not in the list of supported formats.\n{SUPPORTED_FORMATS}")

        app.logger.info(f"Exiftool to run with the command: {cmd}")
        self._status = ExifInfoStatus.WORKING
        if output_file is not None:
            # Make this process atomic
            p_output_file = Path(output_file)
            # Create a new output file in the same directory
            p_tmp_output_file = tempfile.NamedTemporaryFile(delete=False, dir=str(p_output_file.parent))
            # Perform operation
            self._setup_file_process(command=cmd, output_file=p_tmp_output_file.name)
            # Fsync the temp file
            os.fsync(p_tmp_output_file.fileno())
            # Rename the file
            os.rename(p_tmp_output_file.name, output_file)
            # Wait for sync
            os.system("sync")
        else:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self._data = proc.stdout

        app.logger.debug(f"Exiftool command completed.")
        self._status = ExifInfoStatus.READY
        return self._status

    @staticmethod
    def _setup_file_process(command, output_file):
        output_file_obj = Path(output_file)
        if not output_file_obj.exists():
            app.logger.debug(f"{output_file_obj} does not exist. It will be created")
        else:
            app.logger.warning(f"{output_file_obj} exists and will be overwritten")
            output_file_obj.unlink(missing_ok=False)

        # Write to output file
        app.logger.debug(f"Writing output to file {output_file}")
        with output_file_obj.open("w", encoding=ExifInfo.DATA_ENCODING) as f_out:
            proc = subprocess.run(command, stdout=f_out, text=True)
        return proc

    @staticmethod
    def _create_command(file: str, _format: _ExifInfoFormat):
        """
        Creates the exiftool command to run
        :param file: the file to query
        :param _format: the output Format
        :return: the command to execute
        """
        # TODO: Test
        # Create the command
        cmd = [props.EXIFTOOL_APP, file]
        # Format
        cmd.extend(_format.args)

        return cmd
