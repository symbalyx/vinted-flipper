"""Souterrains de la base « Kilo » : un anneau de longs couloirs sous la base, pour les poursuites.

Pense pour une scene de poursuite : des couloirs A LA TAILLE DU SPINOSAURE (5 de large, 6 de
haut ; sa boite fait 3,4 x 5) qui forment une boucle, on peut donc courir sans fin et se faire
couper la route ; des salles a porte etroite (1 ou 2 blocs) ou il n'entre pas : des refuges ; et
des puits a echelle aux quatre coins pour s'echapper par le haut.

    A (nord, 81 blocs) et C (sud, 81 blocs) : les deux grandes lignes droites
    W (ouest) et E (est) ferment la boucle ; B (centre) la coupe en deux
    Entrees a sa taille : la rampe du hangar, et l'effondrement au bout de la trainee de sang
    Entrees des joueurs : l'escalier du QG, les quatre puits

Tout est au-dessus de la nappe (sol a y0 - 9, soit 51 pour une dalle a 60, la mer est a 48) et
sous la zone protegee de la base : les grottes n'y debouchent pas, aucune eau n'y entre.

Repere : celui de la base (y = 0 au-dessus de la dalle). Sol des galeries a y = -9, on y marche
a y = -8.
"""
from mobilier import esc

AIR = 'minecraft:air'
MUR = 'minecraft:light_gray_concrete'
PLINTHE = 'minecraft:gray_concrete'
PLAFOND = 'minecraft:smooth_stone'
SOL = 'minecraft:polished_andesite'
SOL_SALLE = 'minecraft:gray_concrete'
F, S = -9, -8                      # dalle du sol, niveau de marche


class Souterrain:
    # (nom, x0, z0, x1, z1, hauteur interieure) ; x1, z1 inclus
    COULOIRS = [('A', 12, 24, 92, 28, 6), ('C', 12, 62, 92, 66, 6), ('W', 12, 24, 16, 66, 6),
                ('E', 88, 24, 92, 66, 6), ('B', 50, 21, 54, 62, 6), ('rampe', 78, 32, 87, 36, 6)]
    SALLES = [('pc', 42, 4, 63, 19, 5), ('armurerie', 20, 16, 30, 22, 4), ('dortoir', 4, 34, 10, 46, 4),
              ('generateurs', 94, 32, 101, 48, 6), ('infirmerie', 58, 68, 72, 75, 4),
              ('archives', 22, 68, 36, 75, 4), ('reserve', 76, 68, 86, 75, 4)]
    PUITS = [(10, 26), (94, 26), (10, 64), (94, 64)]

    def __init__(self, base):
        self.base, self.v, self.k, self.rng = base, base.v, base.k, base.rng

    def construire(self):
        v = self.v
        tout = self.COULOIRS + self.SALLES
        # 1) coquilles (murs, sol, plafond) puis 2) volumes : un mur commun est reperce par le voisin
        for (_, x0, z0, x1, z1, h) in tout:
            v.boite(x0 - 1, F, z0 - 1, x1 + 1, S + h, z1 + 1, MUR)
        for (nom, x0, z0, x1, z1, h) in tout:
            v.boite(x0, S, z0, x1, S + h - 1, z1, AIR)
            v.boite(x0, F, z0, x1, F, z1, SOL if nom in 'ABCEW' or nom == 'rampe' else SOL_SALLE)
            v.boite(x0, S + h, z0, x1, S + h, z1, PLAFOND)
        for (nom, x0, z0, x1, z1, h) in self.COULOIRS:
            self._habiller_couloir(nom, x0, z0, x1, z1, h)
        # portes des salles : etroites (refuges), sauf la salle des generateurs
        self._porte(51, 20, 'south', 2)                  # poste de commandement <-> B
        self._porte(25, 23, 'south', 1)                  # armurerie <-> A
        self._porte(11, 40, 'east', 1)                   # dortoir <-> W
        self._porte(65, 67, 'north', 1)                  # infirmerie <-> C
        self._porte(29, 67, 'north', 1)                  # archives <-> C
        self._porte(81, 67, 'north', 2)                  # reserve <-> C
        v.boite(93, S, 38, 93, S + 5, 42, AIR)           # generateurs : grande ouverture, il y entre
        self._rayures(93, 38, 93, 42)
        self._poste_commandement()
        self._armurerie()
        self._dortoir()
        self._generateurs()
        self._infirmerie()
        self._archives()
        self._reserve()
        self._escalier_qg()
        self._rampe_hangar()
        for (x, z) in self.PUITS:
            self._puits(x, z)
        self._effondrement()
        self._traces()
        # eclairage : quelques plafonniers marchent encore, veilleuses invisibles (pas de monstres)
        for (_, x0, z0, x1, z1, h) in tout:
            self.k.lampes_plafond(x0, z0, x1 + 1, z1 + 1, S + h, 5, 0.15)
            self.k.veilleuses(x0, z0, x1, z1, S + h - 1, 3, 3)
        b = self.base
        b.li.ajoute('Souterrains de la base (entrees : QG, rampe du hangar, effondrement, puits)',
                    b.bx + 52, b.bz + 44, 0)

    # ------------------------------------------------------------------ couloirs
    def _habiller_couloir(self, nom, x0, z0, x1, z1, h):
        v, rng = self.v, self.rng
        long_x = (x1 - x0) >= (z1 - z0)
        # plinthe sombre, ligne jaune au milieu du sol
        for x in range(x0 - 1, x1 + 2):
            for z in range(z0 - 1, z1 + 2):
                if v.get(x, S, z) != v.AIR:
                    if v.nom(v.get(x, S, z)) == MUR:
                        v.pose(x, S, z, PLINTHE)
        if long_x:
            zc = (z0 + z1) // 2
            for x in range(x0, x1 + 1):
                if v.nom(v.get(x, F, zc)) == SOL:
                    v.pose(x, F, zc, 'minecraft:yellow_terracotta')
        else:
            xc = (x0 + x1) // 2
            for z in range(z0, z1 + 1):
                if v.nom(v.get(xc, F, z)) == SOL:
                    v.pose(xc, F, z, 'minecraft:yellow_terracotta')
        # tuyaux et cables le long du plafond, contre les murs (au-dessus de sa tete)
        yt = S + h - 1
        if long_x:
            for x in range(x0, x1 + 1):
                v.pose(x, yt, z0, 'minecraft:chain[axis=x,waterlogged=false]', seulement_air=True)
                v.pose(x, yt, z1, 'minecraft:chain[axis=x,waterlogged=false]', seulement_air=True)
        else:
            for z in range(z0, z1 + 1):
                v.pose(x0, yt, z, 'minecraft:chain[axis=z,waterlogged=false]', seulement_air=True)
                v.pose(x1, yt, z, 'minecraft:chain[axis=z,waterlogged=false]', seulement_air=True)
        # le long des murs : grilles d'aeration, eclairage de secours rouge, tonneaux, fissures
        n = (x1 - x0) if long_x else (z1 - z0)
        for i in range(3, n, 6):
            for cote in (0, 1):
                if long_x:
                    x, z, zm, face = x0 + i, (z0 if cote == 0 else z1), (z0 - 1 if cote == 0 else z1 + 1), ('south' if cote == 0 else 'north')
                    mur = (x, zm)
                else:
                    x, z, xm, face = (x0 if cote == 0 else x1), z0 + i, (x0 - 1 if cote == 0 else x1 + 1), ('east' if cote == 0 else 'west')
                    mur = (xm, z)
                if v.nom(v.get(mur[0], S + 2, mur[1])) != MUR:
                    continue                                  # une porte, un croisement
                r = (i // 6 + cote) % 4
                if r == 0:
                    v.pose(mur[0], S + 3, mur[1], 'minecraft:iron_bars')
                elif r == 1:
                    v.pose(x, S + 3, z, 'minecraft:redstone_wall_torch[facing=%s,lit=true]' % face)
                elif r == 2 and rng.random() < 0.6:
                    v.pose(x, S, z, 'minecraft:barrel[facing=up,open=false]', seulement_air=True)
                else:
                    v.pose(x, S + 1, z, 'minecraft:lever[face=wall,facing=%s,powered=false]' % face, seulement_air=True)
        self.k.usure(x0 - 1, S, z0 - 1, x1 + 1, S + h - 1, z1 + 1,
                     {MUR: ['minecraft:andesite', 'minecraft:cracked_stone_bricks', 'minecraft:light_gray_terracotta']}, 0.07)
        # bandes jaunes et noires aux croisements
        for (_, a0, b0, a1, b1, _h) in self.COULOIRS:
            if (a0, b0, a1, b1) == (x0, z0, x1, z1):
                continue
            ix0, iz0, ix1, iz1 = max(x0, a0), max(z0, b0), min(x1, a1), min(z1, b1)
            if ix0 <= ix1 and iz0 <= iz1:
                self._rayures(ix0, iz0, ix1, iz1)

    def _rayures(self, x0, z0, x1, z1):
        v = self.v
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if (x, z) != (x0, z0) and not (x in (x0, x1) or z in (z0, z1)):
                    continue
                v.pose(x, F, z, 'minecraft:yellow_concrete' if (x + z) % 2 else 'minecraft:black_concrete')

    def _porte(self, x, z, facing, largeur):
        """Porte de fer ouverte percee dans le mur (x, z) ; largeur 1 ou 2 (vers +x ou +z)."""
        v, k = self.v, self.k
        dx, dz = (1, 0) if facing in ('north', 'south') else (0, 1)
        for i in range(largeur):
            v.boite(x + dx * i, S, z + dz * i, x + dx * i, S + 1, z + dz * i, AIR)
        if largeur == 2:
            k.double_porte(x, S, z, facing, 'iron', ouverte=True)
        else:
            k.porte(x, S, z, facing, 'iron', ouverte=True)
        # la lampe de secours au-dessus
        v.pose(x, S + 2, z, 'minecraft:redstone_lamp[lit=true]')

    # ------------------------------------------------------------------ salles
    def _poste_commandement(self):
        v, k = self.v, self.k
        # (42..63, 4..19) sous le QG : table des operations, consoles, baies, carte murale
        k.longue_table(46, 9, 56, 12, S, 'smooth_quartz', 'dark_oak')
        for i in range(5):
            v.pose(47 + i * 2, S + 1, 10, 'minecraft:white_carpet')
            v.pose(48 + i * 2, S + 1, 11, 'minecraft:light_blue_carpet')
        k.baie_serveur(43, S, 5, 'east', 6, 'south')
        k.baie_serveur(43, S, 13, 'east', 5, 'south')
        for x in (47, 50, 53, 56):
            k.bureau(x, S, 5, 'south', 2, 'dark_oak')
        # carte murale : laine sur le mur sud
        for x in range(46, 58):
            for y in (S + 1, S + 2, S + 3):
                v.pose(x, y, 20, 'minecraft:%s_wool' % ('green' if (x * 7 + y * 3) % 5 else 'lime'))
        v.pose(52, S + 2, 20, 'minecraft:red_wool')                     # « vous etes ici »
        v.coffre(58, S, 16, 'west', [('minecraft:map', 1), ('minecraft:compass', 1), ('minecraft:spyglass', 1),
                                     ('minecraft:ender_pearl', 2), ('minecraft:golden_apple', 1)])
        k.casiers(60, S, 5, 'west', 5, 'south')
        v.pose(45, S, 17, 'minecraft:note_block[instrument=harp,note=0,powered=false]')
        v.pose(46, S, 17, 'minecraft:jukebox[has_record=false]')

    def _armurerie(self):
        v, k = self.v, self.k
        # (20..30, 16..22) : casiers, etablis, caisses de munitions
        k.casiers(20, S, 16, 'south', 6, 'east')
        v.pose(28, S, 16, 'minecraft:grindstone[face=floor,facing=south]')
        v.pose(29, S, 16, 'minecraft:anvil[facing=east]')
        v.pose(30, S, 16, 'minecraft:smithing_table')
        v.coffre(20, S, 21, 'east', [('minecraft:crossbow', 2), ('minecraft:arrow', 64), ('minecraft:spectral_arrow', 16),
                                     ('minecraft:iron_chestplate', 1), ('minecraft:iron_leggings', 1), ('minecraft:shield', 1)])
        v.coffre(20, S, 22, 'east', [('minecraft:tnt', 8), ('minecraft:flint_and_steel', 1), ('minecraft:firework_rocket', 8)])
        for x in range(23, 29, 2):
            v.pose(x, S, 20, 'minecraft:spruce_planks'); v.pose(x, S + 1, 20, 'minecraft:barrel[facing=up,open=true]')

    def _dortoir(self):
        v, k = self.v, self.k
        # (4..10, 34..46) : lits superposes, barricade devant la porte (arrachee)
        for z in range(35, 46, 3):
            k.lit(5, S, z, 'west', 'green')
            v.pose(5, S + 1, z, 'minecraft:spruce_slab[type=bottom,waterlogged=false]')
            k.lit(9, S, z, 'east', 'green')
        v.pose(8, S, 40, 'minecraft:spruce_fence')
        v.pose(9, S, 41, 'minecraft:barrel[facing=north,open=true]')
        v.coffre(4, S, 34, 'east', [('minecraft:bread', 16), ('minecraft:cooked_beef', 8), ('minecraft:torch', 32),
                                    ('minecraft:white_bed', 1)])
        self.k.sang([(10, S, 40), (7, S, 41), (5, S, 44)], 0.6)

    def _generateurs(self):
        v = self.v
        # (94..101, 32..48) : deux groupes electrogenes, cuves, armoires ; on peut s'y cacher,
        # et il peut y entrer (grande ouverture)
        for (cz, bloc) in ((35, 'minecraft:iron_block'), (44, 'minecraft:iron_block')):
            v.boite(96, S, cz - 1, 100, S + 1, cz + 1, bloc)
            v.boite(97, S + 2, cz - 1, 99, S + 2, cz + 1, 'minecraft:blast_furnace[facing=west,lit=false]')
            v.pose(95, S, cz, 'minecraft:piston[extended=false,facing=west]')
        for z in (39, 41):
            for y in range(S, S + 4):
                v.pose(100, y, z, 'minecraft:copper_block' if y < S + 3 else 'minecraft:cut_copper')
        for z in range(32, 49, 4):
            v.pose(101, S + 2, z, 'minecraft:lever[face=wall,facing=west,powered=false]')
        v.boite(94, S + 5, 32, 101, S + 5, 48, 'minecraft:chain[axis=z,waterlogged=false]', seulement_air=True)
        v.coffre(94, S, 48, 'north', [('minecraft:redstone', 16), ('minecraft:lever', 2), ('minecraft:iron_ingot', 6)])

    def _infirmerie(self):
        v, k = self.v, self.k
        # (58..72, 68..75) : lits blancs, paillasse, armoire a pharmacie
        for x in range(59, 72, 3):
            k.lit(x, S, 74, 'north', 'white')
        k.paillasse(59, 68, 66, 69, S, 'south')
        v.pose(68, S, 68, 'minecraft:brewing_stand[has_bottle_0=true,has_bottle_1=false,has_bottle_2=false]')
        v.pose(69, S, 68, 'minecraft:cauldron')
        v.coffre(71, S, 68, 'south', [('minecraft:golden_apple', 2), ('minecraft:honey_bottle', 3), ('minecraft:bread', 6),
                                      ('minecraft:milk_bucket', 1)])
        k.sang([(65, S, 67), (64, S, 70), (62, S, 72), (60, S, 73)], 0.7)

    def _archives(self):
        v, k = self.v, self.k
        # (22..36, 68..75) : rayonnages, lutrin, table de cartographie
        for x in (23, 27, 31, 35):
            k.etagere(x, S, 70, 5, 'south', 3, 'bookshelf')
        v.pose(25, S, 69, 'minecraft:lectern[facing=north,has_book=false,powered=false]')
        v.pose(33, S, 69, 'minecraft:cartography_table')
        v.coffre(36, S, 75, 'west', [('minecraft:paper', 24), ('minecraft:map', 2), ('minecraft:writable_book', 1)])

    def _reserve(self):
        v, k = self.v, self.k
        # (76..86, 68..75) : vivres, caisses, un coffre de secours
        k.casiers(76, S, 72, 'east', 4, 'south')
        for x in range(79, 86, 2):
            for z in (70, 73):
                v.pose(x, S, z, 'minecraft:barrel[facing=up,open=false]')
                if x % 4 == 1:
                    v.pose(x, S + 1, z, 'minecraft:barrel[facing=up,open=false]')
        v.coffre(86, S, 75, 'west', [('minecraft:cooked_porkchop', 16), ('minecraft:bread', 16), ('minecraft:torch', 16),
                                     ('minecraft:iron_pickaxe', 1)])

    # ------------------------------------------------------------------ acces
    def _escalier_qg(self):
        """Escalier de 2 de large depuis le rez du QG (x 62-63, z 10) jusqu'au poste de commandement."""
        v = self.v
        for k in range(8):
            z = 11 + k
            for x in (62, 63):
                v.pose(x, -2 - k, z, esc('stone_brick', 'north'))
                v.boite(x, -1 - k, z, x, min(2 - k, 3), z, AIR)
        for z in range(11, 16):
            v.pose(61, 0, z, 'minecraft:iron_bars'); v.pose(64, 0, z, 'minecraft:iron_bars')

    def _rampe_hangar(self):
        """Rampe de 5 de large dans le hangar (x 70-77, z 32-36), vers le tunnel qui rejoint E."""
        v = self.v
        for k in range(8):
            x = 70 + k
            for z in range(32, 37):
                v.pose(x, -2 - k, z, esc('polished_andesite', 'west'))
                v.boite(x, -1 - k, z, x, -1, z, AIR)
            v.boite(x, F, 31, x, -1, 31, MUR)
            v.boite(x, F, 37, x, -1, 37, MUR)
            v.pose(x, 0, 31, 'minecraft:iron_bars'); v.pose(x, 0, 37, 'minecraft:iron_bars')
        self._rayures(70, 32, 70, 36)

    def _puits(self, x, z):
        """Puits a echelle d'un coin de la boucle jusqu'a un abri en beton en surface."""
        v = self.v
        cote = 'east' if x < 50 else 'west'           # l'echelle regarde vers le couloir
        dx = 1 if x < 50 else -1
        v.boite(x - 1, F, z - 1, x + 1, 3, z + 1, 'minecraft:gray_concrete')
        v.boite(x, S, z, x, 2, z, AIR)
        for y in range(S, 1):
            v.pose(x, y, z, 'minecraft:ladder[facing=%s,waterlogged=false]' % cote)
        v.boite(x + dx, S, z, x + dx, S + 1, z, AIR)          # passage vers le couloir
        # l'abri : ouverture cote couloir en surface, toit en dalle
        v.boite(x + dx, 0, z, x + dx, 1, z, AIR)
        v.pose(x, 3, z, 'minecraft:smooth_stone_slab[type=bottom,waterlogged=false]')
        v.pose(x, 2, z, 'minecraft:lantern[hanging=true,waterlogged=false]')

    def _effondrement(self):
        """Le toit du couloir A s'est effondre au bout de la trainee de sang (x 72-78, z 16-23) :
        un talus d'eboulis descend de la surface au couloir. Il est entre par la."""
        v, rng = self.v, self.rng
        # que du naturel : sur un bloc « ouvrage » (brique, poli...), son pas tombe a 0,6 bloc et
        # il ne monterait plus ce talus a marches d'un bloc
        eboulis = ['minecraft:cobblestone', 'minecraft:gravel', 'minecraft:andesite', 'minecraft:coarse_dirt',
                   'minecraft:tuff']
        for z in range(15, 24):
            w = min(0, S + (24 - z))                          # niveau de marche : 0 en haut, -7 en bas
            for x in range(71, 80):
                bord = x in (71, 79) or z == 15
                for y in range(F, w):
                    v.pose(x, y, z, eboulis[int(rng.integers(0, len(eboulis)))])
                top = 3 if not bord else 1
                v.boite(x, w, z, x, top, z, AIR)
                if bord and rng.random() < 0.5:
                    v.pose(x, w, z, eboulis[int(rng.integers(0, len(eboulis)))])
        # le plafond de A casse autour du trou, des blocs tombes dans le couloir
        for x in range(70, 81):
            for z in range(24, 27):
                if rng.random() < 0.35:
                    v.pose(x, S + 6, z, AIR)
            if rng.random() < 0.3:
                v.pose(x, S, 24 + int(rng.integers(0, 2)), eboulis[int(rng.integers(0, len(eboulis)))])
        for (x, z) in ((70, 14), (80, 14), (69, 17), (81, 19)):
            v.pose(x, 0, z, 'minecraft:iron_bars')
            v.pose(x, 0, z + 1, eboulis[int(rng.integers(0, len(eboulis)))])

    def _traces(self):
        """La trainee de sang continue sous terre : du bas de l'effondrement aux generateurs."""
        k = self.k
        k.sang([(75, S, 24), (82, S, 26), (90, S, 30), (90, S, 38), (96, S, 40), (99, S, 45)], 0.55)
