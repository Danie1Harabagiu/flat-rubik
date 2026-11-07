"""One injective planar deformation for a whole rotating Rubik layer.

Side layers live in a square annulus mapped to the circular drawing. Rotating
its square-polar angle preserves the central hole, all gaps, and disjointness.
Each physical cubie is a single cell; its colors partition one shared fan.
There are no independently moving stickers and no size contraction.
"""
from bisect import bisect_right
import math

from flat_rubik.cube import FACE_NORMALS, parse_move
from flat_rubik.projection import mobile_shapes, cubie_polygon
from flat_rubik.geometry import INNER_RADII, MIDDLE_RADII, OUTER_RADII, SPOKE_HALF_ANGLE

GRID = (-1.5, -1.45, -1, -.55, -.45, 0, .45, .55, 1, 1.45, 1.5)
_HALF = math.degrees(SPOKE_HALF_ANGLE)
ANGLES = (-68, -45 - _HALF, -45, -45 + _HALF, -_HALF, 0,
          _HALF, 45 - _HALF, 45, 45 + _HALF, 68)
RADII = (INNER_RADII[0] - 4, *INNER_RADII, MIDDLE_RADII[0], sum(MIDDLE_RADII) / 2,
         MIDDLE_RADII[1], *OUTER_RADII, OUTER_RADII[-1] + 4)


def ease(t):
    t = max(0, min(1, t))
    return t ** 3 * (t * (6 * t - 15) + 10)


def _map(value, stops):
    i = max(0, min(len(GRID) - 2, bisect_right(GRID, value) - 1))
    t = (value - GRID[i]) / (GRID[i + 1] - GRID[i])
    return stops[i] * (1 - t) + stops[i + 1] * t


def _twist(point, angle):
    """Conjugate a circle rotation by an injective square-to-disk mapping."""
    x, y = point
    radius = max(abs(x), abs(y))
    theta = math.atan2(y, x) + angle
    c, s = math.cos(theta), math.sin(theta)
    factor = radius / max(abs(c), abs(s), 1e-12)
    return c * factor, s * factor


def _world(point, normal, width, height):
    theta = math.atan2(-normal[1], normal[0]) + math.radians(_map(point[0], ANGLES))
    radius = _map(point[1], RADII) * min(width, height) / 800
    return width / 2 + radius * math.cos(theta), height / 2 + radius * math.sin(theta)


def _cell(position, normal):
    x, y, z = position
    return x * normal[1] - y * normal[0], -z


def _partition(position, sticker_normal):
    """Start and length of a color's clockwise interval on a cell perimeter."""
    x, y, z = position
    if sticker_normal[2]:
        return (3.5, 2) if sticker_normal[2] == 1 else (1.5, 2)
    if not (x and y):
        return (1.5, 2) if z == 1 else (3.5, 2)
    a = math.atan2(-y, x)
    b = math.atan2(-sticker_normal[1], sticker_normal[0])
    right = (b - a + math.pi) % (2 * math.pi) - math.pi > 0
    if z == 1:
        return (1.5 if right else 2.5), 1
    if z == -1:
        return (.5 if right else 3.5), 1
    return (.5 if right else 2.5), 2


def _perimeter(t):
    t %= 4
    if t < 1:
        return -.45 + .9 * t, -.45
    if t < 2:
        return .45, -.45 + .9 * (t - 1)
    if t < 3:
        return .45 - .9 * (t - 2), .45
    return -.45, .45 - .9 * (t - 3)


def _fan(start, length):
    """Sample shared seams identically and include every square corner."""
    a, b = _perimeter(start), _perimeter(start + length)
    result = [(a[0] * i / 16, a[1] * i / 16) for i in range(17)]
    stops = [start] + [float(i) for i in range(math.floor(start) + 1, math.ceil(start + length))] + [start + length]
    for low, high in zip(stops, stops[1:]):
        count = max(1, math.ceil((high - low) * 24))
        result.extend(_perimeter(low + (high - low) * i / count) for i in range(1, count + 1))
    result.extend((b[0] * i / 16, b[1] * i / 16) for i in range(15, -1, -1))
    return result


def moving_cubies(cube, face):
    normal = FACE_NORMALS[face]
    return [c for c in cube.cubies if c.kind != "center" and
            sum(a * b for a, b in zip(c.position, normal)) == 1]


def layer_shapes(cube, target, move, progress, width, height):
    result = mobile_shapes(cube, width, height)
    if progress <= 0:
        return result
    if progress >= 1:
        return mobile_shapes(target, width, height)
    face, turns = parse_move(move)
    normal = FACE_NORMALS[face]
    t = ease(progress)
    angle = -turns * math.pi / 2 * t
    movers = moving_cubies(cube, face)
    if normal[2]:
        # Front and back rings can rotate as genuinely rigid 2D assemblies.
        theta = -angle * normal[2]
        c, s = math.cos(theta), math.sin(theta)
        cx, cy = width / 2, height / 2
        for cubie in movers:
            for color in cubie.stickers.values():
                key = cubie.id, color
                polygon = result[key][1]
                result[key] = color, [(cx + (x - cx) * c - (y - cy) * s,
                                       cy + (x - cx) * s + (y - cy) * c) for x, y in polygon]
        return result
    destinations = {c.id: c for c in target.cubies}
    for cubie in movers:
        destination = destinations[cubie.id]
        col, row = _cell(cubie.position, normal)
        target_normals = {color: n for n, color in destination.stickers.items()}
        partitions = sorted((_partition(cubie.position, n)[0] % 4, color,
                             _partition(cubie.position, n)[1]) for n, color in cubie.stickers.items())
        first_start, first_color, _ = partitions[0]
        target_start = (_partition(destination.position, target_normals[first_color])[0] + turns) % 4
        offset = (target_start - first_start + 2) % 4 - 2
        start = first_start + offset * t
        for _, color, source_length in partitions:
            target_length = _partition(destination.position, target_normals[color])[1]
            length = source_length * (1 - t) + target_length * t
            polygon = [_world(_twist((col + x, row + y), angle), normal, width, height)
                       for x, y in _fan(start, length)]
            result[cubie.id, color] = color, polygon
            start += length
    return result


def layer_paths(cube, move, width, height, samples=40):
    face, turns = parse_move(move)
    normal = FACE_NORMALS[face]
    paths = []
    for cubie in moving_cubies(cube, face):
        if normal[2]:
            a = math.atan2(-cubie.position[1], cubie.position[0])
            radii = INNER_RADII if normal[2] == 1 else OUTER_RADII
            radius = (radii[0] + radii[-1]) / 2 * min(width, height) / 800
            paths.append([(width / 2 + radius * math.cos(a + normal[2] * turns * math.pi / 2 * i / samples),
                           height / 2 + radius * math.sin(a + normal[2] * turns * math.pi / 2 * i / samples))
                          for i in range(samples + 1)])
        else:
            cell = _cell(cubie.position, normal)
            paths.append([_world(_twist(cell, -turns * math.pi / 2 * i / samples), normal, width, height)
                          for i in range(samples + 1)])
    return paths


def layer_outlines(cube, target, move, progress, width, height):
    if target is not None and progress >= 1:
        cube = target
    outlines = {c.id: cubie_polygon(c.position, width, height) for c in cube.cubies if c.kind != "center"}
    if target is None or progress <= 0 or progress >= 1:
        return outlines
    face, turns = parse_move(move)
    normal = FACE_NORMALS[face]
    angle = -turns * math.pi / 2 * ease(progress)
    for cubie in moving_cubies(cube, face):
        if normal[2]:
            theta = -angle * normal[2]
            c, s = math.cos(theta), math.sin(theta)
            cx, cy = width / 2, height / 2
            outlines[cubie.id] = [(cx + (x - cx) * c - (y - cy) * s,
                                   cy + (x - cx) * s + (y - cy) * c) for x, y in outlines[cubie.id]]
        else:
            col, row = _cell(cubie.position, normal)
            outlines[cubie.id] = [_world(_twist((col + x, row + y), angle), normal, width, height)
                                 for x, y in (_perimeter(i / 24) for i in range(96))]
    return outlines
