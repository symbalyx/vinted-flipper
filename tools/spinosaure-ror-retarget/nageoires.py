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

NS = uuid.UUID('7d1c4e93-0a62-4f15-9b83-2e5a6c0d41f7')


def mk(name, frm, to, origin, rot, uv):
    faces = {f: {'texture': 0, 'uv': list(uv), 'rotation': 0}
             for f in ('north', 'east', 'south', 'west', 'up', 'down')}
    return {'name': name, 'uuid': str(uuid.uuid5(NS, name)), 'type': 'cube',
            'from': [round(v, 4) for v in frm], 'to': [round(v, 4) for v in to],
            'origin': [round(v, 4) for v in origin], 'rotation': [round(v, 4) for v in rot],
            'autouv': 0, 'color': 0, 'locked': False, 'visibility': True,
            'export': True, 'inflate': 0, 'faces': faces}


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


def ajoute(bb, ep_main=0.55, deb_main=2.2, ep_pied=0.7, deb_pied=1.2,
           ep_tibia=0.6, flasque_tibia=8.0, ep_bras=0.55, larg_bras=11.0):
    em, nodes = index(bb)
    out = []

    for cote, sgn in (('left', +1), ('right', -1)):
        # ---------------------------------------------------------- main
        # une seule feuille, calee sous le plan des doigts pour ne pas les traverser
        dg = []
        for i in range(3):
            dg += [e for e in cubes(nodes['finger_%s_%d' % (cote, i)], em) if 'doigt' in e['name']]
        prox = [e for e in dg if e['name'].endswith('_0')]
        x0 = min(min(e['from'][0], e['to'][0]) for e in dg) - deb_main
        x1 = max(max(e['from'][0], e['to'][0]) for e in dg) + deb_main
        oy = sum(e['origin'][1] for e in prox) / len(prox)
        oz = sum(e['origin'][2] for e in prox) / len(prox)
        rx = sum(e['rotation'][0] for e in prox) / len(prox)
        out.append((nodes['hand_%s' % cote], mk(
            'V74_nageoire_main_%s' % cote,
            [x0, oy - 2.6 - ep_main, oz - 9.5], [x1, oy - 2.6, oz + 6.5],
            [(x0 + x1) / 2, oy, oz], [rx, 0.0, 0.0], prox[0]['faces']['west']['uv'])))

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
        if e['name'].startswith('V74_'):
            print('   %-32s %5.1f x %5.1f x %5.1f' % (e['name'],
                  *[e['to'][i] - e['from'][i] for i in range(3)]))
