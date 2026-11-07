import pygame

from pathlib import Path
from copy import deepcopy

from flat_rubik.animation import Animator
from flat_rubik.cube import scramble, FACE_COLORS
from flat_rubik.controls import move_for_click
from flat_rubik.geometry import center_at, board_point
from flat_rubik.renderer import draw, BACKGROUND_RGB
from flat_rubik.ui import layout, duration_at, render_controls
from flat_rubik.editor import ColorEditor
from flat_rubik.puzzle45 import Puzzle45
from flat_rubik.session import SessionStore, SESSION_PATH


def run(max_frames=None, session_path=SESSION_PATH):
    pygame.init()
    screen = pygame.display.set_mode((1080, 800), pygame.RESIZABLE)
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
    while running:
        dt = clock.tick(60) / 1000
        for event in pygame.event.get():
            board, panel, buttons, slider, actions, compact = layout(screen.get_size())
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((max(320, event.w), max(360, event.h)), pygame.RESIZABLE)
            elif event.type == pygame.MOUSEBUTTONDOWN:
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
                elif event.button == 1 and slider.inflate(18, 16).collidepoint(event.pos):
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
                    move = face + ("'" if event.button == 3 else "") if face else None
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
                if event.key == pygame.K_e or editor.editing and event.key == pygame.K_ESCAPE:
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
        board, panel, buttons, slider, actions, compact = layout(screen.get_size())
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
        render_controls(screen, animator, paused, paths, hovered, editor=editor, session_message=session.message)
        pygame.display.flip()
        frames += 1
        if max_frames is not None and frames >= max_frames:
            running = False
    session.save(classic, variant)
    pygame.quit()
