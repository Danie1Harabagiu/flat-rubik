
import pygame
import math
from functools import lru_cache

from flat_rubik.cube import CENTRE, FACE_COLORS
from flat_rubik.geometry import geometrie_centre, sector_inel, INNER_RADII, OUTER_RADII, ORANGE_RADII
from flat_rubik.layer_motion import layer_paths, moving_cubies
from flat_rubik.editor import slot_regions

BACKGROUND_RGB = (180, 150, 210)
OUTLINE_RGB = (68, 22, 104)


CULORI_RGB = {
    "rosu": (220, 40, 40),
    "portocaliu": (255, 145, 0),
    "galben": (255, 220, 0),
    "verde": (30, 175, 75),
    "alb": (255, 255, 255),
    "albastru": (40, 145, 235),
}


@lru_cache(maxsize=512)
def text_surface(text, size, color):
    """Cache immutable labels instead of rerasterizing the same text each frame."""
    return pygame.font.Font(None, size).render(text, True, color)


def draw_zones(screen, selected=None):
    """Fixed face regions remain legible even after sticker colors mix."""
    width, height = screen.get_size()
    scale = min(width, height) / 800
    center = (width / 2, height / 2)
    layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    angles = {"U": -math.pi / 2, "R": 0, "D": math.pi / 2, "L": math.pi}
    for face, color in FACE_COLORS.items():
        rgb = CULORI_RGB[color]
        fill = (*rgb, 48 if face == selected else 22)
        edge = (*tuple(round(c * .65) for c in rgb), 230)
        thickness = max(1, round((4 if face == selected else 2) * scale))
        if face == "F":
            pygame.draw.circle(layer, fill, center, round(INNER_RADII[1] * scale))
        elif face == "B":
            pygame.draw.circle(layer, fill, center, round(ORANGE_RADII[-1] * scale),
                               max(1, round((ORANGE_RADII[-1] - OUTER_RADII[1]) * scale)))
        else:
            a = angles[face]
            polygon = sector_inel(*center, INNER_RADII[1] * scale, OUTER_RADII[1] * scale, a - math.pi / 4, a + math.pi / 4)
            pygame.draw.polygon(layer, fill, polygon)
            # Keep straight face separators, without circular guides across gaps.
            for angle in (a - math.pi / 4, a + math.pi / 4):
                points = [(center[0] + r * scale * math.cos(angle),
                           center[1] + r * scale * math.sin(angle))
                          for r in (INNER_RADII[1], OUTER_RADII[1])]
                pygame.draw.line(layer, edge, *points, thickness)
    screen.blit(layer, (0, 0))


def draw_routes(screen, animator):
    """One source-to-destination path per cubie, not one per colored sticker."""
    width, height = screen.get_size()
    layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    for points in layer_paths(animator.cube, animator.current, width, height):
        a, b = points[0], points[-1]
        for i in range(0, 40, 3):
            pygame.draw.line(layer, (45, 28, 65, 160), points[i], points[min(40, i + 1)], 2)
        pygame.draw.circle(layer, (255, 255, 255, 230), a, 4, 1)
        direction = pygame.Vector2(points[-1]) - points[-3]
        if direction.length() > 0:
            direction.scale_to_length(8)
            tip = pygame.Vector2(b)
            pygame.draw.polygon(layer, (45, 28, 65, 220), [tip, tip - direction + direction.rotate(90) * .45,
                                                                         tip - direction - direction.rotate(90) * .45])
    screen.blit(layer, (0, 0))


def draw(ecran, timp=0, animator=None, hovered=None, show_paths=False, facelets=None):
    latime, inaltime = ecran.get_size()
    forme = geometrie_centre(latime, inaltime)
    scale = min(latime, inaltime) / 800
    outline_width = max(1, round(3 * scale))
    seam_width = max(1, round(scale))
    badge_size = max(8, round(22 * scale))
    selected = hovered or (animator.current[0] if animator is not None and animator.current else None)
    draw_zones(ecran, selected)

    if animator is not None:
        shapes = (animator.shapes(latime, inaltime) if facelets is None else
                  {(p, n): (facelets[p, n], points) for p, n, points in slot_regions(latime, inaltime)})
        outlines = animator.outlines(latime, inaltime)
        highlighted = {c.id for c in moving_cubies(animator.cube, selected)} if selected else set()
        halo_width = outline_width + max(2, round(4 * scale))
        # Highlight complete physical cubies, including their side colors.
        # Draw the halo underneath the original, opaque colored surfaces.
        for cubie_id in highlighted:
            pygame.draw.polygon(ecran, (255, 255, 255), outlines[cubie_id], halo_width)
        for culoare, puncte in shapes.values():
            pygame.draw.polygon(ecran, CULORI_RGB[culoare], puncte)
        for _, puncte in shapes.values():
            pygame.draw.polygon(ecran, (45, 38, 48), puncte, seam_width)
        for polygon in outlines.values():
            pygame.draw.polygon(ecran, OUTLINE_RGB, polygon, outline_width)

    if show_paths and animator is not None and animator.target is not None:
        draw_routes(ecran, animator)

    if selected:
        shape = forme[FACE_COLORS[selected]]
        glow = max(1, round(2 * scale))
        if shape["tip"] == "poligon":
            pygame.draw.polygon(ecran, (255, 255, 255), shape["puncte"], outline_width + 2 * glow)
        elif shape["tip"] == "cerc":
            pygame.draw.circle(ecran, (255, 255, 255), shape["centru"], shape["raza"] + glow)
        else:
            pygame.draw.circle(ecran, (255, 255, 255), shape["centru"], shape["raza_exterioara"] + glow,
                               shape["raza_exterioara"] - shape["raza_interioara"] + 2 * glow)

    for nume, centru in CENTRE.items():
        forma = forme[nume]
        culoare = CULORI_RGB[centru.culoare]

        if forma["tip"] == "cerc":
            pygame.draw.circle(
                ecran,
                culoare,
                forma["centru"],
                forma["raza"],
            )
            pygame.draw.circle(ecran, OUTLINE_RGB, forma["centru"], forma["raza"], outline_width)

        elif forma["tip"] == "inel":
            cx, cy = forma["centru"]

            exterior = forma["raza_exterioara"]
            interior = forma["raza_interioara"]

            pygame.draw.circle(
                ecran, culoare, (cx, cy), exterior,
                max(1, exterior - interior),
            )
            pygame.draw.circle(ecran, OUTLINE_RGB, (cx, cy), exterior, outline_width)
            pygame.draw.circle(ecran, OUTLINE_RGB, (cx, cy), interior, outline_width)

        elif forma["tip"] == "poligon":
            pygame.draw.polygon(
                ecran,
                culoare,
                forma["puncte"],
            )

            pygame.draw.polygon(
                ecran,
                OUTLINE_RGB,
                forma["puncte"],
                outline_width,
            )

    # Mark only the six fixed, clickable centers, keeping their colored shape.
    for face, color in FACE_COLORS.items():
        shape = forme[color]
        if shape["tip"] == "cerc":
            position = shape["centru"]
        elif shape["tip"] == "inel":
            cx, cy = shape["centru"]
            position = (cx, cy - (shape["raza_interioara"] + shape["raza_exterioara"]) / 2)
        else:
            points = shape["puncte"]
            position = tuple(sum(p[i] for p in points) / len(points) for i in (0, 1))
        position = tuple(round(v) for v in position)
        radius = max(2, round(13 * scale))
        pygame.draw.circle(ecran, (35, 35, 35), position, radius)
        pygame.draw.circle(ecran, (255, 255, 255), position, radius, 1)
        label = text_surface(face, badge_size, (255, 255, 255))
        ecran.blit(label, label.get_rect(center=position))
        if face == selected:
            pygame.draw.circle(ecran, (255, 255, 255), position, radius + max(2, round(4 * scale)), 2)
