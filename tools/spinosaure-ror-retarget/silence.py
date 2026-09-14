"""Mesure ce qui rend un pas silencieux : la vitesse verticale du pied au poser.

Un pas qui claque, c est un pied qui arrive vite. On mesure donc, pour chaque
animation de deplacement, la vitesse de descente du pied a l instant ou il passe
sous 1 unite du sol, plus la hauteur de degagement et l amplitude du dandinement.
"""
import json, sys
sys.path.insert(0, 'tools')
import fk as FK

bb = json.load(open(sys.argv[1]))
rig = FK.Rig(bb)
FLOOR = rig.lowest(rig.pose(lambda b, c: [1., 1., 1.] if c == 'scale' else [0., 0., 0.]))
A = {a['name'].split('.')[-1]: a for a in bb['animations']}


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


print('%-26s %7s %9s %9s %9s' % ('animation', 'duree', 'impact', 'degagement', 'hanche'))
print('%-26s %7s %9s %9s %9s' % ('', 's', 'u/s', 'u', 'u'))
for nm in sys.argv[2:]:
    a = A[nm]
    T, L = tracks(a), a['length']
    N = int(L * 60)
    h = {'foot_left': [], 'foot_right': []}
    hip = []
    for i in range(N):
        u = L * i / N
        P = rig.pose(lambda b, c: (lp(T[b][c], u) if b in T and c in T.get(b, {})
                                   else ([1., 1., 1.] if c == 'scale' else [0., 0., 0.])))
        hip.append(P['body'][1][1])
        for s in h:
            uu = rig.byname[s]
            M, off, O = P[s]
            h[s].append(min(sum(M[1][k] * (p[k] - O[k]) for k in range(3)) + off[1]
                            for p in rig.box[uu]) - FLOOR)
    # vitesse D IMPACT : on cherche l ARRIVEE dans la phase d appui (premiere image ou
    # le pied redescend dans la bande basse) et on mesure sa vitesse verticale sur la
    # trentieme de seconde qui precede. Mesurer au minimum global donnerait zero pour
    # tout le monde, l appui etant plat ; mesurer a un seuil fixe donnerait la vitesse
    # en plein vol. C est bien l arrivee qui fait le bruit.
    vit = []
    for s in h:
        v = h[s]
        bande = min(v) + 0.3
        k = max(1, int(round(N / L / 30)))
        for i in range(N):
            if v[i] <= bande < v[i - 1]:
                vit.append((v[i] - v[(i - k) % N]) / (k * L / N))
    print('%-26s %7.2f %9s %9.1f %9.1f' % (
        nm, L, ('%.1f' % min(vit)) if vit else 'plat',
        max(max(h['foot_left']), max(h['foot_right'])), sum(hip) / len(hip)))
