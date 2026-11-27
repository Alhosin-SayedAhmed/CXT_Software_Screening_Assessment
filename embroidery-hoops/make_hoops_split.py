"""
Flower hoop decorated on BOTH faces, printed as TWO IDENTICAL HALVES (split horizontally through the
middle) + the snap ring + separate pins. Everything prints flat on the bed with NO supports:

  half  : flat mating face on the bed, decorated face up (raised rim, rounded edges, flowers, leaves,
          wavy line). Print it twice; the second one is turned over, so the hoop is decorated front and back.
          3 blind pin holes in the flat face line the halves up; the hanging hole goes through both.
  pins  : separate D-shaped pins that lie flat on the bed (strong along their length).
  ring  : the usual snap ring (bead in the middle clicks into the groove split between the two halves).

Thinner than the one-piece hoop to keep the frame light (~20 g, max ~30 g).
"""
import math, os, sys
import numpy as np
from manifold3d import Manifold, CrossSection
from shapely.geometry import Point
import trimesh
import make_hoops_v2 as v2
from make_hoops_v2 import flower_outline, loft, fillet_pts, motif_pattern, to_cs, to_tm

SIZES      = [60, 80, 100]
PETAL_OFF  = 3.5       # petal centres beyond the rim
PETAL_K    = 0.45      # petal size
PH         = 1.2       # flower plate thickness PER HALF  (whole frame: 2.4 mm)
RH         = 3.6       # rim height PER HALF              (whole frame / ring: 7.2 mm)
F_PLATE    = 0.9       # rounding of the petal edge
F_RIM      = 1.2       # rounding of the rim edges
TEX_H      = 0.4       # raised decoration
PIN_D      = 2.5       # pin diameter (D-shaped, flat side 0.25 mm)
PIN_HOLE   = 2.6       # hole diameter: snug fit (not loose)
PIN_DEPTH  = 2.4       # hole depth in each half
PIN_ANGLES = (90, 210, 330)   # symmetric about the Y axis so the turned-over half lines up
N_PINS     = 4         # 3 needed + 1 spare
RING_WALL, GAP, RIM_W = v2.RING_WALL, v2.FABRIC_GAP, v2.RIM_WIDTH
BEAD, GROOVE, RING_CHAMF = v2.BEAD, v2.GROOVE, v2.RING_CHAMF
SEG, ARC = v2.SEG, v2.ARC

def dims(D):
    Ri = (D + 2 * RING_WALL) / 2 + GAP
    Ro = Ri + RIM_W
    Rc = Ro + PETAL_OFF
    rp = 2 * Rc * math.sin(math.pi / v2.PETALS) * PETAL_K
    return Ri, Ro, Rc, rp

def half(D):
    Ri, Ro, Rc, rp = dims(D)
    Rtip = Rc + rp
    outline = flower_outline(Rc, rp)
    top = [(PH - F_PLATE + dz, 1 - ins / Rtip) for dz, ins in fillet_pts(F_PLATE)]
    plate = loft(outline, [(0.0, 1.0)] + top)
    f = F_RIM
    prof = [(Ri, 0.0), (Ro, 0.0)]
    for a in np.linspace(0, math.pi / 2, ARC + 1):
        prof.append((Ro - f + f * math.cos(a), RH - f + f * math.sin(a)))
    for a in np.linspace(math.pi / 2, math.pi, ARC + 1)[1:]:
        prof.append((Ri + f + f * math.cos(a), RH - f + f * math.sin(a)))
    body = plate + Manifold.revolve(CrossSection([prof]), SEG)
    body = body - Manifold.cylinder(RH + 2, Ri, Ri, SEG).translate([0, 0, -1])
    body = body - Manifold.cylinder(RH + 2, v2.HANG_HOLE_D / 2, v2.HANG_HOLE_D / 2, 32).translate([0, Rc, -1])
    # half of the snap groove sits at the mating face (z = 0 is the middle of the assembled hoop)
    g = [(Ri - 0.2, -GROOVE - 0.5), (Ri + GROOVE, -0.3), (Ri + GROOVE, 0.3), (Ri - 0.2, GROOVE + 0.5)]
    body = body - Manifold.revolve(CrossSection([g]), SEG)
    # pin holes in the flat face
    rpin = (Ri + Ro) / 2
    for a in PIN_ANGLES:
        t = math.radians(a)
        body = body - Manifold.cylinder(PIN_DEPTH + 1, PIN_HOLE / 2, PIN_HOLE / 2, 32).translate(
            [rpin * math.cos(t), rpin * math.sin(t), -1])
    # decoration on the top face (same motifs as the one-piece hoop)
    from shapely.geometry import Polygon
    plate_face = Polygon(outline).buffer(-(F_PLATE + 0.9)).difference(Point(0, 0).buffer(Ro + 0.9, 128)) \
                                  .difference(Point(0, Rc).buffer(v2.HANG_HOLE_D / 2 + 1.2, 24))
    e = F_RIM + 0.4
    rim_face = Point(0, 0).buffer(Ro - e, 128).difference(Point(0, 0).buffer(Ri + e, 128))
    pf, rf = motif_pattern(Rc, rp, Ri, Ro, plate_face, rim_face)
    body = body + Manifold.extrude(to_cs(pf), TEX_H + 0.05).translate([0, 0, PH - 0.05])
    body = body + Manifold.extrude(to_cs(rf), TEX_H + 0.05).translate([0, 0, RH - 0.05])
    half.footprint = Polygon(outline)
    return body

def ring(D):
    ri, ro, c, H = D / 2, D / 2 + RING_WALL, RING_CHAMF, 2 * RH
    m, b = H / 2, BEAD
    prof = [(ri, 0), (ro - c, 0), (ro, c), (ro, m - 2 * b), (ro + b, m - b), (ro + b, m + b), (ro, m + 2 * b),
            (ro, H - c), (ro - c, H), (ri, H)]
    return Manifold.revolve(CrossSection([prof]), SEG)

def pins():
    """N_PINS D-shaped pins lying along X, flat side down, spaced 4 mm apart."""
    L = 2 * PIN_DEPTH - 0.4
    r, flat, ch = PIN_D / 2, 0.25, 0.35
    out = Manifold()
    for k in range(N_PINS):
        p = Manifold.cylinder(L - 2 * ch, r, r, 32).translate([0, 0, ch])
        p = p + Manifold.cylinder(ch, r - ch, r, 32) + Manifold.cylinder(ch, r, r - ch, 32).translate([0, 0, L - ch])
        p = p.rotate([0, 90, 0])                       # lie along X
        p = p.translate([0, 0, r - flat])              # axis at height r - flat
        p = p ^ Manifold.cube([2 * L + 2, 2 * r + 2, 10]).translate([-L - 1, -r - 1, 0])   # cut the flat side
        bb = p.bounding_box()
        out = out + p.translate([-bb[0], k * (PIN_D + 1.5), 0])
    return out

def layout(Dsize, tf_half, tr, tp, BED=256.0, M=3.0):
    """Two halves in opposite corners, ring + pins in a free corner; else split over two plates."""
    from shapely.affinity import translate as T
    Ri, Ro, Rc, rp = dims(Dsize)
    o = Rc + rp
    rr = Dsize / 2 + RING_WALL + BEAD
    a, far = o + M, BED - o - M
    def ok(cands):
        polys = [Point(x, y).buffer(r) for x, y, r in cands]
        return all(polys[i].buffer(1.5).disjoint(polys[j]) for i in range(len(polys)) for j in range(i + 1, len(polys))) \
            and all(x - r >= M - 1e-6 and y - r >= M - 1e-6 and x + r <= BED - M + 1e-6 and y + r <= BED - M + 1e-6 for x, y, r in cands)
    pins_r = 8.0
    for ring_pos in ((BED - rr - M, rr + M), (rr + M, BED - rr - M)):
        for pin_pos in ((rr + M + 2, rr + M + 2), (BED - M - pins_r, BED - M - pins_r), (M + pins_r, BED - M - pins_r), (BED - M - pins_r, M + pins_r)):
            c = [(a, a, o), (far, far, o), (*ring_pos, rr), (*pin_pos, pins_r)]
            if ok(c):
                return [[("half_1", tf_half, (a, a)), ("half_2", tf_half, (far, far)), ("ring", tr, ring_pos), ("pins", tp, pin_pos)]]
    # two plates: half + ring + pins, and half
    c1 = [(a, a, o), (BED - rr - M, BED - rr - M, rr), (BED - M - pins_r, M + pins_r, pins_r)]
    if ok(c1):
        return [[("half_1", tf_half, (a, a)), ("ring", tr, c1[1][:2]), ("pins", tp, c1[2][:2])],
                [("half_2", tf_half, (BED / 2, BED / 2))]]
    return [[("half_1", tf_half, (BED / 2, BED / 2))], [("half_2", tf_half, (BED / 2, BED / 2))],
            [("ring", tr, (BED / 2, BED / 2)), ("pins", tp, (BED / 2, BED / 2 - rr - 10))]]

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl"); os.makedirs(out, exist_ok=True)
    tp = to_tm(pins()); tp.export(os.path.join(out, "split_pins.stl"))
    for D in SIZES:
        hm = half(D)
        assert hm.status().name == "NoError" and len(hm.decompose()) == 1, "half must be one clean solid"
        th, tr = to_tm(hm), to_tm(ring(D))
        assert th.is_watertight and tr.is_watertight and tp.is_watertight
        th.export(os.path.join(out, f"split_{D}mm_half.stl"))
        tr.export(os.path.join(out, f"split_{D}mm_ring.stl"))
        plates = layout(D, th, tr, tp)
        for k, items in enumerate(plates, 1):
            sc = trimesh.Scene()
            for name, mesh, (x, y) in items:
                cx, cy = mesh.bounds.mean(0)[:2]
                sc.add_geometry(mesh.copy().apply_translation([x - cx - 128, y - cy - 128, 0]), node_name=name)
            b = sc.bounds; assert (b[1] - b[0])[:2].max() <= 256, (D, b)
            suf = "" if len(plates) == 1 else f"_{k}of{len(plates)}"
            sc.export(os.path.join(out, f"split_{D}mm_plate{suf}.3mf"))
        e = th.bounds[1] - th.bounds[0]
        print(f"{D:3d}mm half {e[0]:.1f} x {e[1]:.1f} x {e[2]:.2f} mm, faces {len(th.faces)}, plates {len(plates)}")
