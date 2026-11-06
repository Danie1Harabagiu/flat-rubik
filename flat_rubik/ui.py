"""Responsive controls for the circular board; all rectangles are window-local."""
import pygame

from flat_rubik.cube import FACE_COLORS
from flat_rubik.renderer import CULORI_RGB, text_surface

TEXT = (43, 31, 61)
PANEL = (235, 224, 245)
NAMES = {"F": "Rosu", "B": "Portocaliu", "U": "Galben", "R": "Verde", "D": "Alb", "L": "Albastru"}
MIN_DURATION, MAX_DURATION = .2, 3.0


def layout(size):
    w, h = size
    if w >= 960 and h >= 740:
        board = pygame.Rect(0, 0, w - 280, h)
        panel = pygame.Rect(w - 280, 0, 280, h)
        compact = False
    else:
        panel_height = min(210, max(1, h - 120))
        board = pygame.Rect(0, 0, w, h - panel_height)
        panel = pygame.Rect(0, h - panel_height, w, panel_height)
        compact = True
    x, y = panel.x + 16, panel.y + 16
    usable = max(1, panel.w - 32)
    buttons = {}
    if compact:
        button_width = max(1, (usable - 25) // 6)
        for i, face in enumerate(NAMES):
            buttons[face] = pygame.Rect(x + i * (button_width + 5), y + 35, button_width, 30)
        slider = pygame.Rect(x + 26, y + 102, max(1, usable - 52), 18)
        row = y + 139
        width = max(1, (usable - 16) // 3)
        actions = {name: pygame.Rect(x + i * (width + 8), row, width, 30)
                   for i, name in enumerate(("pause", "paths", "reset"))}
    else:
        for i, face in enumerate(NAMES):
            buttons[face] = pygame.Rect(x + (i % 2) * 128, y + 105 + (i // 2) * 48, 120, 40)
        slider = pygame.Rect(x + 8, y + 320, usable - 16, 20)
        actions = {name: pygame.Rect(x, y + 365 + i * 46, usable, 36)
                   for i, name in enumerate(("pause", "paths", "reset"))}
    return board, panel, buttons, slider, actions, compact


def duration_at(x, slider):
    fraction = max(0, min(1, (x - slider.left) / max(1, slider.w)))
    return MIN_DURATION + fraction * (MAX_DURATION - MIN_DURATION)


def render_controls(screen, animator, paused, paths, hovered=None):
    board, panel, buttons, slider, actions, compact = layout(screen.get_size())
    pygame.draw.rect(screen, PANEL, panel)

    def text(value, pos, color=TEXT, small_font=False):
        label = text_surface(value, 19 if small_font else 22, color)
        screen.blit(label, pos)

    x, y = panel.x + 16, panel.y + 16
    text("FLAT RUBIK  |  Alege o fata", (x, y))
    if not compact:
        text("Stanga: orar   Dreapta: invers", (x, y + 34), small_font=True)
        text("Centrele si butoanele sunt active.", (x, y + 57), small_font=True)
    active = animator.current[0] if animator.current else None
    for face, rect in buttons.items():
        pygame.draw.rect(screen, (255, 255, 255), rect, border_radius=7)
        pygame.draw.rect(screen, TEXT if face in (hovered, active) else (195, 176, 212), rect,
                         3 if face in (hovered, active) else 1, border_radius=7)
        if compact:
            label = text_surface(face, 22, TEXT)
            screen.blit(label, label.get_rect(center=rect.center))
        else:
            pygame.draw.circle(screen, CULORI_RGB[FACE_COLORS[face]], (rect.x + 15, rect.centery), 7)
            pygame.draw.circle(screen, TEXT, (rect.x + 15, rect.centery), 7, 1)
            text(f"{face}  {NAMES[face]}", (rect.x + 29, rect.y + 12), small_font=True)
    label_y = y + 77 if compact else y + 275
    text(f"Durata rotatiei: {animator.duration:.1f} s", (x, label_y))
    if not compact:
        text("rapid                             lent", (x + 4, y + 300), small_font=True)
    pygame.draw.line(screen, (166, 140, 187), (slider.left, slider.centery), (slider.right, slider.centery), 5)
    fraction = max(0, min(1, (animator.duration - MIN_DURATION) / (MAX_DURATION - MIN_DURATION)))
    knob = (round(slider.left + fraction * slider.w), slider.centery)
    pygame.draw.circle(screen, TEXT, knob, 9)
    captions = {"pause": "Continua" if paused else "Pauza",
                "paths": "Trasee: DA" if paths else "Trasee: NU", "reset": "Resetare"}
    for name, rect in actions.items():
        pygame.draw.rect(screen, (255, 255, 255), rect, border_radius=7)
        pygame.draw.rect(screen, (195, 176, 212), rect, 1, border_radius=7)
        label = text_surface(captions[name], 22, TEXT)
        if label.get_width() > rect.w - 6:
            label = pygame.transform.smoothscale(label, (max(1, rect.w - 6), 14))
        screen.blit(label, label.get_rect(center=rect.center))
    if not compact:
        status_y = y + 525
        text(f"Mutare: {animator.current or '-'}   |   Coada: {animator.pending}", (x, status_y))
        state = "Pauza" if paused else "Rotatie in curs" if animator.current else "Rezolvat" if animator.cube.solved else "Cub amestecat"
        text(state, (x, status_y + 25))
        legend = "Cerc: plecare  |  Sageata: sosire" if paths else "Piesele raman unite in rotatie."
        for i, line in enumerate((legend, "P: pauza  |  +/-: durata", "Spatiu: amestecare", "Home: reset  |  Esc: iesire", "R L U D F B: rotatie", "Shift: invers  |  Ctrl: dublu")):
            text(line, (x, status_y + 55 + i * 21), small_font=True)
    return board
