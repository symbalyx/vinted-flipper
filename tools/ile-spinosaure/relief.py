"""Relief de l'ile (768 x 768) : cartes de hauteur, d'eau et de zones.

  - cote decoupee (baies, caps), plages, recif et lagon au sud-ouest ;
  - volcan endormi au nord-est : lac de cratere, canyon ouvert a l'ouest, cascade ;
  - crete ouest : collines rocheuses a falaises ;
  - riviere principale : du pied de la cascade, elle contourne le campus par le nord, traverse
    le lac central et se divise en delta a mangrove au sud ;
  - affluent depuis la crete ouest, et bras oriental jusqu'a la cote est ;
  - plaine de jungle ondulee entre les deux.

Toutes les eaux libres (mer, rivieres, lac) sont au niveau de la mer : c'est un seul reseau,
le territoire du spinosaure. Seul le lac de cratere est perche."""
import math

import numpy as np


def lisse(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


class Bruit:
    def __init__(self, W, L, graine):
        self.W, self.L, self.g = W, L, graine

    def valeur(self, echelle, graine):
        g = np.random.default_rng(self.g * 1000 + graine)
        n = int(max(self.W, self.L) / echelle) + 3
        grille = g.random((n, n))
        ys, xs = np.mgrid[0:self.L, 0:self.W] / echelle
        x0, y0 = np.floor(xs).astype(int), np.floor(ys).astype(int)
        fx, fy = xs - x0, ys - y0
        fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a, b = grille[y0, x0], grille[y0, x0 + 1]
        c, d = grille[y0 + 1, x0], grille[y0 + 1, x0 + 1]
        return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

    def fbm(self, echelle, octaves, graine):
        t, amp, tot = 0, 1.0, 0
        for o in range(octaves):
            t = t + amp * self.valeur(echelle / 2 ** o, graine * 10 + o)
            tot += amp
            amp *= 0.5
        return t / tot


def catmull(pts, pas=4.0):
    """Spline de Catmull-Rom echantillonnee tous les ~`pas` blocs."""
    out = []
    p = [pts[0]] + list(pts) + [pts[-1]]
    for i in range(1, len(p) - 2):
        seg = math.dist(p[i], p[i + 1])
        n = max(2, int(seg / pas))
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p[i][k]) + (-p[i - 1][k] + p[i + 1][k]) * t
                                    + (2 * p[i - 1][k] - 5 * p[i][k] + 4 * p[i + 1][k] - p[i + 2][k]) * t2
                                    + (-p[i - 1][k] + 3 * p[i][k] - 3 * p[i + 1][k] + p[i + 2][k]) * t3)
                             for k in range(2)))
    out.append(tuple(pts[-1]))
    return out


def distance_polyligne(W, L, ligne, rayon_max, val=None):
    """Distance (bornee a rayon_max) de chaque colonne a la polyligne, et valeur interpolee
    `val` (liste par sommet) au point le plus proche. Calcule par boites englobantes."""
    d = np.full((L, W), 1e9, np.float32)
    v = np.zeros((L, W), np.float32)
    val = val if val is not None else [0.0] * len(ligne)
    for i in range(len(ligne) - 1):
        (ax, az), (bx, bz) = ligne[i], ligne[i + 1]
        x0 = max(int(min(ax, bx) - rayon_max), 0); x1 = min(int(max(ax, bx) + rayon_max) + 1, W)
        z0 = max(int(min(az, bz) - rayon_max), 0); z1 = min(int(max(az, bz) + rayon_max) + 1, L)
        if x0 >= x1 or z0 >= z1:
            continue
        zz, xx = np.mgrid[z0:z1, x0:x1].astype(np.float32)
        vx, vz = bx - ax, bz - az
        l2 = max(vx * vx + vz * vz, 1e-6)
        t = np.clip(((xx - ax) * vx + (zz - az) * vz) / l2, 0, 1)
        di = np.hypot(xx - (ax + t * vx), zz - (az + t * vz))
        zone = d[z0:z1, x0:x1]
        mieux = di < zone
        zone[mieux] = di[mieux]
        v[z0:z1, x0:x1][mieux] = (val[i] + (val[i + 1] - val[i]) * t)[mieux]
    return d, v


class Relief:
    def __init__(self, W=768, L=768, SEA=48, graine=7):
        self.W, self.L, self.SEA = W, L, SEA
        self.n = Bruit(W, L, graine)
        self.zz, self.xx = np.mgrid[0:L, 0:W].astype(np.float32)
        # points remarquables (x, z)
        self.VOLCAN = (572.0, 200.0)
        self.CAMPUS = (455, 345)                  # origine du campus (coin nord-ouest de son repere)
        self.LAC = (330.0, 440.0)
        self.CASCADE_BASSIN = (500.0, 236.0)
        self.RIVIERE = [(500, 236), (494, 266), (516, 296), (515, 322), (478, 330), (440, 338), (412, 360), (380, 395),
                        (345, 430), (318, 470), (310, 520), (318, 560), (322, 600), (318, 640), (312, 690), (306, 740)]
        self.DELTA_O = [(320, 590), (296, 620), (270, 650), (250, 700)]
        self.DELTA_E = [(320, 596), (350, 625), (378, 652), (396, 700)]
        self.AFFLUENT = [(185, 300), (205, 322), (235, 352), (262, 390), (292, 420), (320, 438)]
        self.BRAS_EST = [(516, 322), (560, 318), (610, 300), (640, 330), (670, 380), (700, 400), (735, 410), (775, 420)]

    def calculer(self):
        W, L, SEA, n = self.W, self.L, self.SEA, self.n
        xx, zz = self.xx, self.zz
        # ------------------------------------------------ contour de l'ile (distorsion de domaine)
        wx = (n.fbm(160, 3, 1) - 0.5) * 120
        wz = (n.fbm(160, 3, 2) - 0.5) * 120
        cx, cz = 384.0, 392.0
        d = np.hypot((xx + wx - cx) / 1.0, (zz + wz - cz) / 0.93)
        rayon = 292 + 70 * (n.fbm(140, 4, 3) - 0.5) + 30 * (n.fbm(60, 2, 31) - 0.5)
        c = (rayon - d) / 40.0                              # > 0 : terre
        self.c = c
        # fond marin puis plaine
        h = np.where(c < 0, SEA - 3 - np.minimum(34, -c * 16), 0.0)
        plaine = SEA + 2 + 5 * lisse(0, 1.2, c) + 16 * (n.fbm(90, 5, 4) - 0.38) * lisse(0.2, 2.0, c)
        # vallons doux
        plaine += 7 * (np.abs(n.fbm(60, 3, 5) - 0.5) * 2) * lisse(0.5, 2.5, c)
        # collines : quelques bosses franches dans la plaine (20-30 blocs)
        plaine += 34 * np.clip(n.fbm(120, 3, 32) - 0.55, 0, 1) * 2.2 * lisse(0.8, 2.5, c)
        h = np.where(c >= 0, plaine, h)
        # ------------------------------------------------ crete ouest
        crete = catmull([(170, 170), (148, 260), (140, 350), (152, 440), (176, 510), (205, 555)], 6)
        dc, tc = distance_polyligne(W, L, crete, 70, list(np.linspace(0, 1, len(crete))))
        haut_crete = 58 * np.clip(np.sin(np.clip(tc, 0, 1) * math.pi), 0, 1) ** 0.6 * (0.75 + 0.5 * n.fbm(40, 3, 6))
        profil = haut_crete * np.clip(1 - dc / 60, 0, 1) ** 1.4
        # falaises en gradins : on quantifie une partie du profil
        gradins = np.floor(profil / 6) * 6
        profil = np.where(n.fbm(30, 2, 7) > 0.55, gradins + (profil - gradins) * 0.3, profil)
        h = np.where(c > 0.2, h + profil * lisse(0.2, 1.0, c), h)
        # ------------------------------------------------ volcan
        vx, vz = self.VOLCAN
        dv = np.hypot(xx - vx + (n.fbm(70, 2, 33) - 0.5) * 50, zz - vz + (n.fbm(70, 2, 34) - 0.5) * 50)
        ang = np.arctan2(zz - vz, xx - vx)
        # cone : levre du cratere a SEA+88 (dv = 40), flancs concaves avec ravines radiales
        levre = 88
        cone = levre * np.clip(1 - (dv - 40) / 150, 0, 1) ** 1.25
        cone *= 1 - 0.10 * (0.5 + 0.5 * np.sin(ang * 9 + 3 * n.fbm(50, 2, 8))) * lisse(45, 90, dv)
        cone += 5 * (n.fbm(40, 3, 9) - 0.5) * lisse(45, 120, dv)
        h = np.where(dv < 190, np.maximum(h, SEA - 4 + cone), h)
        # levre dentelee (sommets a +4..+10), puis la cuvette du cratere
        h = np.where((dv >= 32) & (dv < 42), np.maximum(h, SEA + levre + 2 + 8 * n.fbm(12, 2, 36)), h)
        self.LAC_CRATERE = SEA + levre - 8
        cratere = dv < 32
        h = np.where(cratere, self.LAC_CRATERE - 2 - 14 * (1 - (dv / 32) ** 2), h)
        self.cratere = cratere
        # canyon ouvert a l'ouest du cratere : du lac jusqu'au bassin de la cascade
        canyon = catmull([(vx - 24, vz + 4), (vx - 48, vz + 14), (vx - 62, vz + 26), self.CASCADE_BASSIN], 3)
        dk, tk = distance_polyligne(W, L, canyon, 30, list(np.linspace(0, 1, len(canyon))))
        # la chute : premier point de l'axe, sorti du cratere, ou le flanc passe sous le niveau du lac
        h_cone = h.copy()
        i_chute = len(canyon) // 2
        for i, (px, pz) in enumerate(canyon):
            if not cratere[int(pz), int(px)] and h_cone[int(pz), int(px)] < self.LAC_CRATERE + 2:
                i_chute = i
                break
        chute = i_chute / (len(canyon) - 1)
        largeur = 6 + 5 * tk
        dans_canyon = dk < largeur
        # partie perchee : dans le cratere ou sur un terrain plus haut que le lac
        haut = dans_canyon & (tk < chute) & (cratere | (h_cone >= self.LAC_CRATERE + 2))
        fond = np.where(haut, self.LAC_CRATERE - 3, SEA - 6)
        parois = (dk >= largeur) & (dk < largeur + 16) & ~haut
        h = np.where(dans_canyon, np.minimum(h, fond), h)
        h = np.where(parois & (tk >= chute - 0.05), np.minimum(h, np.maximum(SEA + 2, h - (largeur + 16 - dk) * 3)), h)
        self.canyon_haut = haut
        self.canyon_bas = dans_canyon & ~haut
        self.CHUTE = canyon[max(i_chute - 1, 0)]
        self.CHUTE_DIR = np.subtract(canyon[i_chute + 1], canyon[i_chute - 1])
        # ------------------------------------------------ rivieres
        def riviere(pts, w0, w1, prof):
            ligne = catmull(pts, 4)
            dr, t = distance_polyligne(W, L, ligne, w1 / 2 + 26, list(np.linspace(0, 1, len(ligne))))
            demi = (w0 + (w1 - w0) * t) / 2
            return dr, demi, prof
        self.lits = []
        for pts, w0, w1, prof in ((self.RIVIERE, 16, 28, 9), (self.DELTA_O, 16, 22, 6), (self.DELTA_E, 16, 22, 6),
                                  (self.AFFLUENT, 10, 16, 6), (self.BRAS_EST, 14, 20, 7)):
            self.lits.append(riviere(pts, w0, w1, prof))
        eau_riv = np.zeros((L, W), bool)
        for dr, demi, prof in self.lits:
            dans = dr < demi
            fond = SEA - 1 - prof * np.clip(1 - (dr / demi) ** 2, 0, 1) ** 0.7
            h = np.where(dans, np.minimum(h, fond), h)
            berge = (dr >= demi) & (dr < demi + 26)
            pente = SEA + 1 + (dr - demi) * 0.45 + 2 * (n.fbm(24, 2, 10) - 0.5)
            h = np.where(berge & ~cratere, np.minimum(h, pente), h)
            eau_riv |= dans
        # ------------------------------------------------ lac central (avec l'ile du repaire)
        lx, lz = self.LAC
        dl = np.hypot((xx - lx) / 1.25, zz - lz) * (1 + 0.25 * (n.fbm(40, 2, 11) - 0.5))
        lac = dl < 48
        h = np.where(lac, np.minimum(h, SEA - 2 - 10 * (1 - (dl / 48) ** 2)), h)
        h = np.where((dl >= 48) & (dl < 70), np.minimum(h, SEA + 1 + (dl - 48) * 0.35), h)
        ilot = np.hypot(xx - (lx + 12), zz - (lz - 6)) < 9
        h = np.where(ilot, np.maximum(h, SEA + 1 + (9 - np.hypot(xx - (lx + 12), zz - (lz - 6))) * 0.25), h)
        self.ILOT = (lx + 12, lz - 6)
        # ------------------------------------------------ lagon et recif au sud-ouest
        gx, gz = 178.0, 612.0
        dg = np.hypot(xx - gx, (zz - gz) * 1.2) * (1 + 0.35 * (n.fbm(45, 2, 35) - 0.5))
        lagon = (dg < 70) & (c < 2.2)
        h = np.where(lagon, np.minimum(h, SEA - 2 - 3 * n.fbm(20, 2, 12)), h)
        recif = (np.abs(dg - 82) < 3 + 3 * n.fbm(15, 2, 13)) & (n.fbm(25, 2, 14) > 0.42) & (c < 0.4)
        h = np.where(recif, np.maximum(h, SEA - 1 + 2.5 * (n.fbm(8, 2, 15) > 0.6)), h)
        self.lagon, self.recif = lagon, recif
        # ------------------------------------------------ plate-forme du campus
        ox, oz = self.CAMPUS
        G = SEA + 5
        x0, z0, x1, z1 = ox - 8, oz - 2, ox + 146, oz + 136
        dcamp = np.maximum(np.maximum(x0 - xx, xx - x1), np.maximum(z0 - zz, zz - z1))
        dedans = dcamp <= 0
        h = np.where(dedans, G - 1, h)
        marge = (dcamp > 0) & (dcamp < 30) & (h >= SEA + 1)
        h = np.where(marge, (G - 1) + (h - (G - 1)) * lisse(0, 30, dcamp), h)
        self.campus_zone = dcamp < 6
        self.G = G
        # ------------------------------------------------ finitions
        self.h = np.clip(np.round(h), 2, 250).astype(np.int16)
        eau = np.where(self.h < SEA, SEA, -1).astype(np.int16)
        perche = (cratere | self.canyon_haut) & (self.h < self.LAC_CRATERE) & (self.h >= self.LAC_CRATERE - 24)
        eau = np.where(perche, self.LAC_CRATERE, eau)
        self.eau = eau
        self.riviere = eau_riv & (self.h < SEA)
        self.lac = lac
        gz_, gx_ = np.gradient(self.h.astype(np.float32))
        self.pente = np.hypot(gx_, gz_)
        return self
