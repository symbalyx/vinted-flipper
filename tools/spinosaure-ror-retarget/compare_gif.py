"""GIF comparatif : meme animation, deux versions du modele, cote a cote."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fk as FK, gif
from PIL import Image, ImageDraw, ImageFont

try:
    F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 17)
    FP = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
except Exception:
    F = FP = ImageFont.load_default()


def pistes(a):
    t = {}
    for u, an in a['animators'].items():
        d = {}
        for kf in an['keyframes']:
            d.setdefault(kf['channel'], []).append(
                (kf['time'], [float(kf['data_points'][0].get(q, 0) or 0) for q in 'xyz']))
        for c in d:
            d[c].sort()
        t[an['name']] = d
    return t


def lp(p, u):
    if u <= p[0][0]:
        return p[0][1]
    if u >= p[-1][0]:
        return p[-1][1]
    for i in range(len(p) - 1):
        if p[i + 1][0] >= u:
            x, y = p[i], p[i + 1]
            f = (u - x[0]) / (y[0] - x[0]) if y[0] > x[0] else 0
            return [x[1][k] + (y[1][k] - x[1][k]) * f for k in range(3)]
    return p[-1][1]


def prepare(path):
    bb = json.load(open(path))
    rig = FK.Rig(bb)
    im, res = gif.charge_atlas(bb)
    return bb, rig, im, res, {a['name'].split('.')[-1]: a for a in bb['animations']}


def bande(cote, anim, rig, im, res, nom, sous, u, sc, cx, cy, az, el, fond,
          reperes=False, sol=None, surligne=None):
    T = pistes(anim)
    P = rig.pose(lambda b, c: (lp(T[b][c], u) if b in T and c in T.get(b, {})
                               else ([1., 1., 1.] if c == 'scale' else [0., 0., 0.])))
    img = gif.rendu(rig, im, res, P, cote, sc, cx, cy, az, el, fond, surligne)
    d = ImageDraw.Draw(img)
    if reperes:
        # aplomb et ligne de sol : sans eux, un roulis de quelques degres ne se voit pas
        x = cote[0] / 2
        for y in range(34, cote[1], 9):
            d.line([(x, y), (x, y + 4)], fill=(72, 76, 92), width=1)
        if sol is not None:
            ys = cy - sol * sc
            d.line([(6, ys), (cote[0] - 6, ys)], fill=(78, 96, 78), width=1)
    d.rectangle([0, 0, cote[0], 30], fill=(0, 0, 0))
    d.text((12, 6), nom, font=F, fill=(240, 240, 245))
    if sous:
        d.text((12, cote[1] - 24), sous, font=FP, fill=(150, 152, 165))
    return img


def poses_de(anim, rig, n=14):
    T = pistes(anim)
    out = []
    for i in range(n):
        u = anim['length'] * i / max(1, n - 1)
        out.append(rig.pose(lambda b, c: (lp(T[b][c], u) if b in T and c in T.get(b, {})
                                          else ([1., 1., 1.] if c == 'scale' else [0., 0., 0.]))))
    return out


def sol_de(rig):
    return rig.lowest(rig.pose(lambda b, c: [1., 1., 1.] if c == 'scale' else [0., 0., 0.]))


def fabrique(sortie, gauche, droite, nom_anim, titre_g, titre_d, sous_g='', sous_d='',
             n=48, cote=(430, 400), az=26, el=11, fond=(20, 21, 27), duree=70,
             anim_d=None, reperes=False, boucle=False, L=None):
    A = prepare(gauche)
    B = prepare(droite) if droite != gauche else A
    ag, ad = A[4][nom_anim], B[4][anim_d or nom_anim]
    L = L or max(ag['length'], ad['length'])
    sc, cx, cy = gif.cadre(A[1], poses_de(ag, A[1]) + poses_de(ad, B[1]), cote, az, el)
    tg = (lambda u: u % ag['length']) if boucle else (lambda u: min(u, ag['length']))
    td = (lambda u: u % ad['length']) if boucle else (lambda u: min(u, ad['length']))
    frames = []
    for i in range(n):
        u = L * i / n
        g = bande(cote, ag, A[1], A[2], A[3], titre_g, sous_g, tg(u),
                  sc, cx, cy, az, el, fond, reperes, sol_de(A[1]) if reperes else None)
        dr = bande(cote, ad, B[1], B[2], B[3], titre_d, sous_d, td(u),
                   sc, cx, cy, az, el, fond, reperes, sol_de(B[1]) if reperes else None)
        img = Image.new('RGB', (cote[0] * 2 + 4, cote[1]), (60, 62, 72))
        img.paste(g, (0, 0))
        img.paste(dr, (cote[0] + 4, 0))
        frames.append(img.convert('P', palette=Image.ADAPTIVE, colors=200))
    frames[0].save(sortie, save_all=True, append_images=frames[1:],
                   duration=duree, loop=0, optimize=True, disposal=2)
    print('ecrit %s  %d images  %.1f Mo' % (sortie, n, os.path.getsize(sortie) / 1e6))


def solo(sortie, modele, nom_anim, titre, sous='', n=54, cote=(560, 440),
         az=26, el=11, duree=70):
    A = prepare(modele)
    a = A[4][nom_anim]
    sc, cx, cy = gif.cadre(A[1], poses_de(a, A[1], 16), cote, az, el)
    frames = []
    for i in range(n):
        u = a['length'] * i / n
        frames.append(bande(cote, a, A[1], A[2], A[3], titre, sous, u, sc, cx, cy, az, el,
                            (20, 21, 27)).convert('P', palette=Image.ADAPTIVE, colors=220))
    frames[0].save(sortie, save_all=True, append_images=frames[1:],
                   duration=duree, loop=0, optimize=True, disposal=2)
    print('ecrit %s  %d images  %.1f Mo' % (sortie, n, os.path.getsize(sortie) / 1e6))


def tourne(sortie, gauche, droite, titre_g, titre_d, sous_g='', sous_d='',
           n=48, cote=(430, 400), el=12, duree=75, pose='pose_reference', surl_g=None, surl_d=None):
    """Table tournante comparative : meme pose, deux geometries, 360 degres."""
    A = prepare(gauche)
    B = prepare(droite) if droite != gauche else A
    ag = A[4].get(pose) or list(A[4].values())[0]
    ad = B[4].get(pose) or list(B[4].values())[0]
    # cadrage commun, fige sur l azimut le plus large
    sc, cx, cy = gif.cadre(A[1], poses_de(ag, A[1], 3) + poses_de(ad, B[1], 3), cote, 90, el)
    frames = []
    for i in range(n):
        az = 360.0 * i / n
        g = bande(cote, ag, A[1], A[2], A[3], titre_g, sous_g, 0.0, sc, cx, cy, az, el,
                  (20, 21, 27), surligne=surl_g)
        dr = bande(cote, ad, B[1], B[2], B[3], titre_d, sous_d, 0.0, sc, cx, cy, az, el,
                   (20, 21, 27), surligne=surl_d)
        img = Image.new('RGB', (cote[0] * 2 + 4, cote[1]), (60, 62, 72))
        img.paste(g, (0, 0)); img.paste(dr, (cote[0] + 4, 0))
        frames.append(img.convert('P', palette=Image.ADAPTIVE, colors=200))
    frames[0].save(sortie, save_all=True, append_images=frames[1:],
                   duration=duree, loop=0, optimize=True, disposal=2)
    print('ecrit %s  %d images  %.1f Mo' % (sortie, n, os.path.getsize(sortie) / 1e6))
