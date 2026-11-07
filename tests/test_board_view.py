import math
import unittest

from flat_rubik.geometry import board_point, rotation_handles
from flat_rubik.controls import move_for_click
from flat_rubik.cube import FACE_COLORS


class BoardViewTests(unittest.TestCase):
    def test_view_inverse_preserves_clicks_across_board_and_sizes(self):
        for size in ((800, 800), (400, 600), (1200, 500)):
            for x in range(0, size[0] + 1, 25):
                for y in range(0, size[1] + 1, 25):
                    shown = board_point((x, y), *size)
                    restored = board_point(shown, *size, inverse=True)
                    self.assertLess(math.dist(restored, (x, y)), 1e-9)
            for face, color in FACE_COLORS.items():
                _, left, right, _ = rotation_handles(*size)[color]
                for point, move in ((left, face + "'"), (right, face)):
                    shown = board_point(point, *size)
                    local = board_point(shown, *size, inverse=True)
                    self.assertEqual(move_for_click(local, 1, size), move)

    def test_diagonals_extend_and_cardinal_extents_stay_fixed(self):
        self.assertEqual(board_point((400, 70), 800, 800), (400, 70))
        x, y = board_point((420, 420), 800, 800)
        self.assertGreater(x, 420)
        self.assertGreater(y, 420)
