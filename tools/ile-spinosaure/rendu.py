"""Rendus pour juger ce qu'on construit : vue isometrique voxel (chaque face visible, pas des
colonnes), coupes horizontales d'un etage vu de dessus, et carte de l'ile ombree.

Vue iso depuis le sud-est, au-dessus : faces visibles = dessus (+y), est (+x), sud (+z).
Chaque bloc est un sprite en losange ; le plus proche de l'oeil (x + y + z le plus grand)
est peint en dernier."""
import re
import zlib

import numpy as np
from PIL import Image

# ---------------------------------------------------------------- couleurs des blocs
COULEURS = [
    (r'water', (38, 78, 150)), (r'lava', (230, 110, 20)),
    (r'mangrove_leaves', (58, 110, 38)), (r'jungle_leaves', (48, 118, 30)), (r'oak_leaves', (62, 128, 40)),
    (r'azalea_leaves', (84, 132, 52)), (r'flowering_azalea', (120, 128, 90)), (r'dark_oak_leaves', (40, 90, 26)),
    (r'birch_leaves', (100, 140, 60)), (r'spruce_leaves', (40, 80, 50)), (r'acacia_leaves', (80, 120, 30)),
    (r'leaves', (55, 115, 35)),
    (r'mangrove_roots', (80, 62, 40)), (r'muddy_mangrove', (70, 58, 46)),
    (r'stripped_jungle', (170, 120, 80)), (r'jungle_(log|wood)', (88, 68, 36)), (r'jungle_(planks|slab|stairs|fence|trapdoor|door)', (160, 115, 80)),
    (r'mangrove_(log|wood)', (84, 44, 38)), (r'mangrove_(planks|slab|stairs|fence)', (118, 54, 48)),
    (r'dark_oak_(log|wood)', (60, 46, 30)), (r'dark_oak', (68, 44, 22)),
    (r'spruce_(log|wood)', (60, 44, 28)), (r'spruce', (112, 82, 50)),
    (r'birch_(log|wood)', (210, 206, 190)), (r'birch', (190, 172, 120)),
    (r'oak_(log|wood)', (100, 80, 50)), (r'oak', (160, 130, 80)),
    (r'bamboo_(block|planks|mosaic|slab|stairs|fence)', (190, 170, 80)), (r'bamboo', (100, 150, 40)),
    (r'moss_carpet', (90, 120, 45)), (r'moss', (90, 120, 45)), (r'grass_block', (86, 130, 50)),
    (r'podzol', (100, 70, 40)), (r'coarse_dirt', (110, 80, 55)), (r'rooted_dirt', (120, 88, 62)),
    (r'dirt_path', (148, 122, 72)), (r'mud_brick', (140, 105, 80)), (r'packed_mud', (140, 106, 76)), (r'mud', (60, 54, 50)),
    (r'dirt', (122, 88, 60)), (r'farmland', (100, 70, 44)), (r'clay', (150, 154, 168)),
    (r'red_sandstone', (180, 96, 40)), (r'sandstone', (216, 202, 150)), (r'sand', (220, 208, 160)), (r'gravel', (130, 124, 120)),
    (r'mossy_cobblestone', (100, 118, 90)), (r'mossy_stone_brick', (104, 120, 96)), (r'cracked_stone_brick', (112, 112, 112)),
    (r'stone_brick', (122, 122, 122)), (r'cobblestone', (118, 118, 118)), (r'smooth_stone', (160, 160, 160)),
    (r'andesite', (136, 136, 138)), (r'diorite', (190, 190, 190)), (r'granite', (150, 104, 88)), (r'tuff', (108, 108, 98)),
    (r'deepslate', (72, 72, 78)), (r'basalt', (80, 80, 86)), (r'blackstone', (40, 36, 42)), (r'magma', (140, 60, 30)),
    (r'obsidian', (24, 18, 36)), (r'calcite', (222, 224, 220)), (r'dripstone', (132, 106, 90)),
    (r'stone', (126, 126, 126)),
    (r'white_concrete', (206, 212, 214)), (r'light_gray_concrete', (125, 125, 115)), (r'gray_concrete', (55, 58, 62)),
    (r'black_concrete', (8, 10, 15)), (r'cyan_concrete', (21, 119, 136)), (r'yellow_concrete', (240, 175, 21)),
    (r'red_concrete', (142, 32, 32)), (r'green_concrete', (73, 91, 36)), (r'orange_concrete', (224, 97, 1)),
    (r'blue_concrete', (44, 46, 143)), (r'brown_concrete', (96, 60, 32)), (r'lime_concrete', (94, 169, 24)),
    (r'white_terracotta', (210, 178, 161)), (r'light_gray_terracotta', (135, 107, 98)), (r'terracotta', (152, 94, 68)),
    (r'quartz', (234, 230, 222)), (r'polished_andesite', (132, 134, 133)),
    (r'iron_block', (220, 220, 220)), (r'iron_bars', (110, 110, 110)), (r'chain', (60, 60, 70)), (r'anvil', (70, 70, 70)),
    (r'oxidized', (80, 160, 130)), (r'copper', (180, 110, 80)), (r'weathered', (100, 150, 110)), (r'exposed', (160, 125, 95)),
    (r'glass', (170, 210, 225)), (r'sea_lantern', (200, 230, 225)), (r'glowstone', (240, 200, 110)), (r'shroomlight', (240, 150, 70)),
    (r'lantern', (230, 170, 80)), (r'torch', (250, 200, 90)), (r'redstone_lamp', (170, 100, 60)), (r'redstone_wire', (160, 10, 10)),
    (r'redstone_block', (170, 20, 20)), (r'redstone', (160, 20, 20)), (r'lever', (100, 100, 100)),
    (r'bone_block', (226, 220, 196)), (r'cobweb', (230, 230, 230)), (r'vine', (40, 100, 20)), (r'glow_lichen', (110, 140, 120)),
    (r'cave_vines', (60, 110, 30)), (r'fern', (60, 120, 40)), (r'grass', (80, 130, 50)), (r'lily_pad', (40, 110, 40)),
    (r'big_dripleaf', (80, 140, 40)), (r'dripleaf', (80, 140, 40)), (r'azalea', (80, 130, 50)), (r'sugar_cane', (130, 170, 90)),
    (r'melon', (110, 146, 30)), (r'cocoa', (140, 80, 30)), (r'mushroom', (180, 60, 60)), (r'flower|poppy|orchid|allium|tulip', (200, 60, 90)),
    (r'kelp', (50, 110, 40)), (r'seagrass', (50, 120, 40)), (r'sponge', (190, 180, 60)),
    (r'white_wool|white_carpet|white_bed', (230, 230, 230)), (r'_bed', (160, 40, 40)), (r'carpet', (120, 100, 90)), (r'wool', (180, 180, 180)),
    (r'bookshelf', (120, 80, 50)), (r'crafting|fletching|cartography|smithing|loom', (130, 95, 60)),
    (r'barrel', (130, 90, 50)), (r'chest', (160, 110, 40)), (r'furnace|smoker|blast', (100, 100, 100)),
    (r'cauldron', (60, 60, 60)), (r'brewing', (120, 110, 90)), (r'hopper', (70, 70, 70)), (r'observer', (100, 100, 100)),
    (r'dispenser|dropper', (110, 110, 110)), (r'piston', (150, 130, 90)), (r'target', (220, 200, 180)),
    (r'daylight', (130, 110, 80)), (r'note_block|jukebox', (100, 60, 40)), (r'lectern', (150, 110, 70)),
    (r'flower_pot|potted', (130, 70, 50)), (r'candle', (220, 200, 160)), (r'end_rod', (240, 240, 230)),
    (r'scaffolding', (190, 160, 90)), (r'ladder', (150, 110, 60)), (r'rail', (120, 110, 100)), (r'lightning_rod', (190, 120, 90)),
    (r'heavy_weighted|light_weighted|pressure_plate', (150, 150, 150)), (r'button', (120, 120, 120)), (r'sign', (170, 130, 80)),
    (r'banner', (200, 200, 200)), (r'skull|head', (200, 200, 180)), (r'tripwire', (200, 200, 200)),
    (r'honeycomb', (220, 150, 40)), (r'hay', (190, 160, 40)), (r'pumpkin', (200, 120, 20)), (r'coal_block', (20, 20, 20)),
    (r'prismarine', (90, 150, 140)), (r'purpur', (170, 120, 170)), (r'nether_brick', (50, 24, 28)), (r'netherrack', (110, 40, 40)),
    (r'slime', (110, 190, 90)), (r'tinted', (50, 40, 60)),
]
_COMPILEES = [(re.compile(p), c) for p, c in COULEURS]

# Blocs qu'on ne dessine pas du tout (trop fins, ou air)
INVISIBLES = re.compile(r'(^minecraft:(air|cave_air|void_air|light|barrier|structure_void)$)|tripwire|_button|pressure_plate')
# Blocs qui ne cachent pas ce qui est derriere (pour le tri des blocs exposes)
TRANSPARENTS = re.compile(r'air|glass|water|leaves|_pane|iron_bars|fence|wall|torch|lantern|sign|vine|lichen|fern|grass(?!_block)|'
                          r'flower|door|trapdoor|slab|stairs|carpet|chain|ladder|rail|cobweb|bed|chest|lever|pot|candle|'
                          r'redstone_wire|dripleaf|azalea(?!_leaves)|bamboo(?!_)|sapling|mushroom|cocoa|end_rod|rod|button|plate|'
                          r'kelp|seagrass|lily|banner|head|skull|scaffolding|cake|cauldron|anvil|hopper|lectern|brewing|bell|'
                          r'roots|cave_vines|sugar_cane|campfire|bars|pickle|coral|snow')


def couleur_de(nom):
    base = nom.split('[')[0]
    for rx, c in _COMPILEES:
        if rx.search(base):
            return c
    h = zlib.crc32(base.encode())
    return (80 + h % 120, 80 + (h >> 8) % 120, 80 + (h >> 16) % 120)


def tables(palette):
    """palette : dict nom -> index. Renvoie (couleurs Nx3, invisible N, transparent N)."""
    n = max(palette.values()) + 1
    col = np.zeros((n, 3), np.float32)
    inv = np.zeros(n, bool)
    tr = np.zeros(n, bool)
    for nom, i in palette.items():
        col[i] = couleur_de(nom)
        base = nom.split('[')[0]
        inv[i] = bool(INVISIBLES.search(base))
        tr[i] = bool(TRANSPARENTS.search(base)) or inv[i]
    return col, inv, tr


# ---------------------------------------------------------------- sprite en losange
def _gabarit(s):
    """Pour un bloc dont le coin (x, y+1, z) se projette en (0, 0) : liste de (du, dv, face).
    Projection : u = (x - z) * s, v = (x + z) * s/2 - y * s. face 0 = dessus, 1 = sud (+z), 2 = est (+x)."""
    h = s // 2
    pts = []
    for dv in range(-1, 2 * s + h + 1):
        for du in range(-s - 1, s + 1):
            cu, cv = du + 0.5, dv + 0.5
            # coordonnees du point dans le repere du bloc : resoudre sur chaque face
            # dessus : y = 1 ; u = (a - b) s, v = (a + b) h  -> a, b dans [0,1]
            a = (cu / s + cv / h) / 2
            b = (cv / h - cu / s) / 2
            if 0 <= a < 1 and 0 <= b < 1:
                pts.append((du, dv, 0)); continue
            # face sud (z = 1) : u = (a - 1) s, v = (a + 1) h + t s, t = descente 0..1
            a = cu / s + 1
            if 0 <= a < 1:
                t = (cv - (a + 1) * h) / s
                if 0 <= t < 1:
                    pts.append((du, dv, 1)); continue
            # face est (x = 1) : u = (1 - b) s, v = (1 + b) h + t s
            b = 1 - cu / s
            if 0 <= b < 1:
                t = (cv - (1 + b) * h) / s
                if 0 <= t < 1:
                    pts.append((du, dv, 2)); continue
    return np.array(pts, np.int32)


OMBRE = np.array([1.0, 0.78, 0.62], np.float32)


def iso(blocs, palette, s=4, fond=(18, 20, 24), masque=None, eclairage=True):
    """blocs : tableau [y, z, x] d'indices de palette. masque : booleen [y, z, x] des blocs a
    garder (coupe). Renvoie une image PIL."""
    H, L, W = blocs.shape
    col, inv, tr = tables(palette)
    visible = ~inv[blocs]
    if masque is not None:
        visible &= masque
    # expose si un voisin +x, +y ou +z n'est pas un bloc plein dessine
    cache = visible & ~tr[blocs]
    expose = np.zeros_like(visible)
    expose[:, :, -1] = True; expose[-1] = True; expose[:, -1, :] = True
    expose[:-1] |= ~cache[1:]
    expose[:, :-1] |= ~cache[:, 1:]
    expose[:, :, :-1] |= ~cache[:, :, 1:]
    expose &= visible
    y, z, x = np.nonzero(expose)
    ids = blocs[y, z, x]
    ordre = np.argsort(x + y + z, kind='stable')
    y, z, x, ids = y[ordre], z[ordre], x[ordre], ids[ordre]
    h = s // 2
    u0 = (x - z) * s
    v0 = (x + z) * h - (y + 1) * s
    umin, vmin = -L * s - s - 2, -H * s - s - 2
    larg = (W + L) * s + 2 * s + 6
    haut = (W + L) * h + H * s + 3 * s + 6
    img = np.empty((haut, larg, 3), np.float32)
    img[:] = fond
    base = col[ids]
    # lumiere : un peu plus sombre en bas des volumes, bruit par bloc pour lire la matiere
    bruit = (((x * 73856093) ^ (y * 19349663) ^ (z * 83492791)) & 255).astype(np.float32) / 255.0
    base = base * (0.9 + 0.2 * bruit)[:, None]
    if eclairage:
        # ombre portee grossiere : un bloc qui a un bloc plein au-dessus dans les 12 suivants est plus sombre
        plein = ~tr[blocs] & ~inv[blocs]
        couvert = np.zeros((H, L, W), bool)
        acc = np.zeros((L, W), bool)
        for yy in range(H - 1, -1, -1):
            couvert[yy] = acc
            acc = acc | plein[yy]
        base = base * np.where(couvert[y, z, x], 0.72, 1.0)[:, None]
    # z-buffer : profondeur = x + y + z (le plus grand est le plus proche de l'oeil)
    prof = (x + y + z).astype(np.int32)
    zb = np.full(haut * larg, -1, np.int32)
    gab = _gabarit(s)
    for du, dv, f in gab:
        np.maximum.at(zb, (v0 + dv - vmin) * larg + (u0 + du - umin), prof)
    plat = img.reshape(-1, 3)
    for du, dv, f in gab:
        idx = (v0 + dv - vmin) * larg + (u0 + du - umin)
        ok = zb[idx] == prof
        plat[idx[ok]] = base[ok] * OMBRE[f]
    img = np.clip(img, 0, 255).astype(np.uint8)
    # recadrer sur le contenu
    m = np.any(img != np.array(fond, np.uint8), axis=2)
    if m.any():
        rr = np.nonzero(m.any(1))[0]; cc = np.nonzero(m.any(0))[0]
        img = img[max(rr[0] - 8, 0):rr[-1] + 9, max(cc[0] - 8, 0):cc[-1] + 9]
    return Image.fromarray(img)


def plan(blocs, palette, y0, y1, px=6, grille=True):
    """Coupe d'etage vue de dessus : pour chaque colonne, le plus haut bloc dessine entre y0 et
    y1 (inclus), assombri selon sa profondeur sous y1. Les murs (bloc plein a y1) sont fonces."""
    col, inv, tr = tables(palette)
    tranche = blocs[y0:y1 + 1]
    vis = ~inv[tranche]
    n = tranche.shape[0]
    idx_haut = np.where(vis.any(0), n - 1 - np.argmax(vis[::-1], axis=0), -1)
    L, W = idx_haut.shape
    zz, xx = np.indices((L, W))
    ids = tranche[np.clip(idx_haut, 0, n - 1), zz, xx]
    c = col[ids] * (0.55 + 0.45 * (idx_haut / max(n - 1, 1)))[..., None]
    c[idx_haut < 0] = (20, 20, 24)
    img = np.repeat(np.repeat(np.clip(c, 0, 255).astype(np.uint8), px, 0), px, 1)
    if grille and px >= 4:
        img[::px, :] = (img[::px, :] * 0.85).astype(np.uint8)
        img[:, ::px] = (img[:, ::px] * 0.85).astype(np.uint8)
    return Image.fromarray(img)


def carte(blocs, palette, px=1):
    """Carte vue du ciel : plus haut bloc de chaque colonne, ombrage du relief (nord-ouest)."""
    col, inv, tr = tables(palette)
    vis = ~inv[blocs]
    H = blocs.shape[0]
    haut = np.where(vis.any(0), H - 1 - np.argmax(vis[::-1], axis=0), 0)
    zz, xx = np.indices(haut.shape)
    ids = blocs[haut, zz, xx]
    c = col[ids]
    gx = np.zeros_like(haut, np.float32); gz = np.zeros_like(gx)
    gx[:, 1:-1] = haut[:, 2:] - haut[:, :-2]
    gz[1:-1] = haut[2:] - haut[:-2]
    lum = np.clip(1.0 - 0.06 * (gx + gz), 0.55, 1.35)
    c = c * lum[..., None] * (0.8 + 0.2 * haut[..., None] / H)
    img = np.clip(c, 0, 255).astype(np.uint8)
    if px > 1:
        img = np.repeat(np.repeat(img, px, 0), px, 1)
    return Image.fromarray(img)
