"""Software 3D view of the same physical cubies and animation clock."""
import math
import pygame

from flat_rubik.cube import FACE_NORMALS, parse_move
from flat_rubik.renderer import CULORI_RGB, text_surface
from flat_rubik.layer_motion import ease


def rotate_point(point, axis, angle):
    result = list(point)
    a, b = (axis + 1) % 3, (axis + 2) % 3
    c, s = math.cos(angle), math.sin(angle)
    result[a], result[b] = c * point[a] - s * point[b], s * point[a] + c * point[b]
    return tuple(result)


def animated_point(point, position, animator):
    if animator.target is None:
        return point
    face, turns = parse_move(animator.current)
    normal = FACE_NORMALS[face]
    axis = next(i for i, value in enumerate(normal) if value)
    if position[axis] != normal[axis]:
        return point
    t = max(0, min(1, animator.elapsed / animator.duration))
    t = ease(t)
    return rotate_point(point, axis, -normal[axis] * turns * math.pi / 2 * t)


def view_regions(area, mode):
    """Keep the circle's hit testing in its own coordinates."""
    empty = pygame.Rect(area.x, area.y, 0, 0)
    if mode == "Cerc":
        return area.copy(), empty
    if mode == "Cub":
        return empty, area.copy()
    if area.w >= area.h:
        width = area.w // 2
        return pygame.Rect(area.x, area.y, width, area.h), pygame.Rect(area.x + width, area.y, area.w - width, area.h)
    height = area.h // 2
    return pygame.Rect(area.x, area.y, area.w, height), pygame.Rect(area.x, area.y + height, area.w, area.h - height)


def projected_polygons(size, animator, yaw=-.55, pitch=.45):
    """Shared geometry for drawing and picking, ordered from back to front."""
    w, h = size
    scale = min(w / 5.4, max(1, h - 36) / 5.4)
    polygons = []

    def camera(point):
        return rotate_point(rotate_point(point, 1, yaw), 0, pitch)

    for cubie in animator.cube.cubies:
        for face, normal in FACE_NORMALS.items():
            axis = next(i for i, value in enumerate(normal) if value)
            a, b = (axis + 1) % 3, (axis + 2) % 3
            for inset, color in ((.48, (29, 25, 35)), (.415, CULORI_RGB.get(cubie.stickers.get(normal)))):
                if color is None:
                    continue
                points = []
                for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    point = list(cubie.position)
                    point[axis] += normal[axis] * (.48 if inset == .48 else .485)
                    point[a] += u * inset
                    point[b] += v * inset
                    points.append(camera(animated_point(point, cubie.position, animator)))
                transformed_normal = camera(animated_point(normal, cubie.position, animator))
                if transformed_normal[2] <= 0:
                    continue
                depth = sum(p[2] for p in points) / 4
                shade = .72 + .28 * transformed_normal[2]
                color = tuple(round(channel * shade) for channel in color)
                polygon = [(w / 2 + p[0] * scale, (h - 24) / 2 - p[1] * scale + 8) for p in points]
                polygons.append((depth, color, polygon, face if normal in cubie.stickers else None))
    return sorted(polygons, key=lambda item: item[0])


def cube_face_at(point, size, animator, yaw=-.55, pitch=.45):
    for _, _, polygon, face in reversed(projected_polygons(size, animator, yaw, pitch)):
        sides = []
        for a, b in zip(polygon, polygon[1:] + polygon[:1]):
            sides.append((b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0]))
        if all(s >= -1e-6 for s in sides) or all(s <= 1e-6 for s in sides):
            return face
    return None


def draw_cube(surface, animator, yaw=-.55, pitch=.45):
    w, h = surface.get_size()
    for _, color, polygon, _ in projected_polygons((w, h), animator, yaw, pitch):
        pygame.draw.polygon(surface, color, polygon)
    label = text_surface("Clic: rotire fata | Trage: vedere", 19, (43, 31, 61))
    surface.blit(label, label.get_rect(midbottom=(w // 2, h - 3)))
