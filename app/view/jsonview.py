from PyQt6.QtWidgets import QTextEdit

from app.exifinfo import ExifInfo


class JsonView(QTextEdit):
    def __init__(self, exif_info: ExifInfo):
        super().__init__()
        self.setText(exif_info.raw_data)

# https://github.com/leixingyu/codeEditor/blob/master/highlighter/jsonHighlight.py
