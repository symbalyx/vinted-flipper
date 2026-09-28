"""Genere « Site B » v2, l'ile du spinosaure, en schematics Sponge v2 (.schem, WorldEdit).

Ile de 768 x 768 blocs (160 de haut), en un fichier complet et en 4 tuiles de 384 x 384 a
coller une par une. Idees reprises des jeux de dinosaures et d'horreur :
  - Jurassic Park / Isla Sorna : campus de recherche avec centre d'accueil a charpente, squelette
    dans l'atrium, facade eventree, enclos breche, galerie d'observation sous-marine, portail ;
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

from arbres import Foret, F_JUNGLE
from campus import Campus
from grottes import Grottes
import details
import flore
from lieux import Lieux
from monde import Monde, Decale
from relief import Relief, catmull, distance_polyligne
import rendu

W = L = 768
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
    volcan = np.hypot(r.xx - r.VOLCAN[0], r.zz - r.VOLCAN[1]) < 110
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
    m.blocs[0] = P('minecraft:deepslate')


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
        cx, cz = 384.0, 392.0
        ta, tb = math.atan2(a[1] - cz, a[0] - cx), math.atan2(b[1] - cz, b[0] - cx)
        if tb - ta > math.pi:
            tb -= 2 * math.pi
        elif ta - tb > math.pi:
            tb += 2 * math.pi
        pts = [a]
        for t in np.linspace(0, 1, n)[1:-1]:
            th = ta + (tb - ta) * t
            for rr in range(420, 60, -1):
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
    mangrove_zone = (r.eau > h) & (r.eau - h <= 3) & (r.zz > 560) & ~r.recif & np.isin(
        m.blocs[h.astype(np.int64), np.indices(h.shape)[0], np.indices(h.shape)[1]],
        [i for n_, i in m.palette.items() if 'sand' in n_ or 'mud' in n_ or 'gravel' in n_ or 'clay' in n_])
    def paletuvier(x, z):
        foret.paletuvier(x, z, SEA)
    libre_eau = libre | mangrove_zone
    libre_sauve = libre
    libre = libre_eau
    essai(7, 2, 0.75, 2, paletuvier, lambda x, z: mangrove_zone[z, x])
    libre = libre_sauve
    essai(40, 10, 0.75, 8, foret.emergent, lambda x, z: bas(x, z) and n[z, x] > 0.35)
    essai(70, 18, 0.5, 5, foret.etrangleur, bas)
    essai(10, 3, 0.9, 4, foret.canopee, lambda x, z: terre(x, z) and alt(x, z) < 55 and dist_eau[z, x] > 2)
    # berges et plages : palmiers
    essai(7, 2, 0.6, 2, foret.palmier, lambda x, z: terre(x, z) and alt(x, z) <= 4 and dist_eau[z, x] <= 6)
    # etage bas plus fourni (jeunes arbres, buissons) : il masque la vue sans fermer le passage
    essai(6, 2, 0.7, 3, foret.jeune, lambda x, z: terre(x, z) and alt(x, z) < 70)
    essai(5, 1, 0.6, 2, foret.buisson, lambda x, z: terre(x, z) and alt(x, z) < 75)
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
    choix[libre & (u >= 0.30) & (u < 0.46)] = fougere
    choix[libre & (u >= 0.46) & (u < 0.47)] = m.P('minecraft:melon')
    choix[libre & (u >= 0.47) & (u < 0.49)] = m.P('minecraft:azalea')
    choix[libre & (u >= 0.49) & (u < 0.495)] = m.P('minecraft:flowering_azalea')
    choix[libre & (u >= 0.495) & (u < 0.498)] = m.P('minecraft:blue_orchid')
    choix[libre & (u >= 0.498) & (u < 0.501)] = m.P('minecraft:brown_mushroom')
    k = choix >= 0
    m.blocs[h[k] + 1, zz[k], xx[k]] = choix[k]
    double = libre & (dessus2 == m.AIR) & (u >= 0.52) & (u < 0.66)
    haute = libre & (dessus2 == m.AIR) & (u >= 0.66) & (u < 0.80)
    for msk, b_, h_ in ((double, gf_b, gf_h), (haute, ght_b, ght_h)):
        m.blocs[h[msk] + 1, zz[msk], xx[msk]] = b_
        m.blocs[h[msk] + 2, zz[msk], xx[msk]] = h_
    # cannes a sucre : sol au ras de l'eau avec de l'eau a cote
    eau_haut = (r.eau >= h) & (r.eau > -1) & (r.eau > h)
    voisin = np.zeros_like(eau_haut)
    voisin[1:] |= eau_haut[:-1]; voisin[:-1] |= eau_haut[1:]; voisin[:, 1:] |= eau_haut[:, :-1]; voisin[:, :-1] |= eau_haut[:, 1:]
    canne_sol = np.isin(top, [m.P(s) for s in ('minecraft:grass_block[snowy=false]', 'minecraft:sand', 'minecraft:mud',
                                              'minecraft:dirt', 'minecraft:podzol[snowy=false]')])
    cannes = voisin & canne_sol & (h == SEA) & (m.blocs[np.minimum(h + 1, H - 1), zz, xx] == m.AIR) & (rng.random(h.shape) < 0.35)
    for dy in range(1, 4):
        sel = cannes & (rng.random(h.shape) < (1.0 if dy == 1 else 0.6 if dy == 2 else 0.3))
        m.blocs[h[sel] + dy, zz[sel], xx[sel]] = m.P('minecraft:sugar_cane[age=0]')
        cannes = sel
    # eau : herbiers, kelp, nenuphars, coraux
    prof = r.eau - h
    fond_libre = (r.eau > h) & (m.blocs[np.minimum(h + 1, H - 1), zz, xx] == m.P(EAU))
    u = rng.random(h.shape)
    herb = fond_libre & (prof >= 2) & (u < 0.18)
    m.blocs[h[herb] + 1, zz[herb], xx[herb]] = m.P('minecraft:seagrass')
    kelp = fond_libre & (prof >= 5) & (u > 0.975) & ~r.riviere & ~r.lac
    for z, x in zip(*np.nonzero(kelp)):
        hk = int(h[z, x]); top_k = int(r.eau[z, x]) - int(rng.integers(1, 4))
        for y in range(hk + 1, top_k):
            m.blocs[y, z, x] = m.P('minecraft:kelp_plant')
        m.blocs[top_k, z, x] = m.P('minecraft:kelp[age=20]')
    nenu = (r.riviere | r.lac) & (prof <= 4) & (prof >= 1) & (rng.random(h.shape) < 0.05)
    m.blocs[np.minimum(r.eau[nenu] + 1, H - 1), zz[nenu], xx[nenu]] = m.P('minecraft:lily_pad')
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
    return b, pal


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
    chute = marche(r)
    foret = Foret(m, (r.h + 1).astype(np.int32), rng)
    # ------------------------------------------------ campus
    journal('campus')
    ox, oz = r.CAMPUS
    G = r.G
    v = Decale(m, ox, G, oz)
    Campus(v, foret).construire(chenal_nord=16)
    campus_x0, campus_z0, campus_x1, campus_z1 = ox - 8, oz - 4, ox + 146, oz + 136
    # ------------------------------------------------ lieux
    journal('lieux')
    li = Lieux(m, r, rng)
    li.ajoute('Campus Site B', ox + 70, oz + 60, 0)
    porte = (ox + 58, oz + 126)
    c = li.cote(porte[0] + 20, porte[1] + 10, 0, 1)
    dock = li.ponton(c[0], c[1] - 2)
    # tour : point le plus haut de la crete, vers le milieu
    zone = r.h[300:420, 110:190]
    iz, ix = np.unravel_index(np.argmax(zone), zone.shape)
    tour = (110 + ix, 300 + iz)
    li.tour(*tour)
    heli = (262, 196)
    li.helicoptere(*heli)
    camp = (408, 238)
    li.campement(*camp)
    lagon_bord = li.cote(250, 560, -0.7, 0.7) or (215, 600)
    bung = [(lagon_bord[0] + 10, lagon_bord[1] - 12), (lagon_bord[0] + 22, lagon_bord[1] - 22),
            (lagon_bord[0] + 2, lagon_bord[1] - 26)]
    li.bungalows(bung)
    relais = (652, 492)
    zone = r.h[450:540, 610:700]
    iz, ix = np.unravel_index(np.argmax(zone), zone.shape)
    relais = (610 + ix, 450 + iz)
    li.relais(*relais)
    rec = np.argwhere(r.recif)
    ez, ex = rec[len(rec) // 3]
    li.epave(int(ex) - 6, int(ez))
    li.repaire(int(r.ILOT[0]), int(r.ILOT[1]))
    li.grotte(chute[0] - chute[2] * 2, chute[1] - chute[3] * 2, -chute[2], -chute[3], SEA)
    cascade(m, r, chute)
    li.affut(int(r.LAC[0]) - 62, int(r.LAC[1]) - 6)
    li.passerelle([(372, 600), (356, 614), (344, 626), (336, 642)])
    # ------------------------------------------------ les autres lieux, repartis sur toute l'ile
    def site(cx, cz, R, t, eau_ok=False, tz=None):
        """Point le plus plat (ecart-type des hauteurs sur un carre de demi-cote t) a moins de R
        de (cx, cz), sur la terre ferme, loin des rivieres."""
        mieux, best = None, 1e9
        for z in range(cz - R, cz + R + 1, 3):
            for x in range(cx - R, cx + R + 1, 3):
                u = t if tz is None else tz
                if not (t + 2 <= x < W - t - 2 and u + 2 <= z < L - u - 2):
                    continue
                zone = r.h[z - u:z + u + 1, x - t:x + t + 1]
                mouille = (r.eau[z - u:z + u + 1, x - t:x + t + 1] > zone).mean()
                if mouille > (0.5 if eau_ok else 0.0):
                    continue
                cout = float(zone.std()) + 0.02 * math.hypot(x - cx, z - cz)
                if cout < best:
                    best, mieux = cout, (x, z)
        return mieux or (cx, cz)
    cap = li.cote(345, 330, 0, -1)
    phare = (cap[0], cap[1] + 14)
    li.phare(*phare)
    temple = site(205, 262, 26, 20)
    li.temple(*temple)
    herb = site(360, 302, 20, 30)
    li.enclos_herbivores(herb[0] - 34, herb[1] - 24, herb[0] + 34, herb[1] + 24)
    li.ajoute('', herb[0], herb[1], 30)
    est = li.cote(640, 395, 1, 0)
    village = (est[0] + 4, est[1] + 22)
    li.village(*village)
    vx_, vz_ = r.VOLCAN
    zone = r.h[int(vz_) - 30:int(vz_) + 10, int(vx_) + 28:int(vx_) + 48]
    iz, ix = np.unravel_index(np.argmax(zone), zone.shape)
    obs = (int(vx_) + 28 + ix, int(vz_) - 30 + iz)
    li.observatoire(*obs)
    voliere = site(468, 160, 40, 22)
    li.voliere(*voliere)
    piste_c = (586, 522)
    li.piste(546, 522, 626, avion=(588, 562))
    li.ajoute('', piste_c[0], piste_c[1], 48)
    check = (porte[0] + 6, porte[1] + 40)
    bunker = site(268, 505, 24, 12)
    li.bunker(*bunker)
    # entree de la mine : pied du versant est de la crete (le terrain monte de 10 blocs en 12)
    mine = (196, 450)
    for mx_ in range(250, 150, -1):
        if r.h[450, mx_ - 12] - r.h[450, mx_] >= 10 and r.eau[450, mx_] <= r.h[450, mx_]:
            mine = (mx_, 450)
            break
    li.mine(mine[0], mine[1], -1, 0.0)
    serres = site(392, 462, 16, 20)
    li.serres(serres[0] - 20, serres[1] - 10)
    cimet = (camp[0] + 18, camp[1] + 16)
    li.cimetiere(*cimet)
    # pont suspendu au-dessus de la gorge de la cascade
    gx_, gz_ = chute[0] + chute[2] * 14, chute[1] + chute[3] * 14
    px_, pz_ = -chute[3], chute[2]
    bords = []
    for sgn in (-1, 1):
        for d in range(4, 40):
            qx, qz = int(gx_ + px_ * d * sgn), int(gz_ + pz_ * d * sgn)
            if r.h[qz, qx] > SEA + 22:
                bords.append((qx, qz, int(r.h[qz, qx])))
                break
    if len(bords) == 2:
        yb = min(bords[0][2], bords[1][2]) + 1
        li.pont_suspendu(bords[0][:2], bords[1][:2], yb)
    journal('pistes')
    pi = Pistes(m, r)
    pi.trace([porte, (porte[0] + 6, porte[1] + 40), (dock[0], (porte[1] + dock[1]) // 2), dock], 2.5, route=True)
    pi.trace([(ox - 6, oz + 64), (420, 420), (372, 404), (300, 380), (240, 360), (tour[0] + 8, tour[1] + 4)], 1.8)
    pi.trace([tour, (tour[0] + 20, 280), (220, 240), heli], 1.6)
    pi.trace([(ox + 30, oz - 6), (440, 300), camp], 1.8)
    pi.trace([camp, (460, 236), (476, 250)], 1.5)
    pi.trace([(ox + 146, oz + 80), (600, 470), relais], 1.8)
    pi.trace([tour, (170, 450), (200, 520), bung[1]], 1.6)
    pi.trace([(porte[0], porte[1] + 30), (430, 560), (372, 600)], 1.6)
    pi.trace([camp, (390, 180), phare], 1.6)
    pi.trace([heli, (230, 240), temple], 1.6)
    pi.trace([tour, (175, 300), temple], 1.4)
    pi.trace([(372, 404), (365, 360), (herb[0], herb[1] + 26)], 1.6)
    # le village de pecheurs ne se rejoint plus par la jungle : on longe la plage depuis le ponton
    # et la piste d'atterrissage, a decouvert, a portee de l'eau
    pi.trace(pi.cotier(dock, village), 1.4)
    pi.trace(pi.cotier(bung[1], (336, 642)), 1.2)             # des bungalows a la station du delta
    pi.trace(pi.cotier(phare, voliere), 1.2)                 # du phare vers la voliere, par la cote nord
    pi.trace([camp, (440, 200), voliere], 1.5)
    pi.trace([camp, (470, 200), (520, 150), (570, 140), obs], 1.3)
    pi.trace([(dock[0] + 2, (porte[1] + dock[1]) // 2 - 4), (546, piste_c[1])], 1.8)
    pi.trace([(372, 600), (300, 560), bunker], 1.6)
    pi.trace([(170, 450), mine], 1.4)
    pi.trace([(ox - 6, oz + 110), (serres[0] + 22, serres[1])], 1.6)
    pi.trace([camp, cimet], 1.2)
    li.checkpoint(*check)
    # vehicules abandonnes le long des pistes (plus de poteaux indicateurs : pas de panneaux)
    li.jeep(560, 548, 'east'); li.jeep(300, 372, 'west', renversee=True); li.jeep(446, 290, 'north')
    li.jeep(640, 470, 'south', renversee=True); li.jeep(200, 470, 'north')
    # ------------------------------------------------ grottes, gouffres et nids
    journal('grottes')
    zz, xx = r.zz, r.xx
    protege = (xx >= campus_x0 - 24) & (xx <= campus_x1 + 24) & (zz >= campus_z0 - 24) & (zz <= campus_z1 + 24)
    for nom, x, z, ray in li.poi:
        protege |= np.hypot(xx - x, zz - z) < max(ray, 12) + 16
    protege_lieux = protege.copy()                 # lieux et campus seulement (pour les falaises)
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
    zc = r.h[330:480, 110:210].astype(float) * ~protege_dur[330:480, 110:210]
    iz, ix = np.unravel_index(np.argmax(zc), zc.shape)
    mine_v = (110 + int(ix), 330 + int(iz))
    journal('mine abandonnee : %d couloirs' % gr.mine_vanilla(mine_v[0], mine_v[1], SEA + 8))
    gr.rugosite()
    gr.noyer()
    journal('minerais : %s' % gr.minerais())
    gr.decorer()
    gr.formations()
    gr.porches_rocheux()
    gr.nids_dans_les_salles(2)
    gr.nid_antre()
    if antre:
        li.ajoute('Antre (acces en plongee par le trou bleu du lagon)', antre[0], antre[2], 0)
    li.ajoute('Mine abandonnee (galeries, sous la crete)', mine_v[0], mine_v[1], 0)
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
    libre &= ~pi.masque
    zz, xx = r.zz, r.xx
    libre &= ~((xx >= campus_x0 - 6) & (xx <= campus_x1 + 6) & (zz >= campus_z0 - 6) & (zz <= campus_z1 + 6))
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
    libre_pentes &= ~pi.masque & ~clair
    libre_pentes &= ~((xx >= campus_x0 - 6) & (xx <= campus_x1 + 6) & (zz >= campus_z0 - 6) & (zz <= campus_z1 + 6))
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
    journal('lianes des falaises : %d blocs' % flore.lianes_falaises(m, r, rng))
    journal('recif en volume : %d blocs de corail' % details.recif(m, r, rng))
    journal('clotures ancrees au sol : %d' % m.ancrer_clotures())
    journal('connexions (vitres, barrieres)')
    m.connecter()
    journal('suspendus : lianes corrigees / retirees, propagules retirees : %s' % (m.nettoyer_suspendus(),))
    bio, bio_pal = biomes(r, bambou)
    # ------------------------------------------------ ecriture
    journal('ecriture')
    meta = {'W': W, 'H': H, 'L': L, 'SEA': SEA, 'coller_y': 63 - SEA, 'campus': [ox, G, oz],
            'lieux': [(n, x, z) for n, x, z, _ in li.poi],
            'entrees_grottes': [(int(x), int(r.h[z, x]), int(z)) for x, z in gr.entrees],
            'trous_bleus': [(int(x), int(z), round(float(R)), int(bas)) for x, z, R, bas in r.gouffres]}
    json.dump(meta, open(os.path.join(sortie, 'site_b_v2.json'), 'w'), ensure_ascii=False, indent=1)
    taille = m.ecrire(os.path.join(sortie, 'site_b_v2.schem'), biomes=bio, bio_palette=bio_pal, nom='Site B v2')
    journal('site_b_v2.schem : %.1f Mo' % (taille / 1e6))
    for i in range(2):
        for j in range(2):
            t = m.ecrire(os.path.join(sortie, 'site_b_v2_%d_%d.schem' % (i, j)), 384 * i, 384 * j, 384 * (i + 1), 384 * (j + 1),
                         biomes=bio, bio_palette=bio_pal, nom='Site B v2 tuile %d-%d' % (i, j))
            journal('tuile %d-%d : %.1f Mo' % (i, j, t / 1e6))
    np.save(os.path.join(sortie, 'grottes.npy'), carte_grottes)
    return m, r, li, meta


if __name__ == '__main__':
    sortie = sys.argv[1] if len(sys.argv) > 1 else 'sortie'
    m, r, li, meta = main(sortie)
    np.save(os.path.join(sortie, 'blocs.npy'), m.blocs)
    json.dump(m.palette, open(os.path.join(sortie, 'palette.json'), 'w'))
    journal('fini')
