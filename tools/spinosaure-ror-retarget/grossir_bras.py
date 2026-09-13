"""Grossit les bras pour se rapprocher de la masse de ceux de ROR.

Mesure prealable : notre bras porte deja PLUS LOIN que celui de ROR (77.5 u contre
62.4 de l'epaule au bout de la griffe). Ce n'est donc pas la longueur qui manque,
c'est la masse de la main et des doigts :

    ROR   doigt 5.0 x 4.0 x 15.0  + griffe plane 19 x 0 x 15
    nous  doigt 2.6 x 2.5 x  6.4  + griffe 2.7 x 2.5 x 9.2

On epaissit donc en section, en n'allongeant que tres peu : allonger davantage
nous ecarterait encore de ROR au lieu de nous en rapprocher.

Les from/to d'un cube bbmodel decrivent la boite AVANT rotation : les mettre a
l'echelle autour de l'origine du cube revient donc bien a agir sur ses axes
locaux (section contre longueur), et non sur les axes du modele.
"""
import json, sys

# cube -> (section X, section Y, longueur Z) ; l'axe long de nos cubes de bras est Z
FACTEURS = {
    'V67_epaule_':      (1.10, 1.10, 1.02),
    'V67_bras_':        (1.16, 1.16, 1.02),
    'V67_avant_bras_':  (1.06, 1.06, 1.02),
    'V67_poignet_fin_': (1.16, 1.16, 1.04),
    'V67_main_':        (1.06, 1.70, 1.10),   # ROR a une main haute (11) et etroite (6)
    'V67_doigt_':       (1.80, 1.80, 1.15),
    'V70_ROR_griffe_':  (1.35, 1.35, 1.00),   # x1.40 supplementaire applique par bras_ror
}


def grossir(bb, facteurs=None):
    facteurs = facteurs or FACTEURS
    n = 0
    rapport = {}
    for e in bb['elements']:
        for prefixe, k in facteurs.items():
            if not e['name'].startswith(prefixe):
                continue
            o = e.get('origin', [0, 0, 0])
            av = [round(e['to'][i] - e['from'][i], 2) for i in range(3)]
            for cle in ('from', 'to'):
                e[cle] = [round(o[i] + (e[cle][i] - o[i]) * k[i], 4) for i in range(3)]
            ap = [round(e['to'][i] - e['from'][i], 2) for i in range(3)]
            rapport.setdefault(prefixe, (av, ap))
            n += 1
            break
    return n, rapport


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    bb = json.load(open(src))
    n, rap = grossir(bb)
    json.dump(bb, open(dst, 'w'), separators=(',', ':'))
    print('%d cubes de bras grossis -> %s' % (n, dst))
    print('   %-20s %-22s %s' % ('piece', 'avant', 'apres'))
    for p, (a, b) in rap.items():
        print('   %-20s %-22s %s' % (p.rstrip('_'), '%s x %s x %s' % tuple(a), '%s x %s x %s' % tuple(b)))
