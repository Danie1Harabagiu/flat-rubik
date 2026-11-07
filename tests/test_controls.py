import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from flat_rubik.controls import move_for_click
from flat_rubik.animation import Animator
from flat_rubik.cube import Cube, FACE_COLORS


class MouseControlsTests(unittest.TestCase):
    def setUp(self):
        from flat_rubik.editor import ColorEditor
        isolation = patch("flat_rubik.app.ColorEditor", side_effect=lambda *args, **kwargs: ColorEditor())
        isolation.start()
        self.addCleanup(isolation.stop)

    # Interior points of the six drawn center regions at 800 x 800.
    centers = {"F": (400, 400), "B": (715, 400), "U": (400, 235),
               "R": (565, 400), "D": (400, 565), "L": (235, 400)}

    def test_all_centers_both_buttons_after_resize(self):
        for width, height in ((800, 800), (400, 600), (1200, 500)):
            scale = min(width, height) / 800
            for face, (x, y) in self.centers.items():
                point = (width / 2 + (x - 400) * scale, height / 2 + (y - 400) * scale)
                self.assertEqual(move_for_click(point, 1, (width, height)), face)
                self.assertEqual(move_for_click(point, 3, (width, height)), face + "'")

    def test_gaps_stickers_and_other_buttons_are_ignored(self):
        for point in ((0, 0), (400, 345), (400, 330), (400, 180),
                      (400, 112), (500, 300), (760, 400)):
            for button in (1, 3):
                self.assertIsNone(move_for_click(point, button, (800, 800)))
        for button in (2, 4, 5):
            self.assertIsNone(move_for_click((400, 400), button, (800, 800)))

    def test_arrows_choose_both_directions_with_left_click(self):
        from flat_rubik.geometry import rotation_handles
        for size in ((800, 800), (400, 600), (1200, 500)):
            for face, color in FACE_COLORS.items():
                _, left, right, _ = rotation_handles(*size)[color]
                self.assertEqual(move_for_click(left, 1, size), face + "'")
                self.assertEqual(move_for_click(right, 1, size), face)

    def test_pygame_mouse_events_enqueue_inverse_pairs(self):
        import pygame
        from flat_rubik.app import run
        animator = Animator()
        events, expected = [], []
        from flat_rubik.cube_view import view_regions
        from flat_rubik.ui import layout
        from flat_rubik.geometry import board_point
        from flat_rubik.flat_view import flat_viewport
        area = layout((1080, 800))[0].copy()
        area.y += 46
        area.h -= 46
        circle, _ = view_regions(area, "Ambele")
        virtual, destination = flat_viewport(circle.size, "auto")
        for face, (x, y) in self.centers.items():
            scale = min(virtual) / 800
            local = (virtual[0] / 2 + (x - 400) * scale, virtual[1] / 2 + (y - 400) * scale)
            shown = board_point(local, *virtual)
            point = (circle.x + destination.x + shown[0] * destination.w / virtual[0],
                     circle.y + destination.y + shown[1] * destination.h / virtual[1])
            for button in (1, 3):
                events.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=point, button=button))
                expected.append(face + ("'" if button == 3 else ""))
        events.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(0, 0), button=1))
        with patch("flat_rubik.app.Animator", return_value=animator), patch("pygame.event.get", return_value=events):
            run(max_frames=1, session_path=None)
        self.assertEqual([animator.current] + list(animator.queue), expected)
        animator.update(4)
        self.assertEqual(animator.cube.snapshot(), Cube().snapshot())

    def test_white_face_and_stickers(self):
        from flat_rubik.renderer import CULORI_RGB
        self.assertEqual(FACE_COLORS["D"], "alb")
        self.assertEqual(Cube().color_counts()["alb"], 9)
        self.assertEqual(CULORI_RGB["alb"], (255, 255, 255))

    def test_phone_touch_selects_both_directions_without_duplicate_moves(self):
        import pygame
        from flat_rubik.app import run
        from flat_rubik.ui import layout
        animator = Animator()
        size = (390, 844)
        board, panel, buttons, slider, actions, compact = layout(size)
        events = []
        expected = []
        for face, rect in buttons.items():
            self.assertGreaterEqual(rect.w / 2, 44)
            self.assertGreaterEqual(rect.h, 44)
            for direction in (-1, 1):
                x = rect.centerx + direction * rect.w / 4
                y = rect.centery
                events.extend([
                    pygame.event.Event(pygame.FINGERDOWN, x=x / size[0], y=y / size[1], finger_id=7),
                    pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1, touch=True),
                    pygame.event.Event(pygame.FINGERUP, x=x / size[0], y=y / size[1], finger_id=7),
                ])
                expected.append(face + ("'" if direction == -1 else ""))
        set_mode = pygame.display.set_mode
        with patch("flat_rubik.app.Animator", return_value=animator), \
             patch("pygame.event.get", return_value=events), \
             patch("pygame.display.set_mode", side_effect=lambda *args: set_mode(size)):
            run(max_frames=1, session_path=None)
        self.assertEqual([animator.current] + list(animator.queue), expected)


if __name__ == "__main__":
    unittest.main()
