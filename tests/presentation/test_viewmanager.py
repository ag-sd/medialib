import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt

from app.actions import ViewContextMenuAction
from app.presentation.export import ExportFormat
from app.presentation.models import ViewItem, ModelData, BaseViewBuilder
from app.presentation.viewmanager import ViewManager
from tests.collection import test_utils


class TestViewManagerExportSignal(unittest.TestCase):
    """Tests for ViewManager.export_requested signal."""

    def setUp(self):
        self._view_manager = ViewManager(None)

    def tearDown(self):
        self._view_manager.deleteLater()

    def test_export_requested_signal_exists(self):
        """Verify export_requested signal is defined."""
        self.assertTrue(hasattr(self._view_manager, 'export_requested'))

    def test_export_requested_signal_emission(self):
        """Test that export_requested signal is emitted on EXPORT action."""
        callback = test_utils.CallbackHandler(
            self._view_manager.export_requested,
            expects_callback=True,
            callback_count=1
        )

        # Simulate the context menu event for EXPORT action
        self._view_manager._context_menu_requested_event(
            ViewContextMenuAction.EXPORT,
            None
        )

        self.assertTrue(callback.callback_handled_correctly)

    def test_export_requested_not_emitted_on_other_actions(self):
        """Test that export_requested is NOT emitted for non-export actions."""
        callback = test_utils.CallbackHandler(
            self._view_manager.export_requested,
            expects_callback=False,
            callback_count=0
        )

        # These actions should NOT trigger export_requested
        # Note: These may trigger other side effects, but not the export signal
        # We're just checking the signal is not emitted

        # COLUMN action - should not emit export_requested
        self._view_manager._context_menu_requested_event(
            ViewContextMenuAction.COLUMN,
            ["Field1", "Field2"]
        )

        self.assertTrue(callback.callback_handled_correctly)


class TestViewManagerSaveData(unittest.TestCase):
    """Tests for ViewManager.save_data() method."""

    def setUp(self):
        self._view_manager = ViewManager(None)
        # Load some test data into the view manager
        self._setup_test_data()

    def tearDown(self):
        self._view_manager.deleteLater()

    def _setup_test_data(self):
        """Load test data into the view manager."""
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            model_data = []
            for path in db.paths:
                for _path, entry in db.data([path]).items():
                    model_data.append(ModelData(data=entry, path=_path))

            # Show data in view manager (this sets up _base_view and _current_view)
            if len(model_data) > 0:
                self._view_manager.show_data(model_data, list(db.tags))

    def test_save_data_method_exists(self):
        """Verify save_data method is defined."""
        self.assertTrue(hasattr(self._view_manager, 'save_data'))
        self.assertTrue(callable(self._view_manager.save_data))

    def test_save_data_creates_file(self):
        """Test that save_data creates an export file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_file = Path(tmpdir) / "test_export.csv"

            self._view_manager.save_data(
                _format=ExportFormat.CSV,
                export_file=str(export_file)
            )

            self.assertTrue(export_file.exists())

    def test_save_data_csv_format(self):
        """Test save_data with CSV format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_file = Path(tmpdir) / "test_export.csv"

            self._view_manager.save_data(
                _format=ExportFormat.CSV,
                export_file=str(export_file)
            )

            self.assertTrue(export_file.exists())
            content = export_file.read_bytes()
            self.assertGreater(len(content), 0)

    def test_save_data_json_format(self):
        """Test save_data with JSON format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_file = Path(tmpdir) / "test_export.json"

            self._view_manager.save_data(
                _format=ExportFormat.JSON,
                export_file=str(export_file)
            )

            self.assertTrue(export_file.exists())
            content = export_file.read_text()
            self.assertGreater(len(content), 0)

    def test_save_data_xlsx_format(self):
        """Test save_data with XLSX format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_file = Path(tmpdir) / "test_export.xlsx"

            self._view_manager.save_data(
                _format=ExportFormat.XLSX,
                export_file=str(export_file)
            )

            self.assertTrue(export_file.exists())
            # XLSX is binary, just check it has content
            content = export_file.read_bytes()
            self.assertGreater(len(content), 0)


class TestViewManagerExportIntegration(unittest.TestCase):
    """Integration tests for the complete export flow in ViewManager."""

    def setUp(self):
        self._view_manager = ViewManager(None)

    def tearDown(self):
        self._view_manager.deleteLater()

    def test_export_with_table_view(self):
        """Test export when using TableView (no grouping)."""
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            model_data = []
            for path in db.paths:
                for _path, entry in db.data([path]).items():
                    model_data.append(ModelData(data=entry, path=_path))

            # Show data without grouping (uses TableView)
            self._view_manager.show_data(model_data, list(db.tags), group_by=None)

            with tempfile.TemporaryDirectory() as tmpdir:
                export_file = Path(tmpdir) / "table_export.csv"

                self._view_manager.save_data(
                    _format=ExportFormat.CSV,
                    export_file=str(export_file)
                )

                self.assertTrue(export_file.exists())
                content = export_file.read_bytes().decode('utf-8')
                # Should have exported the data
                self.assertGreater(len(content), 0)

    def test_export_with_tree_view(self):
        """Test export when using SpanningTreeview (with grouping)."""
        with tempfile.TemporaryDirectory() as db_path:
            test_paths = test_utils.get_test_paths()
            db = test_utils.create_test_media_db(db_path, test_paths)
            model_data = []
            for path in db.paths:
                for _path, entry in db.data([path]).items():
                    model_data.append(ModelData(data=entry, path=_path))

            # Show data with grouping (uses SpanningTreeview)
            self._view_manager.show_data(
                model_data,
                list(db.tags),
                group_by=["File:FileType"]
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                export_file = Path(tmpdir) / "tree_export.csv"

                self._view_manager.save_data(
                    _format=ExportFormat.CSV,
                    export_file=str(export_file)
                )

                self.assertTrue(export_file.exists())

    def test_full_export_signal_flow(self):
        """Test the complete signal flow: menu action -> signal -> export."""
        signal_received = []

        def on_export_requested():
            signal_received.append(True)

        self._view_manager.export_requested.connect(on_export_requested)

        # Trigger the export action
        self._view_manager._context_menu_requested_event(
            ViewContextMenuAction.EXPORT,
            None
        )

        # Signal should have been received
        self.assertEqual(1, len(signal_received))
        self.assertTrue(signal_received[0])


class TestViewManagerBaseViewBuilder(unittest.TestCase):
    """Tests for ViewManager's interaction with BaseViewBuilder for export."""

    def test_base_view_data_available_for_export(self):
        """Test that base view data is available after show_data."""
        view_manager = ViewManager(None)

        try:
            with tempfile.TemporaryDirectory() as db_path:
                test_paths = test_utils.get_test_paths()
                db = test_utils.create_test_media_db(db_path, test_paths)
                model_data = []
                for path in db.paths:
                    for _path, entry in db.data([path]).items():
                        model_data.append(ModelData(data=entry, path=_path))

                view_manager.show_data(model_data, list(db.tags))

                # _base_view should have data
                self.assertGreater(len(view_manager._base_view.data), 0)
        finally:
            view_manager.deleteLater()


if __name__ == '__main__':
    unittest.main()
