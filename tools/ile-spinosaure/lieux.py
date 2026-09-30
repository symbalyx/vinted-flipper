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
        # bateau de peche echoue contre le ponton, couche sur le flanc, a demi rempli d'eau
        bx, bz = x + 5, z + 14
        self.navire(bx, self.sol(bx, bz), bz, math.pi / 2 + 0.25, 13, 2.6, 3.2, 'bois', gite=math.radians(-18),
                    tangage=math.radians(4), dechirure=False)
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
        """Helicoptere de transport militaire abattu, couche sur le flanc gauche au bout d'un
        sillon arrache dans la jungle. Modele en coordonnees propres (u : longueur, nez vers +u ;
        v : de gauche a droite ; w : hauteur), puis couche : v devient la hauteur, w l'horizontale.
        La porte cargo droite, ouverte, regarde le ciel : on y entre par le dessus."""
        m, rng, k = self.m, self.rng, self.k
        OLIVE, OLIVE2 = 'minecraft:green_terracotta', 'minecraft:moss_block'
        GRIS, NOIR = 'minecraft:gray_concrete', 'minecraft:black_concrete'
        VITRE = 'minecraft:gray_stained_glass'
        cel = {}

        def met(u, v, w, e):
            cel[(int(round(u)), int(round(v)), int(round(w)))] = e

        # ---- fuselage : sections elliptiques, cabine large, nez effile, poutre de queue fine
        for u10 in range(-150, 91, 5):
            u = u10 / 10
            if u >= -3:
                a_, b_ = 2.9, 2.8                       # demi-largeur, demi-hauteur de la cabine
                if u > 5:
                    t = (u - 5) / 4
                    a_, b_ = 2.9 * (1 - 0.55 * t * t), 2.8 * (1 - 0.45 * t)
                wc = 2.8
            else:
                t = (-3 - u) / 12
                a_, b_ = 1.5 - 0.6 * t, 1.6 - 0.6 * t
                wc = 3.6 + 0.8 * t
            for v in range(-4, 5):
                for w in range(-1, 8):
                    q = (v / a_) ** 2 + ((w - wc) / b_) ** 2
                    if q <= 1.0:
                        coque = q > (0.55 if u >= -3 else 0.2)
                        if not coque:
                            met(u, v, w, 'AIR')
                            continue
                        e = OLIVE
                        if u > 4.5 and w > wc - 0.5:
                            e = VITRE                       # verriere du cockpit
                        elif u > 7.5:
                            e = NOIR                        # nez
                        elif u >= -3 and abs(w - wc) < 1.0 and v * v > 4 and int(u) % 3 == 0:
                            e = VITRE                       # hublots de la cabine
                        elif -3 <= u <= -2.5 or (u < -3 and int(u) % 4 == 0):
                            e = GRIS                        # jonctions
                        met(u, v, w, e)
        # ---- porte cargo droite (v > 0) grande ouverte, porte coulissante reculee sur la coque
        for u in range(-2, 3):
            for w in range(1, 5):
                met(u, 3, w, 'AIR'); met(u, 2, w, 'AIR')
        for u in range(-6, -2):
            for w in range(1, 5):
                met(u, 4, w, OLIVE2 if (u + w) % 3 == 0 else OLIVE)
        # ---- carter moteur et mat du rotor sur le dos
        for u in range(-3, 3):
            for v in (-1, 0, 1):
                met(u, v, 6, GRIS)
                met(u, v, 7, GRIS if abs(v) < 1 or u in (-3, 2) else NOIR)
        met(-4, -1, 6, NOIR); met(-4, 1, 6, NOIR)                # tuyeres
        met(0, 0, 8, 'minecraft:iron_block'); met(0, 0, 9, 'minecraft:iron_block')
        # ---- deriviere : derive, stabilisateur, rotor de queue
        for w in range(4, 10):
            for u in range(-16, -13 + (w < 6)):
                met(u, 0, w, OLIVE)
        for v in range(-3, 4):
            met(-15, v, 4, OLIVE)
        # ---- roues (train fixe) : on les voit en l'air, cote gauche contre le sol
        for (u, v) in ((3, -2), (3, 2), (-13, 0)):
            met(u, v, -1, NOIR); met(u, v, -2, NOIR)

        # couche sur le flanc gauche : la hauteur devient v (+4 au-dessus du sol), w part vers +z
        y0 = self.sol(x, z)
        for (u, v, w), e in cel.items():
            px, py, pz = x + u, y0 + 4 + v, z + w - 3
            if e == 'AIR':
                if py > y0:
                    m.pose(px, py, pz, AIR)
            else:
                m.pose(px, py, pz, e)
        # le nez s'est enfonce : terre retournee autour
        for dz in range(-3, 6):
            for dx in range(7, 13):
                yy = self.sol(x + dx, z + dz)
                if rng.random() < 0.6:
                    m.pose(x + dx, yy + 1, z + dz, 'minecraft:coarse_dirt', seulement_air=True)
        # ---- rotor principal casse : une pale plantee dans le sol, une tordue, deux arrachees
        mx, my, mz = x, y0 + 4, z + 6                # mat (couche : il pointe vers +z)
        pale = 'minecraft:polished_blackstone_brick_wall'
        for i in range(1, 11):                        # plantee en biais dans le sol, vers l'est
            m.pose(mx + i, max(my - i // 2, self.sol(mx + i, mz + 2) + 1), mz + 2, pale)
        for i in range(1, 7):                         # tordue vers le haut
            m.pose(mx - i // 2, my + i, mz + 1, pale)
        for i in range(0, 5):                         # pale arrachee, tombee plus loin
            px, pz = x - 9 + i, z + 11
            m.pose(px, self.sol(px, pz) + 1, pz, pale)
        # rotor de queue arrache, a 10 blocs
        tx, tz = x - 24, z + 5
        ty = self.sol(tx, tz) + 1
        for (dx, dy) in ((0, 0), (1, 1), (-1, 1), (0, 2), (1, -0), (0, 1)):
            m.pose(tx + dx, ty + dy, tz, 'minecraft:iron_bars')
        m.pose(tx, ty, tz + 1, 'minecraft:iron_block')
        # ---- degats : trous dans la coque, traces de brulure, fumee qui monte encore du moteur
        coque = [c_ for c_, e in cel.items() if e in (OLIVE, OLIVE2, GRIS) and c_[1] >= 1]   # flanc du dessus
        for i in rng.choice(len(coque), 22, replace=False):
            u, v, w = coque[i]
            m.pose(x + u, y0 + 4 + v, z + w - 3, rng.choice([NOIR, 'minecraft:coal_block', AIR, 'minecraft:blackstone']))
        m.pose(x - 1, y0 + 4, z + 3, 'minecraft:campfire[facing=north,lit=true,signal_fire=true,waterlogged=false]')
        m.pose(x - 1, y0 + 3, z + 3, 'minecraft:hay_block[axis=y]')
        # ---- soute : fret renverse, civiere, sangles, sang (le flanc gauche est devenu le sol)
        ys = y0 + 2                               # le flanc gauche, devenu plancher, est en y0 + 1
        for (u, w) in ((-2, 1), (1, 2), (2, 4)):
            m.pose(x + u, ys, z + w - 3, 'minecraft:barrel[facing=up,open=false]')
        m.pose(x - 1, ys, z - 1, 'minecraft:white_wool'); m.pose(x, ys, z - 1, 'minecraft:white_wool')
        m.pose(x + 2, ys + 1, z + 1, 'minecraft:chain[axis=x,waterlogged=false]')
        m.pose(x - 2, ys + 1, z, 'minecraft:chain[axis=z,waterlogged=false]')
        m.coffre(x, ys, z + 1, 'east', [('minecraft:crossbow', 1), ('minecraft:arrow', 20),
                                                          ('minecraft:golden_apple', 1), ('minecraft:flint_and_steel', 1),
                                                          ('minecraft:spyglass', 1), ('minecraft:cooked_beef', 6)])
        self.k.sang([(x - 1, ys, z), (x + 3, ys, z + 2), (x - 4, self.sol(x - 4, z + 7) + 1, z + 7)], 0.7)
        # ---- sillon : terre arrachee, arbres brises et couches, debris
        for i in range(10, 46):
            px, pz = x + i, z - i // 3
            for d in (-2, -1, 0, 1, 2):
                if rng.random() < 0.8:
                    m.pose(px, self.sol(px, pz + d), pz + d, 'minecraft:coarse_dirt' if rng.random() < 0.7 else 'minecraft:rooted_dirt')
                m.boite(px, self.sol(px, pz + d) + 1, pz + d, px, self.sol(px, pz + d) + 6, pz + d, AIR)
            if i % 9 == 0:
                # tronc casse net et sa partie couchee
                yy = self.sol(px, pz + 3) + 1
                m.boite(px, yy, pz + 3, px, yy + 2, pz + 3, 'minecraft:jungle_log[axis=y]')
                for j in range(1, 7):
                    m.pose(px + j, self.sol(px + j, pz + 4) + 1, pz + 4, 'minecraft:jungle_log[axis=x]')
            if i % 7 == 3:
                m.pose(px, self.sol(px, pz) + 1, pz, rng.choice(['minecraft:iron_trapdoor[facing=north,half=bottom,open=false,powered=false,waterlogged=false]',
                                                                  GRIS, OLIVE, 'minecraft:iron_bars']))
        self.ajoute('Helicoptere abattu', x, z, 26)

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
        """Bungalows de chercheurs sur pilotis au bord du lagon : meme charpente que les maisons
        du village, toit de bambou, escalier jusqu'au sol."""
        m, SEA = self.m, self.r.SEA
        for n, (x, z) in enumerate(pts):
            y = max(self.sol(x, z), SEA) + 4
            self.maison(x - 3, y, z - 3, 7, 7, 'jungle', n % 2 == 0, [0, 3, 1][n % 3], 'bamboo_mosaic',
                        ['white', 'yellow', 'cyan'][n % 3],
                        [('minecraft:cooked_cod', 6), ('minecraft:fishing_rod', 1), ('minecraft:spyglass', 1)] if n == 2 else None)
            # escalier de la veranda jusqu'au sol (ou jusqu'a l'eau)
            vx = x - 3 - 2 if n % 2 == 0 else x - 3 + 8
            for i in range(0, 6):
                zz = z - 3 + 7 + i
                yy = y - 1 - i
                if yy <= self.sol(vx, zz):
                    break
                m.pose(vx, yy + 1, zz, esc('jungle', 'north'))
                m.pose(vx, yy, zz, 'minecraft:jungle_planks')
            self.ajoute('Bungalow', x, z, 10)

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
    def navire(self, x, y_quille, z, cap, L, B, D, style, gite=0.0, tangage=0.0, dechirure=True, rupture=False):
        """Coque de navire en volume : etrave effilee, coque en V arrondi (plus large en haut),
        tonture (pont releve a l'avant et a l'arriere), pont, bastingage, ecoutilles, timonerie
        a l'arriere, cheminee et mat. Modele en coordonnees propres (u : de la poupe a la proue,
        v : babord-tribord, w : de la quille au pont) echantillonne au demi-bloc, puis incline
        (gite autour de u, tangage autour de v) et oriente (cap).
        style 'acier' : caboteur rouille ; 'bois' : bateau de peche.
        Sous le niveau de la mer, l'interieur est noye, la coque se couvre de concretions."""
        m, rng, SEA = self.m, self.rng, self.r.SEA
        cg, sg = math.cos(gite), math.sin(gite)
        cp, sp = math.cos(tangage), math.sin(tangage)
        cc, sc = math.cos(cap), math.sin(cap)
        demiL = L / 2
        proue = L * 0.28

        def larg(u, w):
            if u > demiL - proue:
                t = (u - (demiL - proue)) / proue
                pl = max(0.0, 1 - t * t) ** 0.6
            elif u < -demiL + 2:
                pl = 0.85 + 0.15 * (u + demiL) / 2
            else:
                pl = 1.0
            return B * pl * (max(w, 0.0) / D) ** 0.45 if w < D else B * pl

        def pont(u):
            return D + 1.2 * (u / demiL) ** 2

        def monde(u, v, w):
            if rupture and u < -L * 0.1:
                u2 = u - 2.5                                      # la poupe s'est detachee et a glisse
                w2 = w - 1.5 - (u + L * 0.1) * 0.12
            else:
                u2, w2 = u, w
            v1 = v * cg - w2 * sg
            w1 = v * sg + w2 * cg
            u1 = u2 * cp - w1 * sp
            w3 = u2 * sp + w1 * cp
            return (int(round(x + u1 * cc - v1 * sc)), int(round(y_quille + w3)), int(round(z + u1 * sc + v1 * cc)))

        if style == 'acier':
            coque_h = ['minecraft:red_terracotta', 'minecraft:brown_terracotta', 'minecraft:red_terracotta', 'minecraft:exposed_copper',
                       'minecraft:weathered_copper']
            coque_b = ['minecraft:weathered_copper', 'minecraft:oxidized_copper', 'minecraft:brown_terracotta', 'minecraft:black_terracotta']
            ponts = ['minecraft:spruce_planks'] * 8 + ['minecraft:dark_oak_planks', AIR]
            rambarde = 'minecraft:iron_bars'
        else:
            coque_h = ['minecraft:dark_oak_planks', 'minecraft:spruce_planks', 'minecraft:dark_oak_planks', 'minecraft:white_terracotta']
            coque_b = ['minecraft:dark_oak_planks', 'minecraft:mossy_cobblestone', 'minecraft:dark_oak_planks']
            ponts = ['minecraft:spruce_planks'] * 8 + ['minecraft:oak_planks', AIR]
            rambarde = 'minecraft:dark_oak_fence'
        pas = 0.5
        us = np.arange(-demiL, demiL + 0.01, pas)
        coque, interieur, plancher = {}, set(), {}
        for u in us:
            hp = pont(u)
            for w in np.arange(0, hp + 0.01, pas):
                b = larg(u, w)
                for v in np.arange(-B - 1, B + 1.01, pas):
                    if abs(v) > b:
                        continue
                    p = monde(u, v, w)
                    if abs(v) > b - 1.0 or w < 1.0:
                        coque[p] = (u, v, w)
                    else:
                        interieur.add(p)
            # pont
            for v in np.arange(-B, B + 0.01, pas):
                if abs(v) <= larg(u, hp):
                    plancher[monde(u, v, hp)] = (u, v)
        # dechirure : grand trou dans le bordage, a l'avant tribord (le choc sur le recif)
        trou = set()
        if dechirure:
            for p, (u, v, w) in coque.items():
                if v > 0 and demiL * 0.15 < u < demiL * 0.55 and 0.8 < w < D * 0.7 and \
                        ((u - demiL * 0.35) / (demiL * 0.22)) ** 2 + ((w - D * 0.4) / (D * 0.33)) ** 2 < 1:
                    trou.add(p)
        # interieur (eau sous la mer), puis coque, puis pont
        for p in interieur:
            if p not in coque:
                m.pose(p[0], p[1], p[2], EAU if p[1] <= SEA else AIR)
        for p, (u, v, w) in coque.items():
            if p in trou:
                m.pose(p[0], p[1], p[2], EAU if p[1] <= SEA else AIR)
                continue
            # plaques de rouille / d'oxydation continues (pas un tirage bloc par bloc)
            tache = math.sin(u * 0.55 + w * 1.1 + v * 0.3) + math.sin(u * 0.21 - w * 0.7 + 2.0)
            if p[1] <= SEA:
                e = coque_b[0] if tache > 0.3 else (coque_b[1] if tache > -0.6 else coque_b[2])
            else:
                e = coque_h[0] if tache > 0.2 else (coque_h[1] if tache > -0.8 else coque_h[3])
                if style == 'acier' and 1.5 < w < 2.3:
                    e = 'minecraft:black_terracotta'                      # la ligne de flottaison peinte
            m.pose(p[0], p[1], p[2], e)
        ecoutilles = [(-demiL * 0.1, demiL * 0.25), (demiL * 0.3, demiL * 0.5)]
        for p, (u, v) in plancher.items():
            if any(a < u < b for a, b in ecoutilles) and abs(v) < B * 0.5:
                continue                                                   # ecoutilles ouvertes sur les cales
            e = ponts[int(rng.integers(0, len(ponts)))]
            if p[1] <= SEA and e != AIR:
                e = 'minecraft:dark_oak_planks'
            m.pose(p[0], p[1], p[2], e if e != AIR else (EAU if p[1] <= SEA else AIR))
        # bastingage
        for u in us[::2]:
            if u < -demiL + 1:
                continue
            for sgn in (-1, 1):
                p = monde(u, sgn * (larg(u, pont(u)) - 0.3), pont(u) + 1)
                if rng.random() < 0.8:
                    m.pose(p[0], p[1], p[2], rambarde, seulement_air=True)
        # timonerie a l'arriere, cheminee, mat
        tu0, tu1 = -demiL + 1.5, -demiL + (7 if style == 'acier' else 4.5)
        th = 4 if style == 'acier' else 3
        for u in np.arange(tu0, tu1 + 0.01, pas):
            bb = larg(u, pont(u)) - 1.2
            for v in np.arange(-bb, bb + 0.01, pas):
                for w in np.arange(pont(u) + 0.5, pont(u) + th + 0.51, pas):
                    p = monde(u, v, w)
                    bord = abs(v) > bb - 0.6 or u < tu0 + 0.6 or u > tu1 - 0.6 or w > pont(u) + th
                    if not bord:
                        m.pose(p[0], p[1], p[2], EAU if p[1] <= SEA else AIR)
                        continue
                    fenetre = w > pont(u) + th - 1.6 and w < pont(u) + th - 0.4 and u > tu1 - 0.6 and abs(v) < bb - 0.8
                    if fenetre:
                        e = (EAU if p[1] <= SEA else AIR) if rng.random() < 0.5 else 'minecraft:glass_pane'
                    elif w > pont(u) + th:
                        e = 'minecraft:light_gray_concrete' if style == 'acier' else 'minecraft:spruce_planks'
                    else:
                        e = 'minecraft:white_terracotta' if (style != 'acier' or math.sin(u * 0.9 + w) > -0.5) \
                            else 'minecraft:light_gray_concrete'
                    m.pose(p[0], p[1], p[2], e)
        if style == 'acier':
            cu = tu0 + 1.5
            for w in np.arange(pont(cu) + th + 1, pont(cu) + th + 5, pas):
                for a in range(0, 360, 30):
                    p = monde(cu + 0.9 * math.cos(math.radians(a)), 0.9 * math.sin(math.radians(a)), w)
                    m.pose(p[0], p[1], p[2], 'minecraft:black_concrete' if w > pont(cu) + th + 3.5 else 'minecraft:red_concrete')
        mu = demiL * 0.45
        hm = 9 if style == 'acier' else 7
        for w in np.arange(pont(mu), pont(mu) + hm, pas):
            p = monde(mu + (w - pont(mu)) * (0.25 if w > pont(mu) + hm * 0.6 else 0), 0, w)   # tete du mat pliee
            m.pose(p[0], p[1], p[2], 'minecraft:stripped_spruce_log[axis=y]' if style == 'bois' else 'minecraft:chain[axis=y,waterlogged=false]')
        for v in np.arange(-B * 0.7, B * 0.7 + 0.01, pas):
            p = monde(mu, v, pont(mu) + hm * 0.55)
            m.pose(p[0], p[1], p[2], 'minecraft:chain[axis=x,waterlogged=false]' if abs(cc) < 0.7 else 'minecraft:chain[axis=z,waterlogged=false]')
        # concretions sur la coque immergee
        for p in list(coque)[::7]:
            if p[1] < SEA - 1 and rng.random() < 0.4:
                for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if m.get(p[0] + dx, p[1], p[2] + dz) == m.P(EAU):
                        f = {(1, 0): 'east', (-1, 0): 'west', (0, 1): 'south', (0, -1): 'north'}[(dx, dz)]
                        m.pose(p[0] + dx, p[1], p[2] + dz, 'minecraft:%s_coral_wall_fan[facing=%s,waterlogged=true]'
                               % (rng.choice(['brain', 'tube', 'horn', 'fire', 'bubble']), f))
                        break
        return monde

    def epave(self, x, z):
        """Caboteur rouille echoue sur le recif : etrave montee sur le recif, poupe dans l'eau
        profonde et detachee, gite de 25 degres, flanc tribord eventre, cales noyees."""
        m, r, SEA = self.m, self.r, self.r.SEA
        # orientation : l'etrave vers la terre (vers le centre du lagon)
        gx, gz = self.r.D(178, 612) if hasattr(self.r, 'D') else (178, 612)
        cap = math.atan2(gz - z, gx - x)
        fond = int(np.median(r.h[z - 6:z + 7, x - 6:x + 7]))
        self.navire(x, fond - 1, z, cap, 30, 4.5, 6.5, 'acier', gite=math.radians(25), tangage=math.radians(-6),
                    dechirure=True, rupture=True)
        m.coffre(x, fond + 2, z, 'north', [('minecraft:gold_ingot', 6), ('minecraft:compass', 1), ('minecraft:nautilus_shell', 2),
                                           ('minecraft:trident', 1)])
        self.ajoute('Epave', x, z, 20)

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
        # une carcasse entiere, en os
        self.k.carcasse(x, self.sol(x + 3, z) + 1, z, True, 9, 1)
        self.ajoute('Ilot aux carcasses', x, z, 10)

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
        y = max(int(y), r.SEA + 1)                 # jamais sous la mer : l'air degage au-dessus toucherait l'eau
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

    # ================================================================== temple maya en ruine
    def temple(self, x, z):
        """Pyramide maya a degres (facon Tikal) : 8 terrasses en talud-tablero a angles rentrants,
        escalier central raide borde de rampes et gardé par deux tetes de serpent, sanctuaire au
        sommet (murs epais, trois portes, voute en encorbellement, frise), crete ajouree sur le
        toit. Devant : place et steles. A cote : un cenote (puits noye) et un nid sur sa corniche.
        Dedans : galerie basse (2 blocs, il n'y entre pas) vers la chambre du tresor."""
        m, k, rng = self.m, self.k, self.rng
        N, HT, B = 8, 4, 21                     # terrasses, hauteur d'une terrasse, demi-base
        y0 = self.sol_moyen(x - B, z - B, x + B, z + B)
        Htot = N * HT
        bt = B - (N - 1) * 2                    # demi-cote de la plate-forme sommitale (7)
        z_esc = z + bt + Htot + 1               # pied de l'escalier (il deborde vers le sud)
        self.plateforme(x - B - 6, z - B - 6, x + B + 6, z_esc + 16, y0, 'minecraft:mossy_cobblestone', 'minecraft:stone', 60)
        pierre = ['minecraft:stone_bricks', 'minecraft:stone_bricks', 'minecraft:cracked_stone_bricks', 'minecraft:mossy_stone_bricks',
                  'minecraft:andesite', 'minecraft:polished_andesite', 'minecraft:mossy_cobblestone', 'minecraft:stone']
        ids = np.array([m.P(e) for e in pierre], np.uint16)
        mousse = np.array([m.P('minecraft:mossy_stone_bricks'), m.P('minecraft:mossy_cobblestone'), m.P('minecraft:moss_block')], np.uint16)

        def masse(x0, y0_, z0, x1, y1, z1, frac_mousse=0.25):
            zone = m.blocs[y0_:y1 + 1, z0:z1 + 1, x0:x1 + 1]
            zone[...] = ids[rng.integers(0, len(ids), zone.shape)]
            mo = rng.random(zone.shape) < frac_mousse
            zone[mo] = mousse[rng.integers(0, len(mousse), int(mo.sum()))]

        # ---- les terrasses : talud (pente), tablero (panneau vertical a bandeau en retrait), corniche
        for n in range(N):
            b = B - n * 2
            ya = y0 + 1 + n * HT
            masse(x - b + 1, ya, z - b + 1, x + b - 1, ya + HT - 1, z + b - 1, 0.35 - n * 0.03)
            anneau = []
            for i in range(-b, b + 1):
                anneau += [(x + i, z - b, 'north'), (x + i, z + b, 'south'), (x - b, z + i, 'west'), (x + b, z + i, 'east')]
            for (px, pz, face) in anneau:
                coin = abs(px - x) == b and abs(pz - z) == b
                if coin:
                    continue                      # angles rentrants
                # talud : marche inclinee vers l'exterieur (le dos de la marche vers le centre)
                m.pose(px, ya, pz, esc('mossy_stone_brick' if rng.random() < 0.5 else 'stone_brick', OPP[face]))
                m.pose(px, ya + 1, pz, pierre[rng.integers(0, 4)])
                # bandeau en retrait : un bloc sur deux, laisse en creux (ombre du tablero)
                if (px + pz) % 2 == 0:
                    m.pose(px, ya + 2, pz, 'minecraft:chiseled_stone_bricks' if (px * 3 + pz) % 7 == 0 else pierre[rng.integers(0, 3)])
                m.pose(px, ya + 3, pz, 'minecraft:polished_andesite' if rng.random() < 0.7 else 'minecraft:mossy_stone_bricks')
            for (sx, sz) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                m.boite(x + sx * (b - 1), ya, z + sz * (b - 1), x + sx * (b - 1), ya + HT - 1, z + sz * (b - 1), pierre[rng.integers(0, 4)])
        top = y0 + Htot
        # ---- escalier central : 9 de large, une marche par bloc, rampes (alfardas) de chaque cote
        for i in range(Htot):
            yy = y0 + 1 + i
            zz = z_esc - i
            m.boite(x - 4, yy, zz, x + 4, yy, zz, esc('stone_brick' if rng.random() < 0.7 else 'mossy_stone_brick', 'north'))
            m.boite(x - 4, y0 + 1, zz, x + 4, yy - 1, zz, 'minecraft:stone_bricks')
            m.boite(x - 4, yy + 1, zz, x + 4, yy + 4, zz, AIR)
            for sx in (-5, 5):
                m.boite(x + sx, y0 + 1, zz, x + sx, yy + 1, zz, 'minecraft:polished_andesite')
                m.pose(x + sx, yy + 2, zz, 'minecraft:andesite_wall')
        # marches usees ou manquantes
        for _ in range(10):
            i = int(rng.integers(2, Htot - 2)); dx = int(rng.integers(-4, 5))
            m.pose(x + dx, y0 + 1 + i, z_esc - i, rng.choice(['minecraft:mossy_cobblestone', 'minecraft:moss_block', 'minecraft:cracked_stone_bricks']))
        # tetes de serpent au pied des rampes : gueule ouverte vers le sud
        for sx in (-6, 6):
            hx, hz, hy = x + sx, z_esc + 1, y0 + 1
            m.boite(hx - 1, hy, hz - 1, hx + 1, hy + 2, hz + 1, 'minecraft:mossy_stone_bricks')
            m.boite(hx - 1, hy + 1, hz + 1, hx + 1, hy + 1, hz + 1, AIR)                   # gueule
            m.pose(hx - 1, hy + 2, hz + 1, 'minecraft:chiseled_stone_bricks'); m.pose(hx + 1, hy + 2, hz + 1, 'minecraft:chiseled_stone_bricks')
            m.pose(hx, hy, hz + 2, 'minecraft:stone_brick_slab[type=bottom,waterlogged=false]')   # machoire
        # ---- sanctuaire : 13 x 9, murs de 2, trois portes au sud, voute en encorbellement, frise
        ts = top + 1
        masse(x - 6, ts, z - 4, x + 6, ts + 6, z + 4, 0.15)
        m.boite(x - 4, ts, z - 2, x + 4, ts + 3, z + 2, AIR)                # la salle
        m.boite(x - 3, ts + 4, z - 1, x + 3, ts + 4, z + 1, AIR)            # encorbellement
        m.boite(x - 2, ts + 5, z, x + 2, ts + 5, z, AIR)
        for dxp in (-3, 0, 3):
            m.boite(x + dxp, ts, z + 3, x + dxp, ts + 2, z + 4, AIR)        # portes (murs epais)
        for i in range(-6, 7):                                             # frise sculptee
            if i % 2 == 0:
                m.pose(x + i, ts + 5, z + 4, 'minecraft:chiseled_stone_bricks')
                m.pose(x + i, ts + 5, z - 4, 'minecraft:chiseled_stone_bricks')
        m.boite(x - 7, ts + 6, z - 5, x + 7, ts + 6, z + 5, 'minecraft:polished_andesite')   # corniche du toit
        # ---- crete faitiere ajouree (cresteria), en retrait vers l'arriere
        for j in range(9):
            demi = 5 - j // 3
            yy = ts + 7 + j
            m.boite(x - demi, yy, z - 2, x + demi, yy, z - 1, 'minecraft:stone_bricks' if j % 3 else 'minecraft:polished_andesite')
            if j in (1, 2, 4, 5):
                for hx in range(x - demi + 1, x + demi, 3):
                    m.pose(hx, yy, z - 2, AIR); m.pose(hx, yy, z - 1, AIR)       # jours de la crete
        m.pose(x, ts + 16, z - 2, 'minecraft:chiseled_stone_bricks'); m.pose(x, ts + 16, z - 1, 'minecraft:chiseled_stone_bricks')
        # autel et fresque en os dans le sanctuaire
        m.boite(x - 1, ts, z - 2, x + 1, ts, z - 2, 'minecraft:polished_andesite')
        m.pose(x, ts + 1, z - 2, 'minecraft:skeleton_skull[rotation=0]')
        for (dx, dy) in ((-3, 1), (-2, 1), (-1, 1), (0, 1), (1, 1), (2, 2), (3, 2), (-1, 2), (0, 2), (0, 3), (1, 2), (-2, 2)):
            m.pose(x + dx, ts + dy, z - 3, 'minecraft:bone_block[axis=y]')
        # ---- galerie basse vers la chambre du tresor, depuis la face est
        yb = y0 + 1
        m.boite(x + 2, yb, z - 1, x + B + 1, yb + 1, z, AIR)
        m.boite(x - 4, yb, z - 4, x + 4, yb + 3, z + 4, AIR)
        for (dx, dz) in ((-4, -4), (4, -4), (-4, 4), (4, 4)):
            m.boite(x + dx, yb, z + dz, x + dx, yb + 3, z + dz, 'minecraft:chiseled_stone_bricks')
        m.coffre(x, yb, z - 3, 'south', [('minecraft:gold_ingot', 8), ('minecraft:emerald', 5), ('minecraft:golden_apple', 2),
                                         ('minecraft:experience_bottle', 8), ('minecraft:diamond', 3)])
        for (dx, dz) in ((-3, 3), (3, 3), (-3, -3), (3, -3)):
            m.pose(x + dx, yb, z + dz, 'minecraft:skeleton_skull[rotation=%d]' % rng.integers(0, 16))
        m.pose(x + 1, yb, z + 2, 'minecraft:bone_block[axis=x]'); m.pose(x + 2, yb, z + 2, 'minecraft:bone_block[axis=x]')
        k.toiles(x - 3, yb, z - 3, x + 3, yb + 3, z + 3, 8)
        # ---- ruine : pans effondres, vegetation sur les gradins, lianes
        for _ in range(5):
            n_ = int(rng.integers(1, N - 1)); b = B - n_ * 2
            cx = x + int(rng.choice([-b, b])); cz = z + int(rng.integers(-b, b))
            if abs(cx - x) < 7:
                continue
            m.ellipsoide(cx, y0 + n_ * HT + 2, cz, rng.uniform(2, 3.5), rng.uniform(2, 3), rng.uniform(2, 3.5), AIR, seulement_air=False)
            for _ in range(6):                                                  # eboulis au pied
                ex, ez = cx + int(rng.integers(-5, 6)), cz + int(rng.integers(-5, 6))
                if abs(ex - x) > B or abs(ez - z) > B:
                    m.pose(ex, self.sol(ex, ez) + 1, ez, rng.choice(['minecraft:mossy_cobblestone', 'minecraft:cobblestone',
                                                                     'minecraft:mossy_stone_brick_slab[type=bottom,waterlogged=false]']))
        for n_ in range(N):
            b = B - n_ * 2 - 1
            ya = y0 + (n_ + 1) * HT + 1
            for _ in range(int(rng.integers(3, 7))):
                px, pz = x + int(rng.integers(-b, b + 1)), z + int(rng.integers(-b, b + 1))
                if abs(px - x) <= 5 and pz > z:
                    continue                                                    # pas sur l'escalier
                if m.get(px, ya, pz) == m.AIR and m.get(px, ya - 1, pz) != m.AIR:
                    m.pose(px, ya, pz, rng.choice(['minecraft:moss_carpet', 'minecraft:fern', 'minecraft:azalea',
                                                   'minecraft:flowering_azalea', 'minecraft:jungle_leaves[distance=1,persistent=true,waterlogged=false]']))
        from arbres import vigne
        for _ in range(260):
            face = ['north', 'south', 'east', 'west'][rng.integers(0, 4)]
            n_ = int(rng.integers(0, N)); b = B - n_ * 2
            i = int(rng.integers(-b + 1, b))
            if face == 'south' and abs(i) <= 6:
                continue
            px, pz = {'north': (x + i, z + b + 1), 'south': (x + i, z - b - 1), 'west': (x + b + 1, z + i), 'east': (x - b - 1, z + i)}[face]
            px, pz = {'north': (x + i, z - b - 1), 'south': (x + i, z + b + 1), 'west': (x - b - 1, z + i), 'east': (x + b + 1, z + i)}[face]
            att = OPP[face]
            for yy in range(y0 + (n_ + 1) * HT, y0 + n_ * HT, -1):
                if m.get(px, yy, pz) == m.AIR:
                    m.pose(px, yy, pz, vigne(att))
        # ---- la place : steles et autels ronds
        for i, sx in enumerate((-12, -7, 7, 12)):
            px, pz = x + sx, z_esc + 9
            m.boite(px, y0 + 1, pz, px + 1, y0 + 4, pz, 'minecraft:polished_andesite')
            m.pose(px, y0 + 3, pz, 'minecraft:chiseled_stone_bricks'); m.pose(px + 1, y0 + 2, pz, 'minecraft:chiseled_stone_bricks')
            m.pose(px + (i % 2), y0 + 5, pz, 'minecraft:mossy_stone_brick_wall')
            m.pose(px, y0 + 1, pz + 2, 'minecraft:andesite_slab[type=bottom,waterlogged=false]')
            m.pose(px + 1, y0 + 1, pz + 2, 'minecraft:andesite_slab[type=bottom,waterlogged=false]')
            if i == 2:
                m.boite(px, y0 + 1, pz, px + 1, y0 + 4, pz, AIR)                 # stele renversee
                m.boite(px - 3, y0 + 1, pz + 1, px, y0 + 1, pz + 1, 'minecraft:polished_andesite')
        self.ajoute('Temple maya en ruine', x, z, B + 13)
        self.ajoute('', x, z_esc + 8, 16)                                     # la place et les steles
        self.cenote(x - B - 20, z + 4)

    def cenote(self, x, z):
        """Puits naturel noye : parois verticales, eau 12 blocs sous le bord, racines et lianes
        pendantes, corniche avec un nid a 2 blocs au-dessus de l'eau."""
        m, r, rng = self.m, self.r, self.rng
        R = 9
        if not (R + 4 <= x < r.W - R - 4 and R + 4 <= z < r.L - R - 4):
            return
        zone_e = r.eau[z - R - 3:z + R + 4, x - R - 3:x + R + 4] > r.h[z - R - 3:z + R + 4, x - R - 3:x + R + 4]
        if zone_e.any():
            return
        y_bord = int(r.h[z - R - 3:z + R + 4, x - R - 3:x + R + 4].min())
        eau_y = y_bord - 12
        fond = eau_y - 9
        if fond < 4:
            return
        from arbres import vigne
        # parois irregulieres : le rayon varie avec l'angle et la hauteur (niches, surplombs,
        # rebords), et la levre du haut avance au-dessus du vide
        Rmax = R + 3
        roche = ['minecraft:stone', 'minecraft:tuff', 'minecraft:stone', 'minecraft:andesite', 'minecraft:mossy_cobblestone']
        for dz in range(-Rmax - 1, Rmax + 2):
            for dx in range(-Rmax - 1, Rmax + 2):
                px, pz = x + dx, z + dz
                d = math.hypot(dx, dz)
                th = math.atan2(dz, dx)
                if d > Rmax + 1:
                    continue
                hs = int(r.h[pz, px])
                for yy in range(fond, hs + 1):
                    Ry = R + 1.6 * math.sin(3 * th + 0.35 * yy) + 0.9 * math.sin(7 * th - 0.23 * yy + 1)
                    if yy >= y_bord - 2:
                        Ry -= 2.0                                  # la levre en surplomb
                    if (yy - eau_y) in (3, 4, 8):
                        Ry -= 1.3                                  # rebords
                    if d <= Ry:
                        m.pose(px, yy, pz, 'minecraft:gravel' if yy == fond else (EAU if yy <= eau_y else AIR))
                    else:
                        m.pose(px, yy, pz, roche[int(abs(math.sin(px * 3.1 + yy * 1.7 + pz * 2.3)) * 5) % 5]
                               if yy < hs - 1 or d <= Rmax - 1 else m.nom(m.get(px, yy, pz)))
                if d <= R - 2.5:
                    m.boite(px, hs + 1, pz, px, hs + 8, pz, AIR)
                    r.h[pz, px] = fond; r.eau[pz, px] = eau_y
        # corniche au nord-est, avec le nid
        cx, cz = x + R - 3, z - R + 3
        for dz in range(-3, 4):
            for dx in range(-3, 4):
                if math.hypot(dx, dz) <= 3.3:
                    m.boite(cx + dx, fond, cz + dz, cx + dx, eau_y + 1, cz + dz, 'minecraft:stone')
                    r.h[cz + dz, cx + dx] = eau_y + 1; r.eau[cz + dz, cx + dx] = -1
        self.nid_simple(cx, eau_y + 2, cz)
        # lianes qui pendent le long des parois, du bord jusqu'a l'eau pour certaines
        for _ in range(90):
            a = rng.uniform(0, 2 * math.pi)
            ca, sa = math.cos(a), math.sin(a)
            px, pz = x + int(round(ca * (R - 0.6))), z + int(round(sa * (R - 0.6)))
            att = ('east' if ca > 0 else 'west') if abs(ca) > abs(sa) else ('south' if sa > 0 else 'north')
            ddx, ddz = {'east': (1, 0), 'west': (-1, 0), 'south': (0, 1), 'north': (0, -1)}[att]
            for k_ in range(int(rng.integers(3, 13))):
                yy = y_bord - k_
                if yy <= eau_y or m.get(px, yy, pz) != m.AIR or m.get(px + ddx, yy, pz + ddz) == m.AIR:
                    break
                m.pose(px, yy, pz, vigne(att))
        self.ajoute('Cenote', x, z, R + 4)

    def nid_simple(self, x, y, z):
        """Nid de spinosaure : cuvette de vase, couronne de racines tressees, oeufs, ossements."""
        m, rng = self.m, self.rng
        for dz in range(-3, 4):
            for dx in range(-3, 4):
                d = math.hypot(dx, dz)
                if d <= 2.2:
                    m.pose(x + dx, y - 1, z + dz, 'minecraft:mud')
                elif d <= 3.3:
                    m.pose(x + dx, y, z + dz, 'minecraft:mangrove_roots[waterlogged=false]')
        for (dx, dz) in ((0, 0), (1, 0), (0, 1), (-1, 0)):
            m.pose(x + dx, y, z + dz, 'minecraft:sniffer_egg[hatch=%d]' % rng.integers(0, 2))
        m.pose(x + 1, y, z - 1, 'minecraft:bone_block[axis=x]')

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
        # carcasses d'herbivores : squelettes d'os couches dans l'herbe
        for _ in range(5):
            px = int(rng.integers(x0 + 10, x1 - 14)); pz = int(rng.integers(z0 + 10, z1 - 14))
            k.carcasse(px, self.sol(px, pz) + 1, pz, rng.random() < 0.5, int(rng.integers(8, 12)), int(rng.choice([-1, 1])))
        m.panneau(cx, yc, cz - 2, 'north', ['Il ne reste', 'rien. Il est entre', "par l'eau et", 'ressorti par la.'], mural=False)
        self.ajoute('Enclos des herbivores', cx, cz, 0)

    # ================================================================== maison sur pilotis
    def maison(self, hx, yp, hz, Lx, Lz, bois, porte_ouest, variante, toit='dark_oak', couleur_lit='white', coffre=None):
        """Maison de pecheur sur pilotis. Plancher en (hx..hx+Lx-1, yp, hz..hz+Lz-1).
        Charpente apparente (poteaux et sabliere en rondins ecorces), bardage de planches,
        fenetres a volets, veranda couverte avec garde-corps du cote de la porte, toit a deux
        pans debordant avec pignons, cheminee de pierre, interieur meuble. variante : 0 intacte,
        1 porte arrachee et griffures, 2 toit creve, 3 fenetres brisees et toiles."""
        m, rng = self.m, self.rng
        v = Decale(m, hx, yp, hz)
        kv = Kit(v, rng)
        LOG = 'minecraft:stripped_%s_log[axis=%%s]' % bois
        PL = 'minecraft:%s_planks' % bois
        # ---- pilotis et contreventement
        px_ = [0, Lx // 2, Lx - 1]
        for dx in px_:
            for dz in (0, Lz - 1):
                for yy in range(self.sol(hx + dx, hz + dz) - yp - 2, 0):
                    v.pose(dx, yy, dz, LOG % 'y')
        v.boite(0, -1, 0, Lx - 1, -1, 0, LOG % 'x'); v.boite(0, -1, Lz - 1, Lx - 1, -1, Lz - 1, LOG % 'x')
        # ---- plancher, veranda
        v.boite(0, 0, 0, Lx - 1, 0, Lz - 1, PL)
        vx0, vx1 = (-2, -1) if porte_ouest else (Lx, Lx + 1)
        v.boite(vx0, 0, 0, vx1, 0, Lz - 1, PL)
        bord = vx0 if porte_ouest else vx1
        for dz in range(Lz):
            if dz not in (Lz // 2 - 1, Lz // 2):
                v.pose(bord, 1, dz, 'minecraft:%s_fence' % bois)
        for dz in (0, Lz - 1):
            v.boite(bord, 1, dz, bord, 3, dz, LOG % 'y')
            for yy in range(self.sol(hx + bord, hz + dz) - yp - 2, 0):
                v.pose(bord, yy, dz, LOG % 'y')
        # auvent de la veranda
        v.boite(vx0, 4, -1, vx1, 4, Lz, 'minecraft:%s_slab[type=bottom,waterlogged=false]' % toit)
        # ---- murs : bardage, poteaux, sabliere
        v.boite(0, 1, 0, Lx - 1, 3, Lz - 1, PL)
        v.boite(1, 1, 1, Lx - 2, 3, Lz - 2, AIR)
        for dx in px_:
            for dz in (0, Lz - 1):
                v.boite(dx, 1, dz, dx, 3, dz, LOG % 'y')
        v.boite(0, 4, 0, Lx - 1, 4, 0, LOG % 'x'); v.boite(0, 4, Lz - 1, Lx - 1, 4, Lz - 1, LOG % 'x')
        v.boite(0, 4, 0, 0, 4, Lz - 1, LOG % 'z'); v.boite(Lx - 1, 4, 0, Lx - 1, 4, Lz - 1, LOG % 'z')
        v.boite(1, 4, Lz // 2, Lx - 2, 4, Lz // 2, LOG % 'x')              # entrait (on y pend la lanterne)
        # ---- fenetres a volets (murs nord et sud)
        brisees = variante == 3
        for wx in (2, Lx - 3):
            for wz, face, ext in ((0, 'north', -1), (Lz - 1, 'south', Lz)):
                v.pose(wx, 2, wz, AIR if (brisees and rng.random() < 0.7) else 'minecraft:glass_pane')
                for sx in (-1, 1):
                    if rng.random() < 0.85:
                        v.pose(wx + sx, 2, ext, 'minecraft:%s_trapdoor[facing=%s,half=top,open=true,powered=false,waterlogged=false]'
                               % (bois, face))
        # ---- porte (cote veranda)
        dxp = 0 if porte_ouest else Lx - 1
        v.boite(dxp, 1, Lz // 2, dxp, 2, Lz // 2, AIR)
        if variante != 1:
            kv.porte(dxp, 1, Lz // 2, 'west' if porte_ouest else 'east', bois, ouverte=rng.random() < 0.5)
        else:
            # porte arrachee, jetee sur la veranda ; trois griffures dans le bardage
            v.pose(vx0 + (1 if porte_ouest else 0), 1, Lz // 2 + 1, 'minecraft:%s_trapdoor[facing=north,half=bottom,open=false,powered=false,waterlogged=false]' % bois)
            gz = Lz - 1
            for i, gx in enumerate((Lx // 2 - 1, Lx // 2, Lx // 2 + 1)):
                v.boite(gx, 1 + i % 2, gz, gx, 2 + i % 2, gz, AIR)
        # ---- toit a deux pans (faitage selon x), debord d'un bloc, pignons fermes
        for zz in range(-1, Lz + 1):
            d = min(zz + 1, Lz - zz)                     # 1 au bord, croit vers le faitage
            yr = 4 + d
            milieu = (Lz % 2 == 1 and zz == Lz // 2) or (Lz % 2 == 0 and zz in (Lz // 2 - 1, Lz // 2))
            etat = ('minecraft:%s_slab[type=bottom,waterlogged=false]' % toit) if milieu else esc(toit, 'south' if zz < Lz / 2 else 'north')
            v.boite(-1, yr, zz, Lx, yr, zz, etat)
            if 0 <= zz < Lz:
                for gx in (0, Lx - 1):
                    v.boite(gx, 5, zz, gx, yr - 1, zz, PL)                 # pignons
        # mousse sur le toit
        for _ in range(Lx):
            tx, tz = int(rng.integers(-1, Lx + 1)), int(rng.integers(-1, Lz + 1))
            d = min(tz + 1, Lz - tz)
            v.pose(tx, 5 + d, tz, 'minecraft:moss_carpet', seulement_air=True)
        if variante == 2:
            # toit creve (arbre tombe ou autre chose) : trou et gravats a l'interieur
            cx = Lx // 2
            for zz in range(0, Lz // 2 + 1):
                for xx in (cx - 1, cx, cx + 1):
                    v.pose(xx, 4 + min(zz + 1, Lz - zz), zz, AIR)
            for xx, zz in ((cx, 1), (cx + 1, 2), (cx - 1, 2)):
                v.pose(xx, 1, zz, 'minecraft:%s_slab[type=bottom,waterlogged=false]' % toit)
        # ---- cheminee de pierre, cote oppose a la porte
        cx = Lx - 2 if porte_ouest else 1
        ch = Lz - 2
        haut = 4 + min(ch + 1, Lz - ch) + 2
        v.boite(cx, 1, ch, cx, haut, ch, 'minecraft:cobblestone')
        v.pose(cx, haut + 1, ch, 'minecraft:cobblestone_wall')
        v.pose(cx, 1, ch - 1, 'minecraft:smoker[facing=%s,lit=false]' % ('west' if porte_ouest else 'east'))
        # ---- interieur
        lx_ = 1 if porte_ouest else Lx - 2
        kv.lit(Lx - 2 if porte_ouest else 1, 1, 1, 'north' if False else 'south', couleur_lit)
        tx = Lx // 2
        kv.table(tx, 1, Lz // 2 + (1 if Lz > 6 else 0), 'spruce')
        kv.chaise(tx - 1, 1, Lz // 2 + (1 if Lz > 6 else 0), 'east', bois)
        kv.chaise(tx + 1, 1, Lz // 2 + (1 if Lz > 6 else 0), 'west', bois)
        v.pose(lx_, 1, 1, 'minecraft:barrel[facing=up,open=false]')
        v.pose(lx_, 2, 1, 'minecraft:%s_trapdoor[facing=%s,half=top,open=false,powered=false,waterlogged=false]'
               % (bois, 'east' if porte_ouest else 'west'))
        v.pose(lx_, 1, Lz - 2, 'minecraft:cauldron')
        v.pose(Lx // 2, 1, 1, 'minecraft:%s_carpet' % ['brown', 'red', 'green', 'blue', 'cyan', 'orange'][variante % 6], seulement_air=True)
        v.pose(Lx // 2 - 1, 1, Lz - 2, 'minecraft:%s_carpet' % ['brown', 'red', 'green', 'blue', 'cyan', 'orange'][variante % 6], seulement_air=True)
        kv.lanterne(Lx // 2, 3, Lz // 2)
        if coffre:
            v.coffre(lx_, 1, 2, 'east' if porte_ouest else 'west', coffre)
        if variante == 3:
            kv.toiles(1, 1, 1, Lx - 2, 3, Lz - 2, 4)
        kv.veilleuses(1, 1, Lx - 2, Lz - 2, 3, 3, 3)
        # ---- dehors : lierre sur un pignon, filets et nasses sur la veranda
        from arbres import vigne
        gx, face = (Lx, 'west') if porte_ouest else (-1, 'east')       # pignon oppose a la porte
        for zz in range(Lz):
            if rng.random() < 0.55:
                for yy in range(4, int(rng.integers(0, 4)), -1):
                    v.pose(gx, yy, zz, vigne(face), seulement_air=True)
        v.pose(vx1 if porte_ouest else vx0, 1, 0, 'minecraft:barrel[facing=up,open=false]')
        v.pose(vx1 if porte_ouest else vx0, 1, Lz - 1, 'minecraft:dried_kelp_block')

    # ================================================================== village de pecheurs
    def village(self, x, z, n=6):
        """Maisons sur pilotis de part et d'autre d'un ponton ; veranda sur le ponton, sechoirs,
        barques. Chaque maison differe (taille, bois, toit, etat d'abandon)."""
        m, k, rng, SEA = self.m, self.k, self.rng, self.r.SEA
        yp = SEA + 2
        # ponton principal (nord-sud)
        for dz in range(-(n // 2) * 14 - 6, 8):
            for dx in (-1, 0, 1):
                m.pose(x + dx, yp, z + dz, 'minecraft:spruce_planks')
            if dz % 5 == 0:
                for dx in (-2, 2):
                    self.pilier(x + dx, z + dz, yp + 2, 'minecraft:stripped_spruce_log[axis=y]')
            for dx in (-2, 2):
                if dz % 5:
                    m.pose(x + dx, yp + 1, z + dz, 'minecraft:spruce_fence')
        bois = ['spruce', 'jungle', 'mangrove', 'dark_oak', 'spruce', 'jungle']
        toits = ['dark_oak', 'spruce', 'mangrove', 'spruce', 'mangrove', 'dark_oak']
        tailles = [(8, 7), (7, 6), (9, 7), (7, 7), (8, 6), (9, 7)]
        variantes = [0, 1, 3, 2, 0, 3]
        for i in range(n):
            zc = z - 6 - (i // 2) * 14
            cote = -1 if i % 2 else 1
            Lx, Lz = tailles[i % len(tailles)]
            hx = x + 5 if cote > 0 else x - 5 - (Lx - 1)
            hz = zc - Lz + 1
            coffre = ([('minecraft:fishing_rod', 1), ('minecraft:cooked_salmon', 8), ('minecraft:oak_boat', 1),
                       ('minecraft:crossbow', 1), ('minecraft:arrow', 16)] if i == 3 else None)
            self.maison(hx, yp, hz, Lx, Lz, bois[i % 6], cote > 0, variantes[i % 6], toits[i % 6],
                        ['white', 'brown', 'blue', 'green', 'yellow', 'gray'][i], coffre)
            # passage entre le ponton et la veranda : on ouvre le garde-corps
            for dz in (Lz // 2 - 1, Lz // 2):
                for dx in (2, 3, 4):
                    m.pose(x + dx * cote, yp, hz + dz, 'minecraft:spruce_planks')
                    m.pose(x + dx * cote, yp + 1, hz + dz, AIR)
        # sechoirs a poisson et barques
        for i in range(4):
            sx, sz = x + 6 + i * 3, z + 4
            y = max(self.sol(sx, sz), SEA) + 1
            m.boite(sx, y, sz, sx, y + 2, sz, 'minecraft:spruce_fence')
            m.pose(sx, y + 3, sz, 'minecraft:spruce_slab[type=bottom,waterlogged=false]')
            m.pose(sx + 1, y + 2, sz, 'minecraft:dried_kelp_block')
        for i in range(3):
            bx, bz = x + (5 if i % 2 else -6), z + 2 + i * 3
            for j in range(5):
                m.pose(bx, SEA, bz + j, 'minecraft:spruce_planks'); m.pose(bx + 1, SEA, bz + j, 'minecraft:spruce_planks')
                if j in (0, 4):
                    continue
                m.pose(bx - 1, SEA + 1, bz + j, 'minecraft:spruce_slab[type=bottom,waterlogged=false]')
                m.pose(bx + 2, SEA + 1, bz + j, 'minecraft:spruce_slab[type=bottom,waterlogged=false]')
        self.ajoute('Village de pecheurs', x, z - (n // 2) * 5, 20)

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
        # un nid de spinosaure sous le dome eventre, parmi les nids d'oiseaux : inattendu
        self.nid_simple(x + 4, self.sol(x + 4, z - 5) + 1, z - 5)
        self.ajoute('Nid (sous le dome de la voliere)', x + 4, z - 5, 0)
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
