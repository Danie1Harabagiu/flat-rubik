"""Nonblocking move queue. Logical state commits once per completed move."""
from collections import deque
from copy import deepcopy

from flat_rubik.cube import Cube, parse_move
from flat_rubik.projection import mobile_shapes
from flat_rubik.layer_motion import layer_shapes, layer_outlines


class Animator:
    def __init__(self, cube=None, duration=.3):
        if duration <= 0:
            raise ValueError("Duration must be positive")
        self.cube = cube if cube is not None else Cube()
        self.duration = duration
        self.queue = deque()
        self.target = None
        self.elapsed = 0.0
        self.current = None
        self.history = []

    def enqueue(self, moves):
        moves = moves.split() if isinstance(moves, str) else list(moves)
        for move in moves:
            parse_move(move)
        self.queue.extend(moves)

    def set_duration(self, duration):
        """Change speed without changing the current animation's progress."""
        if duration <= 0:
            raise ValueError("Duration must be positive")
        self.elapsed *= duration / self.duration
        self.duration = duration

    @property
    def pending(self):
        return len(self.queue) + int(self.target is not None)

    def reset(self):
        self.cube = Cube()
        self.queue.clear()
        self.target = None
        self.current = None
        self.elapsed = 0.0
        self.history.clear()

    def update(self, dt):
        if dt < 0:
            raise ValueError("Time step must be nonnegative")
        while True:
            if self.target is None:
                if not self.queue:
                    return
                self.current = self.queue.popleft()
                self.target = deepcopy(self.cube)
                self.target.move(self.current)
                self.elapsed = 0.0
            remaining = self.duration - self.elapsed
            if dt < remaining:
                self.elapsed += dt
                return
            dt -= remaining
            self.cube = self.target
            self.target = None
            self.history.append(self.current)
            self.current = None

    def shapes(self, width, height):
        if self.target is None:
            return mobile_shapes(self.cube, width, height)
        return layer_shapes(self.cube, self.target, self.current, self.elapsed / self.duration, width, height)

    def outlines(self, width, height):
        return layer_outlines(self.cube, self.target, self.current, self.elapsed / self.duration, width, height)
