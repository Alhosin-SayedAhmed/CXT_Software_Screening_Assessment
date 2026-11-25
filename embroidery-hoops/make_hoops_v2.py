"""
Two-part scalloped embroidery hoop - v2 (slicer-friendly geometry).

Why v2: v1 built the rounded edges from 0.2 mm stacked steps; with the leaf texture on top
that created hundreds of tiny top surfaces and Bambu Studio could hang at
"Generating infill regions". v2 builds every rounded edge as ONE smooth surface:
  * the round rim is a revolved profile with true arcs,
  * the flower plate is a single loft of scaled copies of its outline (it is star-shaped),
  * the leaf texture is simplified (fewer, cleaner polygons).

Styles (all two parts: frame + snap-in ring):
  bedside: decorated on BOTH faces, NO supports: raised rim + raised decoration on the front,
           flat bed face with the same decoration engraved 0.6 mm and a 45 deg bevelled edge
  single : decorated front, plain flat back (no supports)
  double : (old) rim raised on both faces, needs small supports under the petals
"""
import math, os, random
import numpy as np
from manifold3d import Manifold, CrossSection, Mesh, triangulate
from shapely.geometry import Point
from shapely.geometry.polygon import orient
from shapely.affinity import rotate, translate, scale
from shapely.ops import unary_union
import trimesh

SIZES       = [60, 80, 100]
PETALS      = 12
RING_WALL   = 3.5
FABRIC_GAP  = 0.35     # radial room for the fabric at the seated position
TAPER       = 0.6      # ring + bore narrow by this (radial) toward the back -> pushing harder clamps tighter
LIP_W       = 1.5      # back lip (on the bed): ring cannot pass out of the back (45 deg seat)
LIP_T       = 1.2      # lip thickness above the seat
RIM_WIDTH   = 5.0
H           = 9.0      # rim height = ring height
PLATE_T     = 4.0      # petal thickness
FILLET      = 1.2
BED_CHAMFER = 0.8
TEX_H       = 0.4      # raised decoration height (front)
BACK_DEPTH  = 0.6      # bed side: background recessed by this -> decoration stands out 0.6 mm (style "bedside")
MAX_BRIDGE  = 8.0      # longest allowed bridge over the recessed background on the bed face (mm)
BACK_BEVEL  = 0.8      # 45 deg bevel on the bed-side petal edge (no support needed)
TEXTURE     = "motifs" # "motifs" = few large shapes (slicer-friendly), "leaves" = dense leaves, None = smooth
HANG_HOLE_D = 4.0
RING_CHAMF  = 0.6
Z_SEAT      = H - LIP_T - LIP_W   # where the tapered bore meets the 45 deg lip seat
RING_H      = H - LIP_T           # ring height: flush with the FRONT when seated (white ring visible at the front)
SEG         = 360      # circle resolution
ARC         = 8        # segments per rounded edge

def to_cs(geom):
    polys = []
    for g in getattr(geom, "geoms", [geom]):
        if g.is_empty: continue
        g = orient(g, 1.0)
        polys.append(np.asarray(g.exterior.coords[:-1], dtype=np.float64))
        for h in g.interiors:
            polys.append(np.asarray(h.coords[:-1], dtype=np.float64))
    return CrossSection(polys)

def flower_outline(Rc, rp, n=720):
    """Star-shaped flower outline sampled on n rays (radius = max of base circle and petals)."""
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    r = np.full(n, Rc)
    for i in range(PETALS):
        a = 2 * math.pi * i / PETALS + math.pi / 2
        cx, cy = Rc * math.cos(a), Rc * math.sin(a)
        # ray/circle intersection: |t*u - c| = rp  -> t = u.c + sqrt((u.c)^2 - |c|^2 + rp^2)
        uc = np.cos(th) * cx + np.sin(th) * cy
        disc = uc ** 2 - (cx * cx + cy * cy) + rp * rp
        ok = disc >= 0
        r[ok] = np.maximum(r[ok], uc[ok] + np.sqrt(disc[ok]))
    return np.stack([r * np.cos(th), r * np.sin(th)], 1)

def loft(outline, rings):
    """Solid from scaled copies of a star-shaped outline. rings = [(z, scale), ...] bottom->top."""
    n, k = len(outline), len(rings)
    verts = np.concatenate([np.c_[outline * s, np.full(n, z)] for z, s in rings])
    faces = []
    idx = np.arange(n)
    for j in range(k - 1):
        a, b = j * n + idx, j * n + (idx + 1) % n
        c, d = (j + 1) * n + (idx + 1) % n, (j + 1) * n + idx
        faces += [np.c_[a, b, c], np.c_[a, c, d]]
    cap = np.asarray(triangulate([outline]))          # CCW triangles of the outline
    faces += [cap[:, ::-1], cap + (k - 1) * n]         # bottom (flipped) + top
    m = Manifold(Mesh(vert_properties=verts.astype(np.float32), tri_verts=np.concatenate(faces).astype(np.uint32)))
    assert m.status().name == "NoError", m.status()
    return m

def fillet_pts(f, n=ARC):
    """(dz, inset) along a quarter arc, from the flat side to the top."""
    return [(f * math.sin(a), f - f * math.cos(a)) for a in np.linspace(0, math.pi / 2, n + 1)]

def leaf_pattern(region, seed):
    rnd = random.Random(seed)
    minx, miny, maxx, maxy = region.bounds
    leaf = scale(Point(0, 0).buffer(1.0, 6), 2.4, 0.95)
    shapes, step, y, row = [], 4.8, miny, 0
    while y < maxy:
        x = minx + (step / 2 if row % 2 else 0)
        while x < maxx:
            px, py = x + rnd.uniform(-0.6, 0.6), y + rnd.uniform(-0.6, 0.6)
            if rnd.random() < 0.75:
                ang = math.degrees(math.atan2(py, px)) + 90 + rnd.uniform(-35, 35)
                shapes.append(translate(rotate(leaf, ang, origin=(0, 0)), px, py))
            else:
                shapes.append(Point(px, py).buffer(0.9, 3))
            x += step
        y += step * 0.87
        row += 1
    pat = unary_union(shapes).intersection(region)
    pat = pat.buffer(-0.4, 4).buffer(0.4, 4).simplify(0.1)          # drop slivers, keep it light
    return unary_union([g for g in getattr(pat, "geoms", [pat]) if g.area > 1.2])

def mini_flower(cx, cy, size, ang0):
    """5-petal flower, one connected island."""
    parts = [Point(cx, cy).buffer(0.22 * size, 12)]
    for k in range(5):
        a = ang0 + 2 * math.pi * k / 5
        pet = scale(Point(0, 0).buffer(1.0, 12), 0.30 * size, 0.15 * size)
        pet = rotate(pet, math.degrees(a), origin=(0, 0))
        parts.append(translate(pet, cx + 0.27 * size * math.cos(a), cy + 0.27 * size * math.sin(a)))
    return unary_union(parts)

def leaf_pair(cx, cy, size, ang):
    """Two leaves in a V joined at the stem, one island."""
    leaf = scale(Point(0, 0).buffer(1.0, 12), 0.5 * size, 0.18 * size)
    out = []
    for side in (-1, 1):
        a = ang + side * math.radians(32)
        l = rotate(leaf, math.degrees(a), origin=(0, 0))
        out.append(translate(l, cx + 0.42 * size * math.cos(a), cy + 0.42 * size * math.sin(a)))
    out.append(Point(cx, cy).buffer(0.12 * size, 8))
    return unary_union(out)

def wave_band(r, amp, waves, width, n=720):
    """Closed wavy line around the rim, one island."""
    from shapely.geometry import LinearRing
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    rr = r + amp * np.sin(waves * th)
    return LinearRing(np.c_[rr * np.cos(th), rr * np.sin(th)]).buffer(width / 2, 4)

def motif_pattern(Rc, rp, Ri, Ro, plate_face, rim_face):
    shapes = []
    for i in range(PETALS):
        a = 2 * math.pi * i / PETALS + math.pi / 2
        if i == 0:      # top petal carries the hanging hole
            continue
        rr = Rc + 0.30 * rp
        shapes.append(mini_flower(rr * math.cos(a), rr * math.sin(a), 1.05 * rp, a))
    for i in range(PETALS):   # leaf pairs in the valleys between petals, pointing outward
        a = 2 * math.pi * (i + 0.5) / PETALS + math.pi / 2
        rr = Ro + 1.6
        shapes.append(leaf_pair(rr * math.cos(a), rr * math.sin(a), 0.75 * rp, a))
    plate = unary_union(shapes).intersection(plate_face)
    rim = wave_band((Ri + Ro) / 2, 0.9, 24, 1.0).intersection(rim_face)
    clean = lambda g: unary_union([x for x in getattr(g, "geoms", [g]) if x.area > 1.0]).simplify(0.03)
    return clean(plate), clean(rim)

def frame(D, style):
    ro_b = D / 2 + RING_WALL                 # ring outer radius at its back (wide) end
    Rb = ro_b + FABRIC_GAP                   # bore radius at the back (entry)
    Rf = ro_b - TAPER + FABRIC_GAP           # bore radius at the lip seat
    Ri = Rf - LIP_W                          # lip inner radius (lip sits on the bed side)
    Ro = Rb + RIM_WIDTH
    Rc = Ro + 5.0
    rp = 2 * Rc * math.sin(math.pi / PETALS) * 0.55
    Rtip = Rc + rp
    outline = flower_outline(Rc, rp)
    f = FILLET

    # ---- flower plate (one smooth loft) ----
    z0, z1 = (0.0, PLATE_T) if style in ("single", "bedside") else ((H - PLATE_T) / 2, (H + PLATE_T) / 2)
    top = [(z1 - f + dz, 1 - ins / Rtip) for dz, ins in fillet_pts(f)]
    if style == "single":
        rings = [(z0, 1.0)] + top
    elif style == "bedside":
        rings = [(0.0, 1 - BACK_BEVEL / Rtip), (BACK_BEVEL, 1.0)] + top
    else:
        bot = [(z0 + f - dz, 1 - ins / Rtip) for dz, ins in fillet_pts(f)][::-1]
        rings = bot + top
    plate = loft(outline, rings)

    # ---- round rim (revolved profile with true arcs) ----
    prof = []
    if style == "single":
        prof += [(Ri, 0.0), (Ro, 0.0)]
    elif style == "bedside":
        prof += [(Ri, 0.0), (Ro, 0.0)]
    else:
        c = BED_CHAMFER
        prof += [(Ri + c, 0.0), (Ro - c, 0.0), (Ro, c)]
    for a in np.linspace(0, math.pi / 2, ARC + 1):                      # outer top arc
        prof.append((Ro - f + f * math.cos(a), H - f + f * math.sin(a)))
    for a in np.linspace(math.pi / 2, math.pi, ARC + 1)[1:]:            # inner top arc
        prof.append((Ri + f + f * math.cos(a), H - f + f * math.sin(a)))
    if style == "double":
        prof.append((Ri, BED_CHAMFER))
    rim = Manifold.revolve(CrossSection([prof]), SEG)

    body = plate + rim
    body = body - Manifold.cylinder(H + 2, Ri, Ri, SEG).translate([0, 0, -1])
    body = body - Manifold.cylinder(H + 2, HANG_HOLE_D / 2, HANG_HOLE_D / 2, 32).translate([0, Rc, -1])
    # ---- tapered bore + front lip seat (ring enters from the back only) ----
    c = RING_CHAMF
    Rb_c = Rb - TAPER * c / Z_SEAT
    space = [(Ri - 1, -1), (Rb_c + c, -1), (Rb_c + c, 0.0), (Rb_c, c), (Rf, Z_SEAT), (Ri, Z_SEAT + LIP_W), (Ri, H + 1), (Ri - 1, H + 1)]
    # ring enters from the FRONT (top) and seats on a lip at the BACK (bed side): mirror the bore in z
    space = [(r, H - z) for r, z in space][::-1]
    body = body - Manifold.revolve(CrossSection([space]), SEG)

    # ---- leaf texture on the flat faces ----
    from shapely.geometry import Polygon  # noqa: E402
    flat_flower = Polygon(outline).buffer(-(f + 0.9))
    hole = Point(0, Rc).buffer(HANG_HOLE_D / 2 + 1.2, 24)
    plate_face = flat_flower.difference(Point(0, 0).buffer(Ro + 0.9, 128)).difference(hole)
    e = max(f, BED_CHAMFER) + 0.4
    def tex(seed, r_in=Ri):
        # r_in = inner edge of the flat rim face (front: the lip; back: the bore entry)
        rim_face = Point(0, 0).buffer(Ro - e, 128).difference(Point(0, 0).buffer(r_in + e, 128))
        if TEXTURE == "motifs":
            return motif_pattern(Rc, rp, r_in, Ro, plate_face, rim_face)
        return leaf_pattern(plate_face, seed), leaf_pattern(rim_face, seed + 1)
    if TEXTURE:
        pf, rf = tex(D, r_in=Rb + RING_CHAMF)          # front rim face starts at the wide bore entry
        body = body + Manifold.extrude(to_cs(pf), TEX_H + 0.05).translate([0, 0, z1 - 0.05])
        body = body + Manifold.extrude(to_cs(rf), TEX_H + 0.05).translate([0, 0, H - 0.05])
        if style == "bedside":
            # RAISED decoration on the bed face without supports: the motifs and a border around the petals,
            # the rim and the bore stay on the bed; only the background between them is recessed, so the
            # printer just bridges short gaps between the raised shapes.
            pb, rb = tex(D + 7, r_in=Ri)                # back rim face starts at the lip
            back_rim_face = Point(0, 0).buffer(Ro - e, 128).difference(Point(0, 0).buffer(Ri + e, 128))
            bg = unary_union([plate_face.difference(pb), back_rim_face.difference(rb)])
            # add small raised dots where the background is widest, so no bridge is longer than MAX_BRIDGE
            from shapely.ops import polylabel
            for _ in range(200):
                worst, at = 0.0, None
                for g in getattr(bg, "geoms", [bg]):
                    if g.area < 1.0: continue
                    pt = polylabel(g, 0.05)
                    d = min([g.exterior.distance(pt)] + [h.distance(pt) for h in g.interiors])
                    if d > worst: worst, at = d, pt
                if at is None or 2 * worst <= MAX_BRIDGE: break
                for k in (1, -1):                       # keep the back symmetric left/right
                    bg = bg.difference(Point(k * at.x, at.y).buffer(1.0, 12))
            bg = bg.buffer(-0.05, 4).buffer(0.05, 4)
            bg = unary_union([g for g in getattr(bg, "geoms", [bg]) if g.area > 1.0])
            body = body - Manifold.extrude(to_cs(bg), BACK_DEPTH + 0.5).translate([0, 0, -0.5])
            frame.back_background = bg                  # kept for the bridge-span check
        if style == "double":                                           # same decoration, engraved on the back
            pb, rb = tex(D + 7)
            body = body - Manifold.extrude(to_cs(pb), TEX_H + 0.5).translate([0, 0, z0 - 0.5])
            body = body - Manifold.extrude(to_cs(rb), TEX_H + 0.5).translate([0, 0, -0.5])

    return body, 2 * Rtip

def ring(D):
    # tapered ring (printed wide end down): narrow 45 deg end goes in first from the front and seats on the back lip;
    # the wide end ends flush with the front of the frame
    ri, ro, c = D / 2, D / 2 + RING_WALL, RING_CHAMF
    prof = [(ri, 0), (ro - c, 0), (ro - TAPER * c / Z_SEAT, c), (ro - TAPER, Z_SEAT),
            (ro - TAPER - LIP_W, RING_H), (ri, RING_H)]
    return Manifold.revolve(CrossSection([prof]), SEG)

def to_tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)

if __name__ == "__main__":
    import sys
    if "--smooth" in sys.argv: TEXTURE = None
    suffix = "_smooth" if TEXTURE is None else ""
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl"); os.makedirs(out, exist_ok=True)
    BED, M = 256.0, 3.0
    for style, tag in (("bedside", "2side"), ("single", "1side")):
        for D in SIZES:
            f, outer = frame(D, style)
            assert f.status().name == "NoError" and len(f.decompose()) == 1, "frame must be one clean solid"
            tf, tr = to_tm(f), to_tm(ring(D))
            assert tf.is_watertight and tr.is_watertight
            tf.export(os.path.join(out, f"hoop_{D}mm_{tag}{suffix}_frame.stl"))
            tr.export(os.path.join(out, f"hoop_{D}mm_{tag}{suffix}_ring.stl"))
            o, rr = outer / 2, D / 2 + RING_WALL + 0.5
            fp, rp_ = (o + M, o + M), (BED - rr - M, BED - rr - M)
            assert math.hypot(fp[0] - rp_[0], fp[1] - rp_[1]) > o + rr + 2
            sc = trimesh.Scene()
            sc.add_geometry(tf.copy().apply_translation([fp[0] - BED / 2, fp[1] - BED / 2, 0]), node_name="frame")
            sc.add_geometry(tr.copy().apply_translation([rp_[0] - BED / 2, rp_[1] - BED / 2, 0]), node_name="ring")
            sc.export(os.path.join(out, f"hoop_{D}mm_{tag}{suffix}_plate.3mf"))
            print(f"{style:6s} {D:3d}mm outer {outer:.1f}  faces {len(tf.faces):6d}  z {tf.bounds[0][2]:.2f}..{tf.bounds[1][2]:.2f}")
