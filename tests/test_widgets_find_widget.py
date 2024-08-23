import unittest

from app.plugins.search import FindWidget


class FindWidgetTester(unittest.TestCase):

    def setUp(self):
        self._find_widget = FindWidget(None)

    def test_statustip(self):
        self.assertEqual(self._find_widget.statustip, "Find items in the current view")

    def test_icon(self):
        self.assertEqual(self._find_widget.icon.name(), "folder-saved-search")

    def test_shortcut(self):
        self.assertEqual(self._find_widget.shortcut, "Ctrl+F")

    def test_query(self):
        test_text = "Foo_BAR baz"

        def callback(text):
            self.assertEqual(text, test_text)

        self._find_widget.find_event.connect(callback)
        self._find_widget._find_text.setText(test_text)


