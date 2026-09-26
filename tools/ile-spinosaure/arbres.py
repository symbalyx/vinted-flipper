"""Arbres de jungle credibles, a l'echelle d'un animal de 13 blocs.

Plutot que des sucettes (tronc + boule), chaque essence a sa silhouette :
- emergent (fromager / kapok) : contreforts en ailettes, fut droit et nu sur 25-40 blocs,
  branches maitresses qui partent haut, couronne en parasol faite de grappes aplaties ;
- canopee : tronc qui ondule, fourche en 2-4 branches, grappes irregulieres ;
- figuier etrangleur : reseau de racines ajoure qui enserre un tronc ;
- palmier : stipe fin et courbe, palmes qui retombent ;
- paletuvier : racines-echasses arquees au-dessus de l'eau ;
- sous-bois : buissons, jeunes arbres, fougeres, bambous, troncs couches couverts de mousse.

Toutes les feuilles sont persistantes (sinon elles se decomposent loin d'un tronc)."""
import math

import numpy as np

FEUILLES = 'minecraft:%s_leaves[distance=7,persistent=true,waterlogged=false]'
F_JUNGLE = FEUILLES % 'jungle'
F_CHENE = FEUILLES % 'oak'
F_AZALEE = FEUILLES % 'azalea'
F_AZALEE_FLEUR = FEUILLES % 'flowering_azalea'
F_MANGROVE = FEUILLES % 'mangrove'
F_SOMBRE = FEUILLES % 'dark_oak'


def tronc(bois='jungle', ecorce=False):
    nom = 'minecraft:%s_%s' % (bois, 'wood' if ecorce else 'log')
    return lambda axe: '%s[axis=%s]' % (nom, axe)


VIGNE = 'minecraft:vine[east=%s,north=%s,south=%s,up=false,west=%s]'
DIRS = {'north': (0, -1), 'south': (0, 1), 'west': (-1, 0), 'east': (1, 0)}
OPPOSE = {'north': 'south', 'south': 'north', 'west': 'east', 'east': 'west'}


def vigne(face):
    """Vigne accrochee au bloc situe du cote `face`."""
    return VIGNE % tuple('true' if f == face else 'false' for f in ('east', 'north', 'south', 'west'))


class Foret:
    """Pose les arbres dans un Monde. sol[z, x] : premier y libre au-dessus du sol."""

    def __init__(self, m, sol, rng):
        self.m, self.sol, self.rng = m, sol, rng
        self.feuilles = set()

    def P(self, e):
        i = self.m.P(e)
        if 'leaves' in e:
            self.feuilles.add(i)
        return e

    # ------------------------------------------------------------------ briques
    def fut(self, cx, cz, y0, h, r0, r1, bois='jungle', derive=0.0, phase=0.0):
        """Tronc rond, de rayon r0 en bas a r1 en haut, centre (cx, cz) flottant qui derive
        doucement. Renvoie la liste des centres par etage."""
        m = self.m
        etat = tronc(bois)('y')
        centres = []
        prec = set()
        for k in range(h):
            t = k / max(h - 1, 1)
            r = r0 + (r1 - r0) * t
            ox = derive * math.sin(phase + t * 2.2) * t
            oz = derive * math.cos(phase * 1.3 + t * 1.7) * t
            x, z = cx + ox, cz + oz
            centres.append((x, z, r))
            ir = int(math.ceil(r)) + 1
            disque = {(bx, bz) for bx in range(int(x) - ir, int(x) + ir + 1) for bz in range(int(z) - ir, int(z) + ir + 1)
                      if (bx + 0.5 - x) ** 2 + (bz + 0.5 - z) ** 2 <= r * r}
            if not disque:
                disque = {(int(math.floor(x)), int(math.floor(z)))}
            if prec and not (disque & prec):
                # le fut s'est decale : on garde l'etage precedent a cette hauteur aussi, pour que le
                # tronc reste d'un seul tenant (sinon il ne se touche que par les coins)
                disque = disque | prec
            for (bx, bz) in disque:
                m.pose(bx, y0 + k, bz, etat)
                if k == 0 and 0 <= bx < m.W and 0 <= bz < m.L:
                    # ancrage : sur une pente, chaque colonne du pied descend jusqu'au sol
                    for yy in range(int(self.sol[bz, bx]) - 1, y0):
                        m.pose(bx, yy, bz, etat)
            prec = disque
        return centres

    def grappe(self, cx, cy, cz, rx, ry, feuille=F_JUNGLE, dessous_vide=True):
        """Grappe de feuilles aplatie et irreguliere : un gros disque et 2-4 sous-grappes."""
        rng = self.rng
        self.P(feuille)
        self.m.ellipsoide(cx, cy, cz, rx, ry, rx * rng.uniform(0.8, 1.2), feuille, bruit=0.35, rng=rng)
        for _ in range(rng.integers(2, 5)):
            a = rng.uniform(0, 2 * math.pi)
            d = rng.uniform(0.3, 0.8) * rx
            r = rx * rng.uniform(0.45, 0.7)
            self.m.ellipsoide(cx + d * math.cos(a), cy + rng.uniform(-0.3, 1.0) * ry, cz + d * math.sin(a),
                              r, ry * rng.uniform(0.7, 1.0), r * rng.uniform(0.8, 1.2), feuille, bruit=0.45, rng=rng)
        # taches de feuilles d'azalee (epiphytes, fleurs) pour casser l'uniformite
        if feuille == F_JUNGLE and rng.random() < 0.5:
            for _ in range(rng.integers(1, 4)):
                a = rng.uniform(0, 2 * math.pi); d = rng.uniform(0, rx)
                x, z = int(cx + d * math.cos(a)), int(cz + d * math.sin(a))
                # on recolore des feuilles existantes, on n'en ajoute pas (sinon touffes en l'air)
                self.m.ellipsoide(x, cy + ry * 0.4, z, 1.6, 1.2, 1.6,
                                  self.P(F_AZALEE_FLEUR if rng.random() < 0.4 else F_AZALEE),
                                  seulement={self.m.P(feuille)}, rng=rng)

    def branche(self, a, b, bois='jungle', epaisseur=0.0):
        self.m.ligne(a, b, tronc(bois, ecorce=True), epaisseur)

    def contreforts(self, cx, cz, y0, r, n, hauteur, longueur, bois='jungle'):
        """Ailettes radiales d'un bloc d'epaisseur, hautes contre le tronc, qui s'effilent au sol
        en suivant le relief."""
        m, rng = self.m, self.rng
        etat = tronc(bois, ecorce=True)('y')
        a0 = rng.uniform(0, 2 * math.pi)
        for i in range(n):
            a = a0 + i * 2 * math.pi / n + rng.uniform(-0.3, 0.3)
            L = longueur * rng.uniform(0.7, 1.2)
            ca, sa = math.cos(a), math.sin(a)
            pas = int(L * 2) + 2
            for k in range(pas):
                d = r - 0.3 + (L - r) * k / pas
                t = (d - r) / max(L - r, 1)
                h = int(round(hauteur * (1 - t) ** 1.6))
                # l'ailette serpente un peu
                d2 = d + 0.0
                off = math.sin(t * 3 + i) * 0.8 * t
                x = cx + ca * d2 - sa * off
                z = cz + sa * d2 + ca * off
                bx, bz = int(math.floor(x)), int(math.floor(z))
                if not (0 <= bx < m.W and 0 <= bz < m.L):
                    continue
                ys = self.sol[bz, bx]
                bas = min(ys, y0) - 1
                for y in range(bas, y0 + max(h, 0)):
                    m.pose(bx, y, bz, etat)

    def vignes_sous(self, cx, cy, cz, r, n, lmax):
        """Rideaux de vignes accroches au bord inferieur des feuillages proches."""
        m, rng = self.m, self.rng
        for _ in range(n):
            a = rng.uniform(0, 2 * math.pi); d = rng.uniform(0.5, 1.0) * r
            x, z = int(cx + d * math.cos(a)), int(cz + d * math.sin(a))
            # trouver une feuille dans la colonne sous cy+2
            y = int(cy) + 2
            while y > cy - 6 and not (m.dedans(x, y, z) and m.get(x, y, z) in self.feuilles):
                y -= 1
            if y <= cy - 6:
                continue
            face = rng.choice(list(DIRS))
            dx, dz = DIRS[face]
            vx, vz = x - dx, z - dz          # bloc voisin, la vigne regarde la feuille
            if not m.dedans(vx, y, vz) or m.get(vx, y, vz) != m.AIR:
                continue
            etat = vigne(face)
            long = int(rng.integers(3, lmax + 1))
            for k in range(long):
                yy = y - k
                if yy <= self.sol[min(max(vz, 0), m.L - 1), min(max(vx, 0), m.W - 1)] + 1 or m.get(vx, yy, vz) != m.AIR:
                    break
                m.pose(vx, yy, vz, etat)

    def habiller_tronc(self, centres, y0, frac_vigne=0.25, cacao=True):
        """Vignes plaquees et cabosses sur les faces du tronc."""
        m, rng = self.m, self.rng
        for k, (x, z, r) in enumerate(centres):
            y = y0 + k
            for face, (dx, dz) in DIRS.items():
                # bloc juste a l'exterieur du tronc de ce cote
                bx = int(math.floor(x + dx * (r + 0.6)))
                bz = int(math.floor(z + dz * (r + 0.6)))
                if m.get(bx, y, bz) != m.AIR:
                    continue
                if 'log' not in m.nom(m.get(bx + dx, y, bz + dz)):
                    continue
                u = rng.random()
                if u < frac_vigne:
                    m.pose(bx, y, bz, vigne(face))
                elif cacao and u < frac_vigne + 0.012 and 2 < k < 14:
                    m.pose(bx, y, bz, 'minecraft:cocoa[age=%d,facing=%s]' % (rng.integers(0, 3), face))

    # ------------------------------------------------------------------ essences
    def emergent(self, x, z, h=None):
        """Fromager geant. Empreinte au sol ~ 14 blocs de diametre (contreforts)."""
        rng, m = self.rng, self.m
        y0 = int(self.sol[z, x])
        h = h or int(rng.integers(30, 42))
        r0 = rng.uniform(1.6, 2.1)
        cx, cz = x + 0.5, z + 0.5
        centres = self.fut(cx, cz, y0 - 1, h, r0, r0 * 0.55, derive=rng.uniform(0.5, 1.5), phase=rng.uniform(0, 6))
        self.contreforts(cx, cz, y0, r0, int(rng.integers(5, 8)), hauteur=rng.uniform(5, 8), longueur=r0 + rng.uniform(4, 6.5))
        tx, tz, tr = centres[-1]
        ty = y0 - 1 + h
        # branches maitresses : 4 a 6, depuis les 25 % superieurs, qui montent en s'ecartant
        nb = int(rng.integers(4, 7))
        a0 = rng.uniform(0, 2 * math.pi)
        for i in range(nb):
            a = a0 + i * 2 * math.pi / nb + rng.uniform(-0.35, 0.35)
            k = int(h * rng.uniform(0.72, 0.92))
            bx, bz, _ = centres[k]
            by = y0 - 1 + k
            L = rng.uniform(8, 13)
            fin = (bx + math.cos(a) * L, by + rng.uniform(4, 8), bz + math.sin(a) * L)
            self.branche((bx, by, bz), fin, epaisseur=0.6)
            # rameaux
            for _ in range(int(rng.integers(1, 3))):
                a2 = a + rng.uniform(-0.9, 0.9)
                L2 = rng.uniform(3, 6)
                mil = (bx + math.cos(a) * L * 0.6, by + (fin[1] - by) * 0.6, bz + math.sin(a) * L * 0.6)
                fin2 = (mil[0] + math.cos(a2) * L2, mil[1] + rng.uniform(1, 3), mil[2] + math.sin(a2) * L2)
                self.branche(mil, fin2)
                self.grappe(fin2[0], fin2[1] + 1, fin2[2], rng.uniform(3.2, 4.5), rng.uniform(1.6, 2.2))
            self.grappe(fin[0], fin[1] + 1, fin[2], rng.uniform(4.5, 6.5), rng.uniform(1.8, 2.6))
        # coeur de couronne au sommet du fut
        self.grappe(tx, ty + 2, tz, rng.uniform(4.5, 6), 2.2)
        self.habiller_tronc(centres, y0 - 1, frac_vigne=0.18)
        self.vignes_sous(tx, ty + 3, tz, 11, 22, 12)
        return h

    def canopee(self, x, z, h=None, bois='jungle', feuille=F_JUNGLE):
        """Arbre de la voute : 16-26 blocs, tronc qui ondule, fourche."""
        rng = self.rng
        y0 = int(self.sol[z, x])
        h = h or int(rng.integers(15, 25))
        r0 = rng.choice([0.72, 1.0, 1.0, 1.25])
        cx, cz = (x + 0.5, z + 0.5) if r0 < 0.9 else (x + 1.0, z + 1.0)
        centres = self.fut(cx, cz, y0 - 1, h, r0, max(r0 * 0.7, 0.6), bois=bois, derive=rng.uniform(1, 2.5),
                           phase=rng.uniform(0, 6))
        if r0 >= 1.0:
            self.contreforts(cx, cz, y0, r0, int(rng.integers(3, 6)), hauteur=rng.uniform(2, 4), longueur=r0 + rng.uniform(2, 3.5),
                             bois=bois)
        tx, tz, _ = centres[-1]
        ty = y0 - 1 + h
        nb = int(rng.integers(2, 5))
        a0 = rng.uniform(0, 2 * math.pi)
        for i in range(nb):
            a = a0 + i * 2 * math.pi / nb + rng.uniform(-0.5, 0.5)
            k = int(h * rng.uniform(0.62, 0.9))
            bx, bz, _ = centres[k]
            by = y0 - 1 + k
            L = rng.uniform(4, 8)
            fin = (bx + math.cos(a) * L, by + rng.uniform(3, 6), bz + math.sin(a) * L)
            self.branche((bx, by, bz), fin, bois=bois)
            self.grappe(fin[0], fin[1] + 1, fin[2], rng.uniform(3.2, 5), rng.uniform(1.5, 2.2), feuille)
        self.grappe(tx, ty + 1.5, tz, rng.uniform(3.5, 5), 2.0, feuille)
        self.habiller_tronc(centres, y0 - 1, frac_vigne=0.3, cacao=bois == 'jungle')
        self.vignes_sous(tx, ty + 2, tz, 7, 10, 9)
        return h

    def etrangleur(self, x, z):
        """Figuier etrangleur : l'hote a pourri, il reste une cage de racines tressees, creuse,
        dans laquelle on peut se cacher (1 bloc de passage)."""
        rng, m = self.rng, self.m
        y0 = int(self.sol[z, x])
        h = int(rng.integers(20, 30))
        cx, cz = x + 0.5, z + 0.5
        R = rng.uniform(2.2, 2.8)
        etat = tronc('jungle', ecorce=True)
        brins = int(rng.integers(7, 10))
        for i in range(brins):
            a = i * 2 * math.pi / brins
            sens = 1 if i % 2 else -1
            pts = []
            for k in range(0, h + 1, 2):
                t = k / h
                aa = a + sens * t * 2.4
                rr = R * (1 - 0.45 * t) + (1.2 * (1 - t) ** 3 if k < 4 else 0)
                pts.append((cx + math.cos(aa) * rr, y0 - 1 + k, cz + math.sin(aa) * rr))
            for p, q in zip(pts, pts[1:]):
                m.ligne(p, q, etat)
        # une ouverture au pied (on peut s'y glisser)
        a = rng.uniform(0, 2 * math.pi)
        ox, oz = int(math.floor(cx + math.cos(a) * R)), int(math.floor(cz + math.sin(a) * R))
        m.boite(ox, y0, oz, ox, y0 + 1, oz, m.AIR)
        ty = y0 - 1 + h
        for i in range(int(rng.integers(3, 5))):
            a = rng.uniform(0, 2 * math.pi); L = rng.uniform(5, 9)
            fin = (cx + math.cos(a) * L, ty + rng.uniform(2, 5), cz + math.sin(a) * L)
            self.branche((cx, ty - 2, cz), fin)
            self.grappe(fin[0], fin[1] + 1, fin[2], rng.uniform(3.5, 5), 1.9, F_SOMBRE if rng.random() < 0.4 else F_JUNGLE)
        self.grappe(cx, ty + 2, cz, 5, 2.2)
        self.vignes_sous(cx, ty + 2, cz, 9, 14, 10)

    def palmier(self, x, z, penche=None):
        """Stipe de 1 bloc qui s'incline puis se redresse ; 7-9 palmes qui retombent."""
        rng, m = self.rng, self.m
        y0 = int(self.sol[z, x])
        h = int(rng.integers(9, 16))
        a = rng.uniform(0, 2 * math.pi) if penche is None else penche
        inc = rng.uniform(2.5, 5)
        stipe = tronc('jungle')
        pts = []
        for k in range(h + 1):
            t = k / h
            d = inc * math.sin(t * math.pi * 0.5) ** 1.3
            pts.append((x + 0.5 + math.cos(a) * d, y0 + k, z + 0.5 + math.sin(a) * d))
        for p, q in zip(pts, pts[1:]):
            m.ligne(p, q, lambda axe: stipe('y'))
        tx, ty, tz = pts[-1]
        m.ellipsoide(tx, ty + 0.5, tz, 1.2, 0.8, 1.2, self.P(F_JUNGLE))
        n = int(rng.integers(7, 10))
        for i in range(n):
            b = i * 2 * math.pi / n + rng.uniform(-0.2, 0.2)
            L = rng.uniform(6, 8.5)
            # palme = polyligne continue (reliee par les faces), doublee pres du coeur
            for lat in (-0.6, 0.0, 0.6):
                pts_f = []
                for s in np.linspace(0.5, L * (1.0 if lat == 0 else 0.6), 8):
                    t = s / L
                    yy = ty + 1 + 1.6 * t - 4.2 * t * t
                    pts_f.append((tx + math.cos(b) * s - math.sin(b) * lat, yy + 0.5, tz + math.sin(b) * s + math.cos(b) * lat))
                for p_, q_ in zip(pts_f, pts_f[1:]):
                    for (cx_, cy_, cz_) in m.cellules(p_, q_):
                        m.pose(cx_, cy_, cz_, self.P(F_JUNGLE), seulement_air=True)
        # noix de coco
        for face, (dx, dz) in list(DIRS.items())[:int(rng.integers(0, 4))]:
            m.pose(int(math.floor(tx)) - dx, int(ty) - 1, int(math.floor(tz)) - dz, 'minecraft:cocoa[age=2,facing=%s]' % face,
                   seulement_air=True)

    def paletuvier(self, x, z, eau):
        """Paletuvier : racines-echasses arquees depuis ~3 blocs au-dessus de l'eau jusqu'a la vase."""
        rng, m = self.rng, self.m
        yfond = int(self.sol[z, x])
        yb = max(yfond, eau) + int(rng.integers(3, 6))
        h = int(rng.integers(7, 12))
        cx, cz = x + 0.5, z + 0.5
        self.fut(cx, cz, yb, h, 0.75, 0.6, bois='mangrove', derive=1.0, phase=rng.uniform(0, 6))
        for i in range(int(rng.integers(6, 10))):
            a = rng.uniform(0, 2 * math.pi); R = rng.uniform(3, 5.5)
            arc = []
            for s in np.linspace(0, 1, 10):
                px = cx + math.cos(a) * R * s
                pz = cz + math.sin(a) * R * s
                py = yb + 1 - (yb + 1 - (yfond - 1)) * s ** 2.2 + 1.5 * math.sin(s * math.pi)
                arc.append((px, py + 0.5, pz))
            # racine d'un seul tenant, du tronc jusque dans la vase
            for p_, q_ in zip(arc, arc[1:]):
                for (qx, qy, qz) in m.cellules(p_, q_):
                    if qy < yfond - 1:
                        continue
                    m.pose(qx, qy, qz, 'minecraft:mangrove_roots[waterlogged=%s]' % ('true' if qy <= eau else 'false'))
        ty = yb + h
        self.grappe(cx, ty, cz, rng.uniform(3.5, 5), 2.0, F_MANGROVE)
        for _ in range(2):
            a = rng.uniform(0, 2 * math.pi); L = rng.uniform(3, 5)
            fin = (cx + math.cos(a) * L, ty - rng.uniform(0, 2), cz + math.sin(a) * L)
            self.branche((cx, ty - 3, cz), fin, bois='mangrove')
            self.grappe(fin[0], fin[1] + 0.5, fin[2], rng.uniform(2.5, 3.5), 1.6, F_MANGROVE)
        for _ in range(int(rng.integers(2, 6))):
            a = rng.uniform(0, 2 * math.pi); d = rng.uniform(1, 3.5)
            px, pz = int(cx + math.cos(a) * d), int(cz + math.sin(a) * d)
            for yy in range(ty, ty - 5, -1):
                if m.get(px, yy, pz) != m.AIR and m.get(px, yy - 1, pz) == m.AIR:
                    m.pose(px, yy - 1, pz, 'minecraft:mangrove_propagule[age=4,hanging=true,stage=0,waterlogged=false]')
                    break

    def jeune(self, x, z):
        """Jeune arbre du sous-bois : fin, 7-11 blocs, une grappe haute (on passe dessous)."""
        rng, m = self.rng, self.m
        y0 = int(self.sol[z, x])
        h = int(rng.integers(8, 12))
        bois, f = (('jungle', F_JUNGLE), ('jungle', F_JUNGLE), ('oak', F_CHENE), ('dark_oak', F_SOMBRE))[rng.integers(0, 4)]
        centres = self.fut(x + 0.5, z + 0.5, y0, h, 0.6, 0.6, bois=bois, derive=1.2, phase=rng.uniform(0, 6))
        tx, tz, _ = centres[-1]
        self.grappe(tx, y0 + h, tz, rng.uniform(2.2, 3.2), 1.4, f)

    def buisson(self, x, z, feuille=None):
        rng, m = self.rng, self.m
        y0 = int(self.sol[z, x])
        feuille = feuille or (F_JUNGLE, F_JUNGLE, F_CHENE, F_AZALEE)[rng.integers(0, 4)]
        m.pose(x, y0, z, tronc('jungle')('y'))
        m.ellipsoide(x + 0.5, y0 + 0.7, z + 0.5, rng.uniform(1.5, 2.6), rng.uniform(1.1, 1.8), rng.uniform(1.5, 2.6),
                     self.P(feuille), bruit=0.5, rng=rng, bas=y0)

    def souche(self, x, z):
        """Tronc couche, moussu, avec champignons : un obstacle bas qu'on enjambe."""
        rng, m = self.rng, self.m
        y0 = int(self.sol[z, x])
        a = rng.uniform(0, 2 * math.pi); L = rng.uniform(7, 15)
        fin = (x + 0.5 + math.cos(a) * L, y0 + 0.5, z + 0.5 + math.sin(a) * L)
        axe = 'x' if abs(math.cos(a)) > abs(math.sin(a)) else 'z'
        etat = 'minecraft:jungle_log[axis=%s]' % axe
        for (px, _, pz) in m.cellules((x + 0.5, 0, z + 0.5), (fin[0], 0, fin[2])):
            if not (0 <= px < m.W and 0 <= pz < m.L):
                continue
            yy = int(self.sol[pz, px])
            m.pose(px, yy, pz, etat)
            u = rng.random()
            dessus = ('minecraft:moss_carpet' if u < 0.6 else 'minecraft:brown_mushroom' if u < 0.66
                      else 'minecraft:red_mushroom' if u < 0.7 else None)
            if dessus:
                m.pose(px, yy + 1, pz, dessus, seulement_air=True)
        # la galette de racines arrachees, dressee a la base
        m.ellipsoide(x + 0.5 - math.cos(a), y0 + 1.5, z + 0.5 - math.sin(a), 1.2, 2.2, 1.2, 'minecraft:rooted_dirt',
                     bruit=0.6, rng=rng)

    def bambous(self, x, z, r):
        rng, m = self.rng, self.m
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if dx * dx + dz * dz > r * r or rng.random() > 0.45:
                    continue
                px, pz = x + dx, z + dz
                if not (0 <= px < m.W and 0 <= pz < m.L):
                    continue
                y0 = int(self.sol[pz, px])
                dessous = m.nom(m.get(px, y0 - 1, pz))
                if m.get(px, y0, pz) != m.AIR or not any(k in dessous for k in ('grass_block', 'dirt', 'podzol', 'moss', 'mud', 'sand')):
                    continue
                h = int(rng.integers(6, 15))
                for k in range(h):
                    if m.get(px, y0 + k, pz) != m.AIR:
                        break                   # une branche au-dessus : la tige s'arrete (pas de bambou en l'air)
                    f = 'large' if k >= h - 2 else 'small' if k == h - 3 else 'none'
                    m.pose(px, y0 + k, pz, 'minecraft:bamboo[age=1,leaves=%s,stage=0]' % f)
