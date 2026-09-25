"""Exporte un .bbmodel (format bedrock) vers les fichiers que GeckoLib lit :
geo/<nom>.geo.json (format 1.12.0) et animations/<nom>.animation.json (format 1.8.0).

Reproduit l'export « Bedrock Geometry » / « Export Animations » de Blockbench :
  - os : pivot avec X oppose ; rotation avec X et Y opposes ;
  - cubes : origine = coin min avec X miroir -(from.x + taille.x) ; pivot X oppose ;
    rotation X et Y opposees ; UV par face [u, v] + [du, dv], les faces up et down
    retournees (u + du, v + dv, tailles negatives) comme le fait Blockbench ;
  - animations : valeurs des images cles telles quelles (c'est l'espace des animations
    bedrock), boucle 'loop' -> true, 'hold' -> "hold_on_last_frame", 'once' -> absent.
GeckoLib applique les conventions inverses a la lecture.

Usage : python3 export_geckolib.py MODELE.bbmodel DOSSIER_ASSETS [nom]
        (DOSSIER_ASSETS = .../src/main/resources/assets/<modid>)
"""
import json
import os
import sys


def nombre(v):
    v = float(v)
    r = round(v, 4)
    return int(r) if r == int(r) else r


def geo(bb, identifiant):
    groupes = {g['uuid']: g for g in bb['groups']}
    elements = {e['uuid']: e for e in bb['elements']}
    os_ = []

    def cube(e):
        taille = [e['to'][k] - e['from'][k] for k in range(3)]
        c = {'origin': [nombre(-(e['from'][0] + taille[0])), nombre(e['from'][1]), nombre(e['from'][2])],
             'size': [nombre(t) for t in taille]}
        if e.get('inflate'):
            c['inflate'] = nombre(e['inflate'])
        rot = e.get('rotation') or [0, 0, 0]
        if any(abs(r) > 1e-9 for r in rot):
            o = e['origin']
            c['pivot'] = [nombre(-o[0]), nombre(o[1]), nombre(o[2])]
            c['rotation'] = [nombre(-rot[0]), nombre(-rot[1]), nombre(rot[2])]
        uv = {}
        for nom, f in e['faces'].items():
            if f.get('texture') is None or f.get('enabled') is False:
                continue
            u0, v0, u1, v1 = f['uv']
            u, v, du, dv = u0, v0, u1 - u0, v1 - v0
            if nom in ('up', 'down'):
                u, v, du, dv = u + du, v + dv, -du, -dv
            face = {'uv': [nombre(u), nombre(v)], 'uv_size': [nombre(du), nombre(dv)]}
            if f.get('rotation'):
                face['uv_rotation'] = f['rotation']
            uv[nom] = face
        c['uv'] = uv
        return c

    def parcourir(noeud, parent):
        if isinstance(noeud, str):
            return
        g = groupes[noeud['uuid']]
        if g.get('export') is False:
            return
        os_courant = {'name': g['name'], 'pivot': [nombre(-g['origin'][0]), nombre(g['origin'][1]), nombre(g['origin'][2])]}
        if parent:
            os_courant['parent'] = parent
        rot = g.get('rotation') or [0, 0, 0]
        if any(abs(r) > 1e-9 for r in rot):
            os_courant['rotation'] = [nombre(-rot[0]), nombre(-rot[1]), nombre(rot[2])]
        cubes = [cube(elements[c]) for c in noeud.get('children', [])
                 if isinstance(c, str) and elements[c].get('export', True) is not False
                 and elements[c].get('type', 'cube') == 'cube']
        if cubes:
            os_courant['cubes'] = cubes
        os_.append(os_courant)
        for c in noeud.get('children', []):
            parcourir(c, g['name'])

    for racine in bb['outliner']:
        parcourir(racine, None)
    res = bb.get('resolution', {'width': 16, 'height': 16})
    return {'format_version': '1.12.0', 'minecraft:geometry': [{
        'description': {'identifier': 'geometry.' + identifiant,
                        'texture_width': res['width'], 'texture_height': res['height'],
                        'visible_bounds_width': 24, 'visible_bounds_height': 12,
                        'visible_bounds_offset': [0, 4, 0]},
        'bones': os_}]}


def animations(bb):
    noms_os = {g['uuid']: g['name'] for g in bb['groups']}
    out = {}
    for a in bb['animations']:
        entree = {'animation_length': nombre(a['length'])}
        if a.get('loop') == 'loop':
            entree['loop'] = True
        elif a.get('loop') == 'hold':
            entree['loop'] = 'hold_on_last_frame'
        os_ = {}
        for uuid_, an in a.get('animators', {}).items():
            nom = an.get('name') or noms_os.get(uuid_)
            if nom not in noms_os.values() or an.get('type', 'bone') != 'bone':
                continue
            canaux = {}
            for k in an['keyframes']:
                if k['channel'] not in ('rotation', 'position', 'scale'):
                    continue
                if k.get('interpolation', 'linear') != 'linear':
                    raise ValueError('interpolation non geree : %s' % k.get('interpolation'))
                p = k['data_points'][0]
                val = [nombre(p.get(ax, 0) or 0) for ax in 'xyz']
                t = ('%.4f' % k['time']).rstrip('0')
                t = t + '0' if t.endswith('.') else t
                canaux.setdefault(k['channel'], {})[t] = val
            if canaux:
                os_[nom] = {c: dict(sorted(v.items(), key=lambda kv: float(kv[0]))) for c, v in canaux.items()}
        entree['bones'] = os_
        out[a['name']] = entree
    return {'format_version': '1.8.0', 'animations': out}


def main():
    src, dossier = sys.argv[1], sys.argv[2]
    nom = sys.argv[3] if len(sys.argv) > 3 else 'spinosaure'
    bb = json.load(open(src))
    os.makedirs(os.path.join(dossier, 'geo'), exist_ok=True)
    os.makedirs(os.path.join(dossier, 'animations'), exist_ok=True)
    g = geo(bb, nom)
    a = animations(bb)
    pg = os.path.join(dossier, 'geo', nom + '.geo.json')
    pa = os.path.join(dossier, 'animations', nom + '.animation.json')
    json.dump(g, open(pg, 'w'), separators=(',', ':'))
    json.dump(a, open(pa, 'w'), separators=(',', ':'))
    nc = sum(len(b.get('cubes', [])) for b in g['minecraft:geometry'][0]['bones'])
    nk = sum(len(v) for an in a['animations'].values() for b in an['bones'].values() for v in b.values())
    print('%s : %d os, %d cubes (%.1f Mo)' % (pg, len(g['minecraft:geometry'][0]['bones']), nc, os.path.getsize(pg) / 1e6))
    print('%s : %d animations, %d cles (%.1f Mo)' % (pa, len(a['animations']), nk, os.path.getsize(pa) / 1e6))


if __name__ == '__main__':
    main()
