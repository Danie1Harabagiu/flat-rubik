"""Eight-spoke layout reconstructed from the user's reference photographs.

Each noncentral cubie occupies one compound region with 2 or 3 stickers.
Dimensions are visual estimates; topology and color adjacency follow the photos.
Cubies remain owned exclusively by Cube.
"""
from dataclasses import dataclass
from functools import lru_cache
import math

from flat_rubik.geometry import sector_inel, SPOKE_HALF_ANGLE, MIDDLE_RADII, INNER_RADII, OUTER_RADII


@dataclass(frozen=True)
class StickerView:
    cubie_id: str
    color: str
    position: tuple
    normal: tuple

    @property
    def key(self):
        return self.cubie_id, self.color


def project(cube):
    return [StickerView(c.id, color, c.position, normal)
            for c in cube.cubies for normal, color in c.stickers.items()]


@lru_cache(maxsize=4096)
def slot_polygon(position, normal, width, height):
    """Map a physical slot to a subregion of its shared cubie footprint.

    Front/back stickers span the spoke. Adjacent lateral colors split its
    width at diagonal positions, matching the reference's corner/edge seams.
    """
    x, y, z = position
    scale = min(width, height) / 800
    cx, cy = width / 2, height / 2
    angle = math.atan2(-y, x)
    half_width = SPOKE_HALF_ANGLE
    start, end = angle - half_width, angle + half_width
    if normal[2]:
        inner, outer = INNER_RADII[:2] if normal[2] == 1 else OUTER_RADII[1:]
    else:
        inner, outer = {1: INNER_RADII[1:], 0: MIDDLE_RADII, -1: OUTER_RADII[:2]}[z]
        if x and y:
            face_angle = math.atan2(-normal[1], normal[0])
            offset = (face_angle - angle + math.pi) % (2 * math.pi) - math.pi
            if offset < 0:
                end = angle
            else:
                start = angle
    return sector_inel(cx, cy, inner * scale, outer * scale, start, end,
                       segmente=max(24, round(24 * scale)))


def mobile_shapes(cube, width, height):
    return {s.key: (s.color, slot_polygon(s.position, s.normal, width, height))
            for s in project(cube) if sum(abs(v) for v in s.position) > 1}


@lru_cache(maxsize=2048)
def cubie_polygon(position, width, height):
    """One outside boundary enclosing all colors of a physical mobile cubie."""
    x, y, z = position
    radii = {1: INNER_RADII, 0: MIDDLE_RADII, -1: OUTER_RADII}[z]
    scale = min(width, height) / 800
    angle = math.atan2(-y, x)
    return sector_inel(width / 2, height / 2, radii[0] * scale, radii[-1] * scale,
                       angle - SPOKE_HALF_ANGLE, angle + SPOKE_HALF_ANGLE,
                       segmente=max(48, round(48 * scale)))
