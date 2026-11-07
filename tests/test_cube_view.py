import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from flat_rubik.animation import Animator
from flat_rubik.cube_view import animated_point, view_regions, cube_face_at, rotate_point


class CubeViewTests(unittest.TestCase):
    def test_picking_tracks_faces_after_camera_rotation(self):
        from flat_rubik.cube import FACE_NORMALS
        for yaw, pitch in ((-.55, .45), (2.6, -.45)):
            for face, normal in FACE_NORMALS.items():
                visible = rotate_point(rotate_point(normal, 1, yaw), 0, pitch)
                if visible[2] <= 0:
                    continue
                center = rotate_point(rotate_point(tuple(v * 1.485 for v in normal), 1, yaw), 0, pitch)
                scale = 564 / 5.4
                point = (300 + center[0] * scale, 296 - center[1] * scale)
                self.assertEqual(cube_face_at(point, (600, 600), Animator(), yaw, pitch), face)
        self.assertIsNone(cube_face_at((0, 0), (600, 600), Animator()))

    def test_phone_tap_turns_face_but_drag_only_orbits(self):
        from unittest.mock import patch
        from flat_rubik.app import run
        from flat_rubik.editor import ColorEditor
        original = pygame.display.set_mode
        for drag in (False, True):
            animator = Animator(duration=10)
            from flat_rubik.ui import layout
            area = layout((390, 844))[0].copy()
            area.y += 46
            area.h -= 46
            _, cube = view_regions(area, "Ambele")
            start = cube.center
            expected = cube_face_at((start[0] - cube.x, start[1] - cube.y), cube.size, animator)
            self.assertIsNotNone(expected)
            batches = [[pygame.event.Event(pygame.FINGERDOWN, x=start[0] / 390, y=start[1] / 844, finger_id=7)]]
            if drag:
                batches.append([pygame.event.Event(pygame.FINGERMOTION, x=(start[0] + 40) / 390, y=start[1] / 844, finger_id=7)])
            batches.append([pygame.event.Event(pygame.FINGERUP, x=(start[0] + (40 if drag else 0)) / 390, y=start[1] / 844, finger_id=7)])
            with patch('pygame.display.set_mode', side_effect=lambda *args: original((390, 844))), \
                 patch('flat_rubik.app.Animator', return_value=animator), \
                 patch('flat_rubik.app.ColorEditor', side_effect=lambda *args: ColorEditor()), \
                 patch('pygame.event.get', side_effect=batches):
                run(max_frames=len(batches), session_path=None)
            self.assertEqual(animator.current, None if drag else expected)

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
