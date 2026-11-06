import pygame

from flat_rubik.animation import Animator
from flat_rubik.cube import scramble, FACE_COLORS
from flat_rubik.controls import move_for_click
from flat_rubik.geometry import center_at
from flat_rubik.renderer import draw, BACKGROUND_RGB
from flat_rubik.ui import layout, duration_at, render_controls


def run(max_frames=None):
    pygame.init()
    screen = pygame.display.set_mode((1080, 800), pygame.RESIZABLE)
    pygame.display.set_caption("Flat Rubik")
    clock = pygame.time.Clock()
    animator = Animator(duration=1.0)
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
                if event.button == 1 and slider.inflate(18, 16).collidepoint(event.pos):
                    dragging = True
                    animator.set_duration(duration_at(event.pos[0], slider))
                elif event.button == 1 and any(r.collidepoint(event.pos) for r in actions.values()):
                    action = next(name for name, rect in actions.items() if rect.collidepoint(event.pos))
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
                        move = move_for_click(local, event.button, board.size)
                    if move:
                        animator.enqueue([move])
            elif event.type == pygame.MOUSEMOTION and dragging:
                animator.set_duration(duration_at(event.pos[0], slider))
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = False
            elif event.type == pygame.KEYDOWN:
                key = pygame.key.name(event.key).upper()
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif key in ("R", "L", "U", "D", "F", "B"):
                    suffix = "2" if double or event.mod & pygame.KMOD_CTRL else "'" if event.mod & pygame.KMOD_SHIFT else ""
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
        if not paused:
            animator.update(dt)
        board, panel, buttons, slider, actions, compact = layout(screen.get_size())
        mouse = pygame.mouse.get_pos()
        hovered = next((f for f, rect in buttons.items() if rect.collidepoint(mouse)), None)
        if board.collidepoint(mouse):
            color = center_at((mouse[0] - board.x, mouse[1] - board.y), *board.size)
            hovered = next((f for f, c in FACE_COLORS.items() if c == color), None)
        screen.fill(BACKGROUND_RGB)
        draw(screen.subsurface(board), animator=animator, hovered=hovered, show_paths=paths)
        render_controls(screen, animator, paused, paths, hovered)
        pygame.display.flip()
        frames += 1
        if max_frames is not None and frames >= max_frames:
            running = False
    pygame.quit()
