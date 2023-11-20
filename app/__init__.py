import logging

__VERSION__ = "0.0.1"
__NAME__ = "Exiftool GUI"
__APP_NAME__ = f"{__NAME__} v{__VERSION__}"

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - '
                              '%(module)s:[%(funcName)s]:%(lineno)s - %(message)s')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger = logging.getLogger(__APP_NAME__)
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)
