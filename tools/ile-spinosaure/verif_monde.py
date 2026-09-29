"""Relit le monde exporte (regions .mca) avec nbtlib, independamment de l'exporteur, et le
compare bloc a bloc au modele (blocs.npy + profond.npy + palette.json) sur des chunks tires au
sort : format des regions, compression, NBT, palettes, tableaux de longs, biomes, entites de
blocs, level.dat.

Usage : python3 verif_monde.py dossier_de_generation [n_chunks]
"""
import gzip
import io
import json
import math
import os
import struct
import sys
import zlib

import nbtlib
import numpy as np

import monde_java as mj


def lire_chunk(chemin, cx, cz):
    with open(chemin, 'rb') as f:
        data = f.read()
    idx = (cx & 31) + (cz & 31) * 32
    loc = struct.unpack('>I', data[idx * 4:idx * 4 + 4])[0]
    off, n = loc >> 8, loc & 0xFF
    assert off >= 2 and n > 0, 'chunk absent %d %d' % (cx, cz)
    lg, typ = struct.unpack('>ib', data[off * 4096:off * 4096 + 5])
    assert typ == 2 and lg + 4 <= n * 4096, 'entete de chunk'
    brut = zlib.decompress(data[off * 4096 + 5:off * 4096 + 4 + lg])
    return nbtlib.File.parse(io.BytesIO(brut))


def deplier(longs, bits, n=4096):
    par = 64 // bits
    v = np.array(longs, dtype=np.int64).view(np.uint64)
    masque = np.uint64((1 << bits) - 1)
    out = np.zeros(len(v) * par, np.uint64)
    for k in range(par):
        out[k::par] = (v >> np.uint64(k * bits)) & masque
    return out[:n].astype(np.int64)


def etat_texte(c):
    nom = str(c['Name'])
    if 'Properties' in c and len(c['Properties']):
        return nom + '[' + ','.join('%s=%s' % (k, str(v)) for k, v in sorted(c['Properties'].items())) + ']'
    return nom


def normaliser(etat):
    nom, props = mj.analyser(etat)
    if not props:
        return nom
    return nom + '[' + ','.join('%s=%s' % kv for kv in sorted(props.items())) + ']'


def main(dossier, n_chunks=60):
    blocs = np.load(os.path.join(dossier, 'blocs.npy'), mmap_mode='r')
    prof = np.load(os.path.join(dossier, 'profond.npy'), mmap_mode='r')
    palette = json.load(open(os.path.join(dossier, 'palette.json')))
    inv = {v: normaliser(k) for k, v in palette.items()}
    monde = os.path.join(dossier, 'Site B')
    rng = np.random.default_rng(5)
    H = blocs.shape[0]
    erreurs = 0
    compte = {}
    # 1. level.dat
    ld = nbtlib.load(os.path.join(monde, 'level.dat'))
    d = ld['Data']
    print('level.dat : DataVersion %d, %s, apparition (%d, %d, %d), generateur %s' % (
        d['DataVersion'], d['Version']['Name'], d['SpawnX'], d['SpawnY'], d['SpawnZ'],
        d['WorldGenSettings']['dimensions']['minecraft:overworld']['generator']['type']))
    couches = d['WorldGenSettings']['dimensions']['minecraft:overworld']['generator']['settings']['layers']
    haut = -64 + sum(int(c['height']) for c in couches) - 1
    print('ocean plat : %s -> eau jusqu\'a y = %d' % ([(str(c['block']), int(c['height'])) for c in couches], haut))
    # 2. chunks : tous les coins + un tirage
    cxs = list(range(mj.ORIGINE >> 4, (mj.ORIGINE + blocs.shape[2]) >> 4))
    tirage = [(cxs[0], cxs[0]), (cxs[-1], cxs[-1]), (cxs[0], cxs[-1]), (cxs[-1], cxs[0])]
    tirage += [(int(rng.choice(cxs)), int(rng.choice(cxs))) for _ in range(n_chunks)]
    n_be = 0
    for (cx, cz) in tirage:
        chemin = os.path.join(monde, 'region', 'r.%d.%d.mca' % (cx >> 5, cz >> 5))
        c = lire_chunk(chemin, cx, cz)
        assert int(c['xPos']) == cx and int(c['zPos']) == cz and int(c['DataVersion']) == mj.DATA_VERSION
        assert str(c['Status']) == 'minecraft:full'
        secs = c['sections']
        assert len(secs) == mj.N_SECTIONS
        x0, z0 = cx * 16 - mj.ORIGINE, cz * 16 - mj.ORIGINE
        for s in secs:
            sy = int(s['Y'])
            pal = [etat_texte(p) for p in s['block_states']['palette']]
            if 'data' in s['block_states']:
                bits = max(4, math.ceil(math.log2(len(pal))))
                assert len(s['block_states']['data']) == math.ceil(4096 / (64 // bits)), 'longueur des longs'
                ids = deplier(s['block_states']['data'], bits)
            else:
                ids = np.zeros(4096, np.int64)
            lu = np.array(pal, dtype=object)[ids].reshape(16, 16, 16)
            # attendu
            att = np.empty((16, 16, 16), dtype=object)
            for k in range(16):
                y = sy * 16 + k
                if y < mj.DECALAGE_Y:
                    i = y - mj.Y_MIN
                    ligne = prof[i, z0:z0 + 16, x0:x0 + 16]
                elif y - mj.DECALAGE_Y < H:
                    ligne = blocs[y - mj.DECALAGE_Y, z0:z0 + 16, x0:x0 + 16]
                else:
                    ligne = np.full((16, 16), palette['minecraft:air'])
                att[k] = np.vectorize(inv.get, otypes=[object])(ligne)
            diff = lu != att
            if diff.any():
                erreurs += int(diff.sum())
                k, z, x = np.argwhere(diff)[0]
                print('ECART chunk (%d,%d) section %d : lu %s attendu %s' % (cx, cz, sy, lu[k, z, x], att[k, z, x]))
            for e in pal:
                compte[e.split('[')[0]] = compte.get(e.split('[')[0], 0) + 1
            b = s['biomes']
            assert len(b['palette']) >= 1
        for be in c['block_entities']:
            n_be += 1
            X, Y, Z = int(be['x']), int(be['y']), int(be['z'])
            assert cx * 16 <= X < cx * 16 + 16 and cz * 16 <= Z < cz * 16 + 16, 'entite hors du chunk'
    print('%d chunks relus, %d ecarts, %d entites de blocs' % (len(tirage), erreurs, n_be))
    mods = sorted({k for k in compte if not k.startswith('minecraft:')})
    print('blocs de mods rencontres : %s' % ', '.join(mods))
    return erreurs


if __name__ == '__main__':
    sys.exit(1 if main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 60) else 0)
