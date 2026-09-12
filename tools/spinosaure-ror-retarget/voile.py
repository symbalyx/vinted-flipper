"""Retaille le profil de la voile SANS modifier un seul pixel de texture.

Changer la hauteur d'une dalle sans toucher a son rectangle UV etirerait la
texture : l'aspect changerait alors qu'aucun pixel n'aurait bouge. On re-mappe
donc chaque flanc a densite constante (la densite propre de la dalle, ~7.44 px
par unite), en gardant le bas du rectangle fixe puisque la voile est alignee
par le bas.

Seules les faces east/west portent la texture haute de la voile ; north, south,
up et down pointent deja toutes sur un petit patch generique commun aux 12
dalles, quelles que soient leurs hauteurs : le modele ne leur demande aucune
coherence de densite, on n'y touche pas.
"""
import json, sys

PROFILS = {
    'A': [40.0, 49.0, 55.2, 59.4, 62.1, 63.3, 63.3, 62.1, 59.4, 55.2, 49.0, 40.0],
    'B': [42.0, 53.7, 61.5, 66.7, 70.0, 71.6, 71.6, 70.0, 66.7, 61.5, 53.7, 42.0],
    'C': [38.0, 48.4, 57.0, 63.4, 67.3, 67.3, 64.2, 59.9, 54.6, 48.4, 41.5, 34.0],
}
V_PLAFOND = 1272.0   # haut de la bande de camouflage peinte de la voile


def reshape(bb, profil):
    gm = {g['uuid']: g for g in bb['groups']}
    em = {e['uuid']: e for e in bb['elements']}

    def find(n, name):
        if isinstance(n, str):
            return None
        if gm.get(n['uuid'], {}).get('name') == name:
            return n
        for c in n.get('children', []):
            r = find(c, name)
            if r:
                return r

    sail = find(bb['outliner'][0], 'sail')
    cubes = [em[c] for c in sail['children'] if isinstance(c, str)]
    slabs = sorted([e for e in cubes if 'bord' not in e['name']], key=lambda e: e['from'][2])
    bords = sorted([e for e in cubes if 'bord' in e['name']], key=lambda e: e['from'][2])
    assert len(slabs) == len(bords) == len(profil), (len(slabs), len(bords), len(profil))

    rap = []
    for i, (sl, bo) in enumerate(zip(slabs, bords)):
        base = sl['from'][1]
        h_old = sl['to'][1] - base
        h_new = profil[i]
        top_old, top_new = sl['to'][1], base + h_new
        # le bord garde son decalage relatif au sommet de la dalle
        d0 = bo['from'][1] - top_old
        d1 = bo['to'][1] - top_old
        sl['to'][1] = round(top_new, 4)
        bo['from'][1] = round(top_new + d0, 4)
        bo['to'][1] = round(top_new + d1, 4)
        # re-mappage UV des flancs, a la densite propre de la dalle
        for f in ('east', 'west'):
            uv = sl['faces'][f]['uv']
            v_haut, v_bas = min(uv[1], uv[3]), max(uv[1], uv[3])
            dens = (v_bas - v_haut) / h_old
            v_new = v_bas - dens * h_new
            assert v_new >= V_PLAFOND - 1e-6, (
                'dalle %d : le sommet UV %0.1f depasse la bande peinte (%0.1f)' % (i, v_new, V_PLAFOND))
            uv[1], uv[3] = (round(v_new, 4), round(v_bas, 4)) if uv[1] < uv[3] else \
                           (round(v_bas, 4), round(v_new, 4))
        rap.append((sl['name'], round(h_old, 1), round(h_new, 1), round(dens, 3),
                    round((v_bas - v_new) / h_new, 3)))
    return rap


if __name__ == '__main__':
    src, dst, p = sys.argv[1], sys.argv[2], sys.argv[3]
    bb = json.load(open(src))
    rap = reshape(bb, PROFILS[p])
    json.dump(bb, open(dst, 'w'), separators=(',', ':'))
    print('profil %s applique' % p)
    print('%-16s %8s %8s %10s %10s' % ('dalle', 'avant', 'apres', 'dens.av', 'dens.ap'))
    for n, a, b, d0, d1 in rap:
        print('%-16s %8.1f %8.1f %10.3f %10.3f%s' % (n, a, b, d0, d1,
              '   OK' if abs(d0 - d1) < 0.01 else '   !! DENSITE CHANGEE'))
    print('\necrit', dst)
