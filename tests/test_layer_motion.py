import os
import unittest
from copy import deepcopy

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from flat_rubik.cube import Cube, FACE_NORMALS
from flat_rubik.layer_motion import layer_shapes, moving_cubies
from flat_rubik.projection import mobile_shapes
from flat_rubik.geometry import geometrie_centre


class LayerMotionTests(unittest.TestCase):
    def setUp(self):
        import pygame
        self.pygame = pygame
        self.size = (480, 480)

    def mask(self, polygon):
        pygame = self.pygame
        surface = pygame.Surface(self.size)
        surface.fill((0, 0, 0))
        pygame.draw.polygon(surface, (255, 255, 255), polygon)
        return pygame.mask.from_threshold(surface, (255, 255, 255), (1, 1, 1, 255))

    def interior(self, mask):
        # True one-pixel erosion, independent of polygon stroke orientation.
        result = mask.copy()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                shifted = self.pygame.mask.Mask(self.size)
                shifted.draw(mask, (dx, dy))
                result = result.overlap_mask(shifted, (0, 0))
        return result

    def test_all_faces_directions_no_overlapping_interiors(self):
        pygame = self.pygame
        cube = Cube()
        cube.apply("R U F' L D2 B R'")  # identities/colors cannot affect geometry
        for face in FACE_NORMALS:
            for suffix in ("", "'", "2"):
                move = face + suffix
                target = deepcopy(cube)
                target.move(move)
                for t in (.05, .125, .25, .375, .5, .625, .75, .875, .95):
                    with self.subTest(move=move, t=t):
                        occupied = pygame.mask.Mask(self.size)
                        shapes = layer_shapes(cube, target, move, t, *self.size)
                        self.assertEqual(len(shapes), 48)
                        pieces = {}
                        for key, (_, polygon) in shapes.items():
                            pieces.setdefault(key[0], pygame.mask.Mask(self.size)).draw(self.mask(polygon), (0, 0))
                        for key, full_mask in pieces.items():
                            mask = self.interior(full_mask)
                            overlap = occupied.overlap_area(mask, (0, 0))
                            self.assertEqual(overlap, 0, (move, t, key, overlap))
                            occupied.draw(mask, (0, 0))
                        # No mobile cell may intrude into any fixed center.
                        for center in geometrie_centre(*self.size).values():
                            surface = pygame.Surface(self.size)
                            surface.fill((0, 0, 0))
                            if center["tip"] == "poligon":
                                mask = self.interior(self.mask(center["puncte"]))
                            else:
                                radius = center.get("raza", center.get("raza_exterioara"))
                                width = 0 if center["tip"] == "cerc" else radius - center["raza_interioara"]
                                pygame.draw.circle(surface, (255, 255, 255), center["centru"], radius, width)
                                mask = pygame.mask.from_threshold(surface, (255, 255, 255), (1, 1, 1, 255))
                            self.assertEqual(occupied.overlap_area(mask, (0, 0)), 0)

    def test_endpoints_approach_the_correct_sticker_shapes_without_a_jump(self):
        cube = Cube()
        for face in FACE_NORMALS:
            for suffix in ("", "'", "2"):
                target = deepcopy(cube)
                target.move(face + suffix)
                for t, expected in ((.000001, cube), (.999999, target)):
                    frame = layer_shapes(cube, target, face + suffix, t, *self.size)
                    ideal = mobile_shapes(expected, *self.size)
                    for key, (_, polygon) in frame.items():
                        a, b = self.mask(polygon), self.mask(ideal[key][1])
                        for inside, other in ((self.interior(a), b), (self.interior(b), a)):
                            overlap = inside.overlap_area(other, (0, 0))
                            self.assertGreaterEqual(overlap, inside.count() * .99,
                                                    (face + suffix, t, key, inside.count(), overlap))

    def test_colors_of_each_cubie_remain_glued(self):
        cube = Cube()
        for face in FACE_NORMALS:
            for suffix in ("", "'", "2"):
                target = deepcopy(cube)
                target.move(face + suffix)
                for t in (.1, .3, .5, .7, .9):
                    shapes = layer_shapes(cube, target, face + suffix, t, 800, 800)
                    for cubie in moving_cubies(cube, face):
                        boundaries = [set((round(x, 5), round(y, 5)) for x, y in shapes[cubie.id, color][1])
                                      for color in cubie.stickers.values()]
                        connected = {0}
                        while True:
                            expanded = connected | {j for j, boundary in enumerate(boundaries)
                                                      if any(len(boundary & boundaries[i]) >= 2 for i in connected)}
                            if expanded == connected:
                                break
                            connected = expanded
                        self.assertEqual(len(connected), len(boundaries), (face + suffix, t, cubie.id))


if __name__ == "__main__":
    unittest.main()
