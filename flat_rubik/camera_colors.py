"""Camera face grids use the standard face-on URFDLB orientation."""
from flat_rubik.cube import FACE_NORMALS
from flat_rubik.state import cube_from_facelets

ORDER = "FRBLUD"


def scan_cube(grids):
    """Validate corrected camera labels, including physical reachability."""
    if not isinstance(grids, dict) or set(grids) != set(ORDER):
        raise ValueError("Scaneaza toate cele sase fete.")
    colors = {}
    for face in ORDER:
        values = grids[face]
        if not isinstance(values, list) or len(values) != 9:
            raise ValueError("Fiecare fata trebuie sa aiba noua culori.")
        for index, color in enumerate(values):
            if not isinstance(color, str):
                raise ValueError("Culoare invalida.")
            row, col = divmod(index, 3)
            position = {
                "U": (col - 1, 1, row - 1), "R": (1, 1 - row, 1 - col),
                "F": (col - 1, 1 - row, 1), "D": (col - 1, -1, 1 - row),
                "L": (-1, 1 - row, col - 1), "B": (1 - col, 1 - row, -1),
            }[face]
            colors[position, FACE_NORMALS[face]] = color
    return cube_from_facelets(colors)
