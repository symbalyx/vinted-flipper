"""Genere « Site B », l'ile du spinosaure, en schematic Sponge v2 (.schem, WorldEdit).

Idees reprises des jeux de dinosaures et d'horreur :
  - Jurassic Park / Isla Nublar : complexe de recherche InGen-like, enclos de confinement
    breche, ponton d'arrivee, tour de guet, helicoptere abattu ;
  - Resident Evil / Dino Crisis : sous-sol inonde et generateur de secours, couloirs etroits
    ou l'on se croit a l'abri, recits laisses sur des panneaux ;
  - Alien Isolation : la creature a une route cachee jusque dans le batiment (enclos ->
    tunnel de drainage noye -> sous-sol), on l'entend avant de la voir ;
  - The Isle : une jungle dont la canopee plonge le sol dans la penombre, des rivieres
    profondes comme territoire, pas de zone vraiment sure.

Tout est dimensionne pour le spinosaure (boite 3.4 x 5 blocs) : troncs espaces de 10 a 12
blocs, canopee au-dessus de 14 blocs, sous-bois non bloquant (fougeres, herbes), riviere
de 16 a 22 blocs de large et 7 de profondeur (il s'y submerge), couloirs du laboratoire a
2 blocs de large (il n'y entre pas) mais sous-sol et enclos a sa taille.

Usage : python3 generer_ile.py [sortie.schem]
"""
import json
import math
import sys

import numpy as np

import nbt

W = L = 384          # x, z
H = 128              # y
SEA = 48             # niveau de la mer dans le schematic (coller a y=15 -> mer a 63)
G = SEA + 3          # sol du laboratoire (51)
rng = np.random.default_rng(20260925)

# ============================================================== palette et blocs

palette = {}
blocs = np.zeros((H, L, W), dtype=np.uint16)
entites_blocs = []


def P(etat):
    if etat not in palette:
        palette[etat] = len(palette)
    return palette[etat]


AIR = P('minecraft:air')
PIERRE = P('minecraft:stone')
TERRE = P('minecraft:dirt')
EAU = P('minecraft:water[level=0]')
FEUILLE = P('minecraft:jungle_leaves[distance=1,persistent=true,waterlogged=false]')
TRONC = P('minecraft:jungle_log[axis=y]')


def pose(x, y, z, etat):
    if 0 <= x < W and 0 <= y < H and 0 <= z < L:
        blocs[y, z, x] = P(etat) if isinstance(etat, str) else etat


def boite(x0, y0, z0, x1, y1, z1, etat):
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    x0, y0, z0 = max(x0, 0), max(y0, 0), max(z0, 0)
    x1, y1, z1 = min(x1, W - 1), min(y1, H - 1), min(z1, L - 1)
    if x0 <= x1 and y0 <= y1 and z0 <= z1:
        blocs[y0:y1 + 1, z0:z1 + 1, x0:x1 + 1] = P(etat) if isinstance(etat, str) else etat


def murs(x0, y0, z0, x1, y1, z1, etat):
    boite(x0, y0, z0, x1, y1, z0, etat); boite(x0, y0, z1, x1, y1, z1, etat)
    boite(x0, y0, z0, x0, y1, z1, etat); boite(x1, y0, z0, x1, y1, z1, etat)


def texte(s):
    return json.dumps({'text': s}, ensure_ascii=False)


def panneau(x, y, z, facing, lignes, mural=True, bois='oak'):
    """Panneau 1.20 (front_text). `facing` : ou regarde la face ecrite."""
    lignes = (list(lignes) + ['', '', '', ''])[:4]
    if mural:
        pose(x, y, z, 'minecraft:%s_wall_sign[facing=%s,waterlogged=false]' % (bois, facing))
    else:
        rot = {'south': 0, 'west': 4, 'north': 8, 'east': 12}[facing]
        pose(x, y, z, 'minecraft:%s_sign[rotation=%d,waterlogged=false]' % (bois, rot))
    face = nbt.Compound({'messages': nbt.List('string', [nbt.String(texte(l)) for l in lignes]),
                         'color': nbt.String('black'), 'has_glowing_text': nbt.Byte(0)})
    vide = nbt.Compound({'messages': nbt.List('string', [nbt.String(texte('')) for _ in range(4)]),
                         'color': nbt.String('black'), 'has_glowing_text': nbt.Byte(0)})
    entites_blocs.append(nbt.Compound({'Pos': nbt.IntArray([x, y, z]), 'Id': nbt.String('minecraft:sign'),
                                       'front_text': face, 'back_text': vide, 'is_waxed': nbt.Byte(1)}))


def coffre(x, y, z, facing, objets):
    pose(x, y, z, 'minecraft:chest[facing=%s,type=single,waterlogged=false]' % facing)
    items = [nbt.Compound({'Slot': nbt.Byte(i), 'id': nbt.String(o), 'Count': nbt.Byte(n)})
             for i, (o, n) in enumerate(objets)]
    entites_blocs.append(nbt.Compound({'Pos': nbt.IntArray([x, y, z]), 'Id': nbt.String('minecraft:chest'),
                                       'Items': nbt.List('compound', items)}))


def barreaux(x0, y, z0, x1, z1, etat='minecraft:iron_bars'):
    """Rangee de barreaux (ou vitres) en ligne, avec les connexions explicites."""
    if z0 == z1:
        for x in range(min(x0, x1), max(x0, x1) + 1):
            pose(x, y, z0, '%s[east=true,north=false,south=false,waterlogged=false,west=true]' % etat)
    else:
        for z in range(min(z0, z1), max(z0, z1) + 1):
            pose(x0, y, z, '%s[east=false,north=true,south=true,waterlogged=false,west=false]' % etat)


# ============================================================== bruit

def bruit(echelle, graine):
    g = np.random.default_rng(graine)
    n = int(max(W, L) / echelle) + 3
    grille = g.random((n, n))
    ys, xs = np.mgrid[0:L, 0:W] / echelle
    x0, y0 = np.floor(xs).astype(int), np.floor(ys).astype(int)
    fx, fy = xs - x0, ys - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = grille[y0, x0], grille[y0, x0 + 1]
    c, d = grille[y0 + 1, x0], grille[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(echelle, octaves, graine):
    t, amp, tot = 0, 1.0, 0
    for o in range(octaves):
        t = t + amp * bruit(echelle / 2 ** o, graine + o)
        tot += amp
        amp *= 0.5
    return t / tot


def lisse(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ============================================================== relief

zz, xx = np.mgrid[0:L, 0:W].astype(float)
CX, CZ = 192.0, 192.0
dist = np.hypot(xx - CX, zz - CZ)
rayon = 150 + 36 * (fbm(90, 3, 1) - 0.5)
c = (rayon - dist) / 30.0                                   # >0 : terre

sol = np.where(c < 0, SEA - 4 - np.minimum(16, -c * 14), 0.0)
terre = SEA + 1 + 3 * lisse(0, 0.8, c) + 10 * (fbm(60, 4, 2) - 0.35) * lisse(0.3, 1.5, c)
sol = np.where(c >= 0, terre, sol)

# montagne au nord-est : plateau (lac de cratere) et falaise verticale a l'ouest
MX, MZ, PLATEAU = 272.0, 108.0, SEA + 56
dm = np.hypot(xx - MX, zz - MZ)
angle = np.degrees(np.arctan2(zz - MZ, xx - MX))            # 180 = ouest
ouest = np.abs(((angle - 180) + 180) % 360 - 180) < 26
pente = PLATEAU - (PLATEAU - SEA - 4) * lisse(30, 82, dm) + 10 * (fbm(24, 3, 3) - 0.5) * lisse(30, 60, dm)
pente = np.where(ouest & (dm > 31), np.minimum(pente, SEA + 3 + 4 * fbm(20, 2, 4)), pente)
sol = np.where(dm < 82, np.maximum(sol, pente), sol)
LAC = PLATEAU - 4
dans_lac = dm < 17
sol = np.where(dans_lac, LAC - 1 - 7 * (1 - (dm / 17) ** 2), sol)
# encoche de la cascade : chenal du lac jusqu'au bord de la falaise, plein ouest
encoche = (np.abs(zz - MZ) <= 3) & (xx >= MX - 31) & (xx <= MX - 15)
sol = np.where(encoche, np.minimum(sol, LAC - 3), sol)

# ============================================================== riviere

points = [(MX - 40, MZ + 2), (228, 126), (216, 146), (220, 166), (219, 190), (214, 214),
          (200, 238), (176, 258), (148, 274), (118, 294), (88, 316), (60, 338), (40, 356)]


def catmull(pts, n=16):
    out = []
    p = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(p) - 2):
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p[i][k]) + (-p[i - 1][k] + p[i + 1][k]) * t
                                    + (2 * p[i - 1][k] - 5 * p[i][k] + 4 * p[i + 1][k] - p[i + 2][k]) * t2
                                    + (-p[i - 1][k] + 3 * p[i][k] - 3 * p[i + 1][k] + p[i + 2][k]) * t3)
                             for k in range(2)))
    out.append(pts[-1])
    return out


ligne = catmull(points)
driv = np.full((L, W), 1e9)
avance = np.zeros((L, W))                                     # 0 amont -> 1 aval
for i in range(len(ligne) - 1):
    (ax, az), (bx, bz) = ligne[i], ligne[i + 1]
    vx, vz = bx - ax, bz - az
    l2 = vx * vx + vz * vz
    t = np.clip(((xx - ax) * vx + (zz - az) * vz) / l2, 0, 1)
    d = np.hypot(xx - (ax + t * vx), zz - (az + t * vz))
    mieux = d < driv
    driv = np.where(mieux, d, driv)
    avance = np.where(mieux, (i + t) / (len(ligne) - 1), avance)
demi = 8 + 4 * avance                                          # 16 blocs en amont, 24 a l'embouchure
riviere = driv < demi
lit = SEA - 7 * (1 - (driv / demi) ** 2)
sol = np.where(riviere, np.minimum(sol, np.floor(lit)), sol)
# vallee : les berges descendent en pente douce vers l'eau
berge = (driv >= demi) & (driv < demi + 22) & (c > 0) & ~(dm < 32)
sol = np.where(berge, np.minimum(sol, SEA + 1 + (driv - demi) * 0.35 + 2 * fbm(20, 2, 5)), sol)
# bassin au pied de la cascade
bassin = np.hypot(xx - (MX - 38), zz - MZ) < 10
sol = np.where(bassin, np.minimum(sol, SEA - 7), sol)

# ============================================================== plate-forme du laboratoire

LAB = (118, 158, 214, 232)                                      # x0, z0, x1, z1 (hors riviere)
dans_lab = (xx >= LAB[0]) & (xx <= LAB[2]) & (zz >= LAB[1]) & (zz <= LAB[3]) & ~riviere
marge_lab = ((xx >= LAB[0] - 10) & (xx <= LAB[2] + 10) & (zz >= LAB[1] - 10) & (zz <= LAB[3] + 10)) & ~dans_lab & ~riviere
sol = np.where(dans_lab, G, sol)
dlab = np.maximum(np.maximum(LAB[0] - xx, xx - LAB[2]), np.maximum(LAB[1] - zz, zz - LAB[3]))
sol = np.where(marge_lab, G + (sol - G) * lisse(0, 10, dlab), sol)

sol = np.round(sol).astype(int)
sol = np.clip(sol, 2, H - 20)

# ============================================================== materiaux du sol

eau_niv = np.full((L, W), -1)
eau_niv = np.where(sol < SEA, SEA, eau_niv)
eau_niv = np.where(dans_lac, LAC, eau_niv)
eau_niv = np.where(encoche, LAC, eau_niv)

raide = np.zeros((L, W), dtype=bool)
gz, gx = np.gradient(sol.astype(float))
raide = np.hypot(gx, gz) > 1.6
plage = (c >= -0.2) & (c < 0.35) & (sol <= SEA + 3) & ~riviere
haut = sol > SEA + 38

SABLE, GRES, HERBE = P('minecraft:sand'), P('minecraft:sandstone'), P('minecraft:grass_block[snowy=false]')
BOUE, GRAVIER, ARGILE = P('minecraft:mud'), P('minecraft:gravel'), P('minecraft:clay')
PODZOL, TERRE_GROSSE, MOUSSE = P('minecraft:podzol[snowy=false]'), P('minecraft:coarse_dirt'), P('minecraft:moss_block')
ANDESITE, TUF = P('minecraft:andesite'), P('minecraft:tuff')

dessus = np.full((L, W), HERBE, dtype=np.uint16)
sous = np.full((L, W), TERRE, dtype=np.uint16)
n1, n2 = fbm(8, 2, 11), fbm(14, 2, 12)
dessus = np.where(n1 > 0.62, PODZOL, dessus)
dessus = np.where((n1 < 0.3) & (n2 > 0.55), MOUSSE, dessus)
dessus = np.where((n2 < 0.28), TERRE_GROSSE, dessus)
dessus = np.where(plage, SABLE, dessus); sous = np.where(plage, GRES, sous)
dessus = np.where(sol < SEA, np.where(n1 > 0.55, GRAVIER, np.where(n2 > 0.6, ARGILE, SABLE)), dessus)
dessus = np.where(riviere | bassin, np.where(n1 > 0.5, BOUE, np.where(n2 > 0.5, GRAVIER, ARGILE)), dessus)
dessus = np.where(berge & (sol <= SEA + 2), BOUE, dessus)
# rochers sur les pentes raides ; le plateau sommital reste vert (jungle d'altitude, rochers epars)
roche = raide | (haut & (n1 > 0.58))
dessus = np.where(roche, np.where(n2 > 0.5, ANDESITE, np.where(n1 > 0.6, TUF, PIERRE)), dessus)
sous = np.where(roche, PIERRE, sous)
dessus = np.where(dans_lab, P('minecraft:gray_concrete'), dessus)

ys = np.arange(H)[:, None, None]
s3 = sol[None]
blocs[:] = np.where(ys <= s3 - 4, PIERRE, np.where(ys < s3, sous[None], np.where(ys == s3, dessus[None],
                    np.where(ys <= eau_niv[None], EAU, AIR)))).astype(np.uint16)

# ============================================================== chemins

chemins = np.zeros((L, W), dtype=bool)


def chemin(pts, larg=1.5):
    global chemins
    for (ax, az), (bx, bz) in zip(pts, pts[1:]):
        vx, vz = bx - ax, bz - az
        l2 = vx * vx + vz * vz
        t = np.clip(((xx - ax) * vx + (zz - az) * vz) / l2, 0, 1)
        d = np.hypot(xx - (ax + t * vx), zz - (az + t * vz))
        chemins |= (d <= larg) & ~riviere & (sol >= SEA)


PONTON = (176, 346)
TOUR = (64, 176)
CAMP = (176, 118)
CRASH = (112, 102)
PONT_Z = 150
chemin([PONTON, (170, 320), (160, 290), (150, 262), (146, 240), (146, 233)])       # arrivee -> labo
chemin([(122, 196), (100, 190), (80, 182), TOUR])                                  # labo -> tour
chemin([TOUR, (70, 140), (84, 104), CRASH])                                        # tour -> helicoptere
chemin([(150, 158), (160, 140), (176, 128), CAMP])                                 # labo -> campement
chemin([CAMP, (196, 138), (206, PONT_Z), (234, PONT_Z)])                           # campement -> pont
CHEMIN = P('minecraft:dirt_path')
zc, xc = np.nonzero(chemins & ~dans_lab)
blocs[sol[zc, xc], zc, xc] = CHEMIN

# ============================================================== vegetation

libre = (c > 0.15) & ~riviere & ~bassin & ~dans_lab & ~marge_lab & ~plage & (sol >= SEA + 1) & ~raide \
    & ~chemins & ~dans_lac & ~encoche & ~(haut & (n1 > 0.58)) & ~(dm < 20)


def proche_chemin(x, z, r):
    return chemins[max(0, z - r):z + r + 1, max(0, x - r):x + r + 1].any()


def canopee(cx, cy, cz, rx, ry, rz):
    x0, x1 = max(int(cx - rx), 0), min(int(cx + rx) + 1, W - 1)
    y0, y1 = max(int(cy - ry), 0), min(int(cy + ry) + 1, H - 1)
    z0, z1 = max(int(cz - rz), 0), min(int(cz + rz) + 1, L - 1)
    if x0 > x1 or y0 > y1 or z0 > z1:
        return
    ys = np.arange(y0, y1 + 1)[:, None, None]
    zs = np.arange(z0, z1 + 1)[None, :, None]
    xs = np.arange(x0, x1 + 1)[None, None, :]
    v = ((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2 + ((zs - cz) / rz) ** 2
    m = v <= 1 - 0.18 * rng.random(v.shape)
    sous_bloc = blocs[y0:y1 + 1, z0:z1 + 1, x0:x1 + 1]
    sous_bloc[m & (sous_bloc == AIR)] = FEUILLE


def lianes(cx, cz, r, y_bas, n):
    for _ in range(n):
        a, d = rng.random() * 2 * math.pi, r * math.sqrt(rng.random())
        x, z = int(cx + math.cos(a) * d), int(cz + math.sin(a) * d)
        if not (0 <= x < W and 0 <= z < L):
            continue
        y = y_bas
        while y > 0 and blocs[y, z, x] == AIR:           # remonter jusqu'au feuillage
            y += 1
            if y >= H - 1:
                break
        y -= 1
        if y >= H - 2 or blocs[y + 1, z, x] != FEUILLE:
            continue
        lg = int(rng.integers(3, 9))
        baies = 'true' if rng.random() < 0.22 else 'false'
        for k in range(lg):
            yy = y - k
            if yy <= sol[z, x] + 2 or blocs[yy, z, x] != AIR:
                break
            dernier = k == lg - 1 or blocs[yy - 1, z, x] != AIR or yy - 1 <= sol[z, x] + 2
            etat = 'minecraft:cave_vines[age=25,berries=%s]' % baies if dernier else \
                'minecraft:cave_vines_plant[berries=%s]' % baies
            blocs[yy, z, x] = P(etat)
            if dernier:
                break


def geant(x, z):
    g = sol[z, x]
    s = 3 if rng.random() < 0.3 else 2
    h = int(rng.integers(22, 35))
    h = min(h, H - 12 - g)
    if h < 16:
        return False
    boite(x, g + 1, z, x + s - 1, g + h, z + s - 1, TRONC)
    boite(x, g - 1, z, x + s - 1, g, z + s - 1, TRONC)            # ancre dans le sol
    # contreforts : racines en arc-boutant, 3-2-1 blocs de haut en s'eloignant du tronc
    for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        if rng.random() < 0.8:
            decal = int(rng.integers(0, s))
            for k, hh in enumerate((3, 2, 1)):
                rx = x - 1 - k if dx < 0 else x + s + k if dx > 0 else x + decal
                rz = z - 1 - k if dz < 0 else z + s + k if dz > 0 else z + decal
                if 0 <= rx < W and 0 <= rz < L:
                    gg = sol[rz, rx]
                    boite(rx, gg, rz, rx, gg + hh, rz, TRONC)
    haut_c = g + h
    rr = rng.uniform(7, 10)
    canopee(x + s / 2, haut_c, z + s / 2, rr, 3.2, rr)
    canopee(x + s / 2, haut_c + 2.5, z + s / 2, rr * 0.6, 2.2, rr * 0.6)
    # branches secondaires, avec leur feuillage, jamais sous 15 blocs (il passe dessous)
    for _ in range(int(rng.integers(2, 4))):
        yb = g + max(15, int(h * rng.uniform(0.6, 0.8)))
        dx, dz = [(1, 0), (-1, 0), (0, 1), (0, -1)][int(rng.integers(4))]
        lg = int(rng.integers(4, 7))
        axe = 'x' if dx else 'z'
        bx, bz = (x + s if dx > 0 else x - 1 if dx < 0 else x), (z + s if dz > 0 else z - 1 if dz < 0 else z)
        for k in range(lg):
            pose(bx + dx * k, yb + k // 3, bz + dz * k, 'minecraft:jungle_log[axis=%s]' % axe)
        canopee(bx + dx * lg, yb + lg // 3 + 1, bz + dz * lg, 4, 2, 4)
    # lianes le long du tronc et cabosses de cacao
    for (vx, vz, face) in ((x - 1, z, 'east'), (x + s, z, 'west'), (x, z - 1, 'south'), (x, z + s, 'north')):
        if rng.random() < 0.6 and 0 <= vx < W and 0 <= vz < L:
            y0 = g + int(rng.integers(6, 14))
            for yy in range(y0, min(g + h, y0 + int(rng.integers(4, 12)))):
                if blocs[yy, vz, vx] == AIR:
                    blocs[yy, vz, vx] = P('minecraft:vine[%s=true]' % face)
        if rng.random() < 0.4 and 0 <= vx < W and 0 <= vz < L:
            yy = g + int(rng.integers(3, 8))
            oppose = {'east': 'west', 'west': 'east', 'south': 'north', 'north': 'south'}[face]
            if blocs[yy, vz, vx] == AIR:
                blocs[yy, vz, vx] = P('minecraft:cocoa[age=2,facing=%s]' % oppose)
    lianes(x + s / 2, z + s / 2, rr * 0.8, haut_c - 5, int(rng.integers(4, 9)))
    # sol plus sombre sous la canopee
    zs, xs = slice(max(0, z - 4), z + s + 4), slice(max(0, x - 4), x + s + 4)
    zone = blocs[:, zs, xs]
    for (zi, xi) in zip(*np.nonzero(rng.random(sol[zs, xs].shape) < 0.35)):
        yy = sol[zs, xs][zi, xi]
        if zone[yy, zi, xi] == HERBE:
            zone[yy, zi, xi] = PODZOL
    return True


def moyen(x, z):
    g = sol[z, x]
    h = int(rng.integers(8, 14))
    boite(x, g + 1, z, x, g + h, z, TRONC)
    canopee(x + 0.5, g + h, z + 0.5, rng.uniform(3, 4.2), 2.2, rng.uniform(3, 4.2))
    return True


troncs = []


def loin_des_troncs(x, z, dmin):
    for (tx, tz) in troncs:
        if (tx - x) ** 2 + (tz - z) ** 2 < dmin * dmin:
            return False
    return True


PAS = 12
for gzc in range(0, L, PAS):
    for gxc in range(0, W, PAS):
        x = gxc + int(rng.integers(0, PAS - 3)); z = gzc + int(rng.integers(0, PAS - 3))
        if x + 3 >= W or z + 3 >= L or not libre[z:z + 3, x:x + 3].all() or proche_chemin(x, z, 3):
            continue
        if sol[z, x] > SEA + 30 or rng.random() > 0.85:
            continue
        if loin_des_troncs(x, z, 10) and geant(x, z):
            troncs.append((x, z))
# arbres moyens entre les geants : au moins 7 blocs entre deux troncs (il passe entre)
for (ox, oz) in ((PAS // 2, PAS // 2), (PAS // 2, 0), (0, PAS // 2)):
    for gzc in range(oz, L, PAS):
        for gxc in range(ox, W, PAS):
            x = gxc + int(rng.integers(-3, 4)); z = gzc + int(rng.integers(-3, 4))
            if not (0 <= x < W and 0 <= z < L) or not libre[z, x] or proche_chemin(x, z, 2) or rng.random() > 0.7:
                continue
            if loin_des_troncs(x, z, 7) and moyen(x, z):
                troncs.append((x, z))

# sous-bois : jamais bloquant, sauf quelques buissons (il les arrache)
HERBE_H, FOUGERE = P('minecraft:grass'), P('minecraft:fern')
GF_BAS, GF_HAUT = P('minecraft:large_fern[half=lower]'), P('minecraft:large_fern[half=upper]')
TAPIS, CHAMP_B, CHAMP_R = P('minecraft:moss_carpet'), P('minecraft:brown_mushroom'), P('minecraft:red_mushroom')
r_sb = rng.random((L, W))
for z in range(L):
    for x in range(W):
        g = sol[z, x]
        if g + 2 >= H or blocs[g + 1, z, x] != AIR:
            continue
        top = blocs[g, z, x]
        if top not in (HERBE, PODZOL, MOUSSE, TERRE_GROSSE) or chemins[z, x] or dans_lab[z, x]:
            continue
        r = r_sb[z, x]
        if r < 0.24:
            blocs[g + 1, z, x] = HERBE_H
        elif r < 0.36:
            blocs[g + 1, z, x] = FOUGERE
        elif r < 0.43 and blocs[g + 2, z, x] == AIR:
            blocs[g + 1, z, x] = GF_BAS; blocs[g + 2, z, x] = GF_HAUT
        elif r < 0.46:
            blocs[g + 1, z, x] = TAPIS
        elif r < 0.465 and not proche_chemin(x, z, 2):
            blocs[g + 1, z, x] = FEUILLE                         # buisson
        elif r < 0.47 and top == PODZOL:
            blocs[g + 1, z, x] = CHAMP_B if r_sb[z, x] * 1000 % 2 < 1 else CHAMP_R
        elif r < 0.4715 and top == HERBE:
            blocs[g + 1, z, x] = P('minecraft:melon')

# nenuphars et herbes aquatiques
for z in range(L):
    for x in range(W):
        if riviere[z, x] and c[z, x] > 0.2 and driv[z, x] > demi[z, x] * 0.7 and r_sb[z, x] < 0.05 \
                and blocs[SEA + 1, z, x] == AIR:
            blocs[SEA + 1, z, x] = P('minecraft:lily_pad')
        g = sol[z, x]
        if g < SEA - 1 and r_sb[z, x] > 0.93 and blocs[g + 1, z, x] == EAU:
            blocs[g + 1, z, x] = P('minecraft:seagrass')

# ============================================================== cascade et grotte

xc_f = int(MX - 31)
for z in range(int(MZ) - 2, int(MZ) + 3):
    for y in range(SEA - 6, LAC + 1):
        pose(xc_f, y, z, 'minecraft:water[level=8]' if y < LAC else 'minecraft:water[level=0]')
    for y in range(SEA - 6, LAC):
        pose(xc_f - 1, y, z, 'minecraft:water[level=8]')
# grotte derriere la cascade
boite(xc_f + 1, SEA + 1, int(MZ) - 4, xc_f + 9, SEA + 7, int(MZ) + 4, AIR)
boite(xc_f + 1, SEA, int(MZ) - 4, xc_f + 9, SEA, int(MZ) + 4, 'minecraft:mossy_cobblestone')
for (bx, bz) in ((xc_f + 7, int(MZ) - 3), (xc_f + 8, int(MZ) + 2), (xc_f + 5, int(MZ) + 3)):
    pose(bx, SEA + 1, bz, 'minecraft:bone_block[axis=x]')
coffre(xc_f + 8, SEA + 1, int(MZ), 'west', [('minecraft:compass', 1), ('minecraft:bone', 6), ('minecraft:paper', 3)])
panneau(xc_f + 8, SEA + 3, int(MZ) - 4, 'south', ['Il revient ici', 'apres chaque', 'chasse.', '- carnet de V.'])

# ============================================================== laboratoire « Site B »

BETON, BETON_C, BETON_F = 'minecraft:light_gray_concrete', 'minecraft:white_concrete', 'minecraft:gray_concrete'
DALLE = 'minecraft:polished_andesite'
VITRE = 'minecraft:glass'
LAMPE_MORTE = 'minecraft:redstone_lamp[lit=false]'
BX0, BZ0, BX1, BZ1 = 125, 170, 169, 204          # batiment principal
F1, F2, TOIT = G, G + 6, G + 12                 # planchers
SOUS = SEA - 4                                    # dalle du sous-sol (44) ; eau jusqu'a SEA (48)

# --- dalle et sous-sol
boite(BX0, SOUS, BZ0, BX1, TOIT, BZ1, AIR)
boite(BX0, SOUS - 1, BZ0, BX1, SOUS, BZ1, 'minecraft:stone_bricks')
murs(BX0, SOUS, BZ0, BX1, TOIT, BZ1, BETON)
boite(BX0, F1, BZ0, BX1, F1, BZ1, DALLE)
boite(BX0, F2, BZ0, BX1, F2, BZ1, DALLE)
boite(BX0, TOIT, BZ0, BX1, TOIT, BZ1, BETON_F)
# sous-sol : grande salle inondee a l'est (a sa taille), salle du generateur au sec a l'ouest
HX0 = 143
boite(HX0, SOUS + 1, BZ0 + 1, BX1 - 1, SEA, BZ1 - 1, EAU)
murs(HX0 - 1, SOUS + 1, BZ0 + 1, HX0 - 1, F1 - 1, BZ1 - 1, BETON)
for px in range(HX0 + 5, BX1 - 2, 7):
    for pz in (BZ0 + 8, BZ1 - 8):
        boite(px, SOUS + 1, pz, px + 1, F1 - 1, pz + 1, BETON)
# passerelles etroites au-dessus de l'eau noire : on y passe, lui guette dessous
boite(HX0, SEA, BZ0 + 16, BX1 - 3, SEA, BZ0 + 17, 'minecraft:stone_bricks')
boite(BX1 - 4, SEA, BZ0 + 4, BX1 - 3, SEA, BZ1 - 4, 'minecraft:stone_bricks')
pose(HX0 - 1, SEA + 1, BZ0 + 16, AIR); pose(HX0 - 1, SEA + 2, BZ0 + 16, AIR)
pose(HX0 - 1, SEA + 1, BZ0 + 17, AIR); pose(HX0 - 1, SEA + 2, BZ0 + 17, AIR)
for pz in range(BZ0 + 3, BZ1 - 2, 6):
    pose(BX1 - 1, F1 - 1, pz, LAMPE_MORTE)
# salle du generateur (seche, plancher surleve)
boite(BX0 + 1, SOUS + 1, BZ0 + 1, HX0 - 2, SEA, BZ1 - 1, 'minecraft:stone_bricks')
boite(BX0 + 1, SEA + 1, BZ0 + 1, HX0 - 2, F1 - 1, BZ1 - 1, AIR)
for gx in (BX0 + 3, BX0 + 7, BX0 + 11):
    boite(gx, SEA + 1, BZ0 + 3, gx + 1, SEA + 2, BZ0 + 4, 'minecraft:iron_block')
    pose(gx, SEA + 3, BZ0 + 3, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
    pose(gx, SEA + 1, BZ0 + 5, 'minecraft:lever[face=floor,facing=north,powered=false]')
pose(BX0 + 5, SEA + 2, BZ0 + 9, LAMPE_MORTE)
panneau(BX0 + 1, SEA + 2, BZ0 + 12, 'east', ['GENERATEUR', 'DE SECOURS', 'Relancer les 3', 'turbines'])
panneau(HX0 - 2, SEA + 2, BZ0 + 18, 'west', ['DRAINAGE B-2', 'Grille arrachee', 'de l\'interieur.', 'NE PAS NAGER'])
coffre(BX0 + 2, SEA + 1, BZ1 - 3, 'north', [('minecraft:torch', 8), ('minecraft:bread', 4), ('minecraft:map', 1)])

# --- tunnel de drainage noye : du sous-sol a l'enclos (sa route secrete)
TZ0, TZ1 = 183, 190
PX0, PZ0, PX1, PZ1 = 172, 164, 208, 222          # enclos S-01 (murs compris)
boite(BX1 - 1, SOUS - 2, TZ0, PX0 + 3, SEA - 1, TZ1, EAU)
boite(BX1 - 1, SEA, TZ0, PX0 + 3, SEA, TZ1, 'minecraft:stone_bricks')
for z in range(TZ0, TZ1 + 1, 2):                  # la grille, tordue et a moitie arrachee
    if z not in (TZ0 + 2, TZ0 + 4, TZ0 + 6):
        pose(BX1 - 1, SEA - 1, z, 'minecraft:iron_bars[east=false,north=true,south=true,waterlogged=true,west=false]')

# --- enclos S-01 : bassin de 10 blocs de fond, hauts murs, breche vers la riviere
boite(PX0, F1 + 1, PZ0, PX1, F1 + 16, PZ1, AIR)
murs(PX0, SOUS - 8, PZ0, PX1, F1 + 12, PZ1, BETON)
murs(PX0 + 1, SOUS - 8, PZ0 + 1, PX1 - 1, F1 + 12, PZ1 - 1, BETON)
boite(PX0, F1 + 4, PZ0 + 2, PX0 + 1, F1 + 12, PZ1 - 2, AIR)          # parapet bas cote labo
boite(PX0 + 2, SOUS - 8, PZ0 + 2, PX1 - 2, SOUS - 8, PZ1 - 2, 'minecraft:stone_bricks')
boite(PX0 + 2, SOUS - 7, PZ0 + 2, PX1 - 2, SEA, PZ1 - 2, EAU)
boite(PX0 + 2, SEA + 1, PZ0 + 2, PX1 - 2, F1 + 12, PZ1 - 2, AIR)
boite(PX0 + 2, SEA - 7, TZ0, PX0 + 3, SEA - 1, TZ1, EAU)               # debouche du tunnel
# rocher au milieu, ossements au fond
boite(188, SOUS - 7, 188, 193, SEA + 2, 194, 'minecraft:mossy_cobblestone')
boite(189, SEA + 3, 189, 192, SEA + 3, 193, 'minecraft:moss_block')
for (ox, oz) in ((180, 175), (196, 210), (184, 205), (200, 180), (178, 200)):
    pose(ox, SOUS - 7, oz, 'minecraft:bone_block[axis=z]')
    pose(ox + 1, SOUS - 7, oz, 'minecraft:bone_block[axis=x]')
# passerelle de surveillance sur les murs, garde-corps
for y in (F1 + 13,):
    barreaux(PX0 + 2, y, PZ0 + 1, PX1 - 2, PZ0 + 1)
    barreaux(PX0 + 2, y, PZ1 - 1, PX1 - 2, PZ1 - 1)
# grue de nourrissage (nord)
boite(190, F1 + 13, PZ0, 190, F1 + 20, PZ0, 'minecraft:oak_fence[east=false,north=false,south=false,waterlogged=false,west=false]')
boite(190, F1 + 20, PZ0 + 1, 190, F1 + 20, PZ0 + 9, 'minecraft:spruce_planks')
for y in range(SEA + 4, F1 + 20):
    pose(190, y, PZ0 + 9, 'minecraft:chain[axis=y,waterlogged=false]')
pose(190, SEA + 3, PZ0 + 9, 'minecraft:red_terracotta')
# LA BRECHE : mur est effondre, eboulis, chenal jusqu'a la riviere
BZB0, BZB1 = 186, 198
boite(PX1 - 1, SEA + 1, BZB0, PX1, F1 + 12, BZB1, AIR)
boite(PX1 - 1, SOUS - 7, BZB0, PX1, SEA, BZB1, EAU)
for z in range(BZB0, BZB1 + 1):
    xr = PX1 + 1
    while xr < W and not riviere[z, xr]:
        boite(xr, SEA - 7, z, xr, SEA, z, EAU)
        boite(xr, SEA + 1, z, xr, SEA + 6, z, AIR)
        xr += 1
for _ in range(60):
    ex = int(rng.integers(PX1 - 4, PX1 + 5)); ez = int(rng.integers(BZB0 - 3, BZB1 + 4))
    ey = SEA + int(rng.integers(-2, 4))
    if not (BZB0 + 2 <= ez <= BZB1 - 2):
        pose(ex, ey, ez, ['minecraft:cracked_stone_bricks', 'minecraft:cobblestone', BETON, 'minecraft:andesite'][int(rng.integers(4))])
pose(PX1 + 1, F1 + 2, BZB0 - 1, 'minecraft:red_concrete')
panneau(PX1 + 1, F1 + 3, BZB0 - 2, 'east', ['ENCLOS S-01', 'SPINOSAURUS', 'CONFINEMENT 4', 'BRECHE 03:12'])

# --- rez-de-chaussee : couloir de 2 blocs (il n'y entre pas), salles
CZ = 186
boite(BX0 + 1, F1 + 1, BZ0 + 1, BX1 - 1, F2 - 1, BZ1 - 1, AIR)
murs(BX0 + 1, F1 + 1, CZ - 1, BX1 - 1, F2 - 1, CZ + 2, BETON_C)             # couloir est-ouest
boite(BX0 + 2, F1 + 1, CZ, BX1 - 2, F2 - 1, CZ + 1, AIR)
for sx in (139, 154):                                                       # cloisons nord et sud
    boite(sx, F1 + 1, BZ0 + 1, sx, F2 - 1, CZ - 1, BETON_C)
    boite(sx, F1 + 1, CZ + 2, sx, F2 - 1, BZ1 - 1, BETON_C)
for (dx, dz0, dz1) in ((132, CZ - 1, CZ - 1), (147, CZ - 1, CZ - 1), (161, CZ - 1, CZ - 1),
                      (132, CZ + 2, CZ + 2), (147, CZ + 2, CZ + 2), (161, CZ + 2, CZ + 2)):
    boite(dx, F1 + 1, dz0, dx + 1, F1 + 2, dz1, AIR)                        # portes de 2 blocs
# entree au sud : double porte, hall d'accueil
boite(146, F1 + 1, BZ1, 148, F1 + 3, BZ1, AIR)
boite(141, F1 + 1, 196, 152, F1 + 1, 196, 'minecraft:smooth_quartz')
barreaux(143, F1 + 1, 200, 150, 200)
panneau(147, F1 + 4, BZ1 + 1, 'south', ['SITE B', 'RIVIERE BIOTECH', 'Personnel', 'autorise seul.'])
panneau(145, F1 + 2, 197, 'south', ['Accueil ferme.', 'Evacuation vers', 'le ponton sud.', ''])
# labo A : cuves (une brisee)
for i, tx in enumerate((157, 161, 165)):
    boite(tx, F1 + 1, 192, tx + 2, F1 + 1, 194, 'minecraft:sea_lantern')
    if i == 1:
        boite(tx, F1 + 2, 192, tx + 2, F1 + 2, 194, VITRE)                  # il n'en reste que la base
        pose(tx + 1, F1 + 2, 193, 'minecraft:water[level=0]')
    else:
        murs(tx, F1 + 2, 192, tx + 2, F2 - 1, 194, VITRE)
        pose(tx + 1, F1 + 2, 193, 'minecraft:water[level=0]')
        boite(tx + 1, F1 + 2, 193, tx + 1, F2 - 1, 193, 'minecraft:water[level=0]')
boite(156, F1 + 1, 200, 167, F1 + 1, 200, 'minecraft:smooth_quartz_slab[type=bottom,waterlogged=false]')
pose(158, F1 + 2, 200, 'minecraft:brewing_stand[has_bottle_0=true,has_bottle_1=false,has_bottle_2=true]')
pose(162, F1 + 2, 200, 'minecraft:cauldron')
panneau(165, F1 + 2, 201, 'north', ['Lot S-01 : croissance', 'x3 attendue.', 'Observee : x5.', ''])
# poste de securite : ecrans morts
for mx in range(127, 138, 2):
    pose(mx, F1 + 1, 202, 'minecraft:smooth_quartz_slab[type=bottom,waterlogged=false]')
    pose(mx, F1 + 2, 203, 'minecraft:black_stained_glass')
pose(129, F1 + 2, 202, 'minecraft:observer[facing=north,powered=false]')
panneau(133, F1 + 3, 203, 'north', ['CAM 7 : aucun signal', 'CAM 9 : aucun signal', 'CAM 12 : eau trouble', ''])
coffre(127, F1 + 1, 190, 'south', [('minecraft:iron_ingot', 3), ('minecraft:spyglass', 1), ('minecraft:lantern', 2)])
# labo B : paillasses et bibliotheque
for tz in (174, 178, 182):
    boite(128, F1 + 1, tz, 137, F1 + 1, tz, 'minecraft:smooth_stone_slab[type=bottom,waterlogged=false]')
boite(141, F1 + 1, 172, 152, F1 + 3, 172, 'minecraft:bookshelf')
pose(145, F1 + 1, 176, 'minecraft:lectern[facing=south,has_book=false,powered=false]')
panneau(144, F1 + 2, 173, 'south', ['Il ne mange pas', 'quand on le', 'regarde.', ''])
# escaliers (nord-est) : vers l'etage et vers le generateur
for k in range(6):
    pose(158 + k, F1 + 1 + k, 175, 'minecraft:stone_brick_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]')
    pose(158 + k, F1 + 1 + k, 176, 'minecraft:stone_brick_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]')
boite(158, F2, 175, 164, F2, 176, AIR)
for k in range(6):
    pose(133 + k, F1 - k, 188, 'minecraft:stone_brick_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]')
    pose(133 + k, F1 - k, 189, 'minecraft:stone_brick_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]')
    boite(133 + k, F1 - k + 1, 188, 133 + k, F1 + 2, 189, AIR)
boite(133, F1, 188, 139, F1, 189, AIR)
# eclairage mort, quelques lanternes
for lx in range(130, 168, 8):
    pose(lx, F2 - 1, CZ, LAMPE_MORTE)
pose(147, F2 - 1, 198, 'minecraft:lantern[hanging=true,waterlogged=false]')
# fenetres (certaines brisees)
for y in (F1 + 2, F1 + 3, F2 + 2, F2 + 3):
    for x in range(BX0 + 2, BX1 - 1, 3):
        for z in (BZ0, BZ1):
            if (x, z) != (147, BZ1):
                pose(x, y, z, AIR if rng.random() < 0.25 else VITRE)
    for z in range(BZ0 + 2, BZ1 - 1, 3):
        pose(BX0, y, z, AIR if rng.random() < 0.25 else VITRE)
# --- etage : salle de controle vitree face a l'enclos, bureaux, couveuse
boite(BX0 + 1, F2 + 1, BZ0 + 1, BX1 - 1, TOIT - 1, BZ1 - 1, AIR)
boite(BX1, F2 + 2, BZ0 + 4, BX1, F2 + 4, BZ1 - 4, 'minecraft:tinted_glass')
boite(155, F2 + 1, BZ0 + 1, 155, TOIT - 1, BZ1 - 1, BETON_C)
boite(155, F2 + 1, 186, 155, F2 + 2, 187, AIR)
boite(158, F2 + 1, 180, 167, F2 + 1, 196, 'minecraft:smooth_quartz_slab[type=bottom,waterlogged=false]')
for mz in range(181, 196, 2):
    pose(166, F2 + 2, mz, 'minecraft:black_stained_glass')
pose(160, F2 + 2, 188, 'minecraft:lever[face=floor,facing=east,powered=false]')
panneau(161, F2 + 2, 180, 'south', ['PORTE DE L\'ENCLOS', 'VERROUILLEE', '(il a appris a', 'ouvrir la vanne)'])
boite(140, F2 + 1, BZ0 + 1, 140, TOIT - 1, BZ1 - 1, BETON_C)
boite(140, F2 + 1, 186, 140, F2 + 2, 187, AIR)
for ex in range(142, 153, 3):                                              # couveuse
    pose(ex, F2 + 1, 176, 'minecraft:sand')
    pose(ex, F2 + 2, 176, 'minecraft:turtle_egg[eggs=3,hatch=2]')
    pose(ex, TOIT - 1, 176, LAMPE_MORTE)
pose(146, F2 + 2, 180, 'minecraft:sniffer_egg[hatch=2]')
panneau(144, F2 + 3, 172, 'south', ['COUVEUSE', 'Oeuf 4 : eclos', 'hors protocole', ''])
boite(127, F2 + 1, 197, 137, F2 + 3, 197, 'minecraft:bookshelf')
coffre(128, F2 + 1, 175, 'east', [('minecraft:writable_book', 1), ('minecraft:clock', 1), ('minecraft:bread', 2)])
panneau(131, F2 + 2, 171, 'south', ['Rapport 17 :', 'il suit les equipes', 'sans jamais se', 'montrer.'])
# --- toit : helistation
boite(135, TOIT, 178, 158, TOIT, 198, 'minecraft:yellow_concrete')
boite(137, TOIT, 180, 156, TOIT, 196, BETON_F)
for (hx0, hz0, hx1, hz1) in ((141, 182, 142, 194), (151, 182, 152, 194), (143, 187, 150, 189)):
    boite(hx0, TOIT, hz0, hx1, TOIT, hz1, 'minecraft:yellow_concrete')
boite(BX0 + 2, TOIT + 1, BZ0 + 2, BX0 + 2, TOIT + 4, BZ0 + 2, 'minecraft:iron_bars[east=false,north=false,south=false,waterlogged=false,west=false]')
pose(BX0 + 2, TOIT + 5, BZ0 + 2, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
for k in range(TOIT - F2):                                                  # echelle vers le toit
    pose(BX0 + 1, F2 + 1 + k, BZ1 - 2, 'minecraft:ladder[facing=east,waterlogged=false]')
pose(BX0 + 1, TOIT, BZ1 - 2, AIR)

# --- ponton sur la riviere, hangar a bateaux, cloture du perimetre
for z in range(228, 236):
    x = 200
    while x < W and not riviere[z, x]:
        x += 1
    boite(x - 6, SEA + 1, z, x + 7, SEA + 1, z, 'minecraft:spruce_planks')
for (fx, fz) in ((204, 227), (212, 227), (204, 236), (212, 236)):
    boite(fx, SEA - 6, fz, fx, SEA + 2, fz, 'minecraft:spruce_log[axis=y]')
boite(186, G + 1, 226, 196, G + 5, 236, 'minecraft:spruce_planks')
boite(187, G + 1, 227, 195, G + 4, 235, AIR)
boite(186, G + 1, 229, 186, G + 3, 232, AIR)
boite(185, G + 6, 225, 197, G + 6, 237, 'minecraft:dark_oak_planks')
pose(190, G + 1, 228, 'minecraft:barrel[facing=up,open=false]'); pose(191, G + 1, 228, 'minecraft:barrel[facing=up,open=false]')
coffre(194, G + 1, 234, 'west', [('minecraft:oak_boat', 1), ('minecraft:lead', 2)])
panneau(185, G + 2, 230, 'west', ['HANGAR', 'Ne jamais rester', 'sur le ponton', 'a la nuit.'])
for x in range(LAB[0], LAB[2] + 1):
    for z in (LAB[1], LAB[3]):
        if rng.random() > 0.2 and not riviere[z, x] and abs(x - 147) > 2:
            boite(x, G + 1, z, x, G + 3, z, 'minecraft:iron_bars[east=true,north=false,south=false,waterlogged=false,west=true]')
for z in range(LAB[1], LAB[3] + 1):
    if rng.random() > 0.2 and abs(z - 196) > 2:
        boite(LAB[0], G + 1, z, LAB[0], G + 3, z, 'minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]')

# ============================================================== autres lieux

# --- ponton d'arrivee et cabane (plage sud)
px, pz = PONTON
pz = next(z for z in range(300, L) if sol[z, px] < SEA)       # premiere eau en descendant vers le sud
gp = int(sol[pz - 8, px])
boite(px - 1, SEA + 1, pz, px + 1, SEA + 1, pz + 18, 'minecraft:oak_planks')
for k in range(0, 19, 4):
    boite(px - 2, SEA - 5, pz + k, px - 2, SEA + 2, pz + k, 'minecraft:oak_log[axis=y]')
    boite(px + 2, SEA - 5, pz + k, px + 2, SEA + 2, pz + k, 'minecraft:oak_log[axis=y]')
boite(px - 8, gp + 1, pz - 10, px - 3, gp + 4, pz - 5, 'minecraft:oak_planks')
boite(px - 7, gp + 1, pz - 9, px - 4, gp + 3, pz - 6, AIR)
boite(px - 5, gp + 1, pz - 5, px - 5, gp + 2, pz - 5, AIR)
boite(px - 9, gp + 5, pz - 11, px - 2, gp + 5, pz - 4, 'minecraft:spruce_slab[type=bottom,waterlogged=false]')
panneau(px, SEA + 2, pz - 1, 'south', ['BIENVENUE', 'SITE B', 'Laboratoire : suivre', 'le chemin au nord'], mural=False)
coffre(px - 6, gp + 1, pz - 8, 'south', [('minecraft:bread', 6), ('minecraft:torch', 16), ('minecraft:compass', 1)])

# --- tour de guet (colline ouest) : 24 de haut, echelle
tx, tz = TOUR
gt = int(sol[tz - 2:tz + 3, tx - 2:tx + 3].max())
for (ox, oz) in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
    boite(tx + ox, sol[tz + oz, tx + ox] - 1, tz + oz, tx + ox, gt + 22, tz + oz, 'minecraft:spruce_log[axis=y]')
boite(tx - 3, gt + 22, tz - 3, tx + 3, gt + 22, tz + 3, 'minecraft:spruce_planks')
boite(tx - 3, gt + 23, tz - 3, tx + 3, gt + 23, tz + 3, 'minecraft:spruce_fence[east=false,north=false,south=false,waterlogged=false,west=false]')
boite(tx - 2, gt + 23, tz - 2, tx + 2, gt + 23, tz + 2, AIR)
boite(tx - 3, gt + 27, tz - 3, tx + 3, gt + 27, tz + 3, 'minecraft:dark_oak_slab[type=bottom,waterlogged=false]')
for (ox, oz) in ((-3, -3), (3, -3), (-3, 3), (3, 3)):
    boite(tx + ox, gt + 23, tz + oz, tx + ox, gt + 26, tz + oz, 'minecraft:spruce_fence[east=false,north=false,south=false,waterlogged=false,west=false]')
for y in range(sol[tz, tx - 1] + 1, gt + 23):
    pose(tx - 1, y, tz, 'minecraft:ladder[facing=west,waterlogged=false]')
pose(tx, gt + 21, tz, 'minecraft:spruce_log[axis=y]')
coffre(tx + 2, gt + 23, tz + 2, 'north', [('minecraft:spyglass', 1), ('minecraft:arrow', 16), ('minecraft:torch', 8)])
panneau(tx + 1, gt + 24, tz - 2, 'south', ['Vu la voile', 'pres du pont.', 'Il ne sortait', 'pas de l\'eau.'])

# --- helicoptere abattu dans la jungle (nord-ouest)
hx, hz = CRASH
gh = int(sol[hz, hx])
boite(hx - 4, gh + 1, hz - 2, hx + 4, gh + 4, hz + 2, 'minecraft:black_concrete')
boite(hx - 3, gh + 2, hz - 1, hx + 3, gh + 3, hz + 1, AIR)
boite(hx + 4, gh + 2, hz - 2, hx + 5, gh + 3, hz + 2, 'minecraft:light_blue_stained_glass')
boite(hx - 12, gh + 3, hz, hx - 5, gh + 3, hz, 'minecraft:gray_concrete')
boite(hx - 13, gh + 3, hz, hx - 13, gh + 5, hz, 'minecraft:gray_concrete')
boite(hx - 1, gh + 5, hz - 7, hx - 1, gh + 5, hz + 6, 'minecraft:smooth_stone_slab[type=bottom,waterlogged=false]')
boite(hx - 6, gh + 5, hz, hx + 5, gh + 5, hz, 'minecraft:smooth_stone_slab[type=bottom,waterlogged=false]')
pose(hx - 1, gh + 1, hz + 3, 'minecraft:campfire[facing=north,lit=false,signal_fire=false,waterlogged=false]')
coffre(hx - 2, gh + 1, hz, 'east', [('minecraft:iron_ingot', 4), ('minecraft:flint_and_steel', 1), ('minecraft:paper', 5)])
panneau(hx - 4, gh + 3, hz + 3, 'south', ['Vol RB-2', 'Quelque chose', 'nous a suivis', 'depuis la riviere'])

# --- campement abandonne
cx, cz = CAMP
gc = int(sol[cz, cx])
for (ox, oz, laine) in ((-5, -3, 'white'), (4, -4, 'lime'), (0, 5, 'white')):
    for k in range(3):
        boite(cx + ox - 2 + k, gc + 1 + k, cz + oz - 2, cx + ox + 2 - k, gc + 1 + k, cz + oz + 2, 'minecraft:%s_wool' % laine)
    boite(cx + ox - 1, gc + 1, cz + oz - 1, cx + ox + 1, gc + 1, cz + oz + 1, AIR)
    boite(cx + ox, gc + 1, cz + oz - 2, cx + ox, gc + 1, cz + oz - 2, AIR)
pose(cx, gc + 1, cz, 'minecraft:campfire[facing=north,lit=false,signal_fire=false,waterlogged=false]')
coffre(cx + 2, gc + 1, cz + 1, 'west', [('minecraft:cooked_beef', 3), ('minecraft:rotten_flesh', 4), ('minecraft:torch', 8)])
panneau(cx - 2, gc + 1, cz + 1, 'east', ['On a entendu', 'respirer derriere', 'la tente.', 'Personne.'], mural=False)

# --- pont suspendu casse sur la riviere
xs_pont = [x for x in range(W) if riviere[PONT_Z, x]]
if xs_pont:
    a, b = xs_pont[0] - 3, xs_pont[-1] + 3
    milieu = (a + b) // 2
    for x in range(a, b + 1):
        if abs(x - milieu) <= 2:
            continue                                                        # le trou
        creux = int(2 * math.sin(math.pi * (x - a) / (b - a)))
        pose(x, SEA + 5 - creux, PONT_Z, 'minecraft:spruce_planks')
        pose(x, SEA + 5 - creux, PONT_Z + 1, 'minecraft:spruce_planks')
        if x % 3 == 0:
            pose(x, SEA + 6 - creux, PONT_Z - 1, 'minecraft:chain[axis=y,waterlogged=false]')
            pose(x, SEA + 6 - creux, PONT_Z + 2, 'minecraft:chain[axis=y,waterlogged=false]')
    for x in (a, b):
        boite(x, sol[PONT_Z, x], PONT_Z - 1, x, SEA + 8, PONT_Z - 1, 'minecraft:spruce_log[axis=y]')
        boite(x, sol[PONT_Z, x], PONT_Z + 2, x, SEA + 8, PONT_Z + 2, 'minecraft:spruce_log[axis=y]')

# ============================================================== biomes

bio_palette = {'minecraft:jungle': 0, 'minecraft:warm_ocean': 1}
bio = np.where((c < 0) & (sol < SEA), 1, 0).astype(np.uint8)   # toute l'ile est jungle, riviere comprise


# ============================================================== ecriture

def varints(v):
    v = v.astype(np.int64)
    un = v < 128
    lg = np.where(un, 1, 2)
    debut = np.concatenate(([0], np.cumsum(lg)[:-1]))
    out = np.zeros(int(lg.sum()), dtype=np.uint8)
    out[debut[un]] = v[un]
    deux = ~un
    out[debut[deux]] = (v[deux] & 0x7F) | 0x80
    out[debut[deux] + 1] = v[deux] >> 7
    return out.tobytes()


def ecrire(chemin):
    assert len(palette) < 16384
    donnees = varints(blocs.reshape(-1))                      # ordre : x + z*W + y*W*L
    racine = nbt.Compound({
        'Version': nbt.Int(2), 'DataVersion': nbt.Int(3465),
        'Width': nbt.Short(W), 'Height': nbt.Short(H), 'Length': nbt.Short(L),
        'Offset': nbt.IntArray([0, 0, 0]),
        'Metadata': nbt.Compound({'WEOffsetX': nbt.Int(0), 'WEOffsetY': nbt.Int(0), 'WEOffsetZ': nbt.Int(0),
                                  'Name': nbt.String('Site B - ile du spinosaure'), 'Author': nbt.String('RIVIERE')}),
        'PaletteMax': nbt.Int(len(palette)),
        'Palette': nbt.Compound({k: nbt.Int(v) for k, v in palette.items()}),
        'BlockData': nbt.ByteArray(donnees),
        'BlockEntities': nbt.List('compound', entites_blocs),
        'BiomePalette': nbt.Compound({k: nbt.Int(v) for k, v in bio_palette.items()}),
        'BiomeData': nbt.ByteArray(varints(bio.reshape(-1))),
    })
    taille = nbt.ecrire(chemin, 'Schematic', racine)
    return taille


if __name__ == '__main__':
    sortie = sys.argv[1] if len(sys.argv) > 1 else 'site_b.schem'
    n = ecrire(sortie)
    np.save(sortie + '.blocs.npy', blocs)
    json.dump({'palette': palette, 'sol': sol.tolist(), 'SEA': SEA, 'LAC': LAC,
               'poi': {'ponton': PONTON, 'tour': TOUR, 'camp': CAMP, 'crash': CRASH, 'labo': [147, 196],
                       'enclos': [190, 192], 'cascade': [xc_f, int(MZ)], 'pont': [220, PONT_Z]}},
              open(sortie + '.meta.json', 'w'))
    non_air = int((blocs != AIR).sum())
    print('%s : %d x %d x %d, %d blocs non vides, %d etats, %d entites de blocs, %.1f Mo brut'
          % (sortie, W, H, L, non_air, len(palette), len(entites_blocs), n / 1e6))
    print('arbres :', len(troncs))
