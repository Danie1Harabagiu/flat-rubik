import pygame
import math

from pathlib import Path
import asyncio
import sys
from copy import deepcopy

from flat_rubik.animation import Animator
from flat_rubik.cube import scramble, FACE_COLORS
from flat_rubik.controls import move_for_click
from flat_rubik.geometry import center_at
from flat_rubik.renderer import BACKGROUND_RGB, text_surface
from flat_rubik.cube_view import draw_cube, view_regions, cube_face_at
from flat_rubik.ui import (layout, duration_at, render_controls,
                           visibility_button, render_visibility_button)
from flat_rubik.editor import ColorEditor
from flat_rubik.puzzle45 import Puzzle45
from flat_rubik.session import SessionStore, SESSION_PATH
from flat_rubik.solve_panel import SolvePanel
from flat_rubik.flat_view import FIT_MODES, draw_flat, flat_pointer


def run(max_frames=None, session_path=SESSION_PATH):
    """Desktop entry point; the browser uses run_async directly."""
    asyncio.run(run_async(max_frames=max_frames, session_path=session_path))


async def run_async(max_frames=None, session_path=SESSION_PATH):
    browser = sys.platform == "emscripten"
    pygame.init()
    size = (1080, 800)
    if browser:
        import platform
        size = (max(320, int(platform.window.innerWidth)), max(360, int(platform.window.innerHeight)))
    screen = pygame.display.set_mode(size, pygame.RESIZABLE)
    pygame.display.set_caption("Flat Rubik")
    clock = pygame.time.Clock()
    animator = Animator(duration=1.0)
    editor = ColorEditor(Path(__file__).resolve().parent.parent / "cube_colors.json")
    if editor.startup_cube is not None:
        animator.set_cube(editor.startup_cube)
    classic = animator
    variant = Puzzle45(duration=1.0)
    session = SessionStore(session_path)
    session.restore(classic, variant)
    solver = SolvePanel()
    editor_view = None
    running, paused, paths, dragging, double = True, False, False, False, False
    frames = 0
    active_finger = None
    controls_visible, fullscreen = True, False
    view_mode = "Ambele"
    fit_mode = "proportional"
    yaw, pitch = -.55, .45
    orbit = None
    windowed_size = size
    while running:
        if browser:
            viewport = (max(320, int(platform.window.innerWidth)), max(360, int(platform.window.innerHeight)))
            if screen.get_size() != viewport:
                screen = pygame.display.set_mode(viewport, pygame.RESIZABLE)
        dt = min(.1, clock.tick(0 if browser else 60) / 1000)
        for event in pygame.event.get():
            # Handle one finger and ignore SDL's duplicate synthetic mouse events.
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION) and getattr(event, "touch", False):
                continue
            if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
                if event.type == pygame.FINGERDOWN and active_finger is None:
                    active_finger = event.finger_id
                if event.finger_id != active_finger:
                    continue
                event_type = {pygame.FINGERDOWN: pygame.MOUSEBUTTONDOWN,
                              pygame.FINGERMOTION: pygame.MOUSEMOTION,
                              pygame.FINGERUP: pygame.MOUSEBUTTONUP}[event.type]
                if event.type == pygame.FINGERUP:
                    active_finger = None
                event = pygame.event.Event(event_type, pos=(round(event.x * screen.get_width()),
                                                            round(event.y * screen.get_height())), button=1)
            if solver.visible and event.type != pygame.QUIT:
                if event.type == pygame.VIDEORESIZE and not fullscreen:
                    screen = pygame.display.set_mode((max(320, event.w), max(360, event.h)), pygame.RESIZABLE)
                else:
                    solver.handle(event, classic, screen.get_size())
                continue
            board, panel, buttons, slider, actions, compact = layout(screen.get_size(), controls_visible)
            view_button = pygame.Rect(180, 8, max(1, min(200, screen.get_width() - 188)), 30)
            area = board.copy()
            area.y += 46
            area.h = max(1, area.h - 46)
            board, cube_rect = view_regions(area, "Cerc" if animator is variant or editor.editing else view_mode)
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE and not fullscreen:
                screen = pygame.display.set_mode((max(320, event.w), max(360, event.h)), pygame.RESIZABLE)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and visibility_button(screen.get_size()).collidepoint(event.pos):
                    controls_visible = not controls_visible
                    dragging = False
                    continue
                if event.button == 1 and view_button.collidepoint(event.pos):
                    view_mode = {"Cerc": "Cub", "Cub": "Ambele", "Ambele": "Cerc"}[view_mode]
                    orbit = None
                    continue
                if event.button in (1, 3) and cube_rect.collidepoint(event.pos):
                    local = (event.pos[0] - cube_rect.x, event.pos[1] - cube_rect.y)
                    face = cube_face_at(local, cube_rect.size, animator, yaw, pitch)
                    if event.button == 3:
                        if face:
                            animator.enqueue([face + "'"])
                    else:
                        orbit = dict(start=event.pos, last=event.pos, moved=False, face=face)
                    continue
                action = next((name for name, rect in actions.items() if rect.collidepoint(event.pos)), None)
                if event.button == 1 and action == "fit":
                    fit_mode = FIT_MODES[(FIT_MODES.index(fit_mode) + 1) % len(FIT_MODES)]
                elif event.button == 1 and action == "solve":
                    if not editor.editing:
                        animator = classic
                        solver.open_panel()
                        dragging, orbit = False, None
                elif event.button == 1 and action == "mode":
                    if not editor.editing:
                        animator = variant if animator is classic else classic
                        paused, dragging, double = False, False, False
                elif event.button == 1 and action == "edit":
                    animator = classic
                    if editor.editing:
                        editor.cancel()
                        editor_view = None
                    else:
                        editor.begin(animator.cube)
                        editor_view = Animator(cube=deepcopy(animator.cube))
                    dragging = False
                elif editor.editing:
                    if board.collidepoint(event.pos):
                        mapped = flat_pointer((event.pos[0] - board.x, event.pos[1] - board.y), board.size, fit_mode)
                        if mapped:
                            local, virtual = mapped
                            editor.paint(local, event.button, virtual)
                    elif event.button == 1 and action == "pause":
                        cube = editor.apply()
                        if cube is not None:
                            animator.set_cube(cube)
                            editor_view = None
                            paused, double = False, False
                    elif event.button == 1 and action == "paths":
                        editor.undo()
                    elif event.button == 1 and action == "reset":
                        editor.reset()
                    elif event.button == 1 and action == "shuffle":
                        editor.randomize()
                elif event.button == 1 and action == "shuffle":
                    animator.enqueue(scramble())
                elif event.button == 1 and controls_visible and slider.inflate(18, 16).collidepoint(event.pos):
                    dragging = True
                    animator.set_duration(duration_at(event.pos[0], slider))
                elif event.button == 1 and action:
                    if action == "pause":
                        paused = not paused
                    elif action == "paths":
                        paths = not paths
                    elif action == "reset":
                        animator.reset()
                        paused, double = False, False
                elif event.button in (1, 3):
                    face = next((f for f, rect in buttons.items() if rect.collidepoint(event.pos)), None)
                    inverse = event.button == 3 or (face and screen.get_width() < 600 and screen.get_height() >= 600 and event.pos[0] < buttons[face].centerx)
                    move = face + ("'" if inverse else "") if face else None
                    if board.collidepoint(event.pos):
                        local = (event.pos[0] - board.x, event.pos[1] - board.y)
                        mapped = flat_pointer(local, board.size, fit_mode)
                        move = move_for_click(mapped[0], event.button, mapped[1]) if mapped else None
                    if move:
                        animator.enqueue([move])
            elif event.type == pygame.MOUSEMOTION and orbit is not None:
                if math.dist(event.pos, orbit["start"]) > 8:
                    orbit["moved"] = True
                if orbit["moved"]:
                    yaw += (event.pos[0] - orbit["last"][0]) * .009
                    pitch = max(-1.5, min(1.5, pitch + (event.pos[1] - orbit["last"][1]) * .009))
                    orbit["last"] = event.pos
            elif event.type == pygame.MOUSEMOTION and dragging:
                animator.set_duration(duration_at(event.pos[0], slider))
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if (orbit is not None and not orbit["moved"] and orbit["face"]
                        and math.dist(event.pos, orbit["start"]) <= 8
                        and cube_rect.collidepoint(event.pos)):
                    animator.enqueue([orbit["face"]])
                dragging = False
                orbit = None
            elif event.type == pygame.KEYDOWN:
                key = pygame.key.name(event.key).upper()
                if event.key == pygame.K_t:
                    fit_mode = FIT_MODES[(FIT_MODES.index(fit_mode) + 1) % len(FIT_MODES)]
                elif event.key == pygame.K_s and not editor.editing:
                    animator = classic
                    solver.open_panel()
                    dragging, orbit = False, None
                elif event.key == pygame.K_v:
                    view_mode = {"Cerc": "Cub", "Cub": "Ambele", "Ambele": "Cerc"}[view_mode]
                    orbit = None
                elif event.key == pygame.K_h:
                    controls_visible = not controls_visible
                    dragging = False
                elif event.key == pygame.K_F11 and not browser:
                    if fullscreen:
                        screen = pygame.display.set_mode(windowed_size, pygame.RESIZABLE)
                    else:
                        windowed_size = screen.get_size()
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    fullscreen = not fullscreen
                    dragging = False
                elif event.key == pygame.K_ESCAPE and fullscreen:
                    screen = pygame.display.set_mode(windowed_size, pygame.RESIZABLE)
                    fullscreen = False
                elif event.key == pygame.K_e or editor.editing and event.key == pygame.K_ESCAPE:
                    animator = classic
                    if editor.editing:
                        editor.cancel()
                        editor_view = None
                    else:
                        editor.begin(animator.cube)
                        editor_view = Animator(cube=deepcopy(animator.cube))
                    dragging = False
                elif editor.editing:
                    if event.key == pygame.K_RETURN:
                        cube = editor.apply()
                        if cube is not None:
                            animator.set_cube(cube)
                            editor_view = None
                            paused, double = False, False
                    elif event.key == pygame.K_z and event.mod & pygame.KMOD_CTRL:
                        editor.undo()
                    elif event.key == pygame.K_DELETE:
                        editor.reset()
                elif event.key == pygame.K_ESCAPE:
                    running = False
                elif key in ("R", "L", "U", "D", "F", "B"):
                    suffix = "2" if double or event.mod & pygame.KMOD_CTRL else "'" if event.mod & pygame.KMOD_SHIFT else ""
                    if animator is variant and suffix == "2" and event.mod & pygame.KMOD_SHIFT:
                        suffix = "2'"
                    animator.enqueue([key + suffix])
                    double = False
                elif event.key == pygame.K_2:
                    double = not double
                elif event.key == pygame.K_SPACE:
                    animator.enqueue(scramble())
                elif event.key == pygame.K_HOME:
                    animator.reset()
                    paused, double = False, False
                elif event.key == pygame.K_p:
                    paused = not paused
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    animator.set_duration(min(3.0, animator.duration + .2))
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    animator.set_duration(max(.2, animator.duration - .2))
        if solver.visible and (solver.autoplay or solver.step_requested):
            paused = False
        if not paused and not editor.editing:
            animator.update(dt)
        solver.update(classic)
        session.save(classic, variant)
        playing_solution = solver.visible and solver.docked
        board, panel, buttons, slider, actions, compact = layout(screen.get_size(), controls_visible and not playing_solution)
        area = board.copy()
        area.y += 46
        area.h = max(1, area.h - 46)
        if solver.visible and solver.docked:
            area.h = max(1, area.h - 114)
        board, cube_rect = view_regions(area, "Cerc" if animator is variant or editor.editing else view_mode)
        mouse = pygame.mouse.get_pos()
        hovered = next((f for f, rect in buttons.items() if rect.collidepoint(mouse)), None)
        if board.collidepoint(mouse):
            mapped = flat_pointer((mouse[0] - board.x, mouse[1] - board.y), board.size, fit_mode)
            color = center_at(mapped[0], *mapped[1]) if mapped else None
            hovered = next((f for f, c in FACE_COLORS.items() if c == color), None)
        if solver.visible:
            hovered = None
        screen.fill(BACKGROUND_RGB)
        if board.w and board.h:
            board_screen = screen.subsurface(board)
            draw_flat(board_screen, mode=fit_mode, animator=editor_view if editor.editing else animator,
                 hovered=None if editor.editing else hovered, show_paths=paths and not editor.editing,
                 facelets=editor.colors if editor.editing else None)
        if cube_rect.w and cube_rect.h:
            draw_cube(screen.subsurface(cube_rect), animator, yaw, pitch)
        if controls_visible and not playing_solution:
            render_controls(screen, animator, paused, paths, hovered, editor=editor, session_message=session.message, fit_mode=fit_mode)
        render_visibility_button(screen, controls_visible)
        view_button = pygame.Rect(180, 8, max(1, min(200, screen.get_width() - 188)), 30)
        pygame.draw.rect(screen, (235, 224, 245), view_button, border_radius=7)
        caption = "45 grade: Cerc" if animator is variant else "Editor: Cerc" if editor.editing else "Vedere: " + view_mode + " [V]"
        label = text_surface(caption, 19, (43, 31, 61))
        screen.blit(label, label.get_rect(center=view_button.center))
        if solver.visible:
            solver.draw(screen)
        pygame.display.flip()
        await asyncio.sleep(0)
        frames += 1
        if max_frames is not None and frames >= max_frames:
            running = False
    solver.close()
    session.save(classic, variant)
    pygame.quit()
