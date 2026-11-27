#!/usr/bin/env python3
"""Folding heart holder: the user's folding phone holder (holder_src/foldingphoneholder.3mf)
with only its phone pocket replaced by a pocket that holds the Quran heart.

The hinge, the leg, the panel, the shelf and the footprint are the original ones, untouched.
The new pocket is added on the panel's front face:
  * a slot shaped like the heart's own bottom edge (board 2.8 mm + clearance), so the heart
    sits in it without rocking sideways;
  * a front lip that covers only the heart's outer rim (no surah pocket is hidden);
  * a back rest that holds the heart more upright than a phone (HEART_TILT from the table),
    because at the phone angle the tall heart's centre of mass falls behind the leg.

Writes holder.stl (both hinge parts, laid on the side exactly like the original, print in place,
no supports), holder.3mf (same, in the original Bambu project) and holder_pose.json.
Run build.py first (preview.json gives the heart outline).
"""
import os, re, json, math, zipfile
import numpy as np
import trimesh
import manifold3d as m3d
from shapely.geometry import shape, box, Polygon
from shapely import affinity
from build import extrude, to_trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'holder_src', 'foldingphoneholder.3mf')

# ---------------------------------------------------------------- CONFIG
BOARD_T    = 2.8    # mm heart board thickness at the rim
SLOT_CLEAR = 0.35   # mm play each side of the board in the slot
EDGE_CLEAR = 0.3    # mm gap between the heart's edge and the slot floor
RIM_COVER  = 2.0    # mm the front lip reaches over the rim (surah pockets start after 3 mm)
FRONT_T    = 2.4    # mm front lip thickness
HEART_TILT = 72.0   # deg between the heart and the table (phone angle on this stand is ~50)
BACK_H     = 35.0   # mm how far up the heart's back the rest reaches
TIP_U      = 1.5    # mm heart's lowest point above the shelf corner, along the panel
# measured from the original model (print frame, mm)
FACE_P0    = np.array([124.556, 87.325])   # panel front face, bottom end
FACE_P1    = np.array([131.856, 150.680])  # panel front face, top end
SHELF_U    = -2.5                          # shelf top, along the face from FACE_P0
HINGE_C    = np.array([122.22, 154.88])    # hinge axis
HINGE_OPEN = 66.0                          # deg the leg opens to its stop
WIDTH      = 60.0                          # mm stand width (print z)


def load_parts():
    """(panel with shelf, leg) as trimesh, in the original plate position, plus raw xml."""
    z = zipfile.ZipFile(SRC)
    txt = z.read('3D/Objects/object_1.model').decode()
    top = z.read('3D/3dmodel.model').decode()

    def mat(s):
        v = list(map(float, s.split())); m = np.eye(4)
        m[:3, :3] = np.array(v[:9]).reshape(3, 3).T; m[:3, 3] = v[9:]
        return m
    comps = {o: mat(t) for t, o in [(t, o) for o, t in
             re.findall(r'<component[^>]*objectid="(\d+)"[^>]*transform="([^"]+)"', top)]}
    item = mat(re.search(r'<item[^>]*transform="([^"]+)"', top).group(1))
    parts = {}
    for oid, body in re.findall(r'<object id="(\d+)"[^>]*>(.*?)</object>', txt, re.S):
        V = np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', body), float)
        F = np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', body), int)
        m = trimesh.Trimesh(V, F, process=True)
        parts[oid] = (m, item @ comps[oid])
    return parts, z


def tm2man(t):
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(t.vertices, np.float32),
                                 tri_verts=np.asarray(t.faces, np.uint32)))


def unit(v):
    return v / np.linalg.norm(v)


def rot2(a):
    return np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])


def table_frame(panel, leg_open):
    """Resting line of the opened stand: leg tip and shelf corner (convex hull edge)."""
    from scipy.spatial import ConvexHull
    pts = np.vstack([panel.vertices[:, :2], leg_open.vertices[:, :2]])
    V = pts[ConvexHull(pts).vertices]
    best = None
    for i in range(len(V)):
        p, q = V[i], V[(i + 1) % len(V)]
        if np.linalg.norm(q - p) > 60 and q[1] < p[1]:      # long edge running down to the shelf
            best = (p, q)
    return best


def main():
    out = os.environ.get('HOLDER_OUT', HERE)
    src = os.environ.get('HOLDER_SRC', HERE)
    parts, zsrc = load_parts()
    (pm, pT), (lm, lT) = parts['1'], parts['2']
    panel = pm.copy(); panel.apply_transform(pT)
    leg = lm.copy(); leg.apply_transform(lT)

    d = unit(FACE_P1 - FACE_P0)                 # up the panel face
    n = np.array([d[1], -d[0]])                 # out of the face (front)
    # opened stand and the table it stands on
    R = trimesh.transformations.rotation_matrix(math.radians(-HINGE_OPEN), [0, 0, 1], [*HINGE_C, 0])
    leg_open = leg.copy(); leg_open.apply_transform(R)
    p_leg, p_shelf = table_frame(panel, leg_open)
    back = unit(p_leg - p_shelf)                # along the table, toward the leg
    face_tilt = math.degrees(math.acos(np.clip(d @ back, -1, 1)))
    delta = math.radians(HEART_TILT - face_tilt)
    e = math.cos(delta) * d + math.sin(delta) * n          # heart's up direction
    f = math.cos(delta) * n - math.sin(delta) * d          # heart's front normal
    T = FACE_P0 + TIP_U * d                                # heart's lowest point (back face)

    # heart outline in heart coords: s across (0 = centre of mass), v up (0 = lowest point)
    H = shape(json.load(open(os.path.join(src, 'preview.json')))['outline'])
    x0, y0 = H.centroid.x, H.bounds[1]
    H = affinity.translate(H, -x0, -y0)
    hc_v = H.centroid.y

    # local heart frame (s, v, m) -> print (x, y, z); right of the heart = -z
    M = [[0, e[0], f[0], T[0]], [0, e[1], f[1], T[1]], [-1, 0, 0, WIDTH / 2]]
    m_slot = BOARD_T + 2 * SLOT_CLEAR
    m_front = m_slot + FRONT_T
    W = box(-WIDTH / 2, -12, WIDTH / 2, BACK_H)
    pocket = extrude(W, -0.6, m_front + 0.6)
    pocket = pocket - extrude(H.buffer(EDGE_CLEAR, join_style=1), 0, m_slot)
    pocket = pocket - extrude(H.buffer(-RIM_COVER, join_style=1), m_slot - 0.01, FRONT_T + 2)
    # back rest: between the panel face and the heart's back, up to BACK_H
    q = T + BACK_H * e
    # walk from q back along -f to the face line (n = -0.6)
    t = ((q - FACE_P0) @ n + 0.6) / (f @ n)
    q_face = q - t * f
    rest2d = Polygon([T - 0.6 * n - 6 * d, q_face, q, T - 0.02 * f - 0.6 * e])
    rest2d = rest2d.buffer(-1.5, join_style=1).buffer(1.5, join_style=1)
    rest = extrude(rest2d, 0, WIDTH)                       # print z = 0..60
    add = pocket.transform(M) + rest
    # keep the additions above the shelf top and in front of the panel: the shelf bottom,
    # the hinge and the footprint stay the original ones
    keep2d = Polygon([FACE_P0 + (SHELF_U - 0.5) * d - 0.6 * n, FACE_P0 + (SHELF_U - 0.5) * d + 40 * n,
                      FACE_P0 + 80 * d + 40 * n, FACE_P0 + 80 * d - 0.6 * n])
    add = add ^ extrude(keep2d, -1, WIDTH + 2)
    add = add ^ extrude(box(0, 0, 400, 400), 0, WIDTH)

    new_panel = tm2man(panel) + add
    pan_t = to_trimesh(new_panel)
    pan_t.merge_vertices()
    os.makedirs(out, exist_ok=True)
    both = trimesh.util.concatenate([pan_t, leg])
    both.apply_translation([0, 0, -both.bounds[0, 2]])
    both.export(os.path.join(out, 'holder.stl'))

    # 3MF: the original Bambu project with the panel mesh replaced
    inv = np.linalg.inv(pT)
    loc = pan_t.copy(); loc.apply_transform(inv)
    vx = ''.join(f'<vertex x="{a:.6f}" y="{b:.6f}" z="{c:.6f}"/>' for a, b, c in loc.vertices)
    tr = ''.join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in loc.faces)
    txt = zsrc.read('3D/Objects/object_1.model').decode()
    body = re.search(r'(<object id="1"[^>]*>.*?<mesh>)(.*?)(</mesh>)', txt, re.S)
    txt = txt[:body.start(2)] + f'<vertices>{vx}</vertices><triangles>{tr}</triangles>' + txt[body.end(2):]
    with zipfile.ZipFile(os.path.join(out, 'holder.3mf'), 'w', zipfile.ZIP_DEFLATED) as zo:
        for it in zsrc.infolist():
            if it.filename.startswith('Metadata/') and it.filename.endswith(('.png', 'slice_info.config')):
                continue                                    # stale previews / slice data
            data = zsrc.read(it.filename)
            if it.filename == '3D/Objects/object_1.model':
                data = txt.encode()
            elif it.filename == 'Metadata/model_settings.config':
                s = data.decode()
                s = re.sub(r'<metadata key="thumbnail[^>]*/>\s*|<metadata key="(top|pick)_file"[^>]*/>\s*', '', s)
                s = s.replace('face_count="2250"', f'face_count="{len(pan_t.faces) + 588}"')
                s = s.replace('mesh_stat face_count="1662"', f'mesh_stat face_count="{len(pan_t.faces)}"')
                data = s.encode()
            zo.writestr(it, data)

    # ---------------- checks and pose
    PM = tm2man(pan_t)
    closed = (PM ^ tm2man(leg)).volume()
    opened = (PM ^ tm2man(leg_open)).volume()
    heart = extrude(H, 0.0, BOARD_T).transform(M)          # board slab in its seat
    hit = (heart ^ PM).volume() + (heart ^ tm2man(leg_open)).volume()
    # stability: heart CoM and stand CoM projected on the table line
    span = np.linalg.norm(p_leg - p_shelf)
    def along(p):                                          # 0 = shelf contact, span = leg tip
        return float((np.asarray(p) - p_shelf) @ back)
    heart_com = T + hc_v * e + BOARD_T / 2 * f
    vol_board = trimesh.load(os.path.join(src, 'board_upright.stl')).volume
    pdir = os.path.join(src, 'pieces')
    vol_pieces = sum(trimesh.load(os.path.join(pdir, p)).volume for p in os.listdir(pdir) if p.endswith('.stl'))
    stand_t = trimesh.util.concatenate([pan_t, leg_open])
    st_com = stand_t.center_mass[:2]
    vh, vs = vol_board + vol_pieces, stand_t.volume
    comb = (along(heart_com) * vh + along(st_com) * vs) / (vh + vs)
    up = np.array([-back[1], back[0]])
    up = up if up @ d > 0 else -up
    side_h = (heart_com - p_shelf) @ up
    pose = dict(hinge=HINGE_C.tolist(), hinge_open=HINGE_OPEN, table_p=p_shelf.tolist(),
                table_back=back.tolist(), heart_M=M, heart_x0=x0, heart_y0=y0,
                z_shift=float(-trimesh.util.concatenate([pan_t, leg]).bounds[0, 2]))
    json.dump(pose, open(os.path.join(out, 'holder_pose.json'), 'w'))
    bb = both.bounds
    low_new = min(((pan_t.vertices[:, :2] - p_shelf) @ up).min(), ((leg_open.vertices[:, :2] - p_shelf) @ up).min())
    low_old = ((panel.vertices[:, :2] - p_shelf) @ up).min()
    print(f'  lowest point vs table: original {low_old:.3f}, new {low_new:.3f} mm')
    print(f'holder {bb[1][0]-bb[0][0]:.1f} x {bb[1][1]-bb[0][1]:.1f} x {bb[1][2]-bb[0][2]:.1f} mm (print), '
          f'panel watertight {pan_t.is_watertight}, leg/panel overlap closed {closed:.2f} open {opened:.2f} mm3, '
          f'heart overlap {hit:.3f} mm3')
    print(f'  phone angle {face_tilt:.1f} deg, heart angle {HEART_TILT} deg; footprint {span:.0f} mm deep; '
          f'heart CoM {along(heart_com):.0f} mm behind the shelf contact (leg at {span:.0f}), '
          f'with the stand {comb:.0f}; CoM height {side_h:.0f} mm -> side tip angle '
          f'{math.degrees(math.atan2(WIDTH/2, side_h)):.0f} deg; heart {vh/1000:.0f} cm3, stand {vs/1000:.0f} cm3')


if __name__ == '__main__':
    main()
