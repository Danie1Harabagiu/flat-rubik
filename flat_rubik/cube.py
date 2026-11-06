
from dataclasses import dataclass
from itertools import product
from collections import Counter
import random


@dataclass(frozen=True)
class Centru:
    id: str
    culoare: str


CENTRE = {
    "rosu": Centru("C_ROSU", "rosu"),
    "portocaliu": Centru("C_PORTOCALIU", "portocaliu"),
    "galben": Centru("C_GALBEN", "galben"),
    "verde": Centru("C_VERDE", "verde"),
    "alb": Centru("C_ALB", "alb"),
    "albastru": Centru("C_ALBASTRU", "albastru"),
}

# Right-handed coordinates: x right, y up, z front. Clockwise as
# seen from outside the face is -90 degrees about its outward normal.
FACE_NORMALS = {"R": (1, 0, 0), "L": (-1, 0, 0),
                "U": (0, 1, 0), "D": (0, -1, 0),
                "F": (0, 0, 1), "B": (0, 0, -1)}
FACE_COLORS = dict(zip("RLUDFB", ("verde", "albastru", "galben", "alb", "rosu", "portocaliu")))


def rotate(vector, axis, quarter):
    """Exact integer quarter turns around a positive coordinate axis."""
    values = list(vector)
    a, b = (axis + 1) % 3, (axis + 2) % 3
    for _ in range(quarter % 4):
        values[a], values[b] = -values[b], values[a]
    return tuple(values)


def parse_move(move):
    if not isinstance(move, str) or not move or move[0] not in FACE_NORMALS or move[1:] not in ("", "'", "2"):
        raise ValueError(f"Invalid move: {move!r}")
    return move[0], {"": 1, "'": -1, "2": 2}[move[1:]]


def inverse(move):
    face, turns = parse_move(move)
    return face + ("2" if turns == 2 else "'" if turns == 1 else "")


@dataclass
class Cubie:
    id: str
    position: tuple
    stickers: dict  # outward normal -> color; orientation lives here

    @property
    def kind(self):
        return {1: "center", 2: "edge", 3: "corner"}[len(self.stickers)]


class Cube:
    def __init__(self):
        self.cubies = []
        for p in product((-1, 0, 1), repeat=3):
            if p == (0, 0, 0):
                continue
            stickers = {normal: FACE_COLORS[face] for face, normal in FACE_NORMALS.items()
                        if sum(a * b for a, b in zip(p, normal)) == 1}
            self.cubies.append(Cubie("P_" + "_".join(map(str, p)), p, stickers))

    def move(self, move):
        face, turns = parse_move(move)
        normal = FACE_NORMALS[face]
        axis = next(i for i, value in enumerate(normal) if value)
        quarter = -normal[axis] * turns
        for cubie in self.cubies:
            if cubie.position[axis] == normal[axis] and cubie.kind != "center":
                cubie.position = rotate(cubie.position, axis, quarter)
                cubie.stickers = {rotate(n, axis, quarter): c for n, c in cubie.stickers.items()}

    def apply(self, sequence):
        for move in sequence.split() if isinstance(sequence, str) else sequence:
            self.move(move)

    def snapshot(self):
        return tuple((c.id, c.position, tuple(sorted(c.stickers.items()))) for c in self.cubies)

    @property
    def solved(self):
        return all(c.stickers[n] == FACE_COLORS[f] for c in self.cubies
                   for f, n in FACE_NORMALS.items() if n in c.stickers)

    def color_counts(self):
        return Counter(color for c in self.cubies for color in c.stickers.values())


def scramble(length=25, rng=None):
    rng = rng or random
    result = []
    for _ in range(length):
        choices = [f for f in FACE_NORMALS if not result or f != result[-1][0]]
        result.append(rng.choice(choices) + rng.choice(("", "'", "2")))
    return result
