"""
Two-part double-sided scalloped embroidery hoop.

  1) frame : ONE piece, raised round rim on BOTH faces, rounded edges, leaf emboss on the front.
             A V-groove runs around the inside of the bore at mid-height.
  2) ring  : inner ring, same height as the rim, with a V-bead around the middle.
             Lay the fabric over the ring and push the frame on: the bead + fabric click into
             the groove and lock the ring in place (works from either side).

Printing: the frame lies flat, back face down. The back rim stands on the bed and the petals
are 2.5 mm above it, so the petals need small supports ("on build plate only").
Usage: python3 make_hoops_2part.py   (needs manifold3d trimesh shapely numpy networkx lxml)
"""
import math, os
import numpy as np
from manifold3d import Manifold, CrossSection, JoinType, OpType
from shapely.geometry import Point
from shapely.ops import unary_union
import trimesh
from make_hoops_relief import to_cs, leaf_pattern, to_tm

SIZES        = [60, 80, 100]
PETALS       = 12
RING_WALL    = 3.5
FABRIC_GAP   = 0.55   # radial clearance per side for the fabric
RIM_WIDTH    = 5.0
H            = 9.0    # total rim height (= ring height)
PLATE_T      = 4.0    # total petal thickness (centred on the rim)
FILLET       = 1.2    # rounding of the visible edges
BED_CHAMFER  = 0.8    # 45 deg chamfer on edges that touch the bed (instead of a fillet)
EMBOSS_FRONT = True
EMBOSS_BACK  = "deboss"  # back faces the bed/supports -> the same leaf pattern, engraved instead of raised
DEBOSS_D     = 0.4      # engraving depth on the back
EMBOSS_H     = 0.4
HANG_HOLE_D  = 4.0
BEAD         = 0.5    # bead height on the ring (radial)
GROOVE       = 0.8    # groove depth in the frame bore (radial)
RING_CHAMF   = 0.6
SEG          = 256
DZ           = 0.2

def edged_extrude(cs, h, r, mode):
    """Extrude to height h; round ('fillet') or bevel ('chamfer') the TOP edges by r."""
    parts = [Manifold.extrude(cs, h - r)]
    n = int(round(r / DZ))
    for i in range(n):
        zr = (i + 1) * DZ
        off = zr if mode == "chamfer" else r - math.sqrt(max(r * r - zr * zr, 0.0))
        s = cs.offset(-off, JoinType.Round, 2.0, 48).simplify(0.02)
        if s.area() <= 0: break
        parts.append(Manifold.extrude(s, DZ + 0.01).translate([0, 0, h - r + i * DZ - 0.01]))  # overlap -> fused
    return Manifold.batch_boolean(parts, OpType.Add)

def frame(D):
    ring_od = D + 2 * RING_WALL
    bore = ring_od + 2 * FABRIC_GAP
    rim_od = bore + 2 * RIM_WIDTH
    Rc = rim_od / 2 + 5.0
    rp = 2 * Rc * math.sin(math.pi / PETALS) * 0.55
    petals = [Point(Rc * math.cos(a), Rc * math.sin(a)).buffer(rp, 64)
              for a in (2 * math.pi * i / PETALS + math.pi / 2 for i in range(PETALS))]
    flower = unary_union(petals + [Point(0, 0).buffer(Rc, 128)])
    hole = Point(0, Rc).buffer(HANG_HOLE_D / 2, 32)
    bore_c = Point(0, 0).buffer(bore / 2, SEG)
    plate2d = to_cs(flower.difference(bore_c).difference(hole))
    rim2d = to_cs(Point(0, 0).buffer(rim_od / 2, SEG).difference(bore_c))
    mid, hp, hr = H / 2, PLATE_T / 2, H / 2

    def face(emboss, rim_mode, seed):
        # emboss: True = raised pattern, "deboss" = engraved pattern, False = smooth
        # one half (from the mid-plane outward), z = 0 .. hr
        m = edged_extrude(plate2d, hp, FILLET, "fillet") + edged_extrude(rim2d, hr, FILLET if rim_mode == "fillet" else BED_CHAMFER, rim_mode)
        if emboss:
            pf = flower.buffer(-(FILLET + 0.8)).difference(Point(0, 0).buffer(rim_od / 2 + 0.8, SEG)).difference(hole.buffer(1.2))
            e = max(FILLET, BED_CHAMFER) + 0.3
            rf = Point(0, 0).buffer(rim_od / 2 - e, SEG).difference(Point(0, 0).buffer(bore / 2 + e, SEG))
            pat = unary_union([leaf_pattern(pf, seed), leaf_pattern(rf, seed + 1)])
            for reg, z in ((pf, hp), (rf, hr)):
                t = pat.intersection(reg)
                if t.is_empty: continue
                if emboss == "deboss":
                    m = m - Manifold.extrude(to_cs(t), DEBOSS_D + 0.5).translate([0, 0, z - DEBOSS_D])
                else:
                    m = m + Manifold.extrude(to_cs(t), EMBOSS_H + 0.05).translate([0, 0, z - 0.05])
        return m

    front = face(EMBOSS_FRONT, "fillet", D).translate([0, 0, mid])
    back = face(EMBOSS_BACK, "chamfer", D + 7).mirror([0, 0, 1]).translate([0, 0, mid])
    body = front + back
    # V-groove around the bore at mid-height (45 deg walls -> prints without support)
    R = bore / 2
    g = [(R - 0.2, mid - GROOVE - 0.5), (R + GROOVE, mid - 0.3), (R + GROOVE, mid + 0.3), (R - 0.2, mid + GROOVE + 0.5)]
    body = body - Manifold.revolve(CrossSection([g]), SEG)
    return body, dict(bore=bore, rim_od=rim_od, outer=2 * (Rc + rp))

def ring(D):
    ri, ro, c, m, b = D / 2, D / 2 + RING_WALL, RING_CHAMF, H / 2, BEAD
    prof = [(ri, 0), (ro - c, 0), (ro, c),
            (ro, m - 2 * b), (ro + b, m - b), (ro + b, m + b), (ro, m + 2 * b),   # 45 deg bead
            (ro, H - c), (ro - c, H), (ri, H)]
    return Manifold.revolve(CrossSection([prof]), SEG)

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl"); os.makedirs(out, exist_ok=True)
    BED, M = 256.0, 3.0
    for D in SIZES:
        f, info = frame(D)
        assert f.status().name == "NoError", f.status()
        assert len(f.decompose()) == 1, "frame is not one solid"
        tf, tr = to_tm(f), to_tm(ring(D))
        assert tf.is_watertight and tr.is_watertight
        tf.export(os.path.join(out, f"hoop_{D}mm_2part_frame.stl"))
        tr.export(os.path.join(out, f"hoop_{D}mm_2part_ring.stl"))
        o, rr = info["outer"] / 2, D / 2 + RING_WALL + BEAD
        fp, rp_ = (o + M, o + M), (BED - rr - M, BED - rr - M)
        assert math.hypot(fp[0] - rp_[0], fp[1] - rp_[1]) > o + rr + 2, "ring overlaps frame"
        sc = trimesh.Scene()
        sc.add_geometry(tf.copy().apply_translation([fp[0] - BED / 2, fp[1] - BED / 2, 0]), node_name="frame")
        sc.add_geometry(tr.copy().apply_translation([rp_[0] - BED / 2, rp_[1] - BED / 2, 0]), node_name="ring")
        sc.export(os.path.join(out, f"hoop_{D}mm_2part_plate.3mf"))
        bead_r = D / 2 + RING_WALL + BEAD
        print(f"{D}mm: outer {2*o:.1f}, bore {info['bore']:.2f}, ring OD {D+2*RING_WALL:.1f} (bead {2*bead_r:.1f}), "
              f"snap with 0.3mm fabric: {(bead_r + 0.3 - info['bore']/2):.2f} mm interference, "
              f"frame {tf.volume/1000:.1f} cm3, faces {len(tf.faces)}")
