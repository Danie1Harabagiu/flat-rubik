import math
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from flat_rubik.animation import Animator
from flat_rubik.controls import move_for_click
from flat_rubik.cube import FACE_COLORS
from flat_rubik.editor import ColorEditor, slot_at
from flat_rubik.flat_view import FIT_MODES, draw_flat, flat_pointer, flat_viewport
from flat_rubik.geometry import board_point, rotation_handles


def displayed(point, virtual, destination):
    x, y = board_point(point, *virtual)
    return destination.x + x * destination.w / virtual[0], destination.y + y * destination.h / virtual[1]


class FlatFitTests(unittest.TestCase):
    def test_stretched_views_are_rasterized_natively_without_bitmap_resizing(self):
        import pygame
        from flat_rubik.puzzle45 import Puzzle45
        from flat_rubik.renderer import CULORI_RGB
        pygame.init()
        try:
            for animator in (Animator(), Puzzle45()):
                animator.enqueue("R")
                animator.update(.15)
                for size in ((1600, 400), (400, 1600)):
                    for mode in ("wide", "tall", "auto"):
                        surface = pygame.Surface(size)
                        with patch("pygame.transform.smoothscale", side_effect=AssertionError("Bitmap scaling")), \
                                patch("pygame.transform.scale", side_effect=AssertionError("Bitmap scaling")):
                            draw_flat(surface, mode, animator=animator, hovered="R", show_paths=True)
                        virtual, destination = flat_viewport(size, mode)
                        point = (virtual[0] / 2, virtual[1] / 2)
                        pixel = tuple(round(v) for v in displayed(point, virtual, destination))
                        self.assertEqual(tuple(surface.get_at(pixel))[:3], CULORI_RGB["rosu"])
        finally:
            pygame.quit()

    def test_every_stretched_center_and_rotation_handle_keeps_correct_clicks(self):
        for size in ((1200, 400), (400, 900), (390, 472), (800, 800)):
            for mode in FIT_MODES:
                virtual, destination = flat_viewport(size, mode)
                for face, color in FACE_COLORS.items():
                    _, left, right, _ = rotation_handles(*virtual)[color]
                    for point, expected in ((left, face + "'"), (right, face)):
                        shown = displayed(point, virtual, destination)
                        actual, coordinates = flat_pointer(shown, size, mode)
                        self.assertLess(math.dist(actual, point), 1e-8)
                        self.assertEqual(move_for_click(actual, 1, coordinates), expected, (mode, face))

    def test_auto_fills_axes_independently_and_manual_modes_have_distinct_aspects(self):
        for size in ((1200, 400), (400, 900)):
            _, full = flat_viewport(size, "auto")
            self.assertEqual(full.size, size)
            self.assertEqual(full.topleft, (0, 0))
            _, wide = flat_viewport(size, "wide")
            _, tall = flat_viewport(size, "tall")
            self.assertAlmostEqual(wide.w / wide.h, 1.4, delta=.01)
            self.assertAlmostEqual(tall.h / tall.w, 1.4, delta=.01)
            for destination in (wide, tall):
                self.assertGreaterEqual(destination.x, 0)
                self.assertGreaterEqual(destination.y, 0)
                self.assertLessEqual(destination.right, size[0])
                self.assertLessEqual(destination.bottom, size[1])
        self.assertIsNone(flat_pointer((0, 0), (1200, 400), "tall"))

    def test_color_editor_selects_same_sticker_after_stretch(self):
        for size in ((1000, 400), (400, 1000)):
            for mode in FIT_MODES:
                virtual, destination = flat_viewport(size, mode)
                scale = min(virtual) / 800
                point = virtual[0] / 2, virtual[1] / 2 - 106 * scale
                target = slot_at(point, virtual)
                self.assertIsNotNone(target)
                mapped, coordinates = flat_pointer(displayed(point, virtual, destination), size, mode)
                self.assertEqual(slot_at(mapped, coordinates), target)

    def test_toggling_fit_does_not_change_cube_view_or_logical_state(self):
        import pygame
        from flat_rubik.app import run
        from flat_rubik.cube_view import draw_cube
        animator = Animator()
        animator.cube.move("F")
        before = animator.cube.snapshot()
        images, modes = [], []

        def capture_cube(surface, *args):
            draw_cube(surface, *args)
            images.append((surface.get_size(), pygame.image.tostring(surface, "RGB")))

        def capture_flat(surface, mode, **kwargs):
            modes.append(mode)
            draw_flat(surface, mode, **kwargs)

        batches = [[pygame.event.Event(pygame.KEYDOWN, key=pygame.K_t, mod=0)] for _ in range(4)]
        with patch("flat_rubik.app.Animator", return_value=animator), \
                patch("flat_rubik.app.ColorEditor", return_value=ColorEditor()), \
                patch("flat_rubik.app.draw_cube", side_effect=capture_cube), \
                patch("flat_rubik.app.draw_flat", side_effect=capture_flat), \
                patch("pygame.event.get", side_effect=batches):
            run(max_frames=4, session_path=None)
        self.assertEqual(modes, ["wide", "tall", "auto", "proportional"])
        self.assertEqual(animator.cube.snapshot(), before)
        self.assertEqual(len(images), 4)
        self.assertTrue(all(image == images[0] for image in images))
