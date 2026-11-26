"""
Puffy (domed) heart frame with the round flower-hoop ring in the middle.

The front of the heart is a smooth cushion: thin at the outer edge, rising toward the inside like a
heart you hold in your hand. Optional soft ripples follow the heart outline. The back is flat on the bed,
so it prints without supports (use adaptive / variable layer height in Bambu Studio for a smooth dome).

Built as: heart region (minus the opening) extruded tall  INTERSECT  a height-field solid z = f(x, y),
then the round rim / bore / snap groove of the flower hoop are added.
"""
import math, os
import numpy as np
import shapely
from manifold3d import Manifold, CrossSection, Mesh
from shapely.geometry import Point
from shapely.ops import unary_union
import trimesh
import make_hoops_v2 as v2
from make_hoops_v2 import to_cs, to_tm
from make_heart_round import heart_around
from make_heart_hoops import centre_line_y

SIZES     = [60, 80, 100]
MARGIN    = 10.0     # narrowest border between rim and heart edge
Z_EDGE    = 1.6      # thickness at the outer edge
Z_PEAK    = 14.0     # cushion height in the lobes / point (puffiness)
EDGE_W    = 16.0     # width of the rounded outer shoulder (quarter-ellipse)
Z_RIMJOIN = 7.2      # cushion height where it meets the round rim (rim top = 9 mm)
INNER_W   = 14.0     # width of the rounded slope up from the rim
SOFT_K    = 1.6      # softness of the blend between the outer shoulder and the inner slope
RIPPLE_A  = 0.45     # ripple amplitude (mm), 0 = smooth
RIPPLE_L  = 6.5      # ripple spacing (mm)
GRID      = 1.25     # height-field resolution (mm)
DECO_H    = 0.6      # front flowers stand this much above the dome
RIPPLES   = False    # option B (soft ripples) - the chosen design is A (smooth)
MOTIF     = "hearts" # decoration: "hearts" or "flowers"
H, SEG, ARC, FILLET = v2.H, v2.SEG, v2.ARC, v2.FILLET

_UNIT_HEART = None
def heart_motif(cx, cy, size, ang):
    """Small classic heart that fits the same circle as mini_flower (radius ~0.6*size), tilted by (ang - 90 deg)."""
    global _UNIT_HEART
    from shapely.affinity import scale as sscale, rotate as srotate, translate as stranslate
    if _UNIT_HEART is None:
        from make_heart_round import classic_heart
        hh = classic_heart(10.0)                                   # lobe radius 10 -> ~35 x 33 units
        minx, miny, maxx, maxy = hh.bounds
        hh = stranslate(hh, -(minx + maxx) / 2, -(miny + maxy) / 2)
        _UNIT_HEART = sscale(hh, 1 / max(maxx - minx, maxy - miny), 1 / max(maxx - minx, maxy - miny), origin=(0, 0))
    d = 1.15 * size                                                # heart width ~ the flower's diameter
    m = sscale(_UNIT_HEART, d, d, origin=(0, 0))
    m = srotate(m, math.degrees(ang) - 90.0, origin=(0, 0))
    return stranslate(m, cx, cy).simplify(0.03)

def height(t, ripples, u=None):
    """t = distance inside the heart edge, u = distance outside the rim (mm)."""
    q = np.clip(t / EDGE_W, 0, 1)
    z = Z_EDGE + (Z_PEAK - Z_EDGE) * np.sqrt(1 - (1 - q) ** 2)            # rounded outer shoulder
    if u is not None:
        w = np.clip(u / INNER_W, 0, 1)
        zi = Z_RIMJOIN + (Z_PEAK - Z_RIMJOIN) * np.sqrt(1 - (1 - w) ** 2)  # rounded slope up from the rim
        z = -SOFT_K * np.logaddexp(-z / SOFT_K, -zi / SOFT_K)               # smooth minimum
        z = np.maximum(z, Z_EDGE)
    if ripples:
        fade = np.clip((t - 3.0) / 4.0, 0, 1)                    # keep the outer edge clean
        z = z + RIPPLE_A * fade * np.sin(2 * math.pi * t / RIPPLE_L)
    return z

def heightfield_solid(heart, ripples, lift=0.0):
    minx, miny, maxx, maxy = heart.bounds
    xs = np.arange(minx - 2, maxx + 2 + GRID, GRID)
    ys = np.arange(miny - 2, maxy + 2 + GRID, GRID)
    X, Y = np.meshgrid(xs, ys)
    pts = shapely.points(X.ravel(), Y.ravel())
    t = shapely.distance(heart.exterior, pts) * np.where(shapely.contains(heart, pts), 1, -1)
    u = np.hypot(X, Y) - heightfield_solid.r_rim
    Z = height(t.reshape(X.shape), ripples, u) + lift
    ny, nx = Z.shape
    top = np.c_[X.ravel(), Y.ravel(), Z.ravel()]
    bot = np.c_[X.ravel(), Y.ravel(), np.full(X.size, -1.0)]
    V = np.vstack([top, bot])
    idx = np.arange(nx * ny).reshape(ny, nx)
    a, b, c, d = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()
    off = nx * ny
    F = [np.c_[a, b, c], np.c_[a, c, d],                          # top (up)
         np.c_[a + off, c + off, b + off], np.c_[a + off, d + off, c + off]]   # bottom (down)
    def wall(edge, flip):
        e0, e1 = edge[:-1], edge[1:]
        q = [np.c_[e0, e1, e1 + off], np.c_[e0, e1 + off, e0 + off]]
        return [x[:, ::-1] for x in q] if flip else q
    F += wall(idx[0, :], False) + wall(idx[-1, :], True) + wall(idx[:, 0], True) + wall(idx[:, -1], False)
    F = np.concatenate(F)
    tm = trimesh.Trimesh(V, F, process=False)
    trimesh.repair.fix_winding(tm); trimesh.repair.fix_inversion(tm)
    m = Manifold(Mesh(vert_properties=np.asarray(tm.vertices, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))
    assert m.status().name == "NoError", m.status()
    return m

def frame(D, style="bedside", ripples=RIPPLES):
    """style: "bedside" = decorated front + raised decoration on the bed face (no supports),
              "single"  = decorated front, plain flat back."""
    from make_heart_round import flower_fill
    from make_heart_hoops import ray_outline
    from make_hoops_v2 import loft, mini_flower, wave_band
    motif = heart_motif if MOTIF == "hearts" else mini_flower
    from shapely.ops import polylabel
    Ri = (D + 2 * v2.RING_WALL) / 2 + v2.FABRIC_GAP
    Ro = Ri + v2.RIM_WIDTH
    f, c = FILLET, v2.RING_CHAMF
    heart, rl = heart_around(Ro + MARGIN)
    heightfield_solid.r_rim = Ro
    out = ray_outline(heart, (0.0, 0.0))
    Rtip = np.linalg.norm(out, axis=1).max()
    bev = v2.BACK_BEVEL if style == "bedside" else 0.0
    outer = loft(out, [(0.0, 1 - bev / Rtip), (max(bev, 0.01), 1.0), (20.0, 1.0)])
    dome = heightfield_solid(heart, ripples)
    plate = outer ^ dome
    prof = [(Ri, 0.0), (Ro, 0.0)]
    for a in np.linspace(0, math.pi / 2, ARC + 1):
        prof.append((Ro - f + f * math.cos(a), H - f + f * math.sin(a)))
    for a in np.linspace(math.pi / 2, math.pi, ARC + 1)[1:]:
        prof.append((Ri + f + f * math.cos(a), H - f + f * math.sin(a)))
    body = plate + Manifold.revolve(CrossSection([prof]), SEG)

    # ---- front decoration: flowers that follow the dome, wavy line on the rim ----
    y_dip, _ = centre_line_y(heart)
    hole_c = (0.0, (Ro + y_dip) / 2)
    hole = Point(*hole_c).buffer(v2.HANG_HOLE_D / 2 + 1.4, 24)
    front_face = heart.buffer(-5.0).difference(Point(0, 0).buffer(Ro + 3.0, 256)).difference(hole)
    flowers = flower_fill(front_face.buffer(-0.3), min_r=3.0, max_size=0.42 * rl)
    clean = lambda gg: unary_union([x for x in getattr(gg, "geoms", [gg]) if x.area > 1.0]).simplify(0.03)
    pf = clean(unary_union([motif(x, y, sz, a) for x, y, sz, a in flowers]).intersection(front_face))
    body = body + (Manifold.extrude(to_cs(pf), 20.0) ^ heightfield_solid(heart, ripples, lift=DECO_H))
    e = f + 0.4
    rim_face = Point(0, 0).buffer(Ro - e, 256).difference(Point(0, 0).buffer(Ri + e, 256))
    rf = clean(wave_band((Ri + Ro) / 2, 0.9, 24, 1.0).intersection(rim_face))
    body = body + Manifold.extrude(to_cs(rf), v2.TEX_H + 0.05).translate([0, 0, H - 0.05])

    # ---- bore, hanging hole, snap groove ----
    body = body - Manifold.cylinder(H + 2, Ri, Ri, SEG).translate([0, 0, -1])
    body = body - Manifold.cylinder(H + 30, v2.HANG_HOLE_D / 2, v2.HANG_HOLE_D / 2, 32).translate([hole_c[0], hole_c[1], -1])
    if style == "bedside":
        body = body - Manifold.cylinder(c + 0.01, Ri + c, Ri - 0.01, SEG).translate([0, 0, -0.01])
    m, G = H / 2, v2.GROOVE
    g = [(Ri - 0.2, m - G - 0.5), (Ri + G, m - 0.3), (Ri + G, m + 0.3), (Ri - 0.2, m + G + 0.5)]
    body = body - Manifold.revolve(CrossSection([g]), SEG)

    # ---- bed side: the same flowers raised, background recessed (bridged, no supports) ----
    if style == "bedside":
        back_face = heart.buffer(-(bev + 1.3)).difference(Point(0, 0).buffer(Ro + 0.9, 256)).difference(hole)
        pb = clean(unary_union([motif(x, y, sz, a) for x, y, sz, a in flowers]).intersection(back_face))
        back_rim = Point(0, 0).buffer(Ro - e, 256).difference(Point(0, 0).buffer(Ri + c + e, 256))
        rb = clean(wave_band((Ri + c + Ro) / 2, 0.9, 24, 1.0).intersection(back_rim))
        bg = unary_union([back_face.difference(pb), back_rim.difference(rb)])
        for _ in range(300):
            worst, at = 0.0, None
            for gg in getattr(bg, "geoms", [bg]):
                if gg.area < 1.0: continue
                pt = polylabel(gg, 0.05)
                dd = min([gg.exterior.distance(pt)] + [hh.distance(pt) for hh in gg.interiors])
                if dd > worst: worst, at = dd, pt
            if at is None or 2 * worst <= v2.MAX_BRIDGE: break
            for k in (1, -1):
                bg = bg.difference(Point(k * at.x, at.y).buffer(1.0, 12))
        bg = bg.buffer(-0.05, 4).buffer(0.05, 4)
        bg = unary_union([gg for gg in getattr(bg, "geoms", [bg]) if gg.area > 1.0])
        body = body - Manifold.extrude(to_cs(bg), v2.BACK_DEPTH + 0.5).translate([0, 0, -0.5])
        frame.back_background = bg
    frame.heart, frame.flowers = heart, flowers
    return body

if __name__ == "__main__":
    import sys
    from make_heart_round import place_on_bed
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl"); os.makedirs(out, exist_ok=True)
    sizes = [int(a) for a in sys.argv[1:]] or SIZES
    for style, tag in (("bedside", "2side"), ("single", "1side")):
        for D in sizes:
            fm = frame(D, style)
            assert fm.status().name == "NoError" and len(fm.decompose()) == 1, "frame must be one clean solid"
            tf, tr = to_tm(fm), to_tm(v2.ring(D))
            assert tf.is_watertight and tr.is_watertight
            tf.export(os.path.join(out, f"heartp_{D}mm_{tag}_frame.stl"))
            tr.export(os.path.join(out, f"heartp_{D}mm_{tag}_ring.stl"))
            plan = place_on_bed(frame.heart, D / 2 + v2.RING_WALL + v2.BEAD)
            plates = []
            if plan:
                (fdx, fdy), (rx, ry) = plan
                plates.append([("frame", tf.copy().apply_translation([fdx - 128, fdy - 128, 0])),
                               ("ring", tr.copy().apply_translation([rx - 128, ry - 128, 0]))])
            else:
                plates.append([("frame", tf.copy().apply_translation(-np.r_[tf.bounds.mean(0)[:2], 0]))])
                plates.append([("ring", tr.copy())])
            for k, items in enumerate(plates, 1):
                sc = trimesh.Scene()
                for name, mesh in items: sc.add_geometry(mesh, node_name=name)
                b = sc.bounds; assert (b[1] - b[0])[:2].max() <= 256, b
                suf = "" if len(plates) == 1 else f"_{k}of{len(plates)}"
                sc.export(os.path.join(out, f"heartp_{D}mm_{tag}_plate{suf}.3mf"))
            e = tf.bounds[1] - tf.bounds[0]
            print(f"{style:7s} {D:3d}mm {e[0]:.0f} x {e[1]:.0f} x {e[2]:.1f} mm, flowers {len(frame.flowers)}, faces {len(tf.faces)}, plates {len(plates)}")
