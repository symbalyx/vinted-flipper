"""Kit d'amenagement et de facade : blocs a etats corrects (portes en deux moities, lits en
deux parties, escaliers orientes...) et meubles composes (bureau a double ecran, paillasse,
hotte, baie de serveurs, cuve de confinement...).

Conventions : `regard` = direction vers laquelle regarde l'occupant ou la face utile.
Escaliers : facing = cote du dossier (partie haute)."""
import math

import numpy as np

DIRS = {'north': (0, -1), 'south': (0, 1), 'west': (-1, 0), 'east': (1, 0)}
OPP = {'north': 'south', 'south': 'north', 'west': 'east', 'east': 'west'}
GAUCHE = {'north': 'west', 'west': 'south', 'south': 'east', 'east': 'north'}   # a gauche quand on regarde vers d
DROITE = {v: k for k, v in GAUCHE.items()}


def esc(bloc, facing, half='bottom', shape='straight'):
    return 'minecraft:%s_stairs[facing=%s,half=%s,shape=%s,waterlogged=false]' % (bloc, facing, half, shape)


def dalle(bloc, t='bottom'):
    return 'minecraft:%s_slab[type=%s,waterlogged=false]' % (bloc, t)


def trappe(bloc, facing, half='top', ouverte=False):
    return 'minecraft:%s_trapdoor[facing=%s,half=%s,open=%s,powered=false,waterlogged=false]' % (
        bloc, facing, half, str(ouverte).lower())


class Kit:
    def __init__(self, m, rng):
        self.m, self.rng = m, rng

    def pose(self, x, y, z, e, seulement_air=False):
        self.m.pose(x, y, z, e, seulement_air)

    # ------------------------------------------------------------------ blocs a etats
    def porte(self, x, y, z, facing, bois='iron', hinge='left', ouverte=False, boutons=True):
        for half, dy in (('lower', 0), ('upper', 1)):
            self.pose(x, y + dy, z, 'minecraft:%s_door[facing=%s,half=%s,hinge=%s,open=%s,powered=false]' % (
                bois, facing, half, hinge, str(ouverte).lower()))
        if bois == 'iron' and boutons:
            # une porte en fer ne s'ouvre pas a la main : un bouton de chaque cote, a cote du chambranle
            for lat in ((GAUCHE[facing], DROITE[facing]) if hinge == 'left' else (DROITE[facing], GAUCHE[facing])):
                lx, lz = DIRS[lat]
                mur = self.m.get(x + lx, y + 1, z + lz)
                if mur == self.m.AIR or 'door' in self.m.nom(mur):
                    continue
                for cote in (facing, OPP[facing]):
                    dx, dz = DIRS[cote]
                    self.pose(x + lx + dx, y + 1, z + lz + dz,
                              'minecraft:stone_button[face=wall,facing=%s,powered=false]' % cote, seulement_air=True)
                break

    def double_porte(self, x, y, z, facing, bois='iron', ouverte=False):
        """Deux vantaux : le premier en (x, z), le second a sa droite quand on regarde `facing`."""
        dx, dz = DIRS[DROITE[facing]]
        self.porte(x, y, z, facing, bois, 'left', ouverte)
        self.porte(x + dx, y, z + dz, facing, bois, 'right', ouverte)

    def lit(self, x, y, z, facing, couleur='white'):
        """Pied en (x, z), tete du cote `facing`."""
        dx, dz = DIRS[facing]
        self.pose(x, y, z, 'minecraft:%s_bed[facing=%s,occupied=false,part=foot]' % (couleur, facing))
        self.pose(x + dx, y, z + dz, 'minecraft:%s_bed[facing=%s,occupied=false,part=head]' % (couleur, facing))

    def lanterne(self, x, y, z, suspendue=True, ame=False):
        self.pose(x, y, z, 'minecraft:%slantern[hanging=%s,waterlogged=false]' % ('soul_' if ame else '', str(suspendue).lower()))

    def torche_murale(self, x, y, z, facing, rouge=False):
        """facing : direction vers laquelle pointe la torche (le mur est du cote oppose)."""
        if rouge:
            self.pose(x, y, z, 'minecraft:redstone_wall_torch[facing=%s,lit=true]' % facing)
        else:
            self.pose(x, y, z, 'minecraft:wall_torch[facing=%s]' % facing)

    def pot(self, x, y, z, plante='fern'):
        self.pose(x, y, z, 'minecraft:potted_%s' % plante)

    def fil(self, x, y, z):
        self.pose(x, y, z, 'minecraft:redstone_wire[east=none,north=none,power=0,south=none,west=none]')

    # ------------------------------------------------------------------ meubles
    def chaise(self, x, y, z, regard, bloc='dark_oak'):
        self.pose(x, y, z, esc(bloc, OPP[regard]))

    def bureau(self, x, y, z, regard, n=2, bois='spruce', ecrans=True, chaise=True):
        """Plateau de n blocs devant l'occupant (qui regarde `regard`), ecrans au fond,
        clavier (plaque), chaise derriere."""
        dx, dz = DIRS[regard]
        lx, lz = DIRS[DROITE[regard]]
        for k in range(n):
            px, pz = x + dx + lx * k, z + dz + lz * k
            self.pose(px, y, pz, dalle(bois, 'top'))
        if ecrans:
            # ecrans poses sur le plateau, en rang (les vitres noires se raccordent : ecrans plats)
            for k in range(min(n, 2)):
                px, pz = x + dx + lx * k, z + dz + lz * k
                self.pose(px, y + 1, pz, 'minecraft:black_stained_glass_pane')
        if chaise:
            self.chaise(x, y, z, regard)

    def table(self, x, y, z, bois='spruce', nappe=None):
        self.pose(x, y, z, 'minecraft:%s_fence' % bois)
        self.pose(x, y + 1, z, 'minecraft:%s_carpet' % nappe if nappe else 'minecraft:%s_pressure_plate' % bois)

    def longue_table(self, x0, z0, x1, z1, y, bloc='smooth_quartz', chaises='dark_oak'):
        """Table (plateau en dalles hautes) avec chaises sur les deux longs cotes."""
        axe_x = (x1 - x0) >= (z1 - z0)
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                self.pose(x, y, z, dalle(bloc, 'top'))
        if axe_x:
            for x in range(x0, x1 + 1):
                if self.rng.random() < 0.85:
                    self.chaise(x, y, z0 - 1, 'south', chaises)
                if self.rng.random() < 0.85:
                    self.chaise(x, y, z1 + 1, 'north', chaises)
        else:
            for z in range(z0, z1 + 1):
                if self.rng.random() < 0.85:
                    self.chaise(x0 - 1, y, z, 'east', chaises)
                if self.rng.random() < 0.85:
                    self.chaise(x1 + 1, y, z, 'west', chaises)

    def paillasse(self, x0, z0, x1, z1, y, regard):
        """Paillasse de labo : placards en bas, plan de travail, instruments dessus."""
        rng = self.rng
        items = ['minecraft:brewing_stand[has_bottle_0=true,has_bottle_1=false,has_bottle_2=true]',
                 'minecraft:brewing_stand[has_bottle_0=true,has_bottle_1=true,has_bottle_2=true]',
                 'minecraft:cauldron', 'minecraft:flower_pot', 'minecraft:potted_red_mushroom',
                 'minecraft:lectern[facing=%s,has_book=false,powered=false]' % OPP[regard],
                 'minecraft:light_gray_stained_glass_pane', 'minecraft:white_candle[candles=3,lit=false,waterlogged=false]',
                 'minecraft:end_rod[facing=up]', None, None, None]
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                self.pose(x, y, z, 'minecraft:white_concrete')
                self.pose(x, y + 1, z, dalle('smooth_quartz', 'bottom'))
                it = items[rng.integers(0, len(items))]
                if it:
                    self.pose(x, y + 1, z, it)

    def hotte(self, x, y, z, regard):
        """Sorbonne : caisson inox, vitre relevee, extraction au plafond."""
        self.pose(x, y, z, 'minecraft:iron_block')
        self.pose(x, y + 1, z, 'minecraft:brewing_stand[has_bottle_0=true,has_bottle_1=false,has_bottle_2=false]')
        dx, dz = DIRS[regard]
        self.pose(x + dx, y + 2, z + dz, trappe('iron', OPP[regard], 'top', False))
        self.pose(x, y + 2, z, 'minecraft:iron_block')
        self.pose(x, y + 3, z, 'minecraft:hopper[enabled=true,facing=down]')

    def baie_serveur(self, x, y, z, regard, n, lat):
        """Rangee de n baies de 3 de haut. lat : direction de la rangee."""
        lx, lz = DIRS[lat]
        rng = self.rng
        for k in range(n):
            px, pz = x + lx * k, z + lz * k
            self.pose(px, y, pz, 'minecraft:dispenser[facing=%s,triggered=false]' % regard)
            self.pose(px, y + 1, pz, 'minecraft:observer[facing=%s,powered=false]' % OPP[regard])
            self.pose(px, y + 2, pz, 'minecraft:redstone_lamp[lit=%s]' % ('true' if rng.random() < 0.15 else 'false'))

    def casiers(self, x, y, z, regard, n, lat):
        lx, lz = DIRS[lat]
        for k in range(n):
            for dy in (0, 1):
                self.pose(x + lx * k, y + dy, z + lz * k, 'minecraft:barrel[facing=%s,open=%s]' % (
                    regard, 'true' if self.rng.random() < 0.2 else 'false'))

    def etagere(self, x, y, z, n, lat, h=3, bloc='bookshelf'):
        lx, lz = DIRS[lat]
        for k in range(n):
            for dy in range(h):
                self.pose(x + lx * k, y + dy, z + lz * k, 'minecraft:' + bloc)

    def plante(self, x, y, z, grande=False):
        rng = self.rng
        if grande:
            self.pose(x, y, z, 'minecraft:moss_block')
            self.pose(x, y + 1, z, 'minecraft:%s' % ('flowering_azalea' if rng.random() < 0.4 else 'azalea'))
        else:
            self.pot(x, y, z, ['fern', 'bamboo', 'dead_bush', 'jungle_sapling', 'azalea_bush'][rng.integers(0, 5)])

    def cuve(self, x, y, z, h=4, brisee=False, specimen=None):
        """Cuve de confinement 3x3 : socle et chapeau en fer, verre, eau, specimen au centre."""
        m = self.m
        m.boite(x - 1, y, z - 1, x + 1, y, z + 1, 'minecraft:iron_block')
        m.boite(x - 1, y + h + 1, z - 1, x + 1, y + h + 1, z + 1, 'minecraft:iron_block')
        self.pose(x, y + h + 2, z, 'minecraft:hopper[enabled=true,facing=down]')
        for dy in range(1, h + 1):
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    if dx == 0 and dz == 0:
                        continue
                    coin = dx != 0 and dz != 0
                    if brisee and not coin and (dy > 1 or self.rng.random() < 0.5):
                        continue
                    self.pose(x + dx, y + dy, z + dz, 'minecraft:iron_bars' if coin else 'minecraft:glass')
            if not brisee:
                self.pose(x, y + dy, z, 'minecraft:water[level=0]')
        if specimen and not brisee:
            self.pose(x, y + 1, z, specimen)
            if 'kelp' in specimen:
                for dy in range(2, h):
                    self.pose(x, y + dy, z, 'minecraft:kelp_plant')
                self.pose(x, y + h, z, 'minecraft:kelp[age=25]')

    def sang(self, pts, densite=0.7):
        """Trainee de gouttes (fil de redstone isole) le long d'une polyligne au sol."""
        rng = self.rng
        for (xa, ya, za), (xb, yb, zb) in zip(pts, pts[1:]):
            n = int(max(abs(xb - xa), abs(zb - za))) + 1
            for k in range(n):
                t = k / max(n - 1, 1)
                x = int(round(xa + (xb - xa) * t + rng.uniform(-0.6, 0.6)))
                z = int(round(za + (zb - za) * t + rng.uniform(-0.6, 0.6)))
                y = int(round(ya + (yb - ya) * t))
                if rng.random() < densite and self.m.get(x, y, z) == self.m.AIR and self.m.get(x, y - 1, z) != self.m.AIR:
                    self.fil(x, y, z)

    def toiles(self, x0, y0, z0, x1, y1, z1, n):
        """Toiles d'araignee dans les angles hauts d'une piece."""
        rng = self.rng
        for _ in range(n):
            x = int(rng.choice([x0, x1])) if rng.random() < 0.5 else int(rng.integers(x0, x1 + 1))
            z = int(rng.choice([z0, z1])) if x not in (x0, x1) else int(rng.integers(z0, z1 + 1))
            self.pose(x, y1, z, 'minecraft:cobweb', seulement_air=True)

    def lampes_plafond(self, x0, z0, x1, z1, y, pas=4, marche=0.12):
        """Plafonniers : quelques-uns fonctionnent encore (lanterne de mer), le reste est mort."""
        for x in range(x0 + pas // 2, x1, pas):
            for z in range(z0 + pas // 2, z1, pas):
                self.pose(x, y, z, 'minecraft:sea_lantern' if self.rng.random() < marche else 'minecraft:redstone_lamp[lit=false]')

    def veilleuses(self, x0, z0, x1, z1, y, pas=3, niveau=3):
        """Lumiere invisible tres faible : l'interieur reste sombre mais aucun monstre vanilla
        n'y apparait (depuis 1.18, ils n'apparaissent qu'a lumiere de bloc 0)."""
        m = self.m
        for x in range(x0, x1 + 1, pas):
            for z in range(z0, z1 + 1, pas):
                if m.get(x, y, z) == m.AIR:
                    m.pose(x, y, z, 'minecraft:light[level=%d,waterlogged=false]' % niveau)

    # ------------------------------------------------------------------ facade
    def usure(self, x0, y0, z0, x1, y1, z1, remplacements, frac):
        """Remplace au hasard une fraction des blocs d'un materiau par ses variantes usees.
        remplacements : {etat_source: [etats_usures]}."""
        m = self.m
        zone = m.vue(x0, y0, z0, x1, y1, z1)
        for src, cibles in remplacements.items():
            i = m.P(src)
            masque = (zone == i) & (self.rng.random(zone.shape) < frac)
            n = int(masque.sum())
            if n:
                ids = np.array([m.P(c) for c in cibles], dtype=zone.dtype)
                zone[masque] = ids[self.rng.integers(0, len(ids), n)]

    def lierre(self, x0, x1, z0, z1, y_haut, y_bas, n, face):
        """Vignes qui descendent le long d'une facade exterieure. face : cote ou se trouve le mur
        par rapport aux vignes (ex. 'north' : mur au nord des vignes)."""
        m, rng = self.m, self.rng
        etat = 'minecraft:vine[east=%s,north=%s,south=%s,up=false,west=%s]' % tuple(
            'true' if f == face else 'false' for f in ('east', 'north', 'south', 'west'))
        for _ in range(n):
            x = int(rng.integers(x0, x1 + 1)); z = int(rng.integers(z0, z1 + 1))
            long = int(rng.integers(3, y_haut - y_bas + 1))
            for y in range(y_haut, y_haut - long, -1):
                if m.get(x, y, z) != m.AIR:
                    break
                m.pose(x, y, z, etat)
