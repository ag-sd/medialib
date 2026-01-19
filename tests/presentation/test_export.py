import tempfile
import unittest
from pathlib import Path

from PyQt6.QtCore import Qt, QSortFilterProxyModel

from app.presentation.export import ExportFormat, from_model, from_data
from app.presentation.models import ViewItem, TableModel


class TestExportFormat(unittest.TestCase):
    """Unit tests for ExportFormat enum - no file I/O needed."""

    def test_csv_properties(self):
        fmt = ExportFormat.CSV
        self.assertEqual("csv", fmt.value)
        self.assertEqual("wb", fmt.file_mode)
        self.assertEqual("csv", fmt.extension)
        self.assertEqual("Comma Separated file (*.csv)", fmt.filter)

    def test_xlsx_properties(self):
        fmt = ExportFormat.XLSX
        self.assertEqual("xlsx", fmt.value)
        self.assertEqual("wb", fmt.file_mode)
        self.assertEqual("xlsx", fmt.extension)
        self.assertEqual("Microsoft Excel spreadsheet (*.xlsx)", fmt.filter)

    def test_json_properties(self):
        fmt = ExportFormat.JSON
        self.assertEqual("json", fmt.value)
        self.assertEqual("w", fmt.file_mode)  # text mode, not binary
        self.assertEqual("json", fmt.extension)

    def test_from_filter_valid(self):
        result = ExportFormat.from_filter("Comma Separated file (*.csv)")
        self.assertEqual(ExportFormat.CSV, result)

    def test_from_filter_xlsx(self):
        result = ExportFormat.from_filter("Microsoft Excel spreadsheet (*.xlsx)")
        self.assertEqual(ExportFormat.XLSX, result)

    def test_from_filter_invalid_returns_none(self):
        result = ExportFormat.from_filter("Unknown format (*.xyz)")
        self.assertIsNone(result)

    def test_from_filter_empty_returns_none(self):
        result = ExportFormat.from_filter("")
        self.assertIsNone(result)

    def test_available_formats_contains_all_formats(self):
        available = ExportFormat.available_formats()
        for fmt in ExportFormat:
            self.assertIn(fmt.filter, available)

    def test_available_formats_separator(self):
        available = ExportFormat.available_formats()
        # Should be separated by ;;
        self.assertIn(";;", available)
        parts = available.split(";;")
        self.assertEqual(len(list(ExportFormat)), len(parts))

    def test_all_formats_have_required_properties(self):
        """Ensure all formats have valid properties defined."""
        for fmt in ExportFormat:
            self.assertIsNotNone(fmt.value)
            self.assertIsNotNone(fmt.file_mode)
            self.assertIsNotNone(fmt.extension)
            self.assertIsNotNone(fmt.filter)
            self.assertIn(fmt.file_mode, ["w", "wb"])


class TestFromModel(unittest.TestCase):
    """Integration tests for from_model function."""

    def setUp(self):
        """Create test data for export tests."""
        self._fields = ["Name", "Size", "Type"]
        self._items = [
            ViewItem(icon=None, parent=None, data={"Name": "file1.txt", "Size": "100", "Type": "text"}),
            ViewItem(icon=None, parent=None, data={"Name": "file2.jpg", "Size": "2000", "Type": "image"}),
            ViewItem(icon=None, parent=None, data={"Name": "file3.mp3", "Size": "5000", "Type": "audio"}),
        ]

    def _create_proxy_model(self):
        """Helper to create a proxy model from test items."""
        model = TableModel(self._items, self._fields)
        proxy = QSortFilterProxyModel()
        proxy.setSourceModel(model)
        return proxy

    def test_export_to_csv(self):
        """Test exporting to CSV format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_file = Path(tmpdir) / "test_export.csv"
            proxy_model = self._create_proxy_model()

            from_model(str(export_file), proxy_model, ExportFormat.CSV)

            self.assertTrue(export_file.exists())
            content = export_file.read_bytes()
            self.assertGreater(len(content), 0)
            # CSV should contain our field names
            content_str = content.decode('utf-8')
            self.assertIn("Name", content_str)
            self.assertIn("file1.txt", content_str)

    def test_export_to_json(self):
        """Test exporting to JSON format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_file = Path(tmpdir) / "test_export.json"
            proxy_model = self._create_proxy_model()

            from_model(str(export_file), proxy_model, ExportFormat.JSON)

            self.assertTrue(export_file.exists())
            content = export_file.read_text()
            self.assertIn("file1.txt", content)
            self.assertIn("file2.jpg", content)

    def test_export_to_html(self):
        """Test exporting to HTML format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_file = Path(tmpdir) / "test_export.html"
            proxy_model = self._create_proxy_model()

            from_model(str(export_file), proxy_model, ExportFormat.HTML)

            self.assertTrue(export_file.exists())
            content = export_file.read_text()
            # HTML should have table structure
            self.assertIn("<table>", content.lower())
            self.assertIn("file1.txt", content)

    def test_export_empty_model(self):
        """Test exporting an empty model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_file = Path(tmpdir) / "test_empty.csv"
            model = TableModel([], self._fields)
            proxy = QSortFilterProxyModel()
            proxy.setSourceModel(model)

            from_model(str(export_file), proxy, ExportFormat.CSV)

            self.assertTrue(export_file.exists())

    def test_export_preserves_row_count(self):
        """Test that export includes all rows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_file = Path(tmpdir) / "test_count.json"
            proxy_model = self._create_proxy_model()

            from_model(str(export_file), proxy_model, ExportFormat.JSON)

            content = export_file.read_text()
            # Should contain all three items
            self.assertIn("file1.txt", content)
            self.assertIn("file2.jpg", content)
            self.assertIn("file3.mp3", content)


class TestFromData(unittest.TestCase):
    """Integration tests for from_data function."""

    def setUp(self):
        """Create test data."""
        self._fields = ["Name", "Size", "Type"]
        self._items = [
            ViewItem(icon=None, parent=None, data={"Name": "alpha.txt", "Size": "100", "Type": "text"}),
            ViewItem(icon=None, parent=None, data={"Name": "beta.jpg", "Size": "2000", "Type": "image"}),
            ViewItem(icon=None, parent=None, data={"Name": "gamma.mp3", "Size": "5000", "Type": "audio"}),
        ]

    def test_from_data_basic_export(self):
        """Test basic export through from_data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_file = Path(tmpdir) / "test_data.csv"

            from_data(
                str(export_file),
                self._items,
                self._fields,
                search_text="",
                sort_column=0,
                sort_order=Qt.SortOrder.AscendingOrder,
                export_format=ExportFormat.CSV
            )

            self.assertTrue(export_file.exists())
            content = export_file.read_bytes().decode('utf-8')
            self.assertIn("alpha.txt", content)

    def test_from_data_with_sorting(self):
        """Test that sorting is applied during export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_file = Path(tmpdir) / "test_sorted.json"

            # Sort by Name descending - gamma should come first
            from_data(
                str(export_file),
                self._items,
                self._fields,
                search_text="",
                sort_column=0,
                sort_order=Qt.SortOrder.DescendingOrder,
                export_format=ExportFormat.JSON
            )

            self.assertTrue(export_file.exists())
            content = export_file.read_text()
            # In descending order, gamma should appear before alpha
            gamma_pos = content.find("gamma")
            alpha_pos = content.find("alpha")
            self.assertLess(gamma_pos, alpha_pos)

    def test_from_data_with_filter(self):
        """Test that search filter is applied during export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_file = Path(tmpdir) / "test_filtered.json"

            # Filter to only include "alpha"
            from_data(
                str(export_file),
                self._items,
                self._fields,
                search_text="alpha",
                sort_column=0,
                sort_order=Qt.SortOrder.AscendingOrder,
                export_format=ExportFormat.JSON
            )

            self.assertTrue(export_file.exists())
            content = export_file.read_text()
            self.assertIn("alpha", content)
            # beta and gamma should be filtered out
            self.assertNotIn("beta", content)
            self.assertNotIn("gamma", content)


if __name__ == '__main__':
    unittest.main()
