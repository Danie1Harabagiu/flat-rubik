"""An independent 45-degree puzzle: eight-slot cycles with attached color fans.

Edges and corners may exchange slots. Each piece retains its identity, colors,
cyclic color order and an orientation in eighth-turns. This is NOT a physical
Rubik state; it must never be fed into the classic facelet validator.
"""
import math

from flat_rubik.animation import Animator
from flat_rubik.cube import Cube, FACE_NORMALS, parse_move
from flat_rubik.geometry import INNER_RADII, MIDDLE_RADII, OUTER_RADII, SPOKE_HALF_ANGLE
from flat_rubik.layer_motion import _cell, _partition, _perimeter, _twist, _world, ease, moving_cubies


def parse_twist(move):
    if isinstance(move, str) and len(move) == 3 and move[1:] == "2'":
        face, _ = parse_move(move[0])
        return face, -2
    return parse_move(move)


def inverse_twist(move):
    face, turns = parse_twist(move)
    return face + {1: "'", -1: "", 2: "2'", -2: "2"}[turns]


class Cube45(Cube):
    def __init__(self):
        super().__init__()
        self.homes = {c.id: c.position for c in self.cubies}
        self.orientations = {c.id: 0 for c in self.cubies}

    def move(self, move):
        face, turns = parse_twist(move)
        normal = FACE_NORMALS[face]
        for cubie in moving_cubies(self, face):
            if normal[2]:
                x, y = _twist(cubie.position[:2], -normal[2] * turns * math.pi / 4)
                cubie.position = round(x), round(y), cubie.position[2]
            else:
                col, row = _twist(_cell(cubie.position, normal), -turns * math.pi / 4)
                col, row = round(col), round(row)
                cubie.position = normal[0] + col * normal[1], normal[1] - col * normal[0], -row
                self.orientations[cubie.id] = (self.orientations[cubie.id] - turns) % 8

    @property
    def solved(self):
        return all(c.position == self.homes[c.id] and self.orientations[c.id] == 0 for c in self.cubies)

    def snapshot(self):
        return super().snapshot(), tuple(sorted(self.orientations.items()))


def _fan(start, length):
    a, b = _perimeter(start), _perimeter(start + length)
    points = [(a[0] * i / 12, a[1] * i / 12) for i in range(13)]
    count = round(length * 24)
    points.extend(_perimeter(start + length * i / count) for i in range(1, count + 1))
    points.extend((b[0] * i / 12, b[1] * i / 12) for i in range(11, -1, -1))
    return points


def _slot_world(position, point, width, height):
    x, y, z = position
    a, b = point
    radii = {1: INNER_RADII, 0: (MIDDLE_RADII[0], sum(MIDDLE_RADII) / 2, MIDDLE_RADII[1]), -1: OUTER_RADII}[z]
    r = radii[1]
    r += b / .45 * (radii[2] - radii[1] if b >= 0 else radii[1] - radii[0])
    theta = math.atan2(-y, x) + a / .45 * SPOKE_HALF_ANGLE
    r *= min(width, height) / 800
    return width / 2 + r * math.cos(theta), height / 2 + r * math.sin(theta)


def _clip(points, planes):
    """Clip a cell and all its colors to the same disjoint moving territory."""
    for nx, ny, bound in planes:
        result = []
        if not points:
            return []
        a = points[-1]
        da = a[0] * nx + a[1] * ny - bound
        for b in points:
            db = b[0] * nx + b[1] * ny - bound
            if (da <= 0) != (db <= 0):
                t = da / (da - db)
                result.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            if db <= 0:
                result.append(b)
            a, da = b, db
        points = result
    return points


def _sample_edges(points):
    result = []
    for a, b in zip(points, points[1:] + points[:1]):
        count = max(1, math.ceil(math.dist(a, b) / .04))
        result.extend((a[0] + (b[0] - a[0]) * i / count,
                       a[1] + (b[1] - a[1]) * i / count) for i in range(count))
    return result


class Puzzle45(Animator):
    step_degrees = 45

    def __init__(self, duration=1):
        super().__init__(cube=Cube45(), duration=duration)
        self.revision = 0
        self._cache = None

    @property
    def is_solved(self):
        return self.cube.solved

    def reset(self):
        self.set_cube(Cube45())

    def set_cube(self, cube):
        if not isinstance(cube, Cube45):
            raise ValueError("The 45-degree puzzle needs its own state")
        super().set_cube(cube)
        self.revision += 1
        self._cache = None

    def enqueue(self, moves):
        moves = moves.split() if isinstance(moves, str) else list(moves)
        for move in moves:
            parse_twist(move)
        self.queue.extend(moves)

    def update(self, dt):
        before = len(self.history)
        super().update(dt)
        self.revision += len(self.history) - before

    def _frame(self, width, height):
        cache_key = width, height, self.revision, self.current, self.elapsed, self.duration
        if self._cache is not None and self._cache[0] == cache_key:
            return self._cache[1]
        t = ease(self.elapsed / self.duration) if self.current else 0
        face, turns = parse_twist(self.current) if self.current else ("F", 0)
        normal = FACE_NORMALS[face]
        movers = {c.id for c in moving_cubies(self.cube, face)} if self.current else set()
        angle = -turns * math.pi / 4 * t
        centers = {c.id: _twist(_cell(c.position, normal), angle) for c in self.cube.cubies
                   if c.id in movers} if not normal[2] else {}
        shapes, outlines = {}, {}
        for cubie in self.cube.cubies:
            if cubie.kind == "center":
                continue
            phase = self.cube.orientations[cubie.id] / 2

            def points_for(start, length, perimeter_only=False):
                source = ([_perimeter(i / 24) for i in range(96)] if perimeter_only else _fan(start, length))
                if cubie.id not in movers:
                    return [_slot_world(cubie.position, p, width, height) for p in source]
                if normal[2]:
                    theta = -angle * normal[2]
                    c, s = math.cos(theta), math.sin(theta)
                    cx, cy = width / 2, height / 2
                    polygon = [_slot_world(cubie.position, p, width, height) for p in source]
                    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c)
                            for x, y in polygon]
                col, row = _cell(cubie.position, normal)
                center = _twist((col, row), angle)
                planes = [(other[0] - center[0], other[1] - center[1],
                           (other[0] ** 2 + other[1] ** 2 - center[0] ** 2 - center[1] ** 2) / 2
                           - .035 * math.dist(center, other))
                          for key, other in centers.items() if key != cubie.id]
                # A supporting line keeps the entire fixed center square clear.
                planes.append((-center[0], -center[1], -.48 * (abs(center[0]) + abs(center[1]))))
                destination = ([_perimeter(i / 24 - turns / 2 * t) for i in range(96)]
                               if perimeter_only else _fan(start - turns / 2 * t, length))
                # A shared cell map carries every color and the piece's outline.
                # Settle into the next slot rather than accumulating deformation.
                result = []
                for p, q in zip(source, destination):
                    a, b = _twist((col + p[0], row + p[1]), angle)
                    local = ((1 - t) * a + t * (center[0] + q[0]),
                             (1 - t) * b + t * (center[1] + q[1]))
                    result.append(local)
                return [_world(p, normal, width, height) for p in _sample_edges(_clip(result, planes))]

            for n, color in cubie.stickers.items():
                start, length = _partition(self.cube.homes[cubie.id], n)
                shapes[cubie.id, color] = color, points_for(start + phase, length)
            outlines[cubie.id] = points_for(0, 4, perimeter_only=True)
        result = shapes, outlines
        self._cache = cache_key, result
        return result

    def shapes(self, width, height):
        return self._frame(width, height)[0]

    def outlines(self, width, height):
        return self._frame(width, height)[1]

    def highlighted_cubies(self, face):
        return {c.id for c in moving_cubies(self.cube, face)}

    def routes(self, width, height):
        if not self.current:
            return []
        face, turns = parse_twist(self.current)
        normal = FACE_NORMALS[face]
        paths = []
        for cubie in moving_cubies(self.cube, face):
            if normal[2]:
                a = math.atan2(-cubie.position[1], cubie.position[0])
                radii = INNER_RADII if face == "F" else OUTER_RADII
                r = (radii[0] + radii[-1]) / 2 * min(width, height) / 800
                paths.append([(width / 2 + r * math.cos(a + normal[2] * turns * math.pi / 4 * i / 40),
                               height / 2 + r * math.sin(a + normal[2] * turns * math.pi / 4 * i / 40)) for i in range(41)])
            else:
                paths.append([_world(_twist(_cell(cubie.position, normal), -turns * math.pi / 4 * i / 40),
                                     normal, width, height) for i in range(41)])
        return paths

    def export_state(self):
        return {"pieces": [{"id": c.id, "position": c.position, "orientation": self.cube.orientations[c.id]}
                           for c in self.cube.cubies], "history": self.history[:], "duration": self.duration}

    def import_state(self, data):
        cube = Cube45()
        items = data["pieces"]
        if len(items) != 26 or len({item["id"] for item in items}) != 26:
            raise ValueError("Invalid piece inventory")
        pieces = {c.id: c for c in cube.cubies}
        original_slots = {c.position for c in cube.cubies}
        for item in items:
            piece = pieces[item["id"]]
            position = tuple(item["position"])
            orientation = item["orientation"]
            if position not in original_slots or type(orientation) is not int or not 0 <= orientation < 8:
                raise ValueError("Invalid position or orientation")
            if piece.kind == "center" and (position != piece.position or orientation):
                raise ValueError("Centers must be fixed")
            piece.position = position
            cube.orientations[piece.id] = orientation
        if {c.position for c in cube.cubies} != original_slots:
            raise ValueError("Duplicated slot")
        history = data["history"]
        if not isinstance(history, list):
            raise ValueError("Invalid history")
        for move in history:
            parse_twist(move)
        duration = float(data["duration"])
        if not math.isfinite(duration) or not .2 <= duration <= 3:
            raise ValueError("Invalid duration")
        self.set_cube(cube)
        self.history = history[:]
        self.duration = duration
