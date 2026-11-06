"""Draft actual facelet colors without mutating the live cube before validation."""
import json
from functools import lru_cache
from pathlib import Path

from flat_rubik.cube import Cube, FACE_COLORS, FACE_NORMALS
from flat_rubik.geometry import center_at
from flat_rubik.projection import project, slot_polygon
from flat_rubik.state import facelets, cube_from_facelets
from flat_rubik.cube import scramble

SLOTS = frozenset((s.position, s.normal) for s in project(Cube()))
COLOR_CYCLE = ("rosu", "portocaliu", "galben", "verde", "albastru", "alb")


def contains(point, polygon):
    x, y = point
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        if (a[1] > y) != (b[1] > y) and x < a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
            inside = not inside
    return inside


@lru_cache(maxsize=16)
def slot_regions(width, height):
    return [(s.position, s.normal, slot_polygon(s.position, s.normal, width, height))
            for s in project(Cube()) if sum(map(abs, s.position)) > 1]


def slot_at(point, size):
    center = center_at(point, *size)
    if center:
        normal = FACE_NORMALS[next(f for f, c in FACE_COLORS.items() if c == center)]
        return normal, normal
    return next(((p, n) for p, n, polygon in slot_regions(*size) if contains(point, polygon)), None)


class ColorEditor:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.colors = facelets(Cube())
        self.baseline = self.colors.copy()
        self.startup_cube = None
        self.applied = None
        self.resume_draft = False
        self.editing = False
        self.color = "rosu"
        self.history = []
        self.message = ""
        self.error = False
        if self.path and self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if data.get("version") != 1:
                    raise ValueError("Unknown color format")
                self.colors = self._decode(data["draft"])
                if data.get("applied"):
                    self.applied = self._decode(data["applied"])
                    self.startup_cube = cube_from_facelets(self.applied)
                self.resume_draft = True
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                self.colors = facelets(Cube())
                self.startup_cube = self.applied = None
                self.message = "Fisierul de culori nu poate fi citit."

    @staticmethod
    def _decode(items):
        colors = {(tuple(i["position"]), tuple(i["normal"])): i["color"] for i in items}
        if set(colors) != SLOTS or any(c not in FACE_COLORS.values() for c in colors.values()):
            raise ValueError("Unknown slot or color")
        for f, n in FACE_NORMALS.items():
            if colors[n, n] != FACE_COLORS[f]:
                raise ValueError("Center modified")
        return colors

    def begin(self, cube):
        self.baseline = facelets(cube)
        if not self.resume_draft:
            self.colors = self.baseline.copy()
        self.resume_draft = False
        self.history.clear()
        self.message = "Clic: urmatoarea culoare. Dreapta: inapoi."
        self.error = False
        self.editing = True

    def cancel(self):
        self.colors = self.baseline.copy()
        self.editing = False
        self.history.clear()
        self.save()

    def _remember(self):
        self.history.append(self.colors.copy())
        self.history = self.history[-100:]
        self.error = False
        self.message = "Apasa Aplica dupa ce ai terminat."

    def save(self):
        if not self.path:
            return
        def encode(colors):
            return [{"position": p, "normal": n, "color": c} for (p, n), c in sorted(colors.items())]
        data = {"version": 1, "draft": encode(self.colors), "applied": encode(self.applied) if self.applied else None}
        try:
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.path)
        except OSError:
            self.message = "Culori active; salvarea a esuat."

    def paint(self, point, button, size):
        if button not in (1, 3):
            return False
        slot = slot_at(point, size)
        if slot is None:
            return False
        if slot[0] == slot[1]:
            self.message = "Centrele sunt fixe; alege o piesa mobila."
            return False
        index = COLOR_CYCLE.index(self.colors[slot])
        color = COLOR_CYCLE[(index + (1 if button == 1 else -1)) % len(COLOR_CYCLE)]
        self._remember()
        self.colors[slot] = color
        self.color = color
        self.save()
        return True

    def reset(self):
        self._remember()
        self.colors = facelets(Cube())
        self.save()

    def randomize(self):
        cube = Cube()
        cube.apply(scramble())
        self._remember()
        self.colors = facelets(cube)
        self.message = "Amestecare valida. Apasa Aplica."
        self.save()

    def undo(self):
        if self.history:
            self.colors = self.history.pop()
            self.message = "Ultima modificare a fost anulata."
            self.error = False
            self.save()

    def apply(self):
        try:
            cube = cube_from_facelets(self.colors)
        except ValueError as error:
            self.message = str(error)
            self.error = True
            return None
        self.editing = False
        self.applied = facelets(cube)
        self.colors = self.applied.copy()
        self.message = "Configuratie valida aplicata."
        self.error = False
        self.save()
        return cube
