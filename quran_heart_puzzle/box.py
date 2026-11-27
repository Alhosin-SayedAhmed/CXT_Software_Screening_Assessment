#!/usr/bin/env python3
"""Heart-shaped storage boxes for the 114 surah pieces - two designs.

Design 1, press-fit lid:
  box_base.stl - the box (print as is, bottom on the plate)
  box_lid.stl  - the lid, already flipped upside down for printing (top face on the plate)
Design 2, hinged lid (two hinges on the back, one per lobe, pinned with 1.75 mm filament):
  box_hinged_base.stl - the box with its hinge knuckles
  box_hinged_lid.stl  - the lid with its knuckles, flipped for printing

Usage:  python3 box.py      (settings in the CONFIG block)
"""
import os, math, json
import numpy as np
import shapely
from shapely.geometry import Polygon, Point
from shapely import affinity
import manifold3d as m3d
from build import extrude, fit_text, to_trimesh, HANGER_FONT, BRAND_TEXT, BRAND_FONT, BRAND_DEPTH

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- CONFIG
BOX_W        = 100.0   # mm, outer width of the heart
BOX_H        = 34.0    # mm, height of the box part (without lid)
WALL         = 2.0     # mm, side wall thickness
FLOOR        = 1.6     # mm, bottom thickness
LID_T        = 2.4     # mm, lid plate thickness
LIP_H        = 10.0    # mm, how deep the lid lip goes into the box
LIP_T        = 1.6     # mm, lip wall thickness
LID_CLEAR    = 0.15    # mm, gap per side between lip and box wall (snug press fit)
NOTCH_W      = 14.0    # mm, thumb notch width in the box rim
NOTCH_D      = 3.0     # mm, thumb notch depth
LID_TEXT     = 'خيركم من تعلم القرآن وعلمه'
LID_TEXT_D   = 0.6     # mm, engraving depth of the lid text
# hinged design
H_LIP_H      = 3.0     # mm, shorter lip so it swings clear of the front wall
H_LID_CLEAR  = 0.25    # mm, gap per side between lip and wall
KNUCKLE_R    = 3.5     # mm, hinge barrel radius
KNUCKLE_L    = 7.6     # mm, length of each barrel segment (3 per hinge: box-lid-box)
KNUCKLE_GAP  = 0.4     # mm, gap between neighbouring barrels
AXIS_OUT     = 1.0     # mm, gap between the heart outline and the barrels
PIN_D        = 1.75    # mm, pin = a piece of 1.75 mm filament
PIN_HOLE_BOX = 1.95    # mm, hole in the box barrels (holds the pin)
PIN_HOLE_LID = 2.25    # mm, hole in the lid barrel (turns freely)
# front clip on the hinged box: a tab hangs from the lid over a small flat at the heart's tip,
# a ridge inside the tab clicks into a groove on the box front
TIP_FLAT     = 6.5     # mm cut off the heart's tip to give the clip a flat face
CLIP_W       = 9.0     # mm tab width
CLIP_T       = 1.4     # mm tab thickness (thin enough to flex)
CLIP_GAP     = 0.15    # mm between tab and box front
CLIP_DOWN    = 8.0     # mm the tab reaches below the lid
CLIP_RIDGE   = 0.5     # mm ridge on the inside of the tab
CLIP_GROOVE  = 0.65    # mm groove depth in the box front
CLIP_Z       = 4.5     # mm ridge centre below the rim


def heart(width):
    """Classic heart outline (♥) of the given width, centred on its bounding box."""
    t = np.linspace(0, 2 * math.pi, 720, endpoint=False)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    p = Polygon(np.c_[x, y]).buffer(0)
    s = width / (p.bounds[2] - p.bounds[0])
    p = affinity.scale(p, s, s, origin=(0, 0))
    p = p.buffer(-2, join_style=1).buffer(2, join_style=1)        # soften the two cusps
    b = p.bounds
    return affinity.translate(p, -(b[0] + b[2]) / 2, -(b[1] + b[3]) / 2)


def brand_cut(outer):
    """ZeroCut engraved into the underside, mirrored so it reads correctly from below."""
    brand, _ = fit_text(BRAND_TEXT, outer.buffer(-25), font=BRAND_FONT, angles=(0,), max_em=16)
    brand = affinity.scale(brand, -1, 1, origin=brand.centroid)
    brand = brand.buffer(-0.02, join_style=1).buffer(0.02, join_style=1)
    return extrude(brand, -1, 1 + BRAND_DEPTH)


def thumb_notch(outer):
    """Half-round notch in the rim at the widest point of the right lobe, to lift the lid."""
    nx = outer.bounds[2]
    ny = max((pt for pt in outer.exterior.coords), key=lambda q: q[0])[1] + 0.37   # off-vertex: avoids a degenerate edge
    return m3d.Manifold.cylinder(WALL * 4, NOTCH_W / 2, NOTCH_W / 2, 64) \
        .rotate([0, 90, 0]).translate([nx - WALL * 2, ny, BOX_H + NOTCH_W / 2 - NOTCH_D])


def lid_text(outer, z_top):
    txt, em = fit_text(LID_TEXT, outer.buffer(-11), font=HANGER_FONT, angles=(0,), max_em=22)
    return extrude(txt, z_top - LID_TEXT_D, LID_TEXT_D + 1), em


def profile_along_x(poly, x0, x1):
    """Extrude a 2D profile drawn in the (y, z) plane along x from x0 to x1."""
    m = extrude(poly, x0, x1 - x0)                         # coords (y, z, x)
    return m.transform([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]])


def x_cylinder(x0, x1, y, z, r):
    return m3d.Manifold.cylinder(x1 - x0, r, r, 48).rotate([0, 90, 0]).translate([x0, y, z])


def main():
    outer = heart(BOX_W)
    inner = outer.buffer(-WALL, join_style=1)
    lip_out = inner.buffer(-LID_CLEAR, join_style=1)
    lip_in = lip_out.buffer(-LIP_T, join_style=1)

    # ---- box
    box = extrude(outer, 0, BOX_H) - extrude(inner, FLOOR, BOX_H)
    notch = thumb_notch(outer)
    box = box - notch - brand_cut(outer)
    to_trimesh(box).export(os.path.join(HERE, 'box_base.stl'))

    # ---- lid (modelled the way it sits on the box: lip at the bottom, plate on top)
    lid = extrude(lip_out.difference(lip_in), 0, LIP_H + 0.01) + extrude(outer, LIP_H, LID_T)
    cut, em = lid_text(outer, LIP_H + LID_T)
    lid = lid - cut
    to_trimesh(lid).export(os.path.join(HERE, 'box_lid_assembled.stl'))
    # print orientation: flip it over so the flat top lies on the plate
    flipped = lid.rotate([180, 0, 0]).translate([0, 0, LIP_H + LID_T])
    to_trimesh(flipped).export(os.path.join(HERE, 'box_lid.stl'))

    vol = inner.area * (BOX_H - FLOOR - LIP_H) / 1000
    b = outer.bounds
    print(f'box {b[2]-b[0]:.0f} x {b[3]-b[1]:.0f} x {BOX_H + LID_T:.1f} mm closed, '
          f'usable volume {vol:.0f} cm3, lid text {em:.1f} mm')
    hinged(outer, inner)


def hinged(outer, inner):
    """Design 2: same heart box, lid joined to the box by two pinned hinges on the back,
    and a snap clip at the front so it stays shut."""
    yf = outer.bounds[1] + TIP_FLAT           # flat front face for the clip
    outer = outer.intersection(shapely.geometry.box(-1e3, yf, 1e3, 1e3))
    inner = outer.buffer(-WALL, join_style=1)
    top = BOX_H + LID_T                       # lid top in use
    az = top - KNUCKLE_R - 0.05               # hinge axis height: barrel top just under the lid top
    pts = np.asarray(outer.exterior.coords)
    lobes = [pts[pts[:, 0] < 0], pts[pts[:, 0] > 0]]
    lobe_x = [float(l[l[:, 1].argmax(), 0]) for l in lobes]
    ay = float(pts[:, 1].max()) + AXIS_OUT + KNUCKLE_R   # hinge axis y (behind the lobes)
    seg = KNUCKLE_L + KNUCKLE_GAP
    box_parts, lid_parts, box_holes, lid_holes = [], [], [], []
    for cx in lobe_x:
        spans = [(cx - 1.5 * seg + KNUCKLE_GAP / 2, 'box'), (cx - 0.5 * seg + KNUCKLE_GAP / 2, 'lid'),
                 (cx + 0.5 * seg + KNUCKLE_GAP / 2, 'box')]
        for x0, who in spans:
            x1 = x0 + KNUCKLE_L
            col = outer.intersection(shapely.geometry.box(x0, -1e3, x1, 1e3))
            y_lo = col.bounds[3] - 3.0                                  # reach well into the wall
            barrel = Point(ay, az).buffer(KNUCKLE_R, 64)
            if who == 'box':
                # barrel + 45 degree gusset down to the back wall (prints without support)
                drop = (ay - y_lo) + KNUCKLE_R * 1.42
                prof = shapely.geometry.MultiPoint(list(barrel.exterior.coords) +
                                                   [(y_lo, az - drop), (y_lo, BOX_H)]).convex_hull
                prof = prof.intersection(shapely.geometry.box(-1e3, 0, 1e3, top))
                # keep clear of the lid plate edge above the rim
                prof = prof.difference(shapely.geometry.box(-1e3, BOX_H, col.bounds[3] + 0.5, 1e3))
                box_parts.append(profile_along_x(prof, x0, x1))
                box_holes.append(x_cylinder(x0 - 1, x1 + 1, ay, az, PIN_HOLE_BOX / 2))
            else:
                # barrel + a strap at lid level that joins it to the lid plate
                strap = shapely.geometry.box(y_lo, BOX_H + 0.03, ay + 1.0, top - 0.03)   # off the plate faces: clean union
                lid_parts.append(profile_along_x(unary(barrel, strap), x0, x1))
                lid_holes.append(x_cylinder(x0 - 1, x1 + 1, ay, az, PIN_HOLE_LID / 2))

    hollow = extrude(inner, FLOOR, BOX_H + 10)
    box = extrude(outer, 0, BOX_H)
    for p in box_parts:
        box = box + p
    box = box - hollow - thumb_notch(outer) - brand_cut(outer)
    for h in box_holes:
        box = box - h
    # clip: V groove across the flat front face of the box
    flat_w = outer.intersection(shapely.geometry.box(-1e3, yf - 0.01, 1e3, yf + 0.01)).bounds
    cw = min(CLIP_W, (flat_w[2] - flat_w[0]) - 1.0)
    zc = BOX_H - CLIP_Z
    groove = Polygon([(yf - 1, zc - CLIP_GROOVE - 1), (yf + CLIP_GROOVE, zc), (yf - 1, zc + CLIP_GROOVE + 1)])
    box = box - profile_along_x(groove, -cw / 2 - 0.6, cw / 2 + 0.6)
    to_trimesh(box).export(os.path.join(HERE, 'box_hinged_base.stl'))

    lip_out = inner.buffer(-H_LID_CLEAR, join_style=1)
    lip_in = lip_out.buffer(-LIP_T, join_style=1)
    lid = extrude(lip_out.difference(lip_in), BOX_H - H_LIP_H, H_LIP_H + 0.01) + extrude(outer, BOX_H, LID_T)
    for p in lid_parts:
        lid = lid + p
    # clip tab hanging from the lid's front edge, ridge inside, finger lip outside at the bottom
    yi = yf - CLIP_GAP                       # tab inner face
    yo = yi - CLIP_T                         # tab outer face
    zb = BOX_H - CLIP_DOWN
    tab = unary(Polygon([(yo, zb), (yi, zb), (yi, top - 0.03), (yo, top - 0.03)]),
                shapely.geometry.box(yo, BOX_H + 0.03, yf + 1.5, top - 0.03))
    ridge = Polygon([(yi - 0.2, zc - CLIP_RIDGE - 0.2), (yi + CLIP_RIDGE, zc), (yi - 0.2, zc + CLIP_RIDGE + 0.2)])
    lip = Polygon([(yo + 0.2, zb), (yo - 1.6, zb), (yo + 0.2, zb + 2.2)])   # outward finger lip, 45 degrees
    lid = lid + profile_along_x(unary(tab, ridge, lip), -cw / 2, cw / 2)
    cut, em = lid_text(outer, top)
    lid = lid - cut
    for h in lid_holes:
        lid = lid - h
    to_trimesh(lid).export(os.path.join(HERE, 'box_hinged_lid_assembled.stl'))
    flipped = lid.rotate([180, 0, 0]).translate([0, 0, top])
    to_trimesh(flipped).export(os.path.join(HERE, 'box_hinged_lid.stl'))
    pin_len = 3 * KNUCKLE_L + 2 * KNUCKLE_GAP - 0.5
    print(f'hinged box: axis y={ay:.2f} z={az:.2f}, hinges at x={lobe_x[0]:.1f} / {lobe_x[1]:.1f}, '
          f'2 pins of {PIN_D} mm filament, {pin_len:.0f} mm long')
    print(f'front clip: tab {cw:.1f} mm wide, ridge {CLIP_RIDGE} mm into a {CLIP_GROOVE} mm groove')
    json.dump(dict(axis_y=ay, axis_z=az, lobe_x=lobe_x, box_h=BOX_H, top=top), open(os.path.join(HERE, 'box_hinged_axis.json'), 'w'))


def unary(*g):
    from shapely.ops import unary_union
    return unary_union(g)


if __name__ == '__main__':
    main()
