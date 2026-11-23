"""
Parametric scalloped (flower) embroidery hoop generator.
Two parts per size, both print flat with NO supports:
  1) frame  : scalloped flower plate + raised round rim + hanging hole
  2) ring   : inner ring with a small back flange (fabric is clamped between ring and frame)
Usage:  python3 make_hoops.py            -> builds all sizes into ./stl
Requires: pip install manifold3d trimesh shapely numpy
"""
import math, os
import numpy as np
from manifold3d import Manifold, CrossSection
from shapely.geometry import Point
from shapely.ops import unary_union
import trimesh

# ---------------- parameters (mm) ----------------
SIZES        = [60, 80, 100]   # visible fabric opening diameter
PETALS       = 12              # number of scallops
RING_WALL    = 3.5             # inner ring wall thickness
FABRIC_GAP   = 0.55            # radial clearance per side for fabric (increase for thick fabric)
RIM_WIDTH    = 5.0             # raised round rim width on frame
PLATE_H      = 3.0             # flower plate thickness
FRAME_H      = 7.0             # total frame height (plate + rim)
FLANGE_W     = 2.0             # inner ring back flange radial width
FLANGE_H     = 1.2             # flange thickness
HANG_HOLE_D  = 4.0             # hanging hole diameter
CHAMFER      = 0.8             # entry chamfer on ring top & frame bore bottom
SEG          = 256             # circle resolution

def circle_cs(r, n=SEG):
    return CrossSection.circle(r, n)

def shapely_to_cs(geom):
    from shapely.geometry.polygon import orient
    polys = []
    for g in getattr(geom, "geoms", [geom]):
        g = orient(g, 1.0)  # CCW outer, CW holes
        polys.append(np.asarray(g.exterior.coords[:-1], dtype=np.float64))
        for h in g.interiors:
            polys.append(np.asarray(h.coords[:-1], dtype=np.float64))
    return CrossSection(polys)

def frame_part(D):
    ring_od = D + 2 * RING_WALL
    bore = ring_od + 2 * FABRIC_GAP
    rim_od = bore + 2 * RIM_WIDTH
    Rc = rim_od / 2 + 5.0                               # petal centre radius
    rp = 2 * Rc * math.sin(math.pi / PETALS) * 0.55     # petal radius
    petals = [Point(Rc * math.cos(a), Rc * math.sin(a)).buffer(rp, 64)
              for a in (2 * math.pi * i / PETALS + math.pi / 2 for i in range(PETALS))]
    flower = unary_union(petals + [Point(0, 0).buffer(Rc, 128)])
    plate = Manifold.extrude(shapely_to_cs(flower), PLATE_H)
    rim = Manifold.extrude(circle_cs(rim_od / 2), FRAME_H)
    body = plate + rim
    # through bore with small chamfer on the bottom (entry side, where the ring enters)
    bore_cyl = Manifold.cylinder(FRAME_H + 2, bore / 2, bore / 2, SEG).translate([0, 0, -1])
    cham = Manifold.cylinder(CHAMFER + 0.01, bore / 2 + CHAMFER, bore / 2, SEG).translate([0, 0, -0.01])
    body = body - bore_cyl - cham
    # hanging hole through the top petal
    hole = Manifold.cylinder(PLATE_H + 2, HANG_HOLE_D / 2, HANG_HOLE_D / 2, 48).translate([0, Rc, -1])
    body = body - hole
    return body, dict(bore=bore, rim_od=rim_od, outer=2 * (Rc + rp))

def ring_part(D):
    ring_od = D + 2 * RING_WALL
    r_in, r_out = D / 2, ring_od / 2
    h = FRAME_H + FLANGE_H
    # profile in (r, z), revolved around Z: flange at bottom, chamfer at top outer edge
    prof = [(r_in, 0), (r_out + FLANGE_W, 0), (r_out + FLANGE_W, FLANGE_H),
            (r_out, FLANGE_H), (r_out, h - CHAMFER), (r_out - CHAMFER, h), (r_in, h)]
    return Manifold.revolve(CrossSection([prof]), SEG)

def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                           faces=np.asarray(mesh.tri_verts), process=True)

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "stl"); os.makedirs(out, exist_ok=True)
    for D in SIZES:
        f, info = frame_part(D)
        r = ring_part(D)
        tf, tr = to_trimesh(f), to_trimesh(r)
        assert tf.is_watertight and tr.is_watertight
        tf.export(os.path.join(out, f"hoop_{D}mm_frame.stl"))
        tr.export(os.path.join(out, f"hoop_{D}mm_ring.stl"))
        # combined plate: both parts side by side, ready for Bambu Studio
        shift = info["outer"] / 2 + (D / 2 + RING_WALL + FLANGE_W) + 8
        scene = trimesh.Scene()
        scene.add_geometry(tf, node_name=f"frame_{D}")
        scene.add_geometry(tr.copy().apply_translation([shift, 0, 0]), node_name=f"ring_{D}")
        scene.export(os.path.join(out, f"hoop_{D}mm_plate.3mf"))
        print(f"{D}mm opening: frame outer {info['outer']:.1f} mm, bore {info['bore']:.2f}, "
              f"ring OD {D + 2*RING_WALL:.1f}, frame vol {tf.volume/1000:.1f} cm3, ring vol {tr.volume/1000:.1f} cm3")
