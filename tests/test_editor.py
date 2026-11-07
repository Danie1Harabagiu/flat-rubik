import os
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from flat_rubik.editor import ColorEditor, COLOR_CYCLE, slot_at, slot_regions
from flat_rubik.cube import Cube, FACE_NORMALS, scramble
from flat_rubik.state import facelets, cube_from_facelets, _position
from flat_rubik.animation import Animator


class StateValidationTests(unittest.TestCase):
    def test_legal_states_reconstruct_exact_identities_and_orientation(self):
        cube = Cube()
        for move in scramble(300, random.Random(42)):
            cube.move(move)
            self.assertEqual(cube_from_facelets(facelets(cube)).snapshot(), cube.snapshot())

    def test_incomplete_colors_and_fixed_centers(self):
        colors = facelets(Cube())
        colors.pop(next(iter(colors)))
        with self.assertRaisesRegex(ValueError, "54"):
            cube_from_facelets(colors)
        colors = facelets(Cube())
        n = FACE_NORMALS["F"]
        colors[n, n] = "verde"
        with self.assertRaisesRegex(ValueError, "Centrele"):
            cube_from_facelets(colors)
        colors = facelets(Cube())
        colors[(1, 1, 0), (1, 0, 0)] = "rosu"
        with self.assertRaisesRegex(ValueError, "9"):
            cube_from_facelets(colors)

    def test_one_flipped_edge_is_impossible(self):
        colors = facelets(Cube())
        p = _position("UF")
        a, b = [(p, FACE_NORMALS[f]) for f in "UF"]
        colors[a], colors[b] = colors[b], colors[a]
        with self.assertRaisesRegex(ValueError, "muchie este intoarsa"):
            cube_from_facelets(colors)

    def test_twisted_and_mirrored_corner_are_impossible(self):
        keys = [(_position("URF"), FACE_NORMALS[f]) for f in "URF"]
        colors = facelets(Cube())
        original = [colors[k] for k in keys]
        colors.update(zip(keys, original[1:] + original[:1]))
        with self.assertRaisesRegex(ValueError, "colt este rasucit"):
            cube_from_facelets(colors)
        colors = facelets(Cube())
        colors[keys[1]], colors[keys[2]] = colors[keys[2]], colors[keys[1]]
        with self.assertRaisesRegex(ValueError, "oglinda"):
            cube_from_facelets(colors)

    def test_odd_permutation_duplicate_and_opposite_edge_colors(self):
        colors = facelets(Cube())
        a = [(_position("UR"), FACE_NORMALS[f]) for f in "UR"]
        b = [(_position("UF"), FACE_NORMALS[f]) for f in "UF"]
        for x, y in zip(a, b):
            colors[x], colors[y] = colors[y], colors[x]
        with self.assertRaisesRegex(ValueError, "schimbate imposibil"):
            cube_from_facelets(colors)
        colors = facelets(Cube())
        colors[_position("UL"), FACE_NORMALS["L"]] = "verde"
        colors[_position("DR"), FACE_NORMALS["R"]] = "albastru"
        with self.assertRaisesRegex(ValueError, "apare de doua ori"):
            cube_from_facelets(colors)
        colors = facelets(Cube())
        a, b = (_position("UR"), FACE_NORMALS["R"]), (_position("DR"), FACE_NORMALS["D"])
        colors[a], colors[b] = colors[b], colors[a]
        with self.assertRaisesRegex(ValueError, "Combinatie imposibila"):
            cube_from_facelets(colors)


class EditorTests(unittest.TestCase):
    def mobile_sample(self, size=(800, 800)):
        p, n, polygon = slot_regions(*size)[0]
        point = tuple(sum(v[i] for v in polygon) / len(polygon) for i in (0, 1))
        return (p, n), point

    def test_surface_hit_testing_and_locked_centers(self):
        editor = ColorEditor()
        editor.begin(Cube())
        for size in ((800, 800), (400, 600), (1200, 500)):
            for p, n, polygon in slot_regions(*size):
                sample = tuple(sum(v[i] for v in polygon) / len(polygon) for i in (0, 1))
                self.assertEqual(slot_at(sample, size), (p, n))
        before = editor.colors.copy()
        editor.color = "verde"
        self.assertFalse(editor.paint((400, 400), 1, (800, 800)))
        self.assertEqual(editor.colors, before)

    def test_paint_undo_restore_and_cancel_do_not_modify_live_cube(self):
        cube = Cube()
        cube.apply("R U F2")
        initial = cube.snapshot()
        editor = ColorEditor()
        editor.begin(cube)
        slot, point = self.mobile_sample()
        editor.color = next(c for c in ("rosu", "verde", "alb") if c != editor.colors[slot])
        editor.paint(point, 1, (800, 800))
        painted = editor.colors[slot]
        self.assertEqual(editor.colors[slot], editor.color)
        self.assertEqual(cube.snapshot(), initial)
        editor.paint(point, 3, (800, 800))
        self.assertEqual(editor.colors, facelets(cube))
        editor.undo()
        self.assertEqual(editor.colors[slot], painted)
        editor.cancel()
        self.assertFalse(editor.editing)
        self.assertEqual(editor.colors, facelets(cube))

    def test_clicks_cycle_all_six_colors_without_palette_and_reverse(self):
        editor = ColorEditor()
        editor.begin(Cube())
        for p, n, polygon in slot_regions(800, 800):
            slot = p, n
            point = tuple(sum(v[i] for v in polygon) / len(polygon) for i in (0, 1))
            original = editor.colors[slot]
            seen = set()
            for _ in range(6):
                self.assertTrue(editor.paint(point, 1, (800, 800)))
                seen.add(editor.colors[slot])
            self.assertEqual(seen, set(COLOR_CYCLE))
            self.assertEqual(editor.colors[slot], original)
            editor.paint(point, 3, (800, 800))
            self.assertEqual(editor.colors[slot], COLOR_CYCLE[(COLOR_CYCLE.index(original) - 1) % 6])
            editor.paint(point, 1, (800, 800))
            self.assertEqual(editor.colors[slot], original)

    def test_random_valid_applies_to_actual_rotatable_cubies(self):
        editor = ColorEditor()
        editor.begin(Cube())
        editor.randomize()
        expected = cube_from_facelets(editor.colors)
        applied = editor.apply()
        self.assertFalse(editor.editing)
        animator = Animator()
        animator.enqueue("R U")
        animator.update(.1)
        animator.set_cube(applied)
        self.assertEqual(animator.pending, 0)
        self.assertEqual(animator.cube.snapshot(), expected.snapshot())
        animator.enqueue("R R'")
        animator.update(1)
        self.assertEqual(animator.cube.snapshot(), expected.snapshot())

    def test_invalid_draft_stays_open_and_persists_separately(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "colors.json"
            editor = ColorEditor(path)
            editor.begin(Cube())
            editor.randomize()
            valid = editor.apply()
            editor.begin(valid)
            slot, point = self.mobile_sample()
            editor.color = next(c for c in ("rosu", "verde") if c != editor.colors[slot])
            editor.paint(point, 1, (800, 800))
            self.assertIsNone(editor.apply())
            self.assertTrue(editor.editing)
            self.assertTrue(editor.error)
            loaded = ColorEditor(path)
            self.assertEqual(loaded.startup_cube.snapshot(), valid.snapshot())
            loaded.begin(loaded.startup_cube)
            self.assertEqual(loaded.colors, editor.colors)

    def test_pygame_paints_full_surface_and_invalid_apply_keeps_live_cube(self):
        import pygame
        from flat_rubik.app import run
        from flat_rubik.ui import layout
        from flat_rubik.renderer import draw, CULORI_RGB
        editor = ColorEditor()
        animator = Animator()
        before = animator.cube.snapshot()
        slot, point = self.mobile_sample()
        _, _, _, _, actions, _ = layout((1080, 800))
        events = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=actions["edit"].center, button=1),
                  pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=point, button=1),
                  pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=actions["pause"].center, button=1)]
        with patch("flat_rubik.app.ColorEditor", return_value=editor), patch("flat_rubik.app.Animator", return_value=animator), patch("pygame.event.get", return_value=events):
            run(max_frames=1, session_path=None)
        self.assertTrue(editor.editing)
        self.assertTrue(editor.error)
        self.assertEqual(animator.cube.snapshot(), before)
        pygame.init()
        try:
            surface = pygame.Surface((800, 800))
            draw(surface, animator=animator, facelets=editor.colors)
            sample = tuple(round(v) for v in point)
            self.assertEqual(tuple(surface.get_at(sample))[:3], CULORI_RGB[editor.color])
        finally:
            pygame.quit()

    def test_invalid_file_and_write_failure_do_not_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "colors.json"
            path.write_text('{"version":1,"draft":[]}', encoding="utf-8")
            editor = ColorEditor(path)
            self.assertEqual(editor.colors, facelets(Cube()))
            editor.begin(Cube())
            with patch.object(Path, "write_text", side_effect=OSError("read only")):
                editor.randomize()
            self.assertIn("esuat", editor.message)

    def test_pygame_applies_entered_colors_then_rotates_that_state(self):
        import pygame
        from flat_rubik.app import run
        from flat_rubik.ui import layout
        target = Cube()
        target.apply("R U F2 L' D B")
        editor = ColorEditor()
        editor.colors = facelets(target)
        editor.resume_draft = True
        animator = Animator()
        actions = layout((1080, 800))[4]
        events = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=actions["edit"].center, button=1),
                  pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=actions["pause"].center, button=1),
                  pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(400, 400), button=1)]
        with patch("flat_rubik.app.ColorEditor", return_value=editor), patch("flat_rubik.app.Animator", return_value=animator), patch("pygame.event.get", return_value=events):
            run(max_frames=1, session_path=None)
        self.assertFalse(editor.editing)
        self.assertEqual(animator.cube.snapshot(), target.snapshot())
        animator.update(1)
        target.move("F")
        self.assertEqual(animator.cube.snapshot(), target.snapshot())


if __name__ == "__main__":
    unittest.main()
