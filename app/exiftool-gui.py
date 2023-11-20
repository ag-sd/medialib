import argparse
import os.path
import sys

from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QComboBox, QWidget, QApplication

import app
from app import exifinfo
from app.exifinfo import ExifInfo
from app.view.jsonview import JsonView


# Syntax Highligting: https://wiki.python.org/moin/PyQt/Python%20syntax%20highlighting
# https://joekuan.wordpress.com/2015/10/02/styling-qt-qtreeview-with-css/
class ExiftoolGUI(QMainWindow):
    def __init__(self, files: list):
        """
        :param files: The files whose information should be shown
        """
        super().__init__()
        self.current_view = QWidget()
        self.view_layout = QVBoxLayout()
        self.view_layout.addWidget(self.current_view)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self._create_file_selector(files))
        main_layout.addLayout(self.view_layout)

        main_layout.setContentsMargins(2, 2, 2, 2)

        dummy_widget = QWidget()
        dummy_widget.setLayout(main_layout)
        self.setCentralWidget(dummy_widget)
        self.setWindowTitle(app.__APP_NAME__)
        self.setMinimumWidth(768)
        self.setMinimumHeight(768)
        self.show()

    def _selection_changed(self, text):
        app.logger.debug(f"Selection changed to {text}")
        info = ExifInfo(text)  # TODO: Support format passing in here
        json_view = JsonView(info)
        self.view_layout.replaceWidget(self.current_view, json_view)
        del self.current_view
        self.current_view = json_view

    def _create_file_selector(self, files: list) -> QComboBox:
        """
        validates the input files and returns a comobobox to select the files
        :param files: to read the exifdata
        :return: a Combobox of valid files
        """

        combo = QComboBox()
        combo.setEditable(False)
        combo.currentTextChanged.connect(self._selection_changed)
        for file in files:
            if os.path.exists(file):
                combo.addItem(file)
            else:
                app.logger.error(f"{file} does not exist. Skipping this file")

        if combo.count() == 0:
            raise ValueError("No valid files were found!")

        return combo


# Test if Exiftool is installed
exifinfo.test_exiftool()

# Check for input arguments
parser = argparse.ArgumentParser(prog=app.__APP_NAME__, description="Frontend to the excellent exiftool")
parser.add_argument("files", metavar="f", type=str, nargs="*", help="file(s) to read the exif data from")
args = parser.parse_args()
app.logger.debug(f"Input args supplied {args.files}")

# Prepare and launch GUI
application = QApplication(sys.argv)
exiftoolgui = ExiftoolGUI(args.files)
sys.exit(application.exec())
