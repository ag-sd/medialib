from functools import partial
from pathlib import Path

from PyQt6.QtCore import QDir, QMimeDatabase
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidgetAction

import app
from app.collection import props

_mime_database = QMimeDatabase()


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


def get_mime_type_icon_name(file: str) -> str:
    mime_type = _mime_database.mimeTypeForFile(file)
    return mime_type.iconName()


def create_action(parent, name, func=None, shortcut=None, tooltip=None, icon=None, checked=None, enabled=True,
                  widget=None):
    """
    Creates an action for use in a Toolbar or Menu
    :param parent: The actions parent
    :param name: The action name
    :param func: The function to call when this action is triggered
    :param shortcut: The keyboard shortcut for this action
    :param tooltip: The tooltip to display when this action is interacted with
    :param icon: The icon to show for this action
    :param checked: Whether the visual cue associated with this action represents a check mark
    :param enabled: Whether the action is enabled once created
    :param widget: If a widget is provided, this function will create a QWidgetAction instead of a QAction
    :return: A QAction object representing this action
    """
    # TODO: Test
    if widget is not None:
        action = QWidgetAction(parent)
    else:
        action = QAction(name, parent)

    if tooltip and shortcut:
        tooltip = f"{tooltip} ({shortcut})"
    if shortcut:
        action.setShortcut(shortcut)
    if tooltip:
        action.setToolTip(tooltip)
        action.setStatusTip(tooltip)
    if func:
        action.triggered.connect(partial(func, name))
    if icon:
        action.setIcon(QIcon.fromTheme(icon))
    if checked is not None:
        action.setCheckable(True)
        action.setChecked(checked)
    action.setEnabled(enabled)
    return action


def create_tag_groups(tags: list) -> dict:
    tag_groups = {
        props.DB_TAG_GROUP_DEFAULT: []
    }
    for key in tags:
        tokens = key.split(":")
        if len(tokens) == 1:
            tag_groups[props.DB_TAG_GROUP_DEFAULT].append(tokens[0])
        elif len(tokens) == 2:
            if tokens[0] not in tag_groups:
                tag_groups[tokens[0]] = []
            tag_groups[tokens[0]].append(tokens[1])
        else:
            app.logger.warning(f"Unhandled field {key} will not be shown in the view")
    if len(tag_groups[props.DB_TAG_GROUP_DEFAULT]) == 0:
        # Remove this group if it's not needed
        del tag_groups[props.DB_TAG_GROUP_DEFAULT]
    return tag_groups
