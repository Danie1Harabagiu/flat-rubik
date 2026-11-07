import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from flat_rubik.animation import Animator
from flat_rubik.cube_view import animated_point, view_regions


class CubeViewTests(unittest.TestCase):
    def test_animation_end_matches_physical_model(self):
        for face in "RLUDFB":
            for suffix in ("", "'", "2"):
                animator = Animator(duration=1)
                animator.cube.apply("R U F2 L' D B")
                animator.enqueue(face + suffix)
                animator.update(0)
                animator.elapsed = 1
                targets = {c.id: c for c in animator.target.cubies}
                for cubie in animator.cube.cubies:
                    target = targets[cubie.id]
                    actual = animated_point(cubie.position, cubie.position, animator)
                    for a, b in zip(actual, target.position):
                        self.assertAlmostEqual(a, b)
                    if cubie.kind != "center":
                        actual_stickers = {tuple(round(v) for v in animated_point(n, cubie.position, animator)): color
                                           for n, color in cubie.stickers.items()}
                        self.assertEqual(actual_stickers, target.stickers)

    def test_split_views_cover_available_space(self):
        for size in ((800, 700), (390, 472), (390, 798)):
            area = pygame.Rect(0, 46, *size)
            circle, cube = view_regions(area, "Ambele")
            self.assertFalse(circle.colliderect(cube))
            self.assertEqual(circle.union(cube), area)
            for mode in ("Cerc", "Cub"):
                regions = view_regions(area, mode)
                self.assertEqual(sum(r.w * r.h for r in regions), area.w * area.h)
