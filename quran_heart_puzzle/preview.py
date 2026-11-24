"""Render a 2D preview of the assembled puzzle (pockets + names) to preview_assembled.png."""
import json, os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import shape
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, 'preview.json'), encoding='utf-8'))

def draw(ax, g, **kw):
    gs = g.geoms if hasattr(g, 'geoms') else [g]
    for p in gs:
        if p.is_empty: continue
        x, y = p.exterior.xy; ax.fill(x, y, **kw)
        for h in p.interiors:
            x, y = h.xy; ax.fill(x, y, color='white', lw=0)

fig, ax = plt.subplots(figsize=(9, 12))
draw(ax, shape(d['outline']), color='#3a3a3a')
if 'banner' in d:
    draw(ax, shape(d['banner']), color='#6b7d5f')
    draw(ax, shape(d['btext']), color='#f3e9dc')
for k, p in d['pockets'].items():
    draw(ax, shape(p), color='#f3e9dc')
for k, t in d['text'].items():
    draw(ax, shape(t), color='#b0465b')
ax.set_aspect('equal'); ax.axis('off')
fig.savefig(os.path.join(HERE, 'images', 'preview_assembled.png'), dpi=160, bbox_inches='tight')

