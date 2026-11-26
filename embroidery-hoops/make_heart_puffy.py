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
Z_RISE    = 5.6      # how much the cushion rises toward the inside
RISE_LEN  = 9.0      # mm over which it rises (smaller = rounder edge)
RIPPLE_A  = 0.45     # ripple amplitude (mm), 0 = smooth
RIPPLE_L  = 6.5      # ripple spacing (mm)
GRID      = 0.8      # height-field resolution (mm)
H, SEG, ARC, FILLET = v2.H, v2.SEG, v2.ARC, v2.FILLET

def height(t, ripples):
    """t = distance inside the heart edge (mm)."""
    z = Z_EDGE + Z_RISE * (1 - np.exp(-np.maximum(t, 0) / RISE_LEN))
    if ripples:
        fade = np.clip((t - 3.0) / 4.0, 0, 1)                    # keep the outer edge clean
        z = z + RIPPLE_A * fade * np.sin(2 * math.pi * t / RIPPLE_L)
    return z

def heightfield_solid(heart, ripples):
    minx, miny, maxx, maxy = heart.bounds
    xs = np.arange(minx - 2, maxx + 2 + GRID, GRID)
    ys = np.arange(miny - 2, maxy + 2 + GRID, GRID)
    X, Y = np.meshgrid(xs, ys)
    pts = shapely.points(X.ravel(), Y.ravel())
    t = shapely.distance(heart.exterior, pts) * np.where(shapely.contains(heart, pts), 1, -1)
    Z = height(t.reshape(X.shape), ripples)
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

def frame(D, ripples=False):
    Ri = (D + 2 * v2.RING_WALL) / 2 + v2.FABRIC_GAP
    Ro = Ri + v2.RIM_WIDTH
    f = FILLET
    heart, _ = heart_around(Ro + MARGIN)
    region = heart.difference(Point(0, 0).buffer(Ri, 256))
    plate = Manifold.extrude(to_cs(region), 20.0) ^ heightfield_solid(heart, ripples)
    prof = [(Ri, 0.0), (Ro, 0.0)]
    for a in np.linspace(0, math.pi / 2, ARC + 1):
        prof.append((Ro - f + f * math.cos(a), H - f + f * math.sin(a)))
    for a in np.linspace(math.pi / 2, math.pi, ARC + 1)[1:]:
        prof.append((Ri + f + f * math.cos(a), H - f + f * math.sin(a)))
    body = plate + Manifold.revolve(CrossSection([prof]), SEG)
    body = body - Manifold.cylinder(H + 2, Ri, Ri, SEG).translate([0, 0, -1])
    y_dip, _ = centre_line_y(heart)
    hole_c = (0.0, (Ro + y_dip) / 2)
    body = body - Manifold.cylinder(H + 30, v2.HANG_HOLE_D / 2, v2.HANG_HOLE_D / 2, 32).translate([hole_c[0], hole_c[1], -1])
    m, G = H / 2, v2.GROOVE
    g = [(Ri - 0.2, m - G - 0.5), (Ri + G, m - 0.3), (Ri + G, m + 0.3), (Ri - 0.2, m + G + 0.5)]
    body = body - Manifold.revolve(CrossSection([g]), SEG)
    frame.heart = heart
    return body

if __name__ == "__main__":
    import sys
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl"); os.makedirs(out, exist_ok=True)
    sizes = [int(a) for a in sys.argv[1:]] or SIZES
    for D in sizes:
        for ripples, tag in ((False, "puffy"), (True, "puffywave")):
            fm = frame(D, ripples)
            assert fm.status().name == "NoError" and len(fm.decompose()) == 1
            tf = to_tm(fm); assert tf.is_watertight
            tf.export(os.path.join(out, f"heart_{tag}_{D}mm_frame.stl"))
            e = tf.bounds[1] - tf.bounds[0]
            print(f"{tag:9s} {D}mm {e[0]:.0f} x {e[1]:.0f} x {e[2]:.1f} mm, faces {len(tf.faces)}")
