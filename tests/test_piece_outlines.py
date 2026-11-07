import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from flat_rubik import renderer


class PieceOutlineTests(unittest.TestCase):
    def test_colors_share_one_piece_without_internal_stroke(self):
        surface = pygame.Surface((240, 180))
        shapes = {0: ("rosu", [(20, 20), (100, 20), (100, 120), (20, 120)]),
                  1: ("verde", [(100, 20), (200, 20), (200, 120), (100, 120)])}
        animator = SimpleNamespace(current=None, shapes=lambda *args: shapes,
                                   outlines=lambda *args: {0: [(20, 20), (200, 20), (200, 120), (20, 120)]})
        with patch.object(renderer, "draw_zones"), patch.object(renderer, "CENTRE", {}), \
                patch.object(renderer, "FACE_COLORS", {}), patch.object(renderer, "geometrie_centre", return_value={}):
            renderer.draw(surface, animator=animator, transform=lambda p: p)
        for x in range(97, 104):
            self.assertIn(tuple(surface.get_at((x, 60)))[:3],
                          (renderer.CULORI_RGB["rosu"], renderer.CULORI_RGB["verde"]))
        self.assertEqual(tuple(surface.get_at((20, 60)))[:3], renderer.OUTLINE_RGB)

    def test_strokes_have_same_perpendicular_width_after_xy_transform(self):
        surface = pygame.Surface((400, 400))
        # Transform first: the oblique side becomes a 45-degree line.
        renderer.board_polygon(surface, (255, 255, 255), [(20, 200), (100, 40), (180, 200)],
                               8, transform=lambda p: (p[0] * 2, p[1]))
        # Center of the left edge: (120,120), outward/inward normals at 45 degrees.
        self.assertEqual(surface.get_at((122, 122))[:3], (255, 255, 255))
        self.assertEqual(surface.get_at((118, 118))[:3], (255, 255, 255))
        self.assertEqual(surface.get_at((124, 124))[:3], (0, 0, 0))
        # Horizontal bottom edge has the same +/- four-pixel extent.
        self.assertEqual(surface.get_at((200, 203))[:3], (255, 255, 255))
        self.assertEqual(surface.get_at((200, 205))[:3], (0, 0, 0))
