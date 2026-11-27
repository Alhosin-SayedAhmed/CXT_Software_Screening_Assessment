"""
Puffy heart hoop in the SAME SYSTEM as the two-half flower hoop:
  * two IDENTICAL halves (print the half twice), each printed flat side down with the puffy, decorated
    side up -> assembled heart is puffy and decorated on both faces, no supports
  * 3 recessed pin holes in each flat face + separate D-shaped pins (same pins file as the flower)
  * the round snap ring of the flower hoop (same height 7.2 mm), groove split at the mating plane
  * small raised hearts on the dome
"""
import math, os
import numpy as np
from manifold3d import Manifold, CrossSection
from shapely.geometry import Point
from shapely.ops import unary_union
import trimesh
import make_hoops_v2 as v2
import make_hoops_split as fs
import make_heart_puffy as hp
from make_heart_round import heart_around, flower_fill
from make_heart_hoops import ray_outline, centre_line_y
from make_hoops_v2 import loft, wave_band, to_cs, to_tm

SIZES     = [60, 80, 100]
MARGIN    = 7.0      # narrowest border between rim and heart edge
RH        = fs.RH    # rim height per half (3.6) -> ring 7.2 mm, same ring as the flower hoop
# dome of ONE half (the assembled heart is twice as thick)
Z_EDGE    = 0.6
Z_PEAK    = 3.4
EDGE_W    = 13.0
Z_RIMJOIN = 2.0
INNER_W   = 11.0
DECO_H    = 0.5
SEG, ARC, F_RIM = v2.SEG, v2.ARC, 1.2

def half(D):
    Ri, Ro = (D + 2 * v2.RING_WALL) / 2 + v2.FABRIC_GAP, (D + 2 * v2.RING_WALL) / 2 + v2.FABRIC_GAP + v2.RIM_WIDTH
    heart, rl = heart_around(Ro + MARGIN)
    out = ray_outline(heart, (0.0, 0.0))
    # dome parameters for one half
    hp.Z_EDGE, hp.Z_PEAK, hp.EDGE_W, hp.Z_RIMJOIN, hp.INNER_W = Z_EDGE, Z_PEAK, EDGE_W, Z_RIMJOIN, INNER_W
    hp.heightfield_solid.r_rim = Ro
    outer = loft(out, [(0.0, 1.0), (20.0, 1.0)])
    body = outer ^ hp.heightfield_solid(heart, False)
    f = F_RIM
    prof = [(Ri, 0.0), (Ro, 0.0)]
    for a in np.linspace(0, math.pi / 2, ARC + 1):
        prof.append((Ro - f + f * math.cos(a), RH - f + f * math.sin(a)))
    for a in np.linspace(math.pi / 2, math.pi, ARC + 1)[1:]:
        prof.append((Ri + f + f * math.cos(a), RH - f + f * math.sin(a)))
    body = body + Manifold.revolve(CrossSection([prof]), SEG)

    # decoration: hearts that follow the dome + wavy line on the rim
    y_dip, _ = centre_line_y(heart)
    hole_c = (0.0, (Ro + y_dip) / 2)
    hole = Point(*hole_c).buffer(v2.HANG_HOLE_D / 2 + 1.4, 24)
    face = heart.buffer(-4.0).difference(Point(0, 0).buffer(Ro + 2.5, 256)).difference(hole)
    motifs = flower_fill(face.buffer(-0.3), min_r=3.0, max_size=0.42 * rl)
    clean = lambda g: unary_union([x for x in getattr(g, "geoms", [g]) if x.area > 1.0]).simplify(0.03)
    pf = clean(unary_union([hp.heart_motif(x, y, s, a) for x, y, s, a in motifs]).intersection(face))
    body = body + (Manifold.extrude(to_cs(pf), 20.0) ^ hp.heightfield_solid(heart, False, lift=DECO_H))
    e = f + 0.4
    rim_face = Point(0, 0).buffer(Ro - e, 256).difference(Point(0, 0).buffer(Ri + e, 256))
    rf = clean(wave_band((Ri + Ro) / 2, 0.9, 24, 1.0).intersection(rim_face))
    body = body + Manifold.extrude(to_cs(rf), v2.TEX_H + 0.05).translate([0, 0, RH - 0.05])

    # bore, hanging hole, half of the snap groove at the mating face, recessed pin holes
    body = body - Manifold.cylinder(30, Ri, Ri, SEG).translate([0, 0, -1])
    body = body - Manifold.cylinder(30, v2.HANG_HOLE_D / 2, v2.HANG_HOLE_D / 2, 32).translate([hole_c[0], hole_c[1], -1])
    G = v2.GROOVE
    g = [(Ri - 0.2, -G - 0.5), (Ri + G, -0.3), (Ri + G, 0.3), (Ri - 0.2, G + 0.5)]
    body = body - Manifold.revolve(CrossSection([g]), SEG)
    rpin = (Ri + Ro) / 2
    for a in fs.PIN_ANGLES:
        t = math.radians(a)
        body = body - Manifold.cylinder(fs.PIN_DEPTH + 1, fs.PIN_HOLE / 2, fs.PIN_HOLE / 2, 32).translate(
            [rpin * math.cos(t), rpin * math.sin(t), -1])
    half.heart, half.motifs = heart, motifs
    return body

def plates_for(th, tr, tp, heart):
    """Plate 1: one half + ring + pins (ring in the free corner beside the heart's point); plate 2: the other half."""
    from shapely.affinity import translate as T
    BED, M = 256.0, 3.0
    hb = heart.bounds
    hx, hy = M - hb[0], BED - M - hb[3]                     # heart at the top-left
    H_ = T(heart, hx, hy)
    rr = (tr.bounds[1][0] - tr.bounds[0][0]) / 2
    for rx, ry in ((BED - M - rr, M + rr), (M + rr, M + rr)):
        if H_.buffer(2).disjoint(Point(rx, ry).buffer(rr)):
            for px, py in ((rx - rr - 12, M + 8), (BED - M - 10, ry + rr + 12), (M + 10, M + 8), (BED - M - 10, BED - M - 10)):
                if H_.buffer(2).disjoint(Point(px, py).buffer(9)) and Point(rx, ry).buffer(rr + 2).disjoint(Point(px, py).buffer(9)) \
                        and M + 9 <= px <= BED - M - 9 and M + 9 <= py <= BED - M - 9:
                    return [[("half_1", th, (hx, hy)), ("ring", tr, (rx, ry)), ("pins", tp, (px, py))],
                            [("half_2", th, (BED / 2 - (hb[0] + hb[2]) / 2, BED / 2 - (hb[1] + hb[3]) / 2))]]
    return [[("half_1", th, (BED / 2 - (hb[0] + hb[2]) / 2, BED / 2 - (hb[1] + hb[3]) / 2))],
            [("half_2", th, (BED / 2 - (hb[0] + hb[2]) / 2, BED / 2 - (hb[1] + hb[3]) / 2))],
            [("ring", tr, (BED / 2, BED / 2)), ("pins", tp, (BED / 2, 30))]]

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl"); os.makedirs(out, exist_ok=True)
    tp = to_tm(fs.pins())
    for D in SIZES:
        m = half(D)
        assert m.status().name == "NoError" and len(m.decompose()) == 1, "half must be one clean solid"
        th, tr = to_tm(m), to_tm(fs.ring(D))
        assert th.is_watertight and tr.is_watertight
        th.export(os.path.join(out, f"hsplit_{D}mm_half.stl"))
        tr.export(os.path.join(out, f"hsplit_{D}mm_ring.stl"))
        for k, items in enumerate(plates_for(th, tr, tp, half.heart), 1):
            sc = trimesh.Scene()
            for name, mesh, (x, y) in items:
                if name.startswith("half"):
                    mm = mesh.copy().apply_translation([x - 128, y - 128, 0])      # x, y = heart-origin offset
                else:
                    cx, cy = mesh.bounds.mean(0)[:2]
                    mm = mesh.copy().apply_translation([x - cx - 128, y - cy - 128, 0])
                sc.add_geometry(mm, node_name=name)
            b = sc.bounds; assert b[0][0] >= -128.01 and b[1][0] <= 128.01 and b[0][1] >= -128.01 and b[1][1] <= 128.01, (D, k, b)
            sc.export(os.path.join(out, f"hsplit_{D}mm_plate_{k}.3mf"))
        e = th.bounds[1] - th.bounds[0]
        print(f"{D:3d}mm heart {e[0]:.0f} x {e[1]:.0f} mm, half {e[2]:.2f} mm tall, hearts {len(half.motifs)}, faces {len(th.faces)}")
