import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from flat_rubik.animation import Animator
from flat_rubik.layer_motion import layer_shapes
from flat_rubik.projection import mobile_shapes
from flat_rubik.cube import Cube
from copy import deepcopy


class InterfaceTests(unittest.TestCase):
    def test_duration_label_does_not_overlap_sidebar_buttons(self):
        import pygame
        from flat_rubik.ui import layout
        from flat_rubik.renderer import text_surface
        pygame.init()
        try:
            for faces in (False, True):
                _, panel, buttons, slider, actions, _ = layout((1080, 800), face_buttons=faces)
                label = text_surface("Durata rotatiei: 0.2 s", 22, (0, 0, 0))
                rect = label.get_rect(topleft=(panel.x + 16, slider.y - 45))
                for name, button in {**buttons, **actions}.items():
                    self.assertFalse(rect.colliderect(button), (faces, name))
                self.assertGreaterEqual(rect.top - actions["mode"].bottom, 8)
        finally:
            pygame.quit()

    def test_main_panel_keeps_editor_and_optional_face_buttons_without_routes(self):
        from flat_rubik.ui import layout
        for size in ((1080, 800), (390, 844), (640, 700), (320, 360)):
            actions = layout(size)[4]
            self.assertIn("edit", actions)
            self.assertNotIn("paths", actions)
            self.assertIn("faces", actions)
            self.assertTrue({"pause", "reset", "shuffle", "mode", "fit", "solve"} <= actions.keys())
            editor = layout(size, editing=True)[4]
            self.assertIn("edit", editor)
            self.assertIn("paths", editor)
        self.assertFalse(layout((1080, 800))[2])
        expanded = layout((390, 844), face_buttons=True)
        collapsed = layout((390, 844), face_buttons=False)
        self.assertEqual(len(expanded[2]), 6)
        self.assertFalse(collapsed[2])
        self.assertGreater(collapsed[0].h, expanded[0].h)

    def setUp(self):
        from flat_rubik.editor import ColorEditor
        # Keep the user's saved configuration independent of UI tests.
        isolation = patch("flat_rubik.app.ColorEditor", side_effect=lambda *args, **kwargs: ColorEditor())
        isolation.start()
        self.addCleanup(isolation.stop)

    def test_phone_can_collapse_face_buttons_and_still_open_color_editor(self):
        import pygame
        import tempfile
        from pathlib import Path
        from flat_rubik.app import run
        from flat_rubik.editor import ColorEditor
        from flat_rubik.preferences import PreferencesStore
        from flat_rubik.ui import layout
        size = (390, 844)
        original = pygame.display.set_mode
        animator = Animator()
        editor = ColorEditor()
        actions = layout(size)[4]
        events = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=actions["faces"].center, button=1),
                  pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=layout(size, face_buttons=False)[4]["edit"].center, button=1)]
        with tempfile.TemporaryDirectory() as directory:
            with patch("flat_rubik.app.Animator", return_value=animator), \
                    patch("flat_rubik.app.ColorEditor", return_value=editor), \
                    patch("pygame.display.set_mode", side_effect=lambda *args: original(size)), \
                    patch("pygame.event.get", return_value=events):
                run(max_frames=1, session_path=Path(directory) / "puzzle_session.json")
            self.assertTrue(editor.editing)
            settings = PreferencesStore(Path(directory) / "puzzle_settings.json")
            self.assertIs(settings.values["face_buttons"], False)

    def test_speed_change_preserves_progress_and_contour(self):
        animator = Animator(duration=1)
        animator.enqueue("R")
        animator.update(.4)
        before = animator.shapes(800, 800)
        animator.set_duration(2.5)
        self.assertAlmostEqual(animator.elapsed, 1)
        self.assertEqual(before, animator.shapes(800, 800))
        animator.update(1.51)
        self.assertEqual(animator.history, ["R"])
        self.assertEqual(animator.pending, 0)
        for duration in (0, -1):
            with self.assertRaises(ValueError):
                animator.set_duration(duration)

    def test_rotating_shapes_do_not_collapse_at_half_turn(self):
        def area(points):
            return abs(sum(a[0] * b[1] - b[0] * a[1]
                           for a, b in zip(points, points[1:] + points[:1]))) / 2

        cube = Cube()
        source = mobile_shapes(cube, 800, 800)
        for move in ("F", "F'", "F2", "B", "B'", "B2"):
            target = deepcopy(cube)
            target.move(move)
            for t in (.1, .25, .5, .75, .9):
                frame = layer_shapes(cube, target, move, t, 800, 800)
                for key, (_, polygon) in frame.items():
                    self.assertAlmostEqual(area(polygon), area(source[key][1]), places=6)

    def test_responsive_controls_fit_and_render(self):
        import pygame
        from flat_rubik.ui import layout, render_controls
        from flat_rubik.renderer import draw, BACKGROUND_RGB
        pygame.init()
        try:
            animator = Animator()
            animator.enqueue("R")
            animator.update(.15)
            for size in ((1080, 800), (640, 700), (320, 360), (1200, 500)):
                screen = pygame.display.set_mode(size)
                board, panel, buttons, slider, actions, compact = layout(size)
                self.assertFalse(board.colliderect(panel))
                for rect in (*buttons.values(), *actions.values(), slider):
                    self.assertTrue(panel.contains(rect), (size, rect))
                screen.fill(BACKGROUND_RGB)
                draw(screen.subsurface(board), animator=animator, hovered="R")
                render_controls(screen, animator, True, True, "R")
        finally:
            pygame.quit()

    def test_slider_drag_and_pause_preserve_active_move(self):
        import pygame
        from flat_rubik.ui import layout
        from flat_rubik.app import run
        animator = Animator(duration=1)
        animator.enqueue("U")
        animator.update(.4)
        _, _, _, slider, actions, _ = layout((1080, 800))
        events = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=slider.midleft, button=1),
                  pygame.event.Event(pygame.MOUSEMOTION, pos=slider.midright),
                  pygame.event.Event(pygame.MOUSEBUTTONUP, pos=slider.midright, button=1),
                  pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=actions["pause"].center, button=1)]
        with patch("flat_rubik.app.Animator", return_value=animator), patch("pygame.event.get", side_effect=[events, []]):
            run(max_frames=2, session_path=None)
        self.assertEqual(animator.duration, 3.0)
        self.assertAlmostEqual(animator.elapsed / animator.duration, .4)
        self.assertEqual(animator.current, "U")

    def test_hover_lights_the_layer_without_changing_sticker_colors(self):
        import pygame
        from flat_rubik.renderer import draw, BACKGROUND_RGB, CULORI_RGB
        from flat_rubik.cube import FACE_NORMALS
        pygame.init()
        try:
            animator = Animator()
            surface = pygame.Surface((800, 800))
            surface.fill(BACKGROUND_RGB)
            draw(surface, animator=animator)
            baseline = pygame.mask.from_threshold(surface, (255, 255, 255), (1, 1, 1, 255)).count()
            for face in FACE_NORMALS:
                surface.fill(BACKGROUND_RGB)
                draw(surface, animator=animator, hovered=face)
                white = pygame.mask.from_threshold(surface, (255, 255, 255), (1, 1, 1, 255)).count()
                self.assertGreater(white, baseline, face)
                for color, polygon in animator.shapes(800, 800).values():
                    from flat_rubik.geometry import board_point
                    middle = tuple(sum(p[i] for p in polygon) / len(polygon) for i in (0, 1))
                    sample = tuple(round(v) for v in board_point(middle, 800, 800))
                    self.assertEqual(tuple(surface.get_at(sample))[:3], CULORI_RGB[color], (face, color))
        finally:
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
