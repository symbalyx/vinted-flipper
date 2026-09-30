"""Le grand lagon du mosasaure, au sud de l'ile, entre la riviere et la base.

Un lagon tropical qu'on croit paisible : plages de sable blanc, eau turquoise (biome ocean
chaud), une ceinture de haut-fond ou l'on a pied... puis le tombant. En dessous, une cuvette de
40 blocs de fond pour qu'une grande bete marine y tourne a l'aise, et au milieu une fosse qui
descend dans le sous-sol profond jusqu'a y = -30 du monde : c'est la que gît l'epave.

Deux temps :
- creuser() juste apres le remplissage du terrain : la cuvette, le haut-fond, les plages, le
  chenal vers l'ocean ; la carte des hauteurs est mise a jour (lieux, pistes et foret s'y
  adaptent : palmiers et jungle tout autour) ;
- approfondir() une fois le sous-sol profond cree : la fosse, le scellement de toute cavite
  voisine (sinon l'eau fuirait dans les grottes), l'epave, les rochers geants, les forets de
  grandes algues.
"""
import math

import numpy as np

AIR = 'minecraft:air'
EAU = 'minecraft:water[level=0]'
SABLE_BLANC = 'biomesoplenty:white_sand'
DECALAGE = 15
Y0_PROFOND = -64


class Lagon:
    def __init__(self, m, r, rng, centre=(150, 190), rx=64, rz=52):
        self.m, self.r, self.rng = m, r, rng
        self.cx, self.cz = centre
        self.rx, self.rz = rx, rz
        self.fond_monde = -20                                # y du monde du fond : ~83 blocs d'eau
        self.epave_xz = (self.cx + 6, self.cz + 4)
        self.masque = np.zeros(r.h.shape, bool)
        self.rive_nord = None

    # ------------------------------------------------------------------ forme
    def _dn(self):
        r = self.r
        a = np.arctan2(r.zz - self.cz, r.xx - self.cx)
        bord = 1 + 0.10 * np.sin(3 * a + 0.7) + 0.06 * np.sin(5 * a + 2.1) + 0.04 * np.sin(9 * a)
        return np.hypot((r.xx - self.cx) / self.rx, (r.zz - self.cz) / self.rz) / bord

    def creuser(self):
        m, r, rng = self.m, self.r, self.rng
        SEA = r.SEA
        P = m.P
        dn = self._dn()
        n1 = r.n.fbm(10, 2, 701)
        n2 = r.n.fbm(24, 2, 702)
        dedans = dn < 1.0
        # fond : une bande de sable blanc au bord (dn 0,9 a 1 : 1 a 4 blocs, pour pouvoir sortir de
        # l'eau), puis la paroi ; partout ailleurs le fond descend a y = 1 du schematic (y 16 du
        # monde), et approfondir() le poursuit dans le sous-sol profond jusqu'a y = -20
        fond = np.full(r.h.shape, 999.0)
        bord = (dn >= 0.90) & dedans
        fond[bord] = SEA - 1 - (1 - (dn[bord] - 0.90) / 0.10) * 3
        fond[dn < 0.90] = 1
        # chenal vers l'ocean : vers la cote la plus proche (hors rivieres et lacs), 12 de large
        meilleur = None
        for k in range(36):
            a = k * math.pi / 18
            for d in range(int(min(self.rx, self.rz) * 0.8), 260):
                x, z = int(self.cx + math.cos(a) * d), int(self.cz + math.sin(a) * d)
                if not (4 <= x < r.W - 4 and 4 <= z < r.L - 4) or r.riviere[z, x] or r.lac[z, x] or r.lagon[z, x]:
                    break
                if r.c[z, x] < -0.6:
                    if meilleur is None or d < meilleur[0]:
                        meilleur = (d, a)
                    break
        chenal = np.zeros(r.h.shape, bool)
        if meilleur:
            d_max, a = meilleur
            for k in range(0, d_max + 8):
                x = int(self.cx + math.cos(a) * k + 4 * math.sin(k * 0.05) * -math.sin(a))
                z = int(self.cz + math.sin(a) * k + 4 * math.sin(k * 0.05) * math.cos(a))
                chenal[max(0, z - 6):z + 7, max(0, x - 6):x + 7] |= np.hypot(r.xx[max(0, z - 6):z + 7, max(0, x - 6):x + 7] - x,
                                                                             r.zz[max(0, z - 6):z + 7, max(0, x - 6):x + 7] - z) <= 6
        self.chenal_cap = meilleur
        chenal &= ~dedans
        fond[chenal] = np.minimum(fond[chenal], np.minimum(r.h[chenal] - 1, SEA - 10))
        eau = dedans | chenal
        # plages : anneau de 12 blocs autour, ramene en pente douce au niveau de la mer
        plage = (dn >= 1.0) & (dn < 1.22) & ~chenal
        tp = (dn[plage] - 1.0) / 0.22
        cible = SEA + 1 + (r.h[plage].astype(float) - (SEA + 1)) * (tp * tp * (3 - 2 * tp))
        sol_plage = np.minimum(r.h[plage].astype(float), cible)
        # blocs
        zs, xs = np.nonzero(eau | plage)
        blanc, sable, gravier, argile = P(SABLE_BLANC), P('minecraft:sand'), P('minecraft:gravel'), P('minecraft:clay')
        roches = [P('minecraft:stone'), P('minecraft:andesite'), P('minecraft:tuff'), P('minecraft:stone')]
        E, A = P(EAU), m.AIR
        herbe = P('minecraft:grass_block[snowy=false]')
        h_nouv = r.h.astype(np.int32).copy()
        h_nouv[plage] = np.round(sol_plage).astype(np.int32)
        for z, x in zip(zs, xs):
            if eau[z, x]:
                f = int(round(fond[z, x]))
                f = max(1, min(f, SEA - 1))
                d = dn[z, x]
                if d >= 0.90 or chenal[z, x]:
                    dessus = blanc if n2[z, x] > 0.35 else sable
                else:
                    dessus = roches[int(n1[z, x] * 40) % len(roches)]            # la paroi : roche nue
                m.blocs[max(0, f - 3):f, z, x] = sable if d >= 0.9 else roches[0]
                m.blocs[f, z, x] = dessus
                m.blocs[f + 1:SEA + 1, z, x] = E
                m.blocs[SEA + 1:, z, x] = A
                r.h[z, x] = f
                r.eau[z, x] = SEA
            else:
                y = int(h_nouv[z, x])
                if y < int(r.h[z, x]):
                    m.blocs[y + 1:, z, x] = A
                sec = dn[z, x] < 1.08
                m.blocs[y - 3:y, z, x] = sable if sec else P('minecraft:dirt')
                m.blocs[y, z, x] = blanc if sec else (sable if dn[z, x] < 1.13 else herbe)
                r.h[z, x] = y
        self.masque = eau
        r.grand_lagon = dedans
        # la carte des pentes (foret, falaises)
        gz_, gx_ = np.gradient(r.h.astype(np.float32))
        r.pente = np.hypot(gx_, gz_)
        # un point de la rive nord (arrivee de la tyrolienne qui survole le lagon)
        for k in range(0, 60):
            z = int(self.cz - self.rz * 1.05 - k)
            if z > 2 and not eau[z, self.cx] and r.h[z, self.cx] >= SEA + 1:
                self.rive_nord = (self.cx, z - 8)
                break
        return int(eau.sum())

    # ------------------------------------------------------------------ le grand fond
    def approfondir(self, pr, li):
        """Tout le lagon (hors bande de bord) descend jusqu'a y = -20 du monde : cuvette a fond
        plat et parois raides, scellee, avec l'epave posee au fond, des rochers enormes, des
        aiguilles qui montent jusqu'a la surface et quelques algues le long des parois."""
        m, r, rng = self.m, self.r, self.rng
        P = m.P
        E = P(EAU)
        dn = self._dn()
        interieur = dn < 0.88
        # fond en cuvette : plat au centre, qui remonte un peu vers la paroi
        F = np.round(self.fond_monde + 10 * np.clip((dn - 0.55) / 0.33, 0, 1) ** 2).astype(np.int32)
        self.F = F
        poteau = P('minecraft:stripped_spruce_log[axis=y]')
        poteaux = interieur & (m.blocs[2] == poteau)          # pylones de tyrolienne plantes dans le lagon
        zs, xs = np.nonzero(interieur)
        vase, gravier, sable = P('minecraft:mud'), P('minecraft:gravel'), P('minecraft:sand')
        n2 = r.n.fbm(20, 2, 703)
        for z, x in zip(zs, xs):
            f = int(F[z, x])
            etat = poteau if poteaux[z, x] else E
            for yw in range(f + 1, DECALAGE + 2):
                self._poser_u(pr, yw, z, x, etat)
            fondb = vase if n2[z, x] < 0.4 else (gravier if n2[z, x] < 0.6 else sable)
            self._poser_u(pr, f, z, x, poteau if poteaux[z, x] else fondb)
            r.h[z, x] = 0                                     # le vrai fond est sous le schematic (self.F)
        scelles = self._sceller(pr)
        n_roc = self._rochers(pr)
        self._epave(pr)
        n_alg = self._algues(pr)
        scelles += self._sceller(pr)                           # l'epave et les rochers deborbent parfois
        li.ajoute('Lagon du mosasaure (fond a y = -20)', self.cx, self.cz, 0)
        li.ajoute('Epave du lagon (au fond)', self.epave_xz[0], self.epave_xz[1], 0)
        return {'scelles': scelles, 'rochers': n_roc, 'algues': n_alg}

    def _poser_u(self, pr, yw, z, x, etat_id):
        if yw >= DECALAGE:
            if yw - DECALAGE < self.m.H:
                self.m.blocs[yw - DECALAGE, z, x] = etat_id
        elif yw >= Y0_PROFOND + 5:
            pr.b[yw - Y0_PROFOND, z, x] = etat_id

    def _get_u(self, pr, yw, z, x):
        if yw >= DECALAGE:
            return int(self.m.blocs[yw - DECALAGE, z, x]) if yw - DECALAGE < self.m.H else self.m.AIR
        return int(pr.b[yw - Y0_PROFOND, z, x]) if yw >= Y0_PROFOND else -1

    def _sceller(self, pr):
        """Dans une boite autour du lagon, toute cellule d'air ou de lave sous le niveau de la mer a
        moins de 3 blocs d'une eau du lagon devient roche (sinon l'eau fuirait dans les grottes)."""
        m, r = self.m, self.r
        SEA = r.SEA
        E, A = m.P(EAU), m.AIR
        L_ = m.P('minecraft:lava[level=0]')
        zs, xs = np.nonzero(self.masque)
        z0, z1 = max(zs.min() - 6, 0), min(zs.max() + 6, m.L - 1)
        x0, x1 = max(xs.min() - 6, 0), min(xs.max() + 6, m.W - 1)
        pile = np.concatenate([pr.b[:, z0:z1 + 1, x0:x1 + 1], m.blocs[:SEA + 1, z0:z1 + 1, x0:x1 + 1]], axis=0)
        eau = pile == E
        vide = (pile == A) | (pile == L_)
        prox = eau.copy()
        for _ in range(3):
            d = prox.copy()
            d[1:] |= prox[:-1]; d[:-1] |= prox[1:]
            d[:, 1:] |= prox[:, :-1]; d[:, :-1] |= prox[:, 1:]
            d[:, :, 1:] |= prox[:, :, :-1]; d[:, :, :-1] |= prox[:, :, 1:]
            prox = d
        a_sceller = prox & vide & (self._dn()[z0:z1 + 1, x0:x1 + 1] < 1.35)[None]
        n_prof = pr.b.shape[0]
        roche_prof, roche_ile = m.P('minecraft:deepslate[axis=y]'), m.P('minecraft:stone')
        ys, zs2, xs2 = np.nonzero(a_sceller)
        for y, z, x in zip(ys, zs2, xs2):
            if y < n_prof:
                pr.b[y, z + z0, x + x0] = roche_prof
            else:
                m.blocs[y - n_prof, z + z0, x + x0] = roche_ile
        return int(len(ys))

    def _boule_u(self, pr, cx, cyw, cz, rx, ry, rz, etat, bruit=0.4):
        """Ellipsoide de roche dans l'eau du lagon, a cheval sur l'ile et le sous-sol profond."""
        m, rng = self.m, self.rng
        E = m.P(EAU)
        e = m.P(etat)
        n = 0
        for yw in range(int(cyw - ry) - 1, int(cyw + ry) + 2):
            for z in range(int(cz - rz) - 1, int(cz + rz) + 2):
                for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                    if not (1 <= x < m.W - 1 and 1 <= z < m.L - 1):
                        continue
                    d = ((x + 0.5 - cx) / rx) ** 2 + ((yw + 0.5 - cyw) / ry) ** 2 + ((z + 0.5 - cz) / rz) ** 2
                    if d > 1 or (d > 0.55 and rng.random() < bruit * (d - 0.55) / 0.45):
                        continue
                    if self._get_u(pr, yw, z, x) == E:
                        self._poser_u(pr, yw, z, x, e)
                        n += 1
        return n

    def _rochers(self, pr):
        m, r, rng = self.m, self.r, self.rng
        SEA = r.SEA
        mats = ['minecraft:stone', 'minecraft:andesite', 'minecraft:tuff', 'minecraft:mossy_cobblestone', 'minecraft:deepslate[axis=y]']
        dn = self._dn()
        ex, ez = self.epave_xz
        n = 0
        # blocs enormes poses sur le fond, loin de l'epave
        zs, xs = np.nonzero((dn < 0.8) & (np.hypot(r.xx - ex, r.zz - ez) > 26))
        faits = []
        for k in rng.permutation(len(zs)):
            x, z = int(xs[k]), int(zs[k])
            if any(math.hypot(x - a, z - b) < 18 for a, b in faits):
                continue
            f = int(self.F[z, x])
            R = rng.uniform(6, 11)
            self._boule_u(pr, x + 0.5, f + R * 0.4, z + 0.5, R, R * rng.uniform(0.6, 0.9), R * rng.uniform(0.7, 1.2),
                          mats[rng.integers(0, len(mats))])
            a = rng.uniform(0, 6.28)
            self._boule_u(pr, x + math.cos(a) * R + 0.5, f + R * 0.3, z + math.sin(a) * R + 0.5, R * 0.6, R * 0.5, R * 0.6,
                          mats[rng.integers(0, len(mats))])
            faits.append((x, z))
            n += 1
            if n >= 8:
                break
        # aiguilles rocheuses : du fond jusqu'au-dessus de la surface (80 a 90 blocs de haut)
        zs, xs = np.nonzero((dn > 0.3) & (dn < 0.7) & (np.hypot(r.xx - ex, r.zz - ez) > 30))
        self.aiguilles = []
        for k in rng.permutation(len(zs)):
            x, z = int(xs[k]), int(zs[k])
            if any(math.hypot(x - a, z - b) < 34 for a, b in self.aiguilles + faits):
                continue
            f = int(self.F[z, x])
            top = SEA + DECALAGE + int(rng.integers(4, 12))
            R0 = rng.uniform(5.5, 8)
            for yw in range(f, top + 1, 2):
                t = (yw - f) / max(top - f, 1)
                Ry = R0 * (1.25 - 0.7 * t) * (1 + 0.12 * math.sin(yw * 0.5))
                ox, oz = 1.8 * math.sin(yw * 0.09 + x), 1.8 * math.cos(yw * 0.07 + z)
                self._boule_u(pr, x + ox + 0.5, yw + 1, z + oz + 0.5, Ry, 1.4, Ry * 0.85, mats[(yw // 6 + len(self.aiguilles)) % 3], 0.25)
                if yw > SEA + DECALAGE:                        # au-dessus de l'eau : sur l'air aussi
                    m.ellipsoide(x + ox + 0.5, yw - DECALAGE + 1, z + oz + 0.5, Ry, 1.4, Ry * 0.85, mats[(yw // 6) % 3],
                                 seulement_air=True, bruit=0.25, rng=rng)
            # mousse sur le sommet
            for dz in range(-7, 8):
                for dx in range(-7, 8):
                    for y in range(top - DECALAGE + 3, SEA, -1):
                        q = m.get(x + dx, y, z + dz)
                        if q != m.AIR and q != m.P(EAU):
                            if m.get(x + dx, y + 1, z + dz) == m.AIR and rng.random() < 0.6:
                                m.pose(x + dx, y, z + dz, 'minecraft:moss_block')
                            break
            self.aiguilles.append((x, z))
            n += 1
            if len(self.aiguilles) >= 3:
                break
        return n

    def _epave(self, pr):
        """Grand caboteur rouille couche sur le fond (coque construite par Lieux.navire, via une vue
        qui ecrit dans le sous-sol profond sous y = 15)."""
        from lieux import Lieux
        fx, fz = self.epave_xz
        bas = int(self.F[fz, fx])
        vue = Empile(self.m, pr)
        li = Lieux(vue, self.r, self.rng)
        li.poi = []
        cap = self.rng.uniform(0, 6.28)
        li.navire(fx, bas - DECALAGE, fz, cap, 44, 6.0, 8.5, 'acier', gite=math.radians(28), tangage=math.radians(4),
                  dechirure=True, rupture=True)
        pr.coffre(fx, bas + 2, fz, [('minecraft:gold_ingot', 9), ('minecraft:nautilus_shell', 3), ('minecraft:heart_of_the_sea', 1),
                                    ('minecraft:compass', 1), ('minecraft:diamond', 3)])
        for k in range(8):
            a = self.rng.uniform(0, 6.28)
            d = self.rng.uniform(10, 20)
            x, z = int(fx + math.cos(a) * d), int(fz + math.sin(a) * d)
            yw = int(self.F[z, x]) + 1
            if self._get_u(pr, yw, z, x) == self.m.P(EAU):
                self._poser_u(pr, yw, z, x, self.m.P('minecraft:bone_block[axis=%s]' % ('x' if k % 2 else 'z')))

    def _algues(self, pr):
        """Quelques algues seulement, en touffes le long des parois (10 a 22 blocs de haut) : l'eau
        reste claire, on voit ce qui arrive. Herbiers sur la bande de sable du bord."""
        m, r, rng = self.m, self.r, self.rng
        SEA = r.SEA
        E = m.P(EAU)
        kelp, tige = m.P('minecraft:kelp[age=24]'), m.P('minecraft:kelp_plant')
        herbe = m.P('minecraft:seagrass')
        dn = self._dn()
        zone = r.n.fbm(14, 2, 777) > 0.6
        n = 0
        zs, xs = np.nonzero(self.masque)
        u = rng.random(len(zs))
        for (z, x, v) in zip(zs, xs, u):
            d = dn[z, x]
            if d < 0.88:
                if not (d > 0.70 and zone[z, x] and v < 0.35):
                    continue
                f = int(self.F[z, x])
                haut = f + int(rng.integers(10, 23))
                if all(self._get_u(pr, yw, z, x) == E for yw in range(f + 1, haut + 1)):
                    for yw in range(f + 1, haut):
                        self._poser_u(pr, yw, z, x, tige)
                    self._poser_u(pr, haut, z, x, kelp)
                    n += 1
            else:
                f = int(r.h[z, x])
                if 0 <= f + 1 < m.H and m.blocs[f + 1, z, x] == E and v < 0.2:
                    m.blocs[f + 1, z, x] = herbe
        return n


class Empile:
    """Vue d'un Monde prolongee sous y = 0 par le sous-sol profond (pour construire l'epave)."""

    def __init__(self, m, pr):
        self.m, self.pr = m, pr
        self.AIR = m.AIR
        self.W, self.L, self.H = m.W, m.L, m.H
        self.rng = m.rng if hasattr(m, 'rng') else np.random.default_rng(0)
        self.entites = m.entites

    def P(self, e):
        return self.m.P(e)

    def nom(self, i):
        return self.m.nom(i)

    def dedans(self, x, y, z):
        return 0 <= x < self.W and 0 <= z < self.L and -79 <= y < self.H

    def get(self, x, y, z):
        if y >= 0:
            return self.m.get(x, y, z)
        return self.pr.get(x, y + DECALAGE, z)

    def pose(self, x, y, z, etat, seulement_air=False):
        if seulement_air and self.get(x, y, z) != self.AIR:
            return
        if y >= 0:
            self.m.pose(x, y, z, etat)
        else:
            self.pr.pose(x, y + DECALAGE, z, etat)
