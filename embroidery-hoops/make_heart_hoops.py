"""
Heart-shaped embroidery hoop - same family as the flower hoop (make_hoops_v2.py):
  * two parts: one-piece frame + heart-shaped inner ring that clicks in (bead + groove)
  * scalloped heart outline, hanging hole in the top scallop
  * styles: "bedside" = decorated on both faces, no supports (raised front; raised motifs on the bed face
            with the background recessed), "single" = decorated front, plain flat back
  * sizes = width of the fabric opening (60 / 80 / 100 mm)

How the heart is built without slicer-hostile steps:
  the rim, the ring, the groove and the entry chamfer are SWEEPS of a 2D (offset, z) profile along a
  smooth heart curve (normal offsets), the scalloped plate is one loft of scaled copies of its outline.
"""
import math, os
import numpy as np
from manifold3d import Manifold, CrossSection, Mesh
from shapely.geometry import Point, Polygon, LineString, LinearRing
from shapely.geometry.polygon import orient
from shapely.affinity import scale as sscale, translate as stranslate, rotate as srotate
from shapely.ops import unary_union, polylabel
import trimesh
from make_hoops_v2 import loft, fillet_pts, to_cs, to_tm, mini_flower, leaf_pair

SIZES        = [60, 80, 100]
RING_WALL    = 3.5
FABRIC_GAP   = 0.55
BEAD, GROOVE = 0.5, 0.8
RIM_WIDTH    = 5.0
H            = 9.0
PLATE_T      = 4.0
FILLET       = 1.2
TEX_H        = 0.4
BACK_DEPTH   = 0.6
BACK_BEVEL   = 0.8
MAX_BRIDGE   = 8.0
RING_CHAMF   = 0.6
HANG_HOLE_D  = 4.0
SCALLOP_STEP = 25.7     # mm between scallop centres (same rhythm as the 12-petal flower at 60 mm)
DIP_R        = 9.0      # rounding of the heart's top dip (must exceed the largest outward sweep offset)
TIP_R        = 6.0      # rounding of the bottom tip (must exceed the ring wall)
N            = 540      # samples along the heart curve
ARC          = 8

# ---------------------------------------------------------------- heart curve
def resample(ring_xy, n, start_top=True):
    """Uniform arc-length resampling of a closed CCW curve, starting at the top centre."""
    pts = np.asarray(ring_xy)
    if np.allclose(pts[0], pts[-1]): pts = pts[:-1]
    if start_top:
        upper = np.where(pts[:, 1] > pts[:, 1].mean())[0]
        k = upper[np.argmin(np.abs(pts[upper, 0]))]
        pts = np.roll(pts, -k, axis=0)
    seg = np.linalg.norm(np.diff(np.vstack([pts, pts[:1]]), axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    L = s[-1]
    t = np.linspace(0, L, n, endpoint=False)
    closed = np.vstack([pts, pts[:1]])
    x = np.interp(t, s, closed[:, 0]); y = np.interp(t, s, closed[:, 1])
    out = np.c_[x, y]
    out[:, 0] -= out[0, 0]                    # exact symmetry axis through the first sample (top centre)
    return out, L

def normals(P):
    d = np.roll(P, -1, axis=0) - np.roll(P, 1, axis=0)
    Nn = np.c_[d[:, 1], -d[:, 0]]             # outward for a CCW curve
    Nn /= np.linalg.norm(Nn, axis=1)[:, None]
    for _ in range(3):                        # light smoothing
        Nn = (np.roll(Nn, 1, 0) + 2 * Nn + np.roll(Nn, -1, 0)); Nn /= np.linalg.norm(Nn, axis=1)[:, None]
    return Nn

def heart_curve(width):
    """Smooth heart, outer width = width, centred on its bounding box, CCW, resampled from the top centre."""
    t = np.linspace(0, 2 * math.pi, 4000, endpoint=False)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    p = Polygon(np.c_[x, y]).buffer(0)
    for _ in range(2):                        # scale, round dip + tip, rescale to the exact width
        minx, miny, maxx, maxy = p.bounds
        p = sscale(p, width / (maxx - minx), width / (maxx - minx), origin=(0, 0))
        p = p.buffer(DIP_R, 64).buffer(-DIP_R, 64)        # closing: rounds the concave dip
        p = p.buffer(-TIP_R, 64).buffer(TIP_R, 64)        # opening: rounds the bottom tip
    minx, miny, maxx, maxy = p.bounds
    p = stranslate(p, -(minx + maxx) / 2, -(miny + maxy) / 2)
    p = orient(p, 1.0)
    P, L = resample(p.exterior.coords, N)
    return Polygon(P), P, normals(P), L

# ---------------------------------------------------------------- sweep along the heart
def sweep(P, Nn, prof):
    """Closed tube: 2D profile [(offset d, z), ...] (CCW in the d-z plane) swept along curve P with normals Nn."""
    n, m = len(P), len(prof)
    V = np.zeros((n * m, 3))
    for j, (d, z) in enumerate(prof):
        V[j::m, :2] = P + d * Nn
        V[j::m, 2] = z
    F = []
    for i in range(n):
        i2 = (i + 1) % n
        for j in range(m):
            j2 = (j + 1) % m
            a, b, c, d = i * m + j, i2 * m + j, i2 * m + j2, i * m + j2
            F += [(a, b, c), (a, c, d)]
    F = np.asarray(F)
    tri = V[F]
    vol = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6
    if vol < 0: F = F[:, ::-1]
    man = Manifold(Mesh(vert_properties=V.astype(np.float32), tri_verts=F.astype(np.uint32)))
    assert man.status().name == "NoError", man.status()
    return man

def offset_curve(P, Nn, d):
    return Polygon(P + d * Nn)

# ---------------------------------------------------------------- star-shaped outline sampling (for the plate loft)
def ray_outline(poly, center, n=900):
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    R = 1000.0
    pts = []
    for a in th:
        ray = LineString([center, (center[0] + R * math.cos(a), center[1] + R * math.sin(a))])
        hit = ray.intersection(poly.exterior)
        geoms = getattr(hit, "geoms", [hit])
        far = max(geoms, key=lambda g: Point(center).distance(g))
        pts.append((far.x, far.y) if far.geom_type == "Point" else far.coords[-1])
    out = np.asarray(pts) - np.asarray(center)
    assert abs(Polygon(out + center).area - poly.area) / poly.area < 0.01, "outline is not star-shaped"
    return out

# ---------------------------------------------------------------- frame
def frame(D, style):
    W = D + 2 * RING_WALL                          # base curve = ring outer surface
    base, P, Nn, L = heart_curve(W)
    G = FABRIC_GAP
    d_rim = G + RIM_WIDTH                          # rim outer offset
    d_sc = d_rim + 5.0                             # scallop centre offset
    f = FILLET

    # scallop centres along the offset curve, symmetric, one at the top centre
    sc_poly = base.buffer(d_sc, 64)
    S, Ls = resample(orient(sc_poly, 1.0).exterior.coords, 2000)
    SN = normals(S)
    n_sc = max(10, int(round(Ls / SCALLOP_STEP / 2)) * 2)
    idx = (np.arange(n_sc) * len(S) / n_sc).astype(int)
    rp = 0.55 * Ls / n_sc
    scal = unary_union([sc_poly] + [Point(*S[i]).buffer(rp, 64) for i in idx])
    center = (0.0, (scal.bounds[1] + scal.bounds[3]) / 2 - 0.08 * (scal.bounds[3] - scal.bounds[1]))
    out = ray_outline(scal, center)
    Rtip = np.linalg.norm(out, axis=1).max()

    # plate loft (shifted so the loft centre is the origin, then moved back)
    z1 = PLATE_T
    top = [(z1 - f + dz, 1 - ins / Rtip) for dz, ins in fillet_pts(f)]
    rings = [(0.0, 1.0)] + top if style == "single" else [(0.0, 1 - BACK_BEVEL / Rtip), (BACK_BEVEL, 1.0)] + top
    plate = loft(out, rings).translate([center[0], center[1], 0])

    # rim (sweep with rounded top edges)
    prof = [(G, 0.0), (d_rim, 0.0)]
    for a in np.linspace(0, math.pi / 2, ARC + 1):
        prof.append((d_rim - f + f * math.cos(a), H - f + f * math.sin(a)))
    for a in np.linspace(math.pi / 2, math.pi, ARC + 1)[1:]:
        prof.append((G + f + f * math.cos(a), H - f + f * math.sin(a)))
    rim = sweep(P, Nn, prof)

    body = plate + rim
    bore = offset_curve(P, Nn, G)
    body = body - Manifold.extrude(to_cs(bore), H + 2).translate([0, 0, -1])
    hole_c = S[idx[0]]
    body = body - Manifold.cylinder(H + 2, HANG_HOLE_D / 2, HANG_HOLE_D / 2, 32).translate([hole_c[0], hole_c[1], -1])
    m = H / 2
    body = body - sweep(P, Nn, [(G - 0.2, m - GROOVE - 0.5), (G + GROOVE, m - 0.3), (G + GROOVE, m + 0.3), (G - 0.2, m + GROOVE + 0.5)])
    if style == "bedside":
        c = RING_CHAMF
        body = body - sweep(P, Nn, [(G - 0.2, -0.5), (G + c + 0.5, -0.5), (G - 0.2, c + 0.2)])

    # ---- decoration ----
    hole = Point(*hole_c).buffer(HANG_HOLE_D / 2 + 1.2, 24)
    plate_face = scal.buffer(-(f + 0.9)).difference(base.buffer(d_rim + 0.9, 64)).difference(hole)
    e = f + 0.4
    rim_face = base.buffer(d_rim - e, 64).difference(offset_curve(P, Nn, G + e))

    def motifs():
        shapes = []
        for k, i in enumerate(idx):
            if k == 0: continue                                    # hanging-hole scallop
            a = math.atan2(SN[i, 1], SN[i, 0])
            cx, cy = S[i] + 0.30 * rp * SN[i]
            shapes.append(mini_flower(cx, cy, 1.05 * rp, a))
        for k in range(n_sc):                                      # leaf pairs between scallops
            i = (idx[k] + len(S) // (2 * n_sc)) % len(S)
            q = S[i] - SN[i] * (d_sc - d_rim - 1.6)
            a = math.atan2(SN[i, 1], SN[i, 0])
            shapes.append(leaf_pair(q[0], q[1], 0.75 * rp, a))
        plate_m = unary_union(shapes).intersection(plate_face)
        dm = G + RIM_WIDTH / 2
        n_w = int(round(L / 12.0))
        s_ = np.linspace(0, 2 * math.pi * n_w, len(P), endpoint=False)
        wave = LinearRing(P + (dm + 0.9 * np.sin(s_))[:, None] * Nn).buffer(0.5, 4)
        rim_m = wave.intersection(rim_face)
        clean = lambda g: unary_union([x for x in getattr(g, "geoms", [g]) if x.area > 1.0]).simplify(0.03)
        return clean(plate_m), clean(rim_m)

    pf, rf = motifs()
    body = body + Manifold.extrude(to_cs(pf), TEX_H + 0.05).translate([0, 0, z1 - 0.05])
    body = body + Manifold.extrude(to_cs(rf), TEX_H + 0.05).translate([0, 0, H - 0.05])
    if style == "bedside":
        back_rim_face = base.buffer(d_rim - e, 64).difference(offset_curve(P, Nn, G + RING_CHAMF + e))
        bg = unary_union([plate_face.difference(pf), back_rim_face.difference(rf)])
        for _ in range(200):                                       # anchor dots: keep every bridge short
            worst, at = 0.0, None
            for g in getattr(bg, "geoms", [bg]):
                if g.area < 1.0: continue
                pt = polylabel(g, 0.05)
                dd = min([g.exterior.distance(pt)] + [h.distance(pt) for h in g.interiors])
                if dd > worst: worst, at = dd, pt
            if at is None or 2 * worst <= MAX_BRIDGE: break
            for k in (1, -1):
                bg = bg.difference(Point(k * at.x, at.y).buffer(1.0, 12))
        bg = bg.buffer(-0.05, 4).buffer(0.05, 4)
        bg = unary_union([g for g in getattr(bg, "geoms", [bg]) if g.area > 1.0])
        body = body - Manifold.extrude(to_cs(bg), BACK_DEPTH + 0.5).translate([0, 0, -0.5])
        frame.back_background = bg
    frame.footprint = scal
    return body

def ring(D):
    W = D + 2 * RING_WALL
    base, P, Nn, L = heart_curve(W)
    c, m, b = RING_CHAMF, H / 2, BEAD
    prof = [(-RING_WALL, 0), (-c, 0), (0, c), (0, m - 2 * b), (b, m - b), (b, m + b), (0, m + 2 * b),
            (0, H - c), (-c, H), (-RING_WALL, H)]
    ring.footprint = offset_curve(P, Nn, b)
    return sweep(P, Nn, prof)

# ---------------------------------------------------------------- build
def place_on_bed(fp_frame, fp_ring, BED=256.0, M=3.0):
    """Frame in one corner, ring in the opposite corner (optionally rotated 180 deg); None if it does not fit."""
    fb = fp_frame.bounds
    fdx, fdy = M - fb[0], M - fb[1]
    F = stranslate(fp_frame, fdx, fdy)
    for rot in (0, 180):
        Rg = srotate(fp_ring, rot, origin=(0, 0))
        rb = Rg.bounds
        rdx, rdy = BED - M - rb[2], BED - M - rb[3]
        Rp = stranslate(Rg, rdx, rdy)
        if F.bounds[2] <= BED - M and F.bounds[3] <= BED - M and F.buffer(2).disjoint(Rp):
            return (fdx, fdy), (rdx, rdy, rot)
    return None

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl"); os.makedirs(out, exist_ok=True)
    for style, tag in (("bedside", "2side"), ("single", "1side")):
        for D in SIZES:
            fm = frame(D, style)
            assert fm.status().name == "NoError" and len(fm.decompose()) == 1, "frame must be one clean solid"
            rm = ring(D)
            tf, tr = to_tm(fm), to_tm(rm)
            assert tf.is_watertight and tr.is_watertight
            tf.export(os.path.join(out, f"heart_{D}mm_{tag}_frame.stl"))
            tr.export(os.path.join(out, f"heart_{D}mm_{tag}_ring.stl"))
            plan = place_on_bed(frame.footprint, ring.footprint)
            plates = []
            if plan:
                (fdx, fdy), (rdx, rdy, rot) = plan
                rr = tr.copy(); rr.apply_transform(trimesh.transformations.rotation_matrix(math.radians(rot), [0, 0, 1]))
                plates.append([("frame", tf.copy().apply_translation([fdx - 128, fdy - 128, 0])),
                               ("ring", rr.apply_translation([rdx - 128, rdy - 128, 0]))])
            else:
                plates.append([("frame", tf.copy().apply_translation(-np.r_[tf.bounds.mean(0)[:2], 0]))])
                plates.append([("ring", tr.copy().apply_translation(-np.r_[tr.bounds.mean(0)[:2], 0]))])
            for k, items in enumerate(plates, 1):
                sc = trimesh.Scene()
                for name, mesh in items: sc.add_geometry(mesh, node_name=name)
                b = sc.bounds; assert (b[1] - b[0])[:2].max() <= 256
                suf = "" if len(plates) == 1 else f"_{k}of{len(plates)}"
                sc.export(os.path.join(out, f"heart_{D}mm_{tag}_plate{suf}.3mf"))
            ext = tf.bounds[1] - tf.bounds[0]
            print(f"{style:7s} {D:3d}mm frame {ext[0]:.1f} x {ext[1]:.1f} mm, faces {len(tf.faces)}, plates {len(plates)}")
