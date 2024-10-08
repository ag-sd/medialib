import unittest
from unittest import skip

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QDialogButtonBox

from app.plugins.search import QueryWidget


class QueryWidgetTester(unittest.TestCase):

    def setUp(self):
        self._callback_called = False
        self._query_widget = QueryWidget(None)

    def test_statustip(self):
        self.assertEqual(self._query_widget.statustip, "Search this collection using SQL statements")

    def test_icon(self):
        self.assertEqual(self._query_widget.icon.name(), "folder-saved-search")

    def test_shortcut(self):
        self.assertEqual(self._query_widget.shortcut, "F3")

    def test_dockwidget_area(self):
        self.assertEqual(self._query_widget.dockwidget_area, Qt.DockWidgetArea.BottomDockWidgetArea)

    def test_name(self):
        self.assertEqual(self._query_widget.name, "Collection Search")

    def test_is_visible_on_start(self):
        self.assertEqual(self._query_widget.is_visible_on_start, False)

    def test_query_event_not_raised_if_text_is_empty(self):
        def callback(_):
            self._callback_called = True
            self.fail("This call should not be made because there is no text in the search box")

        self._query_widget.query_event.connect(callback)
        self._query_widget._toolbar_button_clicked("Run")
        self.assertFalse(self._callback_called, "Callback event shouldnt be called")

    def test_query_event_fired_when_valid_text_present(self):
        test_text = "Foo_BAR baz"

        def callback(cb):
            self._callback_called = True
            self.assertEqual(cb, test_text)

        self._query_widget.query_event.connect(callback)
        self._query_widget._query_text.setPlainText(test_text)
        self._query_widget._toolbar_button_clicked("Run")
        self.assertTrue(self._callback_called, "Callback event wasn't received")

    def test_reset_event(self):
        test_text = "Foo_BAR baz"

        def callback(_):
            self._callback_called = True
            self.fail("This call should not be made because there is no text in the search box")

        self._query_widget._query_text.setPlainText(test_text)
        self._query_widget.query_event.connect(callback)
        self._query_widget._toolbar_button_clicked("Clear")
        self.assertEqual(self._query_widget._query_text.toPlainText(), "")

    def test_text_retrieval(self):
        test_text = "Foo_BAR baz"
        self._query_widget._query_text.setPlainText(test_text)
        self.assertEqual(self._query_widget.query, test_text)



