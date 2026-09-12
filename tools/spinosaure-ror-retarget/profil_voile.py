"""Compare des profils de voile en vue de profil, sans rien modifier du fichier."""
import json, math, sys
sys.path.insert(0, 'tools')
from PIL import Image, ImageDraw

bb = json.load(open('modelzip/RIVIERE_70_ADAPTATION_ROR(1).bbmodel'))
gm = {g['uuid']: g for g in bb['groups']}
em = {e['uuid']: e for e in bb['elements']}


def find(n, name):
    if isinstance(n, str):
        return None
    if gm.get(n['uuid'], {}).get('name') == name:
        return n
    for c in n.get('children', []):
        r = find(c, name)
        if r:
            return r


root = bb['outliner'][0]
sail = find(root, 'sail')
slabs, bords = [], []
for c in sail['children']:
    if not isinstance(c, str):
        continue
    e = em[c]
    (bords if 'bord' in e['name'] else slabs).append(e)
slabs.sort(key=lambda e: e['from'][2])
bords.sort(key=lambda e: e['from'][2])
BASE = slabs[0]['from'][1]
CUR = [round(e['to'][1] - BASE, 1) for e in slabs]
Z = [(e['from'][2], e['to'][2]) for e in slabs]


def ellipse(hmax, hend, n=12):
    c = (n - 1) / 2.0
    k = hend / hmax
    R = c / math.sqrt(max(1e-6, 1 - k * k))
    return [round(hmax * math.sqrt(max(0.0, 1 - ((i - c) / R) ** 2)), 1) for i in range(n)]


def asym(hmax, hfront, hback, peak=4.5, n=12):
    out = []
    for i in range(n):
        if i <= peak:
            d = (peak - i) / peak
            out.append(round(hmax - (hmax - hfront) * d ** 1.7, 1))
        else:
            d = (i - peak) / (n - 1 - peak)
            out.append(round(hmax - (hmax - hback) * d ** 1.5, 1))
    return out


PROFILS = {
    'actuel (deux bosses)': CUR,
    'A  dome conservateur': ellipse(63.5, 40.0),
    'B  dome plus haut': ellipse(71.8, 42.0),
    'C  dome asymetrique': asym(68.0, 38.0, 34.0),
}

# corps en fond, pour juger la voile en contexte
body_pts = []
for e in bb['elements']:
    if e in slabs or e in bords:
        continue
    f, t = e['from'], e['to']
    body_pts.append((f[2], t[2], f[1], t[1]))

CW, CH, sc = 470, 300, 1.05
ox, oy = 150, 250
img = Image.new('RGB', (CW * len(PROFILS), CH), (18, 18, 24))
d = ImageDraw.Draw(img)
for k, (name, prof) in enumerate(PROFILS.items()):
    X = CW * k
    if k % 2:
        d.rectangle([X, 0, X + CW, CH], fill=(26, 26, 34))
    for z0, z1, y0, y1 in body_pts:
        d.rectangle([X + ox + z0 * sc, oy - y1 * sc, X + ox + z1 * sc, oy - y0 * sc],
                    outline=(58, 58, 70))
    for i, (z0, z1) in enumerate(Z):
        h = prof[i]
        top = BASE + h
        d.rectangle([X + ox + z0 * sc, oy - top * sc, X + ox + z1 * sc, oy - BASE * sc],
                    fill=(150, 112, 40), outline=(90, 66, 22))
        d.rectangle([X + ox + z0 * sc, oy - top * sc, X + ox + z1 * sc, oy - (top - 1) * sc],
                    fill=(196, 74, 56))
    d.text((X + 10, 8), name, fill=(220, 220, 230))
    d.text((X + 10, 24), 'max %.1f  avant %.1f  arriere %.1f' % (max(prof), prof[0], prof[-1]),
           fill=(150, 150, 165))
    d.text((X + 10, CH - 16), ' '.join('%.0f' % v for v in prof), fill=(140, 140, 155))
d.text((8, CH - 32), 'vue de profil, museau a gauche | plafond texture disponible : 83 u',
       fill=(120, 120, 135))
img.save('profils_voile.png')
print('profils :')
for n, p in PROFILS.items():
    print('  %-22s %s' % (n, p))
print('ecrit profils_voile.png', img.size)
