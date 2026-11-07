"""Modal solve controls: time budget, proof status and verified step playback."""
from copy import deepcopy
import math
import pygame

from flat_rubik.renderer import text_surface
from flat_rubik.solve_job import SearchJob
from flat_rubik.solver import SearchResult, history_solution
from flat_rubik.cube import inverse


def solve_layout(size):
    w, h = size
    panel = pygame.Rect(0, 0, min(744, w - 24), min(600, h - 24))
    panel.center = w / 2, h / 2
    x, y, width = panel.x + 12, panel.y + 12, panel.w - 24
    half = (width - 16) // 3
    fourth = (width - 24) // 4
    return panel, {
        "minus": pygame.Rect(x, y + 52, 30, 30),
        "budget": pygame.Rect(x + 36, y + 52, 78, 30),
        "plus": pygame.Rect(x + 120, y + 52, 30, 30),
        "search": pygame.Rect(x, y + 94, half, 32),
        "camera": pygame.Rect(x + half + 8, y + 94, half, 32),
        "stop": pygame.Rect(x + 2 * (half + 8), y + 94, half, 32),
        "steps": pygame.Rect(x, y + 184, width, max(24, panel.h - 272)),
        "back": pygame.Rect(x, panel.bottom - 42, fourth, 30),
        "next": pygame.Rect(x + fourth + 8, panel.bottom - 42, fourth, 30),
        "auto": pygame.Rect(x + 2 * (fourth + 8), panel.bottom - 42, fourth, 30),
        "close": pygame.Rect(x + 3 * (fourth + 8), panel.bottom - 42, fourth, 30),
    }


def playback_layout(size):
    w, h = size
    panel = pygame.Rect(8, h - 110, w - 16, 102)
    width = (panel.w - 40) // 5
    return panel, {name: pygame.Rect(panel.x + 8 + i * (width + 6), panel.y + 64, width, 30)
                   for i, name in enumerate(("back", "next", "auto", "plan", "close"))}


class SolvePanel:
    def __init__(self, job=None):
        self.job = job if job is not None else SearchJob()
        self.visible = False
        self.camera_requested = False
        self.budget_text = "30"
        self.budget_focused = False
        self.select_budget = False
        self.expected = None
        self.solution = None
        self.index = 0
        self.inflight = self.autoplay = self.step_requested = False
        self.inflight_direction = 1
        self.message = "Alege bugetul si apasa Cauta."
        self.scroll = 0
        self.docked = False

    def open_panel(self):
        self.close()
        self.job.result = SearchResult(status="idle")
        self.visible = True
        self.expected = self.solution = None
        self.index = self.scroll = 0
        self.inflight = False
        self.docked = False
        self.message = "Alege bugetul si apasa Cauta."

    def close(self):
        self.job.cancel()
        self.visible = self.autoplay = self.step_requested = self.budget_focused = False
        pygame.key.stop_text_input()

    @property
    def steps(self):
        if self.expected is None:
            return None
        return self.solution if self.solution is not None else self.job.result.best

    def start(self, animator):
        try:
            budget = float(self.budget_text.replace(",", "."))
            if not math.isfinite(budget) or not 1 <= budget <= 3600:
                raise ValueError
        except ValueError:
            self.message = "Buget: intre 1 si 3600 de secunde."
            return
        # Solve the final queued state, never a half-rotated visual frame.
        cube = deepcopy(animator.target if animator.target is not None else animator.cube)
        cube.apply(list(animator.queue))
        history = animator.history[:] + ([animator.current] if animator.current else []) + list(animator.queue)
        seed = history_solution(cube, history)
        self.expected = deepcopy(cube)
        self.solution = None
        self.index = self.scroll = 0
        self.inflight = self.autoplay = self.step_requested = False
        self.docked = False
        self.budget_focused = False
        pygame.key.stop_text_input()
        self.message = ""
        try:
            self.job.start(cube, budget, seed)
        except (ValueError, OSError, RuntimeError) as error:
            self.expected = None
            self.message = str(error)

    def _invalidate(self):
        self.job.cancel()
        self.expected = self.solution = None
        self.job.result = SearchResult(status="idle")
        self.autoplay = self.step_requested = self.inflight = False
        self.message = "Pozitia s-a schimbat. Apasa Cauta."

    def update(self, animator):
        if not self.visible:
            return
        self.job.poll()
        if self.expected is None:
            return
        if animator.pending:
            return
        if animator.cube.snapshot() != self.expected.snapshot():
            self._invalidate()
            return
        if self.inflight:
            self.index += self.inflight_direction
            self.inflight = False
        steps = self.steps
        if steps is None:
            return
        if self.autoplay or self.step_requested:
            direction = -1 if self.step_requested == -1 else 1
            if direction < 0 and self.index <= 0 or direction > 0 and self.index >= len(steps):
                self.autoplay = self.step_requested = False
                return
            self.docked = True
            self.job.cancel()
            if self.solution is None:
                self.solution = tuple(self.job.result.best)
            move = inverse(self.solution[self.index - 1]) if direction < 0 else self.solution[self.index]
            self.expected.move(move)
            animator.enqueue([move])
            self.inflight = True
            self.inflight_direction = direction
            self.step_requested = False

    def can_step(self, direction):
        if self.steps is None:
            return False
        position = self.index + (self.inflight_direction if self.inflight else 0)
        return position > 0 if direction < 0 else position < len(self.steps)

    def request_back(self):
        if self.can_step(-1):
            self.step_requested = -1
            self.autoplay = False

    def handle(self, event, animator, size):
        _, rects = playback_layout(size) if self.docked else solve_layout(size)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (4, 5):
                self.scroll = max(0, self.scroll + (1 if event.button == 5 else -1))
                return
            if event.button != 1:
                return
            action = next((key for key, rect in rects.items() if rect.collidepoint(event.pos)), None)
            self.budget_focused = action == "budget"
            if self.budget_focused:
                self.select_budget = True
                pygame.key.start_text_input()
            else:
                pygame.key.stop_text_input()
            if action == "close":
                self.close()
            elif action == "camera":
                self.job.cancel()
                self.autoplay = self.step_requested = False
                self.camera_requested = True
            elif action == "search":
                self.start(animator)
            elif action == "stop":
                self.job.cancel()
                self.autoplay = self.step_requested = False
            elif action == "plan":
                self.docked = self.autoplay = self.step_requested = False
            elif action in ("minus", "plus"):
                try:
                    value = float(self.budget_text.replace(",", "."))
                except ValueError:
                    value = 30
                self.budget_text = f"{max(1, min(3600, value + (10 if action == 'plus' else -10))):g}"
            elif action == "next" and self.steps is not None:
                self.step_requested = True
                self.autoplay = False
            elif action == "back":
                self.request_back()
            elif action == "auto" and self.steps is not None:
                self.autoplay = not self.autoplay
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - event.y)
        elif event.type == pygame.TEXTINPUT and self.budget_focused:
            value = "" if self.select_budget else self.budget_text
            self.budget_text = (value + "".join(c for c in event.text if c in "0123456789.,"))[:8]
            self.select_budget = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
            elif event.key == pygame.K_RETURN:
                self.start(animator)
            elif self.budget_focused and event.key == pygame.K_BACKSPACE:
                self.budget_text = "" if self.select_budget else self.budget_text[:-1]
                self.select_budget = False
            elif self.budget_focused and event.key == pygame.K_a and event.mod & pygame.KMOD_CTRL:
                self.select_budget = True
            elif not self.budget_focused and event.key == pygame.K_RIGHT and self.steps is not None:
                self.step_requested = True
                self.autoplay = False
            elif not self.budget_focused and event.key == pygame.K_LEFT:
                self.request_back()
            elif not self.budget_focused and event.key == pygame.K_SPACE and self.steps is not None:
                self.autoplay = not self.autoplay

    def draw(self, screen):
        if self.docked:
            self.draw_playback(screen)
            return
        panel, rects = solve_layout(screen.get_size())
        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shade.fill((24, 12, 38, 180))
        screen.blit(shade, (0, 0))
        pygame.draw.rect(screen, (244, 237, 250), panel, border_radius=10)
        pygame.draw.rect(screen, (105, 60, 139), panel, 2, border_radius=10)
        x, y = panel.x + 12, panel.y + 12

        def text(value, pos, size=20, color=(43, 31, 61), width=None):
            label = text_surface(value, size, color)
            available = width if width is not None else panel.right - 12 - pos[0]
            if label.get_width() > available:
                label = pygame.transform.smoothscale(label, (max(1, available), label.get_height()))
            screen.blit(label, pos)

        text("REZOLVARE RUBIK 90°", (x, y), 25)
        text("90° = 1 pas  |  180° = 2 pasi", (x, y + 28), 19)
        text("secunde", (x + 160, y + 59), 19)
        result = self.job.result
        captions = {"camera": "Camera", "minus": "-", "budget": self.budget_text, "plus": "+", "search": "Cauta",
                    "stop": "Opreste", "back": "Inapoi", "next": "Pas", "auto": "Pauza" if self.autoplay else "Automat", "close": "Inchide"}
        for name, caption in captions.items():
            rect = rects[name]
            disabled = name in ("next", "auto") and not self.can_step(1) or name == "back" and not self.can_step(-1)
            pygame.draw.rect(screen, (225, 217, 233) if disabled else (255, 255, 255), rect, border_radius=5)
            pygame.draw.rect(screen, (93, 40, 139) if name == "budget" and self.budget_focused else (181, 159, 198), rect, 2, border_radius=5)
            text(caption, (rect.x + 6, rect.y + 7), 19, width=rect.w - 12)
        if self.message:
            status = self.message
        elif result.optimal:
            status = f"Optim demonstrat: {len(result.best)} pasi."
        elif self.steps is not None:
            status = f"Solutie: {len(self.steps)} pasi. Optimul nu este demonstrat."
        elif result.status == "budget":
            status = "Buget epuizat, fara solutie. Mareste bugetul."
        elif result.status == "error":
            status = "Calculul nu a reusit. Poti incerca din nou."
        elif result.status == "cancelled":
            status = "Cautare oprita."
        else:
            status = "Caut o solutie..."
        text(status, (x, y + 137), 20)
        elapsed = self.job.elapsed
        progress = f"{elapsed:.1f}/{self.job.budget:g} s | Minim {result.lower_bound} pasi"
        if self.job.busy:
            progress += " | " + result.detail
        elif result.status == "budget":
            progress += " | Buget epuizat"
        text(progress, (x, y + 160), 18)
        steps_rect = rects["steps"]
        pygame.draw.rect(screen, (232, 221, 242), steps_rect, border_radius=5)
        steps = self.steps or ()
        columns = max(1, steps_rect.w // 54)
        rows = max(1, steps_rect.h // 28)
        max_scroll = max(0, math.ceil(len(steps) / columns) - rows)
        self.scroll = min(self.scroll, max_scroll)
        first = self.scroll * columns
        for item, move in enumerate(steps[first:first + columns * rows], first):
            row, col = divmod(item - first, columns)
            rect = pygame.Rect(steps_rect.x + col * 54 + 3, steps_rect.y + row * 28 + 3, 49, 23)
            pygame.draw.rect(screen, (185, 227, 198) if item < self.index else (210, 184, 240) if item == self.index else (255, 255, 255), rect, border_radius=4)
            text(f"{item + 1}.{move}", (rect.x + 3, rect.y + 4), 18, width=43)
        current = "Rezolvat." if steps and self.index >= len(steps) else f"Pas {self.index + 1}/{len(steps)}: {steps[self.index]}" if steps else ""
        text(current, (x, panel.bottom - 66), 19)

    def draw_playback(self, screen):
        panel, rects = playback_layout(screen.get_size())
        pygame.draw.rect(screen, (244, 237, 250), panel, border_radius=8)
        pygame.draw.rect(screen, (105, 60, 139), panel, 2, border_radius=8)

        def label(value, rect, size=19):
            text = text_surface(value, size, (43, 31, 61))
            if text.get_width() > rect.w - 12:
                text = pygame.transform.smoothscale(text, (max(1, rect.w - 12), text.get_height()))
            screen.blit(text, text.get_rect(center=rect.center))

        steps = self.steps or ()
        status = (f"Inapoi: {inverse(steps[self.index - 1])} | {self.index - 1}/{len(steps)}"
                  if self.inflight and self.inflight_direction < 0 else
                  "Rezolvat." if self.index >= len(steps) else f"Pas {self.index + 1}/{len(steps)}: {steps[self.index]}")
        label(status, pygame.Rect(panel.x + 8, panel.y + 5, panel.w - 16, 25), 22)
        proof = "Solutie minima demonstrata." if self.job.result.optimal else "Solutie verificata. Optimul nu este demonstrat."
        label(proof, pygame.Rect(panel.x + 8, panel.y + 32, panel.w - 16, 23))
        captions = {"back": "Inapoi", "next": "Pas", "auto": "Pauza" if self.autoplay else "Automat", "plan": "Plan", "close": "Inchide"}
        for name, rect in rects.items():
            disabled = name in ("next", "auto") and not self.can_step(1) or name == "back" and not self.can_step(-1)
            pygame.draw.rect(screen, (225, 217, 233) if disabled else (255, 255, 255), rect, border_radius=5)
            pygame.draw.rect(screen, (181, 159, 198), rect, 1, border_radius=5)
            label(captions[name], rect)
