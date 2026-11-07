import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from flat_rubik.animation import Animator
from flat_rubik.cube import FACE_NORMALS
from flat_rubik.geometry import geometrie_centre
from flat_rubik.puzzle45 import Puzzle45, inverse_twist
from flat_rubik.session import SessionStore


class Puzzle45Tests(unittest.TestCase):
    def assertSameShapes(self, a, b, tolerance=1e-6):
        self.assertEqual(a.keys(), b.keys())
        for key, (color, points) in a.items():
            self.assertEqual(color, b[key][0])
            self.assertEqual(len(points), len(b[key][1]))
            self.assertLess(max(math.dist(p, q) for p, q in zip(points, b[key][1])), tolerance)

    def test_45_is_a_committed_position_and_other_faces_can_follow(self):
        puzzle = Puzzle45()
        before = puzzle.shapes(800, 800)
        puzzle.enqueue("F")
        puzzle.update(1)
        self.assertIsNone(puzzle.current)
        self.assertEqual(puzzle.history, ["F"])
        after = puzzle.shapes(800, 800)
        # A red front sticker moves 45 degrees, not 90 degrees.
        key = next(key for key in before if key[1] == "rosu")
        p, q = before[key][1][0], after[key][1][0]
        angle = (math.atan2(q[1] - 400, q[0] - 400) - math.atan2(p[1] - 400, p[0] - 400)) % (2 * math.pi)
        self.assertAlmostEqual(angle, math.pi / 4)
        puzzle.enqueue("R U B' L D")
        puzzle.update(5)
        self.assertEqual(len(puzzle.history), 6)
        self.assertEqual(puzzle.pending, 0)
        self.assertEqual(len(puzzle.outlines(800, 800)), 20)
        self.assertEqual(set(before), set(puzzle.shapes(800, 800)))

    def test_arbitrary_moves_and_inverses_preserve_all_colored_regions(self):
        puzzle = Puzzle45()
        before = puzzle.shapes(800, 800)
        moves = "R U F2 L' B D R' F U2 B'".split()
        puzzle.enqueue(moves + [inverse_twist(m) for m in reversed(moves)])
        puzzle.update(20)
        self.assertSameShapes(before, puzzle.shapes(800, 800))
        self.assertTrue(puzzle.is_solved)

    def test_eight_turns_restore_positions_and_orientations_on_every_face(self):
        for face in FACE_NORMALS:
            puzzle = Puzzle45()
            before = puzzle.cube.snapshot()
            puzzle.enqueue([face] * 8)
            puzzle.update(8)
            self.assertEqual(before, puzzle.cube.snapshot())

    def test_all_six_centers_are_fixed_under_every_move(self):
        puzzle = Puzzle45()
        before = [(c.id, c.position, c.stickers.copy()) for c in puzzle.cube.cubies if c.kind == "center"]
        for face in FACE_NORMALS:
            puzzle.enqueue(face)
            puzzle.update(1)
            self.assertEqual(before, [(c.id, c.position, c.stickers) for c in puzzle.cube.cubies if c.kind == "center"])
            self.assertEqual(len({c.position for c in puzzle.cube.cubies}), 26)

    def test_pause_speed_resize_and_animation_endpoint(self):
        puzzle = Puzzle45()
        puzzle.enqueue("R")
        puzzle.update(.5)
        frame = puzzle.shapes(800, 800)
        puzzle.set_duration(2)
        self.assertSameShapes(frame, puzzle.shapes(800, 800))
        puzzle.elapsed = 2 - 1e-9
        near_end = puzzle.shapes(800, 800)
        puzzle.update(1)
        import pygame
        # Near-end contours cover the target's same colored areas, despite resampling.
        def mask(points):
            s = pygame.Surface((800, 800))
            s.fill("black")
            pygame.draw.polygon(s, "white", points)
            return pygame.mask.from_threshold(s, (255, 255, 255), (1, 1, 1, 255))
        for key, (_, points) in puzzle.shapes(800, 800).items():
            a, b = mask(points), mask(near_end[key][1])
            self.assertLess(abs(a.count() - b.count()), 60)
        small = puzzle.shapes(400, 600)
        for key, (_, points) in puzzle.shapes(800, 800).items():
            for p, q in zip(points, small[key][1]):
                self.assertAlmostEqual(q[0], p[0] / 2)
                self.assertAlmostEqual(q[1], p[1] / 2 + 100)

    def test_session_restores_both_modes_and_ignores_unfinished_move(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.json"
            classic, variant = Animator(), Puzzle45()
            classic.cube.apply("R U F2")
            variant.enqueue("R U F")
            variant.update(3)
            expected = variant.shapes(800, 800)
            variant.enqueue("B")
            variant.update(.5)
            store = SessionStore(path)
            store.save(classic, variant)
            first = path.read_bytes()
            store.save(classic, variant)
            self.assertEqual(first, path.read_bytes())
            other_classic, other_variant = Animator(), Puzzle45()
            SessionStore(path).restore(other_classic, other_variant)
            self.assertEqual(classic.cube.snapshot(), other_classic.cube.snapshot())
            self.assertSameShapes(expected, other_variant.shapes(800, 800))
            self.assertEqual(other_variant.pending, 0)
            self.assertFalse(path.with_suffix(".tmp").exists())
            data = json.loads(path.read_text())
            data["puzzle45"]["pieces"][0]["position"] = [99, 0, 0]
            path.write_text(json.dumps(data))
            clean = Puzzle45()
            SessionStore(path).restore(Animator(), clean)
            self.assertTrue(clean.is_solved)

    def test_cells_do_not_overlap_or_cover_centers_during_animation(self):
        import pygame
        import test_layer_motion as motion_checks
        checks = motion_checks.LayerMotionTests()
        checks.setUp()
        for face in FACE_NORMALS:
            for suffix in ("", "'", "2", "2'"):
                puzzle = Puzzle45()
                puzzle.enqueue("R F U")
                puzzle.update(3)
                puzzle.enqueue(face + suffix)
                puzzle.update(0)
                for t in (.125, .5, .875):
                    puzzle.elapsed = t
                    occupied = pygame.mask.Mask(checks.size)
                    for points in puzzle.outlines(*checks.size).values():
                        inside = checks.interior(checks.mask(points))
                        self.assertEqual(occupied.overlap_area(inside, (0, 0)), 0, (face, suffix, t))
                        occupied.draw(inside, (0, 0))
                    for center in geometrie_centre(*checks.size).values():
                        if center["tip"] == "poligon":
                            fixed = checks.interior(checks.mask(center["puncte"]))
                        else:
                            s = pygame.Surface(checks.size)
                            s.fill("black")
                            radius = center.get("raza", center.get("raza_exterioara"))
                            width = 0 if center["tip"] == "cerc" else radius - center["raza_interioara"]
                            pygame.draw.circle(s, "white", center["centru"], radius, width)
                            fixed = pygame.mask.from_threshold(s, (255, 255, 255), (1, 1, 1, 255))
                        self.assertEqual(occupied.overlap_area(fixed, (0, 0)), 0, (face, suffix, t))

    def test_ui_switches_modes_and_restarts_in_classic(self):
        import pygame
        from flat_rubik.app import run
        from flat_rubik.editor import ColorEditor
        from flat_rubik.ui import layout
        classic, variant = Animator(), Puzzle45()
        mode = layout((1080, 800))[4]["mode"].center
        events = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=mode, button=1),
                  pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f, mod=0)]
        with patch("flat_rubik.app.Animator", return_value=classic), patch("flat_rubik.app.Puzzle45", return_value=variant), \
                patch("flat_rubik.app.ColorEditor", return_value=ColorEditor()), patch("pygame.event.get", return_value=events):
            run(max_frames=1, session_path=None)
        self.assertEqual(variant.current, "F")
        self.assertIsNone(classic.current)
        variant.update(1)
        # A new application run always starts in Rubik, irrespective of the prior mode.
        with patch("flat_rubik.app.Animator", return_value=classic), patch("flat_rubik.app.Puzzle45", return_value=variant), \
                patch("flat_rubik.app.ColorEditor", return_value=ColorEditor()), \
                patch("pygame.event.get", return_value=[pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r, mod=0)]):
            run(max_frames=1, session_path=None)
        self.assertEqual(classic.current, "R")
        self.assertIsNone(variant.current)


if __name__ == "__main__":
    unittest.main()
