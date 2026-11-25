#!/usr/bin/env python3
"""Quran heart puzzle generator (Bambu Lab A1, 256 x 256 mm bed).

Traces the cells of the heart drawing in reference.jpg, then builds:
  * board.stl            - one-piece heart: 1.2 mm base + 2 mm walls around every pocket
  * pieces/NNN_<name>.stl - one piece per surah, with its name raised 1 mm
  * pieces_plate_N.stl   - all pieces packed onto A1-sized plates

Usage:  python3 build.py            (all settings are in the CONFIG block)
"""
import json, os, math
import numpy as np
import cv2
from scipy import ndimage as ndi
import shapely
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union, polylabel
from shapely import affinity
import manifold3d as m3d
import trimesh
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- CONFIG
HEART_MAX_SIZE = 238.0   # mm, longest side of the heart drawing (board adds rim + hanger lugs)
BASE_H         = 0.8     # mm, base plate thickness
WALL_H         = 2.0     # mm, wall height above the base (= pocket depth)
WALL_T         = 1.6     # mm, thickness of the walls between pockets
RIM_T          = 3.0     # mm, thickness of the outer rim of the heart
CLEARANCE      = 0.20    # mm, gap per side between piece and pocket
PIECE_H        = 2.0     # mm, piece body thickness (flush with the walls)
TEXT_H         = 1.0     # mm, raised name height
TEXT_MARGIN    = 0.8     # mm, keep text this far from the piece edge
TEXT_MAX_EM    = 10.0    # mm, largest font size used
FONT           = '/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf'
# name lock: the surah name is raised on the pocket floor, and the same name is
# hollowed into the underside of the piece, so each piece sits on its own name
FLOOR_TEXT_H   = 1.0     # mm, name height above the pocket floor
NAME_CLEAR     = 0.12    # mm, gap per side between raised name and hollow
RECESS_DEPTH   = 1.2     # mm, hollow depth under the piece (> FLOOR_TEXT_H)
# hanger: separate banner part that plugs into two lugs on top of the heart
BRAND_TEXT     = 'ZeroCut'  # engraved into the back of the heart
BRAND_FONT     = '/usr/share/fonts/opentype/inter/Inter-Bold.otf'
BRAND_DEPTH    = 0.2     # mm engraving depth on the back face
BRAND_MAX_EM   = 26.0    # mm
HANGER_TEXT    = 'بسم الله الرحمن الرحيم'
HANGER_FONT    = '/usr/share/fonts/opentype/fonts-hosny-amiri/Amiri-Bold.ttf'
HANGER_W       = 130.0   # mm banner width
HANGER_H       = 30.0    # mm banner height
HANGER_HOLE_D  = 5.0     # mm hanging hole (nail / hook)
LUG_W          = 14.0    # mm width of the lugs added to the heart
LUG_RISE       = 8.0     # mm the lugs rise above the highest tube
KNOB_R         = 3.5     # mm jigsaw knob head radius
KNOB_NECK_W    = 4.0     # mm jigsaw knob neck width
KNOB_NECK_L    = 3.0     # mm jigsaw knob neck length
KNOB_CLEAR     = 0.15    # mm gap per side in the jigsaw joint
# the hanger lies level with the heart; its jigsaw knobs press into the lug sockets.
# A thin back layer reaches down behind each lug (hidden against the wall), so the knob
# cannot slide through the socket, and the snug fit holds it in place.
HANGER_KNOB_CLEAR = 0.07 # mm gap per side between knob and socket (snug press fit)
HANGER_BACK_T  = 1.0     # mm back layer behind the hanger and behind each lug
PLATE          = 250.0   # mm usable square on the A1 plate
PLATE_GAP      = 3.0     # mm between pieces on a plate

SURAHS = ['الفاتحة','البقرة','آل عمران','النساء','المائدة','الأنعام','الأعراف','الأنفال','التوبة','يونس',
 'هود','يوسف','الرعد','إبراهيم','الحجر','النحل','الإسراء','الكهف','مريم','طه','الأنبياء','الحج','المؤمنون',
 'النور','الفرقان','الشعراء','النمل','القصص','العنكبوت','الروم','لقمان','السجدة','الأحزاب','سبأ','فاطر','يس',
 'الصافات','ص','الزمر','غافر','فصلت','الشورى','الزخرف','الدخان','الجاثية','الأحقاف','محمد','الفتح','الحجرات',
 'ق','الذاريات','الطور','النجم','القمر','الرحمن','الواقعة','الحديد','المجادلة','الحشر','الممتحنة','الصف',
 'الجمعة','المنافقون','التغابن','الطلاق','التحريم','الملك','القلم','الحاقة','المعارج','نوح','الجن','المزمل',
 'المدثر','القيامة','الإنسان','المرسلات','النبأ','النازعات','عبس','التكوير','الانفطار','المطففين','الانشقاق',
 'البروج','الطارق','الأعلى','الغاشية','الفجر','البلد','الشمس','الليل','الضحى','الشرح','التين','العلق','القدر',
 'البينة','الزلزلة','العاديات','القارعة','التكاثر','العصر','الهمزة','الفيل','قريش','الماعون','الكوثر',
 'الكافرون','النصر','المسد','الإخلاص','الفلق','الناس']
assert len(SURAHS) == 114

# ---------------------------------------------------------------- 1. trace cells
def trace_cells():
    im = cv2.imread(os.path.join(HERE, 'reference.jpg'))
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    v, s = hsv[..., 2].astype(int), hsv[..., 1].astype(int)
    white = (v > 170) & (s < 40)
    dark = cv2.dilate((~white).astype(np.uint8), np.ones((2, 2), np.uint8)).astype(bool)
    comp, _ = ndi.label(~dark)
    cells = json.load(open(os.path.join(HERE, 'cells.json'), encoding='utf-8'))
    H, W = comp.shape
    # group components by name (one cell may be split in the drawing by its text)
    groups = {}
    for c in cells:
        x, y = c['seed']
        cid = comp[y, x]
        assert cid > 0, c
        key = c['name'] if c['name'] else f"__blank_{x}_{y}"
        groups.setdefault(key, set()).add(cid)
    keys = list(groups)
    lab = np.zeros((H, W), np.int32)
    for k, key in enumerate(keys, 1):
        m = np.isin(comp, list(groups[key]))
        lab[ndi.binary_fill_holes(m)] = k
    # merge pieces of one name across the line that splits them
    for k, key in enumerate(keys, 1):
        if len(groups[key]) > 1:
            m = lab == k
            m2 = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)).astype(bool)
            lab[m2 & (lab == 0)] = k
    # close notches left by letters touching the outline
    claim = np.zeros((H, W), np.int32); cnt = np.zeros((H, W), np.int32)
    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    for k in range(1, len(keys) + 1):
        m = cv2.morphologyEx((lab == k).astype(np.uint8), cv2.MORPH_CLOSE, disk).astype(bool)
        m = ndi.binary_fill_holes(m) & (lab == 0)
        claim[m] = k; cnt[m] += 1
    lab[(cnt == 1)] = claim[cnt == 1]
    # heart silhouette, then give every leftover pixel (lines) to the nearest cell
    heart = cv2.morphologyEx((lab > 0).astype(np.uint8), cv2.MORPH_CLOSE,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))).astype(bool)
    heart = cv2.dilate(heart.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))).astype(bool)
    heart = ndi.binary_fill_holes(heart)
    _, (iy, ix) = ndi.distance_transform_edt(lab == 0, return_indices=True)
    full = lab[iy, ix] * heart
    return full, keys


def mask_to_polys(mask, scale, H, up=4):
    """Smooth sub-pixel contour of a binary mask -> shapely geometry in mm (y up)."""
    f = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 1.2)
    f = cv2.resize(f, None, fx=up, fy=up, interpolation=cv2.INTER_LINEAR)
    b = (f > 0.5).astype(np.uint8)
    cs, hier = cv2.findContours(b, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    polys = []
    if hier is None:
        return Polygon()
    hier = hier[0]
    for i, c in enumerate(cs):
        if hier[i][3] != -1 or len(c) < 4:
            continue
        def tomm(cc):
            p = cc[:, 0, :].astype(float) / up
            return [(x * scale, (H - y) * scale) for x, y in p]
        holes = []
        j = hier[i][2]
        while j != -1:
            if len(cs[j]) >= 4: holes.append(tomm(cs[j]))
            j = hier[j][0]
        polys.append(Polygon(tomm(c), holes).buffer(0))
    g = unary_union(polys).simplify(0.05)
    return g

# ---------------------------------------------------------------- 2. text
class FlatPen(BasePen):
    def __init__(self, gs, steps=5):
        super().__init__(gs); self.contours = []; self.cur = []; self.steps = steps
    def _moveTo(self, p): self.cur = [p]
    def _lineTo(self, p): self.cur.append(p)
    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        for t in np.linspace(0, 1, self.steps + 1)[1:]:
            a = (1 - t) ** 3; b = 3 * (1 - t) ** 2 * t; c = 3 * (1 - t) * t * t; d = t ** 3
            self.cur.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        for t in np.linspace(0, 1, self.steps + 1)[1:]:
            a = (1 - t) ** 2; b = 2 * (1 - t) * t; c = t * t
            self.cur.append((a * p0[0] + b * p1[0] + c * p2[0], a * p0[1] + b * p1[1] + c * p2[1]))
    def _closePath(self):
        if len(self.cur) > 2: self.contours.append(self.cur)
        self.cur = []
    _endPath = _closePath

_font_cache = {}
def text_shape(txt, font=None):
    """Shaped Arabic text as shapely geometry, 1 unit = 1 em, centred on its bbox."""
    font = font or FONT
    if font not in _font_cache:
        _font_cache[font] = (hb.Font(hb.Face(hb.Blob.from_file_path(font))), TTFont(font))
    hfont, tt = _font_cache[font]
    upem = tt['head'].unitsPerEm
    buf = hb.Buffer(); buf.add_str(txt); buf.guess_segment_properties()
    hb.shape(hfont, buf, {})
    gs = tt.getGlyphSet(); order = tt.getGlyphOrder()
    contours = []; x = 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        pen = FlatPen(gs); gs[order[info.codepoint]].draw(pen)
        for c in pen.contours:
            contours.append([((px + x + pos.x_offset) / upem, (py + pos.y_offset) / upem) for px, py in c])
        x += pos.x_advance
    cs = m3d.CrossSection(contours, m3d.FillRule.NonZero)
    geom = cross_to_shapely(cs)
    minx, miny, maxx, maxy = geom.bounds
    return affinity.translate(geom, -(minx + maxx) / 2, -(miny + maxy) / 2)


def cross_to_shapely(cs):
    polys = []
    for ring in cs.to_polygons():
        polys.append(np.asarray(ring))
    # rebuild with even-odd from (already non-overlapping) rings
    outers, holes = [], []
    for r in polys:
        if len(r) < 3: continue
        p = Polygon(r)
        (outers if p.exterior.is_ccw else holes).append(p)
    g = unary_union(outers)
    if holes: g = g.difference(unary_union(holes))
    return g


def shapely_to_cross(g):
    rings = []
    geoms = g.geoms if hasattr(g, 'geoms') else [g]
    for p in geoms:
        if p.is_empty: continue
        p = shapely.geometry.polygon.orient(p, 1.0)
        rings.append(list(p.exterior.coords)[:-1])
        for h in p.interiors: rings.append(list(h.coords)[:-1])
    return m3d.CrossSection(rings, m3d.FillRule.EvenOdd)


def fit_text(name, area, font=None, angles=range(-90, 91, 10), max_em=None):
    """Largest placement of `name` inside polygon `area` (searches position + angle)."""
    TEXT_MAX = max_em or TEXT_MAX_EM
    base = text_shape(name, font)
    if hasattr(area, 'geoms'):
        area = max(area.geoms, key=lambda p: p.area)
    if area.is_empty:
        return None, 0
    probe = base.simplify(0.01)
    shapely.prepare(area)
    # candidate centres: the most "inside" points of the piece
    minx, miny, maxx, maxy = area.bounds
    step = max(maxx - minx, maxy - miny) / 24
    pts = [Point(x, y) for x in np.arange(minx, maxx, step) for y in np.arange(miny, maxy, step)]
    pts = [p for p in pts if area.contains(p)]
    pts.sort(key=lambda p: -area.exterior.distance(p))
    cands = [polylabel(area, 0.05), area.centroid] + pts[:40]
    best = (0.0, None)
    def ok(rot, c, em):
        return area.contains(affinity.translate(affinity.scale(rot, em, em, origin=(0, 0)), c.x, c.y))
    for ang in angles:
        pen = 1.0 - 0.003 * abs(ang)          # small preference for upright text
        rot = affinity.rotate(probe, ang, origin=(0, 0))
        for c in cands:
            lo = best[0] / pen * 1.005
            if lo >= TEXT_MAX or not ok(rot, c, max(lo, 0.3)):
                continue
            hi = TEXT_MAX
            if ok(rot, c, hi): lo = hi
            for _ in range(12):
                mid = (lo + hi) / 2
                if ok(rot, c, mid): lo = mid
                else: hi = mid
            if lo * pen > best[0]:
                best = (lo * pen, (lo, ang, c))
    if best[1] is None:
        return None, 0
    em, ang, c = best[1]
    rot = affinity.rotate(base, ang, origin=(0, 0))
    while em > 0.3 and not ok(rot, c, em):
        em *= 0.98
    t = affinity.translate(affinity.scale(rot, em, em, origin=(0, 0)), c.x, c.y).simplify(0.02)
    # small text: thicken strokes so they stay printable with a 0.4 mm nozzle
    grow = min(0.15, max(0.0, (0.55 - 0.1 * em) / 2))
    if grow > 0:
        t = t.buffer(grow, join_style=1).intersection(area.buffer(TEXT_MARGIN / 2))
    return t, em

# ---------------------------------------------------------------- 3. solids
def extrude(g, z0, h):
    return shapely_to_cross(g).extrude(h).translate([0, 0, z0])

def to_trimesh(man):
    mesh = man.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts), process=False)


def main():
    out = HERE
    os.makedirs(os.path.join(out, 'pieces'), exist_ok=True)
    print('tracing cells ...')
    full, keys = trace_cells()
    H, W = full.shape
    ys, xs = np.nonzero(full)
    span = max(xs.max() - xs.min(), ys.max() - ys.min())
    scale = HEART_MAX_SIZE / span
    print(f'  {len(keys)} cells, scale {scale:.4f} mm/px')

    cells = {}
    for k, key in enumerate(keys, 1):
        cells[key] = mask_to_polys(full == k, scale, H)
    heart = unary_union(list(cells.values())).buffer(0.3).buffer(-0.3)
    heart = Polygon(max(heart.geoms, key=lambda p: p.area).exterior) if hasattr(heart, 'geoms') else Polygon(heart.exterior)
    # centre the heart at origin
    minx, miny, maxx, maxy = heart.bounds
    dx, dy = -(minx + maxx) / 2, -(miny + maxy) / 2
    heart = affinity.translate(heart, dx, dy)
    cells = {k: affinity.translate(v, dx, dy).intersection(heart) for k, v in cells.items()}

    outline = heart.buffer(RIM_T - WALL_T / 2, join_style=1)
    pockets = {}
    for key, g in cells.items():
        if key.startswith('__blank'):
            continue
        p = g.buffer(-WALL_T / 2, join_style=1).buffer(-0.4).buffer(0.4)   # drop slivers
        if hasattr(p, 'geoms'): p = max(p.geoms, key=lambda q: q.area)
        pockets[key] = p.simplify(0.03).buffer(0)
    TOP = BASE_H + WALL_H

    # ---- hanger lugs on the two tallest tubes (الفاتحة / البقرة) + jigsaw sockets
    lug_x = []
    for name in ('الفاتحة', 'البقرة'):
        c = cells[name]
        c = max(c.geoms, key=lambda q: q.area) if hasattr(c, 'geoms') else c
        pts = np.asarray(c.exterior.coords)
        top = pts[pts[:, 1] > pts[:, 1].max() - 1.5]
        lug_x.append(float(top[:, 0].mean()))
    def outline_top(x):
        col = outline.intersection(shapely.geometry.LineString([(x, -500), (x, 500)]))
        return col.bounds[3]
    y_join = max(outline_top(x) for x in lug_x) + LUG_RISE
    lugs, sockets, knobs = [], [], []
    for x in lug_x:
        y0 = min(outline_top(x + d) for d in (-LUG_W / 2, 0, LUG_W / 2)) - 3
        lugs.append(shapely.geometry.box(x - LUG_W / 2, y0, x + LUG_W / 2, y_join).buffer(-1.5).buffer(1.5))
        def knob(cl):
            cy = y_join - KNOB_NECK_L - KNOB_R
            return unary_union([Point(x, cy).buffer(KNOB_R + cl, 48),
                                shapely.geometry.box(x - KNOB_NECK_W / 2 - cl, cy, x + KNOB_NECK_W / 2 + cl, y_join + 2)])
        sockets.append(knob(KNOB_CLEAR)); knobs.append(knob(0).intersection(
            shapely.geometry.box(-1e3, -1e3, 1e3, y_join + 0.5)))
    board_outline = unary_union([outline] + lugs).simplify(0.03).buffer(0)
    bx = board_outline.bounds
    print(f'  board size {bx[2]-bx[0]:.1f} x {bx[3]-bx[1]:.1f} mm (incl. hanger lugs)')

    # ---- name placement for every pocket (same on piece top, pocket floor and piece underside)
    names = {}
    for key, pk in pockets.items():
        body = pk.buffer(-CLEARANCE, join_style=1)
        if hasattr(body, 'geoms'): body = max(body.geoms, key=lambda q: q.area)
        body = body.simplify(0.03).buffer(0)
        txt, em = fit_text(key, body.buffer(-TEXT_MARGIN, join_style=1))
        if txt is not None:   # closing removes glyphs that touch at a single point
            txt = txt.buffer(0.03, join_style=1, quad_segs=2).buffer(-0.05, join_style=1, quad_segs=2).buffer(0.02, join_style=1, quad_segs=2).simplify(0.01)
        names[key] = (body, txt, em)

    # ---- board
    board = extrude(board_outline, 0, TOP)
    # opening removes zero-width wall pinches where two pocket corners meet
    cut = extrude(unary_union(list(pockets.values())).buffer(-0.15, join_style=1).buffer(0.12, join_style=1), BASE_H, WALL_H + 1)
    board = board - cut - extrude(unary_union(sockets), -1, TOP + 2)
    floor_txt = unary_union([t for _, t, _ in names.values() if t is not None])
    board = board + extrude(floor_txt, BASE_H - 0.01, FLOOR_TEXT_H + 0.01)
    # brand engraved into the back face, mirrored so it reads correctly from behind
    btx, bte = fit_text(BRAND_TEXT, outline.buffer(-12), font=BRAND_FONT, angles=(0,), max_em=BRAND_MAX_EM)
    btx = affinity.scale(btx, -1, 1, origin=btx.centroid)
    board = board - extrude(btx, -1, 1 + BRAND_DEPTH)
    print(f'  back engraving "{BRAND_TEXT}" {btx.bounds[2]-btx.bounds[0]:.0f} mm wide, {BRAND_DEPTH} mm deep')
    to_trimesh(board).export(os.path.join(out, 'board.stl'))
    print('  board.stl written')

    # ---- hanger banner
    cx = outline.centroid.x                      # hang above the centre of mass
    lo_x = min(min(lug_x) - LUG_W, cx - HANGER_W / 2)
    hi_x = max(max(lug_x) + LUG_W, cx + HANGER_W / 2)
    band = shapely.geometry.box(lo_x, y_join, hi_x, y_join + HANGER_H).buffer(-6).buffer(6)
    ear_c = Point(cx, y_join + HANGER_H + 4)
    ear = unary_union([ear_c.buffer(8, 64), shapely.geometry.box(cx - 8, y_join + HANGER_H - 3, cx + 8, ear_c.y)])
    head_y = y_join - KNOB_NECK_L - KNOB_R
    cl = KNOB_CLEAR - HANGER_KNOB_CLEAR
    knobs = [unary_union([Point(x, head_y).buffer(KNOB_R + cl, 64),
                          shapely.geometry.box(x - KNOB_NECK_W / 2 - cl, head_y, x + KNOB_NECK_W / 2 + cl, y_join + 1)])
             .intersection(shapely.geometry.box(-1e3, -1e3, 1e3, y_join + 1)) for x in lug_x]
    banner = unary_union([band, ear] + knobs)
    banner = banner.difference(ear_c.buffer(HANGER_HOLE_D / 2, 48))
    backs = [shapely.geometry.box(x - LUG_W / 2 + 0.5, head_y - KNOB_R - 3, x + LUG_W / 2 - 0.5, y_join + 2)
             .buffer(-2, join_style=1).buffer(2, join_style=1) for x in lug_x]
    back = unary_union([banner] + backs).difference(ear_c.buffer(HANGER_HOLE_D / 2, 48))
    text_area = band.buffer(-3.5)
    btxt, bem = fit_text(HANGER_TEXT, text_area, font=HANGER_FONT, angles=(0,), max_em=40)
    # banner + knobs from z=-0.5 up to the heart's front face; back layer from -1 to exactly 0 (the heart's back face)
    hanger = extrude(banner, -0.5, TOP + 0.5) + extrude(back, -HANGER_BACK_T, HANGER_BACK_T)
    if btxt is not None:
        hanger = hanger + extrude(btxt, TOP - 0.01, TEXT_H + 0.01)
    to_trimesh(hanger).export(os.path.join(out, 'hanger_assembled.stl'))
    # print orientation: back layer on the plate, Basmala up
    to_trimesh(hanger.translate([0, 0, HANGER_BACK_T])).export(os.path.join(out, 'hanger.stl'))
    json.dump(dict(text_from_z=TOP), open(os.path.join(out, 'hanger_pose.json'), 'w'))
    print(f'  hanger.stl written ({hi_x-lo_x:.0f} x {HANGER_H+8:.0f} mm, basmala {bem:.1f} mm)')

    # ---- pieces
    report = []
    pieces = []
    for key, pk in pockets.items():
        num = SURAHS.index(key) + 1
        body, txt, em = names[key]
        solid = extrude(body, 0, PIECE_H)
        if txt is not None and not txt.is_empty:
            solid = solid + extrude(txt, PIECE_H - 0.01, TEXT_H + 0.01)
        if txt is not None and not txt.is_empty:
            hollow = txt.buffer(NAME_CLEAR, join_style=1, quad_segs=3).simplify(0.01).intersection(body.buffer(-0.4))
            solid = solid - extrude(hollow, -1, RECESS_DEPTH + 1)
        mesh = to_trimesh(solid)
        mesh.export(os.path.join(out, 'pieces', f'{num:03d}_{key}.stl'))
        pieces.append((num, key, body, txt, solid))
        report.append(dict(number=num, name=key, font_mm=round(em, 2),
                           width_mm=round(body.bounds[2] - body.bounds[0], 1),
                           height_mm=round(body.bounds[3] - body.bounds[1], 1)))
    report.sort(key=lambda r: r['number'])
    json.dump(report, open(os.path.join(out, 'pieces_report.json'), 'w'), ensure_ascii=False, indent=1)
    print(f'  {len(pieces)} pieces written; smallest font {min(r["font_mm"] for r in report):.1f} mm')

    # ---- pack pieces on plates (shelf packing of min-area rectangles)
    items = []
    for num, key, body, txt, solid in pieces:
        mrr = body.minimum_rotated_rectangle
        cs = list(mrr.exterior.coords)
        e = (cs[1][0] - cs[0][0], cs[1][1] - cs[0][1])
        ang = math.degrees(math.atan2(e[1], e[0]))
        rb = affinity.rotate(body, -ang, origin=(0, 0))
        b = rb.bounds
        w, h = b[2] - b[0], b[3] - b[1]
        if h > w:
            ang += 90; rb = affinity.rotate(body, -ang, origin=(0, 0)); b = rb.bounds; w, h = b[2] - b[0], b[3] - b[1]
        items.append(dict(num=num, solid=solid, ang=-ang, b=b, w=w, h=h, outline=rb))
    items.sort(key=lambda it: -it['h'])
    plates = [[]]; x = y = 0.0; shelf = 0.0
    for it in items:
        if x + it['w'] > PLATE:
            x = 0; y += shelf + PLATE_GAP; shelf = 0
        if y + it['h'] > PLATE:
            plates.append([]); x = y = shelf = 0.0
        tx, ty = x - it['b'][0] - PLATE / 2, y - it['b'][1] - PLATE / 2
        plates[-1].append(it['solid'].rotate([0, 0, it['ang']]).translate([tx, ty, 0]))
        x += it['w'] + PLATE_GAP; shelf = max(shelf, it['h'])
    for i, pl in enumerate(plates, 1):
        tm = trimesh.util.concatenate([to_trimesh(s) for s in pl])
        tm.export(os.path.join(out, f'pieces_plate_{i}.stl'))
    print(f'  {len(plates)} piece plates written')

    # ---- preview data
    json.dump(dict(outline=shapely.geometry.mapping(board_outline), banner=shapely.geometry.mapping(banner),
                   btext=shapely.geometry.mapping(btxt),
                   pockets={k: shapely.geometry.mapping(v) for k, v in pockets.items()},
                   text={p[1]: shapely.geometry.mapping(p[3]) for p in pieces if p[3] is not None}),
              open(os.path.join(out, 'preview.json'), 'w'), ensure_ascii=False)


if __name__ == '__main__':
    main()
