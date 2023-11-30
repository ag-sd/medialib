import logging

# python3 -m app.exiftool-gui "/home/sheldon/Downloads/20170812 Edward Dye 340.jpg"
__VERSION__ = "0.0.5"
__NAME__ = "MediaLib"
__APP_NAME__ = f"{__NAME__} v{__VERSION__}"
__APP_URL__ = "https://github.com/ag-sd/medialib"

from pathlib import Path

from PyQt6.QtGui import QIcon

# Set Fallback Theme
QIcon.setFallbackSearchPaths([str(Path(__file__).parent / "resources" / "icon_theme")])

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - '
                              '%(module)s:[%(funcName)s]:%(lineno)s - %(message)s')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger = logging.getLogger(__APP_NAME__)
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)
