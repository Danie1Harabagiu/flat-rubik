from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from flat_rubik.storage import read_text, write_text


class BrowserStorageTests(unittest.TestCase):
    def test_browser_saves_use_local_storage_and_survive_new_path_instances(self):
        values = {}
        local = SimpleNamespace(getItem=values.get, setItem=values.__setitem__)
        with patch("flat_rubik.storage.sys", SimpleNamespace(platform="emscripten")), \
             patch("platform.window", SimpleNamespace(localStorage=local), create=True):
            self.assertIsNone(read_text(Path("puzzle_session.json")))
            write_text(Path("puzzle_session.json"), '{"version":1}')
            self.assertEqual(read_text(Path("/different/runtime/puzzle_session.json")), '{"version":1}')
            self.assertIsNone(read_text(Path("cube_colors.json")))

    def test_storage_restrictions_are_reported_as_io_errors(self):
        def denied(*args):
            raise RuntimeError("Storage disabled")
        local = SimpleNamespace(getItem=denied, setItem=denied)
        with patch("flat_rubik.storage.sys", SimpleNamespace(platform="emscripten")), \
             patch("platform.window", SimpleNamespace(localStorage=local), create=True):
            with self.assertRaises(OSError):
                read_text(Path("puzzle_session.json"))
            with self.assertRaises(OSError):
                write_text(Path("puzzle_session.json"), "{}")
