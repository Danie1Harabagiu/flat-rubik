"""Rebuild physical cubies from painted facelets; reject unreachable states."""
from collections import Counter

from flat_rubik.cube import Cube, FACE_COLORS, FACE_NORMALS

CORNER_FACES = ("URF", "UFL", "ULB", "UBR", "DFR", "DLF", "DBL", "DRB")
EDGE_FACES = ("UR", "UF", "UL", "UB", "DR", "DF", "DL", "DB", "FR", "FL", "BL", "BR")


def facelets(cube):
    return {(c.position, n): color for c in cube.cubies for n, color in c.stickers.items()}


def _position(faces):
    return tuple(sum(FACE_NORMALS[f][i] for f in faces) for i in (0, 1, 2))


def _parity(permutation):
    return sum(a > b for i, a in enumerate(permutation) for b in permutation[i + 1:]) % 2


def cube_from_facelets(colors):
    """Return a cube with original identities, never relabeled fake cubies."""
    solved = Cube()
    template = facelets(solved)
    if set(colors) != set(template):
        raise ValueError("Completeaza toate cele 54 de suprafete.")
    if any(c not in FACE_COLORS.values() for c in colors.values()):
        raise ValueError("Foloseste numai cele sase culori ale cubului.")
    for f, n in FACE_NORMALS.items():
        if colors[n, n] != FACE_COLORS[f]:
            raise ValueError("Centrele trebuie sa ramana fixe.")
    counts = Counter(colors.values())
    wrong = [f"{c}={counts[c]}" for c in FACE_COLORS.values() if counts[c] != 9]
    if wrong:
        raise ValueError("Trebuie 9 din fiecare culoare: " + ", ".join(wrong) + ".")
    homes = {c.position: c for c in solved.cubies}
    permutations = []
    orientations = []
    for family in (EDGE_FACES, CORNER_FACES):
        home_colors = [tuple(FACE_COLORS[f] for f in faces) for faces in family]
        signatures = {frozenset(c): i for i, c in enumerate(home_colors)}
        permutation, orientation = [], []
        for faces in family:
            position = _position(faces)
            observed = tuple(colors[position, FACE_NORMALS[f]] for f in faces)
            index = signatures.get(frozenset(observed))
            kind = "muchie" if len(faces) == 2 else "colt"
            if index is None or len(set(observed)) != len(faces):
                raise ValueError(f"Combinatie imposibila de culori pe un {kind}.")
            if index in permutation:
                raise ValueError(f"Un {kind} apare de doua ori. Verifica culorile.")
            expected = home_colors[index]
            if len(faces) == 2:
                twist = 0 if observed == expected else 1
            else:
                twist = next(i for i, c in enumerate(observed) if c in (FACE_COLORS["U"], FACE_COLORS["D"]))
                if observed[twist:] + observed[:twist] != expected:
                    raise ValueError("Culorile unui colt sunt in oglinda. Verifica ordinea lor.")
            cubie = homes[_position(family[index])]
            cubie.position = position
            cubie.stickers = {FACE_NORMALS[f]: color for f, color in zip(faces, observed)}
            permutation.append(index)
            orientation.append(twist)
        permutations.append(permutation)
        orientations.append(orientation)
    if sum(orientations[0]) % 2:
        raise ValueError("O muchie este intoarsa. Verifica orientarea culorilor.")
    if sum(orientations[1]) % 3:
        raise ValueError("Un colt este rasucit. Verifica orientarea culorilor.")
    if _parity(permutations[0]) != _parity(permutations[1]):
        raise ValueError("Piese schimbate imposibil intre ele. Verifica pozitiile.")
    return solved
