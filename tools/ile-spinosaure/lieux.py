"""Les lieux disperses sur l'ile, loin les uns des autres : on traverse la jungle pour aller de
l'un a l'autre.

Chaque fonction pose ses blocs (coordonnees absolues) et renvoie (nom, x, z, rayon) : le rayon
sert a ecarter les arbres."""
import math

import numpy as np

from arbres import DIRS
from mobilier import Kit, esc, dalle, trappe, OPP
from monde import Decale

AIR = 'minecraft:air'
EAU = 'minecraft:water[level=0]'


class Lieux:
    def __init__(self, m, r, rng):
        self.m, self.r, self.rng = m, r, rng
        self.k = Kit(m, rng)
        self.poi = []

    def sol(self, x, z):
        return int(self.r.h[int(z), int(x)])

    def ajoute(self, nom, x, z, rayon):
        self.poi.append((nom, int(x), int(z), rayon))

    def cote(self, x, z, dx, dz, n=400):
        """Premier point d'eau de mer en partant de (x, z) dans la direction (dx, dz)."""
        r = self.r
        for i in range(n):
            px, pz = int(x + dx * i), int(z + dz * i)
            if not (0 <= px < r.W and 0 <= pz < r.L):
                break
            if r.eau[pz, px] >= 0 and r.h[pz, px] < r.SEA - 1 and not r.riviere[pz, px] and not r.lac[pz, px]:
                return px, pz
        return None

    # ------------------------------------------------------------------ ponton d'arrivee
    def ponton(self, x, z):
        """Ponton de 28 blocs vers le sud, abri, bateau echoue, coffre de depart."""
        m, k, SEA = self.m, self.k, self.r.SEA
        y = SEA + 1
        for dz in range(-6, 28):
            for dx in range(-1, 2):
                m.pose(x + dx, y, z + dz, 'minecraft:spruce_planks' if (dz + dx) % 7 else 'minecraft:stripped_spruce_wood[axis=y]')
            if dz % 5 == 0:
                for dx in (-2, 2):
                    for yy in range(self.sol(x + dx, z + dz), y + 1):
                        m.pose(x + dx, yy, z + dz, 'minecraft:stripped_spruce_log[axis=y]')
                    m.pose(x + dx, y + 1, z + dz, 'minecraft:spruce_fence')
            else:
                for dx in (-2, 2):
                    m.pose(x + dx, y + 1, z + dz, 'minecraft:spruce_fence')
        k.lanterne(x - 2, y + 2, z + 27, suspendue=False); k.lanterne(x + 2, y + 2, z + 27, suspendue=False)
        # bateau a moteur echoue contre le ponton (coque de chene sombre, cabine)
        bx, bz = x + 4, z + 14
        for i in range(10):
            lg = 2 if 2 <= i <= 7 else 1
            for j in range(-lg, lg + 1):
                m.pose(bx + j, SEA, bz + i, 'minecraft:dark_oak_planks')
                if abs(j) == lg:
                    m.pose(bx + j, SEA + 1, bz + i, 'minecraft:dark_oak_slab[type=bottom,waterlogged=false]')
        m.boite(bx - 1, SEA + 1, bz + 4, bx + 1, SEA + 3, bz + 6, 'minecraft:white_concrete')
        m.boite(bx - 1, SEA + 2, bz + 4, bx + 1, SEA + 2, bz + 4, 'minecraft:glass_pane')
        m.boite(bx, SEA + 1, bz + 5, bx, SEA + 2, bz + 5, AIR)
        # abri et coffre de depart a terre
        ys = self.sol(x, z - 10) + 1
        v = Decale(m, x - 4, ys, z - 16)
        v.boite(0, -1, 0, 8, -1, 6, 'minecraft:spruce_planks')
        v.boite(0, 0, 0, 8, 3, 6, 'minecraft:stripped_spruce_log[axis=y]')
        v.boite(1, 0, 1, 7, 3, 5, AIR)
        v.boite(1, 0, 0, 7, 3, 0, 'minecraft:spruce_planks'); v.boite(1, 0, 6, 7, 3, 6, 'minecraft:spruce_planks')
        v.boite(0, 0, 1, 0, 3, 5, 'minecraft:spruce_planks'); v.boite(8, 0, 1, 8, 3, 5, 'minecraft:spruce_planks')
        v.boite(3, 0, 6, 5, 1, 6, AIR)
        v.boite(2, 1, 0, 3, 2, 0, 'minecraft:glass_pane'); v.boite(5, 1, 0, 6, 2, 0, 'minecraft:glass_pane')
        for zz in range(-1, 8):
            d = min(zz + 1, 7 - zz)
            v.boite(-1, 4 + d // 2, zz, 9, 4 + d // 2, zz, esc('spruce', 'south' if zz < 3 else 'north') if d % 2 == 0
                    else dalle('spruce', 'top'))
        kv = Kit(v, self.rng)
        v.coffre(2, 0, 1, 'south', [('minecraft:map', 1), ('minecraft:compass', 1), ('minecraft:bread', 16),
                                     ('minecraft:torch', 32), ('minecraft:crossbow', 1), ('minecraft:arrow', 32),
                                     ('minecraft:oak_boat', 1), ('minecraft:spyglass', 1)])
        kv.lit(6, 0, 2, 'north')
        kv.lanterne(4, 3, 3)
        v.panneau(4, 2, 7, 'south', ['SITE B', 'Ponton d\'arrivee', 'Campus : suivre', 'la piste au nord'])
        kv.veilleuses(1, 1, 7, 5, 0, 3, 3)
        self.ajoute('Ponton d\'arrivee', x, z - 10, 16)
        return x, z - 18

    # ------------------------------------------------------------------ tour de guet
    def tour(self, x, z):
        m, k = self.m, self.k
        y0 = self.sol(x, z)
        H = 26
        for (dx, dz) in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
            m.boite(x + dx, y0 - 4, z + dz, x + dx, y0 + H, z + dz, 'minecraft:stripped_spruce_log[axis=y]')
        for yy in range(y0 + 4, y0 + H, 6):
            for i in range(-2, 3):
                for (a, b) in ((i, -2), (i, 2), (-2, i), (2, i)):
                    m.pose(x + a, yy, z + b, 'minecraft:spruce_fence')
        for yy in range(y0 + 1, y0 + H + 1):
            m.pose(x, yy, z + 1, 'minecraft:ladder[facing=south,waterlogged=false]')
            m.pose(x, yy, z, 'minecraft:stripped_spruce_log[axis=y]')
        m.boite(x - 3, y0 + H + 1, z - 3, x + 3, y0 + H + 1, z + 3, 'minecraft:spruce_planks')
        m.pose(x, y0 + H + 1, z + 1, trappe('spruce', 'south', 'bottom'))
        m.pose(x, y0 + H + 1, z, 'minecraft:spruce_planks')
        for i in range(-3, 4):
            for (a, b) in ((i, -3), (i, 3), (-3, i), (3, i)):
                m.pose(x + a, y0 + H + 2, z + b, 'minecraft:spruce_fence')
        for (dx, dz) in ((-3, -3), (3, -3), (-3, 3), (3, 3)):
            m.boite(x + dx, y0 + H + 2, z + dz, x + dx, y0 + H + 4, z + dz, 'minecraft:spruce_fence')
        for zz in range(-4, 5):
            d = min(zz + 4, 4 - zz)
            m.boite(x - 4, y0 + H + 5 + d // 2, z + zz, x + 4, y0 + H + 5 + d // 2, z + zz,
                    esc('spruce', 'south' if zz < 0 else 'north') if d % 2 == 0 else dalle('spruce', 'top'))
        m.coffre(x + 2, y0 + H + 2, z - 2, 'west', [('minecraft:spyglass', 1), ('minecraft:arrow', 16), ('minecraft:bread', 4)])
        m.panneau(x - 2, y0 + H + 3, z - 2, 'south', ['Relevé 12 :', 'il remonte la', 'riviere a la', 'tombee de la nuit'],
                  mural=False)
        k.lanterne(x, y0 + H + 5, z)
        self.ajoute('Tour de guet', x, z, 6)

    # ------------------------------------------------------------------ helicoptere abattu
    def helicoptere(self, x, z):
        m, rng = self.m, self.rng
        y = self.sol(x, z) + 1
        # cellule couchee sur le flanc, cockpit ecrase
        for i in range(-6, 7):
            for j in range(-2, 3):
                for dy in range(0, 4):
                    if (j in (-2, 2) or dy in (0, 3)) and not (i > 3 and dy == 3):
                        m.pose(x + i, y + dy, z + j, 'minecraft:gray_concrete' if (i + dy) % 5 else 'minecraft:yellow_concrete')
            if i > 3:
                for j in (-1, 0, 1):
                    m.pose(x + i, y + 2, z + j, 'minecraft:black_stained_glass')
        m.boite(x - 3, y + 1, z - 1, x + 2, y + 2, z + 1, AIR)
        for i in range(7, 22):
            m.pose(x - i, y + 2 + (i > 18), z + (i // 6), 'minecraft:gray_concrete')
        m.pose(x - 21, y + 3, z + 3, 'minecraft:iron_bars'); m.pose(x - 21, y + 4, z + 3, 'minecraft:iron_bars')
        for a in range(0, 360, 90):
            for d in range(1, 9):
                m.pose(x + int(round(math.cos(math.radians(a + 20)) * d)), y + 4,
                       z + int(round(math.sin(math.radians(a + 20)) * d)) + (d > 6), 'minecraft:smooth_stone_slab[type=bottom,waterlogged=false]')
        m.pose(x, y + 4, z, 'minecraft:iron_block')
        # sillon arrache dans la jungle
        for i in range(10, 40):
            px, pz = x + i, z - i // 3
            m.pose(px, self.sol(px, pz), pz, 'minecraft:coarse_dirt')
        m.coffre(x - 1, y + 1, z, 'east', [('minecraft:crossbow', 1), ('minecraft:arrow', 20), ('minecraft:golden_apple', 1),
                                           ('minecraft:flint_and_steel', 1)])
        m.panneau(x + 3, y + 1, z - 3, 'north', ['VOL 21', "Il n'a pas", "touche l'appareil.", "Il a attendu."], mural=False)
        self.ajoute('Helicoptere abattu', x, z, 24)

    # ------------------------------------------------------------------ campement abandonne
    def campement(self, x, z):
        m, rng, k = self.m, self.rng, self.k
        for (tx, tz, coul) in ((x - 8, z - 4, 'green'), (x + 6, z - 6, 'brown'), (x - 2, z + 7, 'green')):
            y = self.sol(tx, tz) + 1
            for dz in range(-2, 3):
                for dx in range(-3, 4):
                    t = 2 - abs(dz)
                    if abs(dx) <= 3:
                        m.pose(tx + dx, y + t, tz + dz, 'minecraft:%s_wool' % coul if abs(dx) < 3 else AIR)
            m.boite(tx - 2, y, tz, tx + 2, y, tz, AIR)
            m.pose(tx - 1, y, tz, 'minecraft:green_bed[facing=east,occupied=false,part=foot]')
            m.pose(tx, y, tz, 'minecraft:green_bed[facing=east,occupied=false,part=head]')
        y = self.sol(x, z) + 1
        m.pose(x, y, z, 'minecraft:campfire[facing=north,lit=false,signal_fire=false,waterlogged=false]')
        for d in DIRS.values():
            m.pose(x + d[0] * 2, y, z + d[1] * 2, esc('spruce', OPP[[k for k, v in DIRS.items() if v == d][0]]))
        m.coffre(x + 3, y, z + 2, 'west', [('minecraft:bread', 6), ('minecraft:paper', 8), ('minecraft:torch', 16),
                                           ('minecraft:map', 1)], 'barrel')
        m.panneau(x - 3, y, z - 1, 'east', ['Camp 3', 'Deux disparus.', 'On a entendu', "respirer. Tout pres."], mural=False)
        self.k.sang([(x + 1, y, z + 1), (x + 6, y, z + 5), (x + 12, y, z + 8)], 0.6)
        self.ajoute('Campement abandonne', x, z, 16)

    # ------------------------------------------------------------------ bungalows sur pilotis
    def bungalows(self, pts):
        m, k, SEA = self.m, self.k, self.r.SEA
        for n, (x, z) in enumerate(pts):
            y = max(self.sol(x, z), SEA) + 4
            v = Decale(m, x - 3, y, z - 3)
            kv = Kit(v, self.rng)
            for (dx, dz) in ((0, 0), (6, 0), (0, 6), (6, 6)):
                for yy in range(self.sol(x - 3 + dx, z - 3 + dz) - y, 0):
                    v.pose(dx, yy, dz, 'minecraft:stripped_jungle_log[axis=y]')
            v.boite(0, -1, 0, 6, -1, 6, 'minecraft:jungle_planks')
            v.boite(0, 0, 0, 6, 3, 6, 'minecraft:bamboo_planks')
            v.boite(1, 0, 1, 5, 3, 5, AIR)
            for (a, b) in ((0, 0), (6, 0), (0, 6), (6, 6)):
                v.boite(a, 0, b, a, 3, b, 'minecraft:stripped_jungle_log[axis=y]')
            v.boite(2, 1, 0, 4, 2, 0, 'minecraft:glass_pane'); v.boite(0, 1, 2, 0, 2, 4, 'minecraft:glass_pane')
            v.boite(6, 1, 2, 6, 2, 4, 'minecraft:glass_pane')
            v.boite(3, 0, 6, 3, 1, 6, AIR)
            kv.porte(3, 0, 6, 'south', 'jungle', ouverte=n == 1)
            for zz in range(-1, 8):
                d = min(zz + 1, 7 - zz)
                v.boite(-1, 4 + d // 2, zz, 7, 4 + d // 2, zz, esc('bamboo_mosaic', 'south' if zz < 3 else 'north')
                        if d % 2 == 0 else dalle('bamboo_mosaic', 'top'))
            v.boite(0, 4, 0, 6, 5, 0, 'minecraft:bamboo_planks'); v.boite(0, 4, 6, 6, 5, 6, 'minecraft:bamboo_planks')
            kv.lit(1, 0, 4, 'north', ['white', 'yellow', 'cyan'][n % 3])
            v.pose(5, 0, 1, 'minecraft:barrel[facing=up,open=false]')
            kv.bureau(4, 0, 3, 'east', 1, 'jungle', ecrans=False)
            kv.lanterne(3, 3, 3)
            # escalier d'acces
            for i in range(0, 5):
                v.boite(3, -1 - i, 7 + i, 3, -1 - i, 7 + i, esc('jungle', 'north'))
            if n == 2:
                v.coffre(5, 0, 2, 'west', [('journal:bungalow', 1), ('minecraft:cooked_cod', 6), ('minecraft:fishing_rod', 1)])
                v.panneau(1, 1, 1, 'south', ['Il nage sous', 'le ponton. On', 'voit la voile', 'depasser.'], mural=False)
            kv.veilleuses(1, 1, 5, 5, 0, 3, 3)
            self.ajoute('Bungalow', x, z, 8)

    # ------------------------------------------------------------------ relais radio
    def relais(self, x, z):
        m, k = self.m, self.k
        y0 = self.sol(x, z) + 1
        m.boite(x - 4, y0 - 1, z - 3, x + 4, y0 - 1, z + 3, 'minecraft:gray_concrete')
        m.boite(x - 4, y0, z - 3, x + 4, y0 + 3, z + 3, 'minecraft:light_gray_concrete')
        m.boite(x - 3, y0, z - 2, x + 3, y0 + 3, z + 2, AIR)
        m.boite(x - 4, y0 + 4, z - 3, x + 4, y0 + 4, z + 3, 'minecraft:smooth_stone_slab[type=bottom,waterlogged=false]')
        m.boite(x, y0, z + 3, x, y0 + 1, z + 3, AIR)
        k.porte(x, y0, z + 3, 'south', 'iron')
        m.boite(x - 3, y0, z - 2, x + 3, y0, z - 2, 'minecraft:gray_concrete')
        for i in range(-3, 4):
            m.pose(x + i, y0 + 1, z - 2, 'minecraft:black_stained_glass_pane' if i % 2 else 'minecraft:lime_stained_glass_pane')
        m.pose(x - 2, y0, z, 'minecraft:dark_oak_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]')
        m.coffre(x + 3, y0, z + 2, 'north', [('minecraft:redstone', 8), ('minecraft:map', 1), ('minecraft:bread', 4)])
        m.panneau(x + 3, y0 + 1, z - 1, 'west', ['RELAIS 2', 'Liaison coupee', 'depuis 3 jours.', 'Personne ne vient.'])
        k.veilleuses(x - 3, z - 2, x + 3, z + 2, y0, 3, 3)
        # mat haubane de 40 blocs
        m.boite(x + 7, y0 - 1, z, x + 7, y0 + 40, z, 'minecraft:iron_bars')
        m.pose(x + 7, y0 + 41, z, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
        for yy in range(y0 + 8, y0 + 40, 8):
            m.pose(x + 6, yy, z, 'minecraft:end_rod[facing=west]'); m.pose(x + 8, yy, z, 'minecraft:end_rod[facing=east]')
        for (dx, dz) in ((12, 5), (12, -5), (2, 6)):
            for t in np.linspace(0, 1, 40):
                px = int(round(x + 7 + (dx - 7) * t)); pz = int(round(z + dz * t))
                yy = int(round(y0 + 36 * (1 - t) + (self.sol(x + dx, z + dz) + 1 - y0) * t))
                m.pose(px, yy, pz, 'minecraft:chain[axis=y,waterlogged=false]', seulement_air=True)
        self.ajoute('Relais radio', x, z, 12)

    # ------------------------------------------------------------------ epave sur le recif
    def epave(self, x, z):
        m, SEA = self.m, self.r.SEA
        # coque inclinee (gite de ~20 degres), echouee, a demi immergee
        for i in range(-12, 13):
            larg = int(round(4 * math.sqrt(max(0, 1 - (i / 13) ** 2)))) + 1
            for j in range(-larg, larg + 1):
                for dy in range(-3, 3):
                    bord = abs(j) == larg or dy == -3
                    if not bord:
                        continue
                    yy = SEA + dy + int(round(j * 0.35))
                    m.pose(x + j, yy, z + i, 'minecraft:dark_oak_planks' if (i + dy) % 4 else 'minecraft:stripped_dark_oak_log[axis=z]')
            if -8 < i < 6 and i % 3 == 0:
                for j in range(-larg + 1, larg):
                    m.pose(x + j, SEA + 1 + int(round(j * 0.35)), z + i, 'minecraft:dark_oak_slab[type=bottom,waterlogged=false]')
        for yy in range(SEA - 2, SEA + 14):
            m.pose(x + int((yy - SEA) * 0.35), yy, z - 2, 'minecraft:stripped_dark_oak_log[axis=y]')
        for i in range(-4, 5):
            m.pose(x + 3 + i, SEA + 10, z - 2, 'minecraft:white_wool' if i % 3 else 'minecraft:light_gray_wool')
        m.coffre(x, SEA - 1, z + 4, 'north', [('minecraft:gold_ingot', 6), ('minecraft:compass', 1), ('minecraft:nautilus_shell', 2),
                                              ('minecraft:trident', 1)])
        self.ajoute('Epave', x, z, 16)

    # ------------------------------------------------------------------ repaire sur l'ilot du lac
    def repaire(self, x, z):
        m, rng, SEA = self.m, self.rng, self.r.SEA
        for dx in range(-9, 10):
            for dz in range(-9, 10):
                if dx * dx + dz * dz > 80:
                    continue
                px, pz = x + dx, z + dz
                y = self.sol(px, pz)
                if y < SEA:
                    continue
                m.pose(px, y, pz, ['minecraft:mud', 'minecraft:packed_mud', 'minecraft:coarse_dirt'][rng.integers(0, 3)])
                u = rng.random()
                if u < 0.05:
                    m.pose(px, y + 1, pz, 'minecraft:skeleton_skull[rotation=%d]' % rng.integers(0, 16))
                elif u < 0.12:
                    m.pose(px, y + 1, pz, 'minecraft:bone_block[axis=%s]' % 'xz'[rng.integers(0, 2)])
                elif u < 0.2:
                    self.k.fil(px, y + 1, pz)
        # une carcasse : cage thoracique d'os et de tiges
        y = self.sol(x + 3, z) + 1
        for i in range(6):
            m.pose(x + i, y, z, 'minecraft:bone_block[axis=x]')
            for s in (-1, 1):
                m.pose(x + i, y, z + s, 'minecraft:end_rod[facing=up]')
                m.pose(x + i, y + 1, z + s * 2, 'minecraft:end_rod[facing=up]')
        m.pose(x - 1, y, z, 'minecraft:skeleton_skull[rotation=4]')
        self.ajoute('Repaire', x, z, 10)

    # ------------------------------------------------------------------ grotte derriere la cascade
    def grotte(self, x, z, dx, dz, y):
        """Galerie creusee dans la paroi, au pied de la chute, dans la direction (dx, dz)."""
        m, rng = self.m, self.rng
        n = math.hypot(dx, dz); dx, dz = dx / n, dz / n
        for i in range(2, 34):
            cx, cz = x + dx * i, z + dz * i
            r = 3.5 + 1.5 * math.sin(i / 5) + (3 if i > 24 else 0)
            m.ellipsoide(cx, y + 3, cz, r, 3.2 + (1.5 if i > 24 else 0), r, AIR, seulement_air=False)
        fx, fz = int(x + dx * 29), int(z + dz * 29)
        for _ in range(60):
            px, pz = fx + int(rng.integers(-5, 6)), fz + int(rng.integers(-5, 6))
            for yy in range(y + 8, y - 3, -1):
                if m.get(px, yy, pz) == m.AIR and m.get(px, yy - 1, pz) != m.AIR:
                    u = rng.random()
                    m.pose(px, yy, pz, 'minecraft:bone_block[axis=y]' if u < 0.2 else
                           'minecraft:skeleton_skull[rotation=3]' if u < 0.3 else 'minecraft:glow_lichen[down=true,east=false,north=false,south=false,up=false,waterlogged=false,west=false]')
                    break
        m.coffre(fx, y, fz, 'south', [('journal:grotte', 1), ('minecraft:diamond', 2), ('minecraft:iron_sword', 1)])
        m.panneau(fx + 1, y + 1, fz, 'south', ['Son antre.', 'Il revient', 'toujours ici', 'pour manger.'], mural=False)
        self.ajoute('Grotte de la cascade', fx, fz, 12)

    # ------------------------------------------------------------------ affut de chasse sur pilotis
    def affut(self, x, z):
        m = self.m
        y = max(self.sol(x, z), self.r.SEA) + 6
        for (dx, dz) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            m.boite(x + dx, self.sol(x + dx, z + dz), z + dz, x + dx, y, z + dz, 'minecraft:stripped_spruce_log[axis=y]')
        m.boite(x - 2, y, z - 2, x + 2, y, z + 2, 'minecraft:spruce_planks')
        for i in range(-2, 3):
            for (a, b) in ((i, -2), (i, 2), (-2, i), (2, i)):
                m.pose(x + a, y + 1, z + b, 'minecraft:bamboo_block[axis=y]' if (a + b) % 2 else 'minecraft:spruce_fence')
        m.boite(x - 2, y + 3, z - 2, x + 2, y + 3, z + 2, 'minecraft:bamboo_mosaic_slab[type=bottom,waterlogged=false]')
        for (a, b) in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
            m.boite(x + a, y + 1, z + b, x + a, y + 2, z + b, 'minecraft:spruce_fence')
        for yy in range(self.sol(x, z + 3) + 1, y + 1):
            m.pose(x, yy, z + 3, 'minecraft:ladder[facing=south,waterlogged=false]')
            if yy < y:
                m.pose(x, yy, z + 2, 'minecraft:stripped_spruce_log[axis=y]')
        m.pose(x, y + 1, z + 2, AIR)
        m.coffre(x - 1, y + 1, z - 1, 'south', [('minecraft:spyglass', 1), ('minecraft:arrow', 12), ('minecraft:bread', 4)])
        self.ajoute('Affut', x, z, 5)

    # ------------------------------------------------------------------ passerelle dans la mangrove
    def passerelle(self, pts, station=True):
        m, SEA = self.m, self.r.SEA
        y = SEA + 2
        for (ax, az), (bx, bz) in zip(pts, pts[1:]):
            n = int(max(abs(bx - ax), abs(bz - az)))
            for i in range(n + 1):
                x = int(round(ax + (bx - ax) * i / n)); z = int(round(az + (bz - az) * i / n))
                for dx in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        m.pose(x + dx, y, z + dz, 'minecraft:mangrove_planks')
                if i % 6 == 0:
                    for yy in range(self.sol(x, z), y):
                        m.pose(x, yy, z, 'minecraft:mangrove_log[axis=y]')
        if station:
            x, z = pts[-1]
            v = Decale(m, x - 5, y + 1, z - 4)
            v.boite(0, -1, 0, 10, -1, 8, 'minecraft:mangrove_planks')
            v.boite(0, 0, 0, 10, 3, 8, 'minecraft:mud_bricks')
            v.boite(1, 0, 1, 9, 3, 7, AIR)
            v.boite(3, 1, 0, 7, 2, 0, 'minecraft:glass_pane'); v.boite(10, 1, 3, 10, 2, 5, 'minecraft:glass_pane')
            v.boite(0, 0, 4, 0, 1, 4, AIR)
            v.boite(-1, 4, -1, 11, 4, 9, 'minecraft:mangrove_slab[type=bottom,waterlogged=false]')
            kv = Kit(v, self.rng)
            kv.porte(0, 0, 4, 'west', 'mangrove')
            kv.paillasse(2, 1, 7, 1, 0, 'south')
            kv.bureau(8, 0, 6, 'east', 1, 'mangrove')
            v.coffre(1, 0, 7, 'east', [('minecraft:glass_bottle', 6), ('journal:delta', 1), ('minecraft:bread', 4)])
            v.panneau(5, 1, 7, 'north', ['STATION DELTA', 'Echantillons :', 'eau, vase,', 'empreintes (15 m)'])
            kv.veilleuses(1, 1, 9, 7, 0, 3, 3)
            self.ajoute('Station du delta', x, z, 10)

    # ------------------------------------------------------------------ pont suspendu casse
    def pont_suspendu(self, a, b, y):
        """Pont de planches entre a et b a l'altitude y, qui s'affaisse au milieu et s'est rompu."""
        m = self.m
        n = int(math.dist(a, b))
        for i in range(n + 1):
            t = i / n
            if 0.45 < t < 0.58:
                continue                               # la rupture
            x = a[0] + (b[0] - a[0]) * t; z = a[1] + (b[1] - a[1]) * t
            yy = int(round(y - 5 * math.sin(math.pi * t)))
            if t > 0.58:
                yy -= int(round((t - 0.58) * 25 * (1 - t)))     # le troncon aval pend
            nx, nz = -(b[1] - a[1]) / n, (b[0] - a[0]) / n
            for s in (-1, 0, 1):
                m.pose(int(round(x + nx * s)), yy, int(round(z + nz * s)), 'minecraft:spruce_slab[type=bottom,waterlogged=false]')
            for s in (-2, 2):
                m.pose(int(round(x + nx * s)), yy + 1, int(round(z + nz * s)), 'minecraft:spruce_fence')
        for (px, pz) in (a, b):
            for s in (-2, 2):
                m.boite(px, y - 6, pz + s, px, y + 3, pz + s, 'minecraft:stripped_spruce_log[axis=y]')
        self.ajoute('Pont suspendu', int((a[0] + b[0]) / 2), int((a[1] + b[1]) / 2), 6)

    # ================================================================== outils de terrain
    def plateforme(self, x0, z0, x1, z1, y, surface='minecraft:coarse_dirt', dessous='minecraft:dirt', hauteur_libre=24, talus=10):
        """Aplanit un rectangle a y (sol) : remblai ou deblai, air au-dessus. Met a jour la
        carte de hauteur (pour la foret, le sous-bois et les pistes)."""
        m, r = self.m, self.r
        x0, x1 = sorted((int(x0), int(x1))); z0, z1 = sorted((int(z0), int(z1)))
        for z in range(z0, z1 + 1):
            for x in range(x0, x1 + 1):
                if not (0 <= x < r.W and 0 <= z < r.L):
                    continue
                hs = int(r.h[z, x])
                bas = min(hs, y) - 3
                m.boite(x, bas, z, x, y - 1, z, dessous)
                m.pose(x, y, z, surface)
                m.boite(x, y + 1, z, x, y + hauteur_libre, z, AIR)
                r.h[z, x] = y
                if r.eau[z, x] > y:
                    r.eau[z, x] = -1
        # talus : on raccorde en pente douce au terrain autour, au lieu d'une falaise ou d'une fosse
        T = talus
        for z in range(z0 - T, z1 + T + 1):
            for x in range(x0 - T, x1 + T + 1):
                if not (0 <= x < r.W and 0 <= z < r.L):
                    continue
                d = max(x0 - x, x - x1, z0 - z, z - z1)
                if d <= 0 or r.eau[z, x] > r.h[z, x]:
                    continue
                t = d / (T + 1)
                t = t * t * (3 - 2 * t)
                hs = int(r.h[z, x])
                cible = int(round(y + (hs - y) * t))
                if cible == hs:
                    continue
                if cible > hs:
                    m.boite(x, hs, z, x, cible - 1, z, dessous)
                else:
                    m.boite(x, cible + 1, z, x, hs + 1, z, AIR)
                m.pose(x, cible, z, 'minecraft:grass_block[snowy=false]')
                r.h[z, x] = cible

    def sol_moyen(self, x0, z0, x1, z1):
        return int(round(np.median(self.r.h[int(z0):int(z1) + 1, int(x0):int(x1) + 1])))

    def pilier(self, x, z, y_haut, etat):
        """Poteau du sol jusqu'a y_haut (exclu)."""
        for yy in range(self.sol(x, z) - 2, y_haut):
            self.m.pose(x, yy, z, etat)

    def jeep(self, x, z, sens='south', renversee=False):
        """Tout-terrain abandonne sur une piste."""
        m = self.m
        y = self.sol(x, z) + 1
        axe_z = sens in ('north', 'south')
        for i in range(6):
            for j in range(3):
                px, pz = (x + j, z + i) if axe_z else (x + i, z + j)
                if renversee:
                    m.pose(px, y, pz, 'minecraft:red_concrete' if j != 1 else 'minecraft:white_concrete')
                    m.pose(px, y + 1, pz, 'minecraft:white_concrete' if 0 < i < 5 else 'minecraft:gray_concrete')
                    if i in (1, 4) and j in (0, 2):
                        m.pose(px, y + 2, pz, 'minecraft:black_concrete')
                else:
                    m.pose(px, y, pz, 'minecraft:white_concrete' if 0 < i < 5 else 'minecraft:gray_concrete')
                    m.pose(px, y + 1, pz, 'minecraft:red_concrete' if j != 1 and 1 < i < 5 else 'minecraft:white_concrete')
                    if 1 <= i <= 3:
                        m.pose(px, y + 2, pz, 'minecraft:light_blue_stained_glass' if (i + j) % 3 else AIR)
            if not renversee:
                for j in (-1, 3):
                    if i in (1, 4):
                        px, pz = (x + j, z + i) if axe_z else (x + i, z + j)
                        m.pose(px, y, pz, 'minecraft:black_concrete')

    def poteau_indicateur(self, x, z, fleches):
        """Poteau de bois avec jusqu'a 4 panneaux : fleches = [(facing, texte1, texte2)]."""
        m = self.m
        y = self.sol(x, z) + 1
        m.boite(x, y, z, x, y + 3, z, 'minecraft:spruce_fence')
        for i, (facing, t1, t2) in enumerate(fleches[:4]):
            dx, dz = DIRS[facing]
            m.panneau(x + dx, y + 1 + (i // 2), z + dz, facing, [t1, t2, '', ''], mural=True, bois='spruce')

    # ================================================================== phare
    def phare(self, x, z):
        m, k, rng = self.m, self.k, self.rng
        y0 = self.sol_moyen(x - 6, z - 6, x + 6, z + 6) + 1
        self.plateforme(x - 7, z - 7, x + 14, z + 7, y0 - 1, 'minecraft:stone_bricks', 'minecraft:stone')
        R, H = 4, 36
        for y in range(y0, y0 + H):
            for dx in range(-R, R + 1):
                for dz in range(-R, R + 1):
                    d = math.hypot(dx, dz)
                    if d > R + 0.4:
                        continue
                    if d > R - 0.6:
                        bande = ((y - y0) // 6) % 2
                        e = 'minecraft:red_concrete' if bande else 'minecraft:white_concrete'
                        if (y - y0) % 8 in (3, 4) and (dx == 0 or dz == 0):
                            e = 'minecraft:glass_pane'
                        m.pose(x + dx, y, z + dz, e)
                    else:
                        m.pose(x + dx, y, z + dz, AIR)
        # colimacon
        m.boite(x, y0, z, x, y0 + H - 1, z, 'minecraft:stone_bricks')
        for i in range(H - 1):
            a = i * 2 * math.pi / 10
            for rr in (1.2, 2.3, 3.2):
                px, pz = int(round(x + rr * math.cos(a))), int(round(z + rr * math.sin(a)))
                m.pose(px, y0 + i, pz, 'minecraft:smooth_stone_slab[type=top,waterlogged=false]')
        # porte
        m.boite(x + R, y0, z, x + R, y0 + 1, z, AIR)
        k.porte(x + R, y0, z, 'east', 'spruce')
        # galerie et lanterne
        yt = y0 + H
        for dx in range(-R - 2, R + 3):
            for dz in range(-R - 2, R + 3):
                d = math.hypot(dx, dz)
                if d <= R + 2.4:
                    m.pose(x + dx, yt, z + dz, 'minecraft:polished_andesite')
                if R + 1.5 < d <= R + 2.4:
                    m.pose(x + dx, yt + 1, z + dz, 'minecraft:iron_bars')
        m.boite(x, yt, z, x, yt, z, 'minecraft:polished_andesite')
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                bord = max(abs(dx), abs(dz)) == 2
                for yy in range(yt + 1, yt + 5):
                    m.pose(x + dx, yy, z + dz, ('minecraft:iron_bars' if (abs(dx) == 2 and abs(dz) == 2) else 'minecraft:glass')
                           if bord else AIR)
        m.pose(x, yt + 1, z, 'minecraft:iron_block'); m.pose(x, yt + 2, z, 'minecraft:redstone_lamp[lit=false]')
        m.pose(x, yt + 3, z, 'minecraft:iron_block')
        for dx in range(-3, 4):
            for dz in range(-3, 4):
                if abs(dx) + abs(dz) <= 4:
                    m.pose(x + dx, yt + 5 + (abs(dx) + abs(dz) < 3), z + dz, 'minecraft:red_concrete')
        m.pose(x, yt + 7, z, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
        # trappe d'acces a la galerie : on ouvre la dalle au-dessus de la derniere marche
        a = (H - 2) * 2 * math.pi / 10
        for rr in (1.2, 2.3, 3.2):
            m.pose(int(round(x + rr * math.cos(a))), yt, int(round(z + rr * math.sin(a))), AIR)
        # maison du gardien
        v = Decale(m, x + 6, y0, z - 4)
        kv = Kit(v, rng)
        v.boite(0, 0, 0, 8, 3, 8, 'minecraft:stone_bricks'); v.boite(1, 0, 1, 7, 3, 7, AIR)
        v.boite(-1, -1, -1, 9, -1, 9, 'minecraft:stone_bricks')
        v.boite(1, -1, 1, 7, -1, 7, 'minecraft:spruce_planks')
        for zz in range(-1, 10):
            d = min(zz + 1, 9 - zz)
            v.boite(-1, 4 + d // 2, zz, 9, 4 + d // 2, zz, esc('dark_oak', 'south' if zz < 4 else 'north') if d % 2 == 0
                    else dalle('dark_oak', 'top'))
        for zz in range(0, 9):
            d = min(zz + 1, 9 - zz)
            for xx in (0, 8):
                v.boite(xx, 4, zz, xx, 3 + d // 2, zz, 'minecraft:stone_bricks')
        v.boite(0, 1, 3, 0, 2, 5, 'minecraft:glass_pane'); v.boite(8, 1, 3, 8, 2, 5, 'minecraft:glass_pane')
        v.boite(3, 1, 8, 5, 2, 8, 'minecraft:glass_pane')
        v.boite(4, 0, 0, 4, 1, 0, AIR); kv.porte(4, 0, 0, 'north', 'spruce')
        kv.lit(1, 0, 5, 'south')
        kv.bureau(6, 0, 5, 'east', 1, 'spruce', ecrans=False)
        v.pose(7, 0, 1, 'minecraft:furnace[facing=west,lit=false]')
        v.coffre(7, 0, 2, 'west', [('minecraft:spyglass', 1), ('minecraft:cooked_cod', 8), ('minecraft:lantern', 2),
                                   ('journal:phare', 1)])
        v.panneau(4, 2, 7, 'north', ['JOURNAL DU PHARE', 'Le feu s\'est eteint', 'le 14. Quelque chose', 'nage autour.'])
        kv.lanterne(4, 3, 4)
        kv.veilleuses(1, 1, 7, 7, 0, 3, 3)
        kv.usure(-1, -1, -1, 9, 4, 9, {'minecraft:stone_bricks': ['minecraft:mossy_stone_bricks', 'minecraft:cracked_stone_bricks']}, 0.25)
        k.veilleuses(x - 3, z - 3, x + 3, z + 3, y0 + 1, 3, 3)
        self.ajoute('Phare', x, z, 16)

    # ================================================================== temple en ruine
    def temple(self, x, z):
        """Pyramide a degres envahie par la jungle ; escalier au sud, sanctuaire au sommet,
        galerie basse (2 blocs : il ne peut pas y entrer) vers la chambre du tresor."""
        m, k, rng = self.m, self.k, self.rng
        B = 17                      # demi-base
        y0 = self.sol_moyen(x - B, z - B, x + B, z + B)
        self.plateforme(x - B - 4, z - B - 4, x + B + 4, z + B + 10, y0, 'minecraft:mossy_cobblestone', 'minecraft:stone', 40)
        mat = ['minecraft:mossy_stone_bricks', 'minecraft:stone_bricks', 'minecraft:cracked_stone_bricks',
               'minecraft:mossy_cobblestone', 'minecraft:mossy_stone_bricks']
        ids = [m.P(e) for e in mat]
        niveaux = 6
        for n in range(niveaux):
            b = B - n * 3
            ya, yb = y0 + 1 + n * 4, y0 + 4 + n * 4
            zone_b = m.blocs[ya:yb + 1, z - b:z + b + 1, x - b:x + b + 1]
            zone_b[...] = np.array(ids, np.uint16)[rng.integers(0, len(ids), zone_b.shape)]
            # corniche sculptee
            for i in range(-b, b + 1, 4):
                for (px, pz) in ((x + i, z - b), (x + i, z + b), (x - b, z + i), (x + b, z + i)):
                    m.pose(px, yb, pz, 'minecraft:chiseled_stone_bricks')
        top = y0 + niveaux * 4
        # escalier monumental au sud (pente 4/3 : une marche par bloc, paliers)
        for i in range(niveaux * 4):
            zz = z + (B - (niveaux - 1) * 3) + (niveaux * 4 - 1 - i)
            m.boite(x - 3, y0 + 1 + i, zz, x + 3, y0 + 1 + i, zz, esc('mossy_stone_brick', 'north'))
            m.boite(x - 3, y0 + 2 + i, zz, x + 3, y0 + 5 + i, zz, AIR)
            m.boite(x - 3, y0 + 1, zz, x + 3, y0 + i, zz, 'minecraft:stone_bricks')
            for s in (-4, 4):
                m.pose(x + s, y0 + 1 + i, zz, 'minecraft:mossy_stone_brick_wall')
        # sanctuaire au sommet : 4 piliers, linteau, autel
        b = B - niveaux * 3 + 2
        for (dx, dz) in ((-b, -b), (b, -b), (-b, b), (b, b)):
            m.boite(x + dx, top + 1, z + dz, x + dx, top + 5, z + dz, 'minecraft:chiseled_stone_bricks')
        m.boite(x - b, top + 6, z - b, x + b, top + 6, z + b, 'minecraft:mossy_stone_bricks')
        m.boite(x - b + 1, top + 6, z - b + 1, x + b - 1, top + 6, z + b - 1, AIR)
        m.boite(x - 1, top + 1, z - 1, x + 1, top + 1, z + 1, 'minecraft:polished_andesite')
        m.pose(x, top + 2, z, 'minecraft:lantern[hanging=false,waterlogged=false]')
        m.panneau(x, top + 2, z + 1, 'south', ['Ils le priaient', 'bien avant nous.', 'La voile au-dessus', "de l'eau."], mural=False)
        # fresque en os sur la face nord du sanctuaire : silhouette a voile
        for (dx, dy) in ((-3, 1), (-2, 1), (-1, 1), (0, 1), (1, 1), (2, 2), (3, 2), (-1, 2), (0, 2), (0, 3), (-1, 3),
                         (1, 2), (-2, 2), (4, 2)):
            m.pose(x + dx, top + 1 + dy, z - (B - niveaux * 3 + 2), 'minecraft:bone_block[axis=y]')
        # galerie basse vers la chambre, depuis la face est
        yb = y0 + 1
        m.boite(x + 2, yb, z - 1, x + B + 1, yb + 1, z, AIR)
        m.boite(x - 4, yb, z - 4, x + 4, yb + 3, z + 4, AIR)
        for (dx, dz) in ((-4, -4), (4, -4), (-4, 4), (4, 4)):
            m.boite(x + dx, yb, z + dz, x + dx, yb + 3, z + dz, 'minecraft:chiseled_stone_bricks')
        m.coffre(x, yb, z - 3, 'south', [('minecraft:gold_ingot', 8), ('minecraft:emerald', 5), ('minecraft:golden_apple', 2),
                                         ('journal:temple', 1), ('minecraft:experience_bottle', 8), ('minecraft:diamond', 3)])
        for (dx, dz) in ((-3, 3), (3, 3), (-3, -3), (3, -3)):
            m.pose(x + dx, yb, z + dz, 'minecraft:skeleton_skull[rotation=%d]' % rng.integers(0, 16))
        k.torche_murale(x - 3, yb + 2, z, 'east')
        m.pose(x + 1, yb, z + 2, 'minecraft:bone_block[axis=x]'); m.pose(x + 2, yb, z + 2, 'minecraft:bone_block[axis=x]')
        k.toiles(x - 3, yb, z - 3, x + 3, yb + 3, z + 3, 8)
        # ruine : effondrements et vegetation
        for _ in range(4):
            cx, cz = x + int(rng.choice([-B + 2, B - 2])), z + int(rng.integers(-B, B))
            m.ellipsoide(cx, top - int(rng.integers(6, 16)), cz, rng.uniform(2, 4), rng.uniform(2, 3), rng.uniform(2, 4), AIR,
                         seulement_air=False)
        for _ in range(22):
            cx, cz = x + int(rng.integers(-B - 2, B + 3)), z + int(rng.integers(-B - 2, B + 3))
            for yy in range(top + 7, y0, -1):
                if m.get(cx, yy, cz) != m.AIR:
                    m.pose(cx, yy + 1, cz, ['minecraft:moss_carpet', 'minecraft:fern', 'minecraft:azalea'][rng.integers(0, 3)],
                           seulement_air=True)
                    break
        from arbres import vigne
        for _ in range(140):
            face = ['north', 'south', 'east', 'west'][rng.integers(0, 4)]
            n_ = int(rng.integers(0, niveaux)); b = B - n_ * 3
            i = int(rng.integers(-b, b + 1))
            px, pz = {'north': (x + i, z + b + 1), 'south': (x + i, z - b - 1), 'west': (x + b + 1, z + i), 'east': (x - b - 1, z + i)}[face]
            for yy in range(y0 + 4 + n_ * 4, y0 + n_ * 4, -1):
                if m.get(px, yy, pz) == m.AIR:
                    m.pose(px, yy, pz, vigne(face))
        # statues renversees le long de l'allee
        for i, s in enumerate((-1, 1, -1, 1)):
            px, pz = x + s * 7, z + B + 4 + i * 2
            if i % 2:
                m.boite(px, y0 + 1, pz, px, y0 + 3, pz, 'minecraft:chiseled_stone_bricks')
                m.pose(px, y0 + 4, pz, 'minecraft:mossy_stone_brick_wall')
            else:
                m.boite(px - 2, y0 + 1, pz, px, y0 + 1, pz, 'minecraft:mossy_stone_bricks')
        self.ajoute('Temple en ruine', x, z, B + 8)

    # ================================================================== enclos des herbivores
    def enclos_herbivores(self, x0, z0, x1, z1):
        m, k, rng = self.m, self.k, self.rng
        n = 0
        # cloture electrique, avec un pan couche
        def poteau(x, z, i):
            y = self.sol(x, z) + 1
            if i % 6 == 0:
                m.boite(x, y - 2, z, x, y + 6, z, 'minecraft:polished_andesite')
                m.pose(x, y + 7, z, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
            else:
                m.boite(x, y, z, x, y + 5, z, 'minecraft:iron_bars')
        cotes = [((x0, z0), (x1, z0)), ((x1, z0), (x1, z1)), ((x1, z1), (x0, z1)), ((x0, z1), (x0, z0))]
        for (ax, az), (bx, bz) in cotes:
            L_ = max(abs(bx - ax), abs(bz - az))
            for i in range(L_):
                x = ax + (bx - ax) * i // L_; z = az + (bz - az) * i // L_
                if (ax, az) == (x1, z1) and 20 < i < 30:
                    y = self.sol(x, z) + 1
                    m.pose(x, y, z + (1 if i % 2 else 2), 'minecraft:iron_bars')     # pan arrache, couche au sol
                    continue
                poteau(x, z, i)
        # portail et poste de nourrissage
        mx = (x0 + x1) // 2
        y = self.sol(mx, z1) + 1
        m.boite(mx - 3, y, z1, mx + 3, y + 5, z1, AIR)
        m.boite(mx - 4, y - 1, z1, mx - 4, y + 7, z1, 'minecraft:stone_bricks'); m.boite(mx + 4, y - 1, z1, mx + 4, y + 7, z1, 'minecraft:stone_bricks')
        m.boite(mx - 4, y + 8, z1, mx + 4, y + 8, z1, 'minecraft:stripped_spruce_log[axis=x]')
        m.panneau(mx, y + 7, z1 + 1, 'south', ['ENCLOS H-02', 'Parasaurolophus', '(6 individus)', ''])
        cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
        yc = self.sol(cx, cz) + 1
        for i in range(-6, 7):
            m.pose(cx + i, yc, cz, 'minecraft:composter[level=%d]' % rng.integers(0, 8))
            m.pose(cx + i, yc - 1, cz + 1, 'minecraft:hay_block[axis=x]')
        # tour d'observation dans un angle
        tx, tz = x0 + 6, z0 + 6
        yt = self.sol(tx, tz) + 1
        for (dx, dz) in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
            m.boite(tx + dx, yt - 2, tz + dz, tx + dx, yt + 10, tz + dz, 'minecraft:stripped_spruce_log[axis=y]')
        m.boite(tx - 2, yt + 10, tz - 2, tx + 2, yt + 10, tz + 2, 'minecraft:spruce_planks')
        for i in range(-2, 3):
            for (a, b) in ((i, -2), (i, 2), (-2, i), (2, i)):
                m.pose(tx + a, yt + 11, tz + b, 'minecraft:spruce_fence')
        for yy in range(yt, yt + 11):
            m.pose(tx, yy, tz + 3, 'minecraft:ladder[facing=south,waterlogged=false]')
        m.pose(tx, yt + 11, tz + 2, AIR)
        m.pose(tx, yt + 10, tz + 2, 'minecraft:spruce_trapdoor[facing=south,half=bottom,open=true,powered=false,waterlogged=false]')
        m.coffre(tx - 1, yt + 11, tz - 1, 'south', [('minecraft:spyglass', 1), ('minecraft:bread', 4), ('minecraft:arrow', 16)])
        # carcasses : cotes en tiges, colonne d'os, cranes
        for _ in range(5):
            px = int(rng.integers(x0 + 8, x1 - 8)); pz = int(rng.integers(z0 + 8, z1 - 8))
            yy = self.sol(px, pz) + 1
            axe = rng.random() < 0.5
            for i in range(7):
                ex, ez = (px + i, pz) if axe else (px, pz + i)
                m.pose(ex, yy, ez, 'minecraft:bone_block[axis=%s]' % ('x' if axe else 'z'))
                if 1 <= i <= 5:
                    for s in (-1, 1):
                        rx, rz = (ex, ez + s) if axe else (ex + s, ez)
                        m.pose(rx, yy, rz, 'minecraft:end_rod[facing=up]')
                        m.pose(rx + (0 if axe else s), yy + 1, rz + (s if axe else 0), 'minecraft:end_rod[facing=up]')
            m.pose(px - (1 if axe else 0), yy, pz - (0 if axe else 1), 'minecraft:skeleton_skull[rotation=%d]' % rng.integers(0, 16))
            k.sang([(px, yy, pz), (px + int(rng.integers(-9, 10)), yy, pz + int(rng.integers(-9, 10)))], 0.5)
        m.panneau(cx, yc, cz - 2, 'north', ['Il ne reste', 'rien. Il est entre', "par l'eau et", 'ressorti par la.'], mural=False)
        self.ajoute('Enclos des herbivores', cx, cz, 0)

    # ================================================================== village de pecheurs
    def village(self, x, z, n=6):
        """Maisons sur pilotis alignees le long d'un ponton, sechoirs, barques, chapelle."""
        m, k, rng, SEA = self.m, self.k, self.rng, self.r.SEA
        yp = SEA + 2
        # ponton principal (nord-sud) et appontements
        for dz in range(-n * 7, 8):
            for dx in (-1, 0, 1):
                m.pose(x + dx, yp, z + dz, 'minecraft:spruce_planks')
            if dz % 5 == 0:
                for dx in (-2, 2):
                    self.pilier(x + dx, z + dz, yp + 2, 'minecraft:stripped_spruce_log[axis=y]')
            for dx in (-2, 2):
                if dz % 5:
                    m.pose(x + dx, yp + 1, z + dz, 'minecraft:spruce_fence')
        bois = ['spruce', 'jungle', 'mangrove', 'dark_oak', 'spruce', 'jungle']
        for i in range(n):
            cote = -1 if i % 2 else 1
            hx = x + cote * 4 - (7 if cote < 0 else 0)
            hz = z - i * 7 - 6
            bw = bois[i % len(bois)]
            v = Decale(m, hx, yp, hz)
            kv = Kit(v, rng)
            for (dx, dz) in ((0, 0), (6, 0), (0, 5), (6, 5)):
                for yy in range(self.sol(hx + dx, hz + dz) - yp - 2, 0):
                    v.pose(dx, yy, dz, 'minecraft:stripped_%s_log[axis=y]' % bw)
            v.boite(0, 0, 0, 6, 0, 5, 'minecraft:%s_planks' % bw)
            v.boite(0, 1, 0, 6, 3, 5, 'minecraft:%s_planks' % bw); v.boite(1, 1, 1, 5, 3, 4, AIR)
            for (a, b) in ((0, 0), (6, 0), (0, 5), (6, 5)):
                v.boite(a, 1, b, a, 3, b, 'minecraft:stripped_%s_log[axis=y]' % bw)
            v.boite(2, 2, 0, 4, 2, 0, 'minecraft:glass_pane'); v.boite(2, 2, 5, 4, 2, 5, 'minecraft:glass_pane')
            porte_x = 6 if cote < 0 else 0
            v.boite(porte_x, 1, 2, porte_x, 2, 2, AIR)
            kv.porte(porte_x, 1, 2, 'east' if cote < 0 else 'west', bw, ouverte=rng.random() < 0.4)
            for zz in range(-1, 7):
                d = min(zz + 1, 6 - zz)
                v.boite(-1, 4 + d // 2, zz, 7, 4 + d // 2, zz, esc(bw, 'south' if zz < 3 else 'north') if d % 2 == 0
                        else dalle(bw, 'top'))
            v.boite(0, 4, 0, 6, 4, 0, 'minecraft:%s_planks' % bw); v.boite(0, 4, 5, 6, 4, 5, 'minecraft:%s_planks' % bw)
            kv.lit(2, 1, 3, 'north', ['white', 'brown', 'blue', 'green', 'yellow', 'gray'][i])
            v.pose(4, 1, 1, 'minecraft:barrel[facing=up,open=false]')
            v.pose(5, 1, 4, 'minecraft:furnace[facing=west,lit=false]' if i % 2 else 'minecraft:crafting_table')
            kv.lanterne(3, 3, 3)
            kv.veilleuses(1, 2, 5, 4, 1, 3, 3)
            if i == 3:
                v.coffre(1, 1, 1, 'south', [('minecraft:fishing_rod', 1), ('minecraft:cooked_salmon', 8), ('minecraft:oak_boat', 1),
                                           ('minecraft:crossbow', 1), ('minecraft:arrow', 16)])
                v.panneau(3, 2, 4, 'north', ['On a remonte', 'les filets vides.', 'Dechiquetes.', "Il chasse ici."])
            # passerelle vers le ponton
            for dx in range(1, 4):
                px = hx + (7 + dx - 1 if cote < 0 else -dx)
                m.pose(px, yp, hz + 2, 'minecraft:spruce_planks'); m.pose(px, yp, hz + 3, 'minecraft:spruce_planks')
        # sechoirs a poisson et barques
        for i in range(4):
            sx, sz = x + 6 + i * 3, z + 4
            y = max(self.sol(sx, sz), SEA) + 1
            m.boite(sx, y, sz, sx, y + 2, sz, 'minecraft:spruce_fence')
            m.pose(sx, y + 3, sz, 'minecraft:spruce_slab[type=bottom,waterlogged=false]')
            m.pose(sx + 1, y + 2, sz, 'minecraft:dried_kelp_block')
        for i in range(3):
            bx, bz = x + (5 if i % 2 else -6), z - 4 - i * 12
            for j in range(5):
                m.pose(bx, SEA, bz + j, 'minecraft:spruce_planks'); m.pose(bx + 1, SEA, bz + j, 'minecraft:spruce_planks')
                if j in (0, 4):
                    continue
                m.pose(bx - 1, SEA + 1, bz + j, 'minecraft:spruce_slab[type=bottom,waterlogged=false]')
                m.pose(bx + 2, SEA + 1, bz + j, 'minecraft:spruce_slab[type=bottom,waterlogged=false]')
        self.ajoute('Village de pecheurs', x, z - n * 3, 18)

    # ================================================================== observatoire du volcan
    def observatoire(self, x, z):
        m, k, rng = self.m, self.k, self.rng
        y0 = self.sol_moyen(x - 4, z - 4, x + 4, z + 4) + 1
        self.plateforme(x - 5, z - 5, x + 5, z + 5, y0 - 1, 'minecraft:gray_concrete', 'minecraft:tuff', 10)
        m.boite(x - 3, y0, z - 3, x + 3, y0 + 3, z + 3, 'minecraft:light_gray_concrete')
        m.boite(x - 2, y0, z - 2, x + 2, y0 + 3, z + 2, AIR)
        m.boite(x - 3, y0 + 4, z - 3, x + 3, y0 + 4, z + 3, 'minecraft:gray_concrete')
        m.boite(x - 2, y0 + 1, z - 3, x + 2, y0 + 2, z - 3, 'minecraft:glass_pane')
        m.boite(x, y0, z + 3, x, y0 + 1, z + 3, AIR); k.porte(x, y0, z + 3, 'south', 'iron')
        m.pose(x - 2, y0, z - 2, 'minecraft:observer[facing=up,powered=false]')
        m.pose(x - 1, y0, z - 2, 'minecraft:lectern[facing=south,has_book=false,powered=false]')
        m.pose(x + 1, y0, z - 2, 'minecraft:lever[face=floor,facing=north,powered=false]')
        m.pose(x + 2, y0, z - 2, 'minecraft:target[power=0]')
        m.coffre(x + 2, y0, z + 1, 'west', [('minecraft:spyglass', 1), ('minecraft:map', 1), ('minecraft:clock', 1)])
        m.panneau(x - 2, y0 + 1, z + 2, 'east', ['SISMOGRAPHE', 'Pas le volcan.', 'Des pas. Lourds.', 'Rythmes de 3 s.'])
        m.boite(x + 2, y0 + 5, z + 2, x + 2, y0 + 14, z + 2, 'minecraft:iron_bars')
        m.pose(x + 2, y0 + 15, z + 2, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
        # parabole
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                if abs(dx) + abs(dz) <= 3:
                    m.pose(x - 1 + dx, y0 + 6 + (abs(dx) + abs(dz) >= 3), z - 1 + dz, 'minecraft:smooth_quartz_slab[type=bottom,waterlogged=false]')
        m.pose(x - 1, y0 + 5, z - 1, 'minecraft:iron_bars')
        k.veilleuses(x - 2, z - 2, x + 2, z + 2, y0, 3, 3)
        self.ajoute('Observatoire du volcan', x, z, 8)

    # ================================================================== voliere
    def voliere(self, x, z, R=20):
        """Dome geodesique de barreaux (hommage a la voliere de Jurassic Park III), eventre ;
        passerelle interieure en hauteur, nids d'os."""
        m, k, rng = self.m, self.k, self.rng
        y0 = self.sol_moyen(x - R, z - R, x + R, z + R)
        self.plateforme(x - R - 2, z - R - 2, x + R + 2, z + R + 2, y0, 'minecraft:coarse_dirt', 'minecraft:dirt', R + 4)
        for dy in range(0, R + 1):
            for dx in range(-R, R + 1):
                for dz in range(-R, R + 1):
                    d = math.sqrt(dx * dx + dy * dy * 1.3 + dz * dz)
                    if R - 0.8 < d <= R:
                        # la maille : un anneau sur trois en plein, le reste en barreaux ; une grande dechirure
                        if dx > 6 and -8 < dz < 8 and dy < 12:
                            continue
                        e = 'minecraft:iron_bars' if (dy % 4 and (dx + dz) % 5) else 'minecraft:light_gray_concrete'
                        m.pose(x + dx, y0 + 1 + dy, z + dz, e)
        # passerelle en anneau a mi-hauteur sur poteaux
        yp = y0 + 10
        for a in range(0, 360, 2):
            px = int(round(x + 11 * math.cos(math.radians(a)))); pz = int(round(z + 11 * math.sin(math.radians(a))))
            m.pose(px, yp, pz, 'minecraft:spruce_planks')
            px2 = int(round(x + 12.5 * math.cos(math.radians(a)))); pz2 = int(round(z + 12.5 * math.sin(math.radians(a))))
            m.pose(px2, yp + 1, pz2, 'minecraft:spruce_fence')
            if a % 30 == 0:
                m.boite(px, y0 + 1, pz, px, yp - 1, pz, 'minecraft:stripped_spruce_log[axis=y]')
            if 150 < a < 170:
                m.pose(px, yp, pz, AIR)                       # la passerelle s'est effondree ici
        for yy in range(y0 + 1, yp + 1):
            m.pose(x - 12, yy, z, 'minecraft:ladder[facing=west,waterlogged=false]')
            m.pose(x - 11, yy, z, 'minecraft:stripped_spruce_log[axis=y]')
        # nids et os
        for _ in range(6):
            px, pz = x + int(rng.integers(-12, 13)), z + int(rng.integers(-12, 13))
            yy = self.sol(px, pz) + 1
            m.boite(px - 1, yy, pz - 1, px + 1, yy, pz + 1, 'minecraft:hay_block[axis=y]')
            m.pose(px, yy + 1, pz, 'minecraft:bone_block[axis=y]')
            m.pose(px + 1, yy + 1, pz, 'minecraft:white_carpet')
        m.panneau(x, y0 + 1, z + R - 2, 'north', ['VOLIERE', 'Fermee depuis', "que la voile a", 'traverse le filet.'], mural=False)
        m.coffre(x, yp + 1, z - 11, 'south', [('minecraft:feather', 16), ('minecraft:arrow', 32), ('minecraft:bow', 1)])
        self.ajoute('Voliere', x, z, R + 4)

    # ================================================================== piste d'atterrissage et avion cargo
    def piste(self, x0, z, x1, avion=None):
        m, k, rng = self.m, self.k, self.rng
        y = self.sol_moyen(x0, z - 6, x1, z + 6)
        self.plateforme(x0 - 4, z - 10, x1 + 4, z + 10, y, 'minecraft:grass_block[snowy=false]', 'minecraft:dirt', 20)
        for xx in range(x0, x1 + 1):
            for dz in range(-5, 6):
                e = 'minecraft:gray_concrete' if (xx * 3 + dz * 7) % 11 else 'minecraft:cracked_stone_bricks'
                if dz == 0 and xx % 8 < 4:
                    e = 'minecraft:white_concrete'
                if abs(dz) == 5:
                    e = 'minecraft:light_gray_concrete'
                m.pose(xx, y, z + dz, e)
                if rng.random() < 0.04:
                    m.pose(xx, y + 1, z + dz, ['minecraft:grass', 'minecraft:fern'][rng.integers(0, 2)])
            if xx % 10 == 0:
                for dz in (-6, 6):
                    m.pose(xx, y + 1, z + dz, 'minecraft:redstone_lamp[lit=false]')
        # manche a air et hangar
        m.boite(x0 + 4, y + 1, z - 9, x0 + 4, y + 7, z - 9, 'minecraft:iron_bars')
        for i in range(4):
            m.pose(x0 + 5 + i, y + 7 - i // 2, z - 9, 'minecraft:orange_wool' if i % 2 else 'minecraft:white_wool')
        v = Decale(m, x0 + 12, y + 1, z - 22)
        kv = Kit(v, rng)
        v.boite(0, 0, 0, 16, 7, 10, 'minecraft:light_gray_concrete')
        v.boite(1, 0, 1, 15, 6, 9, AIR)
        v.boite(3, 0, 10, 13, 6, 10, AIR)                  # grande porte ouverte
        for xx in range(0, 17):
            d = min(xx, 16 - xx)
            v.boite(xx, 7 + min(d, 3), 0, xx, 7 + min(d, 3), 10, 'minecraft:gray_concrete')
        kv.casiers(1, 0, 1, 'south', 6, 'east')
        v.coffre(14, 0, 1, 'south', [('minecraft:iron_ingot', 8), ('minecraft:bucket', 1), ('minecraft:torch', 32),
                                     ('minecraft:crossbow', 1), ('minecraft:arrow', 24)])
        for i in range(4):
            v.pose(3 + i * 3, 0, 5, 'minecraft:barrel[facing=up,open=false]')
            v.pose(3 + i * 3, 1, 5, 'minecraft:barrel[facing=up,open=false]')
        v.panneau(8, 2, 1, 'south', ['PISTE NORD', 'Dernier vol :', 'annule. Carburant', 'siphonne. Par qui ?'])
        kv.veilleuses(1, 1, 15, 9, 0, 3, 3)
        # l'avion cargo : sorti de piste, fuselage casse en deux dans la jungle
        ax, az = avion if avion else (x1 - 24, z + 36)
        ya = self.sol(ax, az) + 3
        for i in range(-16, 14):
            if -2 <= i <= 0:
                continue                                    # la cassure
            for a in range(0, 360, 12):
                dy = int(round(3 * math.sin(math.radians(a)))); dz = int(round(3 * math.cos(math.radians(a))))
                off = 0 if i > 0 else int((-i) * 0.15)
                m.pose(ax + i, ya + dy - off, az + dz + (0 if i > 0 else 2), 'minecraft:light_gray_concrete' if a % 36 else 'minecraft:white_concrete')
            if i == 12:
                m.boite(ax + i + 1, ya - 1, az - 1, ax + i + 2, ya + 1, az + 1, 'minecraft:black_stained_glass')
        for j in range(-14, 15):
            if abs(j) < 3:
                continue
            if j < 10:
                m.boite(ax + 2, ya, az + j, ax + 5, ya, az + j, 'minecraft:light_gray_concrete')
        m.boite(ax - 15, ya + 3, az + 2, ax - 13, ya + 9, az + 2, 'minecraft:light_gray_concrete')
        for _ in range(8):
            px, pz = ax + int(rng.integers(-24, 20)), az + int(rng.integers(-12, 13))
            yy = self.sol(px, pz) + 1
            m.pose(px, yy, pz, 'minecraft:barrel[facing=up,open=false]')
        m.coffre(ax + 6, ya - 2, az, 'west', [('minecraft:golden_apple', 2), ('minecraft:iron_ingot', 12), ('minecraft:tnt', 2),
                                              ('minecraft:flint_and_steel', 1)])
        for i in range(0, 40):
            px, pz = ax + 14 + i // 2, az + 6 + i // 3
            m.pose(px, self.sol(px, pz), pz, 'minecraft:coarse_dirt')
        self.ajoute('Piste d\'atterrissage', (x0 + x1) // 2, z, 0)
        self.ajoute('Avion cargo', ax, az, 22)

    # ================================================================== poste de controle sur la route
    def checkpoint(self, x, z, axe_z=True):
        m, k = self.m, self.k
        y = self.sol(x, z) + 1
        # barriere levee (cassee) et guerite
        m.boite(x - 5, y, z, x - 5, y + 1, z, 'minecraft:polished_andesite')
        for i in range(8):
            m.pose(x - 4 + i, y + 1 + (i > 5), z, 'minecraft:red_concrete' if i % 2 else 'minecraft:white_concrete')
        v = Decale(m, x + 5, y, z - 2)
        kv = Kit(v, self.rng)
        v.boite(0, -1, 0, 4, -1, 4, 'minecraft:gray_concrete')
        v.boite(0, 0, 0, 4, 3, 4, 'minecraft:light_gray_concrete'); v.boite(1, 0, 1, 3, 2, 3, AIR)
        v.boite(0, 1, 1, 0, 2, 3, 'minecraft:glass_pane'); v.boite(4, 1, 1, 4, 2, 3, 'minecraft:glass_pane')
        v.boite(2, 0, 4, 2, 1, 4, AIR); kv.porte(2, 0, 4, 'south', 'iron')
        kv.bureau(2, 0, 2, 'west', 1)
        v.coffre(3, 0, 1, 'west', [('minecraft:crossbow', 1), ('minecraft:arrow', 16), ('minecraft:bread', 4), ('minecraft:torch', 16)])
        v.panneau(1, 1, 3, 'east', ['CHECKPOINT 2', 'Personne ne passe', 'apres 18 h.', ''])
        kv.veilleuses(1, 1, 3, 3, 0, 3, 3)
        # sacs de sable et projecteur
        for i in range(-3, 4):
            m.pose(x - 8, y, z + i, 'minecraft:mud_bricks'); m.pose(x - 8, y + 1, z + i, 'minecraft:mud_brick_slab[type=bottom,waterlogged=false]')
        m.boite(x + 5, y, z + 4, x + 5, y + 3, z + 4, 'minecraft:iron_bars')
        m.pose(x + 5, y + 4, z + 4, 'minecraft:redstone_lamp[lit=false]')
        self.ajoute('Checkpoint', x, z, 10)

    # ================================================================== bunker militaire
    def bunker(self, x, z):
        m, k, rng = self.m, self.k, self.rng
        y0 = self.sol_moyen(x - 8, z - 6, x + 8, z + 6)
        self.plateforme(x - 12, z - 10, x + 12, z + 12, y0, 'minecraft:coarse_dirt', 'minecraft:dirt', 16)
        v = Decale(m, x - 8, y0 - 3, z - 6)
        kv = Kit(v, rng)
        # caisson de beton a demi enterre
        v.boite(0, 0, 0, 16, 7, 12, 'minecraft:gray_concrete')
        v.boite(1, 1, 1, 15, 5, 11, AIR)
        v.boite(0, 7, 0, 16, 7, 12, 'minecraft:smooth_stone')
        # remblai de terre sur les flancs et le toit
        for dz in range(-3, 16):
            for dx in range(-3, 20):
                d = max(0, -dx, dx - 16, -dz, dz - 12)
                if d > 0:
                    for yy in range(0, max(0, 7 - d * 2)):
                        v.pose(dx, yy + 1, dz, 'minecraft:dirt', seulement_air=True)
                    v.pose(dx, max(0, 7 - d * 2), dz, 'minecraft:grass_block[snowy=false]', seulement_air=True)
        v.boite(0, 8, 0, 16, 8, 12, 'minecraft:grass_block[snowy=false]')
        # entree en tranchee au sud, porte blindee
        v.boite(7, 1, 12, 9, 3, 18, AIR)
        for i in range(4):
            v.boite(7, 3 - i, 15 + i, 9, 3 - i, 15 + i, AIR)
        v.boite(7, 0, 13, 9, 0, 18, 'minecraft:gray_concrete')
        for i in range(4):
            v.boite(7, i, 18 - i, 9, i, 18 - i, esc('stone', 'south'))
        v.boite(8, 1, 12, 8, 2, 12, AIR); kv.porte(8, 1, 12, 'south', 'iron')
        # meurtrieres
        for xx in range(2, 15, 4):
            v.pose(xx, 4, 0, 'minecraft:iron_bars')
        # interieur : couchettes, armurerie, radio, vivres
        v.boite(1, 0, 1, 15, 0, 11, 'minecraft:polished_andesite')
        for i, zz in enumerate((2, 5, 8)):
            v.pose(1, 1, zz, 'minecraft:white_bed[facing=west,occupied=false,part=head]')
            v.pose(2, 1, zz, 'minecraft:white_bed[facing=west,occupied=false,part=foot]')
            v.pose(1, 3, zz, 'minecraft:white_bed[facing=west,occupied=false,part=head]')
            v.pose(2, 3, zz, 'minecraft:white_bed[facing=west,occupied=false,part=foot]')
            v.pose(1, 2, zz, 'minecraft:spruce_slab[type=top,waterlogged=false]'); v.pose(2, 2, zz, 'minecraft:spruce_slab[type=top,waterlogged=false]')
        v.coffre(14, 1, 2, 'west', [('minecraft:crossbow', 2), ('minecraft:arrow', 64), ('minecraft:iron_chestplate', 1),
                                    ('minecraft:iron_helmet', 1), ('minecraft:shield', 1), ('journal:bunker', 1)])
        v.coffre(14, 1, 3, 'west', [('minecraft:cooked_beef', 16), ('minecraft:bread', 16), ('minecraft:golden_carrot', 8),
                                    ('minecraft:torch', 32)])
        v.coffre(14, 1, 4, 'west', [('minecraft:tnt', 4), ('minecraft:flint_and_steel', 1), ('minecraft:iron_sword', 1)])
        kv.bureau(10, 1, 9, 'north', 2)
        v.pose(12, 1, 7, 'minecraft:note_block[instrument=harp,note=0,powered=false]')
        v.panneau(8, 3, 1, 'south', ['ABRI 4', 'Tenir jusqu\'a', "l'evacuation.", "Elle n'est pas venue."])
        kv.lampes_plafond(1, 1, 15, 11, 6, 4, 0.5)
        kv.veilleuses(1, 1, 15, 11, 1, 3, 3)
        # nid de mitrailleuse sur le toit : sacs de sable
        for dx in range(-3, 4):
            for dz in range(-3, 4):
                if max(abs(dx), abs(dz)) == 3:
                    v.pose(8 + dx, 9, 6 + dz, 'minecraft:mud_bricks')
        v.pose(8, 9, 6, 'minecraft:anvil[facing=north]')
        self.ajoute('Bunker', x, z, 16)

    # ================================================================== mine abandonnee
    def mine(self, x, z, dx, dz):
        """Galerie de 3 x 4 qui s'enfonce dans la crete (direction dx, dz), boisage, rails,
        minerai, salle de stockage au fond."""
        m, k, rng = self.m, self.k, self.rng
        n = math.hypot(dx, dz); dx, dz = dx / n, dz / n
        px_, pz_ = -dz, dx
        y = self.sol(x, z) + 1
        for i in range(0, 48):
            cx, cz = x + dx * i, z + dz * i
            yy = y - i // 12
            for s in (-1.5, -0.5, 0.5, 1.5):
                bx, bz = int(round(cx + px_ * s)), int(round(cz + pz_ * s))
                for h_ in range(0, 4):
                    m.pose(bx, yy + h_, bz, AIR)
                m.pose(bx, yy - 1, bz, 'minecraft:gravel' if rng.random() < 0.4 else 'minecraft:stone')
            m.pose(int(round(cx)), yy, int(round(cz)), 'minecraft:rail[shape=%s,waterlogged=false]' % (
                'north_south' if abs(dz) > abs(dx) else 'east_west'))
            if i % 5 == 0:
                for s in (-2, 2):
                    bx, bz = int(round(cx + px_ * s)), int(round(cz + pz_ * s))
                    m.boite(bx, yy, bz, bx, yy + 3, bz, 'minecraft:stripped_oak_log[axis=y]')
                for s in (-2, -1, 0, 1, 2):
                    bx, bz = int(round(cx + px_ * s)), int(round(cz + pz_ * s))
                    m.pose(bx, yy + 4, bz, 'minecraft:stripped_oak_log[axis=%s]' % ('x' if abs(dz) > abs(dx) else 'z'))
                bx, bz = int(round(cx + px_ * 1)), int(round(cz + pz_ * 1))
                m.pose(bx, yy + 3, bz, 'minecraft:lantern[hanging=true,waterlogged=false]' if i % 10 == 0 else AIR)
            # minerai dans les parois
            for s in (-3, 3):
                if rng.random() < 0.3:
                    bx, bz = int(round(cx + px_ * s)), int(round(cz + pz_ * s))
                    m.pose(bx, yy + int(rng.integers(0, 3)), bz,
                           ['minecraft:coal_ore', 'minecraft:iron_ore', 'minecraft:copper_ore', 'minecraft:gold_ore'][rng.integers(0, 4)])
        # salle du fond
        cx, cz = x + dx * 50, z + dz * 50
        yy = y - 4
        m.ellipsoide(cx, yy + 2.5, cz, 6, 3.5, 6, AIR, seulement_air=False)
        m.coffre(int(cx), yy, int(cz), 'south', [('minecraft:iron_pickaxe', 1), ('minecraft:raw_gold', 8), ('minecraft:tnt', 3),
                                                 ('minecraft:torch', 32), ('journal:mine', 1)])
        m.panneau(int(cx) + 1, yy, int(cz), 'south', ['Galerie 3', 'Il ne rentre pas.', 'Il attend dehors.', 'Depuis 2 jours.'], mural=False)
        k.veilleuses(int(cx) - 4, int(cz) - 4, int(cx) + 4, int(cz) + 4, yy, 3, 3)
        # portique d'entree
        for s in (-2, 2):
            bx, bz = int(round(x + px_ * s)), int(round(z + pz_ * s))
            m.boite(bx, y, bz, bx, y + 4, bz, 'minecraft:stripped_oak_log[axis=y]')
        m.panneau(int(round(x - dx * 2)), y, int(round(z - dz * 2)), 'south', ['MINE', 'Danger', 'eboulements', ''], mural=False)
        self.ajoute('Mine abandonnee', x, z, 10)

    # ================================================================== serres botaniques
    def serres(self, x, z):
        m, k, rng = self.m, self.k, self.rng
        y0 = self.sol_moyen(x, z, x + 40, z + 20)
        self.plateforme(x - 2, z - 2, x + 42, z + 22, y0, 'minecraft:gravel', 'minecraft:dirt', 14)
        for n_ in range(3):
            gx = x + n_ * 14
            for xx in range(gx, gx + 12):
                for zz in range(z, z + 20):
                    m.pose(xx, y0, zz, 'minecraft:polished_andesite')
                # arc de verre (demi-cylindre selon z)
            for zz in range(z, z + 20):
                for dx in range(0, 12):
                    for dy in range(0, 8):
                        d = math.hypot((dx - 5.5) / 6, dy / 7.5)
                        if 0.86 < d <= 1.0:
                            e = 'minecraft:white_concrete' if zz % 5 == 0 else 'minecraft:glass'
                            if rng.random() < 0.08:
                                e = AIR                                        # carreaux brises
                            m.pose(gx + dx, y0 + 1 + dy, zz, e)
            for dx in range(0, 12):
                for dy in range(0, 8):
                    if math.hypot((dx - 5.5) / 6, dy / 7.5) <= 1.0:
                        m.pose(gx + dx, y0 + 1 + dy, z, 'minecraft:glass_pane')
                        m.pose(gx + dx, y0 + 1 + dy, z + 19, 'minecraft:glass_pane')
            m.boite(gx + 5, y0 + 1, z + 19, gx + 6, y0 + 2, z + 19, AIR)
            # bacs de culture : mousse, azalees, fougeres, bambous en pot, grosse plante
            for zz in range(z + 2, z + 18, 4):
                for dx in (1, 2, 9, 10):
                    m.pose(gx + dx, y0 + 1, zz, 'minecraft:moss_block')
                    m.pose(gx + dx, y0 + 2, zz, ['minecraft:azalea', 'minecraft:flowering_azalea', 'minecraft:fern',
                                                  'minecraft:big_dripleaf[facing=south,tilt=none,waterlogged=false]'][rng.integers(0, 4)])
            m.pose(gx + 5, y0 + 1, z + 10, 'minecraft:moss_block')
            m.boite(gx + 5, y0 + 2, z + 10, gx + 5, y0 + 5, z + 10, 'minecraft:jungle_log[axis=y]')
            m.ellipsoide(gx + 5.5, y0 + 6.5, z + 10.5, 2.5, 1.2, 3.5, 'minecraft:jungle_leaves[distance=7,persistent=true,waterlogged=false]')
            k.veilleuses(gx + 1, z + 1, gx + 10, z + 18, y0 + 1, 3, 3)
        m.panneau(x + 20, y0 + 1, z + 21, 'south', ['SERRES', 'Plantes du Cretace', 'reconstituees.', "L'une est toxique."], mural=False)
        m.coffre(x + 16, y0 + 1, z + 3, 'east', [('minecraft:bone_meal', 16), ('minecraft:glow_berries', 12), ('minecraft:melon_slice', 12)])
        self.ajoute('Serres', x + 20, z + 10, 14)

    # ================================================================== cimetiere
    def cimetiere(self, x, z):
        m, rng = self.m, self.rng
        for i in range(10):
            gx, gz = x + (i % 5) * 4, z + (i // 5) * 5
            y = self.sol(gx, gz)
            m.pose(gx, y, gz, 'minecraft:coarse_dirt'); m.pose(gx, y, gz + 1, 'minecraft:coarse_dirt')
            m.pose(gx, y + 1, gz - 1, 'minecraft:spruce_fence')
            m.pose(gx, y + 2, gz - 1, 'minecraft:spruce_fence')
            m.pose(gx - 1, y + 2, gz - 1, 'minecraft:spruce_fence')
            m.pose(gx + 1, y + 2, gz - 1, 'minecraft:spruce_fence')
        noms = [['M. Keller', 'securite'], ['A. Diallo', 'soigneur'], ['J. Perrin', 'genetique'], ['T. Okafor', 'pilote']]
        for i, (n_, r_) in enumerate(noms):
            gx, gz = x + i * 4, z
            y = self.sol(gx, gz)
            m.panneau(gx, y + 1, gz - 2, 'south', [n_, r_, '', 'RIP'], mural=False)
        self.ajoute('Cimetiere', x + 8, z + 3, 8)
