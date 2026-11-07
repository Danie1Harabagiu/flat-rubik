from collections import deque
from copy import deepcopy
import os
from pathlib import Path
import json
import random
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from flat_rubik.animation import Animator
from flat_rubik.cube import Cube, inverse, scramble
from flat_rubik.puzzle45 import Cube45
from flat_rubik.solver import (ExactSearch, GOAL, GROUPS, MOVES, PATTERN_SIZE, SearchResult,
                               checked_solution, encode, facelet_string, framed_cube,
                               history_solution, move_tables, quarter_steps, search_events,
                               _pattern_index, _pattern_table, _load_patterns, _save_patterns)
from flat_rubik.solve_job import SearchJob
from flat_rubik.solve_panel import SolvePanel, solve_layout, playback_layout


class SolverTests(unittest.TestCase):
    def solve(self, cube, seed=None):
        return list(search_events(cube, 3, seed=seed, cache_dir=None))[-1]

    def test_all_moves_and_long_sequence_match_the_physical_model(self):
        self.assertEqual(encode(Cube()), GOAL)
        rng = random.Random(551)
        cube, compact = Cube(), GOAL
        for _ in range(500):
            index = rng.randrange(12)
            cube.move(MOVES[index])
            compact = compact.translate(move_tables()[index])
            self.assertEqual(compact, encode(cube))
        with self.assertRaises(ValueError):
            encode(Cube45())

    def test_minimum_qtm_matches_an_independent_facelet_breadth_first_search(self):
        from test_physical_model import SLOTS, reference_turn, actual_labels
        labels = tuple(SLOTS)
        goal = tuple(labels)
        distances = {goal: 0}
        queue = deque([goal])
        while queue:
            state = queue.popleft()
            depth = distances[state]
            if depth == 3:
                continue
            for move in MOVES:
                d = dict(zip(labels, state))
                reference_turn(d, move)
                nxt = tuple(d[label] for label in labels)
                if nxt not in distances:
                    distances[nxt] = depth + 1
                    queue.append(nxt)
        sequences = ("", "R", "R2", "R U", "R L R'", "F2 U", "B' D L", "U D U'", "R U R'")
        for sequence in sequences:
            cube = Cube()
            cube.apply(sequence)
            actual = actual_labels(cube)
            expected = distances[tuple(actual[label] for label in labels)]
            before = cube.snapshot()
            result = self.solve(cube)
            self.assertTrue(result.optimal, sequence)
            self.assertEqual(len(result.best), expected, sequence)
            self.assertIsNotNone(checked_solution(cube, result.best))
            self.assertEqual(cube.snapshot(), before)
        cube = Cube()
        cube.move("R2")
        self.assertEqual(len(self.solve(cube).best), 2)

    def test_quarter_steps_and_seed_are_verified_not_blindly_reversed(self):
        self.assertEqual(quarter_steps("R2 U' F2"), ("R", "R", "U'", "F", "F"))
        cube = Cube()
        cube.apply("R U F2")
        self.assertIsNone(checked_solution(cube, ("U",)))
        self.assertIsNone(history_solution(cube, ("R",)))
        seed = history_solution(cube, ("R", "U", "F2"))
        self.assertIsNotNone(seed)
        self.assertEqual(len(seed), 4)
        self.assertEqual(checked_solution(Cube(), "R L R' L'"), ())

    def test_pattern_distances_are_admissible_and_cache_is_checked(self):
        builder = _pattern_table(GROUPS[0])
        while True:
            try:
                next(builder)
            except StopIteration as result:
                table = result.value
                break
        self.assertEqual(table[_pattern_index(GOAL, GROUPS[0])], 0)
        rng = random.Random(13)
        for length in range(1, 9):
            cube = Cube()
            cube.apply([rng.choice(MOVES) for _ in range(length)])
            self.assertLessEqual(table[_pattern_index(encode(cube), GROUPS[0])], length)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "patterns.bin"
            patterns = [table] * 5
            _save_patterns(path, patterns)
            self.assertEqual(_load_patterns(path), patterns)
            data = bytearray(path.read_bytes())
            data[-1] ^= 1
            path.write_bytes(data)
            self.assertIsNone(_load_patterns(path))

    def test_budget_expiry_preserves_candidate_without_claiming_optimality(self):
        cube = Cube()
        moves = scramble(25, random.Random(103))
        cube.apply(moves)
        seed = history_solution(cube, moves)
        result = list(search_events(cube, .001, seed=seed, cache_dir=None))[-1]
        self.assertEqual(result.status, "budget")
        self.assertFalse(result.optimal)
        self.assertEqual(result.best, seed)
        self.assertLessEqual(result.lower_bound, len(seed))
        self.assertIsNotNone(checked_solution(cube, result.best))

    def test_framed_seeds_map_back_to_original_moves(self):
        sequence = "R U' F2 L D B'".split()
        cube = Cube()
        cube.apply(sequence)
        for axis in range(3):
            for turns in range(4):
                framed, back = framed_cube(cube, axis, turns)
                forward = {value: key for key, value in back.items()}
                other = Cube()
                other.apply([forward[m[0]] + m[1:] for m in sequence])
                self.assertEqual(facelet_string(framed), facelet_string(other))
                solution = [inverse(m) for m in reversed(sequence)]
                mapped_solution = [forward[m[0]] + m[1:] for m in solution]
                self.assertIsNotNone(checked_solution(framed, mapped_solution))

    def test_desktop_job_is_cancellable_and_proves_a_small_case(self):
        job = SearchJob(browser=False, cache_dir=None)
        self.addCleanup(job.cancel)
        cube = Cube()
        cube.move("R2")
        job.start(cube, 5)
        limit = time.monotonic() + 6
        while job.busy and time.monotonic() < limit:
            job.poll()
            time.sleep(.01)
        self.assertFalse(job.busy)
        self.assertTrue(job.result.optimal, job.result)
        self.assertEqual(len(job.result.best), 2)
        cube.apply(scramble(25, random.Random(7)))
        job.start(cube, 1)
        while job.busy and time.monotonic() < limit:
            job.poll()
            time.sleep(.01)
        self.assertFalse(job.busy)
        self.assertEqual(job.result.status, "budget")
        self.assertIsNone(job.process)

    def test_browser_worker_seed_is_verified_and_merged_into_exact_search(self):
        cube = Cube()
        moves = scramble(25, random.Random(103))
        cube.apply(moves)
        candidate = [inverse(move) for move in reversed(moves)]
        calls = []
        replies = [{"candidates": [["R"], candidate], "status": "done"}]
        bridge = SimpleNamespace(
            startJson=lambda job, payload: calls.append((job, json.loads(payload))),
            pollJson=lambda job: json.dumps(replies.pop(0) if replies else {"candidates": [], "status": "done"}),
            cancel=lambda job: calls.append(("cancel", job)))
        job = SearchJob(browser=True, cache_dir=None)
        with patch("flat_rubik.solve_job.sys", SimpleNamespace(platform="emscripten")), \
                patch("platform.window", SimpleNamespace(flatRubikSolver=bridge), create=True):
            try:
                job.start(cube, 3)  # No history seed.
                limit = time.monotonic() + .3
                while job.result.best is None and time.monotonic() < limit:
                    job.poll()
                self.assertEqual(job.result.best, checked_solution(cube, candidate))
                self.assertFalse(job.result.optimal)
                self.assertEqual(len(calls[0][1]), 6)
            finally:
                job.cancel()
        self.assertEqual(calls[-1][0], "cancel")

    def test_external_candidate_can_only_certify_optimum_when_lower_bound_matches(self):
        cube = Cube()
        cube.move("R2")
        result = list(search_events(cube, 1, incumbent=lambda: ("R", "R")))[-1]
        self.assertTrue(result.optimal)
        self.assertEqual(result.best, ("R", "R"))
        self.assertEqual(result.lower_bound, 2)


class SolvePanelTests(unittest.TestCase):
    def setUp(self):
        import pygame
        pygame.init()
        self.addCleanup(pygame.quit)

    def panel(self):
        result = SolvePanel(SearchJob(browser=True, cache_dir=None))
        self.addCleanup(result.close)
        result.open_panel()
        return result

    def test_budget_input_layout_and_render_at_desktop_and_phone_sizes(self):
        import pygame
        panel = self.panel()
        animator = Animator()
        for size in ((1080, 800), (390, 844), (320, 360), (1200, 500)):
            rect, controls = solve_layout(size)
            for item in controls.values():
                self.assertTrue(rect.contains(item), (size, item))
            surface = pygame.Surface(size)
            panel.draw(surface)
            dock, controls = playback_layout(size)
            self.assertTrue(surface.get_rect().contains(dock))
            for item in controls.values():
                self.assertTrue(dock.contains(item))
        controls = solve_layout((390, 844))[1]
        panel.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=controls["budget"].center, button=1), animator, (390, 844))
        panel.handle(pygame.event.Event(pygame.TEXTINPUT, text="12"), animator, (390, 844))
        self.assertEqual(panel.budget_text, "12")
        panel.budget_text = "nan"
        panel.start(animator)
        self.assertFalse(panel.job.busy)
        self.assertIn("Buget", panel.message)

    def test_steps_autoplay_and_stale_solution_protection(self):
        animator = Animator()
        animator.cube.apply("R U")
        panel = self.panel()
        panel.start(animator)
        deadline = time.monotonic() + 3
        while panel.job.busy and time.monotonic() < deadline:
            panel.update(animator)
        self.assertTrue(panel.job.result.optimal)
        self.assertEqual(panel.steps, ("U'", "R'"))
        panel.step_requested = True
        panel.update(animator)
        self.assertTrue(panel.docked)
        animator.update(1)
        panel.update(animator)
        self.assertEqual(panel.index, 1)
        self.assertFalse(animator.cube.solved)
        panel.autoplay = True
        panel.update(animator)
        animator.update(1)
        panel.update(animator)
        self.assertTrue(animator.cube.solved)
        self.assertEqual(panel.index, 2)
        self.assertFalse(panel.autoplay)
        animator.cube.move("F")
        panel.update(animator)
        self.assertIsNone(panel.steps)

    def test_solves_the_final_queue_and_does_not_change_a_running_move(self):
        animator = Animator()
        animator.enqueue("R U")
        animator.update(.1)
        before = animator.cube.snapshot(), animator.elapsed, tuple(animator.queue)
        panel = self.panel()
        panel.start(animator)
        panel.update(animator)
        self.assertEqual((animator.cube.snapshot(), animator.elapsed, tuple(animator.queue)), before)
        animator.update(1)
        panel.update(animator)
        self.assertIsNotNone(panel.steps)
        self.assertIsNotNone(checked_solution(animator.cube, panel.steps))

    def test_application_button_opens_solver_without_changing_cube(self):
        import pygame
        from flat_rubik.app import run
        from flat_rubik.editor import ColorEditor
        from flat_rubik.ui import layout
        panel = self.panel()
        panel.close()
        animator = Animator()
        animator.cube.move("F")
        before = animator.cube.snapshot()
        rect = layout((1080, 800))[4]["solve"]
        events = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=rect.center, button=1)]
        with patch("flat_rubik.app.SolvePanel", return_value=panel), \
                patch("flat_rubik.app.Animator", return_value=animator), \
                patch("flat_rubik.app.ColorEditor", return_value=ColorEditor()), \
                patch("pygame.event.get", return_value=events), patch.object(panel, "draw") as draw:
            run(max_frames=1, session_path=None)
        draw.assert_called_once()
        self.assertEqual(before, animator.cube.snapshot())


if __name__ == "__main__":
    unittest.main()
