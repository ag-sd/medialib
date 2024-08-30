import re

from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer
from PyQt6.QtGui import QIcon, QTextCursor, QFontDatabase, QSyntaxHighlighter, QTextCharFormat, QFont
from PyQt6.QtWidgets import QDialogButtonBox, \
    QDockWidget, QCompleter, QLineEdit, QPlainTextEdit

import app
from app.collection.ds import Collection, HasCollectionDisplaySupport
from app.plugins.framework import WindowInfo, SearchEventHandler, PluginToolBar


# https://panthema.net/2006/qtsqlview/src/QtSqlView-0.8.0/src/SQLHighlighter.cpp.html
#
# https://doc.qt.io/qtforpython-6/examples/example_widgets_richtext_syntaxhighlighter.html
#
# https://stackoverflow.com/questions/52765697/qregexp-and-single-quoted-text-for-qsyntaxhighlighter
#
# https://wiki.python.org/moin/PyQt/Python%20syntax%20highlighting

def get_context_aware_completer(collection: Collection = None):
    keywords = sorted(SQLHighlighter.ALL_KEYWORDS + collection.tags if collection is not None else [])
    _completer = QCompleter(keywords, None)
    sys_monospace_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()
    _completer.popup().setStyleSheet(f"font-family: '{sys_monospace_font}', monospace;")
    return _completer


class SQLHighlighter(QSyntaxHighlighter):
    _KEYWORD_GROUPS = [
        # Most used
        ["SELECT", "DISTINCT", "FROM", "WHERE", "GROUP", "BY", "HAVING", "ORDER", "LIMIT", "IS", "BETWEEN", "LIKE",
         "ILIKE", "ELSE", "END", "CASE", "WHEN", "THEN", "EXISTS", "IN", "AVG", "SUM"],
        # Less used
        ["UNION", "ALL", "AND", "INTERSECT", "EXCEPT", "COLLATE", "ASC", "DESC", "ON", "USING", "NATURAL", "INNER",
         "CROSS", "LEFT", "OUTER", "JOIN", "NOTNULL", "NULL", ],
        # Even lesser used
        ["CURRENT_TIME", "CURRENT_DATE", "CURRENT_TIMESTAMP", "TRUE", "FALSE", "ANY", "SOME", "WITH", "AS", ],
        ["INDEXED", "NOT", "OFFSET", "OR", "CAST", "ISNULL", "GLOB", "REGEXP", "MATCH", "ESCAPE"]
    ]

    ALL_KEYWORDS = sum(_KEYWORD_GROUPS, [])

    _SQL_OPERATORS = [
        "--[+\\-*/]",
        "--[<>=!]"
    ]

    _BRACES = ["--[()[\\]{}]", ]

    def __init__(self, parent):
        super().__init__(parent)
        self._rule_map = {}
        self._create_rule(SQLHighlighter._KEYWORD_GROUPS, weight=QFont.Weight.Bold, foreground=Qt.GlobalColor.blue)
        self._create_rule(SQLHighlighter._SQL_OPERATORS, weight=QFont.Weight.Bold, foreground=Qt.GlobalColor.magenta)
        self._create_rule(SQLHighlighter._BRACES, weight=QFont.Weight.Bold, foreground=Qt.GlobalColor.magenta)

    def _create_rule(self, rule_group: list, weight, foreground):
        for group in rule_group:
            if isinstance(group, list):
                rule_pattern = f"\\b({"|".join(group)})\\b"
            else:
                rule_pattern = group[2:]

            rule_format = QTextCharFormat()
            rule_format.setForeground(foreground)
            rule_format.setFontWeight(weight)
            self._rule_map[re.compile(rule_pattern, re.IGNORECASE)] = rule_format

    def highlightBlock(self, text: str):
        for pattern, _format in self._rule_map.items():
            for match in re.finditer(pattern, text):
                start, end = match.span()
                # print(f"Match found {text[start:end]}")
                self.setFormat(start, end - start, _format)

    @property
    def keywords(self):
        return sorted(self._ALL_KEYWORDS)


class AutoCompletionTextEdit(QPlainTextEdit):
    # https://doc.qt.io/qt-6/qtwidgets-tools-customcompleter-example.html
    # https://stackoverflow.com/questions/28956693/pyqt5-qtextedit-auto-completion

    def __init__(self, parent):
        super().__init__(parent=parent)
        self._completer = None
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))

    def set_completer(self, completer):
        if self._completer:
            self._completer.disconnect()

        self._completer = completer
        if not self._completer:
            return

        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.activated.connect(self.insert_completion)

    def insert_completion(self, completion):
        if self._completer.widget() != self:
            return

        tc = self.textCursor()

        # Handle case
        last_char_before_completion = tc.block().text()[-1]
        if last_char_before_completion.islower():
            completion = completion.lower()

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


class FindWidget(QDockWidget, WindowInfo, SearchEventHandler):
    find_event = pyqtSignal(str)
    do_search = pyqtSignal(str, "PyQt_PyObject")

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setWindowTitle(self.name)
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

    @property
    def dockwidget_area(self):
        return Qt.DockWidgetArea.TopDockWidgetArea

    @property
    def name(self) -> str:
        return "Find"

    def _text_changed(self):
        # Backoff triggering any events for 500ms after the user started typing
        self._backoff_timer.start(500)

    def trigger_find_request(self):
        self.find_event.emit(self._find_text.text())
        self.do_search.emit(self._find_text.text(), SearchEventHandler.SearchType.VISUAL)

    def eventFilter(self, source, event):
        if source is self._find_text:
            if event.type() == QEvent.Type.Show:
                self._find_text.setFocus()
            elif event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
                self._find_text.clear()
                self.setVisible(False)
        return super().eventFilter(source, event)


class QueryWidget(QDockWidget, WindowInfo, HasCollectionDisplaySupport, SearchEventHandler):

    query_event = pyqtSignal(str)
    do_search = pyqtSignal(str, "PyQt_PyObject")

    def __init__(self, parent):
        super().__init__(parent=parent)
        self._query_text = AutoCompletionTextEdit(parent=self)
        self._highlighter = SQLHighlighter(self._query_text.document())
        self.toolbar = PluginToolBar(self, self.name)
        self.toolbar.button_clicked.connect(self._toolbar_button_clicked)
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle(self.name)
        self._query_text.setPlaceholderText("Search this collection using SQL statements\n"
                                            "Ex: Select * from collection where 1=1")

        self.toolbar.add_button("Run", "media-playback-start", "F9")
        self.toolbar.add_button("Clear", "edit-clear")
        self.setTitleBarWidget(self.toolbar)
        self.setWidget(self._query_text)

    @property
    def statustip(self) -> str:
        return "Search this collection using SQL statements"

    @property
    def icon(self) -> QIcon:
        return QIcon.fromTheme("folder-saved-search")

    @property
    def shortcut(self) -> str:
        return "F3"

    @property
    def query(self):
        return self._query_text.toPlainText()

    @property
    def dockwidget_area(self):
        return Qt.DockWidgetArea.BottomDockWidgetArea

    @property
    def name(self) -> str:
        return "Collection Search"

    @property
    def is_visible_on_start(self) -> bool:
        return False

    def windowIcon(self) -> QIcon:
        return self.icon

    def show_collection(self, collection: Collection):
        self._query_text.clear()
        ca_completer = get_context_aware_completer(collection)
        self._query_text.set_completer(ca_completer)

    def shut_collection(self):
        self.setEnabled(False)

    def hasFocus(self):
        self._query_text.setFocus()

    def _toolbar_button_clicked(self, button_name):
        if button_name == "Run":
            text = self._query_text.toPlainText()
            if text != "":
                self.query_event.emit(text)
                self.do_search.emit(text, SearchEventHandler.SearchType.QUERY)

            else:
                app.logger.error("Invalid query will not be sent to the collection")
        elif button_name == "Clear":
            self._query_text.clear()
        else:
            app.logger.warning(f"Unknown Action {button_name}")

    def _clicked(self, btn):
        if btn == self._run_button:
            text = self._query_text.toPlainText()
            if text != "":
                self.query_event.emit(text)
                self.do_search.emit(text, SearchEventHandler.SearchType.QUERY)

            else:
                app.logger.error("Invalid query will not be sent to the collection")
        elif btn.text() == QDialogButtonBox.StandardButton.Reset.name:
            self._query_text.clear()
        else:
            app.logger.warning(f"Unknown Action {btn.text()}")

