"""Coins et faces d un cube Blockbench, definis UNE fois pour tous les outils.

Le bug corrige ici : gif.py et audit_geo.py avaient chacun une table de faces ecrite
pour un ordre de coins different de celui que leur fonction coins() produisait. Les
six faces designaient toutes le mauvais plan (north pointait sur le dessous, etc.).
Consequence dans les GIFs : silhouettes et mouvements justes, mais chaque face peinte
avec la couleur d une autre et l elimination des faces cachees faite du mauvais cote.
Consequence dans l audit : le detecteur de z-fighting ne pouvait rien trouver.
"""

# indice d un coin = 4*x + 2*y + z, avec x, y, z dans {0 (from), 1 (to)}
def coins(f, t):
    return [[f[0] if x == 0 else t[0], f[1] if y == 0 else t[1], f[2] if z == 0 else t[2]]
            for x in (0, 1) for y in (0, 1) for z in (0, 1)]


# face -> (indices des 4 coins, normale locale, axes (u, v) de la face)
FACES = {
    'north': ([0, 2, 6, 4], (0, 0, -1), (0, 1)),
    'south': ([1, 5, 7, 3], (0, 0, 1), (0, 1)),
    'west':  ([0, 1, 3, 2], (-1, 0, 0), (2, 1)),
    'east':  ([4, 6, 7, 5], (1, 0, 0), (2, 1)),
    'down':  ([0, 4, 5, 1], (0, -1, 0), (0, 2)),
    'up':    ([2, 3, 7, 6], (0, 1, 0), (0, 2)),
}


def _autotest():
    C = coins([0, 0, 0], [1, 1, 1])
    for nom, (idx, n, _) in FACES.items():
        axe = [k for k in range(3) if n[k] != 0][0]
        val = 1 if n[axe] > 0 else 0
        assert all(C[i][axe] == val for i in idx), nom
        assert len({tuple(C[i]) for i in idx}) == 4, nom


_autotest()
