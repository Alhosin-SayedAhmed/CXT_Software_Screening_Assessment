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
# crescent = outer circle minus a bigger inner circle shifted up; the horns end
# MOON_SPAN degrees apart (seen from the outer circle's centre), less than a half circle
MOON_R      = 72.0    # mm outer radius
MOON_SPAN   = 135.0   # deg from horn tip to horn tip (between 90 and 180)
MOON_THICK  = 18.0    # mm crescent thickness at its middle (under the heart)
MOON_BELOW  = 12.0    # mm the crescent reaches below the heart's bottom tip
MOON_ROT    = 0.0     # deg, tilt the crescent sideways (0 = horns up evenly)
REST_W      = 34.0    # mm hidden back rest behind the heart (not seen from the front)
REST_H      = 72.0    # mm back rest height above the heart's bottom
BASE_T      = 4.0     # mm base plate thickness
BASE_RX     = 62.0    # mm base half-width (oval)
BASE_RY     = 48.0    # mm base half-depth (oval)
BASE_SHIFT  = 26.0    # mm base centre behind the heart (the heart leans back)
BRACE_T     = 6.0     # mm rear brace thickness


def main():
    outline = shape(json.load(open(os.path.join(HERE, 'preview.json')))['outline'])
    y0 = outline.bounds[1]
    outline = affinity.translate(outline, 0, -y0)            # heart's bottom tip at y = 0
    cx = outline.centroid.x
    a = math.radians(TILT)

    # crescent in the heart's plane
    cy = MOON_R - MOON_BELOW
    # inner circle chosen so it meets the outer circle exactly at the horn tips
    c = math.cos(math.radians(MOON_SPAN / 2))
    d = ((MOON_R - MOON_THICK) ** 2 - MOON_R ** 2) / (2 * MOON_R * c - 2 * (MOON_R - MOON_THICK))
    r_in = MOON_R - MOON_THICK + d
    moon = Point(cx, cy).buffer(MOON_R, 256).difference(Point(cx, cy + d).buffer(r_in, 256))
    moon = affinity.rotate(moon, MOON_ROT, origin=(cx, 0))
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
    rest = box(cx - REST_W / 2, 0, cx + REST_W / 2, REST_H).buffer(-8, join_style=1).buffer(8, join_style=1)
    rest = rest.intersection(outline.buffer(-6, join_style=1))          # stays hidden behind the heart
    local = local + extrude(rest.union(box(cx - REST_W / 2, 2, cx + REST_W / 2, 20)), n_back, BACK_T)
    local = local - extrude(box(-1e3, CUP_H, 1e3, 1e3), n_back + BACK_T, 50)
    local = local - extrude(slot, -SLOT_CLEAR, BOARD_T + 2 * SLOT_CLEAR)
    local = local - extrude(outline.buffer(-RIM_COVER, join_style=1), BOARD_T + SLOT_CLEAR - 0.01, 50)

    # lift so the crescent's lowest point sinks just into the base
    lift = BASE_T - moon.bounds[1] * math.cos(a) - 0.5
    M = [[1, 0, 0, 0],
         [0, math.sin(a), -math.cos(a), 0],
         [0, math.cos(a), math.sin(a), lift]]
    world = local.transform(M).trim_by_plane([0, 0, 1], 0)

    base2d = affinity.scale(Point(cx, BASE_SHIFT).buffer(1, 128), BASE_RX, BASE_RY, origin=(cx, BASE_SHIFT))
    base = extrude(base2d, 0, BASE_T)

    def w(y, n):                                            # local (y, n) -> world (Y, Z)
        return (y * math.sin(a) - n * math.cos(a), y * math.cos(a) + n * math.sin(a) + lift)
    # hidden rear brace from the crescent's back down to the base
    p_top = w(REST_H - 12, n_back + 0.5)
    p_low = w(moon.bounds[1] + 6, n_back + 0.5)
    back_y = BASE_SHIFT + BASE_RY - 10
    tri = shapely.geometry.Polygon([p_top, (p_low[0], BASE_T - 0.01), (back_y, BASE_T - 0.01)])
    brace = extrude(tri, cx - BRACE_T / 2, BRACE_T).transform([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]])

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
          f'heart CoM at Y={com[0]:.0f} mm (base spans {BASE_SHIFT-BASE_RY:.0f}..{BASE_SHIFT+BASE_RY:.0f}), '
          f'volume {stand.volume()/1000:.1f} cm3')


if __name__ == '__main__':
    main()
