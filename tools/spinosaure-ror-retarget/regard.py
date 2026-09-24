"""Tenue du regard : derive d orientation de la tete dans le monde sur une fenetre."""
import json, sys, math
sys.path.insert(0, 'tools')
import fk as FK

bb = json.load(open(sys.argv[1]))
rig = FK.Rig(bb)
A = {a['name'].split('.')[-1]: a for a in bb['animations']}


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


def angle(M1, M2):
    tr = sum(M1[r][k] * M2[r][k] for r in range(3) for k in range(3))
    return math.degrees(math.acos(max(-1, min(1, (tr - 1) / 2))))


for arg in sys.argv[2:]:
    nm, a0, a1 = arg.split(':')
    a = A[nm]; t = pistes(a)
    Ms = []
    for i in range(int(float(a0) * 30), int(float(a1) * 30) + 1):
        u = i / 30.
        P = rig.pose(lambda b, c: (lp(t[b][c], u) if b in t and c in t.get(b, {})
                                   else ([1., 1., 1.] if c == 'scale' else [0., 0., 0.])))
        Ms.append(P['head'][0])
    print('%-32s fenetre %s-%s s : derive max de la tete %5.2f deg' % (nm, a0, a1, max(angle(Ms[0], M) for M in Ms)))
