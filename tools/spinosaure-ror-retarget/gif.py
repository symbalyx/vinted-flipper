"""Rendu GIF plein, texture echantillonnee et eclairage directionnel.

Chaque face prend la couleur moyenne de son rectangle UV dans l atlas, puis un
lambert simple. Tri par profondeur (peintre) sur le centre de chaque face. Vue
orthographique, orientable, pour comparer deux versions cote a cote.
"""
import json, math, os, sys, base64, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fk as FK
from boite import coins, FACES
from PIL import Image, ImageDraw, ImageFont

LUM = (-0.40, 0.72, -0.57)
AMBIANT, DIFFUS = 0.52, 0.62


def charge_atlas(bb):
    src = bb['textures'][0]['source']
    im = Image.open(io.BytesIO(base64.b64decode(src.split(',', 1)[1]))).convert('RGB')
    return im, bb.get('resolution', {'width': im.size[0], 'height': im.size[1]})


_cache = {}


def couleur(im, res, uv, cle):
    if cle in _cache:
        return _cache[cle]
    W, H = im.size
    sx, sy = W / res['width'], H / res['height']
    x0, x1 = sorted((uv[0] * sx, uv[2] * sx))
    y0, y1 = sorted((uv[1] * sy, uv[3] * sy))
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(W, max(x0 + 1, int(x1))), min(H, max(y0 + 1, int(y1)))
    petit = im.crop((x0, y0, x1, y1)).resize((1, 1), Image.BOX)
    c = petit.getpixel((0, 0))
    _cache[cle] = c
    return c


def mat_vue(az, el):
    a, e = math.radians(az), math.radians(el)
    ca, sa, ce, se = math.cos(a), math.sin(a), math.cos(e), math.sin(e)
    # rotation Y puis X
    return [[ca, 0, -sa], [-sa * se, ce, -ca * se], [sa * ce, se, ca * ce]]


def applique(M, v):
    return [sum(M[r][k] * v[k] for k in range(3)) for r in range(3)]


def etendue(rig, P, az, el):
    """Boite englobante projetee, pour cadrer automatiquement."""
    V = mat_vue(az, el)
    xs, ys = [], []
    for u, cl in rig.cubes.items():
        nm = rig.groups[u]['name']
        if nm not in P:
            continue
        M, off, O = P[nm]
        for cu in cl:
            e = rig.elems[cu]
            R = FK.mat_rot(*e.get('rotation', [0, 0, 0]))
            eo = e.get('origin', O)
            for p in coins(e['from'], e['to']):
                q = FK.apply(R, [p[x] - eo[x] for x in range(3)])
                q = [q[x] + eo[x] for x in range(3)]
                w = FK.apply(M, [q[x] - O[x] for x in range(3)])
                v = applique(V, [w[x] + off[x] for x in range(3)])
                xs.append(v[0]); ys.append(v[1])
    return min(xs), max(xs), min(ys), max(ys)


def cadre(rig, poses, taille, az, el, marge=0.90, bas=0.0):
    """Echelle et centre qui contiennent TOUTES les poses fournies."""
    b = [etendue(rig, P, az, el) for P in poses]
    x0 = min(v[0] for v in b); x1 = max(v[1] for v in b)
    y0 = min(v[2] for v in b); y1 = max(v[3] for v in b)
    sc = min(taille[0] * marge / max(1e-6, x1 - x0),
             (taille[1] - 44) * marge / max(1e-6, y1 - y0))
    cx = taille[0] / 2 - (x0 + x1) / 2 * sc
    cy = (taille[1] + 30) / 2 + (y0 + y1) / 2 * sc + bas
    return sc, cx, cy


def rendu(rig, im, res, P, taille, sc, cx, cy, az, el, fond=(20, 21, 27), surligne=None):
    V = mat_vue(az, el)
    img = Image.new('RGB', taille, fond)
    d = ImageDraw.Draw(img)
    quads = []
    for u, cl in rig.cubes.items():
        nm = rig.groups[u]['name']
        if nm not in P:
            continue
        M, off, O = P[nm]
        for cu in cl:
            e = rig.elems[cu]
            if not e.get('visibility', True):
                continue
            R = FK.mat_rot(*e.get('rotation', [0, 0, 0]))
            eo = e.get('origin', O)
            infl = e.get('inflate', 0) or 0
            f = [e['from'][k] - infl for k in range(3)]
            t = [e['to'][k] + infl for k in range(3)]
            monde = []
            for p in coins(f, t):
                q = FK.apply(R, [p[x] - eo[x] for x in range(3)])
                q = [q[x] + eo[x] for x in range(3)]
                w = FK.apply(M, [q[x] - O[x] for x in range(3)])
                monde.append([w[x] + off[x] for x in range(3)])
            for nomf, (idx, nloc, _axes) in FACES.items():
                fd = e.get('faces', {}).get(nomf)
                if not fd or fd.get('texture') is None or not fd.get('uv'):
                    continue
                pts = [monde[i] for i in idx]
                # normale monde, via la rotation du cube puis celle de l os
                n = FK.apply(M, FK.apply(R, list(nloc)))
                ln = math.sqrt(sum(x * x for x in n)) or 1
                n = [x / ln for x in n]
                vue = [applique(V, p) for p in pts]
                if sum(applique(V, n)[2] for _ in (0,)) > 0:      # face arriere
                    continue
                prof = sum(p[2] for p in vue) / 4
                lam = max(0.0, sum(n[k] * LUM[k] for k in range(3)))
                k = AMBIANT + DIFFUS * lam
                c = couleur(im, res, fd['uv'], (id(e), nomf))
                if surligne and (e['uuid'], nomf) in surligne:
                    c = (255, 40, 40)
                quads.append((prof, [(cx + p[0] * sc, cy - p[1] * sc) for p in vue],
                              tuple(min(255, int(x * k)) for x in c)))
    quads.sort(key=lambda q: q[0])
    for _, poly, col in quads:
        d.polygon(poly, fill=col)
    return img
