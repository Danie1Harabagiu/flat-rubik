"""Flat-board-only aspect controls, including the inverse pointer transform."""
import pygame
import math
from functools import lru_cache

from flat_rubik.geometry import board_point, geometrie_centre, ORANGE_RADII, RED_RADIUS, SPOKE_HALF_ANGLE
from flat_rubik.renderer import BACKGROUND_RGB, OUTLINE_RGB, CULORI_RGB, draw
from flat_rubik.editor import slot_regions
from flat_rubik.layer_motion import layer_paths
from flat_rubik.cube import Cube

FIT_MODES = ("proportional", "wide", "tall", "auto")
FIT_LABELS = {"proportional": "Forma: 1:1", "wide": "Forma: Lat", "tall": "Forma: Inalt", "auto": "Forma: X/Y"}
UNWRAPPED = "Desf\u0103\u0219urat"
UNWRAPPED_CUBE = "Desf\u0103\u0219urat + Cub"
# Put the cut on the boundary between the green and white center zones.
# The slice crossed by the cut is mirrored at both ends and remains synchronized.
UNWRAP_CUT = math.radians(45)
UNWRAP_RADIUS = ORANGE_RADII[-1]
UNWRAP_SIZE = (800, 800)
UNWRAP_COLUMNS = 12
UNWRAP_RADIAL_UNITS = 7
UNWRAP_CELL_FRACTION = 1 / UNWRAP_COLUMNS
UNWRAP_RADIAL_STOPS = ((0, 0), (44, 1), (48, 1), (88, 2),
                       (128, 3), (132, 3), (204, 4), (208, 4),
                       (246, 5), (296, 6), (300, 6), (330, 7))


def _radius_to_unit(radius):
    radius = max(0, min(UNWRAP_RADIUS, radius))
    for (r0, u0), (r1, u1) in zip(UNWRAP_RADIAL_STOPS, UNWRAP_RADIAL_STOPS[1:]):
        if radius <= r1:
            return u0 + (radius - r0) * (u1 - u0) / (r1 - r0)
    return UNWRAP_RADIAL_UNITS


def _unit_to_radius(unit):
    unit = max(0, min(UNWRAP_RADIAL_UNITS, unit))
    for (r0, u0), (r1, u1) in zip(UNWRAP_RADIAL_STOPS, UNWRAP_RADIAL_STOPS[1:]):
        if unit <= u1:
            return r0 + (unit - u0) * (r1 - r0) / (u1 - u0)
    return UNWRAP_RADIUS


def _wrap_angle(angle):
    return (angle + math.pi) % math.tau - math.pi


@lru_cache(maxsize=1)
def _row_angle_maps():
    """Pack each radial sticker row into twelve gap-free square units."""
    rows = [[] for _ in range(5)]
    for cubie in Cube().cubies:
        if cubie.kind == "center":
            continue
        x, y, z = cubie.position
        base = math.atan2(-y, x)
        for normal in cubie.stickers:
            if normal[2]:
                row = 0 if z == 1 else 4
                units = 2 if cubie.kind == "corner" else 1
                center, span = base, 2 * SPOKE_HALF_ANGLE
            else:
                row = {1: 1, 0: 2, -1: 3}[z]
                units, center, span = 1, base, 2 * SPOKE_HALF_ANGLE
                if x and y:
                    face_angle = math.atan2(-normal[1], normal[0])
                    side = -1 if _wrap_angle(face_angle - base) < 0 else 1
                    center = base + side * SPOKE_HALF_ANGLE / 2
                    span = SPOKE_HALF_ANGLE
            start = (center - span / 2 - UNWRAP_CUT) % math.tau
            rows[row].append((start, span, units))

    center_angles = {"galben": -math.pi / 2, "verde": 0,
                     "alb": math.pi / 2, "albastru": math.pi}
    for angle in center_angles.values():
        start = (angle - SPOKE_HALF_ANGLE - UNWRAP_CUT) % math.tau
        rows[2].append((start, 2 * SPOKE_HALF_ANGLE, 1))

    result = []
    for segments in rows:
        crossing = [entry for entry in segments
                    if entry[0] + entry[1] > math.tau + 1e-8]
        if len(crossing) > 1:
            raise ValueError("More than one color segment crosses the unwrap cut")
        regular = sorted((entry for entry in segments if entry not in crossing), key=lambda e: e[0])
        cursor = crossing[0][2] / 2 if crossing else 0
        intervals = []
        for start, span, units in regular:
            intervals.append((start, start + span, cursor, cursor + units))
            cursor += units
        if crossing:
            start, span, units = crossing[0]
            end = start + span - math.tau
            intervals.extend(((0, end, 0, units / 2),
                              (start, math.tau, UNWRAP_COLUMNS - units / 2, UNWRAP_COLUMNS)))
            expected = UNWRAP_COLUMNS - units / 2
        else:
            expected = UNWRAP_COLUMNS
        if abs(cursor - expected) > 1e-7:
            raise ValueError(f"Unpacked color row: expected {expected} units, got {cursor}")
        result.append(tuple(sorted(intervals, key=lambda e: e[0])))
    return tuple(result)


def _angle_to_units(angle, row):
    position = (angle - UNWRAP_CUT) % math.tau
    intervals = _row_angle_maps()[row]
    previous = None
    for a0, a1, u0, u1 in intervals:
        if a0 <= position <= a1:
            fraction = (position - a0) / max(1e-12, a1 - a0)
            return u0 + fraction * (u1 - u0)
        if position < a0:
            return previous[3] if previous is not None else 0
        previous = (a0, a1, u0, u1)
    return UNWRAP_COLUMNS


def _units_to_angle(units, row):
    units = max(0, min(UNWRAP_COLUMNS, units))
    for a0, a1, u0, u1 in _row_angle_maps()[row]:
        if u0 <= units <= u1 and u1 > u0:
            fraction = (units - u0) / (u1 - u0)
            return UNWRAP_CUT + a0 + fraction * (a1 - a0)
    return UNWRAP_CUT


def _row_for_radius(radius):
    if radius < 48:
        return 2
    if radius < 88:
        return 0
    if radius < 132:
        return 1
    if radius < 208:
        return 2
    if radius < 246:
        return 3
    return 4


def _unwrapped_destination(size, zoom=(1, 1), fit_mode="proportional"):
    width, height = size
    grid_ratio = UNWRAP_COLUMNS / UNWRAP_RADIAL_UNITS
    ratios = {"proportional": grid_ratio, "wide": grid_ratio * 1.4,
              "tall": grid_ratio / 1.4,
              "auto": (width * .96) / max(1, height * .72)}
    if fit_mode not in ratios:
        raise ValueError("Unknown unwrapped fit mode")
    ratio = ratios[fit_mode]
    rect_width = min(width * .96 / (1 + 2 * UNWRAP_CELL_FRACTION),
                     height * .72 * ratio)
    rect_height = rect_width / ratio
    rect = pygame.Rect(0, 0, max(1, round(rect_width * zoom[0])),
                       max(1, round(rect_height * zoom[1])))
    rect.center = width // 2, height // 2
    return rect


def _unwrapped_polygon(points, destination, size=UNWRAP_SIZE):
    """Project a facelet onto packed square units and repeat it across the cut."""
    cx, cy = size[0] / 2, size[1] / 2
    radii = [math.hypot(x - cx, y - cy) for x, y in points]
    if not radii:
        return ()
    # Circular source contours are rounded to pixels. Snap their radial edges
    # back to the shared stops before selecting a row or projecting a band.
    def snapped(radius):
        return next((stop for stop, _ in UNWRAP_RADIAL_STOPS
                     if abs(radius - stop) <= .75), radius)

    inner, outer = min(map(snapped, radii)), max(map(snapped, radii))
    inset = min(1, (outer - inner) / 2)
    mapped = []
    for x, y in points:
        dx, dy = x - cx, y - cy
        radius = snapped(math.hypot(dx, dy))
        angle = math.atan2(dy, dx)
        row = _row_for_radius(max(inner + inset, min(outer - inset, radius)))
        u = _angle_to_units(angle, row) / UNWRAP_COLUMNS
        mapped.append((destination.x + u * destination.w,
                       destination.y + (1 - _radius_to_unit(radius) / UNWRAP_RADIAL_UNITS) * destination.h))
    if not mapped:
        return ()
    continuous = []
    for x, y in mapped:
        if continuous:
            while x - continuous[-1][0] > destination.w / 2:
                x -= destination.w
            while x - continuous[-1][0] < -destination.w / 2:
                x += destination.w
        continuous.append((x, y))
    mean_x = sum(point[0] for point in continuous) / len(continuous)
    shift = round((destination.centerx - mean_x) / destination.w) * destination.w
    continuous = [(x + shift, y) for x, y in continuous]
    return tuple(tuple((round(x + repeat * destination.w), round(y)) for x, y in continuous)
                 for repeat in (-1, 0, 1))


def unwrapped_screen_point(point, destination, size=UNWRAP_SIZE):
    cx, cy = size[0] / 2, size[1] / 2
    dx, dy = point[0] - cx, point[1] - cy
    radius = math.hypot(dx, dy)
    row = _row_for_radius(radius)
    u = _angle_to_units(math.atan2(dy, dx), row) / UNWRAP_COLUMNS
    return (destination.x + u * destination.w,
            destination.y + (1 - _radius_to_unit(radius) / UNWRAP_RADIAL_UNITS) * destination.h)


def unwrapped_pointer(point, size, zoom=(1, 1), fit_mode="proportional"):
    destination = _unwrapped_destination(size, zoom, fit_mode)
    cell = destination.w / UNWRAP_COLUMNS
    middle = pygame.Rect(destination.x - math.ceil(cell),
                         round(destination.y + destination.h / 7),
                         destination.w + 2 * math.ceil(cell),
                         round(destination.h * 5 / 7))
    if not destination.collidepoint(point) and not middle.collidepoint(point):
        return None
    u = ((point[0] - destination.x) / destination.w * UNWRAP_COLUMNS) % UNWRAP_COLUMNS
    v = (point[1] - destination.y) / destination.h
    radius = _unit_to_radius((1 - v) * UNWRAP_RADIAL_UNITS)
    row = _row_for_radius(radius)
    angle = _units_to_angle(u, row)
    return (UNWRAP_SIZE[0] / 2 + radius * math.cos(angle),
            UNWRAP_SIZE[1] / 2 + radius * math.sin(angle)), UNWRAP_SIZE


def _spaced_unwrapped(points, destination, gap, outline=None):
    """Inset a whole cubie, using the same affine map for all its stickers."""
    polygons = _unwrapped_polygon(points, destination)
    boundaries = _unwrapped_polygon(outline, destination) if outline is not None else polygons
    bounds = [(min(x for x, _ in p), min(y for _, y in p),
               max(x for x, _ in p), max(y for _, y in p)) for p in boundaries]
    result = []
    for polygon in polygons:
        center = sum(x for x, _ in polygon) / len(polygon)
        left, top, right, bottom = min(bounds, key=lambda b: abs((b[0] + b[2]) / 2 - center))
        sx = max(.1, 1 - gap / max(1, right - left))
        sy = max(.1, 1 - gap / max(1, bottom - top))
        cx, cy = (left + right) / 2, (top + bottom) / 2
        result.append(tuple((round(cx + (x - cx) * sx), round(cy + (y - cy) * sy))
                            for x, y in polygon))
    return tuple(result)


def draw_unwrapped(surface, animator, hovered=None, show_paths=False, facelets=None,
                   zoom=(1, 1), fit_mode="proportional"):
    """Draw the circular board as a periodic rectangle with a visible cut seam."""
    destination = _unwrapped_destination(surface.get_size(), zoom, fit_mode)
    surface.fill(BACKGROUND_RGB)
    previous_clip = surface.get_clip()
    surface.set_clip(destination)
    # The central disk and outer orange ring become bands and retain their width.
    red_y = round(destination.y + (1 - _radius_to_unit(RED_RADIUS) / UNWRAP_RADIAL_UNITS) * destination.h)
    orange_y = round(destination.y + (1 - _radius_to_unit(ORANGE_RADII[0]) / UNWRAP_RADIAL_UNITS) * destination.h)
    gap = max(3, round(min(destination.w / UNWRAP_COLUMNS,
                                destination.h / UNWRAP_RADIAL_UNITS) * .055))
    half_gap = math.ceil(gap / 2)
    pygame.draw.rect(surface, CULORI_RGB["rosu"],
                     pygame.Rect(destination.x, red_y + half_gap, destination.w,
                                 destination.bottom - red_y - half_gap))
    pygame.draw.rect(surface, CULORI_RGB["portocaliu"],
                     pygame.Rect(destination.x, destination.y, destination.w,
                                 orange_y - destination.y - half_gap))

    line_width = max(1, round(min(destination.size) / 420))
    # The repeated cut cubie is drawn in full at both ends, including all
    # stickers. Only the middle five rows extend beyond the center bands.
    cell = math.ceil(destination.w / UNWRAP_COLUMNS)
    middle = pygame.Rect(destination.x - cell, orange_y,
                         destination.w + 2 * cell, red_y - orange_y)
    surface.set_clip(previous_clip.clip(middle))
    # Fixed center zones form the colored underlay between the cubies.
    for color, shape in geometrie_centre(*UNWRAP_SIZE).items():
        if color in ("rosu", "portocaliu") or shape["tip"] != "poligon":
            continue
        rgb = CULORI_RGB[color]
        for polygon in _spaced_unwrapped(shape["puncte"], destination, gap):
            pygame.draw.polygon(surface, rgb, polygon)
            pygame.draw.polygon(surface, OUTLINE_RGB, polygon, line_width)

    if animator is not None:
        shapes = animator.shapes(*UNWRAP_SIZE) if facelets is None else {
            (p, n): (facelets[p, n], points)
            for p, n, points in slot_regions(*UNWRAP_SIZE)
        }
        outlines = animator.outlines(*UNWRAP_SIZE)
        positions = {cubie.position: cubie.id for cubie in animator.cube.cubies}
        highlighted = (animator.highlighted_cubies(hovered)
                       if hovered and hasattr(animator, "highlighted_cubies") else set())
        for cubie_id in highlighted:
            outline = outlines[cubie_id]
            polygons = _spaced_unwrapped(outline, destination, gap)
            for polygon in polygons:
                pygame.draw.polygon(surface, (255, 255, 255), polygon, line_width + 2)
        for key, (color, points) in shapes.items():
            cubie_id = positions.get(key[0]) if isinstance(key[0], tuple) else key[0]
            polygons = _spaced_unwrapped(points, destination, gap, outlines.get(cubie_id))
            for polygon in polygons:
                pygame.draw.polygon(surface, CULORI_RGB[color], polygon)
        for cubie_id, outline in outlines.items():
            polygons = _spaced_unwrapped(outline, destination, gap)
            for polygon in polygons:
                pygame.draw.polygon(surface, OUTLINE_RGB, polygon, line_width)
        if show_paths and animator.target is not None:
            routes = (animator.routes(*UNWRAP_SIZE) if hasattr(animator, "routes") else
                      layer_paths(animator.cube, animator.current, *UNWRAP_SIZE))
            for route in routes:
                for start, end in zip(route, route[1:]):
                    a = unwrapped_screen_point(start, destination)
                    b = unwrapped_screen_point(end, destination)
                    if b[0] - a[0] > destination.w / 2:
                        b = (b[0] - destination.w, b[1])
                    elif a[0] - b[0] > destination.w / 2:
                        b = (b[0] + destination.w, b[1])
                    for shift in (-1, 0, 1):
                        pygame.draw.line(surface, (45, 28, 65),
                                         (round(a[0] + shift * destination.w), round(a[1])),
                                         (round(b[0] + shift * destination.w), round(b[1])), 1)

    surface.set_clip(previous_clip.clip(destination))
    edge_width = max(1, round(min(destination.size) / 500))
    pygame.draw.line(surface, OUTLINE_RGB, destination.topleft, destination.topright, edge_width)
    pygame.draw.line(surface, OUTLINE_RGB, destination.bottomleft, destination.bottomright, edge_width)
    centers = []
    for color, shape in geometrie_centre(*UNWRAP_SIZE).items():
        if color == "rosu":
            point = (destination.centerx, destination.y +
                     (1 - _radius_to_unit(RED_RADIUS / 2) / UNWRAP_RADIAL_UNITS) * destination.h)
        elif color == "portocaliu":
            radius = (ORANGE_RADII[0] + ORANGE_RADII[-1]) / 2
            point = (destination.centerx, destination.y +
                     (1 - _radius_to_unit(radius) / UNWRAP_RADIAL_UNITS) * destination.h)
        else:
            points = shape["puncte"]
            center = tuple(sum(p[i] for p in points) / len(points) for i in (0, 1))
            point = unwrapped_screen_point(center, destination)
        centers.append(point)
    marker_radius = max(3, min(8, round(destination.h * .035)))
    for point in centers:
        center = tuple(round(value) for value in point)
        pygame.draw.circle(surface, (255, 255, 255), center, marker_radius + 2, max(1, line_width))
        pygame.draw.circle(surface, OUTLINE_RGB, center, marker_radius, max(1, line_width))
    surface.set_clip(previous_clip)


def _base_viewport(size, mode="proportional"):
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


def flat_viewport(size, mode="proportional", zoom=(1, 1), fit_mode=None):
    if mode == UNWRAPPED:
        return UNWRAP_SIZE, _unwrapped_destination(size, zoom, fit_mode or "proportional")
    virtual, destination = _base_viewport(size, mode)
    # Some source arcs round sample coordinates. Generate those at the enlarged
    # size too, so magnification does not enlarge their rounding steps.
    quality = max(1, *zoom)
    virtual = tuple(max(1, round(value * quality)) for value in virtual)
    center = destination.center
    destination.size = (max(1, round(destination.w * zoom[0])), max(1, round(destination.h * zoom[1])))
    destination.center = center
    return virtual, destination


def flat_pointer(point, size, mode="proportional", zoom=(1, 1), fit_mode=None):
    if mode == UNWRAPPED:
        return unwrapped_pointer(point, size, zoom, fit_mode or "proportional")
    virtual, destination = flat_viewport(size, mode, zoom)
    if not destination.collidepoint(point):
        return None
    local = ((point[0] - destination.x) * virtual[0] / destination.w,
             (point[1] - destination.y) * virtual[1] / destination.h)
    return board_point(local, *virtual, inverse=True), virtual


def draw_flat(surface, mode="proportional", zoom=(1, 1), fit_mode=None, **kwargs):
    if mode == UNWRAPPED:
        draw_unwrapped(surface, zoom=zoom, fit_mode=fit_mode or "proportional", **kwargs)
        return
    if mode == "proportional" and zoom == (1, 1):
        draw(surface, **kwargs)
        return
    virtual, destination = flat_viewport(surface.get_size(), mode, zoom)
    def affine(point):
        return (destination.x + point[0] * destination.w / virtual[0],
                destination.y + point[1] * destination.h / virtual[1])

    def transform(point):
        return affine(board_point(point, *virtual))

    surface.fill(BACKGROUND_RGB)
    # Rasterize transformed geometry directly on the final-resolution surface.
    draw(surface, coordinate_size=virtual, transform=transform, icon_transform=affine, **kwargs)
