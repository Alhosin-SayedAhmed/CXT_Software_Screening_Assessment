"""
Heart-shaped frame with a ROUND opening ("locket" heart) - same round snap ring as the flower hoop.

  * outer outline: classic heart from two overlapping round lobes + two straight flanks to a point,
    with a crisp dip and a lightly rounded tip
  * centre: the flower hoop's round rim, bore, snap groove and ring (ring STL is identical to the flower's)
  * styles: "bedside" = decorated on both faces, no supports (raised front; raised bed side with the
            background recessed), "single" = decorated front, plain flat back
  * decoration: flowers placed where there is room (big ones in the lobes and the point, smaller ones
    down the sides), mirror-symmetric, + the wavy line on the rim
"""
import math, os
import numpy as np
from manifold3d import Manifold, CrossSection
from shapely.geometry import Point, Polygon, MultiPoint, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, polylabel
from shapely.affinity import translate as stranslate, rotate as srotate
import trimesh
import make_hoops_v2 as v2
from make_hoops_v2 import loft, fillet_pts, to_cs, to_tm, mini_flower, wave_band
from make_heart_hoops import ray_outline

SIZES       = [60, 80, 100]
LOBE_K      = 0.75     # lobe centres at +-K * lobe radius (overlap -> depth of the dip)
TIP_RATIO   = 2.3      # bottom point at TIP_RATIO * lobe radius below the lobe centres
MARGIN      = 8.0      # narrowest border between the rim and the heart edge
DIP_R, TIP_R = 2.0, 2.5
H, PLATE_T, FILLET = v2.H, v2.PLATE_T, v2.FILLET
TEX_H, BACK_DEPTH, BACK_BEVEL, MAX_BRIDGE = v2.TEX_H, v2.BACK_DEPTH, v2.BACK_BEVEL, v2.MAX_BRIDGE
RING_CHAMF, HANG_HOLE_D = v2.RING_CHAMF, v2.HANG_HOLE_D
ARC, SEG = v2.ARC, v2.SEG

def classic_heart(rl):
    cx = LOBE_K * rl
    L = Point(-cx, 0).buffer(rl, 256); R = Point(cx, 0).buffer(rl, 256)
    body = MultiPoint(list(L.exterior.coords) + list(R.exterior.coords) + [(0, -TIP_RATIO * rl)]).convex_hull
    yi = math.sqrt(max(rl ** 2 - cx ** 2, 0))
    dip_cut = box(-cx, yi, cx, rl + 50).difference(unary_union([L, R]))
    h = body.difference(dip_cut)
    return h.buffer(DIP_R, 64).buffer(-DIP_R, 64).buffer(-TIP_R, 64).buffer(TIP_R, 64)

def heart_around(r_clear):
    """Smallest classic heart that holds a circle of radius r_clear; returned centred on that circle."""
    for rl in np.arange(20, 160, 0.25):
        h = classic_heart(rl)
        ys = np.linspace(-TIP_RATIO * rl, rl, 400)
        d = [h.exterior.distance(Point(0, y)) if h.contains(Point(0, y)) else 0 for y in ys]
        i = int(np.argmax(d))
        if d[i] >= r_clear:
            return orient(stranslate(h, 0, -ys[i]), 1.0), rl
    raise RuntimeError("no heart found")

def flower_fill(region, min_r=2.6, max_size=None, gap=1.4):
    """Greedy, mirror-symmetric flower placement: biggest free spot first."""
    flowers = []
    free = region
    for _ in range(80):
        right = free.intersection(box(0, -1e3, 1e3, 1e3))
        best, at = 0, None
        for g in getattr(right, "geoms", [right]):
            if g.is_empty or g.area < 2: continue
            p = polylabel(g, 0.1)
            r = min([g.exterior.distance(p)] + [hh.distance(p) for hh in g.interiors])
            if abs(p.x) < 1.0:   # on the axis the mirror half-width is the limit
                r = min(r, free.exterior.distance(p) if free.geom_type == "Polygon" else r)
            if r > best: best, at = r, p
        if at is None or best < min_r: break
        on_axis = at.x < best * 0.9
        x = 0.0 if on_axis else at.x
        if on_axis:
            q = Point(0, at.y)
            g = free if free.geom_type == "Polygon" else min(free.geoms, key=lambda gg: gg.distance(q))
            best = min(best, g.exterior.distance(q))
            if best < min_r:
                free = free.difference(Point(0, at.y).buffer(min_r))
                continue
        size = best / 0.6
        if max_size: size = min(size, max_size)
        rad = 0.6 * size
        for sx in ((1,) if on_axis else (1, -1)):
            ang = math.radians(90 + 18 * ((len(flowers) % 3) - 1))
            flowers.append((sx * x, at.y, size, ang if sx > 0 else math.pi - ang))
            free = free.difference(Point(sx * x, at.y).buffer(rad + gap, 32))
    return flowers

def frame(D, style):
    Ri = (D + 2 * v2.RING_WALL) / 2 + v2.FABRIC_GAP
    Ro = Ri + v2.RIM_WIDTH
    f = FILLET
    heart, rl = heart_around(Ro + MARGIN)
    out = ray_outline(heart, (0.0, 0.0))
    Rtip = np.linalg.norm(out, axis=1).max()

    z1 = PLATE_T
    top = [(z1 - f + dz, 1 - ins / Rtip) for dz, ins in fillet_pts(f)]
    rings = [(0.0, 1.0)] + top if style == "single" else [(0.0, 1 - BACK_BEVEL / Rtip), (BACK_BEVEL, 1.0)] + top
    plate = loft(out, rings)

    prof = [(Ri, 0.0), (Ro, 0.0)]
    for a in np.linspace(0, math.pi / 2, ARC + 1):
        prof.append((Ro - f + f * math.cos(a), H - f + f * math.sin(a)))
    for a in np.linspace(math.pi / 2, math.pi, ARC + 1)[1:]:
        prof.append((Ri + f + f * math.cos(a), H - f + f * math.sin(a)))
    rim = Manifold.revolve(CrossSection([prof]), SEG)

    body = plate + rim
    body = body - Manifold.cylinder(H + 2, Ri, Ri, SEG).translate([0, 0, -1])
    # hanging hole: half way between the rim and the dip
    from make_heart_hoops import centre_line_y
    y_dip, _ = centre_line_y(heart)
    hole_c = (0.0, (Ro + y_dip) / 2)
    body = body - Manifold.cylinder(H + 2, HANG_HOLE_D / 2, HANG_HOLE_D / 2, 32).translate([hole_c[0], hole_c[1], -1])
    c = RING_CHAMF
    if style == "bedside":
        body = body - Manifold.cylinder(c + 0.01, Ri + c, Ri - 0.01, SEG).translate([0, 0, -0.01])
    m = H / 2
    g = [(Ri - 0.2, m - v2.GROOVE - 0.5), (Ri + v2.GROOVE, m - 0.3), (Ri + v2.GROOVE, m + 0.3), (Ri - 0.2, m + v2.GROOVE + 0.5)]
    body = body - Manifold.revolve(CrossSection([g]), SEG)

    # ---- decoration ----
    hole = Point(*hole_c).buffer(HANG_HOLE_D / 2 + 1.4, 24)
    plate_face = heart.buffer(-(f + 0.9)).difference(Point(0, 0).buffer(Ro + 0.9, 256)).difference(hole)
    e = f + 0.4
    flowers = flower_fill(plate_face.buffer(-0.3), max_size=0.42 * rl)
    pf = unary_union([mini_flower(x, y, s, a) for x, y, s, a in flowers]).intersection(plate_face)
    clean = lambda gg: unary_union([x for x in getattr(gg, "geoms", [gg]) if x.area > 1.0]).simplify(0.03)
    pf = clean(pf)
    rim_face = Point(0, 0).buffer(Ro - e, 256).difference(Point(0, 0).buffer(Ri + e, 256))
    rf = clean(wave_band((Ri + Ro) / 2, 0.9, 24, 1.0).intersection(rim_face))
    body = body + Manifold.extrude(to_cs(pf), TEX_H + 0.05).translate([0, 0, z1 - 0.05])
    body = body + Manifold.extrude(to_cs(rf), TEX_H + 0.05).translate([0, 0, H - 0.05])
    if style == "bedside":
        back_rim = Point(0, 0).buffer(Ro - e, 256).difference(Point(0, 0).buffer(Ri + c + e, 256))
        rb = clean(wave_band((Ri + c + Ro) / 2, 0.9, 24, 1.0).intersection(back_rim))
        bg = unary_union([plate_face.difference(pf), back_rim.difference(rb)])
        for _ in range(300):
            worst, at = 0.0, None
            for gg in getattr(bg, "geoms", [bg]):
                if gg.area < 1.0: continue
                pt = polylabel(gg, 0.05)
                dd = min([gg.exterior.distance(pt)] + [hh.distance(pt) for hh in gg.interiors])
                if dd > worst: worst, at = dd, pt
            if at is None or 2 * worst <= MAX_BRIDGE: break
            for k in (1, -1):
                bg = bg.difference(Point(k * at.x, at.y).buffer(1.0, 12))
        bg = bg.buffer(-0.05, 4).buffer(0.05, 4)
        bg = unary_union([gg for gg in getattr(bg, "geoms", [bg]) if gg.area > 1.0])
        body = body - Manifold.extrude(to_cs(bg), BACK_DEPTH + 0.5).translate([0, 0, -0.5])
        frame.back_background = bg
    frame.footprint = heart
    frame.flowers = flowers
    return body

def place_on_bed(fp_frame, ring_r, BED=256.0, M=3.0):
    fb = fp_frame.bounds
    F = stranslate(fp_frame, M - fb[0], M - fb[1])
    if F.bounds[2] > BED - M or F.bounds[3] > BED - M: return None
    for cx, cy in ((BED - M - ring_r, BED - M - ring_r), (BED - M - ring_r, M + ring_r), (M + ring_r, BED - M - ring_r)):
        if F.buffer(2).disjoint(Point(cx, cy).buffer(ring_r)):
            return (M - fb[0], M - fb[1]), (cx, cy)
    return None

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl"); os.makedirs(out, exist_ok=True)
    for style, tag in (("bedside", "2side"), ("single", "1side")):
        for D in SIZES:
            fm = frame(D, style)
            assert fm.status().name == "NoError" and len(fm.decompose()) == 1, "frame must be one clean solid"
            tf, tr = to_tm(fm), to_tm(v2.ring(D))
            assert tf.is_watertight and tr.is_watertight
            tf.export(os.path.join(out, f"heartr_{D}mm_{tag}_frame.stl"))
            tr.export(os.path.join(out, f"heartr_{D}mm_{tag}_ring.stl"))
            ring_r = D / 2 + v2.RING_WALL + v2.BEAD
            plan = place_on_bed(frame.footprint, ring_r)
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
                sc.export(os.path.join(out, f"heartr_{D}mm_{tag}_plate{suf}.3mf"))
            ext = tf.bounds[1] - tf.bounds[0]
            print(f"{style:7s} {D:3d}mm heart {ext[0]:.1f} x {ext[1]:.1f} mm, flowers {len(frame.flowers)}, faces {len(tf.faces)}, plates {len(plates)}")
