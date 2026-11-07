import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from flat_rubik.animation import Animator
from flat_rubik.cube import Cube
from flat_rubik.drag_turn import DragTurn
from flat_rubik.flat_view import flat_viewport
from flat_rubik.geometry import board_point
from flat_rubik.puzzle45 import Puzzle45


def shown(point, size, mode):
    virtual, destination = flat_viewport(size, mode)
    scale = min(virtual) / 800
    p = (virtual[0] / 2 + (point[0] - 400) * scale,
         virtual[1] / 2 + (point[1] - 400) * scale)
    x, y = board_point(p, *virtual)
    return destination.x + x * destination.w / virtual[0], destination.y + y * destination.h / virtual[1]


class DragTurnTests(unittest.TestCase):
    centers = {"F": (400, 400), "B": (715, 400), "U": (400, 235),
               "R": (565, 400), "D": (400, 565), "L": (235, 400)}

    def test_all_faces_both_directions_and_both_puzzles(self):
        for factory in (Animator, Puzzle45):
            for size, mode in (((800, 800), "proportional"), ((390, 510), "auto"),
                               ((1000, 420), "auto"), ((700, 800), "wide"), ((800, 700), "tall")):
                for face, point in self.centers.items():
                    for sign in (1, -1):
                        animator = factory()
                        before = animator.cube.snapshot()
                        start = shown(point, size, mode)
                        drag = DragTurn(animator, start, size, mode)
                        self.assertIn(face, drag.candidates, (face, size, mode))
                        vx, vy = drag.candidates[face]
                        end = start[0] + vx * sign * 60, start[1] + vy * sign * 60
                        drag.motion(end)
                        self.assertIsNotNone(drag.preview)
                        self.assertEqual(animator.cube.snapshot(), before)
                        self.assertFalse(animator.pending)
                        self.assertTrue(drag.release(end))
                        move = face + ("'" if sign < 0 else "")
                        expected = factory().cube
                        expected.move(move)
                        animator.update(animator.duration)
                        self.assertEqual(animator.cube.snapshot(), expected.snapshot())
                        self.assertEqual(animator.history, [move])

    def test_short_motion_busy_board_and_background_do_not_turn(self):
        animator = Animator()
        drag = DragTurn(animator, (400, 400), (800, 800), "proportional")
        self.assertFalse(drag.release((404, 402)))
        self.assertFalse(drag.moved)
        self.assertFalse(animator.pending)
        self.assertFalse(DragTurn(animator, (0, 0), (800, 800), "auto").candidates)
        animator.enqueue(["R"])
        self.assertFalse(DragTurn(animator, (400, 400), (800, 800), "auto").candidates)

    def test_drag_starts_on_a_piece_and_can_reverse(self):
        animator = Animator()
        start = shown((400, 330), (800, 800), "auto")
        drag = DragTurn(animator, start, (800, 800), "auto")
        self.assertIn("F", drag.candidates)
        self.assertIn("U", drag.candidates)
        drag.motion((start[0] + 50, start[1]))
        first = drag.move
        drag.motion((start[0] - 50, start[1]))
        self.assertNotEqual(first, drag.move)
        self.assertTrue(animator.cube.solved)
        self.assertFalse(animator.pending)

    def test_mouse_and_touch_release_commit_exactly_one_move(self):
        from flat_rubik.app import run
        from flat_rubik.editor import ColorEditor
        from flat_rubik.ui import layout
        from flat_rubik.cube_view import view_regions
        size = (390, 844)
        area = layout(size)[0].copy()
        area.y += 46
        area.h -= 46
        board, _ = view_regions(area, "Ambele")
        p = shown((400, 330), board.size, "auto")
        start = (round(p[0] + board.x), round(p[1] + board.y))
        end = (start[0] + 55, start[1])
        original = pygame.display.set_mode
        for touch in (False, True):
            animator = Animator()
            if touch:
                events = [pygame.event.Event(kind, x=p[0]/size[0], y=p[1]/size[1], finger_id=7)
                          for kind, p in ((pygame.FINGERDOWN, start), (pygame.FINGERMOTION, end), (pygame.FINGERUP, end))]
                events.insert(1, pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start, button=1, touch=True))
                events.append(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=end, button=1, touch=True))
            else:
                events = [pygame.event.Event(kind, pos=p, button=1) for kind, p in
                          ((pygame.MOUSEBUTTONDOWN, start), (pygame.MOUSEMOTION, end), (pygame.MOUSEBUTTONUP, end))]
            with patch("flat_rubik.app.Animator", return_value=animator), \
                    patch("flat_rubik.app.ColorEditor", side_effect=lambda *a: ColorEditor()), \
                    patch("pygame.event.get", return_value=events), \
                    patch("pygame.display.set_mode", side_effect=lambda *a: original(size)):
                run(max_frames=1, session_path=None)
            self.assertEqual(animator.pending + len(animator.history), 1)
