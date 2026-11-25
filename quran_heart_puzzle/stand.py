#!/usr/bin/env python3
"""Desk stand for the Quran heart board.

The heart's rounded bottom sits in a cradle shaped to its own outline, leaning back
TILT degrees onto a back rest that is braced to a wide base. The front lip only covers
the outer rim, so no surah pocket is hidden.

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
BOARD_T     = 2.8     # mm board thickness at the rim (pieces' raised names stay clear of the lip)
SLOT_CLEAR  = 0.35    # mm gap each side of the board in the slot
EDGE_CLEAR  = 0.5     # mm gap between the heart outline and the cradle
CUP_H       = 18.0    # mm, how far up the heart's bottom the cradle reaches
CUP_WALL    = 4.0     # mm cradle wall around the outline
FRONT_T     = 2.4     # mm front lip thickness
RIM_COVER   = 2.0     # mm the front lip reaches over the rim (rim is 3 mm, pockets start after it)
BACK_T      = 4.0     # mm back plate thickness
REST_W      = 56.0    # mm back rest width
REST_H      = 80.0    # mm back rest height above the heart's bottom
LIFT        = 5.0     # mm heart's lowest point above the base top
BASE_T      = 4.0     # mm base plate thickness
BASE_W      = 130.0   # mm base width
BASE_FRONT  = 30.0    # mm base reach in front of the heart
BASE_BACK   = 85.0    # mm base reach behind the heart
BRACE_T     = 5.0     # mm rear brace thickness


def main():
    outline = shape(json.load(open(os.path.join(HERE, 'preview.json')))['outline'])
    y0 = outline.bounds[1]                                   # heart's bottom
    outline = affinity.translate(outline, 0, -y0)            # bottom tip at y = 0
    cx = outline.centroid.x
    slot = outline.buffer(EDGE_CLEAR, join_style=1)
    cup_band = box(-1e3, -1e3, 1e3, CUP_H)
    cup = outline.buffer(EDGE_CLEAR + CUP_WALL, join_style=1).intersection(cup_band)
    cb = cup.bounds
    pedestal = box(cb[0], -60, cb[2], CUP_H).intersection(
        unary_union([cup, box(cb[0], -60, cb[2], 0)]).convex_hull)
    rest = box(cx - REST_W / 2, 0, cx + REST_W / 2, REST_H).buffer(-8, join_style=1).buffer(8, join_style=1)

    n_back = -SLOT_CLEAR - BACK_T                 # n = 0 is the heart's back face
    n_front = BOARD_T + SLOT_CLEAR + FRONT_T
    # solid in heart-local coordinates: extrude() makes (x, y, n)
    local = extrude(unary_union([cup, pedestal]), n_back, n_front - n_back)
    local = local + extrude(rest, n_back, BACK_T)
    local = local - extrude(slot, -SLOT_CLEAR, BOARD_T + 2 * SLOT_CLEAR)              # the slot
    local = local - extrude(outline.buffer(-RIM_COVER, join_style=1), BOARD_T + SLOT_CLEAR - 0.01, 50)  # keep pockets visible

    # tilt: heart-up y -> (0, sin a, cos a), front n -> (0, -cos a, sin a)
    a = math.radians(TILT)
    M = [[1, 0, 0, 0],
         [0, math.sin(a), -math.cos(a), 0],
         [0, math.cos(a), math.sin(a), BASE_T + LIFT]]
    world = local.transform(M)
    world = world.trim_by_plane([0, 0, 1], BASE_T - 0.01)        # pedestal stops on the base

    # base plate (rounded), under the cradle, longer behind where the weight leans
    yb = world.bounding_box()
    base2d = box(-BASE_W / 2 + cx, -BASE_FRONT, BASE_W / 2 + cx, BASE_BACK).buffer(-12, join_style=1).buffer(12, join_style=1)
    base = extrude(base2d, 0, BASE_T)

    # rear brace: triangle from the back rest down to the base, in the y-z plane
    top_n = n_back                                          # back face of the back rest
    def w(y, n):                                            # local (y, n) -> world (Y, Z)
        return (y * math.sin(a) - n * math.cos(a), y * math.cos(a) + n * math.sin(a) + BASE_T + LIFT)
    p_top = w(REST_H - 14, top_n + 0.5)
    p_low = w(CUP_H, top_n + 0.5)
    tri = shapely.geometry.Polygon([p_top, (p_low[0], BASE_T - 0.01), (BASE_BACK - 14, BASE_T - 0.01)])
    brace = extrude(tri, cx - BRACE_T / 2, BRACE_T).transform([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]])

    stand = base + world + brace
    # brand underneath, mirrored so it reads from below
    brand, _ = fit_text(BRAND_TEXT, base2d.buffer(-14), font=BRAND_FONT, angles=(0,), max_em=14)
    brand = affinity.scale(brand, -1, 1, origin=brand.centroid).buffer(-0.02).buffer(0.02)
    stand = stand - extrude(brand, -1, 1 + BRAND_DEPTH)
    to_trimesh(stand).export(os.path.join(HERE, 'stand.stl'))

    # where the heart sits, for previews: local -> world transform of the board
    json.dump(dict(tilt=TILT, lift=LIFT, base_t=BASE_T, y0=y0), open(os.path.join(HERE, 'stand_pose.json'), 'w'))

    # stability check: heart + pieces centre of mass must fall inside the base footprint
    cy = outline.centroid.y
    com = w(cy, BOARD_T / 2)
    bb = stand.bounding_box()
    print(f'stand {bb[3]-bb[0]:.0f} x {bb[4]-bb[1]:.0f} x {bb[5]-bb[2]:.0f} mm, '
          f'heart CoM over base at Y={com[0]:.0f} mm (base spans {-BASE_FRONT:.0f}..{BASE_BACK:.0f}), '
          f'volume {stand.volume()/1000:.1f} cm3 = {stand.volume()/1000*1.24:.0f} g solid')


if __name__ == '__main__':
    main()
