import unittest
from unittest.mock import patch

import pygame

from flat_rubik.animation import Animator
from flat_rubik.editor import slot_at, slot_regions
from flat_rubik.flat_view import (
    UNWRAP_SIZE, UNWRAP_COLUMNS, UNWRAP_RADIAL_UNITS, _unwrapped_destination, _unwrapped_polygon,
    UNWRAPPED, draw_flat, draw_unwrapped, unwrapped_pointer, unwrapped_screen_point,
)
from flat_rubik.cube import Cube
from flat_rubik.projection import cubie_polygon
from flat_rubik.renderer import BACKGROUND_RGB, CULORI_RGB


class UnwrappedTests(unittest.TestCase):
    def test_cut_pieces_are_complete_at_both_ends_with_gaps(self):
        size = (1000, 700)
        surface = pygame.Surface(size)
        draw_unwrapped(surface, Animator())
        destination = _unwrapped_destination(size)
        cell = destination.w / UNWRAP_COLUMNS

        def pixel(x, row):
            return surface.get_at((round(x), round(destination.y + row * destination.h / UNWRAP_RADIAL_UNITS)))[:3]

        for edge in (destination.left, destination.right):
            for row in (2.5, 4, 5.5):
                self.assertEqual(pixel(edge - cell / 4, row), CULORI_RGB['verde'])
                self.assertEqual(pixel(edge + cell / 4, row), CULORI_RGB['alb'])
                self.assertIsNotNone(unwrapped_pointer(
                    (edge - cell / 4, destination.y + row * destination.h / UNWRAP_RADIAL_UNITS), size))
        self.assertEqual(pixel(destination.left + cell / 2, 2.5), BACKGROUND_RGB)
        for row in (1, 3, 5, 7):
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

    def test_all_mobile_cubies_have_equal_square_dimensions(self):
        destination = _unwrapped_destination((1000, 700))
        expected = destination.w / UNWRAP_COLUMNS
        for cubie in Cube().cubies:
            if cubie.kind == 'center':
                continue
            points = cubie_polygon(cubie.position, *UNWRAP_SIZE)
            polygon = _unwrapped_polygon(points, destination)[1]
            width = max(x for x, _ in polygon) - min(x for x, _ in polygon)
            height = max(y for _, y in polygon) - min(y for _, y in polygon)
            self.assertAlmostEqual(width, expected, delta=3)
            self.assertAlmostEqual(height, expected, delta=3)

    def test_sticker_edges_stay_on_two_horizontal_grid_lines(self):
        destination = pygame.Rect(0, 0, 1200, 700)
        for position, normal, points in slot_regions(*UNWRAP_SIZE):
            with self.subTest(position=position, normal=normal):
                polygon = _unwrapped_polygon(points, destination)[1]
                self.assertEqual(len({y for _, y in polygon}), 2)
                width = max(x for x, _ in polygon) - min(x for x, _ in polygon)
                expected = 75 if not normal[2] and all(position[:2]) else 150
                self.assertAlmostEqual(width, expected, delta=3)

    def test_sticker_centers_round_trip_to_same_slot(self):
        size = (1000, 700)
        for equal in (True, False):
            destination = _unwrapped_destination(size, equal_pieces=equal)
            for position, normal, points in slot_regions(*UNWRAP_SIZE):
                center = tuple(sum(p[i] for p in points) / len(points) for i in (0, 1))
                shown = unwrapped_screen_point(center, destination, equal_pieces=equal)
                actual, coordinates = unwrapped_pointer(shown, size, equal_pieces=equal)
                self.assertEqual(slot_at(actual, coordinates), (position, normal))

    def test_previous_layout_keeps_wider_corner_pieces(self):
        destination = pygame.Rect(0, 0, 1200, 700)
        for position, normal, points in slot_regions(*UNWRAP_SIZE):
            polygon = _unwrapped_polygon(points, destination, equal_pieces=False)[1]
            width = max(x for x, _ in polygon) - min(x for x, _ in polygon)
            expected = 200 if normal[2] and all(position[:2]) else 100
            self.assertAlmostEqual(width, expected, delta=3)

    def test_button_switches_layout_without_changing_cube(self):
        from flat_rubik.app import run
        from flat_rubik.ui import layout, zoom_buttons

        animator = Animator()
        before = animator.cube.snapshot()
        board = layout((1080, 800))[0].copy()
        board.y += 46
        board.h -= 46
        button = zoom_buttons(board, UNWRAPPED, fit_mode='auto')['pieces']
        events = [
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v, mod=0)],
            [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=button.center, button=1)],
        ]
        with patch('flat_rubik.app.Animator', return_value=animator), \
                patch('pygame.event.get', side_effect=events), \
                patch('flat_rubik.app.draw_flat', wraps=draw_flat) as draw:
            run(max_frames=2, session_path=None)
        self.assertEqual([call.kwargs['equal_pieces'] for call in draw.call_args_list], [True, False])
        self.assertEqual(animator.cube.snapshot(), before)
