"""Relief en volume la ou la carte de hauteurs ne suffit pas.

- falaises() : toute paroi raide au bord de l'eau (gorges, cratere, trous bleus, crevasses,
  pointes rocheuses) descendait en mur parfaitement vertical, colonne par colonne. On la ronge
  et on la fait deborder avec un bruit 3D : niches, surplombs, rebords, eperons, eboulis au
  pied, mousse a la ligne d'eau.
- recif() : la barriere de corail etait une couche plate. On y eleve des pates de corail
  (dômes, tables en champignon, tours), des arches, des surplombs et des chenaux, puis on
  pose gorgones et eventails sur les dessus et les flancs.
"""
import math

import numpy as np

from grottes import Bruit3D, voisins4

EAU = 'minecraft:water[level=0]'
NATUREL = ('stone', 'andesite', 'diorite', 'granite', 'tuff', 'deepslate', 'dirt', 'coarse_dirt', 'basalt', 'cobblestone',
           'mossy_cobblestone', 'moss_block', 'rooted_dirt', 'podzol', 'grass_block', 'clay', 'mud')
TOMBE = ('sand', 'gravel', 'red_sand', 'suspicious')


def _lut(m, noms):
    lut = np.zeros(len(m.palette) + 1, bool)
    for nom, i in m.palette.items():
        base = nom.split('[')[0].replace('minecraft:', '')
        lut[i] = base in noms or any(base.startswith(t) for t in noms if t in TOMBE)
    return lut


def dilate(a, n):
    for _ in range(n):
        a = a | voisins4(a)
    return a


def falaises(m, r, protege, rng):
    P, A = m.P, m.AIR
    E = P(EAU)
    eau2d = r.eau > r.h
    cand = dilate(r.pente > 2.0, 2) & dilate(eau2d, 8) & ~protege
    cx, cz = r.CHUTE
    cand &= np.hypot(r.xx - cx, r.zz - cz) > 14                 # on ne touche pas au rideau de la cascade
    if not cand.any():
        return 0
    naturel = _lut(m, NATUREL)
    tombe = _lut(m, TOMBE)
    b1 = Bruit3D(m.W, m.H, m.L, 3, 901)
    b2 = Bruit3D(m.W, m.H, m.L, 9, 902)
    roches = np.array([P('minecraft:stone'), P('minecraft:andesite'), P('minecraft:stone'), P('minecraft:tuff'),
                       P('minecraft:cobblestone'), P('minecraft:stone')], np.uint16)
    moussu = np.array([P('minecraft:mossy_cobblestone'), P('minecraft:moss_block'), P('minecraft:mossy_cobblestone')], np.uint16)
    hs = r.h[cand]
    y_bas = max(3, int(hs.min()) - 30)
    y_haut = min(m.H - 3, int(hs.max()) + 1)
    touches = 0
    h = r.h.astype(np.int32)
    for passe in range(3):
        for y in range(y_bas, y_haut):
            couche = m.blocs[y]
            dessus = m.blocs[y + 1]
            n = 0.62 * b1.couche((y + passe * 17) % (m.H - 4)) + 0.38 * b2.couche(y)
            eau = couche == E
            fluide = (couche == A) | eau
            solide = naturel[np.minimum(couche, len(naturel) - 1)] & cand
            face = solide & voisins4(fluide & cand)
            # ronger : niches et surplombs (jamais sous un bloc qui tomberait, jamais la surface)
            # sous la levre (les 6 derniers blocs), on ronge davantage : surplombs
            seuil = np.where((y >= h - 7) & (y < h - 1), 0.47, 0.40)
            ronge = face & (n < seuil) & (y < h - 1) & ~tombe[np.minimum(dessus, len(tombe) - 1)]
            remplace = np.where(voisins4(eau), E, A).astype(np.uint16)
            couche[ronge] = remplace[ronge]
            # deborder : eperons et rebords ; les rebords forment des bandes horizontales
            rebord = (b2.couche(y) > 0.52) & (y % 5 == 1)                # bancs de 1 a 3 blocs de large
            deborde = fluide & cand & voisins4(solide & ~ronge) & ((n > 0.63) | rebord)
            deborde &= ~(r.canyon_haut | r.canyon_bas) | (couche == A)     # pas dans l'eau du canyon (cascade)
            mat = roches[(n * 131).astype(int) % len(roches)]
            ligne_eau = (y >= r.SEA - 1) & (y <= r.SEA + 3)
            if ligne_eau:
                mat = np.where(n > 0.5, moussu[(n * 53).astype(int) % len(moussu)], mat)
            couche[deborde] = mat[deborde]
            touches += int(ronge.sum() + deborde.sum())
    # talus d'eboulis au pied des parois : des tas de blocs qui remontent sous l'eau
    pied = cand & eau2d & voisins4(dilate(~eau2d, 2)) & (rng.random(cand.shape) < 0.12)
    for z, x in zip(*np.nonzero(pied)):
        y = int(r.h[z, x])
        m.ellipsoide(x + 0.5, y + 1, z + 0.5, rng.uniform(1.2, 3.2), rng.uniform(1.5, 3.5), rng.uniform(1.2, 3.2),
                     ['minecraft:stone', 'minecraft:mossy_cobblestone', 'minecraft:andesite', 'minecraft:cobblestone'][rng.integers(0, 4)],
                     seulement_air=False, seulement=[A, E], bruit=0.45, rng=rng, bas=y + 1)
    return touches


def recif(m, r, rng):
    """Pates de corail en volume sur la barriere et dans le lagon, puis decor vivant."""
    P, A = m.P, m.AIR
    E = P(EAU)
    SEA = r.SEA
    types = ['brain', 'tube', 'horn', 'fire', 'bubble']
    zone = dilate(r.recif, 5) & (r.eau > r.h)
    # quelques pates isolees dans le lagon (bommies)
    lagon = r.lagon & (r.eau - r.h >= 3) & (rng.random(r.h.shape) < 0.004)
    zs, xs = np.nonzero(zone)
    tirage = rng.random(len(zs)) < 0.05
    centres = list(zip(xs[tirage], zs[tirage])) + list(zip(*np.nonzero(lagon)[::-1]))
    poses = 0
    corail = set()
    for (x, z) in centres:
        x, z = int(x), int(z)
        fond = int(r.h[z, x])
        prof = SEA - 1 - fond
        if prof < 2:
            continue
        t = types[(x // 9 + z // 7) % 5]                      # des colonies par secteurs
        bloc = P('minecraft:%s_coral_block' % t)
        forme = rng.random()
        H_ = int(rng.integers(2, prof + 1))
        R0 = rng.uniform(1.4, 3.6)
        for dy in range(0, H_ + 1):
            k = dy / max(H_, 1)
            if forme < 0.35:
                Rk = R0 * (1 - 0.7 * k)                       # dome
            elif forme < 0.65:
                Rk = R0 * (0.45 + 0.9 * k * k)                # table / champignon : pied etroit, chapeau large
            else:
                Rk = max(0.9, R0 * 0.55 * (1 - 0.3 * k))      # tour
            yy = fond + 1 + dy
            if yy > SEA - 1:
                break
            Ri = int(math.ceil(Rk)) + 1
            for dz in range(-Ri, Ri + 1):
                for dx in range(-Ri, Ri + 1):
                    d = math.hypot(dx, dz) + 0.6 * math.sin(dx * 1.7 + dz * 2.3 + dy)
                    if d <= Rk and m.get(x + dx, yy, z + dz) == E:
                        m.pose(x + dx, yy, z + dz, 'minecraft:%s_coral_block' % t)
                        corail.add((x + dx, yy, z + dz))
                        poses += 1
        # arche : un pont de corail vers une voisine
        if rng.random() < 0.12:
            a = rng.uniform(0, 2 * math.pi)
            Lg = int(rng.integers(5, 9))
            ya = min(fond + H_, SEA - 2)
            for i in range(Lg + 1):
                px, pz = int(round(x + math.cos(a) * i)), int(round(z + math.sin(a) * i))
                yy = int(round(ya + 1.5 * math.sin(math.pi * i / Lg)))
                for w in (0, 1):
                    q = (px + int(round(-math.sin(a) * w)), yy, pz + int(round(math.cos(a) * w)))
                    if m.get(*q) == E:
                        m.pose(*q, 'minecraft:%s_coral_block' % t)
                        corail.add(q)
            # pied de l'arche
            px, pz = int(round(x + math.cos(a) * Lg)), int(round(z + math.sin(a) * Lg))
            for yy in range(int(r.h[pz, px]) + 1, ya + 1):
                if m.get(px, yy, pz) == E:
                    m.pose(px, yy, pz, 'minecraft:%s_coral_block' % t)
                    corail.add((px, yy, pz))
    # decor : gorgones et coraux sur les dessus, eventails sur les flancs, concombres de mer
    for (x, y, z) in corail:
        t = m.nom(m.get(x, y, z)).split(':')[1].split('_coral')[0]
        if m.get(x, y + 1, z) == E and y + 1 <= SEA - 1:
            u = rng.random()
            if u < 0.3:
                m.pose(x, y + 1, z, 'minecraft:%s_coral[waterlogged=true]' % t)
            elif u < 0.45:
                m.pose(x, y + 1, z, 'minecraft:%s_coral_fan[waterlogged=true]' % t)
            elif u < 0.5:
                m.pose(x, y + 1, z, 'minecraft:sea_pickle[pickles=%d,waterlogged=true]' % rng.integers(1, 5))
        if rng.random() < 0.25:
            for (dx, dz, f) in ((1, 0, 'east'), (-1, 0, 'west'), (0, 1, 'south'), (0, -1, 'north')):
                if m.get(x + dx, y, z + dz) == E:
                    m.pose(x + dx, y, z + dz, 'minecraft:%s_coral_wall_fan[facing=%s,waterlogged=true]' % (t, f))
                    break
    return poses
