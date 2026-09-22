from pathlib import Path
import tempfile
import unittest

from export import export


class ExportTests(unittest.TestCase):
    def test_short_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            destination = Path(directory) / "exported.txt"
            text = "Community café\nSaturday at noon.\n"
            source.write_text(text, encoding="utf-8")
            export(source, destination)
            self.assertEqual(destination.read_text(encoding="utf-8"), text)
