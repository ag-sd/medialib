import json
import tempfile
import unittest
from pathlib import Path

from app.collection.exifinfo import ExifInfo, ExifInfoStatus


class TestExifInfo(unittest.TestCase):

    def test_get_data_in_memory(self):
        tmp = Path(tempfile.NamedTemporaryFile(suffix='.jpeg').name)
        tmp.touch()
        test_info = ExifInfo(file=str(tmp))
        js = json.loads(test_info.data)[0]
        self.assertEqual(js['SourceFile'], str(tmp))
        self.assertEqual(js['ExifTool:Error'], "File is empty")

    def test_get_data_from_file(self):
        tmp = Path(tempfile.NamedTemporaryFile(suffix='.jpeg').name)
        tmp.touch()
        output = tempfile.NamedTemporaryFile(suffix='.output').name
        test_info = ExifInfo(file=str(tmp), save_file=str(output))
        js = json.loads(test_info.data)[0]
        self.assertEqual(js['SourceFile'], str(tmp))
        self.assertEqual(js['ExifTool:Error'], "File is empty")

        output_contents = Path(output).read_text(encoding="utf-8")
        js2 = json.loads(output_contents)[0]
        self.assertEqual(js, js2)

    def test_get_data_working(self):
        tmp = Path(tempfile.NamedTemporaryFile(suffix='.jpeg').name)
        tmp.touch()
        output = tempfile.NamedTemporaryFile(suffix='.output').name
        test_info = ExifInfo(file=str(tmp), save_file=str(output))
        test_info._status = ExifInfoStatus.WORKING
        try:
            test_info.data
            self.fail("This call should fail")
        except ValueError as v:
            self.assertEqual(str(v), "Service is not ready to return data")

    def test_file_does_not_exist(self):
        tmp = Path(tempfile.NamedTemporaryFile(suffix='.jpeg').name)
        try:
            _ = ExifInfo(file=str(tmp))
            self.fail("This call should fail")
        except ValueError as v:
            self.assertEqual(str(v), f"Input {str(tmp)} does not exist. Unable to proceed")

    def test_file_not_supported(self):
        tmp = Path(tempfile.NamedTemporaryFile(suffix='.xyz123').name)
        tmp.touch()
        try:
            _ = ExifInfo(file=str(tmp))
            self.fail("This call should fail")
        except ValueError as v:
            self.assertTrue(str(v).startswith(f"Input {str(tmp)} is not in the list of supported formats."))

