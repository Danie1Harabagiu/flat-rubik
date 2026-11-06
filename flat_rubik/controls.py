"""Translate mouse clicks on fixed centers to standard Rubik notation."""
from flat_rubik.cube import FACE_COLORS
from flat_rubik.geometry import center_at


def move_for_click(position, button, size):
    if button not in (1, 3):
        return None
    color = center_at(position, *size)
    face = next((face for face, face_color in FACE_COLORS.items() if face_color == color), None)
    return face + ("'" if button == 3 else "") if face else None
