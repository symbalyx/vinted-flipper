"""Audit profond des animations : ce que qualite.py ne regardait pas.

  A. couture des boucles : la position se referme, mais la VITESSE ? un raccord de
     pente donne un a-coup a chaque tour, meme si les valeurs coincident.
  B. limites articulaires : pour chaque os et chaque axe, l enveloppe des animations
     d ORIGINE sert de reference ; on signale ce qui en sort de plus de 15 degres.
  C. patinage des pieds : en appui, le pied doit reculer a vitesse CONSTANTE (le sol
     defile sous une animation sur place) et ne pas glisser lateralement. On en deduit
     aussi la vitesse au sol de chaque allure, a reporter dans le code du mod.
  D. debut et fin des animations jouees une fois : ecart a la pose de repos.
"""
import json, sys, math, os
sys.path.insert(0, 'tools')
import fk as FK

bb = json.load(open(sys.argv[1]))
orig = json.load(open(sys.argv[2]))
rig = FK.Rig(bb)
FLOOR = rig.lowest(rig.pose(lambda b, c: [1., 1., 1.] if c == 'scale' else [0., 0., 0.]))
NOMS_ORIG = {a['name'] for a in orig['animations']}


def pistes(a):
    t = {}
    for u, an in a['animators'].items():
        d = {}
        for kf in an['keyframes']:
            d.setdefault(kf['channel'], []).append(
                (kf['time'], [float(kf['data_points'][0].get(q, 0) or 0) for q in 'xyz']))
        for c in d:
            d[c].sort()
        t[an['name']] = d
    return t


def lp(p, u):
    if u <= p[0][0]:
        return p[0][1]
    if u >= p[-1][0]:
        return p[-1][1]
    for i in range(len(p) - 1):
        if p[i + 1][0] >= u:
            x, y = p[i], p[i + 1]
            f = (u - x[0]) / (y[0] - x[0]) if y[0] > x[0] else 0
            return [x[1][k] + (y[1][k] - x[1][k]) * f for k in range(3)]
    return p[-1][1]


court = lambda a: a['name'].split('.')[-1]
dt = 1 / 30.

# ------------------------------------------------------------------ A. couture
print('A. COUTURE DES BOUCLES (a-coup de vitesse au raccord)')
acoups = []
for a in bb['animations']:
    if a.get('loop') != 'loop':
        continue
    T, L = pistes(a), a['length']
    for b, d in T.items():
        p = d.get('rotation')
        if not p or len(p) < 3:
            continue
        v = [lp(p, min(i * dt, L)) for i in range(int(round(L / dt)) + 1)]
        if len(v) < 5:
            continue
        # vitesse a la fin et au debut, en degres par image
        fin = [v[-1][k] - v[-2][k] for k in range(3)]
        deb = [v[1][k] - v[0][k] for k in range(3)]
        saut = max(abs(fin[k] - deb[k]) for k in range(3))
        ailleurs = max(max(abs((v[i + 1][k] - v[i][k]) - (v[i][k] - v[i - 1][k])) for k in range(3))
                       for i in range(1, len(v) - 1))
        if saut > 2.5 and saut > 2.0 * ailleurs:
            acoups.append((round(saut, 1), round(ailleurs, 1), court(a), b))
acoups.sort(reverse=True)
print('   %d pistes avec un a-coup au raccord' % len(acoups))
for x in acoups[:12]:
    print('     %5.1f deg/img au raccord (max ailleurs %4.1f)  %-28s %s' % x)

# ------------------------------------------------------------------ B. limites
print('\nB. LIMITES ARTICULAIRES (reference : enveloppe des %d animations d origine)' % len(orig['animations']))
env = {}
for a in orig['animations']:
    T, L = pistes(a), a['length']
    for b, d in T.items():
        p = d.get('rotation')
        if not p:
            continue
        for t, v in p:
            e = env.setdefault(b, [[1e9, -1e9] for _ in range(3)])
            for k in range(3):
                e[k][0] = min(e[k][0], v[k]); e[k][1] = max(e[k][1], v[k])
sorties = []
for a in bb['animations']:
    if a['name'] in NOMS_ORIG:
        continue
    T = pistes(a)
    for b, d in T.items():
        p = d.get('rotation')
        if not p or b not in env:
            continue
        for k in range(3):
            lo, hi = env[b][k]
            vmin = min(v[k] for _, v in p); vmax = max(v[k] for _, v in p)
            dep = max(lo - vmin, vmax - hi)
            if dep > 15:
                sorties.append((round(dep, 1), court(a), b, 'xyz'[k], round(vmin, 1), round(vmax, 1),
                                round(lo, 1), round(hi, 1)))
sorties.sort(reverse=True)
print('   %d depassements de plus de 15 deg' % len(sorties))
for s in sorties[:16]:
    print('     +%5.1f  %-28s %-16s %s  [%6.1f,%6.1f]  origine [%6.1f,%6.1f]' % s)
json.dump(sorties, open('/tmp/sorties.json', 'w'))

# ------------------------------------------------------------------ C. patinage
print('\nC. PATINAGE DES PIEDS ET VITESSE AU SOL (allures en boucle)')
ALLURES = [court(a) for a in bb['animations'] if a.get('loop') == 'loop' and any(
    m in court(a) for m in ('marche', 'course', 'traque_lente', 'avance', 'ruee', 'charge',
                            'virage', 'hurle_en_courant'))]
print('   %-26s %8s %9s %9s %11s %9s' % ('allure', 'lateral', 'glisse av', 'irregul.', 'vit. sol', 'blocs/s'))
res_c = []
for nm in ALLURES:
    a = [x for x in bb['animations'] if court(x) == nm][0]
    T, L = pistes(a), a['length']
    n = int(round(L / dt))
    lat, recul, irr, dist, tps = 0.0, 0.0, [], 0.0, 0.0
    for side in ('foot_left', 'foot_right'):
        prev = None
        for i in range(n + 1):
            u = min(i * dt, L)
            P = rig.pose(lambda b, c: (lp(T[b][c], u) if b in T and c in T.get(b, {})
                                       else ([1., 1., 1.] if c == 'scale' else [0., 0., 0.])))
            h = rig.lowest(P, only=(side,)) - FLOOR
            pos = P[side][1]
            if h < 0.6 and prev is not None and prev[0] < 0.6:
                dx = pos[0] - prev[1][0]; dz = pos[2] - prev[1][2]
                lat += abs(dx)
                # l avant est en z NEGATIF : un pied posé doit reculer (dz > 0) ; s il
                # avance (dz < 0) il glisse. La premiere version comptait l inverse.
                if dz < -0.05:
                    recul += -dz
                irr.append(dz)
                dist += abs(dz); tps += dt
            prev = (h, pos)
    vit = dist / tps if tps else 0.0
    cv = (math.sqrt(sum((x - sum(irr) / len(irr)) ** 2 for x in irr) / len(irr)) / (abs(sum(irr) / len(irr)) or 1)
          if irr else 0.0)
    res_c.append((nm, lat, recul, cv, vit))
    print('   %-26s %8.1f %9.1f %9.2f %8.1f u/s %9.2f' % (nm, lat, recul, cv, vit, vit / 16.0))
json.dump(res_c, open('/tmp/patinage.json', 'w'))

# ------------------------------------------------------------------ D. debut / fin
print('\nD. ECART A LA POSE DE REPOS AU DEBUT ET A LA FIN (animations jouees une fois)')
R = pistes([x for x in bb['animations'] if court(x) == 'repos'][0])
def pose(T, u, b):
    return lp(T[b]['rotation'], u) if b in T and 'rotation' in T[b] else [0., 0., 0.]
OS = ('root', 'body', 'chest', 'neck', 'head', 'jaw', 'thigh_left', 'thigh_right', 'shin_left',
      'shin_right', 'tail_01', 'tail_03', 'upper_arm_left', 'upper_arm_right')
res_d = []
for a in bb['animations']:
    if a.get('loop') == 'loop':
        continue
    T, L = pistes(a), a['length']
    e0 = sum(math.dist(pose(T, 0, b), pose(R, 0, b)) for b in OS) / len(OS)
    e1 = sum(math.dist(pose(T, L, b), pose(R, 0, b)) for b in OS) / len(OS)
    res_d.append((round(max(e0, e1), 1), round(e0, 1), round(e1, 1), court(a), a.get('loop'),
                  a['name'] in NOMS_ORIG))
res_d.sort(reverse=True)
print('   %-30s %6s %6s  %s' % ('animation', 'debut', 'fin', 'mode'))
for x in res_d[:14]:
    print('   %-30s %6.1f %6.1f  %-5s %s' % (x[3], x[1], x[2], x[4], '(origine)' if x[5] else ''))
