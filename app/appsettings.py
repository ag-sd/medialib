import pickle
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QSettings
from PyQt6.QtWidgets import QWidget, QCheckBox, QRadioButton, QGroupBox, QSplitter

import app


class AppSettings(QObject):
    stateful_prefix = "_stateful"
    """
    A class that can read and write application settings. The class can also fire events
    when a setting changes.
    App specific settings are stored as a dictionary that is saved as a byte stream
    This class is also capable of saving stateful UI's.
    UI settings may be partially human readable
    In order to save a UI, prefix each of its child widgets names with stateful_
    NOTE: The UI needs to have a object name if you are dealing with multiple saved UI's
    Currently supported stateful widgets are QCheckBox, QRadioButton, QGroupBox, FileChooser
    """
    settings_changed = pyqtSignal(object, object)

    def __init__(self, app_name, default_settings):
        super().__init__()
        self._app_settings = QSettings(app_name, app_name)
        self._config = self._app_settings.value("app_settings")
        if self._config is None:
            self._config = default_settings

    @property
    def config_dir(self) -> Path:
        return self.config_file.parent

    @property
    def config_file(self) -> Path:
        return Path(self._app_settings.fileName())

    def get_property(self, key, default=None):
        if self._config.__contains__(key):
            return self._config[key]
        return default

    def set_property(self, key, value):
        """
            Save an internal setting and fire an event
            :param key: the setting key
            :param value: the value to set
            :return:
        """
        self._config[key] = value
        self._app_settings.setValue("app_settings", self._config)
        self.settings_changed.emit(key, value)

    def save_ui(self, ui, logger=None, ignore_children=False):
        """
        https://stackoverflow.com/questions/23279125/python-pyqt4-functions-to-save-and-restore-ui-widget-values
        :param ignore_children: If set, the children of the UI will not be saved
        :param ui       : The QWidget to save
        :param logger   : Optional, if provided will log each save attempt of a stateful widget
        :return:
        """
        path = ui.objectName()
        self._app_settings.setValue(f"{path}/geometry", ui.saveGeometry())
        if ignore_children:
            return

        for obj in ui.findChildren(QWidget):
            name = obj.objectName()
            if name.startswith(AppSettings.stateful_prefix):
                value = None
                key = f"{path}/{name}"
                if isinstance(obj, QCheckBox):
                    value = obj.checkState()
                elif isinstance(obj, QRadioButton) or isinstance(obj, QGroupBox):
                    value = obj.isChecked()
                elif isinstance(obj, QSplitter):
                    value = obj.saveState()

                if value is not None:
                    self._app_settings.setValue(key, value)
                    if logger is not None:
                        logger.info(f"Saved {key}: {value}")
                else:
                    if logger is not None:
                        logger.debug(f"{key} could not be saved")

    def load_ui(self, ui, logger=None, ignore_children=False):
        """
        https://stackoverflow.com/questions/23279125/python-pyqt4-functions-to-save-and-restore-ui-widget-values
        :param ignore_children: If set, the children of the UI will not be loaded
        :param ui       : The QWidget to save
        :param logger   : Optional, if provided will log each load attempt of a stateful widget
        :return:
        """
        path = ui.objectName()
        geometry = self._app_settings.value(f"{path}/geometry")
        if geometry is None:
            if logger is not None:
                logger.warn(f"{path} not found in settings")
            return False
        else:
            ui.restoreGeometry(self._app_settings.value(f"{path}/geometry"))
        if ignore_children:
            return True

        for obj in ui.findChildren(QWidget):
            name = obj.objectName()
            if name.startswith(AppSettings.stateful_prefix):
                key = f"{path}/{name}"
                value = self._app_settings.value(key)
                if logger is not None:
                    logger.info(f"Loaded {key}: {value}")
                if value is None:
                    continue
                if isinstance(obj, QCheckBox):
                    obj.setChecked(value)
                elif isinstance(obj, QRadioButton) or isinstance(obj, QGroupBox):
                    obj.setChecked(bool(value))
                elif isinstance(obj, QSplitter):
                    obj.restoreState(value)
        return True


_settings = AppSettings(app.__APP_NAME__, {})


def get_config_dir() -> Path:
    return Path(_settings.config_dir)


def set_db_paths(db_paths: list):
    items_pickle = pickle.dumps(db_paths)
    _settings.apply_setting("db_paths", items_pickle)


def get_db_paths() -> list:
    items_pickle = _settings.get_property("db_paths")
    if items_pickle:
        return pickle.loads(items_pickle)
    return []


def get_registry_db() -> Path:
    return get_config_dir() / "dbregistry.ini"
