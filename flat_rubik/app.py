import pygame
import math

from pathlib import Path
import asyncio
import sys
from copy import deepcopy

from flat_rubik.animation import Animator
from flat_rubik.cube import scramble, FACE_COLORS
from flat_rubik.geometry import center_at
from flat_rubik.renderer import BACKGROUND_RGB, text_surface
from flat_rubik.cube_view import draw_cube, view_regions, cube_face_at
from flat_rubik.ui import (layout, duration_at, render_controls,
                           visibility_button, render_visibility_button, zoom_buttons, render_zoom)
from flat_rubik.editor import ColorEditor, slot_at
from flat_rubik.puzzle45 import Puzzle45
from flat_rubik.session import SessionStore, SESSION_PATH
from flat_rubik.solve_panel import SolvePanel
from flat_rubik.flat_view import FIT_MODES, UNWRAPPED, UNWRAPPED_CUBE, draw_flat, flat_pointer
from flat_rubik.preferences import PreferencesStore
from flat_rubik.camera_capture import CameraSession
from flat_rubik.state import facelets
from flat_rubik.drag_turn import DragTurn


def run(max_frames=None, session_path=SESSION_PATH):
    """Desktop entry point; the browser uses run_async directly."""
    asyncio.run(run_async(max_frames=max_frames, session_path=session_path))


async def run_async(max_frames=None, session_path=SESSION_PATH):
    browser = sys.platform == "emscripten"
    preferences = PreferencesStore(Path(session_path).with_name("puzzle_settings.json") if session_path else None)
    settings = preferences.values
    pygame.init()
    size = tuple(settings["window_size"])
    if browser:
        import platform
        size = (max(320, int(platform.window.innerWidth)), max(360, int(platform.window.innerHeight)))
    fullscreen = settings["fullscreen"] and not browser
    screen = pygame.display.set_mode((0, 0) if fullscreen else size, pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE)
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
    if "rubik_duration" in preferences.present_keys:
        classic.set_duration(settings["rubik_duration"])
    if "puzzle45_duration" in preferences.present_keys:
        variant.set_duration(settings["puzzle45_duration"])
    animator = variant if settings["active_mode"] == "45" else classic
    camera = CameraSession()
    solver = SolvePanel()
    solver.budget_text = f"{settings['search_budget']:g}"
    editor_view = None
    running, paused, paths, dragging, double = True, settings["paused"], False, False, False
    frames = 0
    active_finger = None
    controls_visible = settings["controls_visible"]
    face_buttons = settings["face_buttons"]
    view_mode = settings["view_mode"]
    fit_mode = settings["fit_mode"]
    zoom_x, zoom_y, zoom_axis = settings["zoom_x"], settings["zoom_y"], settings["zoom_axis"]
    unwrapped_zoom_x, unwrapped_zoom_y = settings["unwrapped_zoom_x"], settings["unwrapped_zoom_y"]
    equal_pieces = settings["equal_pieces"]
    fingers, pinch = {}, None
    yaw, pitch = settings["yaw"], settings["pitch"]
    orbit = None
    flat_drag = None
    editor_painting = False
    editor_paint_slot = None
    windowed_size = size
    if view_mode in (UNWRAPPED, UNWRAPPED_CUBE):
        uniform = math.sqrt(unwrapped_zoom_x * unwrapped_zoom_y)
        unwrapped_zoom_x = unwrapped_zoom_y = uniform
        zoom_axis = "XY"

    def save_preferences(force=False):
        try:
            budget = float(solver.budget_text.replace(",", "."))
            if not math.isfinite(budget) or not 1 <= budget <= 3600:
                raise ValueError
        except ValueError:
            budget = preferences.values["search_budget"]
        preferences.save({"fit_mode": fit_mode, "view_mode": view_mode, "controls_visible": controls_visible,
                          "paths": paths, "paused": paused, "fullscreen": fullscreen,
                          "active_mode": "45" if animator is variant else "rubik",
                          "window_size": list(windowed_size if fullscreen else screen.get_size()),
                          "yaw": (yaw + math.pi) % math.tau - math.pi, "pitch": pitch,
                          "search_budget": budget, "rubik_duration": classic.duration,
                          "puzzle45_duration": variant.duration, "face_buttons": face_buttons, "zoom_x": zoom_x, "zoom_y": zoom_y,
                          "unwrapped_zoom_x": unwrapped_zoom_x, "unwrapped_zoom_y": unwrapped_zoom_y,
                          "zoom_axis": zoom_axis, "equal_pieces": equal_pieces}, force=force)
    def flat_mode():
        return UNWRAPPED if view_mode in (UNWRAPPED, UNWRAPPED_CUBE) and animator is not variant else fit_mode

    def active_zoom():
        return (unwrapped_zoom_x, unwrapped_zoom_y) if flat_mode() == UNWRAPPED else (zoom_x, zoom_y)

    def paint_editor(point, button, size):
        nonlocal editor_paint_slot
        slot = slot_at(point, size)
        if slot is not None and slot != editor_paint_slot:
            editor.paint(point, button, size)
        editor_paint_slot = slot

    def set_zoom(factor, axis=None, base=None):
        nonlocal zoom_x, zoom_y, unwrapped_zoom_x, unwrapped_zoom_y, flat_drag
        axis = "XY" if flat_mode() == UNWRAPPED else axis or zoom_axis
        x, y = base if base is not None else active_zoom()
        unwrapped = flat_mode() == UNWRAPPED
        if axis in ("XY", "X"):
            x = max(.4, min(3., x * factor))
        if axis in ("XY", "Y"):
            y = max(.4, min(3., y * factor))
        if unwrapped:
            unwrapped_zoom_x, unwrapped_zoom_y = x, y
        else:
            zoom_x, zoom_y = x, y
        flat_drag = None

    while running:
        if browser:
            viewport = (max(320, int(platform.window.innerWidth)), max(360, int(platform.window.innerHeight)))
            if screen.get_size() != viewport:
                flat_drag, pinch, active_finger = None, None, None
                fingers.clear()
                screen = pygame.display.set_mode(viewport, pygame.RESIZABLE)
        dt = min(.1, clock.tick(0 if browser else 60) / 1000)
        for event in pygame.event.get():
            # Handle touch gestures and ignore SDL's duplicate synthetic mouse events.
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION) and getattr(event, "touch", False):
                continue
            if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
                point = (event.x * screen.get_width(), event.y * screen.get_height())
                if event.type == pygame.FINGERUP:
                    fingers.pop(event.finger_id, None)
                else:
                    fingers[event.finger_id] = point
                if pinch is None and len(fingers) == 2 and not (editor.editing or solver.visible or camera.active):
                    pinch_area = layout(screen.get_size(), controls_visible, face_buttons=face_buttons)[0].copy()
                    pinch_area.y += 46
                    pinch_area.h = max(1, pinch_area.h - 46)
                    pinch_board, _ = view_regions(pinch_area, "Cerc" if animator is variant or (editor.editing and flat_mode() != UNWRAPPED) else view_mode)
                    ids = tuple(fingers)
                    distance = math.dist(fingers[ids[0]], fingers[ids[1]])
                    if distance >= 12 and all(pinch_board.collidepoint(p) for p in fingers.values()):
                        pinch = (ids, distance, active_zoom())
                        flat_drag, orbit, dragging, active_finger = None, None, False, None
                if pinch is not None:
                    ids, distance, base_zoom = pinch
                    if all(key in fingers for key in ids):
                        factor = math.dist(fingers[ids[0]], fingers[ids[1]]) / distance
                        set_zoom(factor, base=base_zoom)
                    if not fingers:
                        pinch = None
                    continue
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
            if event.type in (pygame.KEYDOWN, pygame.VIDEORESIZE, pygame.WINDOWFOCUSLOST, pygame.QUIT):
                flat_drag = None
            if event.type in (pygame.WINDOWFOCUSLOST, pygame.VIDEORESIZE):
                active_finger = None
                fingers.clear()
                pinch = None
                orbit, dragging = None, False
            if camera.active and event.type != pygame.QUIT:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE or event.type == pygame.MOUSEBUTTONDOWN and camera.bridge is None:
                    camera.close()
                continue
            if solver.visible and event.type != pygame.QUIT:
                if event.type == pygame.VIDEORESIZE and not fullscreen:
                    screen = pygame.display.set_mode((max(320, event.w), max(360, event.h)), pygame.RESIZABLE)
                else:
                    solver.handle(event, classic, screen.get_size())
                continue
            board, panel, buttons, slider, actions, compact = layout(screen.get_size(), controls_visible, editing=editor.editing, face_buttons=face_buttons)
            view_button = pygame.Rect(180, 8, max(1, min(200, screen.get_width() - 188)), 30)
            area = board.copy()
            area.y += 46
            area.h = max(1, area.h - 46)
            board, cube_rect = view_regions(area, "Cerc" if animator is variant or (editor.editing and flat_mode() != UNWRAPPED) else view_mode)
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE and not fullscreen:
                screen = pygame.display.set_mode((max(320, event.w), max(360, event.h)), pygame.RESIZABLE)
            elif event.type == pygame.MOUSEWHEEL:
                if board.collidepoint(pygame.mouse.get_pos()):
                    mods = pygame.key.get_mods()
                    axis = "X" if mods & pygame.KMOD_SHIFT else "Y" if mods & pygame.KMOD_CTRL else zoom_axis
                    set_zoom(1.12 ** max(-10, min(10, event.y)), axis)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                flat_drag = None
                zoom_action = next((key for key, rect in zoom_buttons(board, flat_mode(), active_zoom(), fit_mode, equal_pieces=equal_pieces).items()
                                    if rect.collidepoint(event.pos)), None) if controls_visible else None
                if event.button == 1 and zoom_action:
                    if zoom_action == "pieces":
                        equal_pieces = not equal_pieces
                    elif zoom_action == "axis":
                        if flat_mode() == UNWRAPPED:
                            zoom_axis = "XY"
                        else:
                            zoom_axis = {"XY": "X", "X": "Y", "Y": "XY"}[zoom_axis]
                    elif zoom_action == "reset":
                        if flat_mode() == UNWRAPPED:
                            unwrapped_zoom_x = unwrapped_zoom_y = 1.
                        else:
                            zoom_x = zoom_y = 1.
                    else:
                        set_zoom(1.12 if zoom_action == "in" else 1 / 1.12)
                    continue
                if event.button == 1 and visibility_button(screen.get_size()).collidepoint(event.pos):
                    controls_visible = not controls_visible
                    dragging = False
                    continue
                if event.button == 1 and view_button.collidepoint(event.pos):
                    view_mode = {"Cerc": "Cub", "Cub": "Ambele", "Ambele": UNWRAPPED,
                                 UNWRAPPED: UNWRAPPED_CUBE, UNWRAPPED_CUBE: "Cerc"}[view_mode]
                    if view_mode in (UNWRAPPED, UNWRAPPED_CUBE):
                        uniform = math.sqrt(unwrapped_zoom_x * unwrapped_zoom_y)
                        unwrapped_zoom_x = unwrapped_zoom_y = uniform
                        zoom_axis = "XY"
                    orbit = None
                    continue
                if event.button in (1, 3) and cube_rect.collidepoint(event.pos):
                    local = (event.pos[0] - cube_rect.x, event.pos[1] - cube_rect.y)
                    face = cube_face_at(local, cube_rect.size, animator, yaw, pitch)
                    if event.button == 1:
                        orbit = dict(start=event.pos, last=event.pos, moved=False, face=face)
                    elif face and not editor.editing:
                        animator.enqueue([face + "'"])
                    continue
                action = next((name for name, rect in actions.items() if rect.collidepoint(event.pos)), None)
                if event.button == 1 and action == "faces":
                    face_buttons = not bool(buttons)
                elif event.button == 1 and action == "fit":
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
                elif event.button == 1 and action == "camera":
                    camera.start("editor")
                    dragging, orbit = False, None
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
                        mapped = flat_pointer((event.pos[0] - board.x, event.pos[1] - board.y), board.size, flat_mode(), active_zoom(), fit_mode, equal_pieces=equal_pieces)
                        if mapped:
                            local, virtual = mapped
                            paint_editor(local, event.button, virtual)
                            editor_painting = event.button == 1
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
                elif event.button == 1 and board.collidepoint(event.pos) and not animator.pending:
                    local = (event.pos[0] - board.x, event.pos[1] - board.y)
                    candidate = DragTurn(animator, local, board.size, flat_mode(), active_zoom(), fit_mode, equal_pieces=equal_pieces)
                    if candidate.candidates:
                        flat_drag = (candidate, board.copy())
            elif event.type == pygame.MOUSEMOTION and flat_drag is not None:
                gesture, drag_board = flat_drag
                gesture.motion((event.pos[0] - drag_board.x, event.pos[1] - drag_board.y))
            elif event.type == pygame.MOUSEMOTION and editor.editing and editor_painting:
                local = (event.pos[0] - board.x, event.pos[1] - board.y)
                mapped = flat_pointer(local, board.size, flat_mode(), active_zoom(), fit_mode, equal_pieces=equal_pieces) if board.collidepoint(event.pos) else None
                if mapped:
                    paint_editor(mapped[0], 1, mapped[1])
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
                if flat_drag is not None:
                    gesture, drag_board = flat_drag
                    point = event.pos[0] - drag_board.x, event.pos[1] - drag_board.y
                    if gesture.release(point):
                        paused = False
                    flat_drag = None
                if (orbit is not None and not orbit["moved"] and orbit["face"]
                        and not editor.editing and math.dist(event.pos, orbit["start"]) <= 8
                        and cube_rect.collidepoint(event.pos)):
                    animator.enqueue([orbit["face"]])
                editor_painting = False
                editor_paint_slot = None
                dragging = False
                orbit = None
            elif event.type == pygame.KEYDOWN:
                key = pygame.key.name(event.key).upper()
                if event.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
                    set_zoom(1.12 if event.key == pygame.K_RIGHTBRACKET else 1 / 1.12)
                elif event.key == pygame.K_0:
                    if flat_mode() == UNWRAPPED:
                        unwrapped_zoom_x = unwrapped_zoom_y = 1.
                    else:
                        zoom_x = zoom_y = 1.
                elif event.key == pygame.K_t:
                    fit_mode = FIT_MODES[(FIT_MODES.index(fit_mode) + 1) % len(FIT_MODES)]
                elif event.key == pygame.K_s and not editor.editing:
                    animator = classic
                    solver.open_panel()
                    dragging, orbit = False, None
                elif event.key == pygame.K_v:
                    view_mode = {"Cerc": "Cub", "Cub": "Ambele", "Ambele": UNWRAPPED,
                                 UNWRAPPED: UNWRAPPED_CUBE, UNWRAPPED_CUBE: "Cerc"}[view_mode]
                    if view_mode in (UNWRAPPED, UNWRAPPED_CUBE):
                        uniform = math.sqrt(unwrapped_zoom_x * unwrapped_zoom_y)
                        unwrapped_zoom_x = unwrapped_zoom_y = uniform
                        zoom_axis = "XY"
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
        if solver.camera_requested:
            solver.camera_requested = False
            camera.start("solver")
        scanned = camera.poll()
        if scanned:
            target, cube = scanned
            animator = classic
            editor.begin(cube)
            editor.colors = facelets(cube)
            classic.set_cube(editor.apply())
            editor_view = None
            paused, double = False, False
            if target == "solver":
                solver.open_panel()
                solver.start(classic)
        if solver.visible and (solver.autoplay or solver.step_requested):
            paused = False
        if not paused and not editor.editing and not camera.active and flat_drag is None:
            animator.update(dt)
        if not camera.active:
            solver.update(classic)
        session.save(classic, variant)
        save_preferences(force=not dragging and orbit is None and pinch is None)
        playing_solution = solver.visible and solver.docked
        board, panel, buttons, slider, actions, compact = layout(screen.get_size(), controls_visible and not playing_solution, editing=editor.editing, face_buttons=face_buttons)
        area = board.copy()
        area.y += 46
        area.h = max(1, area.h - 46)
        if solver.visible and solver.docked:
            area.h = max(1, area.h - 114)
        board, cube_rect = view_regions(area, "Cerc" if animator is variant or (editor.editing and flat_mode() != UNWRAPPED) else view_mode)
        mouse = pygame.mouse.get_pos()
        hovered = next((f for f, rect in buttons.items() if rect.collidepoint(mouse)), None)
        if board.collidepoint(mouse):
            mapped = flat_pointer((mouse[0] - board.x, mouse[1] - board.y), board.size, flat_mode(), active_zoom(), fit_mode, equal_pieces=equal_pieces)
            color = center_at(mapped[0], *mapped[1]) if mapped else None
            hovered = next((f for f, c in FACE_COLORS.items() if c == color), None)
        if flat_drag is not None:
            hovered = flat_drag[0].face or hovered
        if solver.visible:
            hovered = None
        draw_animator = flat_drag[0].preview if flat_drag and flat_drag[0].preview else animator
        screen.fill(BACKGROUND_RGB)
        if board.w and board.h:
            board_screen = screen.subsurface(board)
            draw_flat(board_screen, mode=flat_mode(), zoom=active_zoom(), fit_mode=fit_mode, equal_pieces=equal_pieces, animator=editor_view if editor.editing else draw_animator,
                 hovered=None if editor.editing else hovered, show_paths=paths and not editor.editing,
                 facelets=editor.colors if editor.editing else None)
        if cube_rect.w and cube_rect.h:
            draw_cube(screen.subsurface(cube_rect), draw_animator, yaw, pitch)
        if controls_visible and not playing_solution:
            render_controls(screen, animator, paused, paths, hovered, editor=editor,
                            session_message=preferences.message or session.message, fit_mode=fit_mode, face_buttons=face_buttons)
        if controls_visible and not solver.visible:
            render_zoom(screen, board, active_zoom(), zoom_axis, flat_mode(), fit_mode, equal_pieces=equal_pieces)
        render_visibility_button(screen, controls_visible)
        view_button = pygame.Rect(180, 8, max(1, min(280, screen.get_width() - 188)), 30)
        pygame.draw.rect(screen, (235, 224, 245), view_button, border_radius=7)
        caption = ("45 grade: Cerc" if animator is variant else
                   "Editor: " + view_mode if editor.editing else "Vedere: " + view_mode + " [V]")
        label = text_surface(caption, 19, (43, 31, 61))
        if label.get_width() > view_button.w - 8:
            label = pygame.transform.smoothscale(label, (max(1, view_button.w - 8), label.get_height()))
        screen.blit(label, label.get_rect(center=view_button.center))
        if solver.visible:
            solver.draw(screen)
        camera.draw(screen)
        pygame.display.flip()
        await asyncio.sleep(0)
        frames += 1
        if max_frames is not None and frames >= max_frames:
            running = False
    camera.close()
    solver.close()
    session.save(classic, variant)
    save_preferences(force=True)
    pygame.quit()
