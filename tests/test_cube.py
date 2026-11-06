import random
import unittest
from collections import Counter

from flat_rubik.cube import Cube, FACE_NORMALS, FACE_COLORS, inverse, scramble
from flat_rubik.projection import project


class CubeTests(unittest.TestCase):
    def test_inventory_and_identities(self):
        cube = Cube()
        self.assertEqual(len(cube.cubies), 26)
        self.assertEqual(Counter(c.kind for c in cube.cubies), dict(center=6, edge=12, corner=8))
        self.assertEqual(len({c.id for c in cube.cubies}), 26)
        self.assertEqual(len({c.position for c in cube.cubies}), 26)
        self.assertTrue(cube.solved)
        self.assertEqual(cube.color_counts(), {c: 9 for c in FACE_COLORS.values()})

    def test_turn_identities_all_faces(self):
        for face in FACE_NORMALS:
            for suffix in ("", "'", "2"):
                with self.subTest(move=face + suffix):
                    cube = Cube()
                    initial = cube.snapshot()
                    cube.apply([face + suffix] * 4)
                    self.assertEqual(cube.snapshot(), initial)
                    cube.apply([face + suffix, inverse(face + suffix)])
                    self.assertEqual(cube.snapshot(), initial)
                    cube.apply([face, face])
                    other = Cube()
                    other.move(face + "2")
                    self.assertEqual(cube.snapshot(), other.snapshot())

    def test_clockwise_positions_and_orientation_independent_examples(self):
        # Track the front/up/right corner from an external face viewpoint.
        cases = {
            "F": ((1, -1, 1), {(0, 0, 1): "rosu", (1, 0, 0): "galben", (0, -1, 0): "verde"}),
            "R": ((1, 1, -1), {(0, 1, 0): "rosu", (0, 0, -1): "galben", (1, 0, 0): "verde"}),
            "U": ((-1, 1, 1), {(-1, 0, 0): "rosu", (0, 1, 0): "galben", (0, 0, 1): "verde"}),
        }
        for move, (position, stickers) in cases.items():
            cube = Cube()
            corner = next(c for c in cube.cubies if c.position == (1, 1, 1))
            cube.move(move)
            self.assertEqual(corner.position, position)
            self.assertEqual(corner.stickers, stickers)
        # Opposite faces: explicit edge cycles and sticker directions.
        for move, start, end, color, direction in (
            ("B", (0, 1, -1), (-1, 0, -1), "galben", (-1, 0, 0)),
            ("L", (-1, 0, 1), (-1, -1, 0), "rosu", (0, -1, 0)),
            ("D", (0, -1, 1), (1, -1, 0), "rosu", (1, 0, 0)),
        ):
            cube = Cube()
            edge = next(c for c in cube.cubies if c.position == start)
            cube.move(move)
            self.assertEqual(edge.position, end)
            self.assertEqual(edge.stickers[direction], color)

    def test_centers_colors_orientation_and_projection_long_sequence(self):
        cube = Cube()
        centers = [(c.id, c.position, c.stickers.copy()) for c in cube.cubies if c.kind == "center"]
        identities = {c.id: set(c.stickers.values()) for c in cube.cubies}
        sequence = scramble(250, random.Random(24))
        for move in sequence:
            cube.move(move)
            self.assertEqual(centers, [(c.id, c.position, c.stickers) for c in cube.cubies if c.kind == "center"])
            self.assertEqual(len({c.position for c in cube.cubies}), 26)
            self.assertEqual(cube.color_counts(), {c: 9 for c in FACE_COLORS.values()})
            for c in cube.cubies:
                self.assertEqual(set(c.stickers.values()), identities[c.id])
                self.assertEqual(tuple(map(sum, zip(*c.stickers))), c.position)
            views = project(cube)
            self.assertEqual(len(views), 54)
            self.assertEqual(len({s.key for s in views}), 54)
            self.assertEqual(len({(s.position, s.normal) for s in views}), 54)
            for c in cube.cubies:
                self.assertEqual(len([s for s in views if s.cubie_id == c.id]), len(c.stickers))
        cube.apply([inverse(m) for m in reversed(sequence)])
        self.assertEqual(cube.snapshot(), Cube().snapshot())

    def test_invalid_moves_are_atomic(self):
        cube = Cube()
        for move in ("", "X", "R3", "RR", "R2'", None):
            with self.assertRaises(ValueError):
                cube.move(move)
            self.assertEqual(cube.snapshot(), Cube().snapshot())


if __name__ == "__main__":
    unittest.main()
