"""Rendu GIF plein, texture echantillonnee et eclairage directionnel.

Chaque face prend la couleur moyenne de son rectangle UV dans l atlas, puis un
lambert simple. Tri par profondeur (peintre) sur le centre de chaque face. Vue
orthographique, orientable, pour comparer deux versions cote a cote.
"""
import json, math, os, sys, base64, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fk as FK
from boite import coins, FACES, COINS_UV
from PIL import Image, ImageDraw, ImageFont

LUM = (-0.40, 0.72, -0.57)
AMBIANT, DIFFUS = 0.62, 0.48      # proche de l apercu Blockbench


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
    # profondeur croissante = plus LOIN : on peint du plus lointain au plus proche
    quads.sort(key=lambda q: -q[0])
    for _, poly, col in quads:
        d.polygon(poly, fill=col)
    return img


def _coeffs(ecran, source):
    """Coefficients PIL PERSPECTIVE : point ecran -> point texture."""
    import numpy as np
    A, B = [], []
    for (x, y), (u, v) in zip(ecran, source):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return list(np.linalg.solve(np.array(A, float), np.array(B, float)))


def rendu_texture(rig, im, res, P, taille, sc, cx, cy, az, el, fond=(20, 21, 27), surligne=None):
    """Rendu avec placage de texture reel : chaque face est deformee depuis l atlas.
    Le rendu par couleur moyenne ne peut pas juger une texture (grain et motifs
    disparaissent) ; celui-ci montre les pixels."""
    V = mat_vue(az, el)
    img = Image.new('RGB', taille, fond)
    W, H = im.size
    sx, sy = W / res['width'], H / res['height']
    faces = []
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
            g = e.get('inflate', 0) or 0
            f = [e['from'][k] - g for k in range(3)]
            t = [e['to'][k] + g for k in range(3)]
            monde = []
            for p in coins(f, t):
                q = FK.apply(R, [p[x] - eo[x] for x in range(3)])
                q = [q[x] + eo[x] for x in range(3)]
                w = FK.apply(M, [q[x] - O[x] for x in range(3)])
                monde.append([w[x] + off[x] for x in range(3)])
            for nomf, (idx, nloc, _a) in FACES.items():
                fd = e.get('faces', {}).get(nomf)
                if not fd or fd.get('texture') is None or not fd.get('uv'):
                    continue
                n = FK.apply(M, FK.apply(R, list(nloc)))
                if applique(V, n)[2] > 0:
                    continue
                pts = [monde[i] for i in COINS_UV[nomf]]
                vue = [applique(V, p) for p in pts]
                prof = sum(p[2] for p in vue) / 4
                lam = max(0.0, sum(n[k] * LUM[k] for k in range(3)))
                k = AMBIANT + DIFFUS * lam
                ecr = [(cx + p[0] * sc, cy - p[1] * sc) for p in vue]
                hl = bool(surligne and (e['uuid'], nomf) in surligne)
                faces.append((prof, ecr, fd['uv'], k, hl))
    faces.sort(key=lambda q: -q[0])
    for prof, ecr, uv, k, hl in faces:
        xs = [p[0] for p in ecr]; ys = [p[1] for p in ecr]
        x0, y0 = int(max(0, min(xs))), int(max(0, min(ys)))
        x1, y1 = int(min(taille[0], max(xs) + 1)), int(min(taille[1], max(ys) + 1))
        if x1 - x0 < 1 or y1 - y0 < 1:
            continue
        masque = Image.new('L', (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(masque).polygon([(x - x0, y - y0) for x, y in ecr], fill=255)
        if hl:
            img.paste((255, 40, 40), (x0, y0), masque)
            continue
        src = [(uv[0] * sx, uv[1] * sy), (uv[2] * sx, uv[1] * sy),
               (uv[2] * sx, uv[3] * sy), (uv[0] * sx, uv[3] * sy)]
        try:
            co = _coeffs([(x - x0, y - y0) for x, y in ecr], src)
        except Exception:
            continue
        morceau = im.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, co, Image.NEAREST)
        if k < 0.999:
            morceau = morceau.point(lambda c, k=k: int(c * k))
        img.paste(morceau, (x0, y0), masque)
    return img


_ATLAS_NP = {}


def rendu_z(rig, im, res, P, taille, sc, cx, cy, az, el, fond=(20, 21, 27), surligne=None):
    """Rendu texture avec TAMPON DE PROFONDEUR (numpy), comme Blockbench.

    Le rendu par ordre de profondeur (peintre) laissait passer les faces INTERNES
    (entre deux plaques de voile qui se touchent, cachees dans Blockbench) par-dessus
    les faces visibles : fausses rayures sombres. En vue orthographique, profondeur et
    UV sont affines sur chaque face : on les interpole exactement, pixel par pixel.
    """
    import numpy as np
    cle = id(im)
    if cle not in _ATLAS_NP:
        _ATLAS_NP[cle] = np.asarray(im.convert('RGB'))
    tex = _ATLAS_NP[cle]
    Ht, Wt = tex.shape[:2]
    sx, sy = Wt / res['width'], Ht / res['height']
    V = mat_vue(az, el)
    Wd, Hd = taille
    img = np.empty((Hd, Wd, 3), dtype=np.uint8); img[:] = fond
    zb = np.full((Hd, Wd), 1e18)          # profondeur croissante = plus loin
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
            g = e.get('inflate', 0) or 0
            f = [e['from'][k] - g for k in range(3)]
            t = [e['to'][k] + g for k in range(3)]
            monde = []
            for p in coins(f, t):
                q = FK.apply(R, [p[x] - eo[x] for x in range(3)])
                q = [q[x] + eo[x] for x in range(3)]
                w = FK.apply(M, [q[x] - O[x] for x in range(3)])
                monde.append([w[x] + off[x] for x in range(3)])
            for nomf, (idx, nloc, _a) in FACES.items():
                fd = e.get('faces', {}).get(nomf)
                if not fd or fd.get('texture') is None or not fd.get('uv'):
                    continue
                n = FK.apply(M, FK.apply(R, list(nloc)))
                if applique(V, n)[2] > 0:
                    continue
                vue = [applique(V, monde[i]) for i in COINS_UV[nomf]]
                S = [(cx + p[0] * sc, cy - p[1] * sc, p[2]) for p in vue]
                ax, ay = S[1][0] - S[0][0], S[1][1] - S[0][1]
                bx, by = S[3][0] - S[0][0], S[3][1] - S[0][1]
                det = ax * by - ay * bx
                if abs(det) < 1e-9:
                    continue
                xs = [p[0] for p in S]; ys = [p[1] for p in S]
                x0, x1 = max(0, int(min(xs))), min(Wd, int(max(xs)) + 2)
                y0, y1 = max(0, int(min(ys))), min(Hd, int(max(ys)) + 2)
                if x1 <= x0 or y1 <= y0:
                    continue
                gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
                dx, dy = gx - S[0][0], gy - S[0][1]
                s_ = (dx * by - dy * bx) / det
                t_ = (ax * dy - ay * dx) / det
                dedans = (s_ >= 0) & (s_ <= 1) & (t_ >= 0) & (t_ <= 1)
                if not dedans.any():
                    continue
                z = S[0][2] + s_ * (S[1][2] - S[0][2]) + t_ * (S[3][2] - S[0][2])
                zone = zb[y0:y1, x0:x1]
                ok = dedans & (z < zone)
                if not ok.any():
                    continue
                uv = fd['uv']
                lam = max(0.0, sum(n[k] * LUM[k] for k in range(3)))
                kk = AMBIANT + DIFFUS * lam
                if surligne and (e['uuid'], nomf) in surligne:
                    col = np.array([255, 40, 40], dtype=float)
                    pix = np.broadcast_to(col, ok.shape + (3,))
                else:
                    uu = uv[0] + s_ * (uv[2] - uv[0]); vv = uv[1] + t_ * (uv[3] - uv[1])
                    iu = np.clip((uu * sx).astype(int), 0, Wt - 1)
                    iv = np.clip((vv * sy).astype(int), 0, Ht - 1)
                    pix = tex[iv, iu].astype(float) * kk
                zone[ok] = z[ok]
                sub = img[y0:y1, x0:x1]
                sub[ok] = np.clip(pix[ok], 0, 255).astype(np.uint8)
    return Image.fromarray(img)
