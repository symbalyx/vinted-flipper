"""Grottes de l'ile, gouffres terrestres et nids.

Des reseaux de galeries creuses a la maniere des « vers » de Minecraft, a l'echelle du
spinosaure :
  - galeries principales de 6 a 9 blocs de diametre : il y passe ;
  - boyaux lateraux de 3 blocs : les joueurs seulement (on s'y croit a l'abri) ;
  - cavernes (salles de 18 a 30 blocs), dont le fond noye forme des lacs souterrains
    (toute cavite sous SEA - 2 est pleine d'eau : surfaces planes, rien ne coule) ;
  - entrees a flanc de colline et gouffres verticaux ouverts dans la jungle.
Plafond d'au moins 5 blocs de roche partout ailleurs qu'aux entrees : les arbres restent
poses sur du plein. Rien n'est creuse sous les lieux, le campus et les pistes.

Decor : stalactites et stalagmites, lichen luisant rare, racines et lianes des cavernes,
mousse, toiles et ossements. Les nids : cuvette de vase, couronne de racines tressees, oeufs
(oeufs de renifleur, les plus gros du jeu) et restes de repas."""
import math

import numpy as np

AIR = 'minecraft:air'
EAU = 'minecraft:water[level=0]'

TERRAIN = ('stone', 'andesite', 'diorite', 'granite', 'tuff', 'deepslate', 'dirt', 'grass_block', 'podzol',
           'moss_block', 'rooted_dirt', 'coarse_dirt', 'gravel', 'sand', 'sandstone', 'clay', 'mud', 'basalt')


class Grottes:
    def __init__(self, m, r, rng, protege, sea):
        self.m, self.r, self.rng, self.SEA = m, r, rng, sea
        self.protege = protege                        # colonnes interdites (lieux, campus, pistes, eaux)
        self.creuse = np.zeros(m.blocs.shape, bool)   # [y, z, x] : cellules creusees
        self.nids = []
        self.salles = []
        self.entrees = []
        self._lut = None

    # ------------------------------------------------------------------ creusement
    def _creusable(self):
        m = self.m
        lut = np.zeros(len(m.palette) + 1, bool)
        for nom, i in m.palette.items():
            base = nom.split('[')[0].replace('minecraft:', '')
            lut[i] = base in TERRAIN
        return lut

    def boule(self, cx, cy, cz, rh, rv, plafond=5, forcer=False):
        """Creuse un ellipsoide. Hors entree (forcer), on garde `plafond` blocs de roche sous la
        surface et on ne touche ni aux colonnes protegees ni a ce qui n'est pas du terrain."""
        m, r = self.m, self.r
        x0, x1 = int(math.floor(cx - rh)), int(math.ceil(cx + rh))
        z0, z1 = int(math.floor(cz - rh)), int(math.ceil(cz + rh))
        y0, y1 = int(math.floor(cy - rv)), int(math.ceil(cy + rv))
        x0, z0, y0 = max(x0, 1), max(z0, 1), max(y0, 2)
        x1, z1, y1 = min(x1, m.W - 2), min(z1, m.L - 2), min(y1, m.H - 2)
        if x0 > x1 or z0 > z1 or y0 > y1:
            return
        ys, zs, xs = np.ogrid[y0:y1 + 1, z0:z1 + 1, x0:x1 + 1]
        d = ((xs + 0.5 - cx) / rh) ** 2 + ((zs + 0.5 - cz) / rh) ** 2 + ((ys + 0.5 - cy) / rv) ** 2
        sel = d <= 1.0
        hcol = r.h[z0:z1 + 1, x0:x1 + 1].astype(np.int32)[None, :, :]
        if not forcer:
            sel &= ys <= hcol - plafond
            sel &= ~self.protege[z0:z1 + 1, x0:x1 + 1][None, :, :]
        blocs = m.blocs[y0:y1 + 1, z0:z1 + 1, x0:x1 + 1]
        sel &= self._lut[np.minimum(blocs, len(self._lut) - 1)]
        blocs[sel] = m.AIR
        self.creuse[y0:y1 + 1, z0:z1 + 1, x0:x1 + 1] |= sel

    def ver(self, x, y, z, cap, n, rh, pente=0.0, branches=True, profondeur=0, plancher=None):
        """Galerie sinueuse : n pas de ~1,6 bloc, cap et pente derivant doucement. Elle reste
        au-dessus de `plancher` (par defaut SEA + 2 : grottes seches ; plus bas, elle se noie)."""
        rng, r = self.rng, self.r
        plancher = self.SEA + 2 if plancher is None else plancher
        for i in range(n):
            rv = rh * 0.8 + 0.4
            self.boule(x, y, z, rh, rv)
            cap += rng.normal(0, 0.18)
            pente = float(np.clip(pente + rng.normal(0, 0.06), -0.45, 0.45))
            x += math.cos(cap) * 1.6
            z += math.sin(cap) * 1.6
            y += pente * 1.6
            if not (12 <= x < r.W - 12 and 12 <= z < r.L - 12):
                return
            sol = int(r.h[int(z), int(x)])
            # rester sous la surface (plafond), au-dessus du fond du monde
            if y > sol - rh - 7:
                pente = -abs(pente) - 0.1
                y = min(y, sol - rh - 6)
            if y < plancher:
                pente = abs(pente) + 0.08
                y = max(y, plancher - 1)
            rh = float(np.clip(rh + rng.normal(0, 0.08), 1.3, 5.0))
            if profondeur == 0 and rng.random() < 0.02:
                self.salle(x, y, z)
            if branches and profondeur < 2 and rng.random() < 0.02:
                large = profondeur == 0 and rng.random() < 0.35
                # un embranchement sur cinq plonge sous la nappe : lac souterrain
                plonge = rng.random() < 0.2
                self.ver(x, y, z, cap + rng.choice([-1, 1]) * rng.uniform(0.8, 1.6), int(rng.integers(30, 90)),
                         3.2 if large else 1.5, -0.3 if plonge else rng.uniform(-0.2, 0.2), True, profondeur + 1,
                         self.SEA - 8 if plonge else plancher)

    def salle(self, x, y, z):
        rng = self.rng
        rx, ry = rng.uniform(10, 16), rng.uniform(5, 8)
        # plusieurs boules qui se chevauchent : une salle irreguliere, pas une bulle
        for _ in range(5):
            self.boule(x + rng.normal(0, rx / 3), y + rng.normal(0, 1), z + rng.normal(0, rx / 3),
                       rx * rng.uniform(0.55, 0.85), ry * rng.uniform(0.7, 1.0))
        self.salles.append((int(x), int(y), int(z), rx))

    def entree(self, x, z, cap):
        """Descente en pente depuis la surface (flanc de colline) jusqu'a la profondeur."""
        r = self.r
        y = float(r.h[int(z), int(x)]) + 1
        self.entrees.append((int(x), int(z)))
        for i in range(24):
            self.boule(x, y, z, 3.6, 3.2, forcer=i < 10)
            x += math.cos(cap) * 1.5
            z += math.sin(cap) * 1.5
            y = max(y - 0.6, self.SEA + 4)
        return x, y, z

    def gouffre(self, x, z, R):
        """Puits vertical ouvert dans la jungle, jusqu'a une salle."""
        r = self.r
        sol = int(r.h[int(z), int(x)])
        bas = max(self.SEA + 3, sol - 32)
        for y in range(sol + 2, bas, -1):
            k = (sol - y) / max(sol - bas, 1)
            self.boule(x + math.sin(y * 0.3) * 1.2, y, z + math.cos(y * 0.23) * 1.2, R * (1 - 0.25 * k), 1.2, forcer=True)
        self.salle(x, bas + 3, z)
        self.entrees.append((int(x), int(z)))
        return bas

    # ------------------------------------------------------------------ l'ensemble
    def creuser(self, n_reseaux=14):
        self._lut = self._creusable()
        r, rng = self.r, self.rng
        pente = r.pente
        # sous les collines : il faut de la roche au-dessus d'une galerie seche
        ok = (~self.protege) & (r.h >= self.SEA + 18) & (r.eau <= r.h) & (pente > 0.8) & (pente < 3.0)
        zs, xs = np.nonzero(ok[16:-16, 16:-16])
        zs, xs = zs + 16, xs + 16
        choisies = []
        for k in rng.permutation(len(zs)):
            x, z = int(xs[k]), int(zs[k])
            if any(math.hypot(x - a, z - b) < 80 for a, b in choisies):
                continue
            choisies.append((x, z))
            if len(choisies) >= n_reseaux:
                break
        for (x, z) in choisies:
            # entrer face a la pente (vers le haut du terrain) : la galerie s'enfonce dans la colline
            gz, gx = np.gradient(r.h[z - 3:z + 4, x - 3:x + 4].astype(float))
            cap = math.atan2(gz[3, 3], gx[3, 3]) if (gx[3, 3] or gz[3, 3]) else rng.uniform(0, 6.28)
            ex, ey, ez = self.entree(x, z, cap)
            self.ver(ex, ey, ez, cap, int(rng.integers(240, 440)), rng.uniform(3.4, 4.4), -0.15)
        # deux gouffres dans la jungle, loin des entrees
        plats = (~self.protege) & (r.h >= self.SEA + 20) & (pente < 0.8) & (r.eau <= r.h)
        zs, xs = np.nonzero(plats[40:-40, 40:-40])
        zs, xs = zs + 40, xs + 40
        n = 0
        for k in rng.permutation(len(zs)):
            x, z = int(xs[k]), int(zs[k])
            if self.protege[z - 12:z + 13, x - 12:x + 13].any():
                continue
            if any(math.hypot(x - a, z - b) < 120 for a, b in choisies + self.entrees):
                continue
            bas = self.gouffre(x, z, float(rng.uniform(5, 7)))
            self.ver(x, bas + 3, z, rng.uniform(0, 6.28), int(rng.integers(80, 160)), 3.4, 0.0)
            n += 1
            if n >= 2:
                break
        self.noyer()

    def noyer(self):
        """Toute cavite creusee sous SEA - 2 devient eau : lacs souterrains a surface plane."""
        m = self.m
        niveau = self.SEA - 2
        c = self.creuse[:niveau + 1]
        m.blocs[:niveau + 1][c] = m.P(EAU)

    # ------------------------------------------------------------------ decor
    def decorer(self):
        m, rng = self.m, self.rng
        P = m.P
        A = m.AIR
        c = self.creuse & (m.blocs == A)
        # sols : cellule creusee d'air avec du plein dessous ; plafonds : du plein au-dessus
        plein = (m.blocs != A) & (m.blocs != P(EAU))
        sol = np.zeros_like(c)
        sol[1:] = c[1:] & plein[:-1]
        plafond = np.zeros_like(c)
        plafond[:-1] = c[:-1] & plein[1:]
        u = rng.random(c.shape, dtype=np.float32)
        ys, zs, xs = np.nonzero(sol)
        v = u[ys, zs, xs]
        # le sol lui-meme : mousse, gravier, terre grossiere par taches
        dessous = np.stack([ys - 1, zs, xs])
        tache = (np.sin(xs * 0.11) + np.cos(zs * 0.13) + np.sin(ys * 0.2)) > 0.9
        m.blocs[ys[tache] - 1, zs[tache], xs[tache]] = P('minecraft:moss_block')
        grav = (~tache) & (v > 0.93)
        m.blocs[ys[grav] - 1, zs[grav], xs[grav]] = P('minecraft:coarse_dirt')
        stal = v < 0.035
        m.blocs[ys[stal], zs[stal], xs[stal]] = P('minecraft:pointed_dripstone[thickness=tip,vertical_direction=up,waterlogged=false]')
        tapis = tache & (v > 0.6) & (v < 0.75)
        m.blocs[ys[tapis], zs[tapis], xs[tapis]] = P('minecraft:moss_carpet')
        os_ = (v > 0.9965)
        m.blocs[ys[os_], zs[os_], xs[os_]] = P('minecraft:bone_block[axis=y]')
        ys, zs, xs = np.nonzero(plafond)
        v = u[ys, zs, xs]
        stal = v < 0.05
        m.blocs[ys[stal], zs[stal], xs[stal]] = P('minecraft:pointed_dripstone[thickness=tip,vertical_direction=down,waterlogged=false]')
        racines = (v > 0.05) & (v < 0.075)
        m.blocs[ys[racines], zs[racines], xs[racines]] = P('minecraft:hanging_roots[waterlogged=false]')
        lianes = (v > 0.075) & (v < 0.09)
        for y, z, x in zip(ys[lianes], zs[lianes], xs[lianes]):
            n = int(rng.integers(1, 5))
            for k in range(n):
                if y - k < 2 or m.blocs[y - k, z, x] != A:
                    break
                fin = k == n - 1 or m.blocs[y - k - 1, z, x] != A
                baies = 'true' if rng.random() < 0.08 else 'false'      # un peu de lumiere, rare
                m.blocs[y - k, z, x] = P('minecraft:cave_vines[age=25,berries=%s]' % baies if fin
                                         else 'minecraft:cave_vines_plant[berries=%s]' % baies)
                if fin:
                    break
        fleur = v > 0.9992
        m.blocs[ys[fleur], zs[fleur], xs[fleur]] = P('minecraft:spore_blossom')
        # lichen luisant, rare, sur les parois (face nord ou sud d'un mur)
        for dz, face in ((-1, 'north'), (1, 'south')):
            mur = np.zeros_like(c)
            if dz < 0:
                mur[:, 1:] = c[:, 1:] & plein[:, :-1]
            else:
                mur[:, :-1] = c[:, :-1] & plein[:, 1:]
            mur &= (u > 0.992) & (m.blocs == A)
            etat = 'minecraft:glow_lichen[down=false,east=false,north=%s,south=%s,up=false,waterlogged=false,west=false]' % (
                'true' if face == 'north' else 'false', 'true' if face == 'south' else 'false')
            m.blocs[mur] = P(etat)
        # toiles dans les boyaux etroits (cellule d'air entouree de plein en x ou en z)
        etroit = c & (m.blocs == A)
        etroit[:, :, 1:-1] &= plein[:, :, :-2] & plein[:, :, 2:]
        etroit &= u > 0.985
        m.blocs[etroit] = P('minecraft:cobweb')

    # ------------------------------------------------------------------ nids
    def nid(self, x, y, z, nom):
        """Cuvette de vase de 7 blocs, couronne de racines tressees, 3 a 5 oeufs, restes."""
        m, rng = self.m, self.rng
        P = m.P
        for dz in range(-4, 5):
            for dx in range(-4, 5):
                d = math.hypot(dx, dz)
                px, pz = x + dx, z + dz
                if d > 4.3:
                    continue
                if d <= 2.6:
                    m.pose(px, y - 1, pz, 'minecraft:mud' if rng.random() < 0.7 else 'minecraft:packed_mud')
                    m.pose(px, y, pz, AIR)
                elif m.get(px, y, pz) == m.AIR and m.get(px, y - 1, pz) != m.AIR:
                    m.pose(px, y, pz, 'minecraft:mangrove_roots[waterlogged=false]' if rng.random() < 0.8
                           else 'minecraft:dead_bush' if m.nom(m.get(px, y - 1, pz)).endswith(('dirt', 'mud', 'sand')) else AIR)
        oeufs = [(0, 0), (1, 0), (0, 1), (-1, 1), (1, -1)][:int(rng.integers(3, 6))]
        for (dx, dz) in oeufs:
            m.pose(x + dx, y, z + dz, 'minecraft:sniffer_egg[hatch=%d]' % rng.integers(0, 2))
        m.pose(x - 1, y, z - 1, 'minecraft:turtle_egg[eggs=3,hatch=2]')
        for _ in range(3):
            a = rng.uniform(0, 6.28)
            px, pz = x + int(round(math.cos(a) * 6)), z + int(round(math.sin(a) * 6))
            if m.get(px, y, pz) == m.AIR and m.get(px, y - 1, pz) != m.AIR:
                m.pose(px, y, pz, 'minecraft:bone_block[axis=%s]' % ('x' if rng.random() < 0.5 else 'z'))
        m.pose(x + 3, y, z - 2, 'minecraft:skeleton_skull[rotation=%d]' % rng.integers(0, 16), seulement_air=True)
        self.nids.append((nom, int(x), int(y), int(z)))

    def nids_dans_les_salles(self, n=3):
        """Nids dans les salles seches : le point de sol le plus degage (7 x 7 d'air sur du
        plein, au-dessus de l'eau), dans la boite de chaque salle, les plus grandes d'abord."""
        m = self.m
        A = m.AIR
        faits = 0
        for (x, y, z, rx) in sorted(self.salles, key=lambda s_: -s_[3]):
            if any(math.hypot(x - a, z - c) < 60 for (_, a, _, c) in self.nids):
                continue                                 # un nid par secteur de grottes
            R = int(rx)
            y0, y1 = max(self.SEA + 1, y - 8), min(m.H - 3, y + 4)
            if y1 <= y0:
                continue
            bloc = m.blocs[y0 - 1:y1 + 2, z - R:z + R + 1, x - R:x + R + 1]
            air = bloc == A
            sol = air[1:-1] & ~air[:-2] & (bloc[:-2] != m.P(EAU)) & air[2:]
            sol &= self.creuse[y0:y1 + 1, z - R:z + R + 1, x - R:x + R + 1]     # dans la grotte, pas dehors
            meilleur = None
            for k in range(sol.shape[0]):
                zs, xs = np.nonzero(sol[k])
                for zz, xx in zip(zs, xs):
                    if 3 <= zz < sol.shape[1] - 3 and 3 <= xx < sol.shape[2] - 3 and sol[k, zz - 3:zz + 4, xx - 3:xx + 4].sum() >= 36:
                        meilleur = (x - R + xx, y0 + k, z - R + zz)
                        break
                if meilleur:
                    break
            if not meilleur:
                continue
            self.nid(*meilleur, 'Nid (grotte)')
            faits += 1
            if faits >= n:
                break
        return faits
