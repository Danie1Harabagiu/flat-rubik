"""Translate mouse clicks on fixed centers to standard Rubik notation."""
from flat_rubik.cube import FACE_COLORS
from flat_rubik.geometry import center_at, rotation_handles
from math import dist


def move_for_click(position, button, size):
    if button not in (1, 3):
        return None
    if button == 1:
        handles = rotation_handles(*size)
        for face, color in FACE_COLORS.items():
            _, left, right, radius = handles[color]
            if dist(position, left) <= radius:
                return face + "'"
            if dist(position, right) <= radius:
                return face
    color = center_at(position, *size)
    face = next((face for face, face_color in FACE_COLORS.items() if face_color == color), None)
    return face + ("'" if button == 3 else "") if face else None
