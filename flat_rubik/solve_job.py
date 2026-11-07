"""Cancellable desktop process, or time-sliced browser search."""
from dataclasses import replace
import math
import sys
import time

from flat_rubik.solver import CACHE_DIR, SearchResult, checked_solution, search_events


def _worker(cube, deadline, seed, output, cache_dir):
    last_sent = 0
    last_best = None
    latest = SearchResult(best=seed)
    try:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            output.put(SearchResult(best=seed, status="budget"))
            return
        for result in search_events(cube, remaining, seed, cache_dir, use_fast_seed=True):
            latest = result
            now = time.monotonic()
            if result.status in ("done", "budget") or result.best != last_best or now - last_sent >= .1:
                output.put(result)
                last_sent = now
                last_best = result.best
    except Exception as error:
        output.put(replace(latest, status="error", detail=str(error)))


class SearchJob:
    def __init__(self, browser=None, cache_dir=CACHE_DIR):
        self.browser = sys.platform == "emscripten" if browser is None else browser
        self.cache_dir = cache_dir
        self.result = SearchResult(status="idle")
        self.busy = False
        self.process = self.output = self.events = None
        self.started = 0
        self.budget = 30

    def start(self, cube, budget, seed=None):
        if not math.isfinite(budget) or not 1 <= budget <= 3600:
            raise ValueError("Alege un buget intre 1 si 3600 de secunde.")
        self.cancel()
        seed = checked_solution(cube, seed)
        self.started, self.budget = time.monotonic(), budget
        self.result = SearchResult(best=seed)
        self.busy = True
        if self.browser:
            self.events = search_events(cube, budget, seed, cache_dir=self.cache_dir)
        else:
            import multiprocessing
            context = multiprocessing.get_context("spawn")
            self.output = context.Queue()
            self.process = context.Process(target=_worker, args=(cube, self.started + budget, seed, self.output, self.cache_dir), daemon=True)
            try:
                self.process.start()
            except (OSError, RuntimeError):
                self.process.close()
                self.output.close()
                self.process = self.output = None
                self.busy = False
                raise

    @property
    def elapsed(self):
        return min(self.budget, time.monotonic() - self.started) if self.busy else self.result.elapsed

    def poll(self):
        if not self.busy:
            return self.result
        if self.events is not None:
            until = time.monotonic() + .003
            while time.monotonic() < until:
                try:
                    self.result = next(self.events)
                except StopIteration:
                    self._stop()
                    break
                if self.result.status in ("done", "budget", "error"):
                    self.result = replace(self.result, elapsed=self.elapsed)
                    self._stop()
                    break
        elif self.output is not None:
            from queue import Empty
            try:
                while True:
                    self.result = self.output.get_nowait()
            except Empty:
                pass
            if self.result.status in ("done", "budget", "error"):
                self.result = replace(self.result, elapsed=self.elapsed)
                self._stop()
            elif self.process is not None and not self.process.is_alive() and self.process.exitcode not in (None, 0):
                self.result = replace(self.result, status="error", detail="Calculul s-a oprit neasteptat.")
                self._stop()
        if self.busy and time.monotonic() - self.started >= self.budget:
            elapsed = self.budget
            self._stop()
            self.result = replace(self.result, status="budget", elapsed=elapsed, detail="Buget epuizat")
        return self.result

    def _stop(self):
        self.busy = False
        if self.process is not None:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=.1)
            self.process.close()
        if self.output is not None:
            self.output.close()
        self.process = self.output = self.events = None

    def cancel(self):
        if self.busy:
            elapsed = time.monotonic() - self.started
            self._stop()
            self.result = replace(self.result, status="cancelled", elapsed=elapsed)
