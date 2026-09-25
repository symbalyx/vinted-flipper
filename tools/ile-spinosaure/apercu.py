"""Apercus de l'ile : carte vue de dessus (ombrage du relief) et gros plan du laboratoire."""
import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

COULEURS = {
    'air': None, 'water': (38, 78, 150), 'grass_block': (74, 132, 44), 'podzol': (92, 70, 38),
    'moss_block': (86, 120, 46), 'coarse_dirt': (110, 80, 56), 'dirt': (120, 86, 60), 'sand': (219, 207, 163),
    'sandstone': (216, 203, 155), 'mud': (60, 57, 60), 'gravel': (130, 124, 122), 'clay': (160, 166, 179),
    'stone': (125, 125, 125), 'andesite': (136, 136, 137), 'tuff': (108, 109, 102), 'jungle_leaves': (48, 110, 28),
    'jungle_log': (85, 68, 25), 'dirt_path': (148, 122, 65), 'grass': (90, 150, 50), 'fern': (80, 140, 50),
    'large_fern': (70, 130, 45), 'moss_carpet': (90, 125, 50), 'lily_pad': (32, 128, 48),
    'cave_vines': (80, 110, 40), 'cave_vines_plant': (80, 110, 40), 'vine': (60, 110, 30),
    'light_gray_concrete': (142, 142, 134), 'white_concrete': (207, 213, 214), 'gray_concrete': (54, 57, 61),
    'yellow_concrete': (240, 175, 21), 'black_concrete': (8, 10, 15), 'iron_bars': (150, 150, 150),
    'spruce_planks': (114, 84, 48), 'oak_planks': (162, 130, 78), 'stone_bricks': (122, 121, 122),
    'mossy_cobblestone': (100, 118, 94), 'polished_andesite': (132, 134, 133), 'glass': (200, 220, 230),
}


def couleur(nom):
    base = nom.split('[')[0].split(':')[1]
    if base in COULEURS:
        return COULEURS[base]
    if 'wool' in base:
        return (230, 230, 230)
    if 'concrete' in base or 'terracotta' in base:
        return (150, 60, 50)
    if 'log' in base or 'planks' in base or 'slab' in base or 'fence' in base:
        return (120, 90, 50)
    return (170, 150, 140)


def main(base):
    blocs = np.load(base + '.blocs.npy')
    meta = json.load(open(base + '.meta.json'))
    palette = {v: k for k, v in meta['palette'].items()}
    H, L, W = blocs.shape
    lut = np.zeros((len(palette), 3), dtype=np.float32)
    air = np.zeros(len(palette), dtype=bool)
    for i, nom in palette.items():
        c = couleur(nom)
        if c is None:
            air[i] = True
        else:
            lut[i] = c
    non_air = ~air[blocs]
    haut = H - 1 - np.argmax(non_air[::-1], axis=0)                      # plus haut bloc non vide
    zz, xx = np.mgrid[0:L, 0:W]
    top = blocs[haut, zz, xx]
    img = lut[top]
    # ombrage du relief
    gz, gx = np.gradient(haut.astype(float))
    ombre = np.clip(1 + (gx - gz) * 0.12, 0.55, 1.35)[..., None]
    eau = np.array([palette[i].startswith('minecraft:water') for i in range(len(palette))])[top]
    sol = np.array(meta['sol'])
    prof = np.clip((haut - sol) / 12.0, 0, 1)[..., None]
    img = np.where(eau[..., None], img * (1.1 - 0.5 * prof), img * ombre)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGB').resize((W * 2, L * 2), Image.NEAREST)
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 15)
    except OSError:
        f = ImageFont.load_default()
    noms = {'ponton': 'Ponton d\'arrivee', 'tour': 'Tour de guet', 'camp': 'Campement', 'crash': 'Helicoptere',
            'labo': 'Laboratoire', 'enclos': 'Enclos S-01 (breche)', 'cascade': 'Cascade + grotte', 'pont': 'Pont casse'}
    for k, (x, z) in meta['poi'].items():
        d.ellipse((x * 2 - 6, z * 2 - 6, x * 2 + 6, z * 2 + 6), outline=(255, 40, 40), width=3)
        d.text((x * 2 + 9, z * 2 - 9), noms[k], fill=(255, 255, 255), font=f, stroke_width=3, stroke_fill=(0, 0, 0))
    d.text((10, 10), 'SITE B - 384 x 384 blocs (nord en haut)', fill=(255, 255, 255), font=f, stroke_width=3, stroke_fill=(0, 0, 0))
    im.save(base + '_carte.png')
    # gros plan du laboratoire, toit et canopee retires (coupe a hauteur du rez-de-chaussee + 4)
    for nom_coupe, yc in (('rdc', meta['SEA'] + 3 + 4), ('sous_sol', meta['SEA'] + 2), ('etage', meta['SEA'] + 3 + 10)):
        x0, z0, x1, z1 = 110, 150, 240, 250
        b = blocs[:yc + 1, z0:z1, x0:x1]
        na = ~air[b]
        hh = yc - np.argmax(na[::-1], axis=0)
        z2, x2 = np.mgrid[0:z1 - z0, 0:x1 - x0]
        t = b[hh, z2, x2]
        c2 = lut[t] * np.clip(0.55 + 0.45 * (hh - (yc - 12)) / 12, 0.4, 1.0)[..., None]
        Image.fromarray(np.clip(c2, 0, 255).astype(np.uint8), 'RGB').resize(((x1 - x0) * 5, (z1 - z0) * 5), Image.NEAREST) \
            .save(base + '_labo_%s.png' % nom_coupe)
    print('ecrit', base + '_carte.png')


if __name__ == '__main__':
    main(sys.argv[1])
