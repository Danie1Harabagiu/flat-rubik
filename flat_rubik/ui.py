"""Responsive controls for the circular board; all rectangles are window-local."""
import pygame
from collections import Counter

from flat_rubik.cube import FACE_COLORS
from flat_rubik.renderer import CULORI_RGB, text_surface, draw_rotation_arrow
from flat_rubik.flat_view import FIT_LABELS

TEXT = (43, 31, 61)
PANEL = (235, 224, 245)
NAMES = {"F": "Rosu", "B": "Portocaliu", "U": "Galben", "R": "Verde", "D": "Alb", "L": "Albastru"}
MIN_DURATION, MAX_DURATION = .2, 3.0


def layout(size, controls_visible=True, editing=False, face_buttons=None):
    w, h = size
    if not controls_visible:
        return pygame.Rect(0, 0, w, h), pygame.Rect(0, 0, 0, 0), {}, pygame.Rect(0, 0, 0, 0), {}, False
    phone = w < 600 and h >= 600
    show_faces = (phone if face_buttons is None else face_buttons) and not editing
    if phone:
        panel_height = 292 if show_faces else 196
        panel = pygame.Rect(0, h - panel_height, w, panel_height)
        board = pygame.Rect(0, 0, w, h - panel_height)
        x, y = 16, panel.y + 16
        usable = w - 32
        width = (usable - 16) // 3
        buttons = ({face: pygame.Rect(x + (i % 3) * (width + 8), y + 54 + (i // 3) * 48, width, 44)
                    for i, face in enumerate(NAMES)} if show_faces else {})
        slider = pygame.Rect(x + 20, y + 26, usable - 40, 18)
        start = y + (151 if show_faces else 55)
        rows = ((("pause", "paths", "reset"), ("edit", "shuffle", "camera"), ("mode", "fit", "solve")) if editing else
                (("pause", "reset", "shuffle"), ("edit", "camera", "faces"), ("mode", "fit", "solve")))
        actions = {}
        for row, names in enumerate(rows):
            action_width = (usable - (len(names) - 1) * 8) // len(names)
            for col, name in enumerate(names):
                actions[name] = pygame.Rect(x + col * (action_width + 8), start + row * 38, action_width, 32)
        return board, panel, buttons, slider, actions, True
    if w >= 960 and h >= 780:
        board = pygame.Rect(0, 0, w - 240, h)
        panel = pygame.Rect(w - 240, 0, 240, h)
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
        if show_faces:
            for i, face in enumerate(NAMES):
                buttons[face] = pygame.Rect(x + i * (button_width + 5), y + 35, button_width, 30)
        slider = pygame.Rect(x + 26, y + 102, max(1, usable - 52), 18)
        row = y + 139
        names = ("pause", "paths", "reset") if editing else ("pause", "reset")
        width = max(1, (usable - (len(names) - 1) * 8) // len(names))
        actions = {name: pygame.Rect(x + i * (width + 8), row, width, 30)
                   for i, name in enumerate(names)}
        actions["edit"] = pygame.Rect(x + usable - 172, y - 3, 82, 26)
        actions["shuffle"] = pygame.Rect(x + usable - 86, y - 3, 86, 26)
        actions["camera"] = pygame.Rect(x + usable - 258, y - 3, 80, 26)
        actions["mode"] = pygame.Rect(x, y + 173, usable, 20)
        actions["faces"] = pygame.Rect(x + usable - 78, y + 77, 78, 22)
    else:
        if show_faces:
            face_width = (usable - 8) // 2
            for i, face in enumerate(NAMES):
                buttons[face] = pygame.Rect(x + (i % 2) * (face_width + 8), y + 105 + (i // 2) * 48, face_width, 40)
        slider = pygame.Rect(x + 8, y + (320 if show_faces else 160), usable - 16, 20)
        names = ("pause", "paths", "reset", "edit", "shuffle") if editing else ("pause", "reset", "edit", "shuffle")
        actions = {name: pygame.Rect(x, slider.y + 45 + i * 46, usable, 36)
                   for i, name in enumerate(names)}
        actions["mode"] = pygame.Rect(x, y + 79, usable, 22)
        actions["faces"] = pygame.Rect(x, y + 55, usable, 20)
    if not compact:
        edit = actions["edit"]
        edit.w = (usable - 8) // 2
        actions["camera"] = pygame.Rect(edit.right + 8, edit.y, usable - edit.w - 8, edit.h)
    mode = actions["mode"]
    mode.w = (usable - 12) // 3
    actions["fit"] = pygame.Rect(mode.right + 6, mode.y, mode.w, mode.h)
    actions["solve"] = pygame.Rect(actions["fit"].right + 6, mode.y, usable - 2 * mode.w - 12, mode.h)
    return board, panel, buttons, slider, actions, compact


def visibility_button(size):
    return pygame.Rect(8, 8, 164, 30)


def zoom_buttons(board):
    if board.w < 80 or board.h < 60:
        return {}
    width = min(280, board.w - 12)
    x, y = board.centerx - width // 2, board.bottom - 34
    return {name: pygame.Rect(x + round(start * width), y, round(span * width) - 4, 28)
            for name, start, span in (("out", 0, .15), ("in", .15, .15),
                                      ("axis", .30, .48), ("reset", .78, .22))}


def render_zoom(screen, board, zoom, axis):
    labels = {"out": "-", "in": "+", "axis": f"{axis} {zoom[0]:.0%}/{zoom[1]:.0%}", "reset": "100%"}
    for name, rect in zoom_buttons(board).items():
        pygame.draw.rect(screen, PANEL, rect, border_radius=6)
        pygame.draw.rect(screen, (120, 85, 150), rect, 1, border_radius=6)
        label = text_surface(labels[name], 18 if name == "axis" else 21, TEXT)
        if label.get_width() > rect.w - 4:
            label = pygame.transform.smoothscale(label, (max(1, rect.w - 4), label.get_height()))
        screen.blit(label, label.get_rect(center=rect.center))


def render_visibility_button(screen, visible):
    rect = visibility_button(screen.get_size())
    pygame.draw.rect(screen, PANEL, rect, border_radius=7)
    label = text_surface("Ascunde butoane [H]" if visible else "Arata butoane [H]", 19, TEXT)
    screen.blit(label, label.get_rect(center=rect.center))


def duration_at(x, slider):
    fraction = max(0, min(1, (x - slider.left) / max(1, slider.w)))
    return MIN_DURATION + fraction * (MAX_DURATION - MIN_DURATION)


def render_controls(screen, animator, paused, paths, hovered=None, editor=None, session_message=None, fit_mode="proportional", face_buttons=None):
    editing = editor is not None and editor.editing
    board, panel, buttons, slider, actions, compact = layout(screen.get_size(), editing=editing, face_buttons=face_buttons)
    touch_layout = screen.get_width() < 600 and screen.get_height() >= 600
    pygame.draw.rect(screen, PANEL, panel)

    def text(value, pos, color=TEXT, small_font=False):
        label = text_surface(value, 19 if small_font else 22, color)
        available = max(1, panel.right - 12 - pos[0])
        if label.get_width() > available:
            label = pygame.transform.smoothscale(label, (available, max(1, round(label.get_height() * available / label.get_width()))))
        screen.blit(label, pos)

    x, y = panel.x + 16, panel.y + 16
    variant = getattr(animator, "step_degrees", 90) == 45
    if not touch_layout and (not compact or panel.w > 600):
        text("CULORI" if editing else "FLAT RUBIK" if compact else "FLAT RUBIK", (x, y))
    if not compact:
        text("Clic pe piesa: culoarea urmatoare." if editing else "Stanga: orar   Dreapta: invers", (x, y + 34), small_font=True)
    active = None if editing else animator.current[0] if animator.current else None
    if editing:
        hovered = None
    for face, rect in buttons.items():
        pygame.draw.rect(screen, (255, 255, 255), rect, border_radius=7)
        pygame.draw.rect(screen, TEXT if face in (hovered, active) else (195, 176, 212), rect,
                         3 if face in (hovered, active) else 1, border_radius=7)
        if compact:
            pygame.draw.rect(screen, CULORI_RGB[FACE_COLORS[face]], rect.inflate(-6, -6), border_radius=4)
            if touch_layout and not editing:
                pygame.draw.line(screen, TEXT, (rect.centerx, rect.y + 5), (rect.centerx, rect.bottom - 5))
                for direction, px in ((-1, rect.x + rect.w / 4), (1, rect.x + 3 * rect.w / 4)):
                    pygame.draw.circle(screen, TEXT, (round(px), rect.centery), 13)
                    draw_rotation_arrow(screen, (px, rect.centery), direction, face, 1.35)
            else:
                label = text_surface(NAMES[face] if editing else face, 19 if editing else 22, TEXT)
                if label.get_width() > rect.w - 8:
                    label = pygame.transform.smoothscale(label, (max(1, rect.w - 8), 12))
                screen.blit(label, label.get_rect(center=rect.center))
        else:
            pygame.draw.circle(screen, CULORI_RGB[FACE_COLORS[face]], (rect.x + 15, rect.centery), 7)
            pygame.draw.circle(screen, TEXT, (rect.x + 15, rect.centery), 7, 1)
            text(NAMES[face] if editing else f"{face}  {NAMES[face]}", (rect.x + 29, rect.y + 12), small_font=True)
    label_y = y if touch_layout else y + 77 if compact else slider.y - 45
    counts = Counter(editor.colors.values()) if editing else {}
    count_label = "  ".join(f"{c}:{counts[color]}" for c, color in zip("RPGVAB", ("rosu", "portocaliu", "galben", "verde", "alb", "albastru"))) if editing else ""
    text(count_label if editing else f"Durata rotatiei: {animator.duration:.1f} s", (x, label_y))
    if editing:
        # Keep validation feedback beside the palette, also in compact windows.
        words = (editor.message or "9 din fiecare culoare. Apoi Aplica.").split()
        lines, line = [], ""
        for word in words:
            candidate = (line + " " + word).strip()
            if text_surface(candidate, 19, TEXT).get_width() > panel.w - 32 and line:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
        for i, line in enumerate(lines[:2 if compact else 3]):
            text(line, (x, (y + 22 if touch_layout else y + 101 if compact else slider.y - 20) + i * (15 if touch_layout else 17)),
                 color=(160, 35, 60) if editor.error else TEXT, small_font=True)
    elif not compact:
        text("rapid                  lent", (x + 4, slider.y - 20), small_font=True)
    if not editing:
        pygame.draw.line(screen, (166, 140, 187), (slider.left, slider.centery), (slider.right, slider.centery), 5)
    fraction = max(0, min(1, (animator.duration - MIN_DURATION) / (MAX_DURATION - MIN_DURATION)))
    knob = (round(slider.left + fraction * slider.w), slider.centery)
    if not editing:
        pygame.draw.circle(screen, TEXT, knob, 9)
    captions = {"camera": "Camera", "pause": "Continua" if paused else "Pauza",
                "paths": "Trasee: DA" if paths else "Trasee: NU", "reset": "Resetare",
                "edit": "Rubik: culori" if variant else "Culori", "shuffle": "Amesteca",
                "mode": "Mod: 45°" if variant else "Mod: 90°", "solve": "Rubik: rezolva" if variant else "Rezolvare",
                "fit": FIT_LABELS[fit_mode], "faces": "Fete: DA" if buttons else "Fete: NU"}
    if editing:
        captions.update(pause="Aplica", paths="Anuleaza", reset="Rezolvat", edit="Renunta", shuffle="Random valid")
    for name, rect in actions.items():
        pygame.draw.rect(screen, (255, 255, 255), rect, border_radius=7)
        pygame.draw.rect(screen, (195, 176, 212), rect, 1, border_radius=7)
        label = text_surface(captions[name], 19 if name == "mode" else 22, TEXT)
        if label.get_width() > rect.w - 6:
            label = pygame.transform.smoothscale(label, (max(1, rect.w - 6), 14))
        screen.blit(label, label.get_rect(center=rect.center))
    if not compact:
        status_y = actions["shuffle"].bottom + 18
        text(f"Mutare: {animator.current or '-'}   |   Coada: {animator.pending}", (x, status_y))
        solved = animator.is_solved if variant else animator.cube.solved
        state = "Editezi culorile reale ale cubului." if editing else "Pauza" if paused else "Rotatie in curs" if animator.current else "Rezolvat" if solved else "Puzzle amestecat"
        text(state, (x, status_y + 25))
        lines = ("Clicuri repetate: schimba culoarea", "Ctrl+Z: anuleaza ultima culoare", "Enter: aplica | Esc: renunta", "Random valid: configuratie posibila") if editing else ("45°: orice fata, fara aliniere." if variant else "Trage piesele pentru rotire.", "P: pauza | +/-: durata", "Spatiu: amestecare", "Home: reset | Esc: iesire", session_message or "Salvare automata dupa mutare.")
        for i, line in enumerate(lines):
            text(line, (x, status_y + 50 + i * 19), small_font=True)
    return board
