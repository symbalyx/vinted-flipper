"""Reprend les idees anatomiques des bras de ROR sans copier sa geometrie.

Trois ajouts, tous en volumes pleins fins (le modele RIVIERE n'utilise aucun plan
a epaisseur nulle : 0 sur 374 elements) et tous mappes sur des rectangles UV DEJA
peints du modele -> aucun pixel de texture n'est modifie.

  1. palmure entre les doigts   <- plans 19x0x15 de ROR
  2. membrane d'avant-bras      <- plan 0x25x46 de ROR
  3. griffes allongees          <- griffes ROR ~15 u contre 6.5 u chez nous
"""
import json, uuid, sys, copy

NS = uuid.UUID('2b7c9d14-5a3e-4f81-8c20-7d6e1b4a9f33')


def load(path):
    return json.load(open(path))


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
    return gm, em, nodes


def cubes(node, em):
    return [em[c] for c in node['children'] if isinstance(c, str)]


def by_name(node, em, frag):
    return [e for e in cubes(node, em) if frag in e['name']]


def mk_cube(name, frm, to, origin, rot, uv):
    """Cube bbmodel complet, 6 faces sur le meme rectangle UV deja peint."""
    faces = {}
    for f in ('north', 'east', 'south', 'west', 'up', 'down'):
        faces[f] = {'texture': 0, 'uv': list(uv), 'rotation': 0}
    return {
        'name': name,
        'uuid': str(uuid.uuid5(NS, name)),
        'type': 'cube',
        'from': [round(v, 4) for v in frm],
        'to': [round(v, 4) for v in to],
        'origin': [round(v, 4) for v in origin],
        'rotation': [round(v, 4) for v in rot],
        'autouv': 0, 'color': 0, 'locked': False, 'visibility': True,
        'export': True, 'inflate': 0, 'faces': faces,
    }


def avg_angle(a, b):
    """Moyenne de deux angles en degres, en gerant le passage par 180."""
    d = ((b - a + 180) % 360) - 180
    return a + d / 2.0


def add(bb, palmure=True, membrane=True, griffes=1.40,
        web_ep=0.7, memb_ep=0.8, memb_larg=10.0, memb_long=20.0, memb_sens=-1,
        web_prise=0.15):
    gm, em, nodes = index(bb)
    added = []

    for side, sgn in (('left', +1), ('right', -1)):
        # ---------------------------------------------------- 1. palmure
        if palmure:
            fing = [nodes['finger_%s_%d' % (side, i)] for i in range(3)]
            phal = [[e for e in cubes(f, em) if 'doigt' in e['name']] for f in fing]
            for gap, (a_i, b_i) in enumerate(((0, 1), (1, 2))):
                for p in range(2):
                    if p >= len(phal[a_i]) or p >= len(phal[b_i]):
                        continue
                    A, B = phal[a_i][p], phal[b_i][p]
                    # x : d un doigt a l autre, en mordant legerement dans chacun
                    xa, xb = sorted((A['origin'][0], B['origin'][0]))
                    # mordre profondement dans chaque doigt : la palmure doit tenir
                    # malgre le jeu residuel entre doigts (12 deg -> environ 0.6 u)
                    x0, x1 = xa - web_prise, xb + web_prise
                    if x1 <= x0:
                        continue
                    oy = (A['origin'][1] + B['origin'][1]) / 2.0
                    oz = (A['origin'][2] + B['origin'][2]) / 2.0
                    zl = min(abs(A['to'][2] - A['from'][2]), abs(B['to'][2] - B['from'][2]))
                    rot = [avg_angle(A['rotation'][0], B['rotation'][0]),
                           avg_angle(A['rotation'][1], B['rotation'][1]), 0.0]
                    origin = [(x0 + x1) / 2.0, oy, oz]
                    # rattachee a la main et non a un doigt : le jeu se repartit
                    # sur les deux bords au lieu de s accumuler sur un seul
                    added.append((nodes['hand_%s' % side], mk_cube(
                        'V71_palmure_%s_%d%d_%d' % (side, a_i, b_i, p),
                        [x0, oy - web_ep / 2, oz - zl / 2],
                        [x1, oy + web_ep / 2, oz + zl / 2],
                        origin, rot, A['faces']['west']['uv'])))

        # ---------------------------------------------------- 2. membrane d avant-bras
        if membrane:
            fa = nodes['forearm_%s' % side]
            ref = by_name(fa, em, 'avant_bras')[0]
            o = ref['origin']
            ly = memb_larg
            off = memb_sens * (abs(ref['to'][1] - ref['from'][1]) / 2 + ly / 2 - 1.0)
            added.append((fa, mk_cube(
                'V71_membrane_avant_bras_%s' % side,
                [o[0] - memb_ep / 2, o[1] + off - ly / 2, o[2] - memb_long / 2],
                [o[0] + memb_ep / 2, o[1] + off + ly / 2, o[2] + memb_long / 2],
                list(o), list(ref['rotation']), ref['faces']['west']['uv'])))

        # ---------------------------------------------------- 3. griffes allongees
        if griffes and griffes != 1.0:
            for i in range(3):
                g = nodes['finger_%s_%d' % (side, i)]
                cl = [e for e in cubes(g, em) if 'griffe' in e['name']]
                if not cl:
                    continue
                # point d attache : arriere-haut du premier segment de griffe
                base = [cl[0]['origin'][0],
                        max(cl[0]['from'][1], cl[0]['to'][1]),
                        max(cl[0]['from'][2], cl[0]['to'][2])]
                k = griffes
                for e in cl:
                    for key in ('from', 'to', 'origin'):
                        e[key] = [round(base[j] + (e[key][j] - base[j]) * k, 4) for j in range(3)]
    for node, cube in added:
        bb['elements'].append(cube)
        node['children'].append(cube['uuid'])
    return len(added)


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    kw = {}
    for a in sys.argv[3:]:
        k, v = a.split('=')
        kw[k] = float(v) if '.' in v or v.lstrip('-').isdigit() else v
    bb = load(src)
    n = add(bb, **kw)
    json.dump(bb, open(dst, 'w'), separators=(',', ':'))
    print('%d cubes ajoutes -> %s (total %d elements)' % (n, dst, len(bb['elements'])))
