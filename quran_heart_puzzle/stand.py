#!/usr/bin/env python3
"""Crescent (هلال) desk stand for the Quran heart board.

An upright crescent stands just behind the heart, leaning back TILT degrees with it.
The heart's rounded bottom sits in a cradle at the crescent's lowest part and its
back rests on the crescent; the two horns show on either side of the heart.
A low oval base and a hidden rear brace keep it from tipping.
The front lip only covers the heart's outer rim, so no surah pocket is hidden.

Writes stand.stl (print as is, base on the plate, no supports).
Run build.py first (it writes preview.json with the board outline).
"""
import os, json, math
import numpy as np
import shapely
from shapely.geometry import shape, box, Point
from shapely.ops import unary_union
from shapely import affinity
import manifold3d as m3d
from build import extrude, fit_text, to_trimesh, BRAND_TEXT, BRAND_FONT, BRAND_DEPTH

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- CONFIG
TILT        = 15.0    # deg the heart leans back from vertical
BOARD_T     = 2.8     # mm board thickness at the rim
SLOT_CLEAR  = 0.35    # mm gap each side of the board in the slot
EDGE_CLEAR  = 0.5     # mm gap between the heart outline and the cradle
CUP_H       = 16.0    # mm, how far up the heart's bottom the front lip reaches
FRONT_T     = 2.4     # mm front lip thickness
RIM_COVER   = 2.0     # mm the front lip reaches over the rim (pockets start after 3 mm)
BACK_T      = 5.0     # mm crescent plate thickness behind the heart
# crescent = outer circle minus inner circle shifted up (horns point up)
MOON_R      = 105.0   # mm outer radius
MOON_BELOW  = 14.0    # mm the crescent reaches below the heart's bottom tip
MOON_SHIFT  = 28.0    # mm inner circle shifted up -> crescent thickness at the bottom
MOON_R_IN   = 103.0   # mm inner radius
BASE_T      = 4.0     # mm base plate thickness
BASE_RX     = 78.0    # mm base half-width (oval)
BASE_RY     = 56.0    # mm base half-depth (oval)
BASE_SHIFT  = 24.0    # mm base centre behind the heart (the heart leans back)
BRACE_T     = 6.0     # mm rear brace thickness


def main():
    outline = shape(json.load(open(os.path.join(HERE, 'preview.json')))['outline'])
    y0 = outline.bounds[1]
    outline = affinity.translate(outline, 0, -y0)            # heart's bottom tip at y = 0
    cx = outline.centroid.x
    a = math.radians(TILT)

    # crescent in the heart's plane
    cy = MOON_R - MOON_BELOW
    moon = Point(cx, cy).buffer(MOON_R, 256).difference(Point(cx, cy + MOON_SHIFT).buffer(MOON_R_IN, 256))
    moon = moon.buffer(-1.5, join_style=1).buffer(1.5, join_style=1)      # soften the horn tips
    if hasattr(moon, 'geoms'):
        moon = max(moon.geoms, key=lambda g: g.area)
    slot = outline.buffer(EDGE_CLEAR, join_style=1)
    # front part (lip + solid crescent below the heart) only low down
    low = box(-1e3, -1e3, 1e3, CUP_H)
    front = moon.intersection(low)

    n_back = -SLOT_CLEAR - BACK_T
    n_front = BOARD_T + SLOT_CLEAR + FRONT_T
    # one solid crescent, then cut away the front part above the cradle (keeps the mesh clean)
    local = extrude(moon, n_back, n_front - n_back)
    local = local - extrude(box(-1e3, CUP_H, 1e3, 1e3), n_back + BACK_T, 50)
    local = local - extrude(slot, -SLOT_CLEAR, BOARD_T + 2 * SLOT_CLEAR)
    local = local - extrude(outline.buffer(-RIM_COVER, join_style=1), BOARD_T + SLOT_CLEAR - 0.01, 50)

    # lift so the crescent's lowest point sinks just into the base
    lift = BASE_T + MOON_BELOW * math.cos(a) - 0.5
    M = [[1, 0, 0, 0],
         [0, math.sin(a), -math.cos(a), 0],
         [0, math.cos(a), math.sin(a), lift]]
    world = local.transform(M).trim_by_plane([0, 0, 1], 0)

    base2d = affinity.scale(Point(cx, BASE_SHIFT).buffer(1, 128), BASE_RX, BASE_RY, origin=(cx, BASE_SHIFT))
    base = extrude(base2d, 0, BASE_T)

    def w(y, n):                                            # local (y, n) -> world (Y, Z)
        return (y * math.sin(a) - n * math.cos(a), y * math.cos(a) + n * math.sin(a) + lift)
    # hidden rear brace from the crescent's back down to the base
    p_top = w(70, n_back + 0.5)
    p_low = w(-MOON_BELOW + 6, n_back + 0.5)
    back_y = BASE_SHIFT + BASE_RY - 10
    tri = shapely.geometry.Polygon([p_top, (p_low[0], BASE_T - 0.01), (back_y, BASE_T - 0.01)])
    brace = extrude(tri, cx - BRACE_T / 2, BRACE_T).transform([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]])

    stand = base + world + brace
    brand, _ = fit_text(BRAND_TEXT, base2d.buffer(-16), font=BRAND_FONT, angles=(0,), max_em=14)
    brand = affinity.scale(brand, -1, 1, origin=brand.centroid).buffer(-0.02).buffer(0.02)
    stand = stand - extrude(brand, -1, 1 + BRAND_DEPTH)
    to_trimesh(stand).export(os.path.join(HERE, 'stand.stl'))
    json.dump(dict(tilt=TILT, lift=lift, base_t=0.0, y0=y0), open(os.path.join(HERE, 'stand_pose.json'), 'w'))

    com = w(outline.centroid.y, BOARD_T / 2)
    bb = stand.bounding_box()
    print(f'crescent stand {bb[3]-bb[0]:.0f} x {bb[4]-bb[1]:.0f} x {bb[5]-bb[2]:.0f} mm, '
          f'heart CoM at Y={com[0]:.0f} mm (base spans {BASE_SHIFT-BASE_RY:.0f}..{BASE_SHIFT+BASE_RY:.0f}), '
          f'volume {stand.volume()/1000:.1f} cm3')


if __name__ == '__main__':
    main()
