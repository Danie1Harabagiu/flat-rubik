import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from flat_rubik.animation import Animator
from flat_rubik.drag_turn import DragTurn
from flat_rubik.flat_view import FIT_MODES, flat_viewport, flat_pointer, draw_flat
from flat_rubik.geometry import board_point
from flat_rubik.preferences import DEFAULTS, PreferencesStore, normalized


class ZoomTests(unittest.TestCase):
    def test_independent_axes_and_inverse_pointer_for_all_layouts(self):
        for size in ((390, 506), (1000, 450), (450, 850)):
            for mode in FIT_MODES:
                for zoom in ((.4, .4), (2, 1), (1, 2.5), (1.8, .7)):
                    virtual, base = flat_viewport(size, mode)
                    virtual, destination = flat_viewport(size, mode, zoom)
                    self.assertEqual(destination.center, base.center)
                    self.assertGreaterEqual(min(virtual), min(flat_viewport(size, mode)[0]))
                    self.assertAlmostEqual(destination.w / base.w, zoom[0], delta=1/base.w)
                    self.assertAlmostEqual(destination.h / base.h, zoom[1], delta=1/base.h)
                    source = (virtual[0] / 2 + 12, virtual[1] / 2 - 18)
                    x, y = board_point(source, *virtual)
                    point = (destination.x + x * destination.w / virtual[0],
                             destination.y + y * destination.h / virtual[1])
                    mapped, _ = flat_pointer(point, size, mode, zoom)
                    self.assertAlmostEqual(mapped[0], source[0])
                    self.assertAlmostEqual(mapped[1], source[1])

    def test_zoom_draws_native_geometry_and_drag_keeps_physical_move(self):
        animator = Animator()
        before = animator.cube.snapshot()
        surface = pygame.Surface((600, 500))
        with patch("pygame.transform.smoothscale", side_effect=AssertionError("bitmap enlargement")):
            draw_flat(surface, mode="auto", zoom=(2, .7), animator=animator)
        self.assertEqual(animator.cube.snapshot(), before)
        drag = DragTurn(animator, (300, 250), surface.get_size(), "auto", (2, .7))
        self.assertTrue(drag.release((360, 250)))
        animator.update(2)
        self.assertEqual(animator.history, ["F"])

    def test_invalid_zoom_settings_fall_back(self):
        values = normalized({"zoom_x": float("nan"), "zoom_y": 99, "zoom_axis": "Z"})
        self.assertEqual((values["zoom_x"], values["zoom_y"], values["zoom_axis"]), (1, 1, "XY"))

    def test_buttons_and_pinch_save_zoom_without_rotating_cube(self):
        from flat_rubik.app import run
        from flat_rubik.editor import ColorEditor
        from flat_rubik.ui import layout, zoom_buttons
        from flat_rubik.cube_view import view_regions
        size = (390, 844)
        area = layout(size)[0].copy()
        area.y += 46
        area.h -= 46
        board, _ = view_regions(area, "Cerc")
        buttons = zoom_buttons(board)
        click = lambda key: pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=buttons[key].center, button=1)
        # Select X and enlarge it; switch to Y and zoom out; reset both.
        for events, expected in (([click("axis"), click("in")], (1.12, 1)),
                                 ([click("axis"), click("axis"), click("out")], (1, 1/1.12)),
                                 ([click("in"), click("reset")], (1, 1))):
            self._app_case(events, expected, size)
        cx, cy = board.center
        touch = lambda kind, finger, x: pygame.event.Event(kind, finger_id=finger, x=x/size[0], y=cy/size[1])
        events = [touch(pygame.FINGERDOWN, 1, cx-30), touch(pygame.FINGERDOWN, 2, cx+30),
                  touch(pygame.FINGERMOTION, 2, cx+90), touch(pygame.FINGERUP, 2, cx+90),
                  touch(pygame.FINGERUP, 1, cx-30)]
        self._app_case(events, (2, 2), size)

    def _app_case(self, events, expected, size):
        from flat_rubik.app import run
        from flat_rubik.editor import ColorEditor
        animator = Animator()
        original = pygame.display.set_mode
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "puzzle_session.json"
            PreferencesStore(path.with_name("puzzle_settings.json")).save({**DEFAULTS, "view_mode": "Cerc"}, force=True)
            with patch("flat_rubik.app.Animator", return_value=animator), \
                    patch("flat_rubik.app.ColorEditor", side_effect=lambda *args: ColorEditor()), \
                    patch("pygame.event.get", return_value=events), \
                    patch("pygame.display.set_mode", side_effect=lambda *args: original(size)):
                run(max_frames=1, session_path=path)
            settings = PreferencesStore(path.with_name("puzzle_settings.json")).values
            self.assertAlmostEqual(settings["zoom_x"], expected[0])
            self.assertAlmostEqual(settings["zoom_y"], expected[1])
            self.assertTrue(animator.cube.solved)
            self.assertFalse(animator.pending)
