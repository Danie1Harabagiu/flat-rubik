
import math

SPOKE_HALF_ANGLE = math.radians(21)  # three-degree separation between adjacent pieces
# Shared by static slots, animated layers, face guides, and mouse hit testing.
RED_RADIUS = 44
# A wider central opening gives the inner ends of the pieces a broader edge.
INNER_RADII = (52, 88, 126)  # inside edge, colored seam, outside edge
MIDDLE_RADII = (134, 202)
OUTER_RADII = (210, 246, 294)
ORANGE_RADII = (302, 330)


def board_point(point, width, height, inverse=False):
    """Map the circular layout to a rounded square, with an exact inverse.

    The fourth-power norm extends diagonal regions without changing the
    cardinal extents. A shared final mapping keeps animated seams together.
    """
    x, y = point[0] - width / 2, point[1] - height / 2
    radius = math.hypot(x, y)
    if radius == 0:
        return width / 2, height / 2
    norm = ((x / radius) ** 4 + (y / radius) ** 4) ** .25
    factor = norm if inverse else 1 / norm
    return width / 2 + x * factor, height / 2 + y * factor


def resample_polygon(points, count=64):
    """Equally spaced boundary samples, shared by straight and curved edges."""
    segments = list(zip(points, points[1:] + points[:1]))
    lengths = [math.dist(a, b) for a, b in segments]
    total = sum(lengths)
    if total == 0:
        return [points[0]] * count
    result = []
    segment, offset = 0, 0.0
    for i in range(count):
        distance = total * i / count
        while segment < len(segments) - 1 and distance > offset + lengths[segment]:
            offset += lengths[segment]
            segment += 1
        a, b = segments[segment]
        t = (distance - offset) / max(lengths[segment], 1e-12)
        result.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return result


def interpolate_shape(source, target, t, center):
    """Continuous boundary morph along a polar path, avoiding the red center.

    Morph in a rotating local frame so opposite orientations never cancel
    into a tiny polygon. Only a gentle 4% temporary contraction is applied.
    """
    if t <= 0:
        return source
    if t >= 1:
        return target
    t = t * t * t * (t * (6 * t - 15) + 10)
    a, b = resample_polygon(source), resample_polygon(target)
    ca = tuple(sum(p[i] for p in a) / len(a) for i in (0, 1))
    cb = tuple(sum(p[i] for p in b) / len(b) for i in (0, 1))
    aa = math.atan2(ca[1] - center[1], ca[0] - center[0])
    ab = math.atan2(cb[1] - center[1], cb[0] - center[0])
    delta = (ab - aa + math.pi) % (2 * math.pi) - math.pi
    radius = math.dist(ca, center) * (1 - t) + math.dist(cb, center) * t
    path = punct_pe_cerc(*center, radius, aa + delta * t)
    contraction = 1 - .04 * math.sin(math.pi * t) ** 2
    result = []
    angle = aa + delta * t
    for p, q in zip(a, b):
        # Express both contours in their own radial/tangential frame first.
        px, py = p[0] - ca[0], p[1] - ca[1]
        qx, qy = q[0] - cb[0], q[1] - cb[1]
        u = (px * math.cos(aa) + py * math.sin(aa)) * (1 - t) + (qx * math.cos(ab) + qy * math.sin(ab)) * t
        v = (-px * math.sin(aa) + py * math.cos(aa)) * (1 - t) + (-qx * math.sin(ab) + qy * math.cos(ab)) * t
        result.append((path[0] + contraction * (u * math.cos(angle) - v * math.sin(angle)),
                       path[1] + contraction * (u * math.sin(angle) + v * math.cos(angle))))
    return result


def punct_pe_cerc(cx, cy, raza, unghi):
    return (
        cx + raza * math.cos(unghi),
        cy + raza * math.sin(unghi),
    )


def sector_inel(
    cx,
    cy,
    raza_interioara,
    raza_exterioara,
    unghi_start,
    unghi_final,
    segmente=40,
):
    puncte = []

    for i in range(segmente + 1):
        t = i / segmente
        unghi = unghi_start + (
            unghi_final - unghi_start
        ) * t

        puncte.append(
            punct_pe_cerc(
                cx, cy, raza_exterioara, unghi
            )
        )

    for i in range(segmente, -1, -1):
        t = i / segmente
        unghi = unghi_start + (
            unghi_final - unghi_start
        ) * t

        puncte.append(
            punct_pe_cerc(
                cx, cy, raza_interioara, unghi
            )
        )

    return [(round(x), round(y)) for x, y in puncte]


def geometrie_centre(latime, inaltime):
    cx = latime / 2
    cy = inaltime / 2

    scara = min(latime, inaltime) / 800

    raza_rosu = RED_RADIUS * scara

    # Reconstructed from the clean reference: isolated cardinal middle slots.
    # Pixel dimensions remain estimates, rather than a dimensioned CAD tracing.
    raza_interna = MIDDLE_RADII[0] * scara
    raza_externa = MIDDLE_RADII[1] * scara
    deschidere = 2 * SPOKE_HALF_ANGLE

    centre = {
        "rosu": {
            "tip": "cerc",
            "centru": (round(cx), round(cy)),
            "raza": round(raza_rosu),
        },
        "portocaliu": {
            "tip": "inel",
            "centru": (round(cx), round(cy)),
            "raza_interioara": round(ORANGE_RADII[0] * scara),
            "raza_exterioara": round(ORANGE_RADII[1] * scara),
        },
    }

    unghiuri = {
        "galben": -math.pi / 2,
        "verde": 0,
        "alb": math.pi / 2,
        "albastru": math.pi,
    }

    for culoare, unghi in unghiuri.items():
        centre[culoare] = {
            "tip": "poligon",
            "puncte": sector_inel(
                cx,
                cy,
                raza_interna,
                raza_externa,
                unghi - deschidere / 2,
                unghi + deschidere / 2,
            ),
        }

    return centre


def rotation_handles(width, height):
    """Shared positions and hit radii for the two arrows on each fixed center."""
    scale = min(width, height) / 800
    result = {}
    for color, shape in geometrie_centre(width, height).items():
        if shape["tip"] == "cerc":
            x, y = shape["centru"]
        elif shape["tip"] == "inel":
            x, y = shape["centru"]
            y -= (shape["raza_interioara"] + shape["raza_exterioara"]) / 2
        else:
            points = shape["puncte"]
            x, y = (sum(p[i] for p in points) / len(points) for i in (0, 1))
        result[color] = ((x, y), (x - 20 * scale, y),
                         (x + 20 * scale, y), 10 * scale)
    return result


def center_at(point, width, height):
    """Hit-test the actual drawn center shapes, never a mobile sticker."""
    x, y = point
    for color, shape in geometrie_centre(width, height).items():
        if shape["tip"] in ("cerc", "inel"):
            distance = math.dist(point, shape["centru"])
            if shape["tip"] == "cerc" and distance <= shape["raza"]:
                return color
            if shape["tip"] == "inel" and shape["raza_interioara"] <= distance <= shape["raza_exterioara"]:
                return color
        else:
            points = shape["puncte"]
            inside = False
            for a, b in zip(points, points[1:] + points[:1]):
                if (a[1] > y) != (b[1] > y):
                    intersection = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
                    if x < intersection:
                        inside = not inside
            if inside:
                return color
    return None
