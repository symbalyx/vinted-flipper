"""Gros plan comparatif sur une zone du modele, en pose de repos. Cadrage automatique."""
import json, sys
sys.path.insert(0, 'tools')
import fk as FK
from PIL import Image, ImageDraw

EDGES = [(0, 1), (1, 3), (3, 2), (2, 0), (4, 5), (5, 7), (7, 6), (6, 4),
         (0, 4), (1, 5), (2, 6), (3, 7)]


def collect(path, bones):
    bb = json.load(open(path))
    rig = FK.Rig(bb)
    P = rig.pose(lambda b, c: [1., 1., 1.] if c == 'scale' else [0., 0., 0.])
    out = []
    for u, cl in rig.cubes.items():
        nm = rig.groups[u]['name']
        if nm not in P or nm not in bones:
            continue
        M, off, O = P[nm]
        for cu in cl:
            e = rig.elems[cu]
            f, t = e['from'], e['to']
            pts = []
            for i in (0, 1):
                for j in (0, 1):
                    for k in (0, 1):
                        p = [f[0] if i == 0 else t[0], f[1] if j == 0 else t[1],
                             f[2] if k == 0 else t[2]]
                        pts.append([sum(M[r][c] * (p[c] - O[c]) for c in range(3)) + off[r]
                                    for r in range(3)])
            kind = 'neuf' if e['name'][:4] in ('V71_', 'V72_') else (
                'griffe' if 'griffe' in e['name'] else 'base')
            out.append((kind, pts))
    return out


COL = {'neuf': (255, 170, 40), 'griffe': (70, 220, 220), 'base': (115, 115, 130)}
WID = {'neuf': 2, 'griffe': 2, 'base': 1}


def draw(sets, vue, W, H, titles, path, note):
    # profil : (z, y) | face : (x, y) | dessus : (x, z)
    ax, vx = (2, 1) if vue == 'profil' else ((0, 1) if vue == 'face' else (0, 2))
    allp = [p for s in sets for _, pts in s for p in pts]
    a0 = min(p[ax] for p in allp); a1 = max(p[ax] for p in allp)
    b0 = min(p[vx] for p in allp); b1 = max(p[vx] for p in allp)
    m = 26
    sc = min((W - 2 * m) / max(1e-6, a1 - a0), (H - 2 * m) / max(1e-6, b1 - b0))
    ca, cb = (a0 + a1) / 2, (b0 + b1) / 2
    sheet = Image.new('RGB', (W * len(sets), H), (18, 18, 24))
    for k, s in enumerate(sets):
        img = Image.new('RGB', (W, H), (18, 18, 24) if k % 2 == 0 else (26, 26, 34))
        d = ImageDraw.Draw(img)
        for kind, pts in sorted(s, key=lambda t: t[0] == 'neuf'):
            pr = [((p[ax] - ca) * sc + W / 2, H / 2 - (p[vx] - cb) * sc) for p in pts]
            for i, j in EDGES:
                d.line([pr[i], pr[j]], fill=COL[kind], width=WID[kind])
        d.text((8, 8), titles[k], fill=(225, 225, 235))
        sheet.paste(img, (W * k, 0))
    ImageDraw.Draw(sheet).text((8, H - 16), note, fill=(150, 150, 165))
    sheet.save(path)
    return path


if __name__ == '__main__':
    bones = {'forearm_left', 'hand_left',
             'finger_left_0', 'finger_left_1', 'finger_left_2'}
    before, after, out = sys.argv[1], sys.argv[2], sys.argv[3]
    sb, sa = collect(before, bones), collect(after, bones)
    draw([sb, sa, sb, sa], 'profil', 400, 430,
         ['avant - profil', 'apres - profil', 'avant - profil', 'apres - profil'],
         out.replace('.png', '_profil.png'),
         'orange = ajout (palmure, membrane) | cyan = griffes | gris = existant')
    draw([sb, sa], 'profil', 460, 470, ['avant - vue de profil', 'apres - vue de profil'],
         out.replace('.png', '_p.png'),
         'orange = palmure et membrane ajoutees | cyan = griffes | gris = existant')
    draw([sb, sa], 'face', 460, 470, ['avant - vue de face', 'apres - vue de face'],
         out.replace('.png', '_f.png'),
         'orange = palmure et membrane ajoutees | cyan = griffes | gris = existant')
    print('ecrit', out.replace('.png', '_p.png'), 'et', out.replace('.png', '_f.png'))
