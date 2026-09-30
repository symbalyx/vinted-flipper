"""Export de l'ile en vrai monde Minecraft Java 1.20.1 (dossier de sauvegarde), a copier dans
.minecraft/saves (ou comme dossier `world` d'un serveur Forge) : plus besoin de WorldEdit.

- L'ile est centree sur l'origine : x et z de -320 a +319. Elle est posee comme le schematic
  colle a y = 15 (la mer a y = 63).
- Sous l'ile, de y = -64 a y = 14, un sous-sol profond (tableau `profond`) : ardoise des abimes,
  cavernes, lave, minerais d'ardoise.
- Autour, le monde est un superflat d'ocean au meme niveau (socle, ardoise, pierre, sable,
  eau jusqu'a y = 63) : l'ile ne flotte pas dans le vide et la mer continue a l'horizon.

Format : regions Anvil (.mca), chunks 1.20.1 (DataVersion 3465) avec sections a palette et
biomes 4 x 4 x 4 ; « isLightOn » a 0 pour que le jeu recalcule la lumiere au chargement, et
pas de heightmaps (le jeu les recalcule aussi).
"""
import gzip
import io
import math
import os
import struct
import time
import zlib

import numpy as np

import nbt

DATA_VERSION = 3465
Y_MIN = -64
N_SECTIONS = 24
DECALAGE_Y = 15                     # y du schematic 0 -> y 15 du monde
ORIGINE = -320                      # x (et z) du schematic 0 -> -320 dans le monde (ile de 640)


def analyser(etat):
    """'minecraft:oak_stairs[facing=north,half=top]' -> ('minecraft:oak_stairs', {'facing': 'north', ...})"""
    if '[' not in etat:
        return etat, {}
    nom, props = etat.split('[', 1)
    kv = {}
    for p in props.rstrip(']').split(','):
        if p:
            k, v = p.split('=', 1)
            kv[k] = v
    return nom, kv


def _paquet(valeurs, bits):
    """Entiers -> tableau de longs (sans chevauchement d'un long a l'autre, comme depuis 1.16)."""
    par_long = 64 // bits
    n = math.ceil(len(valeurs) / par_long)
    v = np.zeros(n * par_long, np.uint64)
    v[:len(valeurs)] = valeurs
    v = v.reshape(n, par_long)
    decal = (np.arange(par_long, dtype=np.uint64) * np.uint64(bits))
    longs = np.bitwise_or.reduce(v << decal, axis=1)
    return longs.view(np.int64)


class Exporteur:
    def __init__(self, m, profond, biomes2d, bio_palette, sea_schem, bio_profond=None):
        self.m = m
        self.bio_profond = bio_profond                  # (indice sous y = 0, indice du sculk, masque 2D du sculk)
        self.profond = profond                          # [y + 64, z, x] pour y de -64 a 14
        self.biomes2d = biomes2d                        # [z, x] -> indice dans bio_palette
        self.bio_noms = {v: k for k, v in bio_palette.items()}
        self.sea = sea_schem
        inv = {v: k for k, v in m.palette.items()}
        self.etats = {}
        for i, nom in inv.items():
            nom_, props = analyser(nom)
            c = {'Name': nbt.String(nom_)}
            if props:
                c['Properties'] = nbt.Compound({k: nbt.String(v) for k, v in props.items()})
            self.etats[i] = nbt.Compound(c)
        # entites de blocs par chunk
        self.be = {}
        for (x, y, z, d) in m.entites:
            X, Y, Z = x + ORIGINE, y + DECALAGE_Y, z + ORIGINE
            c = {k: v for k, v in d.items() if k not in ('Id', 'Pos')}
            c['id'] = d['Id']
            c['x'] = nbt.Int(X); c['y'] = nbt.Int(Y); c['z'] = nbt.Int(Z)
            c['keepPacked'] = nbt.Byte(0)
            self.be.setdefault((X >> 4, Z >> 4), []).append(nbt.Compound(c))

    def colonne(self, cx, cz):
        """Blocs [384, 16, 16] (y de -64 a 319) du chunk (cx, cz) en coordonnees du monde."""
        m = self.m
        x0, z0 = cx * 16 - ORIGINE, cz * 16 - ORIGINE
        c = np.full((384, 16, 16), m.AIR, np.uint16)
        n_prof = self.profond.shape[0]
        c[:n_prof] = self.profond[:, z0:z0 + 16, x0:x0 + 16]
        b = DECALAGE_Y - Y_MIN
        c[b:b + m.H] = m.blocs[:, z0:z0 + 16, x0:x0 + 16]
        return c

    def section(self, blocs, sy, bio):
        uniq, inv = np.unique(blocs.reshape(-1), return_inverse=True)
        bs = {'palette': nbt.List('compound', [self.etats[int(u)] for u in uniq])}
        if len(uniq) > 1:
            bits = max(4, math.ceil(math.log2(len(uniq))))
            bs['data'] = nbt.LongArray(_paquet(inv.astype(np.uint64), bits))
        bu, bi = np.unique(bio.reshape(-1), return_inverse=True)
        bm = {'palette': nbt.List('string', [nbt.String(self.bio_noms[int(u)]) for u in bu])}
        if len(bu) > 1:
            bits = max(1, math.ceil(math.log2(len(bu))))
            bm['data'] = nbt.LongArray(_paquet(bi.astype(np.uint64), bits))
        return nbt.Compound({'Y': nbt.Byte(sy), 'block_states': nbt.Compound(bs), 'biomes': nbt.Compound(bm)})

    def chunk(self, cx, cz):
        col = self.colonne(cx, cz)
        x0, z0 = cx * 16 - ORIGINE, cz * 16 - ORIGINE
        # biomes 4 x 4 : on echantillonne la carte 2D au centre de chaque cellule
        b2 = self.biomes2d[z0 + 2:z0 + 16:4, x0 + 2:x0 + 16:4]                   # [4, 4]
        bio = np.broadcast_to(b2[None, :, :], (4, 4, 4))
        bio_bas = bio
        if self.bio_profond is not None:
            i_bas, i_sculk, sculk = self.bio_profond[:3]
            s2 = sculk[z0 + 2:z0 + 16:4, x0 + 2:x0 + 16:4]
            b2b = np.where(s2, i_sculk, i_bas)
            if len(self.bio_profond) > 3:                     # la fosse du lagon reste de l'ocean
                i_oc, oc = self.bio_profond[3:5]
                b2b = np.where(oc[z0 + 2:z0 + 16:4, x0 + 2:x0 + 16:4], i_oc, b2b)
            bio_bas = np.broadcast_to(b2b[None, :, :], (4, 4, 4))
        sections = []
        for i in range(N_SECTIONS):
            sy = Y_MIN // 16 + i
            sections.append(self.section(col[i * 16:(i + 1) * 16], sy, bio_bas if sy < 0 else bio))
        racine = {
            'DataVersion': nbt.Int(DATA_VERSION),
            'xPos': nbt.Int(cx), 'zPos': nbt.Int(cz), 'yPos': nbt.Int(Y_MIN // 16),
            'Status': nbt.String('minecraft:full'),
            'LastUpdate': nbt.Long(0), 'InhabitedTime': nbt.Long(0),
            'isLightOn': nbt.Byte(0),
            'sections': nbt.List('compound', sections),
            'block_entities': nbt.List('compound', self.be.get((cx, cz), [])),
            'structures': nbt.Compound({'References': nbt.Compound({}), 'starts': nbt.Compound({})}),
            'block_ticks': nbt.List('compound', []),
            'fluid_ticks': nbt.List('compound', []),
            'PostProcessing': nbt.List('list', [nbt.List('short', []) for _ in range(N_SECTIONS)]),
        }
        return zlib.compress(nbt.encoder('', nbt.Compound(racine)), 6)

    def _chunks_ile(self):
        cxs = range(ORIGINE >> 4, (ORIGINE + self.m.W) >> 4)
        czs = range(ORIGINE >> 4, (ORIGINE + self.m.L) >> 4)
        return [(cx, cz) for cz in czs for cx in cxs]

    @staticmethod
    def _ecrire_regions(dossier, donnees, journal, quoi):
        """donnees : {(cx, cz): octets zlib} -> fichiers r.X.Z.mca (entete de 8 Kio, secteurs de 4 Kio)."""
        os.makedirs(dossier, exist_ok=True)
        par_region = {}
        for (cx, cz) in donnees:
            par_region.setdefault((cx >> 5, cz >> 5), []).append((cx, cz))
        t = int(time.time())
        for (rx, rz), chunks in sorted(par_region.items()):
            entete = bytearray(8192)
            corps = io.BytesIO()
            secteur = 2
            for (cx, cz) in chunks:
                data = donnees[(cx, cz)]
                bloc = struct.pack('>ib', len(data) + 1, 2) + data
                n_sect = math.ceil(len(bloc) / 4096)
                bloc += b'\0' * (n_sect * 4096 - len(bloc))
                idx = (cx & 31) + (cz & 31) * 32
                entete[idx * 4:idx * 4 + 4] = struct.pack('>I', (secteur << 8) | n_sect)
                entete[4096 + idx * 4:4096 + idx * 4 + 4] = struct.pack('>I', t)
                corps.write(bloc)
                secteur += n_sect
            chemin = os.path.join(dossier, 'r.%d.%d.mca' % (rx, rz))
            with open(chemin, 'wb') as f:
                f.write(entete)
                f.write(corps.getvalue())
            journal('%s r.%d.%d : %d chunks, %.1f Mo' % (quoi, rx, rz, len(chunks), os.path.getsize(chemin) / 1e6))

    def regions(self, dossier, journal=print):
        donnees = {}
        for (cx, cz) in self._chunks_ile():
            donnees[(cx, cz)] = self.chunk(cx, cz)
        self._ecrire_regions(dossier, donnees, journal, 'region')
        return len(donnees)

    def entites(self, dossier, journal=print):
        """Entites (barques, wagonnets, noeuds de chaine...) : fichiers entities/r.X.Z.mca, un
        compound par chunk {DataVersion, Position [cx, cz], Entities}. Position et UUID ajoutes ici."""
        par_chunk = {}
        for k, (x, y, z, d) in enumerate(getattr(self.m, 'mobiles', [])):
            X, Y, Z = x + ORIGINE, y + DECALAGE_Y, z + ORIGINE
            c = dict(d)
            c['Pos'] = nbt.List('double', [nbt.Double(X), nbt.Double(Y), nbt.Double(Z)])
            c.setdefault('Motion', nbt.List('double', [nbt.Double(0), nbt.Double(0), nbt.Double(0)]))
            c.setdefault('Rotation', nbt.List('float', [nbt.Float(0), nbt.Float(0)]))
            c.setdefault('OnGround', nbt.Byte(0))
            c.setdefault('Air', nbt.Short(300))
            c.setdefault('FallDistance', nbt.Float(0))
            c.setdefault('Fire', nbt.Short(-1))
            c.setdefault('Invulnerable', nbt.Byte(0))
            c.setdefault('PortalCooldown', nbt.Int(0))
            if 'UUID' not in c:
                c['UUID'] = nbt.IntArray([0x51734200, 0x20260925, k >> 16, (k & 0xFFFF) * 7919 + 1])
            par_chunk.setdefault((int(math.floor(X)) >> 4, int(math.floor(Z)) >> 4), []).append(nbt.Compound(c))
        donnees = {}
        for (cx, cz), ents in par_chunk.items():
            racine = nbt.Compound({'DataVersion': nbt.Int(DATA_VERSION), 'Position': nbt.IntArray([cx, cz]),
                                   'Entities': nbt.List('compound', ents)})
            donnees[(cx, cz)] = zlib.compress(nbt.encoder('', racine), 6)
        if donnees:
            self._ecrire_regions(dossier, donnees, journal, 'entites')
        return sum(len(v) for v in par_chunk.values())


def couches_superflat(sea_monde, fond):
    """Ocean plat autour de l'ile : socle, ardoise, pierre, sable dont le dessus est a y = fond
    (le fond du bord de l'ile), eau jusqu'a y = sea_monde compris (comme l'eau de l'ile)."""
    fond = min(fond, sea_monde - 2)
    pierre = fond - 3 - 0                     # sable de fond-2 a fond
    return [('minecraft:bedrock', 1), ('minecraft:deepslate', 64), ('minecraft:stone', pierre - 0),
            ('minecraft:sand', 3), ('minecraft:water', sea_monde - fond)]


def level_dat(chemin, nom, spawn, sea_monde, fond, graine=20260925):
    couches = nbt.List('compound', [nbt.Compound({'block': nbt.String(b), 'height': nbt.Int(h)})
                                    for b, h in couches_superflat(sea_monde, fond)])
    overworld = nbt.Compound({
        'type': nbt.String('minecraft:overworld'),
        'generator': nbt.Compound({
            'type': nbt.String('minecraft:flat'),
            'settings': nbt.Compound({
                'biome': nbt.String('minecraft:warm_ocean'),
                'features': nbt.Byte(0), 'lakes': nbt.Byte(0),
                'layers': couches,
                'structure_overrides': nbt.List('string', []),
            }),
        }),
    })
    nether = nbt.Compound({
        'type': nbt.String('minecraft:the_nether'),
        'generator': nbt.Compound({'type': nbt.String('minecraft:noise'), 'settings': nbt.String('minecraft:nether'),
                                   'biome_source': nbt.Compound({'type': nbt.String('minecraft:multi_noise'),
                                                                 'preset': nbt.String('minecraft:nether')})}),
    })
    end = nbt.Compound({
        'type': nbt.String('minecraft:the_end'),
        'generator': nbt.Compound({'type': nbt.String('minecraft:noise'), 'settings': nbt.String('minecraft:end'),
                                   'biome_source': nbt.Compound({'type': nbt.String('minecraft:the_end')})}),
    })
    regles = {'doFireTick': 'false', 'mobGriefing': 'true', 'doDaylightCycle': 'true', 'doMobSpawning': 'true',
              'keepInventory': 'false', 'announceAdvancements': 'false', 'doInsomnia': 'false', 'spawnRadius': '0',
              'doPatrolSpawning': 'false', 'doTraderSpawning': 'false'}
    data = nbt.Compound({
        'DataVersion': nbt.Int(DATA_VERSION),
        'version': nbt.Int(19133),
        'Version': nbt.Compound({'Id': nbt.Int(DATA_VERSION), 'Name': nbt.String('1.20.1'), 'Series': nbt.String('main'),
                                 'Snapshot': nbt.Byte(0)}),
        'LevelName': nbt.String(nom),
        'GameType': nbt.Int(0),                 # survie : en creatif, il observe et n'attaque jamais
        'Difficulty': nbt.Byte(2), 'DifficultyLocked': nbt.Byte(0), 'hardcore': nbt.Byte(0),
        'allowCommands': nbt.Byte(1), 'initialized': nbt.Byte(1),
        'SpawnX': nbt.Int(spawn[0]), 'SpawnY': nbt.Int(spawn[1]), 'SpawnZ': nbt.Int(spawn[2]), 'SpawnAngle': nbt.Float(0.0),
        'Time': nbt.Long(0), 'DayTime': nbt.Long(1000), 'LastPlayed': nbt.Long(int(time.time() * 1000)),
        'raining': nbt.Byte(0), 'rainTime': nbt.Int(60000), 'thundering': nbt.Byte(0), 'thunderTime': nbt.Int(60000),
        'clearWeatherTime': nbt.Int(0),
        'WasModded': nbt.Byte(1),
        'ServerBrands': nbt.List('string', [nbt.String('forge')]),
        'DataPacks': nbt.Compound({'Enabled': nbt.List('string', [nbt.String('vanilla')]),
                                   'Disabled': nbt.List('string', [])}),
        'GameRules': nbt.Compound({k: nbt.String(v) for k, v in regles.items()}),
        'WorldGenSettings': nbt.Compound({
            'seed': nbt.Long(graine), 'generate_features': nbt.Byte(0), 'bonus_chest': nbt.Byte(0),
            'dimensions': nbt.Compound({'minecraft:overworld': overworld, 'minecraft:the_nether': nether,
                                        'minecraft:the_end': end}),
        }),
        'DragonFight': nbt.Compound({'NeedsStateScanning': nbt.Byte(1), 'DragonKilled': nbt.Byte(0),
                                     'PreviouslyKilled': nbt.Byte(0)}),
        'BorderCenterX': nbt.Double(0.0), 'BorderCenterZ': nbt.Double(0.0), 'BorderSize': nbt.Double(59999968.0),
    })
    nbt.ecrire(chemin, '', nbt.Compound({'Data': data}))


def points_de_controle(m, profond, rng, n_hasard=160):
    """Blocs temoins pour la verification en jeu (serveur Forge de la CI) : chaque etat de
    bloc de mod (3 exemplaires), des coffres et generateurs, et des points tires au hasard dans
    l'ile et dans le sous-sol. Lignes « x y z etat » en coordonnees du monde ; la propriete
    `distance` des feuilles est omise (le jeu la recalcule)."""
    inv = {v: k for k, v in m.palette.items()}

    def etat(i):
        nom, props = analyser(inv[int(i)])
        props.pop('distance', None)
        return nom + ('[' + ','.join('%s=%s' % kv for kv in sorted(props.items())) + ']' if props else '')

    lignes = []
    for nom, i in sorted(m.palette.items()):
        if nom.startswith('minecraft:'):
            continue
        trouves = 0
        for tableau, dy in ((m.blocs, DECALAGE_Y), (profond, Y_MIN)):
            if trouves >= 3:
                break
            ys, zs, xs = np.nonzero(tableau == i)
            if len(ys):
                for k in rng.choice(len(ys), min(3 - trouves, len(ys)), replace=False):
                    lignes.append((int(xs[k]) + ORIGINE, int(ys[k]) + dy, int(zs[k]) + ORIGINE, etat(i)))
                    trouves += 1
    for (x, y, z, d) in m.entites[::max(1, len(m.entites) // 12)]:
        # le bloc porteur de l'entite (coffre, generateur...) doit etre la, dans l'etat prevu
        i = m.blocs[y, z, x] if y >= 0 else profond[y + DECALAGE_Y - Y_MIN, z, x]
        lignes.append((x + ORIGINE, y + DECALAGE_Y, z + ORIGINE, etat(i)))
    H = m.H
    for _ in range(n_hasard):
        x, z = int(rng.integers(0, m.W)), int(rng.integers(0, m.L))
        if rng.random() < 0.35:
            i = int(rng.integers(1, profond.shape[0]))
            lignes.append((x + ORIGINE, i + Y_MIN, z + ORIGINE, etat(profond[i, z, x])))
        else:
            y = int(rng.integers(0, H))
            lignes.append((x + ORIGINE, y + DECALAGE_Y, z + ORIGINE, etat(m.blocs[y, z, x])))
    return lignes


def temoins_entites(m):
    """Temoins pour les entites : chaque noeud de chaine (present, et encore porteur de sa
    chaine apres chargement), barques et wagonnets. Lignes « x y z mob:type » ou
    « x y z mobdata:type:chemin »."""
    lignes = []
    for (x, y, z, d) in m.mobiles:
        t = str(d['id'].v)
        X, Y, Z = x + ORIGINE, y + DECALAGE_Y, z + ORIGINE
        if 'Chains' in d:
            lignes.append((round(X, 2), round(Y, 2), round(Z, 2), 'mobdata:%s:Chains' % t))
        else:
            lignes.append((round(X, 2), round(Y, 2), round(Z, 2), 'mob:%s' % t))
    return lignes
