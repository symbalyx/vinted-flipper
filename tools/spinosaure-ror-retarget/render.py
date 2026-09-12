"""Rendu PNG (vue de profil) de poses cles, pour controler visuellement le resultat."""
import json, sys
sys.path.insert(0, 'tools')
import fk as FK
from PIL import Image, ImageDraw

bb = json.load(open(sys.argv[1]))
rig = FK.Rig(bb)
EDGES = [(0, 1), (1, 3), (3, 2), (2, 0), (4, 5), (5, 7), (7, 6), (6, 4),
         (0, 4), (1, 5), (2, 6), (3, 7)]

COLOR = {'head': (235, 90, 70), 'jaw': (250, 130, 90), 'throat': (0, 210, 210),
         'sail': (150, 110, 240), 'tongue': (250, 120, 190)}
for b in ('upper_arm_left', 'forearm_left', 'hand_left',
          'finger_left_0', 'finger_left_1', 'finger_left_2'):
    COLOR[b] = (255, 175, 40)
for b in ('upper_arm_right', 'forearm_right', 'hand_right',
          'finger_right_0', 'finger_right_1', 'finger_right_2'):
    COLOR[b] = (190, 120, 20)
for b in ('thigh_left', 'shin_left', 'foot_left'):
    COLOR[b] = (90, 200, 120)
for b in ('thigh_right', 'shin_right', 'foot_right'):
    COLOR[b] = (55, 140, 85)
GREY = (130, 130, 145)


def tracks_of(a):
    t = {}
    for u, an in a['animators'].items():
        d = {}
        for k in an['keyframes']:
            d.setdefault(k['channel'], []).append(
                (k['time'], [float(k['data_points'][0].get(q, 0) or 0) for q in 'xyz']))
        for c in d:
            d[c].sort()
        t[an['name']] = d
    return t


def lerp(pts, t):
    if t <= pts[0][0]:
        return pts[0][1]
    if t >= pts[-1][0]:
        return pts[-1][1]
    for i in range(len(pts) - 1):
        if pts[i + 1][0] >= t:
            a, b = pts[i], pts[i + 1]
            f = (t - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0
            return [a[1][k] + (b[1][k] - a[1][k]) * f for k in range(3)]
    return pts[-1][1]


def draw(d, anim, t, ox, oy, sc):
    T = tracks_of(anim)
    P = rig.pose(lambda b, c: lerp(T[b][c], t) if b in T and c in T[b]
                 else ([1., 1., 1.] if c == 'scale' else [0., 0., 0.]))
    later = []
    for u, cl in rig.cubes.items():
        nm = rig.groups[u]['name']
        if nm not in P:
            continue
        M, off, O = P[nm]
        col = COLOR.get(nm, GREY)
        for cu in cl:
            e = rig.elems[cu]
            f, to = e['from'], e['to']
            pts = []
            for i in (0, 1):
                for j in (0, 1):
                    for k in (0, 1):
                        p = [f[0] if i == 0 else to[0], f[1] if j == 0 else to[1],
                             f[2] if k == 0 else to[2]]
                        q = [sum(M[r][c2] * (p[c2] - O[c2]) for c2 in range(3)) + off[r]
                             for r in range(3)]
                        pts.append((ox + q[2] * sc, oy - q[1] * sc))
            seg = [(pts[a], pts[b]) for a, b in EDGES]
            (later if nm in COLOR else d).__class__  # noqa
            if nm in COLOR:
                later.append((seg, col))
            else:
                for a, b in seg:
                    d.line([a, b], fill=col, width=1)
    for seg, col in later:
        for a, b in seg:
            d.line([a, b], fill=col, width=2)


name, times, path = sys.argv[2], [float(x) for x in sys.argv[3].split(',')], sys.argv[4]
anim = [a for a in bb['animations'] if a['name'].endswith(name)][0]
sc, CW, CH = 1.0, 400, 330
img = Image.new('RGB', (CW * len(times), CH), (18, 18, 24))
d = ImageDraw.Draw(img)
for i, t in enumerate(times):
    if i % 2:
        d.rectangle([CW * i, 0, CW * (i + 1), CH], fill=(26, 26, 34))
    ox, oy = CW * i + 190, 245
    d.line([(CW * i + 4, oy + 62.76 * sc), (CW * (i + 1) - 4, oy + 62.76 * sc)],
           fill=(70, 120, 70), width=1)
    draw(d, anim, t, ox, oy, sc)
    d.text((CW * i + 8, 8), 't=%.2fs' % t, fill=(205, 205, 215))
d.text((8, CH - 14), '%s | rouge tete/machoire, cyan gorge, violet voile, orange bras+griffes, vert pattes'
       % anim['name'], fill=(140, 140, 155))
img.save(path)
print('ecrit', path, img.size)
