
import pygame
import math
from functools import lru_cache

from flat_rubik.cube import CENTRE, FACE_COLORS
from flat_rubik.geometry import geometrie_centre, sector_inel, INNER_RADII, OUTER_RADII, ORANGE_RADII
from flat_rubik.layer_motion import layer_paths, moving_cubies
from flat_rubik.editor import slot_regions
from flat_rubik.geometry import rotation_handles, board_point

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


def board_polygon(screen, color, points, width=0):
    pygame.draw.polygon(screen, color,
                        [board_point(p, *screen.get_size()) for p in points], width)


def board_circle(screen, color, center, radius, width=0):
    # Sample both boundaries so a thick ring has the same deformation as pieces.
    if width and width < radius:
        points = sector_inel(*center, radius - width, radius, 0, math.tau, segmente=128)
    else:
        points = [(center[0] + radius * math.cos(i * math.tau / 128),
                   center[1] + radius * math.sin(i * math.tau / 128)) for i in range(128)]
    board_polygon(screen, color, points)


def draw_rotation_arrow(screen, point, direction, face, scale):
    """Curved direction icon, oriented relative to its zone on the board."""
    x, y = point
    width, height = screen.get_size()
    angle = math.atan2(y - height / 2, x - width / 2)
    # The back face is viewed from the opposite side of the physical cube.
    sense = direction * (-1 if face == "B" else 1)
    radius = max(3, 5.5 * scale)
    start = angle - sense * math.radians(110)
    sweep = sense * math.radians(235)
    points = [(x + radius * math.cos(start + sweep * i / 24),
               y + radius * math.sin(start + sweep * i / 24)) for i in range(25)]
    white = (255, 255, 255)
    pygame.draw.lines(screen, white, False, points, max(1, round(1.5 * scale)))
    tip = pygame.Vector2(points[-1])
    tangent = pygame.Vector2(-math.sin(start + sweep), math.cos(start + sweep)) * sense
    back = tip - tangent * max(3, 4 * scale)
    side = tangent.rotate(90) * max(2, 2.5 * scale)
    pygame.draw.polygon(screen, white, [tip, back + side, back - side])


def draw_zones(screen, selected=None):
    """Fixed face regions remain legible even after sticker colors mix."""
    width, height = screen.get_size()
    scale = min(width, height) / 800
    center = (width / 2, height / 2)
    layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    angles = {"U": -math.pi / 2, "R": 0, "D": math.pi / 2, "L": math.pi}
    for face, color in FACE_COLORS.items():
        rgb = CULORI_RGB[color]
        # Color the fixed positions, independently of the scrambled cubies.
        # Stickers are drawn opaquely over this layer, leaving their colors intact.
        fill = (*rgb, 170 if face == selected else 135)
        edge = (*tuple(round(c * .65) for c in rgb), 230)
        thickness = max(1, round((4 if face == selected else 2) * scale))
        if face == "F":
            board_circle(layer, fill, center, round(INNER_RADII[1] * scale))
        elif face == "B":
            board_circle(layer, fill, center, round(ORANGE_RADII[-1] * scale),
                               max(1, round((ORANGE_RADII[-1] - OUTER_RADII[1]) * scale)))
        else:
            a = angles[face]
            polygon = sector_inel(*center, INNER_RADII[1] * scale, OUTER_RADII[1] * scale, a - math.pi / 4, a + math.pi / 4)
            board_polygon(layer, fill, polygon)
            # Keep straight face separators, without circular guides across gaps.
            for angle in (a - math.pi / 4, a + math.pi / 4):
                points = [(center[0] + r * scale * math.cos(angle),
                           center[1] + r * scale * math.sin(angle))
                          for r in (INNER_RADII[1], OUTER_RADII[1])]
                pygame.draw.line(layer, edge, *[board_point(p, width, height) for p in points], thickness)
    screen.blit(layer, (0, 0))


def draw_routes(screen, animator):
    """One source-to-destination path per cubie, not one per colored sticker."""
    width, height = screen.get_size()
    layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    paths = (animator.routes(width, height) if hasattr(animator, "routes") else
             layer_paths(animator.cube, animator.current, width, height))
    for points in paths:
        points = [board_point(p, width, height) for p in points]
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
    selected = hovered or (animator.current[0] if animator is not None and animator.current else None)
    draw_zones(ecran, selected)

    if animator is not None:
        shapes = (animator.shapes(latime, inaltime) if facelets is None else
                  {(p, n): (facelets[p, n], points) for p, n, points in slot_regions(latime, inaltime)})
        outlines = animator.outlines(latime, inaltime)
        highlighted = ((animator.highlighted_cubies(selected) if hasattr(animator, "highlighted_cubies") else
                        {c.id for c in moving_cubies(animator.cube, selected)}) if selected else set())
        halo_width = outline_width + max(2, round(4 * scale))
        # Highlight complete physical cubies, including their side colors.
        # Draw the halo underneath the original, opaque colored surfaces.
        for cubie_id in highlighted:
            board_polygon(ecran, (255, 255, 255), outlines[cubie_id], halo_width)
        for culoare, puncte in shapes.values():
            board_polygon(ecran, CULORI_RGB[culoare], puncte)
        for _, puncte in shapes.values():
            board_polygon(ecran, (45, 38, 48), puncte, seam_width)
        for polygon in outlines.values():
            board_polygon(ecran, OUTLINE_RGB, polygon, outline_width)

    if show_paths and animator is not None and animator.target is not None:
        draw_routes(ecran, animator)

    if selected:
        shape = forme[FACE_COLORS[selected]]
        glow = max(1, round(2 * scale))
        if shape["tip"] == "poligon":
            board_polygon(ecran, (255, 255, 255), shape["puncte"], outline_width + 2 * glow)
        elif shape["tip"] == "cerc":
            board_circle(ecran, (255, 255, 255), shape["centru"], shape["raza"] + glow)
        else:
            board_circle(ecran, (255, 255, 255), shape["centru"], shape["raza_exterioara"] + glow,
                               shape["raza_exterioara"] - shape["raza_interioara"] + 2 * glow)

    for nume, centru in CENTRE.items():
        forma = forme[nume]
        culoare = CULORI_RGB[centru.culoare]

        if forma["tip"] == "cerc":
            board_circle(
                ecran,
                culoare,
                forma["centru"],
                forma["raza"],
            )
            board_circle(ecran, OUTLINE_RGB, forma["centru"], forma["raza"], outline_width)

        elif forma["tip"] == "inel":
            cx, cy = forma["centru"]

            exterior = forma["raza_exterioara"]
            interior = forma["raza_interioara"]

            board_circle(
                ecran, culoare, (cx, cy), exterior,
                max(1, exterior - interior),
            )
            board_circle(ecran, OUTLINE_RGB, (cx, cy), exterior, outline_width)
            board_circle(ecran, OUTLINE_RGB, (cx, cy), interior, outline_width)

        elif forma["tip"] == "poligon":
            board_polygon(
                ecran,
                culoare,
                forma["puncte"],
            )

            board_polygon(
                ecran,
                OUTLINE_RGB,
                forma["puncte"],
                outline_width,
            )

    # Keep the centers clear: only the two direction arrows remain.
    if facelets is None:
        handles = rotation_handles(latime, inaltime)
        for face, color in FACE_COLORS.items():
            _, left, right, hit_radius = handles[color]
            for direction, point in ((-1, left), (1, right)):
                point = tuple(round(v) for v in board_point(point, latime, inaltime))
                pygame.draw.circle(ecran, (35, 35, 35), point, max(2, round(hit_radius)))
                draw_rotation_arrow(ecran, point, direction, face, scale)
