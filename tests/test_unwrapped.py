import unittest

import pygame

from flat_rubik.animation import Animator
from flat_rubik.editor import slot_at, slot_regions
from flat_rubik.flat_view import (
    UNWRAP_SIZE, _unwrapped_destination, _unwrapped_polygon,
    draw_unwrapped, unwrapped_pointer, unwrapped_screen_point,
)
from flat_rubik.renderer import BACKGROUND_RGB, CULORI_RGB


class UnwrappedTests(unittest.TestCase):
    def test_cut_pieces_are_complete_at_both_ends_with_gaps(self):
        size = (1000, 700)
        surface = pygame.Surface(size)
        draw_unwrapped(surface, Animator())
        destination = _unwrapped_destination(size)
        cell = destination.w / 12

        def pixel(x, row):
            return surface.get_at((round(x), round(destination.y + row * destination.h / 7)))[:3]

        for edge in (destination.left, destination.right):
            for row in (2.5, 3.5, 4.5):
                self.assertEqual(pixel(edge - cell / 2, row), CULORI_RGB['verde'])
                self.assertEqual(pixel(edge + cell / 2, row), CULORI_RGB['alb'])
                self.assertIsNotNone(unwrapped_pointer(
                    (edge - cell / 2, destination.y + row * destination.h / 7), size))
        self.assertEqual(pixel(destination.left + cell, 2.5), BACKGROUND_RGB)
        for row in (1, 3, 4, 6):
            self.assertEqual(pixel(destination.centerx, row), BACKGROUND_RGB)

    def test_all_moves_render_during_animation_and_restore_clip(self):
        surface = pygame.Surface((1000, 700))
        for move in 'RLUDFB':
            animator = Animator()
            animator.enqueue(move)
            animator.update(.15)
            clip = pygame.Rect(10, 10, 980, 680)
            surface.set_clip(clip)
            draw_unwrapped(surface, animator, show_paths=True)
            self.assertEqual(surface.get_clip(), clip)

    def test_sticker_edges_stay_on_two_horizontal_grid_lines(self):
        destination = pygame.Rect(0, 0, 1200, 700)
        for position, normal, points in slot_regions(*UNWRAP_SIZE):
            with self.subTest(position=position, normal=normal):
                polygon = _unwrapped_polygon(points, destination)[1]
                self.assertEqual(len({y for _, y in polygon}), 2)
                width = max(x for x, _ in polygon) - min(x for x, _ in polygon)
                expected = 200 if normal[2] and all(position[:2]) else 100
                self.assertAlmostEqual(width, expected, delta=3)

    def test_sticker_centers_round_trip_to_same_slot(self):
        size = (1000, 700)
        destination = _unwrapped_destination(size)
        for position, normal, points in slot_regions(*UNWRAP_SIZE):
            center = tuple(sum(p[i] for p in points) / len(points) for i in (0, 1))
            shown = unwrapped_screen_point(center, destination)
            actual, coordinates = unwrapped_pointer(shown, size)
            self.assertEqual(slot_at(actual, coordinates), (position, normal))
