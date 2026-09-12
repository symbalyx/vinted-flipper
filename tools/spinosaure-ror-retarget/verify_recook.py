"""Verifie qu'un recuit n'a RIEN change d'autre que le nombre de cles."""
import json, sys

a = json.load(open(sys.argv[1]))   # avant
b = json.load(open(sys.argv[2]))   # apres
ok = True


def fail(msg):
    global ok
    ok = False
    print('  ECHEC :', msg)


# 1) tout ce qui n'est pas animation doit etre strictement identique
for k in ['meta', 'name', 'model_identifier', 'visible_box', 'variable_placeholders',
          'resolution', 'elements', 'groups', 'outliner', 'textures', 'credit']:
    if json.dumps(a.get(k), sort_keys=True) != json.dumps(b.get(k), sort_keys=True):
        fail('champ modifie : ' + k)
print('1. geometrie, squelette, texture, credit : %s' % ('identiques' if ok else 'DIFFERENTS'))

# 2) meme liste d'animations, memes metadonnees
am = {x['name']: x for x in a['animations']}
bm = {x['name']: x for x in b['animations']}
if set(am) != set(bm):
    fail('liste d animations differente')
for n in am:
    for f in ('uuid', 'loop', 'length', 'override'):
        if am[n].get(f) != bm[n].get(f):
            fail('%s : champ %s modifie' % (n, f))
    if ('snapping' in am[n]) != ('snapping' in bm[n]) or am[n].get('snapping') != bm[n].get('snapping'):
        fail('%s : snapping modifie' % n)
    if set(am[n]['animators']) != set(bm[n]['animators']):
        fail('%s : liste d animateurs differente' % n)
    for u in am[n]['animators']:
        for f in ('name', 'type'):
            if am[n]['animators'][u].get(f) != bm[n]['animators'][u].get(f):
                fail('%s/%s : champ %s modifie' % (n, u, f))
print('2. %d animations, metadonnees et animateurs : %s'
      % (len(am), 'preserves' if ok else 'ALTERES'))

# 3) aucune valeur modifiee : chaque cle restante doit exister a l'identique dans l'original
tot_a = tot_b = 0
for n in am:
    for u in am[n]['animators']:
        orig = {json.dumps(kf, sort_keys=True) for kf in am[n]['animators'][u]['keyframes']}
        tot_a += len(am[n]['animators'][u]['keyframes'])
        for kf in bm[n]['animators'][u]['keyframes']:
            tot_b += 1
            if json.dumps(kf, sort_keys=True) not in orig:
                fail('%s/%s : cle modifiee ou inventee a t=%s' % (n, am[n]['animators'][u]['name'], kf['time']))
print('3. %d cles -> %d : %s (aucune valeur reecrite, uniquement des suppressions)'
      % (tot_a, tot_b, 'sous-ensemble strict' if ok else 'ALTERE'))

# 4) chaque piste conserve ses bornes temporelles
for n in am:
    for u in am[n]['animators']:
        pa, pb = {}, {}
        for kf in am[n]['animators'][u]['keyframes']:
            pa.setdefault(kf['channel'], []).append(kf['time'])
        for kf in bm[n]['animators'][u]['keyframes']:
            pb.setdefault(kf['channel'], []).append(kf['time'])
        if set(pa) != set(pb):
            fail('%s/%s : canal disparu' % (n, am[n]['animators'][u]['name']))
            continue
        for c in pa:
            if min(pa[c]) != min(pb[c]) or max(pa[c]) != max(pb[c]):
                fail('%s/%s/%s : bornes temporelles modifiees' % (n, am[n]['animators'][u]['name'], c))
print('4. bornes de chaque piste (premiere et derniere cle) : %s'
      % ('preservees' if ok else 'ALTEREES'))

# 5) fermeture des boucles
bad = 0
for n, an in bm.items():
    if an.get('loop') != 'loop':
        continue
    for u, v in an['animators'].items():
        per = {}
        for kf in v['keyframes']:
            per.setdefault(kf['channel'], []).append(
                (kf['time'], [float(kf['data_points'][0].get(q, 0) or 0) for q in 'xyz']))
        for c, p in per.items():
            if len(p) < 2:
                continue
            p.sort()
            if max(abs(p[0][1][i] - p[-1][1][i]) for i in range(3)) > 0.02:
                bad += 1
print('5. boucles non refermees :', bad)

print()
print('VERDICT :', 'conforme' if ok and bad == 0 else 'NON CONFORME')
sys.exit(0 if ok and bad == 0 else 1)
