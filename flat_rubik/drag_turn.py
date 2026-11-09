"""Preview a layer turn while dragging; commit one move only on release."""
from copy import deepcopy
import math

from flat_rubik.cube import FACE_COLORS, FACE_NORMALS
from flat_rubik.editor import contains, slot_at
from flat_rubik.flat_view import flat_pointer, flat_viewport, UNWRAPPED, unwrapped_screen_point
from flat_rubik.geometry import board_point, center_at, rotation_handles
from flat_rubik.layer_motion import ease


class DragTurn:
    threshold = 10

    def __init__(self, animator, point, size, mode, zoom=(1, 1), fit_mode=None, equal_pieces=True):
        self.start = point
        self.moved = False
        self.preview = None
        self.move = self.face = None
        self.candidates = {}
        self.distance = max(45, min(size) * .22)
        if animator.pending:
            return
        mapped = flat_pointer(point, size, mode, zoom, fit_mode, equal_pieces=equal_pieces)
        if not mapped:
            return
        local, virtual = mapped
        center = center_at(local, *virtual)
        if center:
            faces = [f for f, color in FACE_COLORS.items() if color == center]
        else:
            cubie_id = next((key for key, outline in animator.outlines(*virtual).items()
                             if contains(local, outline)), None)
            cubie = next((c for c in animator.cube.cubies if c.id == cubie_id), None)
            if cubie is None:
                return
            faces = [f for f, normal in FACE_NORMALS.items()
                     if sum(a * b for a, b in zip(cubie.position, normal)) == 1]
            slot = slot_at(local, virtual)
            if slot:
                faces.sort(key=lambda f: FACE_NORMALS[f] != slot[1])
        _, destination = flat_viewport(size, mode, zoom, fit_mode, equal_pieces=equal_pieces)

        def display(p):
            if mode == UNWRAPPED:
                return unwrapped_screen_point(p, destination, virtual, equal_pieces=equal_pieces)
            x, y = board_point(p, *virtual)
            return destination.x + x * destination.w / virtual[0], destination.y + y * destination.h / virtual[1]

        handles = rotation_handles(*virtual)
        for face in faces:
            anchor = (virtual[0] / 2, virtual[1] / 2) if face in "FB" else handles[FACE_COLORS[face]][0]
            dx, dy = local[0] - anchor[0], local[1] - anchor[1]
            length = math.hypot(dx, dy)
            if length < 2:
                dx, dy, length = 0, -1, 1
            sign = -1 if face == "B" else 1
            end = display((local[0] - sign * dy / length, local[1] + sign * dx / length))
            origin = display(local)
            vector = end[0] - origin[0], end[1] - origin[1]
            norm = math.hypot(*vector)
            self.candidates[face] = vector[0] / norm, vector[1] / norm
        self.source = animator

    def motion(self, point):
        dx, dy = point[0] - self.start[0], point[1] - self.start[1]
        if math.hypot(dx, dy) < self.threshold and not self.moved:
            return
        self.moved = True
        if not self.candidates:
            return
        if self.face is None:
            face = max(self.candidates, key=lambda f: abs(dx * self.candidates[f][0] + dy * self.candidates[f][1]))
            vector = self.candidates[face]
            if abs(dx * vector[0] + dy * vector[1]) < self.threshold * .7:
                return
            self.face = face
        vector = self.candidates[self.face]
        amount = dx * vector[0] + dy * vector[1]
        move = self.face + ("'" if amount < 0 else "")
        if self.preview is None or self.move != move:
            self.preview = deepcopy(self.source)
            self.preview.enqueue([move])
            self.preview.update(0)
            self.move = move
        fraction = min(.95, abs(amount) / self.distance)
        # Existing animations ease time. Invert that easing for direct finger control.
        low, high = 0., 1.
        for _ in range(20):
            middle = (low + high) / 2
            if ease(middle) < fraction:
                low = middle
            else:
                high = middle
        self.preview.elapsed = (low + high) / 2 * self.preview.duration

    def release(self, point):
        self.motion(point)
        if self.preview is None or ease(self.preview.elapsed / self.preview.duration) < .06:
            return False
        self.source.enqueue([self.move])
        self.source.update(0)
        self.source.elapsed = self.preview.elapsed
        return True
