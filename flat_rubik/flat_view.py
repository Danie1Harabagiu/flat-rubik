"""Flat-board-only aspect controls, including the inverse pointer transform."""
import pygame

from flat_rubik.geometry import board_point
from flat_rubik.renderer import BACKGROUND_RGB, draw

FIT_MODES = ("proportional", "wide", "tall", "auto")
FIT_LABELS = {"proportional": "Forma: 1:1", "wide": "Forma: Lat", "tall": "Forma: Inalt", "auto": "Forma: X/Y"}


def flat_viewport(size, mode="proportional"):
    """Return the virtual drawing size and its destination within the 2D view."""
    width, height = size
    if mode not in FIT_MODES:
        raise ValueError("Unknown flat view mode")
    if mode == "proportional":
        return size, pygame.Rect(0, 0, width, height)
    if mode == "auto":
        side = max(1, max(width, height))
        return (side, side), pygame.Rect(0, 0, width, height)
    ratio_x, ratio_y = (1.4, 1) if mode == "wide" else (1, 1.4)
    side = max(1, int(min(width / ratio_x, height / ratio_y)))
    destination = pygame.Rect(0, 0, max(1, round(side * ratio_x)), max(1, round(side * ratio_y)))
    destination.center = width // 2, height // 2
    quality_side = max(destination.size)
    return (quality_side, quality_side), destination


def flat_pointer(point, size, mode="proportional"):
    virtual, destination = flat_viewport(size, mode)
    if not destination.collidepoint(point):
        return None
    local = ((point[0] - destination.x) * virtual[0] / destination.w,
             (point[1] - destination.y) * virtual[1] / destination.h)
    return board_point(local, *virtual, inverse=True), virtual


def draw_flat(surface, mode="proportional", **kwargs):
    if mode == "proportional":
        draw(surface, **kwargs)
        return
    virtual, destination = flat_viewport(surface.get_size(), mode)
    def affine(point):
        return (destination.x + point[0] * destination.w / virtual[0],
                destination.y + point[1] * destination.h / virtual[1])

    def transform(point):
        return affine(board_point(point, *virtual))

    surface.fill(BACKGROUND_RGB)
    # Rasterize transformed geometry directly on the final-resolution surface.
    draw(surface, coordinate_size=virtual, transform=transform, icon_transform=affine, **kwargs)
