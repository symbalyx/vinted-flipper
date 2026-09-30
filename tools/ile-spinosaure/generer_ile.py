"""Genere « Site B » v2, l'ile du spinosaure, en schematics Sponge v2 (.schem, WorldEdit).

Ile de 640 x 640 blocs (160 de haut), en un fichier complet et en 4 tuiles de 320 x 320 a
coller une par une. Idees reprises des jeux de dinosaures et d'horreur :
  - Jurassic Park / Isla Sorna : base militaire evacuee (enceinte brechee, miradors, QG, hangar,
    heliport), reliee par des routes aux lieux isoles : piste, relais, village, poste de recherche ;
  - Resident Evil / Dino Crisis : sous-sol noye et groupe de secours, couloirs etroits ou l'on
    se croit a l'abri, recits sur les panneaux et dans les coffres ;
  - Alien Isolation : la creature a une route cachee jusque dans le batiment (bassin -> tunnel
    noye -> sous-sol), les vitres ne protegent pas du regard ;
  - The Isle / Path of Titans : jungle a etages (fromagers emergents, voute, sous-bois),
    rivieres profondes comme territoire, lieux isoles relies par des pistes.

Tout est a l'echelle du spinosaure (boite 3,4 x 5) : sous-bois degage (6 blocs sous les
feuillages), troncs espaces, rivieres de 16 a 28 blocs de large et 7 a 10 de fond, couloirs de
2 blocs ou il n'entre pas.

Usage : python3 generer_ile.py [dossier_sortie]
"""
import json
import math
import os
import sys
import time

import numpy as np

from arbres import Foret, F_JUNGLE, F_ACAJOU
from base_militaire import BaseMilitaire
from grottes import Grottes
import details
import flore
from lieux import Lieux
from monde import Monde, Decale
import profond
from profond import Profond
import deplacements
from lagon import Lagon
from relief import Relief, catmull, distance_polyligne
import rendu

W = L = 640
H = 160
SEA = 48                     # coller a y = 15 : la mer du schematic tombe a y = 63, comme la mer vanilla
GRAINE = 20260925

AIR = 'minecraft:air'
EAU = 'minecraft:water[level=0]'


def journal(msg, t0=[time.time()]):
    print('[%6.1f s] %s' % (time.time() - t0[0], msg), flush=True)


# ====================================================================== terrain
def remplir(m, r):
    """Pose le sol colonne par colonne, par tranches horizontales (economie de memoire)."""
    n = r.n
    h = r.h.astype(np.int32)
    eau = r.eau.astype(np.int32)
    P = m.P
    n1, n2, n3 = n.fbm(8, 2, 41), n.fbm(14, 2, 42), n.fbm(30, 2, 43)
    raide = r.pente > 1.7
    tres_raide = r.pente > 3.0
    sous_eau = eau > h
    plage = (r.c > -0.3) & (r.c < 0.55) & (h <= SEA + 2) & ~r.riviere & ~r.lac
    plage |= r.plages_riv & (h <= SEA + 1) & ~sous_eau          # plages des rivieres et du lac
    volcan = np.hypot(r.xx - r.VOLCAN[0], r.zz - r.VOLCAN[1]) < 110 * r.K
    haut = h > SEA + 58
    dessus = np.full(h.shape, P('minecraft:grass_block[snowy=false]'), np.uint16)
    sous = np.full(h.shape, P('minecraft:dirt'), np.uint16)
    dessus[n1 > 0.64] = P('minecraft:podzol[snowy=false]')
    dessus[(n1 < 0.3) & (n2 > 0.55)] = P('minecraft:moss_block')
    dessus[n2 < 0.27] = P('minecraft:coarse_dirt')
    dessus[(n3 > 0.68) & (n1 > 0.5)] = P('minecraft:rooted_dirt')
    # berges boueuses
    berge = (h <= SEA + 2) & ~plage
    dessus[berge] = np.where(n1[berge] > 0.45, P('minecraft:mud'), P('minecraft:grass_block[snowy=false]'))
    dessus[plage] = P('minecraft:sand'); sous[plage] = P('minecraft:sandstone')
    # plages du volcan : sable noir (BOP)
    noire = plage & (np.hypot(r.xx - r.VOLCAN[0], r.zz - r.VOLCAN[1]) < 175 * r.K)
    dessus[noire] = P('biomesoplenty:black_sand'); sous[noire] = P('biomesoplenty:black_sandstone')
    # fonds
    fond_mer = sous_eau & ~r.riviere & ~r.lac & (r.c < 0.5)
    dessus[sous_eau] = np.where(n1[sous_eau] > 0.55, P('minecraft:gravel'),
                                np.where(n2[sous_eau] > 0.6, P('minecraft:clay'), P('minecraft:mud')))
    dessus[fond_mer] = np.where(n1[fond_mer] > 0.66, P('minecraft:gravel'), P('minecraft:sand'))
    sous[fond_mer] = P('minecraft:sand')
    # fond marin travaille : sable pres des cotes, puis gravier, argile et vase au large ;
    # roche nue sur les pitons, les parois des crevasses et des gouffres
    prof = eau - h
    large = fond_mer & (prof > 8)
    dessus[large] = np.where(n2[large] > 0.62, P('minecraft:clay'),
                             np.where(n1[large] > 0.52, P('minecraft:gravel'),
                                      np.where(n3[large] > 0.6, P('minecraft:mud'), P('minecraft:sand'))))
    sous[large] = P('minecraft:gravel')
    roc_ids = np.array([P('minecraft:stone'), P('minecraft:andesite'), P('minecraft:tuff'), P('minecraft:mossy_cobblestone'),
                        P('minecraft:cobblestone'), P('minecraft:stone')], np.uint16)
    roc = fond_mer & ((r.pitons > 2.5) | (r.pente > 1.4) | r.crevasse)
    dessus[roc] = roc_ids[(n1[roc] * 61 + n2[roc] * 17).astype(int) % len(roc_ids)]
    sous[roc] = P('minecraft:stone')
    fond_crev = r.crevasse & (prof > 14)
    dessus[fond_crev] = np.where(n2[fond_crev] > 0.5, P('minecraft:gravel'), P('minecraft:tuff'))
    for gx, gz, R, bas in r.gouffres:
        dg = np.hypot(r.xx - gx, r.zz - gz)
        paroi = (dg < R + 2) & sous_eau
        dessus[paroi] = np.where(n1[paroi] > 0.5, P('minecraft:deepslate'), P('minecraft:tuff'))
        sous[paroi] = P('minecraft:deepslate')
        fond_g = (dg < R * 0.7) & sous_eau
        dessus[fond_g] = np.where(n2[fond_g] > 0.55, P('minecraft:gravel'), P('minecraft:mud'))
    # volcan : cendres et roches, basalte et tuf en altitude
    v_haut = volcan & (h > SEA + 40) & ~sous_eau
    dessus[v_haut & (n2 > 0.5)] = P('minecraft:coarse_dirt')
    roche_v = volcan & haut & ~sous_eau
    dessus[roche_v] = np.where(n1[roche_v] > 0.55, P('minecraft:tuff'),
                               np.where(n2[roche_v] > 0.5, P('minecraft:basalt[axis=y]'), P('minecraft:andesite')))
    sous[roche_v] = P('minecraft:tuff')
    # parois raides : roche nue
    # versants raides : mousse et herbe accrochees a la roche (la jungle couvre tout), roche nue
    # seulement sur les parois quasi verticales
    rv = raide & ~sous_eau
    dessus[rv] = np.where(n1[rv] > 0.62, P('minecraft:stone'), np.where(n2[rv] > 0.5, P('minecraft:moss_block'),
                          P('minecraft:grass_block[snowy=false]')))
    sous[raide] = P('minecraft:stone')
    dessus[tres_raide & ~sous_eau] = P('minecraft:stone')
    # recif corallien
    rec = r.recif & sous_eau
    coraux = ['minecraft:brain_coral_block', 'minecraft:tube_coral_block', 'minecraft:horn_coral_block',
              'minecraft:fire_coral_block', 'minecraft:bubble_coral_block']
    ids_c = np.array([P(c) for c in coraux], np.uint16)
    secteur = ((r.xx // 9 + r.zz // 7) % 5).astype(int)                    # des colonies, pas des confettis
    dessus[rec] = ids_c[secteur[rec]]
    # strates de la roche (visible dans les falaises et le canyon)
    strates = np.array([P('minecraft:stone'), P('minecraft:stone'), P('minecraft:andesite'), P('minecraft:stone'),
                        P('minecraft:tuff'), P('minecraft:stone'), P('minecraft:granite'), P('minecraft:stone'),
                        P('minecraft:diorite')], np.uint16)
    ondul = (n3 * 6).astype(np.int32)
    Ea, Aa = P(EAU), m.AIR
    for y in range(H):
        couche = m.blocs[y]
        roche = strates[(y + ondul) % len(strates)]
        couche[:] = np.where(y <= h - 4, roche, np.where(y < h, sous, np.where(y == h, dessus,
                             np.where(y <= eau, Ea, Aa))))


def marche(r):
    """Position de la rupture du canyon (premier point bas en descendant l'axe) et direction aval."""
    cx, cz = r.CHUTE
    dx, dz = r.CHUTE_DIR
    n = math.hypot(dx, dz); dx, dz = dx / n, dz / n
    # trouver la marche : avancer le long de l'axe jusqu'a ce que le sol tombe au niveau bas
    x, z = cx, cz
    for i in range(40):
        if r.h[int(z), int(x)] < SEA:
            break
        x += dx; z += dz
    return x, z, dx, dz


def cascade(m, r, chute):
    """Chute d'eau : partout ou le lac perche (cratere + haut du canyon) borde une colonne plus
    basse, on dresse un rideau d'eau de la surface du lac jusqu'au sol de cette colonne."""
    w = r.eau == r.LAC_CRATERE
    Ea = m.P(EAU)
    n = 0
    for dz, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nb_w = np.roll(np.roll(w, dz, 0), dx, 1)
        nb_h = np.roll(np.roll(r.h, dz, 0), dx, 1)
        bord = w & ~nb_w & (nb_h < r.LAC_CRATERE)
        for z, x in zip(*np.nonzero(bord)):
            vx, vz = x - dx, z - dz            # la colonne voisine, plus basse
            for y in range(int(r.h[vz, vx]) + 1, r.LAC_CRATERE + 1):
                if m.blocs[y, vz, vx] == m.AIR:
                    m.blocs[y, vz, vx] = Ea
                    n += 1
    return n


# ====================================================================== chemins et ponts
class Pistes:
    def __init__(self, m, r):
        self.m, self.r = m, r
        self.masque = np.zeros((L, W), bool)

    def cotier(self, a, b, n=40, recul=0.3):
        """Points d'un sentier le long de la plage, de a a b en tournant autour de l'ile : sur
        chaque rayon, le premier point de terre ou c depasse `recul` (juste au-dessus de l'eau)."""
        r = self.r
        cx, cz = r.CENTRE
        ta, tb = math.atan2(a[1] - cz, a[0] - cx), math.atan2(b[1] - cz, b[0] - cx)
        if tb - ta > math.pi:
            tb -= 2 * math.pi
        elif ta - tb > math.pi:
            tb += 2 * math.pi
        pts = [a]
        for t in np.linspace(0, 1, n)[1:-1]:
            th = ta + (tb - ta) * t
            for rr in range(int(420 * r.K), int(60 * r.K), -1):
                x, z = int(cx + math.cos(th) * rr), int(cz + math.sin(th) * rr)
                if 0 <= x < W and 0 <= z < L and r.c[z, x] > recul and r.eau[z, x] <= r.h[z, x]:
                    pts.append((x, z))
                    break
        pts.append(b)
        return pts

    def trace(self, pts, larg=2.0, route=False):
        m, r = self.m, self.r
        ligne = catmull([tuple(map(float, p)) for p in pts], 2)
        d, _ = distance_polyligne(W, L, ligne, larg + 2)
        dans = d <= larg
        self.masque |= d <= larg + 2
        zs, xs = np.nonzero(dans)
        rng = m.rng
        mats = [m.P('minecraft:dirt_path'), m.P('minecraft:coarse_dirt'), m.P('minecraft:packed_mud'), m.P('minecraft:rooted_dirt')]
        for z, x in zip(zs, xs):
            hy = int(r.h[z, x])
            if r.eau[z, x] > hy:
                continue
            top = m.blocs[hy, z, x]
            nom = m.nom(top)
            if 'sand' in nom:
                continue                                   # sur la plage, pas de chemin trace : le sable
            if 'grass' in nom or 'podzol' in nom or 'moss' in nom or 'dirt' in nom or 'mud' in nom:
                m.blocs[hy, z, x] = mats[0] if (not route and rng.random() < 0.7) else mats[rng.integers(0, 4)]
        # gues : la ou la piste passe sur l'eau, le pont s'est effondre ; on traverse a pied dans
        # un bloc d'eau, sur un haut-fond de gravier, a decouvert et dans son territoire. Il reste
        # les pilotis du pont.
        gue = (d <= larg + 2) & (r.eau > r.h) & (r.eau == SEA) & (r.riviere | r.lac | (r.h >= SEA - 3))
        if gue.any():
            zs, xs = np.nonzero(gue)
            for z, x in zip(zs, xs):
                hy = int(r.h[z, x])
                if hy < SEA - 1:
                    m.boite(x, hy + 1, z, x, SEA - 2, z, 'minecraft:gravel')
                    m.pose(x, SEA - 1, z, 'minecraft:gravel' if (x + z) % 3 else 'minecraft:sand')
                    r.h[z, x] = SEA - 1
                if (x * 7 + z * 13) % 17 == 0 and d[z, x] > larg - 0.5:
                    m.boite(x, SEA - 1, z, x, SEA + 1 + (x + z) % 3, z, 'minecraft:stripped_spruce_log[axis=y]')



# ====================================================================== foret
def planter(m, r, foret, libre, rng, libre_pentes=None):
    """Plantation par grilles jitterees, du plus grand au plus petit, avec une carte
    d'occupation au sol pour espacer les troncs (le spinosaure doit passer entre)."""
    occupe = np.zeros((L, W), bool)             # emprise des troncs deja plantes
    h = r.h
    SEAh = SEA
    dist_eau = np.full((L, W), 99, np.int16)
    eau = r.eau > h
    # distance a l'eau (approx. par dilatations successives, 12 pas)
    front = eau.copy()
    for k in range(12):
        dist_eau[front & (dist_eau == 99)] = k
        f2 = front.copy()
        f2[1:] |= front[:-1]; f2[:-1] |= front[1:]; f2[:, 1:] |= front[:, :-1]; f2[:, :-1] |= front[:, 1:]
        front = f2
    n = r.n.fbm(70, 2, 51)
    bambou = r.n.fbm(70, 2, 52) > 0.58
    compte = {}

    def essai(pas, jitter, proba, rayon, fn, cond):
        for gz in range(pas // 2, L, pas):
            for gx in range(pas // 2, W, pas):
                x = int(gx + rng.integers(-jitter, jitter + 1)); z = int(gz + rng.integers(-jitter, jitter + 1))
                if not (8 <= x < W - 8 and 8 <= z < L - 8) or rng.random() > proba:
                    continue
                if not cond(x, z) or not libre[z - 1:z + 2, x - 1:x + 2].all():
                    continue
                x0, x1, z0, z1 = x - rayon, x + rayon + 1, z - rayon, z + rayon + 1
                if occupe[z0:z1, x0:x1].any():
                    continue
                fn(x, z)
                m_ = max(rayon * 3 // 4, 1)
                occupe[z - m_:z + m_ + 1, x - m_:x + m_ + 1] = True
                compte[fn.__name__] = compte.get(fn.__name__, 0) + 1

    alt = lambda x, z: int(h[z, x]) - SEAh
    terre = lambda x, z: libre[z, x]
    bas = lambda x, z: terre(x, z) and alt(x, z) < 42 and dist_eau[z, x] > 3 and not bambou[z, x]
    # mangrove du delta et du lagon : eau peu profonde
    mangrove_zone = (r.eau > h) & (r.eau - h <= 3) & (r.zz > 560 * r.K) & ~r.recif & np.isin(
        m.blocs[h.astype(np.int64), np.indices(h.shape)[0], np.indices(h.shape)[1]],
        [i for n_, i in m.palette.items() if 'sand' in n_ or 'mud' in n_ or 'gravel' in n_ or 'clay' in n_])
    def paletuvier(x, z):
        foret.paletuvier(x, z, SEA)
    libre_eau = libre | mangrove_zone
    libre_sauve = libre
    libre = libre_eau
    essai(7, 2, 0.75, 2, paletuvier, lambda x, z: mangrove_zone[z, x])
    libre = libre_sauve
    # saules pleureurs (BOP) le long des rivieres et du lac : des rideaux derriere lesquels il attend
    berges = r.riviere | r.lac
    for _ in range(7):
        berges = berges | np.roll(berges, 1, 0) | np.roll(berges, -1, 0) | np.roll(berges, 1, 1) | np.roll(berges, -1, 1)

    def saule(x, z):
        foret.saule(x, z)
    essai(11, 3, 0.6, 3, saule, lambda x, z: terre(x, z) and berges[z, x] and alt(x, z) < 14)
    essai(40, 10, 0.75, 8, foret.emergent, lambda x, z: bas(x, z) and n[z, x] > 0.35)
    essai(70, 18, 0.5, 5, foret.etrangleur, bas)

    def canopee(x, z):
        # un arbre de voute sur trois est un acajou (BOP) : autre ecorce, autre feuillage
        if rng.random() < 0.36:
            foret.canopee(x, z, bois='biomesoplenty:mahogany', feuille=F_ACAJOU)
        else:
            foret.canopee(x, z)
    essai(10, 3, 0.9, 4, canopee, lambda x, z: terre(x, z) and alt(x, z) < 55 and dist_eau[z, x] > 2)
    # berges et plages : palmiers
    essai(7, 2, 0.6, 2, foret.palmier, lambda x, z: terre(x, z) and alt(x, z) <= 4 and dist_eau[z, x] <= 6)
    # etage bas plus fourni (jeunes arbres, buissons) : il masque la vue sans fermer le passage
    essai(5, 2, 0.85, 2, foret.jeune, lambda x, z: terre(x, z) and alt(x, z) < 70)
    essai(4, 1, 0.8, 1, foret.buisson, lambda x, z: terre(x, z) and alt(x, z) < 75)
    # petits arbres (4 a 6 blocs) : l'etage qui manquait entre les buissons et la voute
    essai(5, 2, 0.8, 2, foret.arbrisseau, lambda x, z: terre(x, z) and alt(x, z) < 72)
    essai(7, 3, 0.6, 2, foret.jeune, lambda x, z: terre(x, z) and alt(x, z) < 70)
    essai(26, 6, 0.35, 3, foret.souche, bas)
    for gz in range(15, L, 30):
        for gx in range(15, W, 30):
            x, z = gx + int(rng.integers(-10, 11)), gz + int(rng.integers(-10, 11))
            if 8 <= x < W - 8 and 8 <= z < L - 8 and bambou[z, x] and libre[z, x] and alt(x, z) < 45:
                foret.bambous(x, z, int(rng.integers(4, 9)))
                compte['bambous'] = compte.get('bambous', 0) + 1
    # sur les versants (hors parois) : buissons et jeunes arbres accroches a la pente
    if libre_pentes is not None:
        libre_sauve = libre
        libre = libre_pentes
        essai(6, 2, 0.55, 2, foret.buisson, lambda x, z: libre_pentes[z, x] and not libre_sauve[z, x])
        essai(9, 3, 0.45, 3, foret.jeune, lambda x, z: libre_pentes[z, x] and not libre_sauve[z, x] and alt(x, z) < 80)
        libre = libre_sauve
    return compte, bambou


def couvert(m, r, rng):
    """Sous-bois (fougeres, herbes, grandes fougeres, melons, azalees), cannes a sucre au bord de
    l'eau, nenuphars, herbiers, kelp, coraux."""
    h = r.h.astype(np.int32)
    zz, xx = np.indices(h.shape)
    top = m.blocs[h, zz, xx]
    dessus = m.blocs[np.minimum(h + 1, H - 1), zz, xx]
    dessus2 = m.blocs[np.minimum(h + 2, H - 1), zz, xx]
    sol_ok = np.isin(top, [m.P(s) for s in ('minecraft:grass_block[snowy=false]', 'minecraft:podzol[snowy=false]',
                                           'minecraft:moss_block', 'minecraft:rooted_dirt', 'minecraft:coarse_dirt')])
    libre = sol_ok & (dessus == m.AIR) & (r.eau <= h)
    u = rng.random(h.shape)
    herbe = m.P('minecraft:grass'); fougere = m.P('minecraft:fern')
    gf_b, gf_h = m.P('minecraft:large_fern[half=lower]'), m.P('minecraft:large_fern[half=upper]')
    ght_b, ght_h = m.P('minecraft:tall_grass[half=lower]'), m.P('minecraft:tall_grass[half=upper]')
    choix = np.full(h.shape, -1, np.int32)
    # sous-bois dense (~80 % du sol couvert, un quart en plantes de 2 blocs) : a hauteur
    # d'yeux on ne voit plus a 50 blocs sous les arbres. Tout se traverse (herbes, fougeres).
    choix[libre & (u < 0.30)] = herbe
    # plantes de Biomes O' Plenty dans le sous-bois : buissons, pousses, trefle
    choix[libre & (u < 0.07)] = m.P('biomesoplenty:bush')
    choix[libre & (u >= 0.07) & (u < 0.11)] = m.P('biomesoplenty:sprout')
    choix[libre & (u >= 0.11) & (u < 0.125)] = m.P('biomesoplenty:clover[facing=north,flower_amount=4]')
    choix[libre & (u >= 0.30) & (u < 0.46)] = fougere
    choix[libre & (u >= 0.46) & (u < 0.47)] = m.P('minecraft:melon')
    choix[libre & (u >= 0.47) & (u < 0.49)] = m.P('minecraft:azalea')
    choix[libre & (u >= 0.49) & (u < 0.495)] = m.P('minecraft:flowering_azalea')
    choix[libre & (u >= 0.495) & (u < 0.498)] = m.P('minecraft:blue_orchid')
    choix[libre & (u >= 0.498) & (u < 0.501)] = m.P('minecraft:brown_mushroom')
    fleurs_bop = np.array([m.P('biomesoplenty:' + f) for f in ('pink_hibiscus', 'orange_cosmos', 'violet', 'pink_hibiscus',
                                                                 'wildflower[facing=east,flower_amount=3]')], np.uint16)
    fl = libre & (u >= 0.501) & (u < 0.509)
    choix[fl] = fleurs_bop[(u[fl] * 1e5).astype(int) % len(fleurs_bop)]
    choix[libre & (u >= 0.509) & (u < 0.5096)] = m.P('biomesoplenty:glowflower')      # rares lueurs dans le noir
    k = choix >= 0
    m.blocs[h[k] + 1, zz[k], xx[k]] = choix[k]
    double = libre & (dessus2 == m.AIR) & (u >= 0.52) & (u < 0.66)
    haute = libre & (dessus2 == m.AIR) & (u >= 0.66) & (u < 0.74)
    herbe_bop = libre & (dessus2 == m.AIR) & (u >= 0.74) & (u < 0.80)          # hautes herbes BOP (2 blocs)
    for msk, b_, h_ in ((double, gf_b, gf_h), (haute, ght_b, ght_h),
                        (herbe_bop, m.P('biomesoplenty:high_grass_plant'), m.P('biomesoplenty:high_grass'))):
        m.blocs[h[msk] + 1, zz[msk], xx[msk]] = b_
        m.blocs[h[msk] + 2, zz[msk], xx[msk]] = h_
    # cannes a sucre : sol au ras de l'eau avec de l'eau a cote
    eau_haut = (r.eau >= h) & (r.eau > -1) & (r.eau > h)
    voisin = np.zeros_like(eau_haut)
    voisin[1:] |= eau_haut[:-1]; voisin[:-1] |= eau_haut[1:]; voisin[:, 1:] |= eau_haut[:, :-1]; voisin[:, :-1] |= eau_haut[:, 1:]
    canne_sol = np.isin(top, [m.P(s) for s in ('minecraft:grass_block[snowy=false]', 'minecraft:sand', 'minecraft:mud',
                                              'minecraft:dirt', 'minecraft:podzol[snowy=false]')])
    cannes = voisin & canne_sol & (h == SEA) & (m.blocs[np.minimum(h + 1, H - 1), zz, xx] == m.AIR) & (rng.random(h.shape) < 0.35)
    # un tiers des bords d'eau : massettes (BOP, 2 blocs) plutot que des cannes
    massettes = cannes & (rng.random(h.shape) < 0.4) & (dessus2 == m.AIR)
    cannes &= ~massettes
    m.blocs[h[massettes] + 1, zz[massettes], xx[massettes]] = m.P('biomesoplenty:cattail[half=lower]')
    m.blocs[h[massettes] + 2, zz[massettes], xx[massettes]] = m.P('biomesoplenty:cattail[half=upper]')
    for dy in range(1, 4):
        sel = cannes & (rng.random(h.shape) < (1.0 if dy == 1 else 0.6 if dy == 2 else 0.3))
        m.blocs[h[sel] + dy, zz[sel], xx[sel]] = m.P('minecraft:sugar_cane[age=0]')
        cannes = sel
    # plages : oyats et herbes des dunes (BOP) sur le sable sec
    sables = np.isin(top, [m.P('minecraft:sand'), m.P('biomesoplenty:black_sand')])
    sec = sables & (h >= SEA + 1) & (r.eau <= h) & (dessus == m.AIR)
    u3 = rng.random(h.shape)
    dune = sec & (u3 < 0.07)
    m.blocs[h[dune] + 1, zz[dune], xx[dune]] = m.P('biomesoplenty:dune_grass')
    oyat = sec & (u3 >= 0.07) & (u3 < 0.12) & (dessus2 == m.AIR)
    m.blocs[h[oyat] + 1, zz[oyat], xx[oyat]] = m.P('biomesoplenty:sea_oats[half=lower]')
    m.blocs[h[oyat] + 2, zz[oyat], xx[oyat]] = m.P('biomesoplenty:sea_oats[half=upper]')
    # eau : herbiers, kelp, nenuphars, coraux
    prof = r.eau - h
    fond_libre = (r.eau > h) & (m.blocs[np.minimum(h + 1, H - 1), zz, xx] == m.P(EAU))
    if hasattr(r, 'grand_lagon'):
        fond_libre &= ~r.grand_lagon                 # le lagon du mosasaure a son propre decor (lagon.py)
    u = rng.random(h.shape)
    herb = fond_libre & (prof >= 2) & (u < 0.18)
    m.blocs[h[herb] + 1, zz[herb], xx[herb]] = m.P('minecraft:seagrass')
    kelp = fond_libre & (prof >= 5) & (u > 0.975) & ~r.riviere & ~r.lac
    for z, x in zip(*np.nonzero(kelp)):
        hk = int(h[z, x]); top_k = int(r.eau[z, x]) - int(rng.integers(1, 4))
        for y in range(hk + 1, top_k):
            m.blocs[y, z, x] = m.P('minecraft:kelp_plant')
        m.blocs[top_k, z, x] = m.P('minecraft:kelp[age=20]')
    douce = r.riviere | r.lac
    un = rng.random(h.shape)
    nenu = douce & (prof <= 4) & (prof >= 1) & (un < 0.05)
    ye = np.minimum(r.eau + 1, H - 1).astype(np.int64)
    m.blocs[ye[nenu], zz[nenu], xx[nenu]] = m.P('minecraft:lily_pad')
    fleuri = douce & (prof <= 4) & (prof >= 1) & (un >= 0.05) & (un < 0.065)
    m.blocs[ye[fleuri], zz[fleuri], xx[fleuri]] = m.P('biomesoplenty:waterlily')
    # roseaux (BOP) dans l'eau d'un bloc de fond, pres des berges : le pied dans l'eau, la tete dehors
    roseau = douce & fond_libre & (prof == 1) & (un > 0.86) & (m.blocs[ye, zz, xx] == m.AIR)
    m.blocs[h[roseau] + 1, zz[roseau], xx[roseau]] = m.P('biomesoplenty:reed[half=lower]')
    m.blocs[h[roseau] + 2, zz[roseau], xx[roseau]] = m.P('biomesoplenty:reed[half=upper]')
    # quelques nenuphars geants (BOP, 2 x 2) sur le lac et les rivieres larges
    geant = douce & (prof >= 2) & (rng.random(h.shape) < 0.0025)
    for z, x in zip(*np.nonzero(geant)):
        if z + 1 >= L or x + 1 >= W:
            continue
        y = int(r.eau[z, x]) + 1
        bloc = m.blocs[y, z:z + 2, x:x + 2]
        dessous = m.blocs[y - 1, z:z + 2, x:x + 2]
        if (bloc == m.AIR).all() and (dessous == m.P(EAU)).all():
            for (dz, dx, q) in ((0, 0, 'north_west'), (0, 1, 'north_east'), (1, 0, 'south_west'), (1, 1, 'south_east')):
                m.blocs[y, z + dz, x + dx] = m.P('biomesoplenty:huge_lily_pad[facing=north,quarter=%s]' % q)
    rec = r.recif & fond_libre & (u < 0.35)
    plantes = ['minecraft:%s[waterlogged=true]' % c for c in ('brain_coral', 'tube_coral', 'horn_coral', 'fire_coral',
                                                              'bubble_coral', 'brain_coral_fan', 'tube_coral_fan')]
    ids = np.array([m.P(p) for p in plantes] + [m.P('minecraft:sea_pickle[pickles=3,waterlogged=true]')], np.uint16)
    m.blocs[h[rec] + 1, zz[rec], xx[rec]] = ids[rng.integers(0, len(ids), int(rec.sum()))]


def biomes(r, bambou):
    pal = {'minecraft:jungle': 0, 'minecraft:bamboo_jungle': 1, 'minecraft:sparse_jungle': 2,
           'minecraft:warm_ocean': 3, 'minecraft:lukewarm_ocean': 4}
    b = np.zeros((L, W), np.int64)
    b[bambou & (r.h >= SEA)] = 1
    b[(r.h > SEA + 55)] = 2
    mer = (r.eau > r.h) & ~r.riviere & ~r.lac & (r.c < 0.4)
    b[mer] = 3
    b[mer & (r.h < SEA - 20)] = 4
    if hasattr(r, 'grand_lagon'):
        b[r.grand_lagon] = 3                     # ocean chaud : l'eau turquoise du lagon
    return b, pal


def sous_sol(m, r, gr, rng, mines):
    """Sous-sol profond, puis ses liaisons avec l'ile : puits de mine a echelles, descentes en
    colimacon depuis les grottes seches, ravins ouverts dans la jungle."""
    pr = Profond(m, r, rng)
    pr.roche()
    journal('profond : roche')
    journal('profond : %d blocs de cavernes' % pr.cavernes())
    journal('profond : %d longs tunnels' % pr.tunnels(3))
    journal('profond : %d blocs de lave' % pr.lave())
    terre = (r.h >= SEA + 12) & (r.eau <= r.h)
    zs, xs = np.nonzero(terre[40:-40, 40:-40])
    for k in rng.choice(len(zs), 2, replace=False):
        pr.geode(int(xs[k]) + 40, int(rng.integers(-45, -15)), int(zs[k]) + 40, float(rng.uniform(4, 6)))
    mx, mz = mines[0]
    journal('profond : mine %s' % pr.mine(mx, mz, -30, profondeur=5))
    journal('profond : puits de mine %d blocs' % profond.puits_de_mine(pr, gr, mx, mz, SEA + 8 + 15, -30))
    # descentes depuis des grottes seches de l'ile
    A = m.AIR
    E = m.P(EAU)
    cand = []
    for y in range(SEA + 2, SEA + 14):
        sol = gr.creuse[y] & (m.blocs[y] == A) & (m.blocs[y - 1] != A) & (m.blocs[y - 1] != E) & (r.h >= SEA + 22)
        zs, xs = np.nonzero(sol)
        if len(zs):
            k = rng.choice(len(zs), min(40, len(zs)), replace=False)
            cand += [(int(xs[j]), y, int(zs[j])) for j in k]
    rng.shuffle(cand)
    faites = []
    for (x, y, z) in cand:
        if any(math.hypot(x - a, z - b) < 110 for a, b in faites) or math.hypot(x - mx, z - mz) < 60:
            continue
        n = profond.descente(pr, gr, x + 0.5, y + 15 + 1.0, z + 0.5, rng.uniform(0, 6.28), int(rng.integers(-34, -18)), rng)
        if n:
            faites.append((x, z))
            journal('descente vers le profond depuis (%d, %d, %d) : %d blocs' % (x, y, z, n))
        if len(faites) >= 5:
            break
    pr.descentes = faites
    # ravins
    pr.ravins = []
    pr.emprises = []
    pr.ravins2d = np.zeros(r.h.shape, bool)
    zs, xs = np.nonzero((r.h >= SEA + 16) & (r.eau <= r.h) & ~gr.protege)
    for essai in range(1500):
        k = int(rng.integers(0, len(zs)))
        if any(math.hypot(xs[k] - a, zs[k] - b) < 200 for a, b in pr.ravins):
            continue
        res = profond.ravin(pr, gr, rng, (float(xs[k]), float(zs[k])), rng.uniform(0, 6.28), int(rng.integers(70, 125)), -28)
        if res is None:
            continue
        emprise, milieu, n = res
        pr.ravins.append(milieu)
        pr.ravins2d |= emprise
        pr.emprises.append((emprise, milieu))
        journal('ravin au (%d, %d) : %d blocs' % (milieu[0], milieu[1], n))
        if len(pr.ravins) >= 2:
            break
    journal('profond : minerais %s' % pr.minerais())
    # la region de sculk : loin de la mine profonde, sous la terre
    d = np.hypot(r.xx - mx, r.zz - mz) * terre
    iz, ix = np.unravel_index(np.argmax(d), d.shape)
    journal('profond : decor %s' % pr.decorer((int(ix), int(iz))))
    return pr


monde_java_ORIGINE = -320  # = monde_java.ORIGINE (ile de 640 centree sur 0, 0)


def tyroliennes(m, r, li, rng, n_max=8):
    """Lignes de tyrolienne entre des lieux, de haut en bas. Station de depart : le point libre
    le plus haut a 12-32 blocs du lieu de depart ; arrivee : un point libre a 10-30 blocs du lieu
    d'arrivee, du cote du depart de preference. Pour chaque paire on garde la premiere ligne qui
    passe (tour de depart la plus basse possible)."""
    res = deplacements.Reseau(m, r, li, rng)
    res.haut_solide(0, 0)
    S = res._sommets
    poi = {}
    for nom, x, z, _ in li.poi:
        if nom and nom not in poi:
            poi[nom] = (x, z)
    # emplacement libre : pas de batiment sur 7 x 7 (sommet solide au niveau du sol naturel),
    # pas d'eau, pas dans un couloir deja pris
    def libre(x, z):
        if not (10 <= x < W - 10 and 10 <= z < L - 10):
            return False
        bloc = S[z - 3:z + 4, x - 3:x + 4]
        sol = r.h[z - 3:z + 4, x - 3:x + 4]
        return bool((bloc <= sol + 1).all() and (r.eau[z - 3:z + 4, x - 3:x + 4] <= sol).all()
                    and not res.couloir[z, x] and (np.ptp(sol) <= 6))

    def autour(c, r0, r1):
        out = []
        for rr in range(r0, r1 + 1, 4):
            for k in range(16):
                a_ = k * math.pi / 8
                p = (int(round(c[0] + math.cos(a_) * rr)), int(round(c[1] + math.sin(a_) * rr)))
                if libre(*p):
                    out.append(p)
        return out

    paires = [('Base militaire', 'Rive sud du lagon'), ('Rive nord du lagon', 'Rive sud du lagon'),
              ('Relais radio', 'Base militaire'), ('Tour de guet', 'Affut'), ('Relais radio', 'Village de pecheurs'),
              ('Observatoire du volcan', 'Campement abandonne'), ('Helicoptere abattu', 'Temple maya en ruine'),
              ('Temple maya en ruine', 'Cenote'), ('Phare', 'Campement abandonne'), ('Tour de guet', 'Mine abandonnee'),
              ('Tour de guet', 'Poste de recherche (lac)')]
    faites = []
    for (na, nb) in paires:
        if na not in poi or nb not in poi:
            continue
        A, B = poi[na], poi[nb]
        cand_a = sorted(autour(A, 12, 32), key=lambda p: -int(r.h[p[1], p[0]]))[:4]
        cand_b = sorted(autour(B, 10, 30), key=lambda p: math.dist(p, A))[:6]
        if not cand_a or not cand_b:
            journal('tyrolienne %s -> %s : pas de place pour les stations' % (na, nb))
            continue
        anc, meilleure = None, -99.0
        for sa in cand_a:
            for sb in cand_b:
                res.derniere_marge = -99.0
                anc = res.tyrolienne(sa, sb, 'Tyrolienne %s -> %s' % (na, nb))
                meilleure = max(meilleure, res.derniere_marge)
                if anc:
                    break
            if anc:
                break
        if anc is None:
            journal('tyrolienne %s -> %s : impossible (meilleure marge %.1f bloc sous le joueur)' % (na, nb, meilleure))
            continue
        faites.append(na + nb)
        journal('Tyrolienne %s -> %s : %d troncons, depart y=%d, arrivee y=%d, %.0f blocs' % (
            na, nb, len(anc) - 1, anc[0][1] + 15, anc[-1][1] + 15,
            sum(math.dist(p, q) for p, q in zip(anc, anc[1:]))))
        if len(faites) >= n_max:
            break
    return res


def site_plat(r, cx, cz, R, t):
    """Point le plus plat (ecart-type des hauteurs sur un carre de demi-cote t) a moins de R de
    (cx, cz), sur la terre ferme."""
    mieux, best = None, 1e9
    for z in range(cz - R, cz + R + 1, 3):
        for x in range(cx - R, cx + R + 1, 3):
            if not (t + 2 <= x < W - t - 2 and t + 2 <= z < L - t - 2):
                continue
            zone = r.h[z - t:z + t + 1, x - t:x + t + 1]
            if (r.eau[z - t:z + t + 1, x - t:x + t + 1] > zone).any():
                continue
            cout = float(zone.std()) + 0.02 * math.hypot(x - cx, z - cz)
            if cout < best:
                best, mieux = cout, (x, z)
    return mieux or (cx, cz)


def poste_recherche(li, x, z):
    """Poste de recherche prefabrique au bord du lac : il observait l'ilot du repaire. Deux
    modules, une antenne, un ponton d'observation, des cages vides."""
    from mobilier import Kit
    m, rng = li.m, li.rng
    y0 = li.sol_moyen(x - 10, z - 8, x + 10, z + 8)
    li.plateforme(x - 12, z - 10, x + 12, z + 10, y0, 'minecraft:coarse_dirt', 'minecraft:dirt', 16, talus=8)
    v = Decale(m, x - 10, y0 + 1, z - 7)
    k = Kit(v, rng)
    for (ox, oz) in ((0, 0), (12, 2)):
        v.boite(ox, 0, oz, ox + 8, 3, oz + 6, 'minecraft:white_concrete')
        v.boite(ox + 1, 0, oz + 1, ox + 7, 2, oz + 5, 'minecraft:air')
        v.boite(ox, 3, oz, ox + 8, 3, oz + 6, 'minecraft:light_gray_concrete')
        v.boite(ox + 1, -1, oz + 1, ox + 7, -1, oz + 5, 'minecraft:polished_andesite')
        v.boite(ox + 2, 1, oz, ox + 6, 1, oz, 'minecraft:glass_pane')
        v.boite(ox + 2, 1, oz + 6, ox + 6, 1, oz + 6, 'minecraft:glass_pane')
        v.boite(ox, 0, oz + 3, ox, 1, oz + 3, 'minecraft:air')
        k.porte(ox, 0, oz + 3, 'west', 'iron')
        k.lampes_plafond(ox + 1, oz + 1, ox + 7, oz + 5, 2, 3, 0.3)
    k.paillasse(2, 1, 6, 1, 0, 'south')
    k.bureau(5, 0, 4, 'north', 2)
    v.coffre(7, 0, 5, 'west', [('minecraft:spyglass', 1), ('minecraft:glass_bottle', 6), ('minecraft:book', 3), ('minecraft:bread', 4)])
    for i in range(3):
        v.boite(14 + i * 2, 0, 3, 14 + i * 2, 1, 3, 'minecraft:iron_bars')
    v.coffre(19, 0, 5, 'north', [('minecraft:bone', 6), ('minecraft:lead', 2), ('minecraft:name_tag', 1)])
    for y in range(4, 16):
        v.pose(4, y, 3, 'minecraft:iron_bars' if y % 5 else 'minecraft:iron_block')
    v.pose(4, 16, 3, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
    li.ajoute('Poste de recherche (lac)', x, z, 14)


def meta_spawn(r, li):
    """Point d'apparition (coordonnees du monde) : au ponton d'arrivee, sur la terre ferme."""
    import monde_java
    x, z = W // 2, L // 2
    for nom, a, b, _ in li.poi:
        if nom.lower().startswith('ponton'):
            x, z = a, b
            break
    # la cellule de terre la plus proche
    terre = (r.eau <= r.h) & (r.h >= SEA + 1)
    zs, xs = np.nonzero(terre)
    k = int(np.argmin((xs - x) ** 2 + (zs - z) ** 2))
    x, z = int(xs[k]), int(zs[k])
    return [x + monde_java.ORIGINE, int(r.h[z, x]) + 1 + monde_java.DECALAGE_Y, z + monde_java.ORIGINE]


# ====================================================================== principal
def main(sortie):
    os.makedirs(sortie, exist_ok=True)
    rng = np.random.default_rng(GRAINE)
    journal('relief')
    r = Relief(W, L, SEA, graine=7).calculer()
    m = Monde(W, H, L, GRAINE)
    m.rng = rng
    journal('remplissage du terrain')
    remplir(m, r)
    # le grand lagon du mosasaure (nord-ouest) : creuse avant les lieux, les pistes et la foret
    lagon = Lagon(m, r, rng, centre=(340, 452), rx=46, rz=42)      # entre la riviere, la base et la cote sud
    journal('grand lagon : %d colonnes d\'eau' % lagon.creuser())
    chute = marche(r)
    foret = Foret(m, (r.h + 1).astype(np.int32), rng)
    # ------------------------------------------------ lieux : une operation militaire sur l'ile
    # La base est au coeur de tout : pres du ponton (ravitaillement par la mer), de la piste
    # d'atterrissage et du relais radio sur la colline ; le bunker de commandement a cote.
    # Autour, ce que l'operation est venue faire (poste de recherche au lac, observatoire du
    # volcan, station du delta) et ce qu'il y avait avant elle (village de pecheurs, temple,
    # phare, mine, bungalows). Les routes partent de la base ; les sentiers menent au reste.
    journal('lieux')
    D = r.D
    li = Lieux(m, r, rng)
    if lagon.rive_nord:
        li.ajoute('Rive nord du lagon', lagon.rive_nord[0], lagon.rive_nord[1], 0)
    li.ajoute('Rive sud du lagon', lagon.cx, lagon.cz + lagon.rz + 18, 0)
    journal('base militaire')
    bx, bz = D(470, 360)
    base = BaseMilitaire(li, bx, bz)
    base.construire()
    pb = base.portes()
    c = li.cote(pb['sud'][0], pb['sud'][1] + 10, 0, 1)
    dock = li.ponton(c[0], c[1] - 2)
    # la piste d'atterrissage longe la base au sud-est ; l'avion cargo a fini dans la jungle
    px0, pz_ = bx + base.LX + 18, bz + base.LZ + 26
    li.piste(px0, pz_, px0 + 64, avion=(px0 + 8, pz_ + 16))      # sorti de piste, dans la jungle
    li.ajoute('', px0 + 32, pz_, 40)
    # relais radio : le point le plus haut de la colline a l'est de la base
    x0_, z0_ = bx + base.LX + 10, bz - 10
    zone = r.h[z0_:z0_ + 80, x0_:x0_ + 70]
    iz, ix = np.unravel_index(np.argmax(zone), zone.shape)
    relais = (x0_ + ix, z0_ + iz)
    li.relais(*relais)
    # bunker de commandement, a demi enterre juste a l'ouest de la base
    bunker = (bx - 26, bz + base.LZ // 2 + 18)
    li.bunker(*bunker)
    # checkpoint sur la route du ponton
    check = (pb['sud'][0] + 4, (pb['sud'][1] + dock[1]) // 2)
    # tour de guet : point le plus haut de la crete ouest (elle surveille le lac et la riviere)
    zx0, zz0 = D(110, 300)
    zone = r.h[zz0:zz0 + 100, zx0:zx0 + 66]
    iz, ix = np.unravel_index(np.argmax(zone), zone.shape)
    tour = (zx0 + ix, zz0 + iz)
    li.tour(*tour)
    # poste de recherche au bord du lac : il observait l'ilot (le repaire)
    lx_, lz_ = r.LAC
    poste = (int(lx_) + 60, int(lz_))
    for dxl in range(int(52 * r.K), 140):              # la premiere terre seche a l'est du lac (apres l'ilot), +12
        px_l, pz_l = int(lx_) + dxl, int(lz_) - 8
        if r.eau[pz_l, px_l] <= r.h[pz_l, px_l] and r.h[pz_l, px_l] >= SEA + 1 and not r.lac[pz_l, px_l]:
            poste = (px_l + 12, pz_l)
            break
    poste_recherche(li, *poste)
    li.repaire(int(r.ILOT[0]), int(r.ILOT[1]))
    li.affut(int(lx_) - 52, int(lz_) - 5)
    # la cascade et sa grotte, le pont suspendu au-dessus de la gorge
    li.grotte(chute[0] - chute[2] * 2, chute[1] - chute[3] * 2, -chute[2], -chute[3], SEA)
    cascade(m, r, chute)
    gx_, gz_ = chute[0] + chute[2] * 12, chute[1] + chute[3] * 12
    px_, pz2 = -chute[3], chute[2]
    bords = []
    for sgn in (-1, 1):
        for d in range(4, 36):
            qx, qz = int(gx_ + px_ * d * sgn), int(gz_ + pz2 * d * sgn)
            if r.h[qz, qx] > SEA + 22:
                bords.append((qx, qz, int(r.h[qz, qx])))
                break
    if len(bords) == 2:
        li.pont_suspendu(bords[0][:2], bords[1][:2], min(bords[0][2], bords[1][2]) + 1)
    # le camp de la premiere expedition, sur la route du volcan ; l'observatoire sur le flanc
    camp = site_plat(r, *D(408, 238), 20, 14)
    li.campement(*camp)
    vx_, vz_ = r.VOLCAN
    zone = r.h[int(vz_) - 25:int(vz_) + 8, int(vx_) + 23:int(vx_) + 40]
    iz, ix = np.unravel_index(np.argmax(zone), zone.shape)
    obs = (int(vx_) + 23 + ix, int(vz_) - 25 + iz)
    li.observatoire(*obs)
    # l'helicoptere abattu sur la route du temple ; le temple et son cenote dans la jungle
    heli = D(262, 196)
    li.helicoptere(*heli)
    temple = site_plat(r, *D(205, 262), 22, 17)
    li.temple(*temple)
    # le phare sur le cap nord
    cap = li.cote(*D(345, 330), 0, -1)
    phare = (cap[0], cap[1] + 12)
    li.phare(*phare)
    # le village de pecheurs sur la cote est, son cimetiere juste derriere
    est = li.cote(*D(640, 395), 1, 0)
    village = (est[0] + 4, est[1] + 18)
    li.village(*village)
    cimet = site_plat(r, village[0] - 34, village[1] - 6, 10, 8)
    li.cimetiere(*cimet)
    # la mine, au pied du versant est de la crete
    mine = D(196, 450)
    zm = D(0, 450)[1]
    for mx_ in range(D(250, 0)[0], D(150, 0)[0], -1):
        if r.h[zm, mx_ - 10] - r.h[zm, mx_] >= 9 and r.eau[zm, mx_] <= r.h[zm, mx_]:
            mine = (mx_, zm)
            break
    li.mine(mine[0], mine[1], -1, 0.0)
    # bungalows du lagon corallien (un ancien hotel) ; station du delta et sa passerelle
    lagon_bord = li.cote(*D(250, 560), -0.7, 0.7) or D(215, 600)
    bung = [(lagon_bord[0] + 10, lagon_bord[1] - 12), (lagon_bord[0] + 22, lagon_bord[1] - 22),
            (lagon_bord[0] + 2, lagon_bord[1] - 26)]
    li.bungalows(bung)
    rec = np.argwhere(r.recif)
    ez, ex = rec[len(rec) // 3]
    li.epave(int(ex) - 6, int(ez))
    li.passerelle([D(372, 600), D(356, 614), D(344, 626), D(336, 642)])
    # ------------------------------------------------ routes et sentiers
    journal('routes et sentiers')
    pi = Pistes(m, r)
    ROUTE, SENTIER = 2.6, 1.3
    pi.trace([pb['sud'], check, dock], ROUTE, route=True)                                   # base -> ponton
    pi.trace([pb['est'], (pb['est'][0] + 14, pb['est'][1]), (px0, pz_ - 6), (px0 + 8, pz_)], ROUTE, route=True)   # -> piste
    pi.trace([pb['est'], ((pb['est'][0] + relais[0]) // 2, pb['est'][1] - 8), relais], 2.0, route=True)  # -> relais
    pi.trace([pb['ouest'], (bunker[0] + 6, bunker[1] - 10), bunker], 2.0, route=True)        # -> bunker
    pi.trace([pb['ouest'], (poste[0] + 20, poste[1] + 6), poste], ROUTE, route=True)          # -> poste du lac (gue)
    pi.trace([poste, (int(lx_) + 10, int(lz_) - 58), (tour[0] + 40, tour[1] - 20), tour], 2.0, route=True)   # -> crete
    pi.trace([pb['nord'], (pb['nord'][0] - 6, pb['nord'][1] - 30), camp], ROUTE, route=True)  # -> camp (gue)
    pi.trace([camp, (camp[0] + 50, camp[1] - 40), obs], 2.0, route=True)                      # -> volcan
    pi.trace(pi.cotier(dock, village), 2.0, route=True)                                       # ponton -> village
    # sentiers
    pi.trace([camp, D(390, 180), phare], SENTIER)
    pi.trace([camp, D(330, 200), heli], SENTIER)
    pi.trace([heli, D(230, 240), temple], SENTIER)
    pi.trace([tour, D(175, 300), temple], SENTIER)
    pi.trace([tour, D(170, 450), mine], SENTIER)
    pi.trace([mine, D(200, 520), bung[1]], SENTIER)
    pi.trace(pi.cotier(bung[1], D(336, 642)), SENTIER)
    pi.trace([poste, (int(lx_) + 30, int(lz_) + 40), (int(lx_) - 40, int(lz_) + 30), (int(lx_) - 52, int(lz_) - 5)], SENTIER)
    pi.trace([dock, (lagon.cx + lagon.rx + 20, lagon.cz + 10), (lagon.cx, lagon.cz + lagon.rz + 18)], SENTIER)
    pi.trace([pb['nord'], (lagon.cx + 10, lagon.cz - lagon.rz - 30), lagon.rive_nord or (lagon.cx, lagon.cz - lagon.rz - 12)], SENTIER)
    pi.trace([village, cimet], SENTIER)
    pi.trace([camp, D(470, 150), D(560, 110)], SENTIER)
    pi.trace([relais, (relais[0] + 10, village[1] + 20), village], SENTIER)
    li.checkpoint(*check)
    # vehicules abandonnes le long des routes
    for (p, sens, renv) in (((pb['sud'][0] + 6, pb['sud'][1] + 12), 'south', False),
                            ((pb['ouest'][0] - 30, pb['ouest'][1] + 2), 'west', True),
                            ((camp[0] + 20, camp[1] + 30), 'north', False),
                            ((tour[0] + 30, tour[1] - 10), 'east', True)):
        li.jeep(p[0], p[1], sens, renversee=renv)
    # ------------------------------------------------ tyroliennes (mods Ziplines: Rezipped! + Reconnectible Chains)
    reseau = tyroliennes(m, r, li, rng)
    if os.environ.get('ARRET') == 'tyroliennes':
        np.save(os.path.join(sortie, 'blocs.npy'), m.blocs)
        json.dump(m.palette, open(os.path.join(sortie, 'palette.json'), 'w'))
        json.dump([(n, x, z) for n, x, z, _ in li.poi if n], open(os.path.join(sortie, 'lieux.json'), 'w'))
        sys.exit(0)
    # ------------------------------------------------ grottes, gouffres et nids
    journal('grottes')
    zz, xx = r.zz, r.xx
    protege = (xx >= bx - 24) & (xx <= bx + base.LX + 24) & (zz >= bz - 24) & (zz <= bz + base.LZ + 24)
    for nom, x, z, ray in li.poi:
        protege |= np.hypot(xx - x, zz - z) < max(ray, 12) + 16
    protege_lieux = protege.copy()                 # lieux et base seulement (pour les falaises)
    protege_dur = protege | r.cratere | r.canyon_haut | r.canyon_bas
    pm = pi.masque.copy()
    for _ in range(4):
        p2 = pm.copy(); p2[1:] |= pm[:-1]; p2[:-1] |= pm[1:]; p2[:, 1:] |= pm[:, :-1]; p2[:, :-1] |= pm[:, 1:]; pm = p2
    protege |= pm | r.cratere | r.canyon_haut | r.canyon_bas
    gr = Grottes(m, r, rng, protege, SEA, protege_dur)
    # l'antre d'abord (et sa gaine de roche) : depuis le trou bleu du lagon, un tunnel noye
    # remonte jusqu'a une salle seche ; les autres reseaux ne pourront pas y deboucher
    gx_, gz_, gR_, _ = r.gouffres[0]
    antre = gr.antre(gx_, gz_, gR_)
    gr.creuser()
    # sous-sol « monde classique » : galeries et cavernes au bruit, mine abandonnee sous la crete
    journal('cavernes : %d blocs creuses' % gr.cavernes())
    (mx0, mz0), (mx1, mz1) = D(110, 330), D(210, 480)
    zc = r.h[mz0:mz1, mx0:mx1].astype(float) * ~protege_dur[mz0:mz1, mx0:mx1]
    iz, ix = np.unravel_index(np.argmax(zc), zc.shape)
    mine_v = (mx0 + int(ix), mz0 + int(iz))
    journal('mine abandonnee : %d couloirs' % gr.mine_vanilla(mine_v[0], mine_v[1], SEA + 8, profondeur=4))
    # deux autres mines, sous d'autres hauteurs
    mines = [mine_v]
    # les autres : la ou le terrain reste haut sur 40 blocs a la ronde (hauteur minimale d'une
    # fenetre glissante, sur une carte reduite au quart), hors lieux
    h4 = np.where(protege_dur | (r.eau > r.h), 0, r.h)[::4, ::4].astype(float)
    fen = np.lib.stride_tricks.sliding_window_view(np.pad(h4, 5, constant_values=0), (11, 11))
    hmin = np.repeat(np.repeat(fen.min(axis=(2, 3)), 4, 0), 4, 1)[:L, :W]
    for _ in range(2):
        haut = hmin.copy()
        for (a, b) in mines:
            haut[np.hypot(xx - a, zz - b) < 170] = 0
        haut[:60] = haut[-60:] = 0; haut[:, :60] = haut[:, -60:] = 0
        iz, ix = np.unravel_index(np.argmax(haut), haut.shape)
        if haut[iz, ix] < SEA + 18:
            break
        mines.append((int(ix), int(iz)))
        journal('mine abandonnee (%d, %d) : %d couloirs' % (ix, iz, gr.mine_vanilla(int(ix), int(iz), SEA + 5, profondeur=4)))
    gr.rugosite()
    gr.noyer()
    # ------------------------------------------------ sous-sol profond (y -64 a 14) et liaisons
    pr = sous_sol(m, r, gr, rng, mines)
    journal('lagon : fosse, scellement, epave, rochers, algues %s' % lagon.approfondir(pr, li))
    for emprise, milieu in pr.emprises:
        bords = deplacements.passerelle_ravin(m, r, pr, emprise, milieu)
        if bords:
            for (a, b) in bords:
                li.ajoute('', a, b, 4)
            li.ajoute('Passerelle du ravin', int(milieu[0]), int(milieu[1]), 0)
            journal('passerelle au-dessus du ravin : %s' % (bords,))
    journal('minerais : %s' % gr.minerais())
    gr.decorer()
    gr.formations()
    gr.porches_rocheux()
    gr.nids_dans_les_salles(2)
    gr.nid_antre()
    if antre:
        li.ajoute('Antre (acces en plongee par le trou bleu du lagon)', antre[0], antre[2], 0)
    li.ajoute('Mine abandonnee (galeries, sous la crete ; puits a echelles vers la mine profonde)', mine_v[0], mine_v[1], 0)
    for (a, b) in mines[1:]:
        li.ajoute('Mine abandonnee', a, b, 0)
    for (a, b) in pr.ravins:
        li.ajoute('Ravin (jusqu\'au sous-sol profond)', int(a), int(b), 0)
    for (a, b) in pr.descentes:
        li.ajoute('Descente vers les cavernes profondes (grotte)', a, b, 0)
    # un nid perche sur la levre du cratere : le dernier endroit ou l'on irait le chercher
    dv = np.hypot(xx - r.VOLCAN[0], zz - r.VOLCAN[1])
    levre = (dv > 44) & (dv < 60) & (r.pente < 0.9) & ~protege & (r.eau <= r.h)
    lz_, lx_ = np.nonzero(levre)
    if len(lz_):
        k = int(rng.integers(0, len(lz_)))
        gr.nid(int(lx_[k]), int(r.h[lz_[k], lx_[k]]) + 1, int(lz_[k]), 'Nid (flanc du volcan)')
    for nom, x, y, z in gr.nids:
        li.ajoute(nom, x, z, 7)
    for (x, z) in gr.entrees:
        li.ajoute('', x, z, 4)                         # porche degage : pas d'arbre plante dessus
    journal('falaises en volume : %d blocs ronges ou ajoutes' % details.falaises(m, r, protege_lieux, rng))
    carte_grottes = np.stack([gr.creuse.any(axis=0), (gr.creuse & (m.blocs == m.P(EAU))).any(axis=0)])
    journal('grottes : %d salles, %d entrees et gouffres, %d nids, %d blocs creuses'
            % (len(gr.salles), len(gr.entrees), len(gr.nids), int(gr.creuse.sum())))
    # ------------------------------------------------ foret
    journal('foret')
    libre = (r.h >= SEA + 1) & (r.eau <= r.h) & (r.pente < 1.6) & ~r.cratere & ~r.canyon_haut & ~r.canyon_bas
    libre &= ~pi.masque & ~pr.ravins2d & ~reseau.couloir
    zz, xx = r.zz, r.xx
    libre &= ~((xx >= bx - 8) & (xx <= bx + base.LX + 8) & (zz >= bz - 8) & (zz <= bz + base.LZ + 8))
    for nom, x, z, ray in li.poi:
        if ray:
            libre &= np.hypot(xx - x, zz - z) > ray + 10
    # ce qui n'est pas des arbres : mares boueuses, rochers moussus, clairieres fleuries
    n_mares, _ = flore.mares(m, r, rng, libre)
    n_rochers = flore.rochers(m, r, rng, libre)
    clair = flore.clairieres(r, rng, libre)
    journal('mares : %d, rochers : %d, clairieres : %d colonnes' % (n_mares, n_rochers, int(clair.sum())))
    libre &= ~clair
    # versants : buissons et jeunes arbres aussi la ou la pente interdit les grands arbres
    libre_pentes = (r.h >= SEA + 1) & (r.eau <= r.h) & (r.pente < 2.8) & ~r.cratere & ~r.canyon_haut & ~r.canyon_bas
    libre_pentes &= ~pi.masque & ~clair & ~pr.ravins2d & ~reseau.couloir
    libre_pentes &= ~((xx >= bx - 8) & (xx <= bx + base.LX + 8) & (zz >= bz - 8) & (zz <= bz + base.LZ + 8))
    for nom, x, z, ray in li.poi:
        if ray:
            libre_pentes &= np.hypot(xx - x, zz - z) > ray + 10
    # le terrain a bouge depuis le debut (plateformes, talus des lieux) : hauteurs a jour, et on
    # ne plante que sur de la vraie terre, avec de l'air (ou de l'eau pour les paletuviers) au-dessus
    foret.sol = (r.h + 1).astype(np.int32)
    hz = r.h.astype(np.int64)
    zz_, xx_ = np.indices(hz.shape)
    dessus_ = m.blocs[hz, zz_, xx_]
    au_dessus = m.blocs[np.minimum(hz + 1, H - 1), zz_, xx_]
    terre_ids = [i for n_, i in m.palette.items() if any(k in n_ for k in (
        'grass_block', 'dirt', 'podzol', 'moss_block', 'mud', 'sand', 'gravel', 'clay'))
        and 'path' not in n_ and 'brick' not in n_ and 'packed' not in n_ and 'sandstone' not in n_]
    vrai_sol = np.isin(dessus_, terre_ids) & ((au_dessus == m.AIR) | (au_dessus == m.P(EAU)))
    libre &= vrai_sol
    libre_pentes &= vrai_sol
    compte, bambou = planter(m, r, foret, libre, rng, libre_pentes)
    journal('arbres : %s' % compte)
    journal('sous-bois et eaux')
    couvert(m, r, rng)
    journal('clairieres fleuries : %d' % flore.fleurs_clairieres(m, r, rng, clair))
    journal('rideaux de lianes : %d blocs' % flore.rideaux_lianes(m, rng))
    journal('mousse espagnole : %d blocs' % flore.mousse_espagnole(m, rng))
    journal('lianes des falaises : %d blocs' % flore.lianes_falaises(m, r, rng))
    journal('recif en volume : %d blocs de corail' % details.recif(m, r, rng))
    journal('clotures ancrees au sol : %d' % m.ancrer_clotures())
    journal('tyroliennes : %d blocs de feuillage degages autour des cables' % reseau.degager())
    journal('connexions (vitres, barrieres)')
    m.connecter()
    journal('suspendus : lianes corrigees / retirees, propagules retirees : %s' % (m.nettoyer_suspendus(),))
    bio, bio_pal = biomes(r, bambou)
    journal('noeuds de chaine : %d, barques : %d, wagonnets : %d' % (
        reseau.noeuds(), deplacements.barques(m, r, li), deplacements.wagonnets(m, pr, rng)))
    # ------------------------------------------------ ecriture
    journal('ecriture')
    meta = {'W': W, 'H': H, 'L': L, 'SEA': SEA, 'coller_y': 63 - SEA, 'base': [bx, base.y0, bz],
            'lieux': [(n, x, z) for n, x, z, _ in li.poi],
            'entrees_grottes': [(int(x), int(r.h[z, x]), int(z)) for x, z in gr.entrees],
            'tyroliennes': [(nom, [(x + monde_java_ORIGINE, y + 15, z + monde_java_ORIGINE) for x, y, z in a]) for nom, a in reseau.lignes],
            'trous_bleus': [(int(x), int(z), round(float(R)), int(bas)) for x, z, R, bas in r.gouffres]}
    json.dump(meta, open(os.path.join(sortie, 'site_b_v2.json'), 'w'), ensure_ascii=False, indent=1)
    taille = m.ecrire(os.path.join(sortie, 'site_b_v2.schem'), biomes=bio, bio_palette=bio_pal, nom='Site B v2')
    journal('site_b_v2.schem : %.1f Mo' % (taille / 1e6))
    for i in range(2):
        for j in range(2):
            t = m.ecrire(os.path.join(sortie, 'site_b_v2_%d_%d.schem' % (i, j)), 320 * i, 320 * j, 320 * (i + 1), 320 * (j + 1),
                         biomes=bio, bio_palette=bio_pal, nom='Site B v2 tuile %d-%d' % (i, j))
            journal('tuile %d-%d : %.1f Mo' % (i, j, t / 1e6))
    np.save(os.path.join(sortie, 'grottes.npy'), carte_grottes)
    # ------------------------------------------------ vrai monde Minecraft (dossier de sauvegarde)
    journal('monde Java 1.20.1')
    import monde_java
    bio3 = dict(bio_pal)
    bio3['minecraft:dripstone_caves'] = len(bio3)
    bio3['minecraft:deep_dark'] = len(bio3)
    dossier = os.path.join(sortie, 'Site B')
    ex = monde_java.Exporteur(m, pr.b, bio, bio3, SEA, bio_profond=(bio3['minecraft:dripstone_caves'],
                                                                     bio3['minecraft:deep_dark'], pr.sculk2d,
                                                                     bio3['minecraft:warm_ocean'], r.grand_lagon))
    n = ex.regions(os.path.join(dossier, 'region'), journal)
    journal('entites : %d' % ex.entites(os.path.join(dossier, 'entities'), journal))
    # l'ocean plat autour : meme fond que le bord de l'ile
    bord = np.concatenate([r.h[0], r.h[-1], r.h[:, 0], r.h[:, -1]])
    fond = int(np.median(bord)) + monde_java.DECALAGE_Y
    spawn = meta_spawn(r, li)
    monde_java.level_dat(os.path.join(dossier, 'level.dat'), 'Site B', spawn, SEA + monde_java.DECALAGE_Y, fond)
    temoins = monde_java.points_de_controle(m, pr.b, np.random.default_rng(3))
    temoins += monde_java.temoins_entites(m)
    with open(os.path.join(sortie, 'verif_monde.txt'), 'w') as f:
        for (x, y, z, e) in temoins:
            f.write('%s %s %s %s\n' % (x, y, z, e))
    meta['lagon'] = {'centre': [lagon.cx + monde_java_ORIGINE, lagon.cz + monde_java_ORIGINE],
                     'epave': [lagon.epave_xz[0] + monde_java_ORIGINE, lagon.epave_xz[1] + monde_java_ORIGINE],
                     'fond_y': lagon.fond_monde, 'surface_y': SEA + 15}
    meta['monde'] = {'dossier': 'Site B', 'chunks': n, 'spawn': spawn, 'fond_ocean': fond,
                     'origine': [monde_java.ORIGINE, monde_java.DECALAGE_Y, monde_java.ORIGINE]}
    json.dump(meta, open(os.path.join(sortie, 'site_b_v2.json'), 'w'), ensure_ascii=False, indent=1)
    journal('monde : %d chunks, apparition %s' % (n, spawn))
    return m, r, li, meta, pr


if __name__ == '__main__':
    sortie = sys.argv[1] if len(sys.argv) > 1 else 'sortie'
    m, r, li, meta, pr = main(sortie)
    np.save(os.path.join(sortie, 'profond.npy'), pr.b)
    np.save(os.path.join(sortie, 'blocs.npy'), m.blocs)
    json.dump(m.palette, open(os.path.join(sortie, 'palette.json'), 'w'))
    journal('fini')
