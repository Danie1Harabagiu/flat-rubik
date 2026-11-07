import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from flat_rubik.animation import Animator
from flat_rubik.cube import Cube
from flat_rubik.geometry import geometrie_centre, MIDDLE_RADII
from flat_rubik.layer_motion import layer_shapes
from flat_rubik.projection import mobile_shapes, project, slot_polygon


class DisplayTests(unittest.TestCase):
    def test_slots_unique_and_resize(self):
        cube = Cube()
        views = [s for s in project(cube) if sum(map(abs, s.position)) > 1]
        shapes = mobile_shapes(cube, 800, 800)
        self.assertEqual(len(shapes), 48)
        self.assertEqual(len({tuple(p) for _, p in shapes.values()}), 48)
        for s in views:
            small = slot_polygon(s.position, s.normal, 400, 400)
            large = slot_polygon(s.position, s.normal, 800, 800)
            for a, b in zip(small, large):
                self.assertLessEqual(math.dist(a, (b[0] / 2, b[1] / 2)), 1)
            for width, height in ((320, 700), (1600, 500)):
                self.assertTrue(all(0 <= x <= width and 0 <= y <= height
                                    for x, y in slot_polygon(s.position, s.normal, width, height)))

    def test_original_centers(self):
        centers = geometrie_centre(800, 800)
        self.assertEqual(len(centers), 6)
        self.assertEqual(centers["rosu"], dict(tip="cerc", centru=(400, 400), raza=44))
        self.assertEqual(centers["portocaliu"]["raza_interioara"], 300)
        for color in ("galben", "verde", "alb", "albastru"):
            self.assertEqual(centers[color]["tip"], "poligon")
            points = centers[color]["puncte"]
            radii = [math.dist(p, (400, 400)) for p in points]
            self.assertAlmostEqual(min(radii), MIDDLE_RADII[0], delta=1)
            self.assertAlmostEqual(max(radii), MIDDLE_RADII[1], delta=1)

    def test_reference_cubies_share_boundaries(self):
        # Every physical mobile piece has one connected footprint, rather
        # than isolated colored bands. A corner joins three colored regions.
        for cubie in Cube().cubies:
            if cubie.kind == "center":
                continue
            shapes = [set(slot_polygon(cubie.position, n, 800, 800)) for n in cubie.stickers]
            connected = {0}
            while True:
                expanded = connected | {j for j, shape in enumerate(shapes)
                                          if any(len(shape & shapes[i]) >= 2 for i in connected)}
                if expanded == connected:
                    break
                connected = expanded
            self.assertEqual(len(connected), len(shapes), cubie.position)

    def test_reference_spokes_and_color_seams(self):
        def region(position, normal):
            polygon = slot_polygon(position, normal, 800, 800)
            radii = [math.dist(p, (400, 400)) for p in polygon]
            return min(radii), max(radii)
        # The front and rear edge stickers touch their lateral partners.
        self.assertAlmostEqual(region((0, 1, 1), (0, 0, 1))[1], 88, delta=1)
        self.assertAlmostEqual(region((0, 1, 1), (0, 1, 0))[0], 88, delta=1)
        self.assertAlmostEqual(region((0, 1, -1), (0, 0, -1))[0], 246, delta=1)
        self.assertAlmostEqual(region((0, 1, -1), (0, 1, 0))[1], 246, delta=1)
        # On the top-right diagonal, yellow is left of green.
        yellow = slot_polygon((1, 1, 0), (0, 1, 0), 800, 800)
        green = slot_polygon((1, 1, 0), (1, 0, 0), 800, 800)
        self.assertLess(sum(x for x, y in yellow), sum(x for x, y in green))

    def test_queue_commits_and_reset(self):
        animator = Animator()
        animator.enqueue("R U' F2")
        animator.update(.15)
        self.assertEqual(animator.cube.snapshot(), Cube().snapshot())
        self.assertEqual(animator.pending, 3)
        self.assertEqual(len(animator.shapes(800, 800)), 48)
        animator.update(.76)
        expected = Cube()
        expected.apply("R U' F2")
        self.assertEqual(animator.cube.snapshot(), expected.snapshot())
        self.assertEqual(animator.pending, 0)
        self.assertEqual(animator.history, ["R", "U'", "F2"])
        animator.enqueue("B")
        animator.update(.1)
        animator.reset()
        self.assertTrue(animator.cube.solved)
        self.assertEqual(animator.pending, 0)

    def test_morph_endpoints_and_continuity(self):
        animator = Animator()
        animator.enqueue("F")
        animator.update(0)
        start = mobile_shapes(animator.cube, 800, 800)
        end = mobile_shapes(animator.target, 800, 800)
        for key, (_, source) in start.items():
            target = end[key][1]
            self.assertEqual(layer_shapes(animator.cube, animator.target, animator.current, 0, 800, 800)[key][1], source)
            self.assertEqual(layer_shapes(animator.cube, animator.target, animator.current, 1, 800, 800)[key][1], target)
            a = layer_shapes(animator.cube, animator.target, animator.current, .5, 800, 800)[key][1]
            b = layer_shapes(animator.cube, animator.target, animator.current, .50001, 800, 800)[key][1]
            self.assertTrue(all(math.dist(p, q) < .1 for p, q in zip(a, b)))

    def test_pygame_render_and_application_smoke(self):
        import pygame
        from flat_rubik.renderer import draw, CULORI_RGB, BACKGROUND_RGB
        from flat_rubik.app import run
        pygame.init()
        animator = Animator()
        animator.enqueue("R U F2")
        for size in ((800, 800), (400, 600), (1200, 500)):
            screen = pygame.display.set_mode(size)
            animator.update(.1)
            screen.fill(BACKGROUND_RGB)
            draw(screen, animator=animator)
            red_sample = (size[0] // 2, size[1] // 2 + round(22 * min(size) / 800))
            self.assertEqual(tuple(screen.get_at(red_sample))[:3], CULORI_RGB["rosu"])
        pygame.quit()
        run(max_frames=3, session_path=None)


if __name__ == "__main__":
    unittest.main()
