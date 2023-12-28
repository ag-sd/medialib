from pathlib import Path

from PyQt6.QtCore import QDir, Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget, QHBoxLayout, QVBoxLayout, QLabel

import app


def show_exception(parent, exception: Exception):
    app.logger.exception(exception)
    QMessageBox.critical(parent, "An Error Occurred", str(exception))


def get_new_paths(parent, is_dir=False, file_filter=None) -> list:
    """
    Sets up a File-Chooser and allows the user to select a file or directory.
    :param parent: The parent who needs this modal
    :param is_dir: whether to allow the user to only choose files or dirs
    :param file_filter: The file filter to use
    :return: Returns a list of files, or a single directory
    """
    files = []
    if is_dir:
        path = QFileDialog.getExistingDirectory(parent, "Select Directory", str(Path.home()),
                                                QFileDialog.Option.DontUseCustomDirectoryIcons |
                                                QFileDialog.Option.ShowDirsOnly)
        if path != "":
            files.append(QDir.toNativeSeparators(path))
    else:
        if file_filter is not None:
            app.logger.debug(f"Filtering for files that match the following extensions {file_filter}")
            resp = QFileDialog.getOpenFileNames(parent, "Select Files", str(Path.home()), filter=file_filter,
                                                options=QFileDialog.Option.DontUseCustomDirectoryIcons)
        else:
            resp = QFileDialog.getOpenFileNames(parent, "Select Files", str(Path.home()),
                                                options=QFileDialog.Option.DontUseCustomDirectoryIcons)
        if len(resp[0]) > 0:
            for file in resp[0]:
                files.append(QDir.toNativeSeparators(file))
    return files
