import pygame

from pathlib import Path
import asyncio
import sys
from copy import deepcopy

from flat_rubik.animation import Animator
from flat_rubik.cube import scramble, FACE_COLORS
from flat_rubik.controls import move_for_click
from flat_rubik.geometry import center_at, board_point
from flat_rubik.renderer import draw, BACKGROUND_RGB
from flat_rubik.ui import (layout, duration_at, render_controls,
                           visibility_button, render_visibility_button)
from flat_rubik.editor import ColorEditor
from flat_rubik.puzzle45 import Puzzle45
from flat_rubik.session import SessionStore, SESSION_PATH


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
    editor_view = None
    running, paused, paths, dragging, double = True, False, False, False, False
    frames = 0
    active_finger = None
    controls_visible, fullscreen = True, False
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
            board, panel, buttons, slider, actions, compact = layout(screen.get_size(), controls_visible)
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE and not fullscreen:
                screen = pygame.display.set_mode((max(320, event.w), max(360, event.h)), pygame.RESIZABLE)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and visibility_button(screen.get_size()).collidepoint(event.pos):
                    controls_visible = not controls_visible
                    dragging = False
                    continue
                action = next((name for name, rect in actions.items() if rect.collidepoint(event.pos)), None)
                if event.button == 1 and action == "mode":
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
                        local = board_point((event.pos[0] - board.x, event.pos[1] - board.y), *board.size, inverse=True)
                        editor.paint(local, event.button, board.size)
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
                        local = board_point(local, *board.size, inverse=True)
                        move = move_for_click(local, event.button, board.size)
                    if move:
                        animator.enqueue([move])
            elif event.type == pygame.MOUSEMOTION and dragging:
                animator.set_duration(duration_at(event.pos[0], slider))
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = False
            elif event.type == pygame.KEYDOWN:
                key = pygame.key.name(event.key).upper()
                if event.key == pygame.K_h:
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
        if not paused and not editor.editing:
            animator.update(dt)
        session.save(classic, variant)
        board, panel, buttons, slider, actions, compact = layout(screen.get_size(), controls_visible)
        mouse = pygame.mouse.get_pos()
        hovered = next((f for f, rect in buttons.items() if rect.collidepoint(mouse)), None)
        if board.collidepoint(mouse):
            local = board_point((mouse[0] - board.x, mouse[1] - board.y), *board.size, inverse=True)
            color = center_at(local, *board.size)
            hovered = next((f for f, c in FACE_COLORS.items() if c == color), None)
        screen.fill(BACKGROUND_RGB)
        board_screen = screen.subsurface(board)
        draw(board_screen, animator=editor_view if editor.editing else animator,
             hovered=None if editor.editing else hovered, show_paths=paths and not editor.editing,
             facelets=editor.colors if editor.editing else None)
        if controls_visible:
            render_controls(screen, animator, paused, paths, hovered, editor=editor, session_message=session.message)
        render_visibility_button(screen, controls_visible)
        pygame.display.flip()
        await asyncio.sleep(0)
        frames += 1
        if max_frames is not None and frames >= max_frames:
            running = False
    session.save(classic, variant)
    pygame.quit()
