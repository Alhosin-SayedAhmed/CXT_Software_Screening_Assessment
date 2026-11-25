#!/usr/bin/env python3
"""Crescent (هلال) desk stand for the Quran heart board.

The heart's rounded bottom sits in a small cradle and leans back TILT degrees onto a
back rest hidden behind it. A crescent stands upright on the heart's right side,
curving up around it like ")": its lower horn meets the base, its upper horn reaches
up the heart's side. A low oval base and a hidden rear brace keep it from tipping.
The cradle's front lip only covers the heart's outer rim, so no surah pocket is hidden.

Writes stand.stl (print as is, base on the plate, no supports).
Run build.py first (it writes preview.json with the board outline).
"""
import os, json, math
import shapely
from shapely.geometry import shape, box, Point, Polygon
from shapely.ops import unary_union
from shapely import affinity
from build import extrude, fit_text, to_trimesh, BRAND_TEXT, BRAND_FONT, BRAND_DEPTH

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- CONFIG
TILT        = 15.0    # deg the heart leans back from vertical
BOARD_T     = 2.8     # mm board thickness at the rim
SLOT_CLEAR  = 0.35    # mm gap each side of the board in the slot
EDGE_CLEAR  = 0.5     # mm gap between the heart outline and the cradle
CUP_H       = 14.0    # mm, how far up the heart's bottom the cradle reaches
CUP_WALL    = 4.0     # mm cradle wall around the outline
FRONT_T     = 2.4     # mm front lip thickness
RIM_COVER   = 2.0     # mm the front lip reaches over the rim (pockets start after 3 mm)
BACK_T      = 5.0     # mm back rest / crescent thickness behind the heart
LIFT        = 6.0     # mm heart's bottom tip above the base
REST_W      = 34.0    # mm hidden back rest width
REST_H      = 72.0    # mm hidden back rest height above the heart's bottom
# crescent on the right side: outer circle minus an inner circle shifted toward the heart
MOON_X      = 45.0    # mm outer circle centre, right of the heart's bottom tip
MOON_Y      = 55.0    # mm outer circle centre height above the heart's bottom tip
MOON_R      = 62.0    # mm outer radius
MOON_SPAN   = 150.0   # deg from horn tip to horn tip
MOON_THICK  = 20.0    # mm crescent thickness at its middle
MOON_DIR    = 0.0     # deg direction of the crescent's thick middle (0 = straight right)
BASE_T      = 4.0     # mm base plate thickness
BASE_CX     = 30.0    # mm base centre x
BASE_RX     = 86.0    # mm base half-width (oval)
BASE_RY     = 48.0    # mm base half-depth (oval)
BASE_SHIFT  = 26.0    # mm base centre behind the heart (the heart leans back)
BRACE_T     = 6.0     # mm rear brace thickness


def crescent(cx, cy, R, span, thick, direction):
    """Crescent whose thick middle points along `direction` and whose horns end span degrees apart."""
    c = math.cos(math.radians(span / 2))
    d = ((R - thick) ** 2 - R ** 2) / (2 * R * c - 2 * (R - thick))
    r_in = R - thick + d
    m = Point(0, 0).buffer(R, 256).difference(Point(0, d).buffer(r_in, 256))   # middle at the bottom
    m = m.buffer(-1.2, join_style=1).buffer(1.2, join_style=1)
    m = affinity.rotate(m, direction + 90, origin=(0, 0))
    return affinity.translate(m, cx, cy)


def main():
    outline = shape(json.load(open(os.path.join(HERE, 'preview.json')))['outline'])
    y0 = outline.bounds[1]
    outline = affinity.translate(outline, 0, -y0)            # heart's bottom tip at y = 0
    hx = outline.centroid.x
    a = math.radians(TILT)
    n_back = -SLOT_CLEAR - BACK_T
    n_front = BOARD_T + SLOT_CLEAR + FRONT_T
    below = -LIFT - 5                                         # local y well under the base top

    # cradle around the heart's bottom, with a pedestal down into the base
    cup = outline.buffer(EDGE_CLEAR + CUP_WALL, join_style=1).intersection(box(-1e3, -1e3, 1e3, CUP_H))
    cb = cup.bounds
    cradle = unary_union([cup, box(cb[0], below, cb[2], 0)]).convex_hull.intersection(box(-1e3, below, 1e3, CUP_H))
    # crescent; its lower horn is extended straight down into the base
    moon = crescent(hx + MOON_X, MOON_Y, MOON_R, MOON_SPAN, MOON_THICK, MOON_DIR)
    low = moon.intersection(box(-1e3, -1e3, 1e3, 4))
    if not low.is_empty:
        lb = low.bounds
        moon = unary_union([moon, box(lb[0], below, lb[2], lb[1] + 1).intersection(
            unary_union([low, box(lb[0], below, lb[2], below + 0.1)]).convex_hull)])
    pad = outline.buffer(EDGE_CLEAR + 0.5, join_style=1)
    behind = moon.intersection(pad)                           # only behind the heart where they overlap
    beside = moon.difference(pad)
    rest = box(hx - REST_W / 2, 0, hx + REST_W / 2, REST_H).buffer(-8, join_style=1).buffer(8, join_style=1)
    rest = rest.intersection(outline.buffer(-6, join_style=1))   # stays hidden behind the heart

    local = extrude(unary_union([cradle, beside]), n_back, n_front - n_back)
    local = local + extrude(unary_union([behind, rest, box(hx - REST_W / 2, 2, hx + REST_W / 2, 20)]), n_back, BACK_T)
    local = local - extrude(outline.buffer(EDGE_CLEAR, join_style=1), -SLOT_CLEAR, BOARD_T + 2 * SLOT_CLEAR)
    local = local - extrude(outline.buffer(-RIM_COVER, join_style=1), BOARD_T + SLOT_CLEAR - 0.01, 50)

    lift = BASE_T + LIFT
    M = [[1, 0, 0, 0],
         [0, math.sin(a), -math.cos(a), 0],
         [0, math.cos(a), math.sin(a), lift]]
    world = local.transform(M).trim_by_plane([0, 0, 1], BASE_T - 0.01)

    base2d = affinity.scale(Point(BASE_CX, BASE_SHIFT).buffer(1, 128), BASE_RX, BASE_RY, origin=(BASE_CX, BASE_SHIFT))
    base = extrude(base2d, 0, BASE_T)

    def w(y, n):                                            # local (y, n) -> world (Y, Z)
        return (y * math.sin(a) - n * math.cos(a), y * math.cos(a) + n * math.sin(a) + lift)
    p_top = w(REST_H - 12, n_back + 0.5)
    p_low = w(0, n_back + 0.5)
    back_y = BASE_SHIFT + BASE_RY - 10
    tri = Polygon([p_top, (p_low[0], BASE_T - 0.01), (back_y, BASE_T - 0.01)])
    brace = extrude(tri, hx - BRACE_T / 2, BRACE_T).transform([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]])

    stand = base + world + brace
    brand, _ = fit_text(BRAND_TEXT, base2d.buffer(-16), font=BRAND_FONT, angles=(0,), max_em=14)
    brand = affinity.scale(brand, -1, 1, origin=brand.centroid).buffer(-0.02).buffer(0.02)
    stand = stand - extrude(brand, -1, 1 + BRAND_DEPTH)
    out = os.environ.get('STAND_OUT', HERE)
    to_trimesh(stand).export(os.path.join(out, 'stand.stl'))
    json.dump(dict(tilt=TILT, lift=lift, base_t=0.0, y0=y0), open(os.path.join(out, 'stand_pose.json'), 'w'))

    com = w(outline.centroid.y, BOARD_T / 2)
    bb = stand.bounding_box()
    print(f'crescent stand {bb[3]-bb[0]:.0f} x {bb[4]-bb[1]:.0f} x {bb[5]-bb[2]:.0f} mm, '
          f'heart CoM at x={hx:.0f} Y={com[0]:.0f} (base x {BASE_CX-BASE_RX:.0f}..{BASE_CX+BASE_RX:.0f}, '
          f'Y {BASE_SHIFT-BASE_RY:.0f}..{BASE_SHIFT+BASE_RY:.0f}), volume {stand.volume()/1000:.1f} cm3')


if __name__ == '__main__':
    main()
