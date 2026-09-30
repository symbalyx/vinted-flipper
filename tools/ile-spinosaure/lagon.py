"""Le grand lagon du mosasaure, au nord-ouest de l'ile.

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
        self.fond_cuvette = 8                               # y du schematic (y 23 du monde) : 40 blocs d'eau
        self.fosse = (self.cx + 8, self.cz + 6, 22, 16)       # centre et rayons de la fosse
        self.fond_fosse = -30                                # y du monde
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
        # fond : haut-fond de sable blanc (1 a 4 blocs), tombant raide, cuvette a 40 blocs
        fond = np.full(r.h.shape, 999.0)
        haut_fond = (dn >= 0.80) & dedans
        fond[haut_fond] = SEA - 1 - (1 - (dn[haut_fond] - 0.80) / 0.20) * 3
        tombant = (dn >= 0.60) & (dn < 0.80)
        t = (0.80 - dn[tombant]) / 0.20
        fond[tombant] = SEA - 4 - (SEA - 4 - self.fond_cuvette) * np.clip(t, 0, 1) ** 0.6
        cuvette = dn < 0.60
        fond[cuvette] = self.fond_cuvette + 3 * (n1[cuvette] - 0.5) + 4 * np.clip((dn[cuvette] - 0.45) / 0.15, 0, 1)
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
                f = max(3, min(f, SEA - 1))
                d = dn[z, x]
                if d >= 0.80 or chenal[z, x]:
                    dessus = blanc if n2[z, x] > 0.35 else sable
                elif d >= 0.60:
                    dessus = roches[int(n1[z, x] * 40) % len(roches)]            # le tombant : roche nue
                else:
                    dessus = gravier if n2[z, x] > 0.62 else (argile if n2[z, x] < 0.3 else sable)
                m.blocs[f - 3:f, z, x] = sable if d >= 0.8 else roches[0]
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

    # ------------------------------------------------------------------ la fosse et l'epave
    def approfondir(self, pr, li):
        """Fosse jusqu'a y = -30 du monde, scellement, epave, rochers, algues."""
        m, r, rng = self.m, self.r, self.rng
        SEA = r.SEA
        P = m.P
        E, A = P(EAU), m.AIR
        fx, fz, ra, rb = self.fosse
        bas = self.fond_fosse                                        # monde
        haut = self.fond_cuvette + DECALAGE                          # monde
        # 1. fosse en entonnoir irregulier : eau dans l'ile (y schem >= 0) et dans le profond
        R = int(max(ra, rb)) + 6
        zz, xx = np.mgrid[fz - R:fz + R + 1, fx - R:fx + R + 1]
        a = np.arctan2(zz - fz, xx - fx)
        forme = 1 + 0.15 * np.sin(4 * a + 1.3) + 0.08 * np.sin(7 * a)
        # les poteaux (pylones de la tyrolienne) qui plongent dans la fosse sont prolonges jusqu'au fond
        poteau = P('minecraft:stripped_spruce_log[axis=y]')
        ys_ref = min(haut + 2 - DECALAGE, m.H - 1)
        poteaux = m.blocs[ys_ref, zz, xx] == poteau
        eau_fosse = []                                               # (y monde, masque 2D)
        for yw in range(bas, haut + 3):
            t = (yw - bas) / max(haut - bas, 1)
            k = (0.62 + 0.38 * t ** 0.7) / forme
            dans = ((xx - fx) / (ra * k)) ** 2 + ((zz - fz) / (rb * k)) ** 2 <= 1.0
            eau_fosse.append((yw, dans))
            self._poser(pr, yw, zz[dans & ~poteaux], xx[dans & ~poteaux], E)
            self._poser(pr, yw, zz[dans & poteaux], xx[dans & poteaux], poteau)
        # le fond de la fosse : vase et gravier
        _, dans_bas = eau_fosse[0]
        self._poser(pr, bas - 1, zz[dans_bas], xx[dans_bas], P('minecraft:mud'))
        # 2. scellement : dans une boite autour du lagon, toute cellule d'air ou de lave sous le
        # niveau de la mer a moins de 3 blocs d'une eau du lagon devient roche
        scelles = self._sceller(pr)
        # 3. rochers geants sur le fond de la cuvette et aiguilles qui percent la surface
        n_roc = self._rochers()
        # 4. l'epave, couchee au fond de la fosse
        self._epave(pr, fx, fz, bas)
        # 5. forets de grandes algues
        n_alg = self._algues(pr, eau_fosse)
        # la coque deborde des parois de la fosse : second scellement, apres l'epave
        scelles += self._sceller(pr)
        li.ajoute('Lagon du mosasaure (fosse et epave a y = -30)', self.cx, self.cz, 0)
        li.ajoute('Epave du lagon (au fond de la fosse)', fx, fz, 0)
        return {'scelles': scelles, 'rochers': n_roc, 'algues': n_alg}

    def _poser(self, pr, yw, zs, xs, etat_id):
        if yw >= DECALAGE:
            ys = yw - DECALAGE
            if ys < self.m.H:
                self.m.blocs[ys, zs, xs] = etat_id
        elif yw >= Y0_PROFOND + 5:
            pr.b[yw - Y0_PROFOND, zs, xs] = etat_id

    def _sceller(self, pr):
        m, r = self.m, self.r
        SEA = r.SEA
        E, A = m.P(EAU), m.AIR
        L_ = m.P('minecraft:lava[level=0]')
        zs, xs = np.nonzero(self.masque)
        z0, z1 = max(zs.min() - 6, 0), min(zs.max() + 6, m.L - 1)
        x0, x1 = max(xs.min() - 6, 0), min(xs.max() + 6, m.W - 1)
        # pile : profond (y monde -64..14) puis ile (15..15+SEA)
        pile = np.concatenate([pr.b[:, z0:z1 + 1, x0:x1 + 1], m.blocs[:SEA + 1, z0:z1 + 1, x0:x1 + 1]], axis=0)
        # l'eau du lagon : l'eau connectee a la surface du lagon (colonnes du lagon et du chenal)
        eau = pile == E
        vide = (pile == A) | (pile == L_)
        prox = eau.copy()
        for _ in range(3):
            d = prox.copy()
            d[1:] |= prox[:-1]; d[:-1] |= prox[1:]
            d[:, 1:] |= prox[:, :-1]; d[:, :-1] |= prox[:, 1:]
            d[:, :, 1:] |= prox[:, :, :-1]; d[:, :, :-1] |= prox[:, :, 1:]
            prox = d
        a_sceller = prox & vide
        # on ne scelle que dans le rayon du lagon (ailleurs, rien n'a change)
        dn = self._dn()[z0:z1 + 1, x0:x1 + 1]
        a_sceller &= (dn < 1.35)[None]
        n_prof = pr.b.shape[0]
        roche_prof = m.P('minecraft:deepslate[axis=y]')
        roche_ile = m.P('minecraft:stone')
        ys, zs2, xs2 = np.nonzero(a_sceller)
        for y, z, x in zip(ys, zs2, xs2):
            if y < n_prof:
                pr.b[y, z + z0, x + x0] = roche_prof
            else:
                m.blocs[y - n_prof, z + z0, x + x0] = roche_ile
        return int(len(ys))

    def _rochers(self):
        m, r, rng = self.m, self.r, self.rng
        SEA = r.SEA
        E = m.P(EAU)
        mats = ['minecraft:stone', 'minecraft:andesite', 'minecraft:tuff', 'minecraft:mossy_cobblestone', 'minecraft:deepslate[axis=y]']
        dn = self._dn()
        fx, fz, ra, rb = self.fosse
        n = 0
        # blocs enormes poses sur le fond de la cuvette, hors de la fosse
        zs, xs = np.nonzero((dn < 0.55) & (((r.xx - fx) / (ra + 6)) ** 2 + ((r.zz - fz) / (rb + 6)) ** 2 > 1))
        for k in rng.choice(len(zs), min(40, len(zs)), replace=False):
            x, z = int(xs[k]), int(zs[k])
            if n >= 11:
                break
            f = int(r.h[z, x])
            R = rng.uniform(5, 11)
            mat = mats[rng.integers(0, len(mats))]
            m.ellipsoide(x + 0.5, f + R * 0.45, z + 0.5, R, R * rng.uniform(0.6, 0.95), R * rng.uniform(0.7, 1.2), mat,
                         seulement_air=False, seulement=[E], bruit=0.45, rng=rng, bas=f - 1)
            # un second bloc cale contre le premier
            a = rng.uniform(0, 6.28)
            m.ellipsoide(x + math.cos(a) * R + 0.5, f + R * 0.3, z + math.sin(a) * R + 0.5, R * 0.6, R * 0.5, R * 0.6,
                         mats[rng.integers(0, len(mats))], seulement_air=False, seulement=[E], bruit=0.45, rng=rng, bas=f - 1)
            n += 1
        # aiguilles rocheuses qui sortent de l'eau (3), l'une percee d'une arche
        zs, xs = np.nonzero((dn > 0.25) & (dn < 0.58))
        faites = []
        for k in rng.permutation(len(zs)):
            x, z = int(xs[k]), int(zs[k])
            if any(math.hypot(x - a, z - b) < 30 for a, b in faites) or math.hypot(x - fx, z - fz) < max(ra, rb) + 8:
                continue
            f = int(r.h[z, x])
            top = SEA + int(rng.integers(5, 14))
            R0 = rng.uniform(5, 7.5)
            for y in range(f, top + 1):
                t = (y - f) / max(top - f, 1)
                Ry = R0 * (1 - 0.55 * t) * (1 + 0.12 * math.sin(y * 0.5))
                ox, oz = 1.5 * math.sin(y * 0.13 + x), 1.5 * math.cos(y * 0.11 + z)
                m.ellipsoide(x + ox + 0.5, y + 0.5, z + oz + 0.5, Ry, 0.6, Ry * 0.85, mats[(y // 4 + len(faites)) % 3],
                             seulement_air=False, seulement=[E, m.AIR], bruit=0.3, rng=rng)
            if not faites:
                # arche : on perce l'aiguille au ras de l'eau
                m.ellipsoide(x + 0.5, SEA + 1.5, z + 0.5, R0 * 1.2, 2.5, 2.2, EAU, seulement_air=False,
                             seulement=[m.P(t_) for t_ in mats], rng=rng)
                for y in range(SEA + 1, SEA + 5):
                    for dz in range(-3, 4):
                        for dx in range(-int(R0) - 2, int(R0) + 3):
                            if m.get(x + dx, y, z + dz) == E and y > SEA:
                                m.pose(x + dx, y, z + dz, AIR)
            # mousse et lianes sur le sommet
            for dz in range(-6, 7):
                for dx in range(-6, 7):
                    for y in range(top + 2, SEA, -1):
                        q = m.get(x + dx, y, z + dz)
                        if q != m.AIR and q != E:
                            if m.get(x + dx, y + 1, z + dz) == m.AIR and rng.random() < 0.6:
                                m.pose(x + dx, y, z + dz, 'minecraft:moss_block')
                            break
            faites.append((x, z))
            n += 1
            if len(faites) >= 3:
                break
        self.aiguilles = faites
        return n

    def _epave(self, pr, fx, fz, bas):
        """Grand caboteur rouille couche au fond de la fosse (coque construite par Lieux.navire,
        via une vue qui ecrit dans le sous-sol profond sous y = 15)."""
        from lieux import Lieux
        vue = Empile(self.m, pr)
        li = Lieux(vue, self.r, self.rng)
        li.poi = []
        cap = self.rng.uniform(0, 6.28)
        y_quille = bas - DECALAGE                                     # y du schematic (negatif)
        li.navire(fx, y_quille, fz, cap, 44, 6.0, 8.5, 'acier', gite=math.radians(28), tangage=math.radians(4),
                  dechirure=True, rupture=True)
        # la cale : un coffre, et des ossements (le mosasaure est deja passe)
        pr.coffre(fx, bas + 2, fz, [('minecraft:gold_ingot', 9), ('minecraft:nautilus_shell', 3), ('minecraft:heart_of_the_sea', 1),
                                    ('minecraft:compass', 1), ('minecraft:diamond', 3)])
        for k in range(8):
            a = self.rng.uniform(0, 6.28)
            d = self.rng.uniform(8, 18)
            x, z = int(fx + math.cos(a) * d), int(fz + math.sin(a) * d)
            yw = bas
            if vue.get(x, yw - DECALAGE, z) == self.m.P(EAU):
                vue.pose(x, yw - DECALAGE, z, 'minecraft:bone_block[axis=%s]' % ('x' if k % 2 else 'z'))

    def _algues(self, pr, eau_fosse):
        """Grandes algues (varech) : forets sur le fond de la cuvette, jusqu'a 2 blocs sous la
        surface (35 a 40 blocs de haut), et quelques algues geantes qui montent du fond de la fosse
        (plus de 80 blocs). Herbiers sur le haut-fond."""
        m, r, rng = self.m, self.r, self.rng
        SEA = r.SEA
        E = m.P(EAU)
        kelp, tige = m.P('minecraft:kelp[age=24]'), m.P('minecraft:kelp_plant')
        herbe, haute_b, haute_h = m.P('minecraft:seagrass'), m.P('minecraft:tall_seagrass[half=lower]'), m.P('minecraft:tall_seagrass[half=upper]')
        dn = self._dn()
        zone = r.n.fbm(18, 2, 777) > 0.52
        n = 0
        zs, xs = np.nonzero(self.masque)
        u = rng.random(len(zs))
        for (z, x, v) in zip(zs, xs, u):
            f = int(r.h[z, x])
            if m.blocs[f + 1, z, x] != E:
                continue
            prof = SEA - f
            if prof >= 6 and zone[z, x] and v < 0.22:
                haut = SEA - int(rng.integers(1, 4))
                if (m.blocs[f + 1:haut + 1, z, x] == E).all():
                    m.blocs[f + 1:haut, z, x] = tige
                    m.blocs[haut, z, x] = kelp
                    n += 1
            elif prof <= 4 and dn[z, x] >= 0.8:
                if v < 0.25:
                    m.blocs[f + 1, z, x] = herbe
                elif v < 0.33 and prof >= 2:
                    m.blocs[f + 1, z, x] = haute_b
                    m.blocs[f + 2, z, x] = haute_h
        # algues geantes de la fosse : du fond (y -30) jusque sous la surface
        yw0, dans0 = eau_fosse[0]
        zz, xx = np.nonzero(dans0)
        fx, fz, ra, rb = self.fosse
        R = int(max(ra, rb)) + 6
        for k in rng.choice(len(zz), min(28, len(zz)), replace=False):
            z, x = int(zz[k]) + fz - R, int(xx[k]) + fx - R
            ok = True
            col = []
            for yw in range(yw0, SEA + DECALAGE - 1):
                ys = yw - DECALAGE
                q = m.blocs[ys, z, x] if ys >= 0 else pr.b[yw - Y0_PROFOND, z, x]
                if q != E:
                    ok = False
                    break
                col.append(yw)
            if not ok or len(col) < 10:
                continue
            for yw in col[:-1]:
                self._poser(pr, yw, np.array([z]), np.array([x]), tige)
            self._poser(pr, col[-1], np.array([z]), np.array([x]), kelp)
            n += 1
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
