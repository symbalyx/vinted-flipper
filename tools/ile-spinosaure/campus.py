"""Le campus de recherche « Site B » : plusieurs batiments aux volumes et materiaux differents,
avec interieurs amenages.

Repere local : x vers l'est, z vers le sud, y = 0 au niveau du rez-de-chaussee (on marche a y=0,
la dalle est a y=-1). Emprise : x 0..140, z 0..124. L'eau (mer, riviere, enclos, sous-sol) est
a y = -5.

  enclos S-01 (x 18..98, z 0..36) ........... bassin, ile interieure, breche au nord, grue
  galerie sous-marine (x 36..78, z 37..47) ... sous le parvis, vitre sur le bassin
  centre d'accueil (x 34..82, z 46..84) ...... atrium, squelette, mezzanine, charpente a deux pans
  aile des laboratoires (x 88..126, z 40..76)  2 niveaux + sous-sol noye + toit technique
  tour technique (x 127..133, z 40..48) ...... reservoir d'eau
  loge du personnel (x 0..31, z 46..84) ...... cantine, cuisine, 12 chambres, toit de cuivre
  centrale (x 0..18, z 16..42) ............... generateurs, cheminee, cuves
  parvis, parking, route, portail, cloture ... z 84..124

Le spinosaure (3,4 x 5 blocs) entre dans l'atrium (facade brisee), le sous-sol noye (tunnel
depuis le bassin), l'enclos et la galerie. Il n'entre pas dans les couloirs (2 blocs) ni les
pieces : on y est a l'abri... tant qu'on ne longe pas les vitres."""
import math

from mobilier import Kit, esc, dalle, trappe, DIRS, OPP

EAU = 'minecraft:water[level=0]'
AIR = 'minecraft:air'
Y_EAU = -5


class Campus:
    def __init__(self, v, foret=None):
        """v : Decale (repere local). foret : Foret en coordonnees absolues (optionnelle)."""
        self.v = v
        self.k = Kit(v, v.rng)
        self.rng = v.rng
        self.foret = foret

    # raccourcis
    def b(self, *a, **k):
        self.v.boite(*a, **k)

    def p(self, *a, **k):
        self.v.pose(*a, **k)

    def construire(self, chenal_nord=0):
        self.terrassement()
        self.enclos(chenal_nord)
        self.galerie()
        self.centre_accueil()
        self.aile_labos()
        self.loge()
        self.centrale()
        self.exterieurs()
        self.belvedere(18, 96)

    # ================================================================ terrain
    def terrassement(self):
        """Plate-forme du campus : sol a y=-1, fondations dessous, air au-dessus."""
        b = self.b
        b(-6, -12, -2, 145, -2, 127, 'minecraft:dirt')
        b(-6, -1, -2, 145, -1, 127, 'minecraft:grass_block[snowy=false]')
        b(-6, 0, -2, 145, 40, 127, AIR)

    # ================================================================ enclos
    def enclos(self, chenal_nord):
        b, p, rng, k = self.b, self.p, self.rng, self.k
        # murs : beton coule, pilastres, couronnement ; mur sud bas surmonte d'une cloture electrique
        b(18, -13, 0, 98, 12, 36, 'minecraft:smooth_stone')
        b(20, -12, 2, 96, 40, 34, AIR)
        b(20, -13, 2, 96, -13, 34, 'minecraft:mud')
        b(20, -12, 2, 96, Y_EAU, 34, EAU)
        # ile interieure : berge en pente douce au nord, sol de jungle
        for z in range(2, 20):
            haut = -1 if z < 12 else int(-1 - (z - 11) * 1.4)
            b(20, -12, z, 96, haut, z, 'minecraft:dirt')
            b(20, haut, z, 96, haut, z, 'minecraft:grass_block[snowy=false]' if haut >= Y_EAU else 'minecraft:mud')
            if haut < Y_EAU:
                b(20, haut + 1, z, 96, Y_EAU, z, EAU)
        # pilastres exterieurs et couronnement
        for x in range(18, 99, 8):
            b(x, 0, -1, x + 1, 12, -1, 'minecraft:stone_bricks')
        for z in range(0, 37, 8):
            b(17, 0, z, 17, 12, z + 1, 'minecraft:stone_bricks')
            b(99, 0, z, 99, 12, z + 1, 'minecraft:stone_bricks')
        b(18, 13, 0, 98, 13, 1, dalle('smooth_stone'))
        b(18, 13, 0, 19, 13, 36, dalle('smooth_stone'))
        b(97, 13, 0, 98, 13, 36, dalle('smooth_stone'))
        # mur sud bas (y 0..4) + barreaux electrifies (y 5..10) + poteaux
        b(20, 5, 35, 96, 13, 36, AIR)
        b(18, 5, 35, 98, 5, 36, dalle('smooth_stone'))
        for x in range(18, 99):
            if x % 6 == 0:
                b(x, 5, 35, x, 11, 35, 'minecraft:polished_andesite')
                p(x, 12, 35, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
            else:
                b(x, 6, 35, x, 10, 35, 'minecraft:iron_bars')
        b(40, 6, 35, 45, 10, 35, AIR)                       # barreaux arraches
        # traces : fissures, mousse en pied de mur
        k.usure(17, -13, -1, 99, 12, 37, {'minecraft:smooth_stone': ['minecraft:andesite', 'minecraft:cobblestone',
                                                                        'minecraft:mossy_cobblestone']}, 0.05)
        k.usure(17, -13, -1, 99, 12, 37, {'minecraft:stone_bricks': ['minecraft:cracked_stone_bricks',
                                                                        'minecraft:mossy_stone_bricks']}, 0.3)
        # la breche au nord : mur eventre, gravats, ouverte sur le chenal
        b(50, -12, 0, 60, 13, 1, AIR)
        b(50, -12, 0, 60, Y_EAU, 1, EAU)
        for _ in range(40):
            x = int(rng.integers(46, 65)); z = int(rng.integers(-3, 5)); y = int(rng.integers(-12, -6))
            p(x, y, z, ['minecraft:cobblestone', 'minecraft:smooth_stone', 'minecraft:mossy_cobblestone'][rng.integers(0, 3)])
        for y in range(-2, 13):
            for x in (49, 61):
                if rng.random() < 0.6:
                    p(x, y, int(rng.integers(0, 2)), 'minecraft:cracked_stone_bricks')
        if chenal_nord:
            b(48, -12, -chenal_nord, 62, -12, -1, 'minecraft:mud')
            b(48, -11, -chenal_nord, 62, Y_EAU, -1, EAU)
            b(48, Y_EAU + 1, -chenal_nord, 62, 20, -1, AIR)
        # panneau d'avertissement sur le mur sud (cote campus)
        self.v.panneau(58, 3, 37, 'south', ['ENCLOS S-01', 'SPINOSAURUS', 'NE PAS NOURRIR', 'A LA MAIN'])
        # grue d'alimentation : mat sur le mur ouest, fleche au-dessus de l'eau, cage qui pend
        b(22, 0, 26, 23, 22, 27, 'minecraft:iron_block')
        for x in range(22, 44):
            p(x, 22, 26, 'minecraft:iron_bars'); p(x, 22, 27, 'minecraft:iron_bars')
            p(x, 23, 26 + (x % 2), dalle('smooth_stone'))
        for y in range(12, 22):
            p(42, y, 26, 'minecraft:chain[axis=y,waterlogged=false]')
        # cage a moitie immergee, porte arrachee
        for x in range(40, 45):
            for z in range(24, 29):
                for y in range(Y_EAU - 1, 12):
                    bord = x in (40, 44) or z in (24, 28)
                    if bord and (y in (Y_EAU - 1, 11) or (x + z) % 2 == 0):
                        p(x, y, z, 'minecraft:iron_bars')
        b(42, 2, 28, 43, 8, 28, AIR)
        # un peu de jungle sur l'ile interieure
        if self.foret is not None:
            f, ox, oz = self.foret, self.v.ox, self.v.oz
            for (x, z) in ((30, 6), (44, 8), (72, 5), (86, 9)):
                f.canopee(ox + x, oz + z, h=int(rng.integers(13, 18)))
            for (x, z) in ((36, 12), (62, 10), (78, 12), (90, 4)):
                f.buisson(ox + x, oz + z)

    # ================================================================ galerie sous-marine
    def galerie(self):
        b, p, k = self.b, self.p, self.k
        b(34, -12, 37, 80, -3, 48, 'minecraft:stone_bricks')
        b(36, -11, 38, 78, -5, 46, AIR)
        b(36, -12, 38, 78, -12, 46, 'minecraft:polished_deepslate')
        b(36, -4, 38, 78, -4, 46, 'minecraft:smooth_stone')
        # la vitre : tout le mur entre le bassin et la galerie
        b(38, -12, 35, 76, -5, 37, 'minecraft:glass')
        b(38, -12, 35, 76, -12, 36, 'minecraft:smooth_stone')
        for x in range(38, 77, 6):
            b(x, -11, 37, x, -5, 37, 'minecraft:polished_deepslate')
        # banquettes, eclairage bleu, panneaux
        for x in range(42, 74, 6):
            b(x, -11, 43, x + 2, -11, 43, esc('dark_oak', 'south'))
        for x in range(40, 76, 8):
            p(x, -4, 41, 'minecraft:sea_lantern')
        k.veilleuses(36, 38, 78, 46, -10, 3, 3)
        self.v.panneau(57, -9, 46, 'north', ['GALERIE', "D'OBSERVATION", 'Il vous voit', 'aussi.'])
        self.v.panneau(47, -9, 46, 'north', ['17 h 40 : il a', 'tape la vitre.', 'Deux fois.', ''])
        # escalier vers le centre d'accueil (angle nord-ouest de l'atrium)
        b(36, -11, 47, 38, -1, 58, 'minecraft:stone_bricks')
        for i in range(10):
            z = 57 - i
            y = -1 - i
            b(36, y, z, 38, y, z, esc('polished_deepslate', 'south'))
            b(36, y + 1, z, 38, y + 4, z, AIR)
        b(36, -10, 47, 38, -6, 47, AIR)
        b(36, -1, 48, 38, -1, 58, AIR)
        b(35, -1, 48, 35, 0, 58, 'minecraft:smooth_sandstone')
        b(39, -1, 48, 39, 0, 58, 'minecraft:smooth_sandstone')
        for z in range(48, 59):
            p(39, 1, z, 'minecraft:glass_pane')

    # ================================================================ centre d'accueil
    def centre_accueil(self):
        b, p, k, rng, v = self.b, self.p, self.k, self.rng, self.v
        X0, X1, Z0, Z1 = 34, 82, 46, 84
        # coque
        b(X0, -1, Z0, X1, -1, Z1, 'minecraft:polished_granite')
        b(X0, 0, Z0, X1, 1, Z1, 'minecraft:stone_bricks')
        b(X0, 2, Z0, X1, 13, Z1, 'minecraft:smooth_sandstone')
        b(X0 + 1, 0, Z0 + 1, X1 - 1, 30, Z1 - 1, AIR)
        b(X0, 14, Z0, X1, 14, Z1, 'minecraft:cut_sandstone')
        b(X0 + 1, 14, Z0 + 1, X1 - 1, 14, Z1 - 1, AIR)
        # sol : bordure claire et medaillon autour du squelette
        b(X0 + 1, -1, Z0 + 1, X1 - 1, -1, Z1 - 1, 'minecraft:polished_granite')
        b(X0 + 2, -1, Z0 + 2, X1 - 2, -1, Z0 + 2, 'minecraft:smooth_sandstone')
        b(X0 + 2, -1, Z1 - 2, X1 - 2, -1, Z1 - 2, 'minecraft:smooth_sandstone')
        for x in range(X0 + 1, X1):
            for z in range(Z0 + 1, Z1):
                d = math.hypot((x - 58) / 1.6, z - 72)
                if 7.5 < d < 8.6 or 10.5 < d < 11.4:
                    p(x, -1, z, 'minecraft:terracotta')
        # pilastres de charpente (bois) sur toutes les faces, cordon, corniche
        for x in range(X0, X1 + 1, 6):
            for z in (Z0 - 1, Z1 + 1):
                b(x, 0, z, x, 14, z, 'minecraft:stripped_jungle_log[axis=y]')
        for z in range(Z0, Z1 + 1, 6):
            for x in (X0 - 1, X1 + 1):
                b(x, 0, z, x, 14, z, 'minecraft:stripped_jungle_log[axis=y]')
        for x in range(X0 - 1, X1 + 2):
            p(x, 14, Z0 - 1, esc('smooth_sandstone', 'south', 'top')); p(x, 14, Z1 + 1, esc('smooth_sandstone', 'north', 'top'))
            p(x, 2, Z0 - 1, dalle('cut_sandstone')); p(x, 2, Z1 + 1, dalle('cut_sandstone'))
        for z in range(Z0 - 1, Z1 + 2):
            p(X0 - 1, 14, z, esc('smooth_sandstone', 'east', 'top')); p(X1 + 1, 14, z, esc('smooth_sandstone', 'west', 'top'))
        # facade sud : grande verriere a meneaux et traverses de bois
        for x in range(X0 + 1, X1):
            if (x - X0) % 6 == 0:
                continue
            for y in range(2, 13):
                bois = y in (6, 10)
                p(x, y, Z1, 'minecraft:stripped_jungle_log[axis=x]' if bois else 'minecraft:glass_pane')
        # autres faces : deux bandeaux de fenetres a appuis
        for (xa, xb, za, zb) in ((X0 + 1, X1 - 1, Z0, Z0), (X0, X0, Z0 + 1, Z1 - 1), (X1, X1, Z0 + 1, Z1 - 1)):
            for x in range(xa, xb + 1):
                for z in range(za, zb + 1):
                    t = (x - X0) if za == zb else (z - Z0)
                    if t % 6 in (2, 3, 4):
                        b(x, 3, z, x, 5, z, 'minecraft:glass_pane')
                        b(x, 9, z, x, 12, z, 'minecraft:glass_pane')
        # entree : portique a colonnes, marquise, facade eventree
        for x in (49, 54, 62, 67):
            b(x, 0, 86, x, 8, 86, 'minecraft:quartz_pillar[axis=y]')
            b(x, 0, 90, x, 8, 90, 'minecraft:quartz_pillar[axis=y]')
        b(47, 9, 85, 69, 9, 91, 'minecraft:smooth_quartz')
        b(47, 10, 85, 69, 10, 91, dalle('smooth_quartz'))
        for x in range(47, 70):
            p(x, 9, 92, esc('smooth_quartz', 'north', 'top'))
        self.v.panneau(58, 8, 92, 'south', ['SITE B', 'Centre de recherche', 'et d\'accueil', ''])
        b(54, -1, 85, 62, -1, 91, 'minecraft:polished_andesite')
        # la breche : 7 blocs de large sur 9 de haut, verre et chambranle arraches
        b(55, 0, Z1 - 1, 61, 8, Z1 + 1, AIR)
        for y in range(0, 9):
            for x in (54, 62):
                if rng.random() < 0.5:
                    p(x, y, Z1, AIR)
        k.porte(53, 0, Z1, 'south', 'dark_oak', 'left', ouverte=True)
        self.p(53, 1, Z1 + 1, 'minecraft:air')
        # griffures sur le chambranle
        for y in range(2, 9):
            p(63, y, Z1 + 1, 'minecraft:cracked_stone_bricks' if y < 2 else AIR)
        # ------------------------------------------------ toiture a deux pans (faitage est-ouest)
        ZA, ZB = Z0 - 2, Z1 + 2
        for z in range(ZA, ZB + 1):
            d = min(z - ZA, ZB - z)
            y = 14 + d // 2
            nord = z - ZA < ZB - z
            if abs((z - ZA) - (ZB - z)) <= 1:
                b(X0 - 2, y, z, X1 + 2, y, z, dalle('spruce', 'bottom' if d % 2 == 0 else 'top'))
                b(X0 - 2, y + (0 if d % 2 else 1), z, X1 + 2, y + (0 if d % 2 else 1), z, dalle('spruce'))
                continue
            etat = esc('spruce', 'south' if nord else 'north') if d % 2 == 0 else dalle('spruce', 'top')
            b(X0 - 2, y, z, X1 + 2, y, z, etat)
            # verriere de faitage
            if d >= 17 and d % 2 == 1:
                b(X0 + 4, y, z, X1 - 4, y, z, 'minecraft:glass')
            # pignons : pan de bois et grand vitrage triangulaire
            if z > Z0 - 1 and z < Z1 + 1:
                for x in (X0, X1):
                    b(x, 15, z, x, y - 1, z, 'minecraft:glass_pane' if z % 4 else 'minecraft:stripped_jungle_log[axis=y]')
                    p(x, y - 1, z, 'minecraft:stripped_jungle_log[axis=z]')
        # fermes de charpente apparentes, tous les 6 blocs
        for x in range(X0 + 3, X1, 6):
            b(x, 14, Z0 + 1, x, 14, Z1 - 1, 'minecraft:stripped_dark_oak_log[axis=z]')
            for z in range(Z0 + 1, Z1):
                d = min(z - ZA, ZB - z)
                if d % 4 == 0:
                    b(x, 15, z, x, 14 + d // 2 - 1, z, 'minecraft:stripped_dark_oak_log[axis=y]')
        # un pan de toit effondre : un arbre est tombe dessus
        for x in range(70, 78):
            for z in range(Z0 - 2, Z0 + 12):
                d = min(z - ZA, ZB - z)
                if rng.random() < 0.85:
                    p(x, 14 + d // 2, z, AIR)
        if self.foret is not None:
            ox, oz, oy = self.v.ox, self.v.oz, self.v.oy
            self.v.ligne((73, 6, 50), (79, 30, 30), lambda axe: 'minecraft:jungle_log[axis=%s]' % axe, epaisseur=1.0)
            from arbres import F_JUNGLE
            self.foret.P(F_JUNGLE)
            self.v.ellipsoide(80, 31, 28, 5, 2.5, 5, F_JUNGLE, bruit=0.5)
            self.v.ellipsoide(73, 7, 52, 3, 1.5, 3, F_JUNGLE, bruit=0.6)
        # ------------------------------------------------ mezzanine (dalle y=6, on marche a y=7)
        MZ = 6
        b(X0 + 1, MZ, Z0 + 1, X1 - 1, MZ, Z0 + 9, 'minecraft:spruce_planks')
        b(X0 + 1, MZ, Z0 + 10, X0 + 5, MZ, Z1 - 10, 'minecraft:spruce_planks')
        b(X1 - 5, MZ, Z0 + 10, X1 - 1, MZ, Z1 - 10, 'minecraft:spruce_planks')
        b(36, MZ, 48, 38, MZ, 58, 'minecraft:spruce_planks')
        for x in range(X0 + 1, X1):
            p(x, MZ + 1, Z0 + 10, 'minecraft:glass_pane')
            p(x, MZ - 1, Z0 + 9, esc('spruce', 'north', 'top'))
        for z in range(Z0 + 10, Z1 - 9):
            p(X0 + 6, MZ + 1, z, 'minecraft:glass_pane'); p(X1 - 6, MZ + 1, z, 'minecraft:glass_pane')
        for x in range(X0 + 6, X1 - 5, 6):
            b(x, 0, Z0 + 9, x, MZ - 1, Z0 + 9, 'minecraft:stripped_jungle_log[axis=y]')
        for z in range(Z0 + 15, Z1 - 9, 6):
            b(X0 + 5, 0, z, X0 + 5, MZ - 1, z, 'minecraft:stripped_jungle_log[axis=y]')
            b(X1 - 5, 0, z, X1 - 5, MZ - 1, z, 'minecraft:stripped_jungle_log[axis=y]')
        # grand escalier vers la mezzanine nord (5 de large, 7 marches)
        for i in range(7):
            z, y = 64 - i, i - 1
            b(56, 0, z, 60, y, z, 'minecraft:spruce_planks')
            if y >= 0:
                b(56, y, z, 60, y, z, esc('spruce', 'north'))
            b(56, y + 1, z, 60, MZ + 3, z, AIR)
        b(56, MZ, 56, 60, MZ, 57, 'minecraft:spruce_planks')
        b(56, MZ + 1, 56, 60, MZ + 4, 57, AIR)
        b(56, MZ + 1, Z0 + 10, 60, MZ + 1, Z0 + 10, AIR)
        for i in range(8):
            p(55, i, 64 - i, 'minecraft:glass_pane'); p(61, i, 64 - i, 'minecraft:glass_pane')
        # ------------------------------------------------ squelette de spinosaure (os et tiges)
        self.squelette(58, 72)
        # ------------------------------------------------ accueil (comptoir en arc) a l'ouest
        for i, (x, z) in enumerate(((42, 66), (41, 67), (41, 68), (41, 69), (41, 70), (42, 71), (43, 72), (44, 72))):
            p(x, 0, z, 'minecraft:smooth_quartz')
            p(x, 1, z, dalle('dark_oak'))
        k.bureau(43, 0, 69, 'west', 2)
        p(43, 1, 67, 'minecraft:black_stained_glass_pane')
        v.panneau(44, 1, 73, 'south', ['ACCUEIL', 'Visiteurs :', 'badge obligatoire', ''])
        # ------------------------------------------------ cafe sous la mezzanine (ouest)
        for x in range(40, 53):
            p(x, 0, 48, 'minecraft:smooth_quartz'); p(x, 1, 48, dalle('smooth_quartz'))
        p(42, 1, 48, 'minecraft:brewing_stand[has_bottle_0=true,has_bottle_1=true,has_bottle_2=false]')
        p(45, 1, 48, 'minecraft:water_cauldron[level=2]'); p(48, 1, 48, 'minecraft:smoker[facing=south,lit=false]')
        for (x, z) in ((42, 52), (47, 51), (52, 53), (44, 55)):
            k.table(x, 0, z, 'dark_oak', 'white')
            for d in ('north', 'south', 'east', 'west'):
                dx, dz = DIRS[d]
                if rng.random() < 0.7:
                    k.chaise(x + dx, 0, z + dz, OPP[d])
        p(47, 0, 51, esc('dark_oak', 'east', 'top'))          # une table renversee
        # ------------------------------------------------ boutique sous la mezzanine (est)
        for x in range(64, 81, 4):
            k.etagere(x, 0, 48, 2, 'east', 3)
            k.etagere(x, 0, 52, 2, 'east', 2, 'barrel[facing=up,open=false]')
        for x in range(65, 80, 5):
            p(x, 2, 52, 'minecraft:decorated_pot[cracked=false,facing=south,waterlogged=false]')
        v.panneau(66, 3, 55, 'south', ['BOUTIQUE', '', 'Peluches, fossiles,', 'cartes de l\'ile'])
        # ------------------------------------------------ expo sur la mezzanine
        for x in range(38, 79, 5):
            if 55 <= x <= 61:
                continue
            p(x, MZ + 1, 49, 'minecraft:smooth_quartz'); p(x, MZ + 2, 49, 'minecraft:glass')
            p(x, MZ + 1, 53, 'minecraft:smooth_quartz'); p(x, MZ + 2, 53, ['minecraft:bone_block[axis=y]',
                                                                          'minecraft:orange_stained_glass',
                                                                          'minecraft:sniffer_egg[hatch=0]'][x % 3])
        v.panneau(58, MZ + 3, Z0 + 1, 'south', ['SPINOSAURUS', 'aegyptiacus', '15 m, 7 tonnes,', 'semi-aquatique'])
        v.panneau(46, MZ + 2, Z0 + 1, 'south', ['Il chasse depuis', "l'eau. Il attend", 'que la proie', 'se retourne.'])
        # sorties : ouest (loge), nord-ouest (galerie), passerelle est vers les labos (mezzanine)
        k.double_porte(X0, 0, 64, 'west', 'spruce', ouverte=False)
        b(X1, MZ + 1, 60, X1, MZ + 3, 61, AIR)
        # ------------------------------------------------ ambiance : sang, banderole tombee, toiles, lumieres
        k.sang([(58, 0, 83), (58, 0, 78), (50, 0, 76), (44, 0, 74)])
        k.sang([(44, 0, 64), (46, 0, 58), (50, 0, 54)], 0.5)
        p(45, 0, 74, 'minecraft:skeleton_skull[rotation=6]')
        for x in range(50, 67):
            p(x, 0, 77 + (x % 3 == 0), 'minecraft:white_carpet' if x % 5 else 'minecraft:red_carpet', seulement_air=True)
        for (x, z) in ((37, 81), (79, 81), (37, 76), (79, 76)):
            k.plante(x, 0, z, True)
        p(37, 1, 76, 'minecraft:air'); p(37, 0, 76, 'minecraft:rooted_dirt')    # bac renverse
        k.toiles(X0 + 1, 0, Z0 + 1, X1 - 1, 13, Z1 - 1, 30)
        for (x, z, f) in ((X0 + 1, 60, 'east'), (X1 - 1, 70, 'west'), (58, Z0 + 1, 'south')):
            k.torche_murale(x, 4, z, f, rouge=True)
        k.lampes_plafond(X0 + 2, Z0 + 11, X1 - 2, Z1 - 2, 13, 8, 0.0)
        k.veilleuses(X0 + 1, Z0 + 1, X1 - 1, Z1 - 1, 0, 3, 3)
        k.veilleuses(X0 + 1, Z0 + 1, X1 - 1, Z0 + 9, MZ + 1, 3, 3)
        k.lierre(X0, X1, Z1 + 2, Z1 + 2, 13, 3, 25, 'north')
        k.lierre(X0 - 2, X0 - 2, Z0, Z1, 13, 3, 18, 'east')

    def squelette(self, cx, cz):
        """Squelette monte de spinosaure, tete a l'est : socle, pattes, colonne, crane allonge,
        voile de longues epines (tiges), cotes."""
        b, p = self.b, self.p
        b(cx - 9, 0, cz - 3, cx + 9, 0, cz + 3, 'minecraft:polished_andesite')
        b(cx - 8, 1, cz - 2, cx + 8, 1, cz + 2, dalle('polished_andesite'))
        os_ = 'minecraft:bone_block[axis=%s]'
        # pattes arriere (fortes), avant (courtes, levees)
        for dz in (-1, 1):
            b(cx - 2, 2, cz + dz, cx - 2, 5, cz + dz, os_ % 'y')
            p(cx - 1, 2, cz + dz, os_ % 'x')
            b(cx + 4, 5, cz + dz, cx + 4, 6, cz + dz, os_ % 'y')
            p(cx + 5, 4, cz + dz, 'minecraft:end_rod[facing=down]')
        # colonne : de la queue (ouest, basse) au cou (est, releve)
        prof = {-12: 3, -11: 3, -10: 4, -9: 4, -8: 5, -7: 5, -6: 6, -5: 6, -4: 6, -3: 7, -2: 7, -1: 7, 0: 7, 1: 7,
                2: 7, 3: 7, 4: 7, 5: 8, 6: 9, 7: 10, 8: 10}
        for dx, y in prof.items():
            p(cx + dx, y, cz, os_ % 'x')
        # queue qui retombe jusqu'au sol, hors du socle
        for i, (dx, y) in enumerate(((-13, 2), (-14, 2), (-15, 1))):
            p(cx + dx, y, cz + (i > 1), os_ % 'x')
        # voile : epines de hauteur en cloche, du bassin aux epaules
        for dx in range(-7, 5):
            h = int(round(7 * math.exp(-((dx + 1.5) / 4.2) ** 2)))
            for y in range(prof[dx] + 1, prof[dx] + 1 + h):
                p(cx + dx, y, cz, 'minecraft:end_rod[facing=up]')
        # cotes
        for dx in range(-3, 4, 2):
            for dz in (-1, 1):
                p(cx + dx, 6, cz + dz, 'minecraft:end_rod[facing=down]')
                p(cx + dx, 5, cz + dz * 1, 'minecraft:end_rod[facing=down]')
        # crane : long museau de crocodile, machoire entrouverte
        for dx in range(9, 14):
            p(cx + dx, 10, cz, os_ % 'x')
        for dx in range(9, 13):
            p(cx + dx, 9 if dx < 11 else 8, cz, dalle('smooth_quartz', 'top') if dx >= 11 else os_ % 'x')
        p(cx + 9, 11, cz, os_ % 'y')
        p(cx + 14, 10, cz, 'minecraft:end_rod[facing=east]')

    # ================================================================ aile des laboratoires
    def aile_labos(self):
        b, p, k, rng, v = self.b, self.p, self.k, self.rng, self.v
        X0, X1, Z0 = 88, 126, 40
        ZR, ZE = 72, 76          # facade sud du RDC, de l'etage (porte-a-faux sur pilotis)
        E1 = 6                   # dalle de l'etage (on y marche a y=7)
        TOIT = 12
        blanc, gris, vitre = 'minecraft:white_concrete', 'minecraft:light_gray_concrete', 'minecraft:light_blue_stained_glass_pane'
        # --------------------------------------------- sous-sol noye (y -11..-2)
        b(X0, -12, Z0, X1, -1, ZR, 'minecraft:stone_bricks')
        b(X0 + 1, -11, Z0 + 1, X1 - 1, -2, ZR - 1, AIR)
        b(X0 + 1, -11, Z0 + 1, X1 - 1, Y_EAU, ZR - 1, EAU)
        b(X0 + 1, -12, Z0 + 1, X1 - 1, -12, ZR - 1, 'minecraft:smooth_stone')
        for x in range(X0 + 6, X1 - 3, 8):
            for z in range(Z0 + 6, ZR - 3, 8):
                b(x, -11, z, x + 1, -2, z + 1, 'minecraft:polished_andesite')
        # passerelles de 2 sur le pourtour (dalles hautes immergees : on marche a y=-4)
        cat = dalle('spruce', 'top').replace('waterlogged=false', 'waterlogged=true')
        b(X0 + 1, Y_EAU, Z0 + 1, X1 - 1, Y_EAU, Z0 + 2, cat)
        b(X0 + 1, Y_EAU, ZR - 2, X1 - 1, Y_EAU, ZR - 1, cat)
        b(X1 - 2, Y_EAU, Z0 + 1, X1 - 1, Y_EAU, ZR - 1, cat)
        b(X0 + 1, Y_EAU, Z0 + 1, X0 + 2, Y_EAU, ZR - 1, cat)
        for x in range(X0 + 3, X1 - 2):
            if x % 3 == 0:
                p(x, -4, Z0 + 3, 'minecraft:chain[axis=y,waterlogged=false]')
        # salle des generateurs, au sec, sur une estrade
        b(X0 + 1, -11, Z0 + 1, X0 + 12, -5, Z0 + 12, 'minecraft:stone_bricks')
        b(X0 + 1, -4, Z0 + 13, X0 + 12, -2, Z0 + 13, 'minecraft:stone_bricks')
        b(X0 + 13, -4, Z0 + 1, X0 + 13, -2, Z0 + 13, 'minecraft:stone_bricks')
        b(X0 + 1, -4, Z0 + 1, X0 + 12, -2, Z0 + 12, AIR)
        k.porte(X0 + 13, -4, Z0 + 7, 'east', 'iron')
        for i, x in enumerate(range(X0 + 2, X0 + 11, 3)):
            p(x, -4, Z0 + 3, 'minecraft:blast_furnace[facing=south,lit=false]')
            p(x, -3, Z0 + 3, 'minecraft:piston[extended=false,facing=up]')
            p(x + 1, -4, Z0 + 3, 'minecraft:iron_block'); p(x + 1, -3, Z0 + 3, 'minecraft:hopper[enabled=true,facing=down]')
        for x in range(X0 + 2, X0 + 12, 2):
            p(x, -3, Z0 + 12, 'minecraft:lever[face=wall,facing=north,powered=false]')
        v.coffre(X0 + 11, -4, Z0 + 9, 'west', [('minecraft:redstone_torch', 4), ('minecraft:map', 1), ('minecraft:bread', 6),
                                                ('minecraft:torch', 32)])
        v.panneau(X0 + 7, -3, Z0 + 12, 'north', ['GROUPE DE SECOURS', 'Relancer : les 5', 'leviers, dans', "l'ordre. Vite."])
        k.torche_murale(X0 + 6, -2, Z0 + 12, 'north', rouge=True)
        # tunnel de drainage noye depuis le bassin (5 x 6), grille arrachee
        b(99, -12, 34, 105, -5, Z0, 'minecraft:stone_bricks')
        b(100, -11, 33, 104, -6, Z0 + 1, EAU)
        for y in (-11, -6):
            p(99 + 1, y, Z0, 'minecraft:iron_bars'); p(104, y, Z0, 'minecraft:iron_bars')
        k.torche_murale(X0 + 4, -3, ZR - 1, 'north', rouge=True)
        k.veilleuses(X0 + 1, Z0 + 1, X1 - 1, ZR - 1, -4, 3, 3)
        # --------------------------------------------- coque RDC (y 0..5), etage (y 7..11)
        b(X0, -1, Z0, X1, -1, ZR, 'minecraft:polished_andesite')
        b(X0, 0, Z0, X1, E1 - 1, ZR, blanc)
        b(X0 + 1, 0, Z0 + 1, X1 - 1, E1 - 1, ZR - 1, AIR)
        b(X0, E1, Z0, X1, E1, ZE, gris)
        b(X0, E1 + 1, Z0, X1, TOIT - 1, ZE, blanc)
        b(X0 + 1, E1 + 1, Z0 + 1, X1 - 1, TOIT - 1, ZE - 1, AIR)
        b(X0, TOIT, Z0, X1, TOIT, ZE, gris)
        b(X0, TOIT + 1, Z0, X1, TOIT + 1, ZE, blanc)
        b(X0 + 1, TOIT + 1, Z0 + 1, X1 - 1, TOIT + 1, ZE - 1, AIR)
        b(X0, TOIT + 2, Z0, X1, TOIT + 2, Z0, dalle('smooth_stone')); b(X0, TOIT + 2, ZE, X1, TOIT + 2, ZE, dalle('smooth_stone'))
        b(X0, TOIT + 2, Z0, X0, TOIT + 2, ZE, dalle('smooth_stone')); b(X1, TOIT + 2, Z0, X1, TOIT + 2, ZE, dalle('smooth_stone'))
        # pilotis sous le porte-a-faux, galerie couverte
        b(X0, -1, ZR + 1, X1, -1, ZE, 'minecraft:polished_andesite')
        for x in range(X0, X1 + 1, 6):
            b(x, 0, ZE, x, E1 - 1, ZE, gris)
        # bandeaux de fenetres et meneaux (toutes faces)
        def bandeau(y0, y1, faces):
            for (xa, xb, za, zb) in faces:
                for x in range(xa, xb + 1):
                    for z in range(za, zb + 1):
                        t = x if za == zb else z
                        b(x, y0, z, x, y1, z, gris if t % 4 == 0 else vitre)
        bandeau(1, 4, ((X0 + 1, X1 - 1, Z0, Z0), (X0 + 1, X1 - 1, ZR, ZR), (X1, X1, Z0 + 1, ZR - 1)))
        bandeau(8, 10, ((X0 + 1, X1 - 1, Z0, Z0), (X0 + 1, X1 - 1, ZE, ZE), (X1, X1, Z0 + 1, ZE - 1),
                        (X0, X0, Z0 + 1, 55), (X0, X0, 64, ZE - 1)))
        # salle de controle : vitrage toute hauteur cote enclos
        b(X0 + 1, E1 + 1, Z0, 106, TOIT - 1, Z0, vitre)
        # brise-soleil sur la facade sud de l'etage
        for x in range(X0 + 2, X1, 3):
            b(x, E1 + 1, ZE + 1, x, TOIT - 1, ZE + 1, 'minecraft:smooth_stone')
        # --------------------------------------------- cloisons RDC
        cloison = blanc
        b(X0 + 1, 0, 55, X1 - 1, E1 - 1, 55, cloison); b(X0 + 1, 0, 58, X1 - 1, E1 - 1, 58, cloison)
        for x in (106, 118):
            b(x, 0, Z0 + 1, x, E1 - 1, 54, cloison)
        for x in (105, 113):
            b(x, 0, 59, x, E1 - 1, ZR - 1, cloison)
        # vitres couloir -> laboratoires (on voit dedans, lui aussi)
        for x in range(90, 105):
            if x % 3:
                b(x, 1, 55, x, 3, 55, 'minecraft:glass_pane')
        # plafond du couloir abaisse avec gaines, eclairage
        b(X0 + 1, 4, 56, X1 - 1, 4, 57, dalle('smooth_stone', 'top'))
        k.lampes_plafond(X0 + 1, 56, X1 - 1, 58, 4, 4, 0.1)
        # portes
        k.porte(97, 0, 55, 'north', 'iron'); k.porte(112, 0, 55, 'north', 'iron'); k.porte(122, 0, 55, 'north', 'iron')
        k.porte(97, 0, 58, 'south', 'iron'); k.porte(120, 0, 58, 'south', 'iron')
        b(107, 0, 58, 111, 3, 58, AIR)                     # cage d'escalier ouverte
        k.double_porte(X1, 0, 56, 'east', 'iron')
        # passerelle vitree depuis la mezzanine du centre d'accueil (on marche a y=7)
        b(82, E1, 59, X0, E1, 62, 'minecraft:smooth_quartz')
        b(83, E1 + 1, 59, X0 - 1, E1 + 3, 59, 'minecraft:glass_pane'); b(83, E1 + 1, 62, X0 - 1, E1 + 3, 62, 'minecraft:glass_pane')
        b(82, E1 + 4, 59, X0, E1 + 4, 62, dalle('smooth_quartz'))
        b(X0, E1 + 1, 60, X0, E1 + 3, 61, AIR)
        b(83, E1 + 1, 60, X0 - 1, E1 + 3, 61, AIR)
        b(85, 0, 60, 85, E1 - 1, 61, 'minecraft:quartz_pillar[axis=y]')
        # --------------------------------------------- labo de genetique (x 89..105, z 41..54)
        for z in (44, 48, 52):
            k.paillasse(91, z, 102, z, 0, 'south')
        for x in range(90, 105, 2):
            k.hotte(x, 0, Z0 + 1, 'south')
        b(89, 1, 44, 89, 4, 52, 'minecraft:black_concrete')
        for z in range(45, 52, 2):
            p(90, 2, z, 'minecraft:lime_stained_glass_pane' if z % 4 == 1 else 'minecraft:black_stained_glass_pane')
        v.panneau(90, 3, 48, 'east', ['SEQUENCAGE', 'Lot 44 : ADN', "d'amphibien pour", 'combler les trous'])
        # --------------------------------------------- couveuse (x 107..117)
        for z in (43, 47, 51):
            for x in range(108, 117):
                p(x, 0, z, 'minecraft:smooth_stone'); p(x, 1, z, dalle('smooth_stone'))
                if x % 2 == 0:
                    p(x, 2, z, 'minecraft:sniffer_egg[hatch=%d]' % rng.integers(0, 3))
                    p(x, 5, z, 'minecraft:chain[axis=y,waterlogged=false]')
                    p(x, 4, z, 'minecraft:shroomlight')
            p(110, 2, z, 'minecraft:turtle_egg[eggs=2,hatch=2]')
        # le nid vide, casse de l'interieur
        b(114, 0, 51, 116, 1, 51, AIR)
        p(115, 0, 51, 'minecraft:turtle_egg[eggs=1,hatch=2]')
        k.sang([(115, 0, 52), (113, 0, 54), (112, 0, 56), (100, 0, 57)], 0.5)
        v.panneau(107, 3, 48, 'east', ['COUVEUSE', 'Oeuf S-02 : eclos', 'hors protocole.', 'Ou est-il ?'])
        # --------------------------------------------- chambre froide (x 119..125)
        b(119, -1, 41, 125, -1, 54, 'minecraft:packed_ice')
        for z in range(42, 54, 2):
            p(125, 0, z, 'minecraft:blue_ice'); p(125, 1, z, 'minecraft:iron_block'); p(125, 2, z, 'minecraft:blue_ice')
            p(119, 1, z, 'minecraft:iron_block'); p(119, 2, z, trappe('iron', 'east', 'top'))
        v.coffre(122, 0, 41, 'south', [('minecraft:turtle_egg', 1), ('minecraft:paper', 5), ('minecraft:glass_bottle', 3)])
        # --------------------------------------------- salle des cuves (x 89..104, z 59..71)
        for x in (92, 97, 102):
            for z in (62, 68):
                brisee = (x, z) == (97, 68)
                k.cuve(x, 0, z, 3, brisee, 'minecraft:kelp[age=25]' if not brisee else None)
        v.panneau(90, 3, 60, 'east', ['CONFINEMENT', 'Specimens S-03', 'a S-08', ''])
        # --------------------------------------------- escalier (x 106..112) : RDC -> etage, RDC -> sous-sol
        b(106, E1, 59, 112, E1, ZR - 1, blanc)
        for i in range(7):
            z, y = ZR - 2 - i, i
            if y > 0:
                b(106, 0, z, 107, y - 1, z, blanc)
            b(106, y, z, 107, y, z, esc('smooth_quartz', 'north'))
            b(106, y + 1, z, 107, y + 4, z, AIR)
        b(106, E1, 64, 107, E1, ZR - 2, AIR)
        b(106, E1, 62, 107, E1, 63, blanc)
        for i in range(4):
            z = 60 + i
            b(109, -1 - i, z, 110, -1 - i, z, AIR)
            b(109, -2 - i, z, 110, -2 - i, z, esc('stone_brick', 'north'))
            b(109, -1 - i, z + 1, 110, -1, z + 1, AIR)
        b(109, -1, 60, 110, -1, 64, AIR)
        for z in range(60, 66):
            p(108, 0, z, 'minecraft:iron_bars'); p(111, 0, z, 'minecraft:iron_bars')
        # --------------------------------------------- poste de securite (x 114..125)
        b(125, 1, 60, 125, 4, 70, 'minecraft:black_concrete')
        for z in range(60, 71):
            for y in (1, 2, 3):
                if (z + y) % 2:
                    p(124, y, z, 'minecraft:gray_stained_glass_pane' if rng.random() < 0.8 else 'minecraft:lime_stained_glass_pane')
        k.bureau(121, 0, 63, 'east', 3); k.bureau(121, 0, 68, 'east', 2)
        k.casiers(114, 0, 70, 'north', 4, 'east')
        v.coffre(115, 0, 60, 'south', [('minecraft:crossbow', 1), ('minecraft:arrow', 32), ('minecraft:iron_sword', 1),
                                         ('minecraft:bread', 8), ('minecraft:torch', 16), ('minecraft:spyglass', 1)])
        v.panneau(114, 2, 64, 'east', ['SECURITE', 'Cameras 4 a 9 :', 'coupees depuis', 'le sous-sol'])
        # --------------------------------------------- ETAGE
        b(X0 + 1, E1 + 1, 55, X1 - 1, TOIT - 1, 55, cloison); b(X0 + 1, E1 + 1, 58, X1 - 1, TOIT - 1, 58, cloison)
        for x in (107,):
            b(x, E1 + 1, Z0 + 1, x, TOIT - 1, 54, cloison)
        for x in (99, 105, 113):
            b(x, E1 + 1, 59, x, TOIT - 1, ZE - 1, cloison)
        k.lampes_plafond(X0 + 1, 56, X1 - 1, 58, TOIT - 1, 4, 0.1)
        # couloir de l'etage relie a la passerelle
        b(X0 + 1, E1 + 1, 58, X0 + 1, E1 + 3, 61, AIR)
        b(X0 + 1, E1 + 1, 59, X0 + 1, E1 + 1, 59, AIR)
        k.porte(98, E1 + 1, 55, 'north', 'iron'); k.porte(115, E1 + 1, 55, 'north', 'spruce')
        k.porte(94, E1 + 1, 58, 'south', 'iron'); k.porte(102, E1 + 1, 58, 'south', 'spruce')
        k.porte(120, E1 + 1, 58, 'south', 'spruce')
        b(106, E1 + 1, 58, 112, E1 + 3, 58, AIR)
        # salle de controle (x 89..106, z 41..54) : pupitres en gradins face a l'enclos
        for z, y in ((44, E1 + 1), (49, E1 + 1)):
            for x in range(91, 105):
                p(x, y, z, 'minecraft:gray_concrete')
                p(x, y + 1, z, 'minecraft:black_stained_glass_pane' if x % 3 else 'minecraft:lime_stained_glass_pane')
                if x % 2:
                    k.chaise(x, y, z + 1, 'north', 'polished_blackstone')
        b(89, E1 + 2, 42, 89, TOIT - 2, 53, 'minecraft:black_concrete')
        for z in range(43, 53):
            p(90, E1 + 3 + (z % 3 == 0), z, 'minecraft:lime_stained_glass_pane')
        v.panneau(90, E1 + 2, 47, 'east', ['CONTROLE', 'Clotures : OFF', 'Enclos S-01 :', 'VIDE'])
        k.sang([(96, E1 + 1, 46), (93, E1 + 1, 50), (92, E1 + 1, 54)], 0.6)
        # bureaux ouverts (x 108..125) et bureau du directeur
        for x in (109, 113):
            for z in (43, 48):
                k.bureau(x, E1 + 1, z, 'east', 2)
                p(x + 2, E1 + 1, z - 1, 'minecraft:light_gray_stained_glass_pane')
        b(119, E1 + 1, 41, 119, TOIT - 1, 49, 'minecraft:glass_pane')
        b(119, E1 + 1, 45, 119, E1 + 2, 45, AIR)
        k.porte(119, E1 + 1, 45, 'east', 'spruce')
        k.etagere(125, E1 + 1, 41, 8, 'south', 3)
        k.bureau(121, E1 + 1, 44, 'east', 3)
        for x in range(120, 125):
            for z in range(42, 48):
                p(x, E1 + 1, z, 'minecraft:red_carpet', seulement_air=True)
        v.coffre(124, E1 + 1, 48, 'north', [('journal:directeur', 1), ('minecraft:compass', 1), ('minecraft:map', 1),
                                              ('minecraft:golden_apple', 1)])
        k.plante(120, E1 + 1, 41, True)
        # salle des serveurs (x 89..98)
        for z in (61, 64, 67, 70, 73):
            k.baie_serveur(90, E1 + 1, z, 'south', 8, 'east')
        for x in range(90, 98, 2):
            p(x, TOIT - 1, 60, 'minecraft:chain[axis=z,waterlogged=false]')
        # salle de reunion (x 100..104)
        k.longue_table(102, 61, 102, 72, E1 + 1)
        b(100, E1 + 2, ZE - 1, 104, TOIT - 2, ZE - 1, 'minecraft:white_wool')
        # infirmerie (x 114..125)
        for z in (61, 66, 71):
            k.lit(116, E1 + 1, z, 'west')
            p(114, E1 + 1, z + 1, 'minecraft:iron_bars')
        k.casiers(125, E1 + 1, 60, 'west', 8, 'south')
        p(121, E1 + 1, 74, 'minecraft:water_cauldron[level=1]')
        p(122, E1 + 1, 74, 'minecraft:brewing_stand[has_bottle_0=true,has_bottle_1=false,has_bottle_2=false]')
        v.coffre(123, E1 + 1, 74, 'north', [('minecraft:potion', 2, {'Potion': 'minecraft:healing'}), ('minecraft:golden_carrot', 4), ('minecraft:honey_bottle', 3)])
        k.sang([(116, E1 + 1, 66), (119, E1 + 1, 64), (120, E1 + 1, 59)], 0.7)
        # acces au toit : echelle dans la cage d'escalier
        for y in range(E1 + 1, TOIT + 1):
            p(112, y, 70, 'minecraft:ladder[facing=west,waterlogged=false]')
        b(112, TOIT, 70, 112, TOIT, 70, 'minecraft:iron_trapdoor[facing=west,half=bottom,open=true,powered=false,waterlogged=false]')
        # --------------------------------------------- toit technique
        R = TOIT + 1
        b(90, TOIT, 42, 106, TOIT, 58, 'minecraft:light_gray_concrete')
        # H jaune et cercle
        b(95, TOIT, 46, 96, TOIT, 54, 'minecraft:yellow_concrete'); b(100, TOIT, 46, 101, TOIT, 54, 'minecraft:yellow_concrete')
        b(97, TOIT, 49, 99, TOIT, 51, 'minecraft:yellow_concrete')
        for a in range(0, 360, 6):
            p(int(round(98 + 7.5 * math.cos(math.radians(a)))), TOIT, int(round(50 + 7.5 * math.sin(math.radians(a)))),
              'minecraft:yellow_concrete')
        for (x, z) in ((90, 42), (106, 42), (90, 58), (106, 58)):
            p(x, R, z, 'minecraft:end_rod[facing=up]')
        # centrales de traitement d'air
        for x0 in (110, 117):
            b(x0, R, 43, x0 + 4, R + 2, 47, 'minecraft:iron_block')
            for x in range(x0, x0 + 5):
                p(x, R + 1, 48, trappe('iron', 'north', 'top', True))
            p(x0 + 1, R + 3, 44, 'minecraft:daylight_detector[inverted=false,power=0]')
            p(x0 + 3, R + 3, 46, 'minecraft:daylight_detector[inverted=false,power=0]')
        b(110, R, 49, 121, R, 49, 'minecraft:smooth_stone')
        # panneaux solaires
        for z in range(62, 75, 3):
            for x in range(92, 124):
                if x % 8 == 7:
                    continue
                p(x, R, z, 'minecraft:daylight_detector[inverted=false,power=0]')
                p(x, R, z + 1, 'minecraft:daylight_detector[inverted=false,power=0]')
        # mat d'antennes
        b(123, R, 52, 123, R + 9, 52, 'minecraft:iron_bars')
        p(123, R + 10, 52, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
        for y in (R + 4, R + 7):
            p(122, y, 52, 'minecraft:end_rod[facing=west]'); p(124, y, 52, 'minecraft:end_rod[facing=east]')
        # --------------------------------------------- tour technique et reservoir
        b(127, 0, 40, 133, 20, 48, gris)
        b(128, 0, 41, 132, 19, 47, AIR)
        for y in range(2, 19, 4):
            b(130, y, 40, 130, y + 2, 40, 'minecraft:glass_pane'); b(133, y, 44, 133, y + 2, 44, 'minecraft:glass_pane')
        for y in range(0, 21):
            p(128, y, 44, 'minecraft:ladder[facing=east,waterlogged=false]')
        k.porte(127, 0, 45, 'west', 'iron')
        for y in range(21, 29):
            for x in range(125, 136):
                for z in range(39, 50):
                    d = math.hypot(x - 130, z - 44)
                    if d <= 5.2 and (d > 4.2 or y in (21, 28)):
                        p(x, y, z, 'minecraft:white_concrete' if y % 3 else 'minecraft:light_gray_concrete')
        for y in range(21, 28):
            for x in range(126, 135):
                for z in range(40, 49):
                    if math.hypot(x - 130, z - 44) <= 4.2:
                        p(x, y, z, EAU)
        # --------------------------------------------- galerie couverte (sous le porte-a-faux)
        for x in range(92, 124, 6):
            b(x, 0, 74, x + 2, 0, 74, esc('spruce', 'south'))
        p(125, 0, 74, 'minecraft:dispenser[facing=west,triggered=false]'); p(125, 1, 74, 'minecraft:dispenser[facing=west,triggered=false]')
        v.panneau(125, 2, 74, 'west', ['DISTRIBUTEUR', 'HORS SERVICE', '', ''])
        # usure, lumieres
        k.usure(X0, -1, Z0, X1 + 7, TOIT + 2, ZE + 1, {blanc: ['minecraft:white_concrete_powder', 'minecraft:light_gray_concrete']}, 0.04)
        k.veilleuses(X0 + 1, Z0 + 1, X1 - 1, ZR - 1, 0, 3, 3)
        k.veilleuses(X0 + 1, Z0 + 1, X1 - 1, ZE - 1, E1 + 1, 3, 3)
        k.toiles(X0 + 1, 0, Z0 + 1, X1 - 1, E1 - 1, ZR - 1, 20)
        k.lierre(X0, X1, Z0 - 1, Z0 - 1, TOIT + 1, 1, 20, 'south')

    # ================================================================ loge du personnel
    def loge(self):
        b, p, k, rng, v = self.b, self.p, self.k, self.rng, self.v
        X0, X1, Z0, Z1 = 0, 28, 46, 84
        E1, TOIT = 5, 10
        bois = 'minecraft:spruce_planks'
        # coque : soubassement moellons, RDC bardage bois, etage enduit blanc, poteaux apparents
        b(X0, -1, Z0, X1, -1, Z1, 'minecraft:mossy_cobblestone')
        b(X0, 0, Z0, X1, 0, Z1, 'minecraft:mossy_cobblestone')
        b(X0, 1, Z0, X1, E1 - 1, Z1, bois)
        b(X0, E1, Z0, X1, E1, Z1, 'minecraft:stripped_spruce_log[axis=x]')
        b(X0, E1 + 1, Z0, X1, TOIT, Z1, 'minecraft:white_terracotta')
        b(X0 + 1, 0, Z0 + 1, X1 - 1, E1 - 1, Z1 - 1, AIR)
        b(X0 + 1, -1, Z0 + 1, X1 - 1, -1, Z1 - 1, 'minecraft:spruce_planks')
        b(X0 + 1, E1, Z0 + 1, X1 - 1, E1, Z1 - 1, 'minecraft:spruce_planks')
        b(X0 + 1, E1 + 1, Z0 + 1, X1 - 1, TOIT, Z1 - 1, AIR)
        for x in range(X0, X1 + 1, 4):
            for z in (Z0, Z1):
                b(x, 1, z, x, TOIT, z, 'minecraft:stripped_spruce_log[axis=y]')
        for z in range(Z0, Z1 + 1, 4):
            for x in (X0, X1):
                b(x, 1, z, x, TOIT, z, 'minecraft:stripped_spruce_log[axis=y]')
        # fenetres a volets
        for z in range(Z0 + 2, Z1 - 1, 4):
            for x, dehors in ((X0, 'west'), (X1, 'east')):
                for y0 in (2, E1 + 2):
                    b(x, y0, z, x, y0 + 1, z + 1, 'minecraft:glass_pane')
                    dx = -1 if dehors == 'west' else 1
                    if rng.random() < 0.8:
                        p(x + dx, y0 + 1, z - 1, trappe('spruce', dehors, 'top', True))
                    if rng.random() < 0.8:
                        p(x + dx, y0 + 1, z + 2, trappe('spruce', dehors, 'top', True))
        for x in range(X0 + 2, X1 - 1, 4):
            for z in (Z0, Z1):
                b(x, 2, z, x + 1, 3, z, 'minecraft:glass_pane'); b(x, E1 + 2, z, x + 1, E1 + 3, z, 'minecraft:glass_pane')
        # toit de cuivre oxyde a deux pans (faitage nord-sud), debord de 2
        XA, XB = X0 - 2, X1 + 2
        for x in range(XA, XB + 1):
            d = min(x - XA, XB - x)
            y = TOIT + 1 + d // 2
            ouest = x - XA < XB - x
            if abs((x - XA) - (XB - x)) <= 1:
                b(x, y, Z0 - 2, x, y, Z1 + 2, 'minecraft:oxidized_cut_copper')
                continue
            etat = esc('oxidized_cut_copper', 'east' if ouest else 'west') if d % 2 == 0 else dalle('oxidized_cut_copper', 'top')
            b(x, y, Z0 - 2, x, y, Z1 + 2, etat)
            if x > X0 and x < X1:
                for z in (Z0, Z1):
                    b(x, TOIT + 1, z, x, y - 1, z, 'minecraft:white_terracotta')
        for z in (Z0, Z1):
            b(13, TOIT + 3, z, 15, TOIT + 5, z, 'minecraft:glass_pane')
        # galerie exterieure a l'est (etage) sur poteaux, escalier au sud
        b(X1 + 1, E1, Z0, X1 + 3, E1, Z1, 'minecraft:spruce_planks')
        for z in range(Z0, Z1 + 1):
            p(X1 + 3, E1 + 1, z, 'minecraft:spruce_fence')
        for z in range(Z0, Z1 + 1, 4):
            b(X1 + 3, 0, z, X1 + 3, E1 - 1, z, 'minecraft:stripped_spruce_log[axis=y]')
        b(X1 + 1, E1 + 4, Z0 - 1, X1 + 3, E1 + 4, Z1 + 1, dalle('spruce'))
        for i in range(E1 + 1):
            z = Z1 + 6 - i
            b(X1 + 1, i - 1, z, X1 + 2, i - 1, z, esc('spruce', 'north'))
            b(X1 + 1, i, z, X1 + 2, i + 3, z, AIR)
        b(X1 + 1, E1, Z1 + 1, X1 + 2, E1, Z1 + 1, 'minecraft:spruce_planks')
        b(X1 + 3, E1 + 1, Z1 - 1, X1 + 3, E1 + 1, Z1 + 1, AIR)
        # ------------------------------------------ RDC : cantine (z 47..64), cuisine, laverie, detente
        b(X0 + 1, 0, 65, X1 - 1, E1 - 1, 65, bois)
        b(X0 + 1, 0, 77, X1 - 1, E1 - 1, 77, bois)
        b(16, 0, 66, 16, E1 - 1, 76, bois)
        b(8, 0, 65, 9, 2, 65, AIR); b(20, 0, 65, 21, 2, 65, AIR); b(22, 0, 77, 22, 1, 77, AIR); b(8, 0, 77, 8, 1, 77, AIR)
        k.porte(22, 0, 77, 'south', 'spruce'); k.porte(8, 0, 77, 'south', 'spruce')
        for z in (50, 55, 60):
            k.longue_table(4, z, 22, z, 0)
        for x in range(3, 24):
            p(x, 0, 63, 'minecraft:smooth_stone'); p(x, 1, 63, dalle('smooth_stone'))
        k.porte(X1, 0, 52, 'east', 'spruce'); k.porte(X1, 0, 72, 'east', 'spruce')
        # cuisine (x 1..15, z 66..76)
        for x in range(1, 16):
            p(x, 0, 66, 'minecraft:barrel[facing=up,open=false]')
            p(x, 1, 66, dalle('polished_andesite'))
        for i, e in enumerate(['minecraft:smoker[facing=south,lit=false]', 'minecraft:furnace[facing=south,lit=false]',
                               'minecraft:blast_furnace[facing=south,lit=false]', 'minecraft:water_cauldron[level=3]',
                               'minecraft:cauldron', 'minecraft:smoker[facing=south,lit=false]']):
            p(2 + i * 2, 0, 66, e)
        for x in range(1, 16, 2):
            p(x, 2, 66, trappe('spruce', 'south', 'top', True))
        b(4, 0, 71, 11, 0, 71, 'minecraft:smooth_quartz'); b(4, 1, 71, 11, 1, 71, dalle('smooth_quartz'))
        b(1, 0, 75, 2, 2, 76, 'minecraft:iron_block')
        k.porte(3, 0, 75, 'east', 'iron')
        v.coffre(14, 0, 76, 'north', [('minecraft:bread', 12), ('minecraft:cooked_beef', 6), ('minecraft:apple', 8)], 'barrel')
        # laverie / douches (x 17..27, z 66..76)
        for z in range(67, 76, 2):
            p(27, 0, z, 'minecraft:water_cauldron[level=%d]' % rng.integers(1, 4))
            p(27, 3, z, 'minecraft:tripwire_hook[attached=false,facing=west,powered=false]')
        k.casiers(18, 0, 76, 'north', 8, 'east')
        # detente (z 78..83) : billard, canape, jukebox
        b(5, 0, 80, 10, 0, 81, 'minecraft:dark_oak_planks'); b(5, 1, 80, 10, 1, 81, 'minecraft:green_carpet')
        for x in range(15, 22):
            p(x, 0, 83, esc('spruce', 'south'))
        p(14, 0, 83, dalle('spruce')); p(22, 0, 83, dalle('spruce'))
        p(25, 0, 80, 'minecraft:jukebox[has_record=false]')
        # escalier interieur (x 25..26) vers l'etage
        for i in range(E1 + 1):
            z = 48 + i
            if i:
                b(25, i - 1, z, 26, i - 1, z, esc('spruce', 'south'))
            b(25, i, z, 26, i + 3, z, AIR)
        b(25, E1, 48, 26, E1, 53, AIR)
        b(25, E1, 54, 26, E1, 54, 'minecraft:spruce_planks')
        # ------------------------------------------ ETAGE : couloir central, 12 chambres
        CY = E1 + 1
        b(X0 + 1, CY, Z0 + 1, 12, TOIT, Z1 - 1, AIR)
        for z in range(Z0 + 1, Z1):
            p(12, CY, z, bois); p(15, CY, z, bois)
        b(12, CY, Z0 + 1, 12, TOIT, Z1 - 1, bois); b(15, CY, Z0 + 1, 15, TOIT, Z1 - 1, bois)
        b(13, CY, Z0 + 1, 14, TOIT, Z1 - 1, AIR)
        b(24, CY, 47, 27, TOIT, 54, AIR)
        b(15, CY, 47, 15, TOIT, 54, AIR)
        chambre = 0
        for zc in range(Z0 + 1, Z1 - 1, 6):
            z0, z1 = zc, min(zc + 5, Z1 - 1)
            for (xa, xb, porte_x, regard) in ((1, 11, 12, 'west'), (16, 27, 15, 'east')):
                if xa == 16 and z0 < 55:
                    continue
                if z1 + 1 < Z1:
                    b(xa, CY, z1 + 1, xb, TOIT, z1 + 1, bois)
                chambre += 1
                pz = z0 + 2
                ouverte = rng.random() < 0.4
                k.porte(porte_x, CY, pz, regard, 'spruce', ouverte=ouverte)
                lx = xa + 1 if regard == 'east' else xb - 1
                k.lit(lx if regard == 'east' else xb - 2, CY, z1 - 1, 'east' if regard == 'east' else 'west',
                      ['white', 'light_gray', 'brown', 'green'][chambre % 4])
                p(xb - 1 if regard == 'east' else xa + 1, CY, z0, 'minecraft:barrel[facing=up,open=false]')
                p(xb - 1 if regard == 'east' else xa + 1, CY + 1, z0, 'minecraft:barrel[facing=up,open=false]')
                k.bureau(xb - 2 if regard == 'east' else xa + 2, CY, z0 + 1, 'north', 1, 'spruce', ecrans=False)
                p(xb - 2 if regard == 'east' else xa + 2, CY + 1, z0, 'minecraft:lantern[hanging=false,waterlogged=false]')
                for x in range(xa + 1, xb):
                    for z in range(z0 + 1, z1):
                        if rng.random() < 0.3:
                            p(x, CY, z, 'minecraft:brown_carpet', seulement_air=True)
                if chambre == 7:
                    # la chambre barricadee : planches contre la porte, dernier message, provisions
                    b(porte_x + (1 if regard == 'east' else -1), CY, pz - 1, porte_x + (1 if regard == 'east' else -1),
                      CY + 1, pz + 1, 'minecraft:spruce_planks')
                    v.coffre(lx, CY, z0 + 3, 'north', [('minecraft:crossbow', 1), ('minecraft:arrow', 24),
                                                         ('minecraft:cooked_beef', 8), ('minecraft:map', 1),
                                                         ('minecraft:writable_book', 1)])
                    v.panneau(xb - 1 if regard == 'east' else xa + 1, CY + 2, z0 + 2, 'west' if regard == 'east' else 'east',
                              ['Jour 6.', "Il ecoute.", 'Ne courez pas', 'pres de l\'eau.'])
        k.porte(13, CY, Z1, 'south', 'spruce')
        b(X1, CY, 49, X1, CY + 1, 50, AIR)
        k.porte(X1, CY, 49, 'east', 'spruce')
        k.lampes_plafond(1, Z0 + 1, X1 - 1, Z1 - 1, E1 - 1, 6, 0.0)
        k.veilleuses(X0 + 1, Z0 + 1, X1 - 1, Z1 - 1, 0, 3, 3)
        k.veilleuses(X0 + 1, Z0 + 1, X1 - 1, Z1 - 1, CY, 3, 3)
        k.toiles(X0 + 1, CY, Z0 + 1, X1 - 1, TOIT, Z1 - 1, 20)
        k.lierre(X0 - 1, X0 - 1, Z0, Z1, TOIT, 1, 20, 'east')
        k.usure(X0, 1, Z0, X1, E1 - 1, Z1, {bois: ['minecraft:stripped_spruce_wood[axis=y]', 'minecraft:mossy_cobblestone']}, 0.03)

    # ================================================================ centrale electrique
    def centrale(self):
        b, p, k, rng, v = self.b, self.p, self.k, self.rng, self.v
        X0, X1, Z0, Z1 = 0, 16, 18, 42
        b(X0, -1, Z0, X1, -1, Z1, 'minecraft:smooth_stone')
        b(X0, 0, Z0, X1, 9, Z1, 'minecraft:gray_concrete')
        b(X0 + 1, 0, Z0 + 1, X1 - 1, 8, Z1 - 1, AIR)
        b(X0, 10, Z0, X1, 10, Z1, 'minecraft:smooth_stone_slab[type=bottom,waterlogged=false]')
        # toiture en sheds (dents de scie) avec verriere
        for z in range(Z0, Z1 + 1, 4):
            for i in range(3):
                b(X0, 10 + i, z + i, X1, 10 + i, z + i, esc('stone', 'north'))
            if z + 3 <= Z1:
                b(X0 + 1, 10, z + 3, X1 - 1, 12, z + 3, 'minecraft:glass')
        for z in range(Z0 + 2, Z1, 4):
            b(X1, 2, z, X1, 6, z + 1, 'minecraft:gray_stained_glass_pane')
        k.double_porte(X1, 0, 29, 'east', 'iron')
        b(X1, 0, 32, X1, 5, 36, AIR)                # grand portail de maintenance, ouvert
        for z in range(Z0 + 3, Z1 - 2, 6):
            b(3, 0, z, 9, 2, z + 2, 'minecraft:iron_block')
            b(4, 3, z + 1, 8, 3, z + 1, 'minecraft:piston[extended=false,facing=up]')
            p(10, 0, z + 1, 'minecraft:blast_furnace[facing=east,lit=false]')
            for x in range(3, 10, 2):
                p(x, 3, z, 'minecraft:hopper[enabled=true,facing=down]')
            b(6, 4, z + 1, 6, 8, z + 1, 'minecraft:iron_bars')
        for z in range(Z0 + 2, Z1 - 1):
            p(14, 1, z, 'minecraft:lever[face=wall,facing=west,powered=false]' if z % 3 == 0 else 'minecraft:air')
        b(15, 0, Z0 + 1, 15, 3, Z1 - 1, 'minecraft:iron_block')
        v.panneau(14, 2, 30, 'west', ['CENTRALE', 'Carburant : 6 %', 'Secours : voir', 'sous-sol labos'])
        # cheminee
        for y in range(-1, 32):
            for x in range(-4, 3):
                for z in range(20, 27):
                    d = math.hypot(x + 1, z - 23)
                    if d <= 3.2 and (d > 2.1 or y < 0):
                        p(x, y, z, 'minecraft:bricks' if y % 6 else 'minecraft:stone_bricks')
        # cuves de carburant et transformateurs
        for (cx, cz) in ((5, 6), (13, 6)):
            for y in range(0, 9):
                for x in range(cx - 4, cx + 5):
                    for z in range(cz - 4, cz + 5):
                        d = math.hypot(x - cx, z - cz)
                        if d <= 3.6 and (d > 2.6 or y in (0, 8)):
                            p(x, y, z, 'minecraft:light_gray_concrete' if y % 4 else 'minecraft:gray_concrete')
            for y in range(0, 10):
                p(cx + 4, y, cz, 'minecraft:ladder[facing=east,waterlogged=false]')
        for x in range(0, 17, 4):
            p(x, 0, 14, 'minecraft:iron_block'); p(x, 1, 14, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
        for x in range(-2, 19):
            p(x, 0, 12, 'minecraft:iron_bars'); p(x, 0, 16, 'minecraft:iron_bars')
        k.veilleuses(X0 + 1, Z0 + 1, X1 - 1, Z1 - 1, 0, 3, 3)

    # ================================================================ exterieurs
    def exterieurs(self):
        b, p, k, rng, v = self.b, self.p, self.k, self.rng, self.v
        dal = 'minecraft:polished_andesite'
        # parvis
        b(34, -1, 86, 82, -1, 104, dal)
        for x in range(34, 83):
            p(x, -1, 86, 'minecraft:stone_bricks'); p(x, -1, 104, 'minecraft:stone_bricks')
        for x in range(36, 81, 4):
            for z in range(88, 103, 4):
                p(x, -1, z, 'minecraft:chiseled_stone_bricks')
        # fontaine seche
        for x in range(50, 67):
            for z in range(90, 102):
                d = math.hypot((x - 58) / 1.3, z - 96)
                if d <= 6.2:
                    p(x, -1, z, 'minecraft:mossy_stone_bricks')
                    if d > 5.3:
                        p(x, 0, z, 'minecraft:stone_brick_wall')
                    elif rng.random() < 0.3:
                        p(x, 0, z, 'minecraft:moss_carpet')
        b(58, 0, 96, 58, 3, 96, 'minecraft:mossy_stone_bricks'); p(58, 4, 96, 'minecraft:stone_brick_wall')
        # lampadaires
        for x in range(36, 81, 11):
            for z in (88, 102):
                b(x, 0, z, x, 4, z, 'minecraft:polished_blackstone_wall')
                p(x, 5, z, 'minecraft:polished_blackstone_slab[type=bottom,waterlogged=false]')
                k.lanterne(x, 6, z, suspendue=False)
        # allees
        b(28, -1, 60, 34, -1, 67, dal)          # loge <-> centre d'accueil
        b(82, -1, 78, 88, -1, 84, dal)
        b(16, -1, 28, 22, -1, 46, 'minecraft:gravel')
        # parking devant les labos
        b(88, -1, 84, 128, -1, 106, 'minecraft:gray_concrete')
        for x in range(90, 128, 4):
            b(x, -1, 86, x, -1, 92, 'minecraft:white_concrete'); b(x, -1, 98, x, -1, 104, 'minecraft:white_concrete')
        self.jeep(96, 88, 'south'); self.jeep(108, 99, 'north', couche=False); self.jeep(118, 88, 'south', ecrase=True)
        # route vers le portail
        for z in range(104, 125):
            b(54, -1, z, 62, -1, z, 'minecraft:packed_mud' if (z * 7) % 5 else 'minecraft:coarse_dirt')
        b(62, -1, 95, 88, -1, 100, 'minecraft:packed_mud')
        # portail (hommage) : deux pylones, poutre, torcheres, vantaux dont un arrache
        for x0 in (48, 63):
            b(x0, -1, 118, x0 + 5, 14, 122, 'minecraft:stone_bricks')
            b(x0 - 1, 15, 117, x0 + 6, 15, 123, 'minecraft:stone_brick_slab[type=bottom,waterlogged=false]')
            p(x0 + 2, 16, 120, 'minecraft:campfire[facing=north,lit=false,signal_fire=false,waterlogged=false]')
            p(x0 + 3, 16, 120, 'minecraft:campfire[facing=north,lit=false,signal_fire=false,waterlogged=false]')
            k.usure(x0, 0, 118, x0 + 5, 14, 122, {'minecraft:stone_bricks': ['minecraft:mossy_stone_bricks',
                                                                              'minecraft:cracked_stone_bricks']}, 0.3)
        b(48, 13, 119, 68, 14, 121, 'minecraft:stripped_dark_oak_log[axis=x]')
        v.panneau(58, 12, 122, 'south', ['SITE B', '', 'ACCES RESTREINT', ''])
        b(54, 0, 120, 57, 10, 120, 'minecraft:spruce_planks')
        for x in range(54, 58):
            for y in range(0, 11, 3):
                p(x, y, 120, 'minecraft:stripped_spruce_log[axis=x]')
        # vantail est arrache, couche dans l'herbe
        b(59, 0, 124, 62, 0, 133, 'minecraft:spruce_planks')
        # cloture de perimetre : poteaux de beton, barreaux, deux breches
        def cloture(xa, za, xb, zb):
            n = max(abs(xb - xa), abs(zb - za))
            for i in range(n + 1):
                x = xa + (xb - xa) * i // n; z = za + (zb - za) * i // n
                if i % 6 == 0:
                    b(x, 0, z, x, 7, z, 'minecraft:polished_andesite')
                    p(x, 8, z, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
                else:
                    b(x, 0, z, x, 6, z, 'minecraft:iron_bars')
        cloture(-6, 44, -6, 122); cloture(-6, 122, 47, 122); cloture(69, 122, 142, 122); cloture(142, 36, 142, 122)
        cloture(100, 36, 142, 36); cloture(-6, 44, -6, 12)
        b(142, 0, 70, 142, 6, 78, AIR)                     # breche est (barreaux arraches)
        b(-6, 0, 96, -6, 6, 101, AIR)
        for i in range(9):
            p(143 + i // 3, 0, 70 + i, 'minecraft:iron_bars')
        v.panneau(-5, 2, 110, 'east', ['DANGER', '10 000 VOLTS', '(coupe)', ''])
        v.panneau(141, 2, 90, 'west', ['DANGER', '10 000 VOLTS', '(coupe)', ''])

    def jeep(self, x, z, sens, couche=False, ecrase=False):
        """Tout-terrain de visite (5 x 3 x 3) : caisse blanche a bandes, bulle de toit, roues."""
        b, p = self.b, self.p
        axe_z = sens in ('north', 'south')
        L, l = 6, 3
        def pos(i, j):
            return (x + j, z + i) if axe_z else (x + i, z + j)
        for i in range(L):
            for j in range(l):
                px, pz = pos(i, j)
                p(px, 0, pz, 'minecraft:white_concrete' if 0 < i < L - 1 else 'minecraft:gray_concrete')
                p(px, 1, pz, 'minecraft:red_concrete' if j != 1 and 1 < i < L - 1 else 'minecraft:white_concrete')
                if 1 <= i <= 3:
                    p(px, 2, pz, 'minecraft:light_blue_stained_glass' if not ecrase else 'minecraft:air')
        for (i, j) in ((1, -1), (1, l), (L - 2, -1), (L - 2, l)):
            px, pz = pos(i, j)
            p(px, 0, pz, 'minecraft:black_concrete')
        avant = 0 if sens in ('north', 'west') else L - 1
        for j in (0, 2):
            px, pz = pos(avant, j)
            p(px, 1, pz, 'minecraft:end_rod[facing=%s]' % sens)
        if ecrase:
            px, pz = pos(2, 1)
            p(px, 1, pz, 'minecraft:air'); p(px, 0, pz, 'minecraft:red_concrete')
            self.v.panneau(*(lambda a: (a[0], 2, a[1]))(pos(2, 1)), sens, ['', 'Traces de', 'morsure', ''], mural=False)

    # ================================================================ belvedere
    def belvedere(self, cx, cz, R=5, H=17):
        """Tour ronde a trois niveaux, escalier en colimacon, toit conique ; en haut, table des
        cartes et longue-vue sur la jungle."""
        b, p, k, v = self.b, self.p, self.k, self.v
        planchers = (6, 12)
        for y in range(-1, H + 1):
            for x in range(cx - R - 1, cx + R + 2):
                for z in range(cz - R - 1, cz + R + 2):
                    d = math.hypot(x - cx, z - cz)
                    if d > R + 0.5:
                        continue
                    if d > R - 0.5:
                        if y == -1 or y in (0,) + planchers + (H,):
                            e = 'minecraft:stripped_jungle_log[axis=y]' if y <= 0 else 'minecraft:cut_sandstone'
                        else:
                            a = math.degrees(math.atan2(z - cz, x - cx)) % 360
                            fenetre = (y % 6 in (2, 3, 4) and int(a // 30) % 2 == 0) or (y > 13 and int(a // 20) % 3)
                            e = 'minecraft:glass_pane' if fenetre else 'minecraft:smooth_sandstone'
                        p(x, y, z, e)
                    elif y == -1:
                        p(x, y, z, 'minecraft:polished_granite')
                    elif y in planchers:
                        p(x, y, z, 'minecraft:spruce_planks')
                    else:
                        p(x, y, z, AIR)
        # colimacon : 12 marches par tour, une marche = un secteur de 30 degres, 3 blocs de large
        marches = []
        for i in range(1, 14):
            a = (i + 0.5) * 2 * math.pi / 12
            for r in (1.5, 2.5, 3.4):
                x, z = int(round(cx + r * math.cos(a))), int(round(cz + r * math.sin(a)))
                marches.append((x, i - 1, z))
        # tremies : degager 3 blocs au-dessus de chaque marche (planchers compris)
        for (x, y, z) in marches:
            for dy in range(1, 4):
                p(x, y + dy, z, AIR)
        for (x, y, z) in marches:
            p(x, y, z, 'minecraft:spruce_planks')
        b(cx, 0, cz, cx, H - 1, cz, 'minecraft:stripped_jungle_log[axis=y]')
        # porte, toit conique, amenagement du sommet
        b(cx + R, 0, cz, cx + R, 1, cz, AIR)
        k.porte(cx + R, 0, cz, 'east', 'spruce')
        for y in range(H + 1, H + 9):
            r = (R + 1.5) * (1 - (y - H - 1) / 8)
            for x in range(cx - R - 2, cx + R + 3):
                for z in range(cz - R - 2, cz + R + 3):
                    d = math.hypot(x - cx, z - cz)
                    if r - 1.1 < d <= r:
                        p(x, y, z, 'minecraft:spruce_planks' if y % 2 else 'minecraft:dark_oak_planks')
        p(cx, H + 9, cz, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
        p(cx + 2, 13, cz - 2, 'minecraft:cartography_table')
        p(cx - 2, 13, cz + 2, 'minecraft:lectern[facing=east,has_book=false,powered=false]')
        v.coffre(cx - 2, 13, cz - 2, 'south', [('minecraft:spyglass', 1), ('minecraft:map', 1), ('minecraft:compass', 1)])
        v.panneau(cx + 3, 14, cz, 'west', ['BELVEDERE', 'Il chasse surtout', 'au crepuscule,', 'depuis la riviere'])
        k.veilleuses(cx - 3, cz - 3, cx + 3, cz + 3, 0, 3, 3)
        k.veilleuses(cx - 3, cz - 3, cx + 3, cz + 3, 7, 3, 3)
