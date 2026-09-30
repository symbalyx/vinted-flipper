"""Base militaire « Kilo » : le coeur de l'operation sur l'ile, la ou tout le reste prend sens.

Elle remplace le campus-musee. Tout y est pratique : un grillage et des miradors, un QG, des
baraquements, une cantine, un hangar, un parc de vehicules, du carburant, un heliport, un mat
radio, un chateau d'eau, des conteneurs de materiel. Elle est posee pres du ponton (ravitaillement
par la mer), de la piste d'atterrissage et du relais radio sur la colline.

Et il est passe par la : un pan du grillage arrache, des conteneurs renverses, du sang jusqu'au
hangar, la base vide.

Repere local : Decale(m, bx, y0 + 1, bz) ; y = 0 est la premiere couche d'air au-dessus de la
dalle, x de 0 a LX - 1 vers l'est, z de 0 a LZ - 1 vers le sud.
"""
import math

from monde import Decale
from mobilier import Kit, esc, dalle, trappe

AIR = 'minecraft:air'
BETON = 'minecraft:light_gray_concrete'
BETON_F = 'minecraft:gray_concrete'
TOLE = 'minecraft:green_terracotta'
GRILLE = 'minecraft:iron_bars'
POTEAU = 'minecraft:stripped_dark_oak_log[axis=y]'
SAC = 'minecraft:mud_bricks'
SAC_D = 'minecraft:mud_brick_slab[type=bottom,waterlogged=false]'


class BaseMilitaire:
    LX, LZ = 104, 84

    def __init__(self, li, bx, bz):
        self.li, self.m, self.r, self.rng = li, li.m, li.r, li.rng
        self.bx, self.bz = bx, bz

    # ------------------------------------------------------------------ l'ensemble
    def construire(self):
        li, LX, LZ = self.li, self.LX, self.LZ
        bx, bz = self.bx, self.bz
        y0 = li.sol_moyen(bx, bz, bx + LX, bz + LZ)
        self.y0 = y0
        li.plateforme(bx - 6, bz - 6, bx + LX + 6, bz + LZ + 6, y0, 'minecraft:gravel', 'minecraft:dirt', 30, talus=12)
        v = self.v = Decale(self.m, bx, y0 + 1, bz)
        self.k = Kit(v, self.rng)
        self._sol()
        self._enceinte()
        for (x, z) in ((2, 2), (LX - 7, 2), (2, LZ - 7), (LX - 7, LZ - 7)):
            self._mirador(x, z)
        self._qg(40, 8)
        self._baraquement(10, 36, 'red')
        self._baraquement(10, 52, 'green')
        self._cantine(40, 36)
        self._hangar(64, 30)
        self._heliport(76, 62)
        self._parc_vehicules(40, 58)
        self._carburant(66, 8)
        self._chateau_eau(86, 10)
        self._mat_radio(33, 10)
        self._conteneurs(10, 68)
        self._projecteurs()
        self._degats()
        li.ajoute('Base militaire', bx + LX // 2, bz + LZ // 2, 0)
        return (bx + LX // 2, bz + LZ + 1)            # la porte sud (vers le ponton)

    def portes(self):
        """Centres des 4 portes, en coordonnees de la grille (pour les routes)."""
        bx, bz, LX, LZ = self.bx, self.bz, self.LX, self.LZ
        return {'sud': (bx + LX // 2, bz + LZ + 4), 'nord': (bx + LX // 2, bz - 4),
                'ouest': (bx - 4, bz + LZ // 2), 'est': (bx + LX + 4, bz + LZ // 2)}

    # ------------------------------------------------------------------ sol : allees et dalles
    def _sol(self):
        v, rng = self.v, self.rng
        LX, LZ = self.LX, self.LZ
        # allees en croix (beton use), le reste en gravier et terre battue
        for x in range(LX):
            for z in range(LZ):
                allee = abs(x - LX // 2) <= 3 or abs(z - LZ // 2) <= 3 or abs(z - 26) <= 2
                if allee:
                    v.pose(x, -1, z, BETON_F if rng.random() < 0.8 else 'minecraft:cracked_stone_bricks')
                elif rng.random() < 0.25:
                    v.pose(x, -1, z, 'minecraft:coarse_dirt')

    # ------------------------------------------------------------------ grillage, portes, guerites
    def _enceinte(self):
        v, k = self.v, self.k
        LX, LZ = self.LX, self.LZ
        portes = {('z', 0): LX // 2, ('z', LZ - 1): LX // 2, ('x', 0): LZ // 2, ('x', LX - 1): LZ // 2}
        self.breche = set()
        for i in range(-6, 7):                                   # le pan arrache, au nord-est
            self.breche.add((LX - 22 + i, 0))
        for (axe, fixe), centre in portes.items():
            n = LX if axe == 'z' else LZ
            for i in range(n):
                x, z = (i, fixe) if axe == 'z' else (fixe, i)
                if abs(i - centre) <= 3:
                    continue                                     # l'ouverture de la porte
                if (x, z) in self.breche:
                    if (x + z) % 3 == 0:
                        v.pose(x, 0, z, GRILLE)                  # des bouts tordus au sol
                    continue
                if i % 6 == 0:
                    v.boite(x, 0, z, x, 3, z, POTEAU)
                else:
                    v.boite(x, 0, z, x, 2, z, GRILLE)
            # guerite et barriere a chaque porte
            gx, gz = (centre + 5, fixe) if axe == 'z' else (fixe, centre + 5)
            ox, oz = (0, 1 if fixe == 0 else -3) if axe == 'z' else (1 if fixe == 0 else -3, 0)
            self._guerite(gx + (ox if axe == 'x' else 0), gz + (oz if axe == 'z' else 0))
            for d in (-4, 4):
                px, pz = (centre + d, fixe) if axe == 'z' else (fixe, centre + d)
                v.boite(px, 0, pz, px, 3, pz, POTEAU)
                v.pose(px, 4, pz, 'minecraft:lantern[hanging=false,waterlogged=false]')

    def _guerite(self, x, z):
        v, k = self.v, self.k
        v.boite(x, 0, z, x + 2, 2, z + 2, 'minecraft:white_concrete')
        v.boite(x + 1, 0, z + 1, x + 1, 1, z + 1, AIR)
        v.boite(x, 1, z + 1, x + 2, 1, z + 1, 'minecraft:glass_pane')
        v.boite(x + 1, 1, z, x + 1, 1, z + 2, 'minecraft:glass_pane')
        v.boite(x, 3, z, x + 2, 3, z + 2, dalle('smooth_stone'))
        v.pose(x + 1, 0, z + 1, AIR)
        v.pose(x + 1, 0, z, AIR); v.pose(x + 1, 1, z, AIR)          # l'entree

    # ------------------------------------------------------------------ miradors
    def _mirador(self, x, z):
        v, k = self.v, self.k
        H = 9
        for dx in (0, 4):
            for dz in (0, 4):
                v.boite(x + dx, -3, z + dz, x + dx, H, z + dz, 'minecraft:stripped_spruce_log[axis=y]')
        for y in (3, 6):
            for i in range(5):
                for (a, b) in ((i, 0), (i, 4), (0, i), (4, i)):
                    v.pose(x + a, y, z + b, 'minecraft:spruce_fence', seulement_air=True)
        v.boite(x, H, z, x + 4, H, z + 4, 'minecraft:spruce_planks')
        for i in range(5):
            for (a, b) in ((i, 0), (i, 4), (0, i), (4, i)):
                v.pose(x + a, H + 1, z + b, SAC_D if (i % 2) else SAC)
        v.boite(x - 1, H + 4, z - 1, x + 5, H + 4, z + 5, dalle('spruce'))
        for (a, b) in ((0, 0), (4, 0), (0, 4), (4, 4)):
            v.boite(x + a, H + 1, z + b, x + a, H + 3, z + b, 'minecraft:spruce_fence')
        # echelle au milieu d'un cote, trappe en haut
        for y in range(0, H):
            v.pose(x + 2, y, z + 5, 'minecraft:ladder[facing=south,waterlogged=false]')
        v.boite(x + 2, -1, z + 4, x + 2, H - 1, z + 4, 'minecraft:spruce_planks')
        v.pose(x + 2, H, z + 5, AIR)
        v.pose(x + 2, H + 2, z + 2, 'minecraft:lantern[hanging=false,waterlogged=false]')
        v.coffre(x + 1, H + 1, z + 1, 'south', [('minecraft:spyglass', 1), ('minecraft:arrow', 24), ('minecraft:crossbow', 1)])

    # ------------------------------------------------------------------ QG
    def _qg(self, x, z):
        v, k = self.v, self.k
        L, P = 26, 14
        for et in (0, 1):
            y = et * 5
            v.boite(x, y, z, x + L, y + 4, z + P, 'minecraft:white_concrete')
            v.boite(x + 1, y, z + 1, x + L - 1, y + 3, z + P - 1, AIR)
            v.boite(x, y + 4, z, x + L, y + 4, z + P, BETON)
            # fenetres en bande
            for xx in range(x + 2, x + L - 1, 3):
                v.boite(xx, y + 1, z, xx + 1, y + 2, z, 'minecraft:glass_pane')
                v.boite(xx, y + 1, z + P, xx + 1, y + 2, z + P, 'minecraft:glass_pane')
            k.lampes_plafond(x + 1, z + 1, x + L - 1, z + P - 1, y + 3, 5, 0.3)
        v.boite(x + 1, -1, z + 1, x + L - 1, -1, z + P - 1, 'minecraft:polished_andesite')
        # entree au sud, avec un auvent
        v.boite(x + 12, 0, z + P, x + 13, 1, z + P, AIR)
        k.double_porte(x + 12, 0, z + P, 'south', 'iron', ouverte=True)
        v.boite(x + 10, 3, z + P + 1, x + 15, 3, z + P + 3, dalle('smooth_stone'))
        # rez : salle des operations (grande table de cartes), radio, armurerie
        k.longue_table(x + 5, z + 5, x + 14, z + 8, 0, 'smooth_quartz', 'dark_oak')
        for i in range(4):
            v.pose(x + 6 + i * 2, 1, z + 6, 'minecraft:white_carpet')     # les cartes etalees
        k.bureau(x + 18, 0, z + 3, 'north', 3)
        k.bureau(x + 18, 0, z + 10, 'south', 3)
        v.pose(x + 23, 0, z + 2, 'minecraft:note_block[instrument=harp,note=0,powered=false]')
        k.casiers(x + 24, 0, z + 5, 'west', 5, 'south')
        v.coffre(x + 2, 0, z + 2, 'south', [('minecraft:crossbow', 2), ('minecraft:arrow', 64), ('minecraft:iron_chestplate', 2),
                                          ('minecraft:iron_helmet', 2), ('minecraft:shield', 2), ('minecraft:spyglass', 1)])
        v.coffre(x + 3, 0, z + 2, 'south', [('minecraft:tnt', 6), ('minecraft:flint_and_steel', 1), ('minecraft:iron_sword', 2),
                                          ('minecraft:cooked_beef', 12)])
        # escalier vers l'etage (le long du mur ouest)
        for i in range(5):
            v.pose(x + 2, i, z + 5 + i, esc('stone_brick', 'south'))
            v.boite(x + 2, i + 1, z + 5 + i, x + 2, 3 + i, z + 5 + i, AIR)
        v.boite(x + 1, 4, z + 6, x + 3, 4, z + 10, AIR)
        # etage : bureau du commandant, dortoir des officiers
        k.bureau(x + 18, 5, z + 6, 'east', 2, 'dark_oak')
        v.coffre(x + 22, 5, z + 2, 'south', [('minecraft:compass', 1), ('minecraft:map', 1), ('minecraft:golden_apple', 2),
                                            ('minecraft:iron_ingot', 8)])
        for i in range(4):
            k.lit(x + 6 + i * 3, 5, z + 12, 'north', 'green')
        # toit : antennes et nid de sacs de sable
        for dx in range(-3, 4):
            for dz in range(-3, 4):
                if max(abs(dx), abs(dz)) == 3:
                    v.pose(x + 6 + dx, 10, z + 7 + dz, SAC)
        v.boite(x + 22, 10, z + 3, x + 22, 16, z + 3, GRILLE)
        v.pose(x + 22, 17, z + 3, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
        self.li.ajoute('QG (base militaire)', self.bx + x + L // 2, self.bz + z + P // 2, 0)

    # ------------------------------------------------------------------ baraquements
    def _baraquement(self, x, z, couleur):
        v, k = self.v, self.k
        L, P = 24, 9
        v.boite(x, 0, z, x + L, 3, z + P, TOLE)
        v.boite(x + 1, 0, z + 1, x + L - 1, 2, z + P - 1, AIR)
        v.boite(x + 1, -1, z + 1, x + L - 1, -1, z + P - 1, 'minecraft:spruce_planks')
        # toit a deux pans en tole sombre
        for i in range(0, P // 2 + 2):
            v.boite(x - 1, 4 + i // 2, z - 1 + i, x + L + 1, 4 + i // 2, z - 1 + i, esc('dark_oak', 'south') if i % 2 == 0 else dalle('dark_oak', 'top'))
            v.boite(x - 1, 4 + i // 2, z + P + 1 - i, x + L + 1, 4 + i // 2, z + P + 1 - i, esc('dark_oak', 'north') if i % 2 == 0 else dalle('dark_oak', 'top'))
        v.boite(x, 3, z + 1, x + L, 5, z + P - 1, TOLE, seulement_air=True)
        v.boite(x + 1, 3, z + 1, x + L - 1, 4, z + P - 1, AIR)
        for xx in range(x + 3, x + L - 1, 4):
            v.pose(xx, 1, z, 'minecraft:glass_pane'); v.pose(xx, 1, z + P, 'minecraft:glass_pane')
        v.boite(x, 0, z + 4, x, 1, z + 4, AIR)
        k.porte(x, 0, z + 4, 'west', 'spruce', ouverte=True)
        v.boite(x + L, 0, z + 4, x + L, 1, z + 4, AIR)
        k.porte(x + L, 0, z + 4, 'east', 'spruce')
        # deux rangees de lits, casiers (tonneaux) en tete
        for i in range(6):
            xx = x + 2 + i * 3
            k.lit(xx, 0, z + 2, 'north', couleur)
            k.lit(xx, 0, z + P - 2, 'south', couleur)
            v.pose(xx + 1, 0, z + 1, 'minecraft:barrel[facing=up,open=false]')
        k.lanterne(x + L // 2, 2, z + P // 2)

    # ------------------------------------------------------------------ cantine
    def _cantine(self, x, z):
        v, k = self.v, self.k
        L, P = 16, 12
        v.boite(x, 0, z, x + L, 3, z + P, 'minecraft:light_blue_terracotta')
        v.boite(x + 1, 0, z + 1, x + L - 1, 2, z + P - 1, AIR)
        v.boite(x, 3, z, x + L, 3, z + P, BETON)
        v.boite(x + 1, -1, z + 1, x + L - 1, -1, z + P - 1, 'minecraft:white_terracotta')
        for xx in range(x + 2, x + L - 1, 3):
            v.boite(xx, 1, z, xx + 1, 1, z, 'minecraft:glass_pane')
        v.boite(x + 7, 0, z + P, x + 8, 1, z + P, AIR)
        k.double_porte(x + 7, 0, z + P, 'south', 'spruce', ouverte=True)
        k.longue_table(x + 2, z + 3, x + 10, z + 4, 0, 'smooth_quartz', 'spruce')
        k.longue_table(x + 2, z + 7, x + 10, z + 8, 0, 'smooth_quartz', 'spruce')
        for zz in range(z + 2, z + P - 1):
            v.pose(x + L - 2, 0, zz, 'minecraft:smoker[facing=west,lit=false]' if zz % 3 == 0 else 'minecraft:iron_block')
        v.coffre(x + L - 2, 0, z + 1, 'west', [('minecraft:bread', 20), ('minecraft:cooked_porkchop', 12), ('minecraft:apple', 10)])
        k.lampes_plafond(x + 1, z + 1, x + L - 1, z + P - 1, 2, 4, 0.2)
        self.li.ajoute('Cantine (base militaire)', self.bx + x + L // 2, self.bz + z + P // 2, 0)

    # ------------------------------------------------------------------ hangar
    def _hangar(self, x, z):
        v, k = self.v, self.k
        L, P = 30, 22
        R = P / 2
        # voute cylindrique en tole, ouverte a l'ouest, fond ferme a l'est
        for dz in range(0, P + 1):
            t = (dz - R) / R
            hh = int(round(math.sqrt(max(0.0, 1 - t * t)) * 11))
            for xx in range(x, x + L + 1):
                v.pose(xx, hh, z + dz, 'minecraft:light_gray_terracotta' if (xx - x) % 5 else 'minecraft:iron_block')
                if xx == x + L:
                    v.boite(xx, 0, z + dz, xx, hh, z + dz, 'minecraft:light_gray_terracotta')
            if dz in (0, P):
                v.boite(x, 0, z + dz, x + L, hh, z + dz, 'minecraft:light_gray_terracotta')
        v.boite(x + 1, -1, z + 1, x + L - 1, -1, z + P - 1, BETON_F)
        # dedans : un camion, des caisses, un etabli
        for i in range(8):
            for j in range(4):
                v.pose(x + 8 + i, 0, z + 9 + j, 'minecraft:green_concrete')
                v.pose(x + 8 + i, 1, z + 9 + j, 'minecraft:green_concrete' if i > 5 else ('minecraft:green_wool' if i > 1 else AIR))
        for i in range(8):
            for j in (-1, 4):
                if i in (1, 6):
                    v.pose(x + 8 + i, 0, z + 9 + j, 'minecraft:black_concrete')
        for (a, b) in ((22, 3), (23, 3), (22, 4), (24, 17), (25, 17), (24, 16)):
            v.pose(x + a, 0, z + b, 'minecraft:spruce_planks' if (a + b) % 2 else 'minecraft:barrel[facing=up,open=false]')
        v.pose(x + 22, 1, z + 3, 'minecraft:spruce_planks')
        v.pose(x + 26, 0, z + 10, 'minecraft:smithing_table')
        v.pose(x + 26, 0, z + 11, 'minecraft:anvil[facing=north]')
        v.coffre(x + 26, 0, z + 12, 'west', [('minecraft:iron_ingot', 12), ('minecraft:rail', 16), ('minecraft:minecart', 1),
                                           ('minecraft:bucket', 2), ('minecraft:lead', 3)])
        k.lampes_plafond(x + 2, z + 4, x + L - 2, z + P - 4, 9, 6, 0.4)
        self.li.ajoute('Hangar (base militaire)', self.bx + x + L // 2, self.bz + z + P // 2, 0)

    # ------------------------------------------------------------------ heliport
    def _heliport(self, x, z):
        v = self.v
        for dx in range(-8, 9):
            for dz in range(-8, 9):
                if dx * dx + dz * dz <= 64:
                    v.pose(x + dx, -1, z + dz, BETON_F)
                if 56 <= dx * dx + dz * dz <= 64:
                    v.pose(x + dx, -1, z + dz, 'minecraft:yellow_concrete')
        for d in range(-3, 4):
            v.pose(x - 2, -1, z + d, 'minecraft:white_concrete'); v.pose(x + 2, -1, z + d, 'minecraft:white_concrete')
        v.pose(x - 1, -1, z, 'minecraft:white_concrete'); v.pose(x + 1, -1, z, 'minecraft:white_concrete'); v.pose(x, -1, z, 'minecraft:white_concrete')
        # balises
        for a in range(0, 360, 45):
            px, pz = x + int(round(9 * math.cos(math.radians(a)))), z + int(round(9 * math.sin(math.radians(a))))
            v.pose(px, 0, pz, 'minecraft:lantern[hanging=false,waterlogged=false]')
        self.li.ajoute('Heliport (base militaire)', self.bx + x, self.bz + z, 0)

    # ------------------------------------------------------------------ vehicules
    def _parc_vehicules(self, x, z):
        v, li = self.v, self.li
        v.boite(x - 1, -1, z - 1, x + 22, -1, z + 12, BETON_F)
        for (i, sens, renv) in ((0, 'south', False), (6, 'south', False), (12, 'south', True)):
            li.jeep(self.bx + x + i, self.bz + z + 2, sens, renversee=renv)
        # auvent sur poteaux
        for xx in (x - 1, x + 21):
            for zz in (z, z + 10):
                v.boite(xx, 0, zz, xx, 4, zz, 'minecraft:iron_bars')
        v.boite(x - 1, 5, z, x + 21, 5, z + 10, dalle('dark_oak'))
        for i in range(5):
            v.pose(x + 18 + (i % 2), 0, z + 2 + i, 'minecraft:barrel[facing=up,open=false]')

    def _carburant(self, x, z):
        v = self.v
        for (cx, cz) in ((x + 4, z + 4), (x + 12, z + 4)):
            for y in range(0, 8):
                for dx in range(-3, 4):
                    for dz in range(-3, 4):
                        d = math.hypot(dx, dz)
                        if 2.2 < d <= 3.2 or (y in (0, 7) and d <= 3.2):
                            v.pose(cx + dx, y, cz + dz, 'minecraft:white_concrete' if y % 4 else 'minecraft:red_concrete')
            for y in range(0, 8):
                v.pose(cx + 4, y, cz, 'minecraft:ladder[facing=east,waterlogged=false]')
        # muret de retention en sacs de sable
        for dx in range(-1, 18):
            for dz in (-1, 9):
                v.pose(x + dx, 0, z + dz, SAC)
        for dz in range(-1, 10):
            for dx in (-1, 17):
                v.pose(x + dx, 0, z + dz, SAC)

    def _chateau_eau(self, x, z):
        v = self.v
        for (a, b) in ((0, 0), (5, 0), (0, 5), (5, 5)):
            v.boite(x + a, -2, z + b, x + a, 11, z + b, 'minecraft:stripped_spruce_log[axis=y]')
        v.boite(x - 1, 12, z - 1, x + 6, 17, z + 6, 'minecraft:spruce_planks')
        v.boite(x, 13, z, x + 5, 17, z + 5, 'minecraft:water[level=0]')
        v.boite(x - 1, 18, z - 1, x + 6, 18, z + 6, dalle('spruce'))
        for y in range(0, 12):
            v.pose(x + 2, y, z - 1, 'minecraft:ladder[facing=north,waterlogged=false]')
        v.boite(x + 2, 0, z, x + 2, 11, z, 'minecraft:spruce_planks')

    def _mat_radio(self, x, z):
        v = self.v
        for y in range(0, 28):
            v.pose(x, y, z, 'minecraft:iron_bars' if y % 7 else 'minecraft:iron_block')
        v.pose(x, 28, z, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
        for (dx, dz) in ((4, 0), (-4, 0), (0, 4), (0, -4)):
            for i in range(1, 9):
                v.pose(x + dx * i // 8, 26 - i * 3, z + dz * i // 8, 'minecraft:chain[axis=y,waterlogged=false]', seulement_air=True)

    def _conteneurs(self, x, z):
        v, rng = self.v, self.rng
        couleurs = ['orange', 'blue', 'green', 'red', 'white', 'brown']
        for i in range(6):
            c = 'minecraft:%s_concrete' % couleurs[i % len(couleurs)]
            cx, cz = x + (i % 3) * 8, z + (i // 3) * 5
            if i == 4:
                # renverse et eventre
                v.boite(cx, 0, cz, cx + 2, 6, cz + 2, c)
                v.boite(cx + 1, 1, cz, cx + 1, 5, cz + 1, AIR)
                continue
            v.boite(cx, 0, cz, cx + 6, 2, cz + 2, c)
            v.boite(cx + 1, 0, cz + 1, cx + 5, 1, cz + 1, AIR)
            v.boite(cx, 0, cz + 1, cx, 1, cz + 1, AIR)
            if i == 1:
                v.boite(cx + 1, 3, cz, cx + 7, 5, cz + 2, 'minecraft:blue_concrete')      # empile
            v.coffre(cx + 5, 0, cz + 1, 'west', [('minecraft:torch', 16), ('minecraft:bread', 6), ('minecraft:rope' if False else 'minecraft:string', 8),
                                                ('minecraft:iron_ingot', int(rng.integers(2, 7)))])

    def _projecteurs(self):
        v = self.v
        LX, LZ = self.LX, self.LZ
        for (x, z) in ((LX // 2 - 8, LZ // 2 - 8), (LX // 2 + 8, LZ // 2 + 8), (LX // 2 - 8, LZ // 2 + 8), (LX // 2 + 8, LZ // 2 - 8)):
            v.boite(x, 0, z, x, 5, z, 'minecraft:iron_bars')
            v.pose(x, 6, z, 'minecraft:lantern[hanging=false,waterlogged=false]')

    def _degats(self):
        """Il est entre par le nord-est : grillage arrache, sang jusqu'au hangar, sacs eventres."""
        v, k, rng = self.v, self.k, self.rng
        LX = self.LX
        pts = []
        for t in range(0, 40):
            pts.append((LX - 22 + int(t * -0.4), 0, 1 + t))
        k.sang(pts, 0.35)
        for (x, z) in ((LX - 30, 12), (LX - 26, 18)):
            v.pose(x, 0, z, SAC); v.pose(x + 1, 0, z, SAC_D)
