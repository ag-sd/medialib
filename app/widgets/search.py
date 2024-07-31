import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QTextCursor
from PyQt6.QtWidgets import QApplication, QTextEdit, QHBoxLayout, QVBoxLayout, QPushButton, QDialogButtonBox, \
    QDockWidget, QWidget, QCheckBox, QCompleter, QLineEdit

from app.database.ds import Database, HasDatabaseDisplaySupport
from app.widgets.windowinfo import WindowInfo


class AutoCompletionTextEdit(QTextEdit):

    def __init__(self, parent):
        super().__init__(parent=parent)
        self._completer = None

    def set_completer(self, _completer):
        if self._completer:
            self._completer.disconnect(self)
        if not _completer:
            return

        _completer.setWidget(self)
        _completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        _completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer = _completer
        self._completer.activated.connect(self.insert_completion)

    def insert_completion(self, completion):
        tc = self.textCursor()
        extra = len(completion) - len(self._completer.completionPrefix())
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)

    def text_under_cursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        return tc.selectedText()

    def focusInEvent(self, event):
        if self._completer:
            self._completer.setWidget(self)
        super().focusInEvent(event)

    def keyPressEvent(self, event):
        if self._completer and self._completer.popup() and self._completer.popup().isVisible():
            match event.key():
                case Qt.Key.Key_Enter | Qt.Key.Key_Return | Qt.Key.Key_Escape | Qt.Key.Key_Tab | Qt.Key.Key_Backtab:
                    event.ignore()
                    return

        is_shortcut = event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Space
        is_inline = event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Enter

        if is_inline:
            # set completion mode as inline
            self._completer.setCompletionMode(QCompleter.CompletionMode.InlineCompletion)
            completion_prefix = self.text_under_cursor()
            if completion_prefix != self._completer.completionPrefix():
                self._completer.setCompletionPrefix(completion_prefix)
            self._completer.complete()
            # set the current suggestion in the text box
            self._completer.insertText.emit(self._completer.currentCompletion())
            # reset the completion mode
            self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            return

        if not self._completer or not is_shortcut:
            super().keyPressEvent(event)

        ctrl_or_shift = event.modifiers() in (Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.ShiftModifier)
        if not self._completer or (ctrl_or_shift and event.text() == ""):
            #  ctrl or shift key on its own
            return

        if not is_shortcut and self._completer.popup():
            self._completer.popup().hide()
            return

        completion_prefix = self.text_under_cursor()
        self._completer.setCompletionPrefix(completion_prefix)
        popup = self._completer.popup()
        popup.setCurrentIndex(self._completer.completionModel().index(0, 0))
        cr = self.cursorRect()
        cr.setWidth(self._completer.popup().sizeHintForColumn(0) +
                    self._completer.popup().verticalScrollBar().sizeHint().width())
        self._completer.complete(cr)


class QueryWindow(QDockWidget, WindowInfo, HasDatabaseDisplaySupport):
    _DB_LABEL_TEXT = "FROM DATABASE {} WHERE"

    def __init__(self, parent):
        super().__init__(parent=parent)
        self._query_text = AutoCompletionTextEdit(parent=self)
        self.run_button = QPushButton(parent=self, text="Run", icon=QIcon.fromTheme("media-playback-start"))
        self._search_text = QLineEdit(self)
        self._search_mode = QCheckBox(self)
        self._layout = QVBoxLayout()
        self._advanced_search = QWidget(self)

        self._init_ui()
        self.shut_database()

    def _init_ui(self):

        self.run_button.setShortcut("F9")
        exec_buttons = QDialogButtonBox(Qt.Orientation.Horizontal, self)
        exec_buttons.addButton(QDialogButtonBox.StandardButton.Reset)
        exec_buttons.addButton(self.run_button, QDialogButtonBox.ButtonRole.AcceptRole)
        exec_buttons.clicked.connect(self._clicked)

        self._search_mode.setText("Advanced Search")
        self._search_mode.clicked.connect(self._search_mode_changed)

        adv_layout = QVBoxLayout()
        adv_layout.setContentsMargins(2, 2, 2, 2)
        adv_layout.addWidget(self._query_text)
        adv_layout.addWidget(exec_buttons)
        self._advanced_search.setLayout(adv_layout)

        self._layout.addWidget(self._search_text)

        layout = QHBoxLayout()
        layout.addWidget(self._search_mode)
        layout.addLayout(self._layout)
        layout_container = QWidget()
        layout_container.setLayout(layout)
        self.setWidget(layout_container)

    @property
    def statustip(self):
        return "Search the database using SQL statements"

    @property
    def icon(self):
        return QIcon.fromTheme("folder-saved-search")

    @property
    def shortcut(self):
        return "F3"

    def _search_mode_changed(self):
        if self._search_mode.isChecked():
            self._layout.replaceWidget(self._search_text, self._advanced_search)
        else:
            self._layout.replaceWidget(self._advanced_search, self._search_text)

    def show_database(self, database: Database):
        self.setWindowTitle(f"Search : {database.name}")
        self._search_text.clear()
        self._query_text.clear()

    def shut_database(self):
        self.setWindowTitle("Search")
        self._search_text.clear()
        self._query_text.clear()

    def _clicked(self, btn):
        print(btn == self.run_button)
        if btn == self.run_button:
            print("Will validate and run query")
        elif btn.text() == QDialogButtonBox.StandardButton.Reset.name:
            self._query_text.clear()
            for action in self._field_menu.actions():
                if action.isChecked():
                    action.setChecked(False)
        else:
            print("Unknown Action")

    def _process_menu_selections(self):
        selected = []
        for item in self._field_menu.actions():
            if item.isChecked():
                selected.append(item.text())
        if len(selected) == len(self._field_menu.actions()):
            text = "*"
        else:
            text = ", ".join(selected)

        self._field_selector.setText(text)


if __name__ == '__main__':
    app = QApplication([])
    ex = QueryWindow(parent=None)
    db = Database.open_db("/mnt/documents/dev/testing/07-24-Test-Images/")
    ex.show_database(db)
    # ex.addItems(["a", "b", "c", "d"])
    # lay = QVBoxLayout()
    # for j in range(8):
    #     label = QLabel("This is label # {}".format(j))
    #     label.setAlignment(Qt.AlignCenter)
    #     lay.addWidget(label)
    # w = QWidget()
    # w.setLayout(lay)
    # ex.set_content_widget(w)
    ex.show()
    sys.exit(app.exec())
