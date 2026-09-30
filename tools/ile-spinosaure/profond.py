"""Le sous-sol profond, sous l'ile (y du monde de -64 a 14), comme dans un monde 1.20 classique.

Le schematic ne couvre que y = 15 a 174. Pour un vrai monde, on ajoute dessous 79 couches :
- socle (bedrock) irregulier en bas, ardoise des abimes (deepslate) sous y = 0, transition
  melangee de 0 a 8, pierre au-dessus ; poches de tuf, de granite, de diorite, d'andesite ;
- cavernes au bruit 3D, plus vastes qu'en surface : « fromage » (grandes salles a piliers),
  « spaghetti » (longues galeries sinueuses), « nouilles » (boyaux etroits) ;
- lacs de lave sous y = -55 (comme en vanilla), qui eclairent le fond ;
- minerais d'ardoise (diamant, redstone, or, lapis) et de pierre (fer, cuivre, charbon) ;
- deux geodes d'amethyste ; une region de gouttes (dripstone) ; une region de sculk
  (biome deep dark) ;
- une mine abandonnee profonde, plus grande que celle de la crete : salle de terre centrale,
  couloirs sur quatre generations, toiles, oeufs d'araignee, generateurs d'araignees
  venimeuses, coffres.

Les liaisons avec l'ile (descentes, ravins, puits de mine a echelles) sont dans liaisons()."""
import math

import numpy as np

from grottes import Bruit3D, voisins4

Y0 = -64                  # y du monde de la premiere couche
NY = 79                   # -64 .. 14
DECALAGE = 15             # y du schematic 0 = y du monde 15
AIR = 'minecraft:air'
EAU = 'minecraft:water[level=0]'
LAVE = 'minecraft:lava[level=0]'

# (minerai, blocs par million de blocs de roche, y mini, y maxi, y le plus riche, taille)
MINERAIS_PROFONDS = [
    ('diamond_ore', 420, -64, 14, -58, 5),
    ('redstone_ore', 1400, -64, 14, -58, 8),
    ('lapis_ore', 520, -64, 14, -4, 6),
    ('gold_ore', 800, -64, 14, -18, 7),
    ('iron_ore', 2600, -30, 14, 10, 9),
    ('copper_ore', 1500, -16, 14, 10, 10),
    ('coal_ore', 900, 0, 14, 12, 12),
]


class Profond:
    def __init__(self, m, r, rng):
        self.m, self.r, self.rng = m, r, rng
        self.W, self.L = m.W, m.L
        self.b = np.empty((NY, m.L, m.W), np.uint16)       # [y - Y0, z, x]
        self.creuse = np.zeros((NY, m.L, m.W), bool)
        self.sculk2d = np.zeros((m.L, m.W), bool)
        self.salles = []
        self.P = m.P

    # ------------------------------------------------------------------ acces
    def dedans(self, x, y, z):
        return 0 <= x < self.W and 0 <= z < self.L and Y0 <= y < Y0 + NY

    def get(self, x, y, z):
        return int(self.b[y - Y0, z, x]) if self.dedans(x, y, z) else self.m.AIR

    def pose(self, x, y, z, etat):
        if self.dedans(x, y, z):
            self.b[y - Y0, z, x] = self.P(etat)

    def _lut(self, noms):
        lut = np.zeros(len(self.m.palette) + 64, bool)
        for nom, i in self.m.palette.items():
            lut[i] = nom.split('[')[0].replace('minecraft:', '') in noms
        return lut

    # ------------------------------------------------------------------ roche
    def roche(self):
        P, rng = self.P, self.rng
        W, L = self.W, self.L
        socle, ardoise, pierre = P('minecraft:bedrock'), P('minecraft:deepslate[axis=y]'), P('minecraft:stone')
        tuf, granite, diorite, andesite = P('minecraft:tuff'), P('minecraft:granite'), P('minecraft:diorite'), P('minecraft:andesite')
        gravier = P('minecraft:gravel')
        bt = Bruit3D(W, NY, L, 9, 961)
        bg = Bruit3D(W, NY, L, 11, 962)
        bd = Bruit3D(W, NY, L, 12, 963)
        ba = Bruit3D(W, NY, L, 10, 964)
        bm = Bruit3D(W, NY, L, 5, 965)
        for i in range(NY):
            y = Y0 + i
            c = self.b[i]
            if i == 0:
                c[:] = socle
                continue
            if y < 0:
                c[:] = ardoise
                c[bt.couche(i) > 0.74] = tuf
            elif y < 8:
                melange = bm.couche(i) < (8 - y) / 8.0
                c[:] = np.where(melange, ardoise, pierre)
            else:
                c[:] = pierre
            if y >= 0:
                c[bg.couche(i) > 0.76] = granite
                c[bd.couche(i) > 0.77] = diorite
                c[ba.couche(i) > 0.76] = andesite
                c[(bt.couche(i) > 0.8) & (y < 10)] = tuf
            c[(bm.couche(i) > 0.86) & (i > 10)] = gravier
            if i <= 4:
                c[rng.random((L, W)) < (5 - i) / 5.0] = socle

    # ------------------------------------------------------------------ cavernes
    def cavernes(self):
        """Grandes cavernes (« fromage » a grande echelle : des salles de 30 a 60 blocs a piliers)
        et longues galeries lisses (« spaghetti » etires) ; plus de boyaux etroits. Rien dans le
        socle ni dans les 6 couches du haut (l'ile repose sur du plein)."""
        W, L = self.W, self.L
        A = self.m.AIR
        b1, b2 = Bruit3D(W, NY, L, 26, 971), Bruit3D(W, NY, L, 26, 972)
        b3, b4 = Bruit3D(W, NY, L, 34, 973), Bruit3D(W, NY, L, 11, 974)
        socle = self.P('minecraft:bedrock')
        for i in range(5, NY - 6):
            y = Y0 + i
            seuil = 0.70 + 0.02 * max(0, (y + 10) / 20.0)
            fromage = (b3.couche(i) + 0.25 * (b4.couche(i) - 0.5)) > seuil
            spaghetti = (np.abs(b1.couche(i) - 0.5) < 0.05) & (np.abs(b2.couche(i) - 0.5) < 0.075)
            sel = (fromage | spaghetti) & (self.b[i] != socle)
            self.b[i][sel] = A
            self.creuse[i] |= sel
        return int(self.creuse.sum())

    def tunnels(self, n=3):
        """Longs tunnels (300 a 500 blocs, 6 a 9 de large) qui traversent tout le sous-sol en
        ondulant : les autoroutes du dessous, qui relient les grandes cavernes."""
        rng, W, L = self.rng, self.W, self.L
        A = self.m.AIR
        socle = self.P('minecraft:bedrock')
        faits = 0
        for k in range(n):
            a = rng.uniform(0, 2 * math.pi)
            x, z = W / 2 - math.cos(a) * W * 0.38, L / 2 - math.sin(a) * L * 0.38
            y = float(rng.uniform(-40, -12))
            cap, pente = a + rng.uniform(-0.3, 0.3), 0.0
            for pas in range(int(rng.integers(220, 340))):
                R = 3.0 + 1.2 * math.sin(pas * 0.07 + k) + rng.uniform(0, 0.5)
                Rv = R * 0.75
                x0, x1 = int(x - R) - 1, int(x + R) + 2
                z0, z1 = int(z - R) - 1, int(z + R) + 2
                i0, i1 = max(5, int(y - Rv - Y0) - 1), min(NY - 7, int(y + Rv - Y0) + 2)
                if not (2 <= x0 and x1 < W - 2 and 2 <= z0 and z1 < L - 2):
                    break
                ii, zz, xx = np.ogrid[i0:i1, z0:z1, x0:x1]
                sel = (((xx + 0.5 - x) / R) ** 2 + ((zz + 0.5 - z) / R) ** 2 + ((ii + Y0 + 0.5 - y) / Rv) ** 2) <= 1
                bloc = self.b[i0:i1, z0:z1, x0:x1]
                sel &= bloc != socle
                bloc[sel] = A
                self.creuse[i0:i1, z0:z1, x0:x1] |= sel
                cap += rng.normal(0, 0.06)
                pente = float(np.clip(pente + rng.normal(0, 0.03), -0.2, 0.2))
                x += math.cos(cap) * 1.5
                z += math.sin(cap) * 1.5
                y = float(np.clip(y + pente * 1.5, -48, -4))
            faits += 1
        return faits

    def lave(self):
        """Quelques mares de lave seulement, au plus bas (y -59 et -58) et par endroits ; leur bord
        est borde de tuf pour que rien ne coule."""
        P = self.P
        L_ = P(LAVE)
        tuf = P('minecraft:tuff')
        masque = Bruit3D(self.W, NY, self.L, 40, 979).couche(6) > 0.62
        n = 0
        for i in (5, 6):
            c = self.creuse[i] & masque
            self.b[i][c] = L_
            n += int(c.sum())
            bord = voisins4(c) & self.creuse[i] & ~c
            self.b[i][bord] = tuf
            self.creuse[i] &= ~bord
        return n

    # ------------------------------------------------------------------ minerais
    def minerais(self):
        m, rng, P = self.m, self.rng, self.P
        for nom, *_ in MINERAIS_PROFONDS:
            etat = nom + ('[lit=false]' if nom == 'redstone_ore' else '')
            P('minecraft:' + etat); P('minecraft:deepslate_' + etat)
        hote_pierre = self._lut(('stone', 'granite', 'diorite', 'andesite'))
        hote_ardoise = self._lut(('deepslate', 'tuff'))
        hote = hote_pierre | hote_ardoise
        n_roche = sum(int(hote[self.b[i]].sum()) for i in range(NY))
        offs = [(dy, dz, dx) for dy in range(-2, 3) for dz in range(-2, 3) for dx in range(-2, 3)]
        offs.sort(key=lambda o: o[0] ** 2 + o[1] ** 2 + o[2] ** 2)
        poses = {}
        for nom, ppm, y0, y1, ypic, taille in MINERAIS_PROFONDS:
            etat = nom + ('[lit=false]' if nom == 'redstone_ore' else '')
            e_p, e_a = P('minecraft:' + etat), P('minecraft:deepslate_' + etat)
            cible = n_roche * ppm / 1e6
            faits = essais = 0
            while faits < cible and essais < cible * 6:
                essais += 1
                i = int(round(rng.triangular(y0, ypic, y1))) - Y0
                x, z = int(rng.integers(3, self.W - 3)), int(rng.integers(3, self.L - 3))
                if not (3 <= i < NY - 3) or not hote[self.b[i, z, x]]:
                    continue
                k = max(1, int(rng.normal(taille, taille * 0.3)))
                for (dy, dz, dx) in offs[:k * 2]:
                    q = self.b[i + dy, z + dz, x + dx]
                    if rng.random() < 0.55 and hote[q]:
                        self.b[i + dy, z + dz, x + dx] = e_a if hote_ardoise[q] else e_p
                        faits += 1
            poses[nom] = faits
        return poses

    # ------------------------------------------------------------------ geodes
    def geode(self, cx, y, cz, R):
        P, rng = self.P, self.rng
        i0 = y - Y0
        couches = [(R, None), (R + 1.0, 'amethyst'), (R + 2.0, 'minecraft:calcite'), (R + 3.0, 'minecraft:smooth_basalt')]
        Rt = int(R + 4)
        for di in range(-Rt, Rt + 1):
            for dz in range(-Rt, Rt + 1):
                for dx in range(-Rt, Rt + 1):
                    i, z, x = i0 + di, cz + dz, cx + dx
                    if not (2 <= i < NY - 6 and 0 <= z < self.L and 0 <= x < self.W):
                        continue
                    d = math.sqrt(dx * dx + dz * dz + (di * 1.15) ** 2) + 0.5 * math.sin(dx * 0.9 + dz * 1.3 + di)
                    for rayon, mat in couches:
                        if d <= rayon:
                            if mat is None:
                                self.b[i, z, x] = self.m.AIR
                                self.creuse[i, z, x] = True
                            elif mat == 'amethyst':
                                self.b[i, z, x] = P('minecraft:budding_amethyst' if rng.random() < 0.09 else 'minecraft:amethyst_block')
                            else:
                                self.b[i, z, x] = P(mat)
                            break
        # grappes d'amethyste sur les parois interieures
        A = self.m.AIR
        faces = (('up', 0, 0, -1), ('down', 0, 0, 1), ('east', -1, 0, 0), ('west', 1, 0, 0), ('south', 0, -1, 0), ('north', 0, 1, 0))
        for di in range(-int(R), int(R) + 1):
            for dz in range(-int(R), int(R) + 1):
                for dx in range(-int(R), int(R) + 1):
                    i, z, x = i0 + di, cz + dz, cx + dx
                    if not (2 <= i < NY - 6) or self.b[i, z, x] != A or rng.random() > 0.35:
                        continue
                    for face, ax, az, ai in faces:
                        # la grappe pointe vers `face` : elle est accrochee au bloc oppose
                        q = self.b[i + ai, z + az, x + ax]
                        if self.m.nom(q).startswith(('minecraft:amethyst_block', 'minecraft:budding')):
                            taille = ['small_amethyst_bud', 'medium_amethyst_bud', 'large_amethyst_bud', 'amethyst_cluster'][rng.integers(0, 4)]
                            self.b[i, z, x] = P('minecraft:%s[facing=%s,waterlogged=false]' % (taille, face))
                            break

    # ------------------------------------------------------------------ decor
    def decorer(self, centre_sculk):
        """Sols et plafonds des cavernes : gouttes (dripstone) par regions, lichen luisant rare,
        gravier et tuf, toiles ; une region de sculk autour de `centre_sculk` sous y = -25."""
        P, rng = self.P, self.rng
        A = self.m.AIR
        L_ = P(LAVE)
        reg = Bruit3D(self.W, NY, self.L, 48, 981)
        sx, sz = centre_sculk
        dsc = np.hypot(self.r.xx - sx, self.r.zz - sz)
        self.sculk2d = dsc < 95
        pd = 'minecraft:pointed_dripstone[thickness=%s,vertical_direction=%s,waterlogged=false]'
        ep = {1: ['tip'], 2: ['frustum', 'tip'], 3: ['base', 'frustum', 'tip'], 4: ['base', 'middle', 'frustum', 'tip']}
        lichen_h = P('minecraft:glow_lichen[down=false,east=false,north=false,south=false,up=true,waterlogged=false]')
        lichen_b = P('minecraft:glow_lichen[down=true,east=false,north=false,south=false,up=false,waterlogged=false]')
        sculk = P('minecraft:sculk')
        veine = P('minecraft:sculk_vein[down=true,east=false,north=false,south=false,up=false,waterlogged=false]')
        stats = {'gouttes': 0, 'lichen': 0, 'sculk': 0}
        for i in range(6, NY - 6):
            y = Y0 + i
            air = self.b[i] == A
            if not air.any():
                continue
            plein_dessous = (self.b[i - 1] != A) & (self.b[i - 1] != L_)
            plein_dessus = (self.b[i + 1] != A) & (self.b[i + 1] != L_)
            sol = air & plein_dessous
            plafond = air & plein_dessus
            u = rng.random(air.shape, dtype=np.float32)
            gouttes = reg.couche(i) > 0.72                         # des regions rares
            zone_sculk = self.sculk2d & (y < -25)
            # sculk : le sol devient sculk, veines et capteurs par-dessus
            s = sol & zone_sculk & (u < 0.8)
            self.b[i - 1][s] = sculk
            v = sol & zone_sculk & (u >= 0.8) & (u < 0.9)
            self.b[i][v] = veine
            stats['sculk'] += int(s.sum())
            # gouttes : sol en bloc de dripstone, stalagmites ; stalactites au plafond
            g = sol & gouttes & ~zone_sculk & (u < 0.5)
            self.b[i - 1][g] = P('minecraft:dripstone_block')
            zs, xs = np.nonzero(sol & gouttes & ~zone_sculk & (u > 0.985))
            for z, x in zip(zs, xs):
                n = int(rng.integers(1, 5))
                for k, t in enumerate(ep[n]):
                    if i + k >= NY - 1 or self.b[i + k, z, x] != A:
                        break
                    self.b[i + k, z, x] = P(pd % (t, 'up'))
                stats['gouttes'] += 1
            zs, xs = np.nonzero(plafond & gouttes & ~zone_sculk & (u < 0.02))
            for z, x in zip(zs, xs):
                n = int(rng.integers(1, 5))
                for k, t in enumerate(ep[n]):
                    if i - k < 2 or self.b[i - k, z, x] != A:
                        break
                    self.b[i - k, z, x] = P(pd % (t, 'down'))
                stats['gouttes'] += 1
            # ailleurs : gravier et tuf au sol, lichen luisant (rare) au plafond et au sol
            ailleurs = ~gouttes & ~zone_sculk
            gr = sol & ailleurs & (u < 0.12)
            self.b[i - 1][gr] = P('minecraft:gravel')
            lh = plafond & (u > 0.985) & (self.b[i] == A)
            self.b[i][lh] = lichen_h
            lb = sol & ailleurs & (u > 0.994) & (self.b[i] == A)
            self.b[i][lb] = lichen_b
            stats['lichen'] += int(lh.sum() + lb.sum())
            # toiles dans les boyaux etroits
            etroit = air & (self.b[i] == A)
            etroit[:, 1:-1] &= (self.b[i][:, :-2] != A) & (self.b[i][:, 2:] != A)
            etroit[:, 0] = etroit[:, -1] = False
            self.b[i][etroit & (u > 0.99)] = P('minecraft:cobweb')
        return stats

    # ------------------------------------------------------------------ mine profonde
    def mine(self, cx, cz, y, profondeur=4):
        """Mine abandonnee profonde : salle de terre au centre, couloirs 3 x 3 etayes, rails,
        toiles (et toiles pendantes), oeufs d'araignee, generateurs d'araignees venimeuses
        entoures de toiles, coffres. Ou le sol manque, un plancher de planches fait pont."""
        m, rng, P = self.m, self.rng, self.P
        A = m.AIR
        i = y - Y0
        L_ = P(LAVE)
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        stats = {'couloirs': 0, 'generateurs': 0, 'coffres': 0}
        sol_ok = lambda x, z: 4 <= x < self.W - 4 and 4 <= z < self.L - 4
        # salle de terre centrale (comme en vanilla)
        for di in range(-1, 6):
            for dz in range(-6, 7):
                for dx in range(-6, 7):
                    self.b[i + di, cz + dz, cx + dx] = P('minecraft:dirt') if di == -1 else A
                    self.creuse[i + di, cz + dz, cx + dx] = di >= 0
        loot = [('minecraft:rail', 12), ('minecraft:torch', 16), ('minecraft:bread', 4), ('minecraft:diamond', 2),
                ('minecraft:golden_apple', 1), ('minecraft:iron_ingot', 6), ('minecraft:name_tag', 1)]

        def couloir(x, z, d, n, prof):
            dx, dz = d
            lx, lz = -dz, dx
            stats['couloirs'] += 1
            for k in range(n):
                px, pz = x + dx * k, z + dz * k
                if not sol_ok(px, pz):
                    return
                for l in (-1, 0, 1):
                    qx, qz = px + lx * l, pz + lz * l
                    for h in range(3):
                        self.b[i + h, qz, qx] = A
                        self.creuse[i + h, qz, qx] = True
                    if self.b[i - 1, qz, qx] in (A, L_):
                        self.b[i - 1, qz, qx] = P('minecraft:oak_planks')
                if rng.random() < 0.8:
                    self.b[i, pz, px] = P('minecraft:rail[shape=%s,waterlogged=false]' % ('east_west' if dx else 'north_south'))
                if k % 4 == 0 and rng.random() < 0.85:
                    for l in (-1, 1):
                        qx, qz = px + lx * l, pz + lz * l
                        self.b[i, qz, qx] = self.b[i + 1, qz, qx] = P('minecraft:oak_fence')
                    for l in (-1, 0, 1):
                        self.b[i + 2, pz + lz * l, px + lx * l] = P('minecraft:oak_planks')
                u = rng.random()
                l = int(rng.choice([-1, 1]))
                qx, qz = px + lx * l, pz + lz * l
                if u < 0.14:
                    self.b[i + 2, qz, qx] = P('minecraft:cobweb')
                elif u < 0.2:
                    self.b[i + 2, qz, qx] = P('biomesoplenty:hanging_cobweb')
                elif u < 0.215 and self.b[i, qz, qx] == A:
                    self.b[i, qz, qx] = P('biomesoplenty:spider_egg')
                elif u < 0.222 and self.b[i, qz, qx] == A:
                    self.coffre(qx, y, qz, loot)
                    stats['coffres'] += 1
                elif u < 0.226 and stats['generateurs'] < 4:
                    self.generateur(px, y + 1, pz)
                    stats['generateurs'] += 1
            fx, fz = x + dx * n, z + dz * n
            if prof <= 0:
                return
            for nd in dirs:
                if nd == (-dx, -dz) or rng.random() < 0.35 or stats['couloirs'] > 170:
                    continue
                couloir(fx, fz, nd, int(rng.integers(18, 44)), prof - 1)

        for d in dirs:
            couloir(cx + d[0] * 6, cz + d[1] * 6, d, int(rng.integers(22, 40)), profondeur)
        return stats

    def coffre(self, x, y, z, objets):
        """Coffre dans le sous-sol profond : l'entite de bloc est rangee avec celles de l'ile
        (y du schematic negatif ; l'export du monde la replace, le .schem l'ignore)."""
        self.pose(x, y, z, 'minecraft:chest[facing=north,type=single,waterlogged=false]')
        import nbt
        items = [nbt.Compound({'Slot': nbt.Byte(k), 'id': nbt.String(o), 'Count': nbt.Byte(n)})
                 for k, (o, n) in enumerate(objets) if self.rng.random() < 0.7]
        self.m.entites.append((x, y - DECALAGE, z, {'Id': nbt.String('minecraft:chest'), 'Items': nbt.List('compound', items)}))

    def generateur(self, x, y, z):
        """Generateur d'araignees venimeuses au milieu du couloir, enrobe de toiles."""
        import nbt
        self.pose(x, y, z, 'minecraft:spawner')
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if self.get(x + dx, y, z + dz) == self.m.AIR:
                self.pose(x + dx, y, z + dz, 'minecraft:cobweb')
        self.m.entites.append((x, y - DECALAGE, z, {
            'Id': nbt.String('minecraft:mob_spawner'),
            'SpawnData': nbt.Compound({'entity': nbt.Compound({'id': nbt.String('minecraft:cave_spider')})}),
            'SpawnPotentials': nbt.List('compound', []),
            'Delay': nbt.Short(20), 'MinSpawnDelay': nbt.Short(200), 'MaxSpawnDelay': nbt.Short(800),
            'SpawnCount': nbt.Short(4), 'MaxNearbyEntities': nbt.Short(6), 'RequiredPlayerRange': nbt.Short(16),
            'SpawnRange': nbt.Short(4)}))


# =============================================================================================
# Liaisons entre l'ile (schematic, y >= 15) et le sous-sol profond (y < 15)
# =============================================================================================
def _creuser_u(pr, gr, x0, x1, z0, z1, yw0, yw1, masque_fn, forcer=False):
    """Creuse, dans la boite [x0,x1] x [z0,z1] x [yw0,yw1] (y du monde), les cellules ou
    masque_fn(ys_monde, zs, xs) est vrai ; partie ile par la table du terrain de Grottes
    (plafond sous la surface, colonnes dures protegees), partie profonde directement."""
    m = pr.m
    A = m.AIR
    x0, z0 = max(x0, 2), max(z0, 2)
    x1, z1 = min(x1, m.W - 3), min(z1, m.L - 3)
    if x0 > x1 or z0 > z1:
        return 0
    n = 0
    # partie profonde
    a, b = max(yw0, Y0 + 5), min(yw1, Y0 + NY - 1)
    if a <= b:
        ys, zs, xs = np.ogrid[a:b + 1, z0:z1 + 1, x0:x1 + 1]
        sel = masque_fn(ys, zs, xs)
        bloc = pr.b[a - Y0:b - Y0 + 1, z0:z1 + 1, x0:x1 + 1]
        sel = sel & (bloc != pr.P('minecraft:bedrock')) & (bloc != pr.P(LAVE))
        bloc[sel] = A
        pr.creuse[a - Y0:b - Y0 + 1, z0:z1 + 1, x0:x1 + 1] |= sel
        n += int(sel.sum())
    # partie ile
    a, b = max(yw0, DECALAGE), min(yw1, DECALAGE + m.H - 3)
    if a <= b:
        ys, zs, xs = np.ogrid[a:b + 1, z0:z1 + 1, x0:x1 + 1]
        sel = np.broadcast_to(masque_fn(ys, zs, xs), (b - a + 1, z1 - z0 + 1, x1 - x0 + 1)).copy()
        ya, yb = a - DECALAGE, b - DECALAGE
        bloc = m.blocs[ya:yb + 1, z0:z1 + 1, x0:x1 + 1]
        if not forcer:
            hcol = pr.r.h[z0:z1 + 1, x0:x1 + 1].astype(np.int32)[None]
            sel &= (np.arange(ya, yb + 1)[:, None, None] <= hcol - 5)
            sel &= ~gr.protege_dur[z0:z1 + 1, x0:x1 + 1][None]
        sel &= ~gr.reserve[ya:yb + 1, z0:z1 + 1, x0:x1 + 1]
        sel &= gr._lut[np.minimum(bloc, len(gr._lut) - 1)]
        bloc[sel] = A
        gr.creuse[ya:yb + 1, z0:z1 + 1, x0:x1 + 1] |= sel
        n += int(sel.sum())
    return n


def _eau_proche(pr, x0, x1, z0, z1, yw0, yw1, marge=2):
    """Y a-t-il de l'eau (ile) ou de la lave (profond) dans la boite elargie de `marge` ?"""
    m = pr.m
    x0, z0, x1, z1 = max(x0 - marge, 0), max(z0 - marge, 0), min(x1 + marge, m.W - 1), min(z1 + marge, m.L - 1)
    E = m.P(EAU)
    a, b = max(yw0 - marge, DECALAGE), min(yw1 + marge, DECALAGE + m.H - 1)
    if a <= b and (m.blocs[a - DECALAGE:b - DECALAGE + 1, z0:z1 + 1, x0:x1 + 1] == E).any():
        return True
    return False


def descente(pr, gr, x, yw, z, cap, yw_fin, rng):
    """Galerie en colimacon, praticable a pied (pente ~ 1 pour 2), depuis une grotte seche de
    l'ile jusqu'aux cavernes profondes. Refusee si elle frole de l'eau."""
    pts = []
    rh = 2.4
    while yw > yw_fin and len(pts) < 400:
        pts.append((x, yw, z, rh))
        cap += 0.09 + rng.normal(0, 0.05)
        x += math.cos(cap) * 1.4
        z += math.sin(cap) * 1.4
        yw -= 0.62
        rh = float(np.clip(rh + rng.normal(0, 0.1), 1.9, 3.2))
        if not (12 <= x < pr.W - 12 and 12 <= z < pr.L - 12):
            return 0
    for (px, py, pz, r_) in pts:
        if _eau_proche(pr, int(px - r_), int(px + r_), int(pz - r_), int(pz + r_), int(py - r_), int(py + r_) + 1):
            return 0
    n = 0
    for (px, py, pz, r_) in pts:
        rv = r_ * 0.85 + 0.3
        f = lambda ys, zs, xs, px=px, py=py, pz=pz, r_=r_, rv=rv: (
            ((xs + 0.5 - px) / r_) ** 2 + ((zs + 0.5 - pz) / r_) ** 2 + ((ys + 0.5 - py) / rv) ** 2) <= 1.0
        n += _creuser_u(pr, gr, int(px - r_) - 1, int(px + r_) + 1, int(pz - r_) - 1, int(pz + r_) + 1,
                        int(py - rv) - 1, int(py + rv) + 1, f)
    # une salle au bout
    fx, fy, fz, _ = pts[-1]
    for _ in range(4):
        cx, cy, cz = fx + rng.normal(0, 3), fy + rng.normal(0, 1), fz + rng.normal(0, 3)
        R, Rv = rng.uniform(5, 8), rng.uniform(3, 4.5)
        f = lambda ys, zs, xs, cx=cx, cy=cy, cz=cz, R=R, Rv=Rv: (
            ((xs + 0.5 - cx) / R) ** 2 + ((zs + 0.5 - cz) / R) ** 2 + ((ys + 0.5 - cy) / Rv) ** 2) <= 1.0
        n += _creuser_u(pr, gr, int(cx - R) - 1, int(cx + R) + 1, int(cz - R) - 1, int(cz + R) + 1, int(cy - Rv) - 1, int(cy + Rv) + 1, f)
    pr.salles.append((int(fx), int(fy), int(fz)))
    return n


def ravin(pr, gr, rng, depart, cap, longueur, fond_min):
    """Ravin a la vanilla, ouvert dans la jungle : une faille longue et etroite, plus large a
    mi-hauteur qu'en haut (profil en lentille), dont le fond descend jusqu'au sous-sol profond.
    Chaque colonne s'arrete au-dessus de toute eau voisine (grottes noyees)."""
    m, r = pr.m, pr.r
    E = m.P(EAU)
    x, z = depart
    pts = []
    for k in range(longueur):
        pts.append((x, z))
        cap += rng.normal(0, 0.05)
        x += math.cos(cap)
        z += math.sin(cap)
    # emprise : on refuse si elle touche de l'eau en surface, un lieu, une piste, le bord
    emprise = np.zeros((m.L, m.W), bool)
    larg = rng.uniform(4.5, 6.5)
    for k, (px, pz) in enumerate(pts):
        t = k / (longueur - 1)
        hw = max(1.2, larg * math.sin(math.pi * t) ** 0.6)
        R = int(hw) + 2
        ix, iz = int(px), int(pz)
        if not (20 <= ix < m.W - 20 and 20 <= iz < m.L - 20):
            return None
        emprise[iz - R:iz + R + 1, ix - R:ix + R + 1] |= np.hypot(r.xx[iz - R:iz + R + 1, ix - R:ix + R + 1] - px,
                                                                   r.zz[iz - R:iz + R + 1, ix - R:ix + R + 1] - pz) <= hw + 1
    marge = emprise.copy()
    for _ in range(4):
        marge |= voisins4(marge)
    if (marge & ((r.eau > r.h) | gr.protege)).any() or (emprise & (r.h < r.SEA + 8)).any():
        return None
    # eau dans le sous-sol de l'ile, dilatee de 2 : plus haute cellule d'eau par colonne
    zs, xs = np.nonzero(emprise)
    z0, z1, x0, x1 = zs.min() - 3, zs.max() + 3, xs.min() - 3, xs.max() + 3
    eau = (m.blocs[:, z0:z1 + 1, x0:x1 + 1] == E)
    for _ in range(2):
        d = eau.copy()
        d[:, 1:] |= eau[:, :-1]; d[:, :-1] |= eau[:, 1:]
        d[:, :, 1:] |= eau[:, :, :-1]; d[:, :, :-1] |= eau[:, :, 1:]
        d[1:] |= eau[:-1]; d[:-1] |= eau[1:]
        eau = d
    ytop_eau = np.where(eau.any(axis=0), m.H - 1 - np.argmax(eau[::-1], axis=0), -1)     # y schematic
    A = m.AIR
    LV, SOC = pr.P(LAVE), pr.P('minecraft:bedrock')
    hloc = r.h[z0:z1 + 1, x0:x1 + 1].astype(np.int32)
    n = 0
    for k, (px, pz) in enumerate(pts):
        t = k / (longueur - 1)
        hw = max(1.2, larg * math.sin(math.pi * t) ** 0.6)
        R = int(hw * 1.35) + 1
        ix, iz = int(px), int(pz)
        surf = int(r.h[iz, ix]) + DECALAGE
        fond = int(round(surf - (surf - fond_min) * math.sin(math.pi * t) ** 0.5))
        fond = min(fond, surf - 3)
        gz, gx = np.mgrid[iz - R:iz + R + 1, ix - R:ix + R + 1]
        d2 = (gx + 0.5 - px) ** 2 + (gz + 0.5 - pz) ** 2
        lz, lx = gz - z0, gx - x0
        yeau = ytop_eau[lz, lx]
        hcol = hloc[lz, lx]
        for yw in range(fond, surf + 2):
            v = (yw - fond) / max(surf - fond, 1)
            f = 0.55 + 0.8 * math.sin(math.pi * min(1.0, v * 1.15)) ** 0.8          # lentille, levre plus etroite
            f *= 1 + 0.18 * math.sin(yw * 0.7 + k * 0.3)                             # parois irregulieres
            dedans = d2 <= (hw * f) ** 2
            ys = yw - DECALAGE
            if ys >= 0:
                sel = dedans & (ys > yeau) & (ys <= hcol + 1) & ~gr.reserve[ys, gz, gx]
                sel &= m.blocs[ys, gz, gx] != A
                m.blocs[ys, gz[sel], gx[sel]] = A
                gr.creuse[ys, gz[sel], gx[sel]] = True
            elif yw >= Y0 + 5:
                i = yw - Y0
                q = pr.b[i, gz, gx]
                sel = dedans & (yeau < 0) & (q != A) & (q != LV) & (q != SOC)
                pr.b[i, gz[sel], gx[sel]] = A
                pr.creuse[i, gz[sel], gx[sel]] = True
            else:
                continue
            n += int(sel.sum())
    return emprise, pts[len(pts) // 2], n


def puits_de_mine(pr, gr, x, z, yw_haut, yw_bas):
    """Puits de 3 x 3 de la mine de la crete jusqu'a la mine profonde : echelles sur la paroi
    nord (maconnee la ou la roche manque), paliers de planches tous les 16 blocs."""
    if _eau_proche(pr, x - 2, x + 2, z - 2, z + 2, yw_bas, yw_haut, marge=2):
        return 0
    m = pr.m
    f = lambda ys, zs, xs: np.ones(np.broadcast(ys, zs, xs).shape, bool)
    n = _creuser_u(pr, gr, x - 1, x + 1, z - 1, z + 1, yw_bas, yw_haut + 2, f, forcer=True)

    def pose(xx, yw, zz, etat):
        if yw >= DECALAGE:
            m.pose(xx, yw - DECALAGE, zz, etat)
        else:
            pr.pose(xx, yw, zz, etat)

    def get(xx, yw, zz):
        return m.get(xx, yw - DECALAGE, zz) if yw >= DECALAGE else pr.get(xx, yw, zz)

    for yw in range(yw_bas, yw_haut + 1):
        if get(x, yw, z - 2) == m.AIR:
            pose(x, yw, z - 2, 'minecraft:cobblestone')
        pose(x, yw, z - 1, 'minecraft:ladder[facing=south,waterlogged=false]')
        if (yw - yw_bas) % 16 == 8:
            for dz in (0, 1):
                for dx in (-1, 0, 1):
                    pose(x + dx, yw, z + dz, 'minecraft:oak_planks')
            pose(x - 1, yw, z - 1, 'minecraft:oak_planks'); pose(x + 1, yw, z - 1, 'minecraft:oak_planks')
    return n
