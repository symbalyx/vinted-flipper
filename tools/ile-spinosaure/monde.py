"""Le volume de blocs en cours de construction, sa palette et ses entites de blocs, et
l'ecriture en schematics Sponge v2 (fichier complet et/ou tuiles a coller une par une)."""
import json
import os
import re

import numpy as np

import nbt


OPPOSES = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east'}


class Monde:
    def __init__(self, W, H, L, graine=1):
        self.W, self.H, self.L = W, H, L
        self.palette = {}
        self.blocs = np.zeros((H, L, W), dtype=np.uint16)
        self.entites = []                       # (x, y, z, compound)
        self.rng = np.random.default_rng(graine)
        self.AIR = self.P('minecraft:air')

    # ------------------------------------------------------------ blocs
    def P(self, etat):
        if not isinstance(etat, str):
            return etat
        i = self.palette.get(etat)
        if i is None:
            i = self.palette[etat] = len(self.palette)
        return i

    def dedans(self, x, y, z):
        return 0 <= x < self.W and 0 <= y < self.H and 0 <= z < self.L

    def pose(self, x, y, z, etat, seulement_air=False):
        if self.dedans(x, y, z):
            if seulement_air and self.blocs[y, z, x] != self.AIR:
                return
            self.blocs[y, z, x] = self.P(etat)

    def get(self, x, y, z):
        return self.blocs[y, z, x] if self.dedans(x, y, z) else self.AIR

    def boite(self, x0, y0, z0, x1, y1, z1, etat, seulement_air=False):
        x0, x1 = sorted((int(x0), int(x1))); y0, y1 = sorted((int(y0), int(y1))); z0, z1 = sorted((int(z0), int(z1)))
        x0, y0, z0 = max(x0, 0), max(y0, 0), max(z0, 0)
        x1, y1, z1 = min(x1, self.W - 1), min(y1, self.H - 1), min(z1, self.L - 1)
        if x0 > x1 or y0 > y1 or z0 > z1:
            return
        v = self.P(etat)
        zone = self.blocs[y0:y1 + 1, z0:z1 + 1, x0:x1 + 1]
        if seulement_air:
            zone[zone == self.AIR] = v
        else:
            zone[...] = v

    def ellipsoide(self, cx, cy, cz, rx, ry, rz, etat, seulement_air=True, bruit=0.0, rng=None, bas=None, seulement=None):
        """Ellipsoide plein (centre flottant). bruit : fraction de la coquille externe retiree au
        hasard pour un contour irregulier. bas : ne pas descendre sous ce y."""
        rng = rng or self.rng
        x0, x1 = int(np.floor(cx - rx)), int(np.ceil(cx + rx))
        y0, y1 = int(np.floor(cy - ry)), int(np.ceil(cy + ry))
        z0, z1 = int(np.floor(cz - rz)), int(np.ceil(cz + rz))
        if bas is not None:
            y0 = max(y0, bas)
        x0, y0, z0 = max(x0, 0), max(y0, 0), max(z0, 0)
        x1, y1, z1 = min(x1, self.W - 1), min(y1, self.H - 1), min(z1, self.L - 1)
        if x0 > x1 or y0 > y1 or z0 > z1:
            return
        yy, zz, xx = np.mgrid[y0:y1 + 1, z0:z1 + 1, x0:x1 + 1]
        d = ((xx + 0.5 - cx) / rx) ** 2 + ((yy + 0.5 - cy) / ry) ** 2 + ((zz + 0.5 - cz) / rz) ** 2
        m = d <= 1.0
        if bruit > 0:
            m &= ~((d > 0.55) & (rng.random(d.shape) < bruit * (d - 0.55) / 0.45))
        zone = self.blocs[y0:y1 + 1, z0:z1 + 1, x0:x1 + 1]
        if seulement is not None:
            m &= np.isin(zone, list(seulement))
        elif seulement_air:
            m &= zone == self.AIR
        zone[m] = self.P(etat)

    @staticmethod
    def cellules(a, b):
        """Cellules d'un segment 3D, reliees par leurs faces (pas seulement par les coins) :
        un tronc ou une branche en biais reste d'un seul tenant, sans marches en diagonale."""
        a = np.asarray(a, float); b = np.asarray(b, float)
        n = int(np.ceil(np.abs(b - a).max() * 3)) + 1
        out = []
        for t in np.linspace(0, 1, n):
            c = tuple(int(v) for v in np.floor(a + (b - a) * t))
            if out and c == out[-1]:
                continue
            if out:
                p = list(out[-1])
                # completer axe par axe (x, puis z, puis y) : on s'appuie d'abord a plat, puis on monte
                for ax in (0, 2, 1):
                    while p[ax] != c[ax] and sum(p[k] != c[k] for k in range(3)) > 1:
                        p[ax] += 1 if c[ax] > p[ax] else -1
                        out.append(tuple(p))
            out.append(c)
        return out

    def ligne(self, a, b, etat_fn, epaisseur=0.0, seulement_air=False):
        """Segment 3D de a a b, d'un seul tenant. etat_fn(axe) -> etat (axe selon la direction
        dominante). epaisseur : rayon ajoute autour de l'axe."""
        a = np.asarray(a, float); b = np.asarray(b, float)
        d = b - a
        axe = 'xyz'[int(np.argmax(np.abs(d)))]
        etat = etat_fn(axe)
        r = int(np.ceil(epaisseur))
        for (x, y, z) in self.cellules(a, b):
            if r == 0:
                self.pose(x, y, z, etat, seulement_air)
                continue
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    for dz in range(-r, r + 1):
                        if dx * dx + dy * dy + dz * dz <= epaisseur * epaisseur + 0.25:
                            self.pose(x + dx, y + dy, z + dz, etat, seulement_air)

    # Blocs qui ne sont pas des faces pleines (on ne s'y raccorde pas)
    _NON_PLEIN = re.compile(r'air|water|lava|_pane|iron_bars|fence|_wall$|torch|lantern|sign|vine|lichen|fern|'
                            r'grass$|flower|door|trapdoor|slab|stairs|carpet|chain|ladder|rail|cobweb|_bed|chest|'
                            r'lever|pot|candle|redstone_wire|dripleaf|sapling|mushroom$|cocoa|rod|button|plate|kelp|'
                            r'seagrass|lily|banner|head|skull|scaffolding|cauldron|anvil|hopper|lectern|brewing|bell|'
                            r'cave_vines|sugar_cane|campfire|pickle|coral|snow$|light$|bamboo$|propagule|egg|grindstone|'
                            r'stonecutter|enchanting|end_rod|leaves|glass$')

    def connecter(self, x0=0, y0=0, z0=0, x1=None, y1=None, z1=None):
        """Calcule les etats de connexion (vitres, barreaux, barrieres, murets, fil de redstone)
        comme le ferait le jeu : WorldEdit colle sans mettre a jour les formes."""
        x1 = self.W - 1 if x1 is None else x1
        y1 = self.H - 1 if y1 is None else y1
        z1 = self.L - 1 if z1 is None else z1
        famille = {}
        _plein = {}

        def plein_(i):
            if i not in _plein:
                _plein[i] = not self._NON_PLEIN.search(self.nom(i).split('[')[0].replace('minecraft:', ''))
            return _plein[i]

        for nom, i in list(self.palette.items()):
            base = nom.split('[')[0].replace('minecraft:', '')
            if base.endswith('_pane') or base == 'iron_bars' or base == 'glass_pane':
                famille[i] = 'vitre'
            elif base.endswith('_fence') and 'gate' not in base:
                famille[i] = 'nether' if 'nether' in base else 'barriere'
            elif base.endswith('_wall') and 'sign' not in base and 'banner' not in base and 'torch' not in base:
                famille[i] = 'muret'
            elif base == 'redstone_wire':
                famille[i] = 'fil'
        if not famille:
            return
        zone = self.blocs[y0:y1 + 1, z0:z1 + 1, x0:x1 + 1]
        ids = np.array(list(famille))
        ys, zs, xs = np.nonzero(np.isin(zone, ids))
        verre = {i for n, i in self.palette.items() if n.split('[')[0].endswith('glass')}
        cache = {}
        for y, z, x in zip(ys + y0, zs + z0, xs + x0):
            i = int(self.blocs[y, z, x])
            fam = famille[i]
            base = self.nom(i).split('[')[0]
            etats = {}
            for face, (dx, dz) in (('north', (0, -1)), ('south', (0, 1)), ('west', (-1, 0)), ('east', (1, 0))):
                v = int(self.get(x + dx, y, z + dz))
                fv = famille.get(v)
                vn = self.nom(v)
                if fam == 'vitre':
                    ok = fv == 'vitre' or plein_(v) or v in verre or fv == 'muret'
                elif fam in ('barriere', 'nether'):
                    ok = fv == fam or plein_(v) or 'fence_gate' in vn
                elif fam == 'muret':
                    ok = fv in ('muret', 'vitre') or plein_(v) or 'fence_gate' in vn
                else:
                    ok = fv == 'fil'
                etats[face] = ok
            if fam == 'vitre':
                props = 'east=%s,north=%s,south=%s,waterlogged=false,west=%s' % tuple(
                    str(etats[f]).lower() for f in ('east', 'north', 'south', 'west'))
            elif fam in ('barriere', 'nether'):
                props = 'east=%s,north=%s,south=%s,waterlogged=false,west=%s' % tuple(
                    str(etats[f]).lower() for f in ('east', 'north', 'south', 'west'))
            elif fam == 'muret':
                haut = plein_(int(self.get(x, y + 1, z)))
                v = 'tall' if haut else 'low'
                droit = (etats['north'] and etats['south'] and not etats['east'] and not etats['west']) or \
                        (etats['east'] and etats['west'] and not etats['north'] and not etats['south'])
                props = 'east=%s,north=%s,south=%s,up=%s,waterlogged=false,west=%s' % (
                    v if etats['east'] else 'none', v if etats['north'] else 'none', v if etats['south'] else 'none',
                    str(not droit).lower(), v if etats['west'] else 'none')
            else:
                n = sum(etats.values())
                cote = lambda f: 'side' if etats[f] or (n == 1 and etats[OPPOSES[f]]) else 'none'
                props = 'east=%s,north=%s,power=0,south=%s,west=%s' % (cote('east'), cote('north'), cote('south'), cote('west'))
            etat = '%s[%s]' % (base, props)
            j = cache.get(etat)
            if j is None:
                j = cache[etat] = self.P(etat)
                famille[j] = fam
            self.blocs[y, z, x] = j

    def nettoyer_suspendus(self):
        """Retire ce qui pendrait dans le vide et tomberait au premier bloc voisin modifie :
        lianes sans appui (on ne garde que les faces reellement accrochees, a un bloc plein ou a
        la liane du dessus), propagules qui ne pendent pas sous des feuilles de paletuvier.
        Renvoie (lianes corrigees, lianes retirees, propagules retirees)."""
        faces = {'north': (0, -1), 'south': (0, 1), 'west': (-1, 0), 'east': (1, 0)}
        ids_v = {i: n for n, i in self.palette.items() if n.startswith('minecraft:vine[')}
        pas_appui = re.compile(r'air|water|vine|_pane|bars|fence|torch|lantern|sign|carpet|fern|grass$|flower|door|slab|'
                               r'stairs|cocoa|lichen|chain|ladder|rail|cobweb|_bed|pot|wire|button|lever|skull|rod|campfire|'
                               r'trapdoor|propagule|bamboo|kelp|seagrass|lily|sugar|azalea$|mushroom|orchid|light$')
        cache = {}

        def appui(i):
            if i not in cache:
                cache[i] = not pas_appui.search(self.nom(i).split('[')[0].replace('minecraft:', ''))
            return cache[i]
        if ids_v:
            ys, zs, xs = np.nonzero(np.isin(self.blocs, list(ids_v)))
            ordre = np.argsort(-ys, kind='stable')                 # de haut en bas
            corrige = retire = 0
            for y, z, x in zip(ys[ordre], zs[ordre], xs[ordre]):
                etat = self.nom(self.blocs[y, z, x])
                garde = []
                au = self.nom(self.get(x, y + 1, z)) if y + 1 < self.H else ''
                for f, (dx, dz) in faces.items():
                    if '%s=true' % f not in etat:
                        continue
                    if appui(int(self.get(x + dx, y, z + dz))) or (au.startswith('minecraft:vine[') and '%s=true' % f in au):
                        garde.append(f)
                if not garde:
                    self.blocs[y, z, x] = self.AIR
                    retire += 1
                    continue
                neuf = 'minecraft:vine[east=%s,north=%s,south=%s,up=false,west=%s]' % tuple(
                    str(f in garde).lower() for f in ('east', 'north', 'south', 'west'))
                if neuf != etat:
                    self.blocs[y, z, x] = self.P(neuf)
                    corrige += 1
        else:
            corrige = retire = 0
        prop = [i for n, i in self.palette.items() if 'propagule' in n]
        feuilles_m = [i for n, i in self.palette.items() if 'mangrove_leaves' in n]
        n_prop = 0
        if prop:
            ys, zs, xs = np.nonzero(np.isin(self.blocs, prop))
            for y, z, x in zip(ys, zs, xs):
                if int(self.get(x, y + 1, z)) not in feuilles_m:
                    self.blocs[y, z, x] = self.AIR
                    n_prop += 1
        return corrige, retire, n_prop

    def murs(self, x0, y0, z0, x1, y1, z1, etat):
        self.boite(x0, y0, z0, x1, y1, z0, etat); self.boite(x0, y0, z1, x1, y1, z1, etat)
        self.boite(x0, y0, z0, x0, y1, z1, etat); self.boite(x1, y0, z0, x1, y1, z1, etat)

    def nom(self, i):
        if not hasattr(self, '_inverse') or len(self._inverse) != len(self.palette):
            self._inverse = {v: k for k, v in self.palette.items()}
        return self._inverse[int(i)]

    # ------------------------------------------------------------ entites de blocs
    def panneau(self, x, y, z, facing, lignes, mural=True, bois='oak'):
        lignes = (list(lignes) + ['', '', '', ''])[:4]
        if mural:
            self.pose(x, y, z, 'minecraft:%s_wall_sign[facing=%s,waterlogged=false]' % (bois, facing))
        else:
            rot = {'south': 0, 'west': 4, 'north': 8, 'east': 12}[facing]
            self.pose(x, y, z, 'minecraft:%s_sign[rotation=%d,waterlogged=false]' % (bois, rot))

        def face(ls):
            return nbt.Compound({'messages': nbt.List('string', [nbt.String(json.dumps({'text': l}, ensure_ascii=False))
                                                                 for l in ls]),
                                 'color': nbt.String('black'), 'has_glowing_text': nbt.Byte(0)})
        self.entites.append((x, y, z, {'Id': nbt.String('minecraft:sign'), 'front_text': face(lignes),
                                       'back_text': face(['', '', '', '']), 'is_waxed': nbt.Byte(1)}))

    def coffre(self, x, y, z, facing, objets, bloc='chest'):
        if bloc == 'chest':
            self.pose(x, y, z, 'minecraft:chest[facing=%s,type=single,waterlogged=false]' % facing)
        else:
            self.pose(x, y, z, 'minecraft:barrel[facing=%s,open=false]' % facing)
        items = []
        for i, obj in enumerate(objets):
            o, n = obj[0], obj[1]
            c = {'Slot': nbt.Byte(i), 'id': nbt.String(o), 'Count': nbt.Byte(n)}
            if o.startswith('journal:'):
                import recits
                c['id'] = nbt.String('minecraft:written_book')
                c['tag'] = recits.livre(o.split(':', 1)[1])
            elif len(obj) > 2:
                c['tag'] = nbt.Compound({k: nbt.String(v) for k, v in obj[2].items()})
            items.append(nbt.Compound(c))
        self.entites.append((x, y, z, {'Id': nbt.String('minecraft:' + bloc), 'Items': nbt.List('compound', items)}))

    # ------------------------------------------------------------ ecriture
    @staticmethod
    def varints(v):
        v = v.astype(np.int64)
        un = v < 128
        lg = np.where(un, 1, 2)
        debut = np.concatenate(([0], np.cumsum(lg)[:-1]))
        out = np.zeros(int(lg.sum()), dtype=np.uint8)
        out[debut[un]] = v[un]
        deux = ~un
        out[debut[deux]] = (v[deux] & 0x7F) | 0x80
        out[debut[deux] + 1] = v[deux] >> 7
        return out.tobytes()

    def ecrire(self, chemin, x0=0, z0=0, x1=None, z1=None, biomes=None, bio_palette=None, nom='Site B'):
        x1 = self.W if x1 is None else x1
        z1 = self.L if z1 is None else z1
        sous = self.blocs[:, z0:z1, x0:x1]
        # palette locale compacte
        utilises = np.unique(sous)
        remap = np.zeros(len(self.palette), dtype=np.int64)
        remap[utilises] = np.arange(len(utilises))
        pal = {self.nom(i): int(j) for j, i in enumerate(utilises)}
        donnees = self.varints(remap[sous].reshape(-1))
        ents = []
        for (x, y, z, d) in self.entites:
            if x0 <= x < x1 and z0 <= z < z1:
                c = dict(d)
                c['Pos'] = nbt.IntArray([x - x0, y, z - z0])
                ents.append(nbt.Compound(c))
        racine = {
            'Version': nbt.Int(2), 'DataVersion': nbt.Int(3465),
            'Width': nbt.Short(x1 - x0), 'Height': nbt.Short(self.H), 'Length': nbt.Short(z1 - z0),
            'Offset': nbt.IntArray([0, 0, 0]),
            'Metadata': nbt.Compound({'WEOffsetX': nbt.Int(0), 'WEOffsetY': nbt.Int(0), 'WEOffsetZ': nbt.Int(0),
                                      'Name': nbt.String(nom), 'Author': nbt.String('RIVIERE')}),
            'PaletteMax': nbt.Int(len(pal)),
            'Palette': nbt.Compound({k: nbt.Int(v) for k, v in pal.items()}),
            'BlockData': nbt.ByteArray(donnees),
            'BlockEntities': nbt.List('compound', ents),
        }
        if biomes is not None:
            racine['BiomePalette'] = nbt.Compound({k: nbt.Int(v) for k, v in bio_palette.items()})
            racine['BiomeData'] = nbt.ByteArray(self.varints(biomes[z0:z1, x0:x1].reshape(-1)))
        nbt.ecrire(chemin, 'Schematic', nbt.Compound(racine))
        return os.path.getsize(chemin)


class Decale:
    """Vue d'un Monde dans un repere local (origine ox, oy, oz) : les batiments s'ecrivent en
    coordonnees locales, y relatif au rez-de-chaussee."""

    def __init__(self, m, ox, oy, oz):
        self.m, self.ox, self.oy, self.oz = m, ox, oy, oz
        self.AIR = m.AIR
        self.rng = m.rng

    def P(self, e):
        return self.m.P(e)

    def nom(self, i):
        return self.m.nom(i)

    def dedans(self, x, y, z):
        return self.m.dedans(x + self.ox, y + self.oy, z + self.oz)

    def pose(self, x, y, z, e, seulement_air=False):
        self.m.pose(x + self.ox, y + self.oy, z + self.oz, e, seulement_air)

    def get(self, x, y, z):
        return self.m.get(x + self.ox, y + self.oy, z + self.oz)

    def boite(self, x0, y0, z0, x1, y1, z1, e, seulement_air=False):
        self.m.boite(x0 + self.ox, y0 + self.oy, z0 + self.oz, x1 + self.ox, y1 + self.oy, z1 + self.oz, e, seulement_air)

    def murs(self, x0, y0, z0, x1, y1, z1, e):
        self.m.murs(x0 + self.ox, y0 + self.oy, z0 + self.oz, x1 + self.ox, y1 + self.oy, z1 + self.oz, e)

    def ellipsoide(self, cx, cy, cz, rx, ry, rz, e, **kw):
        self.m.ellipsoide(cx + self.ox, cy + self.oy, cz + self.oz, rx, ry, rz, e, **kw)

    def ligne(self, a, b, fn, epaisseur=0.0, seulement_air=False):
        d = np.array([self.ox, self.oy, self.oz], float)
        self.m.ligne(np.asarray(a, float) + d, np.asarray(b, float) + d, fn, epaisseur, seulement_air)

    def panneau(self, x, y, z, facing, lignes, mural=True, bois='oak'):
        self.m.panneau(x + self.ox, y + self.oy, z + self.oz, facing, lignes, mural, bois)

    def coffre(self, x, y, z, facing, objets, bloc='chest'):
        self.m.coffre(x + self.ox, y + self.oy, z + self.oz, facing, objets, bloc)

    def vue(self, x0, y0, z0, x1, y1, z1):
        """Tranche numpy [y, z, x] (bornes incluses, rognees au monde)."""
        m = self.m
        X0, Y0, Z0 = max(x0 + self.ox, 0), max(y0 + self.oy, 0), max(z0 + self.oz, 0)
        X1, Y1, Z1 = min(x1 + self.ox, m.W - 1), min(y1 + self.oy, m.H - 1), min(z1 + self.oz, m.L - 1)
        return m.blocs[Y0:Y1 + 1, Z0:Z1 + 1, X0:X1 + 1]
