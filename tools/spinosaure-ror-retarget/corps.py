"""Silhouette du corps rapprochee de la reference (capture 2), tete conservee.

Mesure de l existant : la queue s affinait vite (hauteur 28 -> 9, largeur 27 -> 8) et
plongeait (ligne centrale de y 72 a 39, 33 unites de chute). La reference a une queue
longue, droite, presque horizontale, qui prolonge la ligne du dos et reste epaisse
jusqu au bout. Les pattes arriere de la reference sont aussi plus massives.

Seule la geometrie change : les os et leurs pivots suivent, les animations (qui ne
font que tourner les os) restent valides. Chaque segment de queue tourne autour de
son propre centre, on peut donc le redresser, l epaissir et le deplacer sans effet
de bord.
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from boite import FACES

# segment k : centre z garde, nouveau centre y, nouvelle hauteur (axe local Z du cube),
# nouvelle largeur (X). Chute totale 10 unites au lieu de 33, conicite douce.
QUEUE_Y = [72.0, 71.0, 69.5, 67.5, 65.0, 62.0]
QUEUE_H = [28.0, 27.0, 25.5, 23.5, 21.0, 18.0]
QUEUE_W = [27.0, 24.5, 22.0, 19.0, 16.0, 13.0]
QUEUE_ROT = -86.0              # 4 degres de chute par segment, au lieu de 5 a 20
EPAIS_PATTE = 1.15              # section des cuisses, genoux et tibias ; longueur inchangee


def _interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0] + (ys[1] - ys[0]) * (x - xs[0]) / (xs[1] - xs[0])
    if x >= xs[-1]:
        return ys[-1] + (ys[-1] - ys[-2]) * (x - xs[-1]) / (xs[-1] - xs[-2])
    for i in range(len(xs) - 1):
        if xs[i + 1] >= x:
            f = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + (ys[i + 1] - ys[i]) * f


NON_PEAU = ('V70_dent', 'V46_griffe_pied', 'V70_ROR_griffe', 'V70_paupiere', 'V70_langue',
            'V70_palais', 'V70_plancher', 'V69_voile', 'V69_bord_voile', 'V70_arcade')


def _rect(uv):
    return (min(uv[0], uv[2]), min(uv[1], uv[3]), max(uv[0], uv[2]), max(uv[1], uv[3]))


def _chevauche(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]) > 0.5 and min(a[3], b[3]) - max(a[1], b[1]) > 0.5


def garde_densite(bb, e, avant, apres, interdits, res):
    """Agrandit les rectangles UV d un cube redimensionne, pour garder ses pixels par
    unite : sans cela la queue, deux fois plus haute au bout, montrerait un grain etire
    deux fois. L auteur fait deja chevaucher librement les zones de peau (tout y est du
    bruit brun), on peut donc s etendre sur les voisines -- mais jamais sur la voile, les
    dents, la gueule ou les yeux. En cas de conflit on etend dans l autre sens."""
    faits = 0
    for fn, fd in e['faces'].items():
        uv = fd.get('uv')
        if not uv:
            continue
        au, av = FACES[fn][2]
        ku = apres[au] / avant[au] if avant[au] else 1.0
        kv = apres[av] / avant[av] if avant[av] else 1.0
        if abs(ku - 1) < 1e-6 and abs(kv - 1) < 1e-6:
            continue
        for sens in (1, -1):
            n = list(uv)
            if sens == 1:
                n[2] = uv[0] + (uv[2] - uv[0]) * ku
                n[3] = uv[1] + (uv[3] - uv[1]) * kv
            else:
                n[0] = uv[2] - (uv[2] - uv[0]) * ku
                n[1] = uv[3] - (uv[3] - uv[1]) * kv
            r = _rect(n)
            dedans = r[0] >= 0 and r[1] >= 0 and r[2] <= res[0] and r[3] <= res[1]
            if dedans and not any(_chevauche(r, x) for x in interdits):
                fd['uv'] = [round(x, 3) for x in n]
                faits += 1
                break
        else:
            print('   ATTENTION : %s %s garde son rectangle (aucune extension sure)' % (e['name'], fn))
    return faits


def remodele(bb):
    res = (bb.get('resolution', {}).get('width', 4096), bb.get('resolution', {}).get('height', 4096))
    interdits = [_rect(fd['uv']) for x in bb['elements'] if x['name'].startswith(NON_PEAU)
                 for fd in x['faces'].values() if fd.get('uv')]
    n_uv = 0
    E = {e['name']: e for e in bb['elements']}
    G = {g['name']: g for g in bb['groups']}
    seg = [E['V46_queue_%d' % k] for k in range(6)]
    zc = [(e['from'][2] + e['to'][2]) / 2 for e in seg]
    yc_ancien = [(e['from'][1] + e['to'][1]) / 2 for e in seg]
    rapport = []
    for k, e in enumerate(seg):
        d = [e['to'][i] - e['from'][i] for i in range(3)]
        c = [0.0, QUEUE_Y[k], zc[k]]
        d2 = [QUEUE_W[k], d[1], QUEUE_H[k]]           # longueur (Y local) inchangee
        n_uv += garde_densite(bb, e, d, d2, interdits, res)
        e['from'] = [round(c[i] - d2[i] / 2, 4) for i in range(3)]
        e['to'] = [round(c[i] + d2[i] / 2, 4) for i in range(3)]
        e['origin'] = [round(x, 4) for x in c]
        e['rotation'] = [QUEUE_ROT, 0, 0]
        ep = E['V46_epine_queue_%d' % k]
        de = [ep['to'][i] - ep['from'][i] for i in range(3)]
        ce = [0.0, QUEUE_Y[k] + QUEUE_H[k] / 2 - 0.46, zc[k]]
        ep['from'] = [round(ce[i] - de[i] / 2, 4) for i in range(3)]
        ep['to'] = [round(ce[i] + de[i] / 2, 4) for i in range(3)]
        ep['origin'] = [round(x, 4) for x in ce]
        rapport.append((k, round(d[2], 1), QUEUE_H[k], round(yc_ancien[k], 1), QUEUE_Y[k]))
    # pivots : meme ecart a la ligne centrale qu avant, sur la nouvelle ligne
    for k in range(2, 7):
        g = G['tail_%02d' % k]
        z = g['origin'][2]
        ecart = g['origin'][1] - _interp(zc, yc_ancien, z)
        g['origin'] = [g['origin'][0], round(_interp(zc, QUEUE_Y, z) + ecart, 4), z]
    # pattes : section epaissie autour du centre du cube, dans son repere propre
    n = 0
    for e in bb['elements']:
        if e['name'].startswith(('V46_cuisse_', 'V46_genou_', 'V46_tibia_')):
            c = [(e['from'][i] + e['to'][i]) / 2 for i in range(3)]
            d = [e['to'][i] - e['from'][i] for i in range(3)]
            d0 = list(d)
            d[0] *= EPAIS_PATTE
            d[2] *= EPAIS_PATTE
            n_uv += garde_densite(bb, e, d0, d, interdits, res)
            e['from'] = [round(c[i] - d[i] / 2, 4) for i in range(3)]
            e['to'] = [round(c[i] + d[i] / 2, 4) for i in range(3)]
            n += 1
    rapport.append(('uv', n_uv))
    return rapport, n


if __name__ == '__main__':
    bb = json.load(open(sys.argv[1]))
    rap, n = remodele(bb)
    print('queue : segment  hauteur avant -> apres   centre y avant -> apres')
    n_uv = rap.pop()[1]
    for k, h0, h1, y0, y1 in rap:
        print('        %d        %5.1f -> %5.1f        %5.1f -> %5.1f' % (k, h0, h1, y0, y1))
    print('pattes : %d cubes epaissis de %d %% en section' % (n, round((EPAIS_PATTE - 1) * 100)))
    print('%d faces : rectangle UV agrandi, densite de pixels conservee' % n_uv)
    json.dump(bb, open(sys.argv[2], 'w'), separators=(',', ':'))
