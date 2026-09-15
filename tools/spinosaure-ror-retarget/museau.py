"""Hauteur de la pointe du museau au fil d une animation : le seul chiffre qui dit
si l animal flaire le SOL ou l AIR. Au repos elle vaut 104."""
import json, sys
sys.path.insert(0, 'tools')
import fk as FK

bb = json.load(open(sys.argv[1]))
rig = FK.Rig(bb)
FLOOR = rig.lowest(rig.pose(lambda b, c: [1., 1., 1.] if c == 'scale' else [0., 0., 0.]))
A = {a['name'].split('.')[-1]: a for a in bb['animations']}
TETE = [t for t in ('head', 'jaw', 'tongue') if t in rig.byname]


def tracks(a):
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


print('sol %.1f, museau au repos %.1f' % (FLOOR, min(
    rig.lowest(rig.pose(lambda b, c: [1., 1., 1.] if c == 'scale' else [0., 0., 0.]), only=(t,))
    for t in TETE) - FLOOR))
print('%-22s %7s %8s %8s %8s' % ('animation', 'duree', 'museau', 'museau', 'le+bas'))
print('%-22s %7s %8s %8s %8s' % ('', 's', 'mini', 'maxi', 'du modele'))
for nm in sys.argv[2:]:
    a = A[nm]
    T, L = tracks(a), a['length']
    mu, bas = [], []
    for i in range(int(L * 30) + 1):
        u = min(i / 30., L)
        P = rig.pose(lambda b, c: (lp(T[b][c], u) if b in T and c in T.get(b, {})
                                   else ([1., 1., 1.] if c == 'scale' else [0., 0., 0.])))
        mu.append(min(rig.lowest(P, only=(t,)) for t in TETE) - FLOOR)
        bas.append(rig.lowest(P) - FLOOR)
    print('%-22s %7.2f %8.1f %8.1f %8.1f' % (nm, L, min(mu), max(mu), min(bas)))
