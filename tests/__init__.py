# coverage run -m unittest discover -s /mnt/dev/medialib/tests/database && coverage html
# If pytest is installed:  coverage run -m pytest && coverage html
import sys

from PyQt6.QtWidgets import QApplication

# App instance required for unit testing. Only one app instance should be running!
test_app = QApplication(sys.argv)
