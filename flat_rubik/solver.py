"""Budgeted, exact QTM search. A two-phase seed is NEVER an optimality proof.

All search edges are +/-90 degrees, so a half turn costs two. Admissible
single-piece and four-piece pattern distances prune an iterative-deepening
search. Only exhaustive elimination of shorter depths certifies a solution.
The generator also runs cooperatively in the browser without threads.
"""
from array import array
from collections import deque
from copy import deepcopy
from dataclasses import dataclass, replace
from functools import lru_cache
import hashlib
import math
from pathlib import Path
import time

from flat_rubik.cube import Cube, FACE_COLORS, FACE_NORMALS, inverse, parse_move, rotate
from flat_rubik.state import CORNER_FACES, EDGE_FACES, cube_from_facelets, facelets

MOVES = tuple(face + suffix for face in "URFDLB" for suffix in ("", "'"))
GOAL = bytes([i * 3 for i in range(8)] + [24 + i * 2 for i in range(12)])
GROUPS = ((0, 1, 2, 3), (4, 5, 6, 7), (8, 9, 10, 11), (12, 13, 14, 15), (16, 17, 18, 19))
PATTERN_SIZE = 24 ** 4
CACHE_DIR = Path(__file__).resolve().parent.parent / ".solver_cache"


def quarter_steps(moves):
    """Normalize notation, expanding half turns to two separately shown steps."""
    result = []
    for move in moves.split() if isinstance(moves, str) else moves:
        face, turns = parse_move(move)
        result.extend([face, face] if turns == 2 else [face + ("'" if turns == -1 else "")])
    return tuple(result)


def checked_solution(cube, moves):
    if moves is None:
        return None
    try:
        steps = simplify_steps(quarter_steps(moves))
        check = deepcopy(cube)
        check.apply(steps)
        return steps if check.solved else None
    except (TypeError, ValueError, KeyError):
        return None


def simplify_steps(steps):
    """Cancel adjacent turns and canonically commute opposite faces."""
    word = list(steps)
    order = {face: index for index, face in enumerate("URFDLB")}
    while True:
        before = word[:]
        for i in range(len(word) - 1):
            a, b = order[word[i][0]], order[word[i + 1][0]]
            if abs(a - b) == 3 and a > b:
                word[i], word[i + 1] = word[i + 1], word[i]
        result = []
        i = 0
        while i < len(word):
            face = word[i][0]
            turns = 0
            while i < len(word) and word[i][0] == face:
                turns += -1 if word[i].endswith("'") else 1
                i += 1
            result.extend({0: (), 1: (face,), 2: (face, face), 3: (face + "'",)}[turns % 4])
        word = result
        if word == before:
            return tuple(word)


def framed_cube(cube, axis, turns):
    """Rotate coordinates and color names together; map solutions back exactly."""
    face_for_normal = {normal: face for face, normal in FACE_NORMALS.items()}
    face_map = {face: face_for_normal[rotate(normal, axis, turns)] for face, normal in FACE_NORMALS.items()}
    color_map = {FACE_COLORS[face]: FACE_COLORS[mapped] for face, mapped in face_map.items()}
    result = deepcopy(cube)
    for piece in result.cubies:
        piece.position = rotate(piece.position, axis, turns)
        piece.stickers = {rotate(normal, axis, turns): color_map[color] for normal, color in piece.stickers.items()}
    return result, {mapped: face for face, mapped in face_map.items()}


def history_solution(cube, history):
    return checked_solution(cube, [inverse(move) for move in reversed(history)])


def facelet_string(cube):
    colors = facelets(cube)
    face_for_color = {color: face for face, color in FACE_COLORS.items()}
    result = []
    for face in "URFDLB":
        for row in range(3):
            for col in range(3):
                position = {"U": (col - 1, 1, row - 1), "R": (1, 1 - row, 1 - col),
                            "F": (col - 1, 1 - row, 1), "D": (col - 1, -1, 1 - row),
                            "L": (-1, 1 - row, col - 1), "B": (1 - col, 1 - row, -1)}[face]
                result.append(face_for_color[colors[position, FACE_NORMALS[face]]])
    return "".join(result)


def _position(faces):
    return tuple(sum(FACE_NORMALS[f][i] for f in faces) for i in range(3))


def encode(cube, validate=True):
    if type(cube) is not Cube:
        raise ValueError("Rezolvarea este disponibila pentru Rubik 90°.")
    if validate:
        cube = cube_from_facelets(facelets(cube))
    result = []
    pieces = {frozenset(c.stickers.values()): c for c in cube.cubies if c.kind != "center"}
    for family, offset in ((CORNER_FACES, 0), (EDGE_FACES, 24)):
        slots = {_position(faces): i for i, faces in enumerate(family)}
        for home in family:
            expected = tuple(FACE_COLORS[f] for f in home)
            piece = pieces[frozenset(expected)]
            slot = slots[piece.position]
            observed = tuple(piece.stickers[FACE_NORMALS[f]] for f in family[slot])
            orientation = observed.index(expected[0])
            result.append(offset + slot * len(home) + orientation)
    return bytes(result)


@lru_cache(maxsize=1)
def move_tables():
    tables = []
    for move in MOVES:
        cube = Cube()
        cube.move(move)
        state = encode(cube, validate=False)
        table = bytearray(range(256))
        for start in range(8):
            slot, delta = divmod(state[start], 3)
            for orientation in range(3):
                table[start * 3 + orientation] = slot * 3 + (orientation + delta) % 3
        for start in range(12):
            slot, delta = divmod(state[8 + start] - 24, 2)
            for orientation in range(2):
                table[24 + start * 2 + orientation] = 24 + slot * 2 + (orientation + delta) % 2
        tables.append(bytes(table))
    return tuple(tables)


@lru_cache(maxsize=1)
def piece_distances():
    tables = move_tables()
    result = []
    for goal in GOAL:
        distances = bytearray([255]) * 48
        distances[goal] = 0
        queue = deque([goal])
        while queue:
            code = queue.popleft()
            distance = distances[code] + 1
            for table in tables:
                nxt = table[code]
                if distances[nxt] == 255:
                    distances[nxt] = distance
                    queue.append(nxt)
        result.append(bytes(distances))
    return tuple(result)


def _pattern_index(state, group):
    a, b, c, d = group
    offset = 24 if a >= 8 else 0
    return ((state[a] - offset) * 24 + state[b] - offset) * 576 + (state[c] - offset) * 24 + state[d] - offset


def _pattern_table(group):
    offset = 24 if group[0] >= 8 else 0
    pair_maps = [array("H", ((table[offset + a] - offset) * 24 + table[offset + b] - offset
                            for a in range(24) for b in range(24))) for table in move_tables()]
    distances = bytearray([255]) * PATTERN_SIZE
    root = _pattern_index(GOAL, group)
    distances[root] = 0
    queue = array("I", [root])
    head = 0
    while head < len(queue):
        state = queue[head]
        head += 1
        high, low = divmod(state, 576)
        distance = distances[state] + 1
        for table in pair_maps:
            nxt = table[high] * 576 + table[low]
            if distances[nxt] == 255:
                distances[nxt] = distance
                queue.append(nxt)
        if head % 512 == 0:
            yield None
    return distances


def _cache_header():
    return b"FLAT-QTM-1\n" + hashlib.sha256(b"".join(move_tables()) + GOAL).digest()


def _load_patterns(path):
    if path is None:
        return None
    try:
        data = Path(path).read_bytes()
        header = _cache_header()
        if len(data) != len(header) + 32 + 5 * PATTERN_SIZE or not data.startswith(header):
            return None
        payload = data[len(header) + 32:]
        if hashlib.sha256(payload).digest() != data[len(header):len(header) + 32]:
            return None
        return [payload[i * PATTERN_SIZE:(i + 1) * PATTERN_SIZE] for i in range(5)]
    except OSError:
        return None


def _save_patterns(path, patterns):
    if path is None:
        return
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = b"".join(patterns)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(_cache_header() + hashlib.sha256(payload).digest() + payload)
        temporary.replace(path)
    except OSError:
        pass  # Cache failure cannot change the search or its correctness.


@dataclass(frozen=True)
class SearchResult:
    best: tuple | None = None
    lower_bound: int = 0
    nodes: int = 0
    elapsed: float = 0
    optimal: bool = False
    status: str = "searching"
    detail: str = ""


class ExactSearch:
    def __init__(self, cube, seed=None, deadline=None, clock=time.monotonic):
        self.clock = clock
        self.started = clock()
        self.deadline = deadline if deadline is not None else math.inf
        self.state = encode(cube)
        self.tables = move_tables()
        self.distances = piece_distances()
        self.patterns = []
        self.result = SearchResult(best=checked_solution(cube, seed))
        self.nodes = 0
        self.path = []
        self.ancestors = {self.state}

    def report(self, **changes):
        self.result = replace(self.result, elapsed=self.clock() - self.started, nodes=self.nodes, **changes)
        return self.result

    def heuristic(self, state):
        distances = self.distances
        corners = [distances[i][state[i]] for i in range(8)]
        edges = [distances[i][state[i]] for i in range(8, 20)]
        bound = max(max(corners), max(edges), (sum(corners) + 3) // 4, (sum(edges) + 3) // 4)
        for group, table in zip(GROUPS, self.patterns):
            bound = max(bound, table[_pattern_index(state, group)])
        return bound

    def _dfs(self, state, remaining, heuristic, last=-1, before_last=-1):
        self.nodes += 1
        if self.nodes % 128 == 0:
            yield None
            if self.clock() >= self.deadline:
                raise TimeoutError
        if state == GOAL:
            return tuple(MOVES[i] for i in self.path)
        if heuristic > remaining or remaining == 0:
            return None
        for move, table in enumerate(self.tables):
            if last >= 0:
                if move == (last ^ 1):
                    continue  # Immediate cancellation.
                if move // 2 == last // 2:
                    if move & 1 or before_last // 2 == move // 2:
                        continue  # R'R'=RR; three R turns reduce to R'.
                # Opposite faces commute: retain one canonical ordering.
                if abs(move // 2 - last // 2) == 3 and move // 2 < last // 2:
                    continue
            child = state.translate(table)
            if child in self.ancestors:
                continue
            distance = self.heuristic(child)
            if distance > remaining - 1:
                continue
            self.path.append(move)
            self.ancestors.add(child)
            solution = yield from self._dfs(child, remaining - 1, distance, move, last)
            self.ancestors.remove(child)
            self.path.pop()
            if solution is not None:
                return solution
        return None

    def search(self, cache_path=None, shallow_only=False):
        """Yield progress; the final yielded result records proof vs timeout."""
        if self.state == GOAL:
            yield self.report(best=(), lower_bound=0, optimal=True, status="done")
            return
        lower = max(self.result.lower_bound, self.heuristic(self.state))
        self.result = replace(self.result, lower_bound=lower)
        if shallow_only and lower > 5:
            return
        try:
            if not shallow_only:
                cached = _load_patterns(cache_path)
                if cached is not None:
                    self.patterns = cached
                else:
                    for index, group in enumerate(GROUPS):
                        builder = _pattern_table(group)
                        while True:
                            if self.clock() >= self.deadline:
                                raise TimeoutError
                            try:
                                next(builder)
                                yield self.report(status="preparing", detail=f"Pregatire {index + 1}/5")
                            except StopIteration as completed:
                                self.patterns.append(completed.value)
                                break
                    _save_patterns(cache_path, self.patterns)
                lower = max(lower, self.heuristic(self.state))
                self.result = replace(self.result, lower_bound=lower)
            bound = lower
            while self.result.best is None or bound < len(self.result.best):
                if self.clock() >= self.deadline:
                    raise TimeoutError
                if shallow_only and bound > 5:
                    return
                yield self.report(status="searching", detail=f"Caut la {bound} pasi")
                search = self._dfs(self.state, bound, self.heuristic(self.state))
                while True:
                    try:
                        next(search)
                        yield self.report(status="searching")
                    except StopIteration as completed:
                        if completed.value is not None:
                            yield self.report(best=completed.value, lower_bound=len(completed.value), optimal=True, status="done")
                            return
                        break
                bound += 1
                self.result = replace(self.result, lower_bound=bound)
            yield self.report(lower_bound=len(self.result.best), optimal=True, status="done")
        except TimeoutError:
            yield self.report(status="budget", detail="Buget epuizat")


def search_events(cube, budget, seed=None, cache_dir=None, use_fast_seed=False, clock=time.monotonic):
    """Common worker/browser pipeline; budget includes setup and seed search."""
    if not math.isfinite(budget) or budget <= 0:
        raise ValueError("Bugetul trebuie sa fie pozitiv.")
    started = clock()
    engine = ExactSearch(cube, seed=seed, deadline=started + budget, clock=clock)
    yield engine.report()
    yield from engine.search(shallow_only=True)
    if engine.result.status in ("done", "budget"):
        return
    if use_fast_seed and clock() < engine.deadline:
        yield engine.report(status="preparing", detail="Caut o prima solutie")
        try:
            import os
            if cache_dir is not None:
                os.environ["RUBIK_SOLVER_CACHE_DIR"] = str(Path(cache_dir) / "twophase")
            from importlib import import_module
            seed_solver = import_module("rubik_solver")
            seed_solver.init_solver()
            if clock() < engine.deadline:
                # Two-phase optimizes a different metric. Compare several frames
                # using QTM cost, then leave the remaining budget for exact proof.
                seed_deadline = min(engine.deadline, clock() + 4)
                for axis, turns in ((0, 0), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2)):
                    framed, back = framed_cube(cube, axis, turns)
                    candidate = seed_solver.solve(seed_solver.Cube.from_string(facelet_string(framed)), max_depth=22)
                    mapped = [back[m[0]] + m[1:] for m in candidate.split()] if candidate is not None else None
                    verified = checked_solution(cube, mapped)
                    if verified is not None and (engine.result.best is None or len(verified) < len(engine.result.best)):
                        yield engine.report(best=verified, status="searching", detail="Solutie verificata; caut mai scurt")
                    if clock() >= seed_deadline:
                        break
        except (ImportError, ValueError, RuntimeError, OSError):
            pass  # The exact search still works without the optional fast seed.
    path = Path(cache_dir) / "qtm-patterns-v1.bin" if cache_dir is not None else None
    yield from engine.search(cache_path=path)
