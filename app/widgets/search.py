from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer
from PyQt6.QtGui import QIcon, QTextCursor, QFontDatabase
from PyQt6.QtWidgets import QTextEdit, QPushButton, QDialogButtonBox, \
    QDockWidget, QCompleter, QLineEdit

import app
from app.database.ds import Database, HasDatabaseDisplaySupport
from app.widgets.windowinfo import WindowInfo


class AutoCompletionTextEdit(QTextEdit):
    # https://doc.qt.io/qt-6/qtwidgets-tools-customcompleter-example.html

    def __init__(self, parent):
        super().__init__(parent=parent)
        self._completer = None
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))

    def set_completer(self, _completer):
        if self._completer:
            self._completer.disconnect(self)
        if not _completer:
            self._completer = None
            return

        _completer.setWidget(self)
        _completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        _completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer = _completer
        self._completer.activated.connect(self.insert_completion)

    def remove_completer(self):
        self._completer = None

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


class FindWidget(QDockWidget, WindowInfo):

    find_event = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setWindowTitle("Find")
        self._find_text = QLineEdit(self)
        self._find_text.setPlaceholderText("Find: Enter your text here")
        self._find_text.installEventFilter(self)
        self._find_text.textChanged.connect(self._text_changed)
        self._find_text.setStyleSheet("padding: 3px")

        self._backoff_timer = QTimer()
        self._backoff_timer.setSingleShot(True)
        self._backoff_timer.timeout.connect(self.trigger_find_request)

        self.setTitleBarWidget(self._find_text)

    @property
    def statustip(self) -> str:
        return "Find items in the current view"

    @property
    def icon(self) -> QIcon:
        return QIcon.fromTheme("folder-saved-search")

    @property
    def shortcut(self) -> str:
        return "Ctrl+F"

    def _text_changed(self):
        # Backoff triggering any events for 500ms after the user started typing
        self._backoff_timer.start(500)

    def trigger_find_request(self):
        self.find_event.emit(self._find_text.text())

    def eventFilter(self, source, event):
        if source is self._find_text:
            if event.type() == QEvent.Type.Show:
                self._find_text.setFocus()
            elif event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
                self._find_text.clear()
                self.setVisible(False)
        return super().eventFilter(source, event)


class QueryWidget(QDockWidget, WindowInfo, HasDatabaseDisplaySupport):

    query_event = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent=parent)
        self._query_text = AutoCompletionTextEdit(parent=self)
        self._exec_buttons = QDialogButtonBox(Qt.Orientation.Horizontal, self)
        self._run_button = QPushButton(parent=self, text="Run", icon=QIcon.fromTheme("media-playback-start"))
        self._init_ui()
        self.shut_database()

    def _init_ui(self):
        self.setWindowTitle("SQL Search")
        self._run_button.setShortcut("F9")

        self._exec_buttons.addButton(QDialogButtonBox.StandardButton.Reset)
        self._exec_buttons.addButton(self._run_button, QDialogButtonBox.ButtonRole.AcceptRole)
        self._exec_buttons.clicked.connect(self._clicked)
        self._query_text.setPlaceholderText("Search this database using SQL statements\n"
                                            "Ex: Select * from database where 1=1")
        self.setTitleBarWidget(self._exec_buttons)
        self.setWidget(self._query_text)

    @property
    def statustip(self) -> str:
        return "Search this database using SQL statements"

    @property
    def icon(self) -> QIcon:
        return QIcon.fromTheme("folder-saved-search")

    @property
    def shortcut(self) -> str:
        return "F3"

    @property
    def query(self):
        return self._query_text.toPlainText()

    def show_database(self, database: Database):
        self._query_text.clear()
        completer = QCompleter(database.tags, self)
        self._query_text.set_completer(completer)

    def shut_database(self):
        self._query_text.clear()
        self._query_text.remove_completer()

    def hasFocus(self):
        self._query_text.setFocus()

    def _clicked(self, btn):
        if btn == self._run_button:
            text = self._query_text.toPlainText()
            if text != "":
                self.query_event.emit(text)
            else:
                app.logger.error("Invalid query will not be sent to the database")
        elif btn.text() == QDialogButtonBox.StandardButton.Reset.name:
            self._query_text.clear()
        else:
            app.logger.warning(f"Unknown Action {btn.text()}")

#
# if __name__ == '__main__':
#     app = QApplication([])
#     ex = QueryWidget(parent=None)
#     # db = Database.open_db("/mnt/documents/dev/testing/07-24-Test-Images/")
#     # ex.show_database(db)
#     # ex.addItems(["a", "b", "c", "d"])
#     # lay = QVBoxLayout()
#     # for j in range(8):
#     #     label = QLabel("This is label # {}".format(j))
#     #     label.setAlignment(Qt.AlignCenter)
#     #     lay.addWidget(label)
#     # w = QWidget()
#     # w.setLayout(lay)
#     # ex.set_content_widget(w)
#     ex.show()
#     sys.exit(app.exec())
