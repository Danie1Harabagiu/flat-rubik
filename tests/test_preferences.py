import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from flat_rubik.preferences import DEFAULTS, PreferencesStore


class PreferencesTests(unittest.TestCase):
    def test_default_xy_and_roundtrip_all_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            first = PreferencesStore(path)
            self.assertEqual(first.values["fit_mode"], "auto")
            values = {"fit_mode": "tall", "view_mode": "Cub", "controls_visible": False,
                      "paths": True, "paused": True, "fullscreen": True, "active_mode": "45",
                      "window_size": [1350, 910], "yaw": .8, "pitch": -.3, "search_budget": 75,
                      "rubik_duration": 2.2, "puzzle45_duration": .4, "face_buttons": False,
                      "zoom_x": 1.8, "zoom_y": .7, "zoom_axis": "X"}
            first.save(values, force=True)
            self.assertEqual(PreferencesStore(path).values, values)
            self.assertFalse(path.with_suffix(".tmp").exists())
            # Every user-facing preference has been explicitly covered above.
            self.assertEqual(set(values), set(DEFAULTS))

    def test_invalid_fields_do_not_discard_valid_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            data = {"version": 1, "settings": {"fit_mode": "wide", "view_mode": "bad", "paths": "yes",
                    "yaw": float("nan"), "pitch": 10 ** 400, "search_budget": -5, "window_size": [-1, 200]}}
            path.write_text(json.dumps(data))
            result = PreferencesStore(path).values
            self.assertEqual(result["fit_mode"], "wide")
            for key in ("view_mode", "paths", "yaw", "pitch", "search_budget", "window_size"):
                self.assertEqual(result[key], DEFAULTS[key])
            path.write_text("not JSON")
            self.assertEqual(PreferencesStore(path).values["fit_mode"], "auto")
            with patch("flat_rubik.preferences.write_text", side_effect=OSError("read-only")):
                store = PreferencesStore(path)
                store.save({"fit_mode": "wide"}, force=True)
                self.assertIn("salva", store.message)

    def test_browser_settings_survive_new_instances(self):
        values = {}
        local = SimpleNamespace(getItem=values.get, setItem=values.__setitem__)
        with patch("flat_rubik.storage.sys", SimpleNamespace(platform="emscripten")), \
                patch("platform.window", SimpleNamespace(localStorage=local), create=True):
            first = PreferencesStore(Path("puzzle_settings.json"))
            first.save({**first.values, "fit_mode": "wide", "search_budget": 120}, force=True)
            second = PreferencesStore(Path("/different/runtime/puzzle_settings.json"))
            self.assertEqual(second.values["fit_mode"], "wide")
            self.assertEqual(second.values["search_budget"], 120)

    def test_drag_saves_are_debounced_but_final_value_is_flushed(self):
        with tempfile.TemporaryDirectory() as directory:
            now = [0]
            path = Path(directory) / "settings.json"
            store = PreferencesStore(path, clock=lambda: now[0])
            store.save(store.values)
            now[0] = .01
            store.save({**store.values, "yaw": 1})
            self.assertNotEqual(PreferencesStore(path).values["yaw"], 1)
            store.save(store.values, force=True)
            self.assertEqual(PreferencesStore(path).values["yaw"], 1)

    def test_application_restores_mode_layout_camera_speed_budget_and_pause(self):
        import pygame
        from flat_rubik.animation import Animator
        from flat_rubik.app import run
        from flat_rubik.editor import ColorEditor
        from flat_rubik.puzzle45 import Puzzle45
        from flat_rubik.solve_panel import SolvePanel
        from flat_rubik.solve_job import SearchJob
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "puzzle_settings.json"
            values = {**DEFAULTS, "fit_mode": "tall", "view_mode": "Cerc", "controls_visible": False,
                      "paths": True, "paused": True, "active_mode": "45", "search_budget": 11,
                      "window_size": [960, 720], "yaw": .8, "pitch": -.3,
                      "rubik_duration": 2, "puzzle45_duration": .4}
            PreferencesStore(path).save(values, force=True)
            classic, variant = Animator(), Puzzle45()
            solver = SolvePanel(SearchJob(browser=True, cache_dir=None))
            with patch("flat_rubik.app.Animator", return_value=classic), \
                    patch("flat_rubik.app.Puzzle45", return_value=variant), \
                    patch("flat_rubik.app.ColorEditor", return_value=ColorEditor()), \
                    patch("flat_rubik.app.SolvePanel", return_value=solver), \
                    patch("flat_rubik.app.draw_flat") as flat, patch("flat_rubik.app.draw_cube") as cube, \
                    patch("flat_rubik.app.render_controls") as controls, patch("pygame.event.get", return_value=[]):
                run(max_frames=1, session_path=Path(directory) / "puzzle_session.json")
            self.assertEqual(flat.call_args.kwargs["mode"], "tall")
            self.assertIs(flat.call_args.kwargs["animator"], variant)
            self.assertFalse(flat.call_args.kwargs["show_paths"])
            cube.assert_not_called()
            controls.assert_not_called()
            self.assertEqual(classic.duration, 2)
            self.assertEqual(variant.duration, .4)
            self.assertEqual(solver.budget_text, "11")
            restored = PreferencesStore(path).values
            values["paths"] = False  # Routes have been retired from the UI.
            for key in values:
                if key in ("yaw", "pitch"):
                    self.assertAlmostEqual(restored[key], values[key])
                else:
                    self.assertEqual(restored[key], values[key], key)


if __name__ == "__main__":
    unittest.main()
