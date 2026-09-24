"""Nageoires : main, avant-bras, orteils et tibia, d'apres l'idee de ROR.

ROR equipe son spino de plaques plates :
    Leg6  (tibia)  cube 7x30x10  + PLAN 15x14x0   -> flasque laterale au mollet
    Foot4/5/6      cube 3x13x5   + PLAN 0x9x6     -> flasque sur chaque orteil
    Arm4           cube 6x9x28   + PLAN 0x25x46   -> membrane d'avant-bras
    doigts         cube 5x4x15   + PLAN 19x0x15   -> palmure large

Les versions precedentes placaient la palmure de main a la hauteur des doigts :
elle les traversait et se lisait comme des barres posees dessus. Ici chaque
nageoire est une feuille FINE et CONTINUE, decalee sous la piece qu'elle prolonge,
pour se lire comme une membrane et non comme un baton.

Aucun pixel de texture n'est ajoute : toutes les faces pointent sur des
rectangles UV deja peints du modele.
"""
import json, uuid, sys
from fk import mat_rot, apply
from boite import coins

NS = uuid.UUID('7d1c4e93-0a62-4f15-9b83-2e5a6c0d41f7')


def mk(name, frm, to, origin, rot, uv):
    faces = {f: {'texture': 0, 'uv': list(uv), 'rotation': 0}
             for f in ('north', 'east', 'south', 'west', 'up', 'down')}
    return {'name': name, 'uuid': str(uuid.uuid5(NS, name)), 'type': 'cube',
            'from': [round(v, 4) for v in frm], 'to': [round(v, 4) for v in to],
            'origin': [round(v, 4) for v in origin], 'rotation': [round(v, 4) for v in rot],
            'autouv': 0, 'color': 0, 'locked': False, 'visibility': True,
            'export': True, 'inflate': 0, 'faces': faces}


def _monde(e):
    """Coins monde (au repos) d'un cube tourne autour de son origine."""
    R, o = mat_rot(*e.get('rotation', [0, 0, 0])), e['origin']
    return [[a + b for a, b in zip(apply(R, [p[k] - o[k] for k in range(3)]), o)]
            for p in coins(e['from'], e['to'])]


def _local(R, o, p):
    """Point monde -> repere local d'un cube (R orthogonale : inverse = transposee)."""
    d = [p[k] - o[k] for k in range(3)]
    return [sum(R[k][j] * d[k] for k in range(3)) for j in range(3)]


def index(bb):
    gm = {g['uuid']: g for g in bb['groups']}
    em = {e['uuid']: e for e in bb['elements']}
    nodes = {}

    def walk(n):
        if isinstance(n, str):
            return
        nodes[gm[n['uuid']]['name']] = n
        for c in n.get('children', []):
            walk(c)
    walk(bb['outliner'][0])
    return em, nodes


def cubes(node, em):
    return [em[c] for c in node['children'] if isinstance(c, str)]


def par_nom(bb, nom):
    return [e for e in bb['elements'] if e['name'] == nom][0]


def ajoute(bb, ep_main=0.55, deb_main=2.0, deb_int=2.0, fin_main=2.5, ep_pied=0.7, deb_pied=1.2,
           ep_tibia=0.6, flasque_tibia=8.0, ep_bras=0.55, larg_bras=11.0):
    em, nodes = index(bb)
    out = []

    for cote, sgn in (('left', +1), ('right', -1)):
        # ---------------------------------------------------------- main
        # V82 : la feuille unique de V74 prenait la moyenne des rotations X des doigts
        # mais oubliait leur rotation Y de 180 degres : elle etait inclinee de -53 au
        # lieu de +53 et coupait les doigts a ~106 degres, comme une lame.
        # Desormais chaque doigt EXTERNE porte sa palmure, construite dans le repere
        # exact de sa phalange proximale (meme origine, meme rotation) : elle est dans
        # le plan median du doigt par construction, suit le doigt quand il bouge, et
        # son bord interne s'enfonce dans le doigt du milieu (cache dedans) au lieu
        # de flotter.
        d0 = [par_nom(bb, 'V67_doigt_%s_%d_0' % (cote, i)) for i in range(3)]
        d1 = [par_nom(bb, 'V67_doigt_%s_%d_1' % (cote, i)) for i in range(3)]
        centre = [e['origin'] for e in d0]
        for i in (0, 2):
            p0, p1 = d0[i], d1[i]
            R = mat_rot(*p0['rotation'])
            o = p0['origin']
            L0 = [_local(R, o, q) for q in _monde(p0)]
            L1 = [_local(R, o, q) for q in _monde(p1)]
            hx = max(abs(q[0]) for q in L0)
            z0 = min(q[2] for q in L0) - 1.0                # entre dans la paume
            z1 = max(q[2] for q in L1) - fin_main           # s'arrete avant la griffe
            # cote du doigt du milieu, exprime dans l'axe X local du doigt
            vers = [centre[1][k] - centre[i][k] for k in range(3)]
            s_in = 1 if sum(R[k][0] * vers[k] for k in range(3)) > 0 else -1
            bord_in, bord_out = s_in * (hx + deb_int), -s_in * (hx + deb_main)
            xa, xb = min(bord_in, bord_out), max(bord_in, bord_out)
            out.append((nodes['finger_%s_%d' % (cote, i)], mk(
                'V82_palmure_main_%s_%d' % (cote, i),
                [o[0] + xa, o[1] - ep_main / 2, o[2] + z0],
                [o[0] + xb, o[1] + ep_main / 2, o[2] + z1],
                list(o), list(p0['rotation']), p0['faces']['up']['uv'])))

        # ---------------------------------------------------------- avant-bras
        ab = par_nom(bb, 'V67_avant_bras_%s' % cote)
        o = ab['origin']
        dy = abs(ab['to'][1] - ab['from'][1]) / 2
        out.append((nodes['forearm_%s' % cote], mk(
            'V74_nageoire_avant_bras_%s' % cote,
            [o[0] - ep_bras / 2, o[1] - dy - larg_bras, o[2] - 11.0],
            [o[0] + ep_bras / 2, o[1] - dy + 1.0, o[2] + 11.0],
            list(o), list(ab['rotation']), ab['faces']['west']['uv'])))

        # ---------------------------------------------------------- orteils
        orts = [par_nom(bb, 'V46_orteil_%s_%d' % (cote, i)) for i in range(3)]
        gx0 = min(min(e['from'][0], e['to'][0]) for e in orts) - deb_pied
        gx1 = max(max(e['from'][0], e['to'][0]) for e in orts) + deb_pied
        gz0 = min(min(e['from'][2], e['to'][2]) for e in orts) - 1.0
        gz1 = max(max(e['from'][2], e['to'][2]) for e in orts) - 1.5
        oy = sum((e['from'][1] + e['to'][1]) / 2 for e in orts) / 3
        out.append((nodes['foot_%s' % cote], mk(
            'V74_palmure_pied_%s' % cote,
            [gx0, oy - ep_pied / 2 - 0.6, gz0], [gx1, oy + ep_pied / 2 - 0.6, gz1],
            [(gx0 + gx1) / 2, oy, (gz0 + gz1) / 2], [0.0, 0.0, 0.0],
            orts[0]['faces']['west']['uv'])))

        # ---------------------------------------------------------- tibia
        # flasque laterale, plate, sur le bas de la jambe : la piece de ROR
        tb = par_nom(bb, 'V46_tibia_%s_1' % cote)
        o = tb['origin']
        xb = max(tb['from'][0], tb['to'][0]) if sgn > 0 else min(tb['from'][0], tb['to'][0])
        out.append((nodes['shin_%s' % cote], mk(
            'V74_flasque_tibia_%s' % cote,
            [min(xb, xb + sgn * flasque_tibia) - 1.0, o[1] - 9.0, o[2] - ep_tibia / 2],
            [max(xb, xb + sgn * flasque_tibia) + 1.0, o[1] + 5.0, o[2] + ep_tibia / 2],
            list(o), list(tb['rotation']), tb['faces']['west']['uv'])))

    for node, cube in out:
        bb['elements'].append(cube)
        node['children'].append(cube['uuid'])
    return len(out)


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    bb = json.load(open(src))
    n = ajoute(bb)
    json.dump(bb, open(dst, 'w'), separators=(',', ':'))
    print('%d nageoires ajoutees -> %s (total %d elements)' % (n, dst, len(bb['elements'])))
    for e in bb['elements']:
        if e['name'].startswith(('V74_', 'V82_')):
            print('   %-32s %5.1f x %5.1f x %5.1f' % (e['name'],
                  *[e['to'][i] - e['from'][i] for i in range(3)]))
