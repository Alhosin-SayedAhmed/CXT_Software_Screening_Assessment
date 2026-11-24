"""
Double-sided (relief) scalloped embroidery hoop - looks the same from front and back.

The frame is printed as TWO IDENTICAL HALVES (print the half file twice), each with its
flat mating face on the bed and its decorated face on top -> no supports needed.
Glue the halves back-to-back; 3 pins (pieces of 1.75 mm filament) align them.

Parts per size:
  hoop_XXmm_relief_half.stl  -> print x2 (front half + back half)
  hoop_XXmm_relief_ring.stl  -> inner ring, same height as the frame rim, chamfered both sides
  hoop_XXmm_relief_plate.3mf -> both halves + ring on one A1 plate
"""
import math, os, random
import numpy as np
from manifold3d import Manifold, CrossSection, JoinType, OpType
from shapely.geometry import Point, Polygon
from shapely.geometry.polygon import orient
from shapely.affinity import rotate, translate, scale
from shapely.ops import unary_union
import trimesh

# ---------------- parameters (mm) ----------------
SIZES       = [60, 80, 100]
PETALS      = 12
RING_WALL   = 3.5
FABRIC_GAP  = 0.55     # radial clearance per side for the fabric
RIM_WIDTH   = 5.0
PLATE_T     = 2.0      # flower plate thickness PER HALF  (total 4.0)
RIM_T       = 4.5      # rim height PER HALF             (total 9.0)
FILLET      = 1.2      # rounding radius of the visible edges
EMBOSS      = True     # raised leaf texture on the visible faces
EMBOSS_H    = 0.4      # texture height (2 layers @0.2)
HANG_HOLE_D = 4.0
PIN_D       = 2.0      # holes for 1.75 mm filament pins
PIN_DEPTH   = 3.0
RING_CHAMF  = 0.6
SEG         = 256
DZ          = 0.2      # slice step for the rounded edges

def to_cs(geom):
    polys = []
    for g in getattr(geom, "geoms", [geom]):
        if g.is_empty: continue
        g = orient(g, 1.0)
        polys.append(np.asarray(g.exterior.coords[:-1], dtype=np.float64))
        for h in g.interiors:
            polys.append(np.asarray(h.coords[:-1], dtype=np.float64))
    return CrossSection(polys)

def rounded_extrude(cs, h, r):
    """Extrude cs to height h with the top edges rounded by radius r (inside and outside contours)."""
    base = Manifold.extrude(cs, h - r)
    parts = [base]
    n = int(round(r / DZ))
    for i in range(n):
        zr = (i + 1) * DZ                       # height above the start of the fillet
        off = r - math.sqrt(max(r * r - zr * zr, 0.0))
        s = cs.offset(-off, JoinType.Round, 2.0, 48).simplify(0.02)
        if s.area() <= 0: break
        parts.append(Manifold.extrude(s, DZ + 0.01).translate([0, 0, h - r + i * DZ - 0.01]))  # overlap -> fused
    return Manifold.batch_boolean(parts, OpType.Add)

def leaf_pattern(region, seed):
    """Small leaves + dots scattered over region (shapely), like an embossed leather print."""
    rnd = random.Random(seed)
    minx, miny, maxx, maxy = region.bounds
    leaf = scale(Point(0, 0).buffer(1.0, 8), 2.4, 0.95)       # 4.8 x 1.9 mm leaf
    shapes, step = [], 4.6
    y = miny
    row = 0
    while y < maxy:
        x = minx + (step / 2 if row % 2 else 0)
        while x < maxx:
            px, py = x + rnd.uniform(-0.6, 0.6), y + rnd.uniform(-0.6, 0.6)
            if rnd.random() < 0.72:
                ang = math.degrees(math.atan2(py, px)) + 90 + rnd.uniform(-35, 35)
                shapes.append(translate(rotate(leaf, ang, origin=(0, 0)), px, py))
            else:
                shapes.append(Point(px, py).buffer(0.85, 4))
            x += step
        y += step * 0.87
        row += 1
    pat = unary_union(shapes).intersection(region)
    # drop slivers that are too thin to print
    pat = pat.buffer(-0.35, 8).buffer(0.35, 8).simplify(0.04)
    return pat

def frame_half(D):
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
    plate2d = flower.difference(bore_c).difference(hole)
    rim2d = Point(0, 0).buffer(rim_od / 2, SEG).difference(bore_c)

    body = rounded_extrude(to_cs(plate2d), PLATE_T, min(FILLET, PLATE_T - 0.4)) \
         + rounded_extrude(to_cs(rim2d), RIM_T, FILLET)

    if EMBOSS:
        plate_face = flower.buffer(-(FILLET + 0.8)).difference(Point(0, 0).buffer(rim_od / 2 + 0.8, SEG)) \
                           .difference(hole.buffer(1.2))
        rim_face = Point(0, 0).buffer(rim_od / 2 - FILLET - 0.3, SEG).difference(
                   Point(0, 0).buffer(bore / 2 + FILLET + 0.3, SEG))
        pat = unary_union([leaf_pattern(plate_face, D), leaf_pattern(rim_face, D + 1)])
        tex_plate = pat.intersection(plate_face)
        tex_rim = pat.intersection(rim_face)
        if not tex_plate.is_empty:
            body = body + Manifold.extrude(to_cs(tex_plate), EMBOSS_H + 0.05).translate([0, 0, PLATE_T - 0.05])
        if not tex_rim.is_empty:
            body = body + Manifold.extrude(to_cs(tex_rim), EMBOSS_H + 0.05).translate([0, 0, RIM_T - 0.05])

    # alignment pin holes in the rim, from the mating (bottom) face; symmetric about the Y axis
    rpin = (bore / 2 + rim_od / 2) / 2
    for a in (90, 210, 330):
        t = math.radians(a)
        body = body - Manifold.cylinder(PIN_DEPTH + 0.5, PIN_D / 2, PIN_D / 2, 24) \
                          .translate([rpin * math.cos(t), rpin * math.sin(t), -0.5])
    return body, dict(bore=bore, rim_od=rim_od, outer=2 * (Rc + rp))

def ring_part(D):
    r_in, r_out = D / 2, D / 2 + RING_WALL
    h, c = 2 * RIM_T, RING_CHAMF
    prof = [(r_in, 0), (r_out - c, 0), (r_out, c), (r_out, h - c), (r_out - c, h), (r_in, h)]
    return Manifold.revolve(CrossSection([prof]), SEG)

def to_tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)

if __name__ == "__main__":
    import manifold3d
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl"); os.makedirs(out, exist_ok=True)
    for D in SIZES:
        f, info = frame_half(D)
        assert f.status().name == "NoError", f.status()
        tf, tr = to_tm(f), to_tm(ring_part(D))
        assert tf.is_watertight and tr.is_watertight
        tf.export(os.path.join(out, f"hoop_{D}mm_relief_half.stl"))
        tr.export(os.path.join(out, f"hoop_{D}mm_relief_ring.stl"))
        o, rr = info["outer"] / 2, D / 2 + RING_WALL
        BED, M = 256.0, 3.0
        a = o + M                                   # first half in the bottom-left corner
        lay1 = [("half_front", tf, (a, a))]
        far = BED - o - M                           # second half in the opposite corner
        both = (far - a) * math.sqrt(2) >= 2 * o + 4
        ringpos = (BED - rr - M, rr + M)            # ring in the bottom-right corner
        if both:
            lay1.append(("half_back", tf, (far, far)))
        else:
            ringpos = (BED - rr - M, BED - rr - M)  # only one half on this plate: ring in the free corner
        for _, _, (x, y) in lay1:                     # ring must not touch a half
            assert math.hypot(ringpos[0] - x, ringpos[1] - y) > o + rr + 2, (D, "ring overlaps")
        lay1.append(("ring", tr, ringpos))
        plates = [lay1] if both else [lay1, [("half_back", tf, (BED / 2, BED / 2))]]
        for pi, lay in enumerate(plates, 1):
            sc = trimesh.Scene()
            for name, m, (x, y) in lay:
                sc.add_geometry(m.copy().apply_translation([x - BED / 2, y - BED / 2, 0]), node_name=name)
            b = sc.bounds
            assert (b[1] - b[0])[:2].max() <= BED, (D, b)
            suffix = "" if len(plates) == 1 else f"_{pi}of{len(plates)}"
            sc.export(os.path.join(out, f"hoop_{D}mm_relief_plate{suffix}.3mf"))
        span = len(plates)
        print(f"{D}mm: outer {2*o:.1f}, total thickness rim {2*RIM_T} / plate {2*PLATE_T}, "
              f"half vol {tf.volume/1000:.1f} cm3, faces {len(tf.faces)}, A1 plates {span}")
