"""Vue isometrique (diorama) d'une zone de l'ile, colonne par colonne."""
import json
import sys

import numpy as np
from PIL import Image, ImageDraw

from apercu import couleur


def iso(base, x0, z0, x1, z1, s, sortie, yplancher=None):
    blocs = np.load(base + '.blocs.npy')
    meta = json.load(open(base + '.meta.json'))
    pal = {v: k for k, v in meta['palette'].items()}
    lut = np.array([couleur(pal[i]) or (0, 0, 0) for i in range(len(pal))], dtype=float)
    air = np.array([couleur(pal[i]) is None for i in range(len(pal))])
    b = blocs[:, z0:z1, x0:x1]
    H = b.shape[0]
    na = ~air[b]
    haut = H - 1 - np.argmax(na[::-1], axis=0)
    zz, xx = np.mgrid[0:z1 - z0, 0:x1 - x0]
    top = b[haut, zz, xx]
    col = lut[top]
    plancher = int(haut.min()) if yplancher is None else yplancher
    lw, lh = (x1 - x0 + z1 - z0) * s + 20, int((x1 - x0 + z1 - z0) * s / 2 + (H - plancher) * s) + 40
    im = Image.new('RGB', (lw, lh), (22, 26, 34))
    d = ImageDraw.Draw(im)
    ox, oy = (z1 - z0) * s + 10, (H - plancher) * s + 20

    def P(x, y, z):
        return (ox + (x - z) * s, oy + (x + z) * s / 2 - (y - plancher) * s)

    for somme in range((x1 - x0) + (z1 - z0) - 1):
        for x in range(max(0, somme - (z1 - z0) + 1), min(x1 - x0, somme + 1)):
            z = somme - x
            y = haut[z, x]
            c = col[z, x]
            yb = min(haut[z, x + 1] if x + 1 < x1 - x0 else plancher, haut[z + 1, x] if z + 1 < z1 - z0 else plancher)
            yb = min(yb, y) if yb < y else y
            # faces laterales (visibles : +x a droite, +z a gauche)
            if yb < y or True:
                bas = max(plancher, min(yb, y - 1)) if yb < y else y
                d.polygon([P(x + 1, y + 1, z), P(x + 1, y + 1, z + 1), P(x + 1, bas, z + 1), P(x + 1, bas, z)],
                          fill=tuple(int(v * 0.72) for v in c))
                d.polygon([P(x, y + 1, z + 1), P(x + 1, y + 1, z + 1), P(x + 1, bas, z + 1), P(x, bas, z + 1)],
                          fill=tuple(int(v * 0.55) for v in c))
            d.polygon([P(x, y + 1, z), P(x + 1, y + 1, z), P(x + 1, y + 1, z + 1), P(x, y + 1, z + 1)],
                      fill=tuple(int(v) for v in c))
    im.save(sortie)
    print('ecrit', sortie)


if __name__ == '__main__':
    base = sys.argv[1]
    iso(base, 0, 0, 384, 384, 2, base + '_iso_ile.png', yplancher=30)
    iso(base, 110, 140, 250, 250, 6, base + '_iso_labo.png', yplancher=36)
