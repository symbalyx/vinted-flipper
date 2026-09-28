"""La jungle, pas une foret : ce qui manquait entre les arbres.

- clairieres : trouees ou la lumiere tombe, herbes hautes, fougeres geantes et fleurs ; on y
  voit loin... et on y est vu ;
- mares : cuvettes boueuses d'eau stagnante, nenuphars, grandes feuilles, cannes ;
- rochers : blocs moussus epars, certains gros comme une cabane ;
- rideaux de lianes : elles pendent des feuillages sur 3 a 14 blocs (le signe d'une jungle) ;
- lianes des falaises : les parois raides se couvrent de lianes par plaques ;
- fleurs des clairieres, a poser apres le sous-bois.

Tout en blocs vanilla 1.20.1 : pas de mod a installer.
"""
import math

import numpy as np

EAU = 'minecraft:water[level=0]'
FACES = (('east', 1, 0), ('west', -1, 0), ('south', 0, 1), ('north', 0, -1))


def vigne(face):
    return 'minecraft:vine[east=%s,north=%s,south=%s,up=false,west=%s]' % tuple(
        'true' if f == face else 'false' for f in ('east', 'north', 'south', 'west'))


def clairieres(r, rng, libre, n=34):
    """Disques de 7 a 16 blocs sans arbre, sur terrain plat."""
    L, W = r.h.shape
    masque = np.zeros((L, W), bool)
    zs, xs = np.nonzero(libre & (r.pente < 0.8))
    poses = []
    for k in rng.permutation(len(zs)):
        x, z = int(xs[k]), int(zs[k])
        if any(math.hypot(x - a, z - b) < 60 for a, b in poses):
            continue
        R = rng.uniform(7, 16)
        d = np.hypot(r.xx - x, r.zz - z) * (1 + 0.25 * np.sin(np.arctan2(r.zz - z, r.xx - x) * 3 + x))
        masque |= d < R
        poses.append((x, z))
        if len(poses) >= n:
            break
    return masque & libre


def mares(m, r, rng, libre, n=40):
    """Cuvettes d'eau stagnante de 3 a 7 blocs, 1 a 2 de fond, sur replat de jungle."""
    faites = 0
    zs, xs = np.nonzero(libre & (r.pente < 0.5) & (r.h > r.SEA + 2))
    poses = []
    for k in rng.permutation(len(zs)):
        x, z = int(xs[k]), int(zs[k])
        if any(math.hypot(x - a, z - b) < 45 for a, b in poses):
            continue
        R = rng.uniform(3, 7)
        Ri = int(R) + 2
        if not (Ri + 2 <= x < m.W - Ri - 2 and Ri + 2 <= z < m.L - Ri - 2):
            continue
        zone = r.h[z - Ri:z + Ri + 1, x - Ri:x + Ri + 1]
        if not libre[z - Ri:z + Ri + 1, x - Ri:x + Ri + 1].all():
            continue
        niveau = int(zone.min()) - 1                    # surface de l'eau, sous le bord le plus bas
        for dz in range(-Ri, Ri + 1):
            for dx in range(-Ri, Ri + 1):
                d = math.hypot(dx, dz) * (1 + 0.2 * math.sin(math.atan2(dz, dx) * 4 + x))
                px, pz = x + dx, z + dz
                hs = int(r.h[pz, px])
                if d <= R:
                    fond = niveau - (2 if d < R * 0.5 else 1)
                    m.boite(px, fond + 1, pz, px, hs + 3, pz, 'minecraft:air')
                    m.pose(px, fond, pz, 'minecraft:mud' if rng.random() < 0.7 else 'minecraft:clay')
                    m.boite(px, fond + 1, pz, px, niveau, pz, EAU)
                    r.h[pz, px] = fond
                    r.eau[pz, px] = niveau
                    u = rng.random()
                    if u < 0.18:
                        m.pose(px, niveau + 1, pz, 'minecraft:lily_pad')
                    elif u < 0.26 and niveau - fond == 1:
                        m.pose(px, fond + 1, pz, 'minecraft:seagrass')
                elif d <= R + 1.5:
                    # berge boueuse, grandes feuilles et cannes
                    if hs >= niveau:
                        m.boite(px, niveau, pz, px, hs, pz, 'minecraft:mud')
                        m.boite(px, niveau + 1, pz, px, hs + 3, pz, 'minecraft:air')
                        r.h[pz, px] = niveau
                        u = rng.random()
                        if u < 0.25:
                            f = ['north', 'south', 'east', 'west'][rng.integers(0, 4)]
                            m.pose(px, niveau + 1, pz, 'minecraft:big_dripleaf_stem[facing=%s,waterlogged=false]' % f)
                            m.pose(px, niveau + 2, pz, 'minecraft:big_dripleaf[facing=%s,tilt=none,waterlogged=false]' % f)
                        elif u < 0.45:
                            for k_ in range(int(rng.integers(1, 4))):
                                m.pose(px, niveau + 1 + k_, pz, 'minecraft:sugar_cane[age=0]')
        poses.append((x, z))
        faites += 1
        if faites >= n:
            break
    return faites, poses


def rochers(m, r, rng, libre, n=320):
    """Blocs erratiques moussus : de la roche parmi les arbres, pour casser la monotonie et
    offrir des caches."""
    mats = ['minecraft:mossy_cobblestone', 'minecraft:stone', 'minecraft:andesite', 'minecraft:mossy_cobblestone',
            'minecraft:cobblestone', 'minecraft:tuff']
    zs, xs = np.nonzero(libre)
    faits = 0
    for k in rng.choice(len(zs), min(n * 3, len(zs)), replace=False):
        x, z = int(xs[k]), int(zs[k])
        y = int(r.h[z, x]) + 1
        gros = rng.random() < 0.12
        rx = rng.uniform(2.5, 4.5) if gros else rng.uniform(0.9, 2.2)
        mat = mats[rng.integers(0, len(mats))]
        m.ellipsoide(x + 0.5, y + (0.5 if gros else 0.2), z + 0.5, rx, rx * rng.uniform(0.6, 0.9), rx * rng.uniform(0.7, 1.2),
                     mat, seulement_air=True, bruit=0.4, rng=rng, bas=y - 1)
        # mousse et fougeres sur le dessus
        for dz in range(-int(rx), int(rx) + 1):
            for dx in range(-int(rx), int(rx) + 1):
                for yy in range(y + int(rx) + 1, y - 1, -1):
                    if m.get(x + dx, yy, z + dz) != m.AIR and m.get(x + dx, yy + 1, z + dz) == m.AIR:
                        if 'cobble' in m.nom(m.get(x + dx, yy, z + dz)) or 'stone' in m.nom(m.get(x + dx, yy, z + dz)):
                            u = rng.random()
                            if u < 0.45:
                                m.pose(x + dx, yy + 1, z + dz, 'minecraft:moss_carpet')
                            elif u < 0.55:
                                m.pose(x + dx, yy + 1, z + dz, 'minecraft:fern')
                        break
        faits += 1
        if faits >= n:
            break
    return faits


def rideaux_lianes(m, rng, proba=0.07):
    """Lianes qui pendent des feuillages : a cote d'un bloc de feuilles, dans l'air, on
    accroche une liane (face tournee vers les feuilles) et on la laisse pendre de 3 a 14 blocs,
    tant qu'il y a de l'air. Chaque troncon est porte par celui du dessus (regle vanilla)."""
    A = m.AIR
    feuilles = np.zeros(len(m.palette) + 1, bool)
    for nom, i in m.palette.items():
        feuilles[i] = 'leaves' in nom
    n = 0
    ids = {f: m.P(vigne(f)) for f, _, _ in FACES}
    for y in range(m.H - 2, 4, -1):
        couche = m.blocs[y]
        f = feuilles[couche]
        if not f.any():
            continue
        air = couche == A
        for face, dx, dz in FACES:
            # la cellule d'air a cote d'une feuille situee du cote `face`
            voisin = np.roll(np.roll(f, -dz, 0), -dx, 1)
            cand = air & voisin & (rng.random(air.shape) < proba)
            cand[:3] = cand[-3:] = False
            cand[:, :3] = cand[:, -3:] = False
            for z, x in zip(*np.nonzero(cand)):
                longueur = int(rng.integers(3, 15))
                for k in range(longueur):
                    yy = y - k
                    if yy < 3 or m.blocs[yy, z, x] != A:
                        break
                    m.blocs[yy, z, x] = ids[face]
                    n += 1
    return n


def lianes_falaises(m, r, rng):
    """Les parois raides se couvrent de lianes par plaques : sur une cellule d'air collee a une
    paroi rocheuse, une liane accrochee a la paroi (portee a chaque etage par la roche)."""
    A = m.AIR
    roche = np.zeros(len(m.palette) + 1, bool)
    for nom, i in m.palette.items():
        base = nom.split('[')[0].replace('minecraft:', '')
        roche[i] = base in ('stone', 'andesite', 'tuff', 'granite', 'diorite', 'cobblestone', 'mossy_cobblestone', 'dirt',
                            'coarse_dirt', 'moss_block', 'basalt', 'deepslate')
    raide = r.pente > 2.0
    for _ in range(2):
        raide = raide | np.roll(raide, 1, 0) | np.roll(raide, -1, 0) | np.roll(raide, 1, 1) | np.roll(raide, -1, 1)
    plaques = r.n.fbm(18, 2, 77) > 0.52
    zone = raide & plaques & (r.eau <= r.h)
    ids = {f: m.P(vigne(f)) for f, _, _ in FACES}
    n = 0
    y0 = max(3, int(r.h[zone].min()) - 30) if zone.any() else m.H
    for y in range(y0, m.H - 2):
        couche = m.blocs[y]
        air = (couche == A) & zone & (y >= r.h - 25)          # la paroi, pas les grottes en dessous
        if not air.any():
            continue
        for face, dx, dz in FACES:
            voisin = np.roll(np.roll(roche[couche], -dz, 0), -dx, 1)
            c = air & voisin & (rng.random(air.shape) < 0.85)
            couche[c] = ids[face]
            air &= ~c
            n += int(c.sum())
    return n


def fleurs_clairieres(m, r, rng, masque):
    """Apres le sous-bois : dans les clairieres, herbes hautes et fougeres geantes denses,
    fleurs de jungle, melons."""
    h = r.h.astype(np.int64)
    zz, xx = np.nonzero(masque)
    A = m.AIR
    simples = ['minecraft:blue_orchid', 'minecraft:allium', 'minecraft:azure_bluet', 'minecraft:oxeye_daisy',
               'minecraft:poppy', 'minecraft:cornflower', 'minecraft:torchflower', 'minecraft:lily_of_the_valley']
    n = 0
    for z, x in zip(zz, xx):
        y = int(h[z, x])
        sol = m.nom(m.get(x, y, z))
        if not any(t in sol for t in ('grass_block', 'podzol', 'moss_block', 'rooted_dirt', 'coarse_dirt')):
            continue
        if m.get(x, y + 2, z) != A:
            continue
        u = rng.random()
        if u < 0.40:
            m.pose(x, y + 1, z, 'minecraft:tall_grass[half=lower]'); m.pose(x, y + 2, z, 'minecraft:tall_grass[half=upper]')
        elif u < 0.62:
            m.pose(x, y + 1, z, 'minecraft:large_fern[half=lower]'); m.pose(x, y + 2, z, 'minecraft:large_fern[half=upper]')
        elif u < 0.70:
            m.pose(x, y + 1, z, simples[rng.integers(0, len(simples))])
        elif u < 0.73:
            m.pose(x, y + 1, z, 'minecraft:pink_petals[facing=north,flower_amount=4]')
        elif u < 0.745:
            m.pose(x, y + 1, z, 'minecraft:melon')
        elif u < 0.76:
            m.pose(x, y + 1, z, 'minecraft:rose_bush[half=lower]'); m.pose(x, y + 2, z, 'minecraft:rose_bush[half=upper]')
        elif u < 0.775:
            m.pose(x, y + 1, z, 'minecraft:peony[half=lower]'); m.pose(x, y + 2, z, 'minecraft:peony[half=upper]')
        n += 1
    return n
