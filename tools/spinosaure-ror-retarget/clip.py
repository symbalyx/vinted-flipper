"""Compte les images ou la MAIN ou les DOIGTS penetrent reellement le corps.

L'epaule et l'avant-bras sont volontairement exclus : l'epaule est encastree dans
le torse par construction (c'est anatomiquement correct), et un test qui l'inclut
signale 100 % des images, y compris sur le modele d'origine et en pose de repos.
Seules la main et les phalanges doivent rester a l'exterieur.
"""
import json, sys
sys.path.insert(0, 'tools')
import fk as FK

MAIN = ('hand_left', 'finger_left_0', 'finger_left_1', 'finger_left_2')
CORPS = ('body', 'thigh_left', 'chest')


def mulT(M, v):
    return [sum(M[r][k] * v[r] for r in range(3)) for k in range(3)]


def analyse(path, label, pas=3):
    bb = json.load(open(path))
    rig = FK.Rig(bb)

    def cubes_of(nm):
        return [rig.elems[c] for c in rig.cubes.get(rig.byname[nm], [])]

    A = [(e, b) for b in MAIN for e in cubes_of(b)]
    B = [(e, b) for b in CORPS for e in cubes_of(b)]

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

    def pts(e, bone, P):
        M, off, O = P[bone]
        R = FK.mat_rot(*e.get('rotation', [0, 0, 0]))
        eo = e.get('origin', O)
        f, t = e['from'], e['to']
        out = []
        for i in (0, 1):
            for j in (0, 1):
                for k in (0, 1):
                    p = [f[0] if i == 0 else t[0], f[1] if j == 0 else t[1],
                         f[2] if k == 0 else t[2]]
                    q = FK.apply(R, [p[x] - eo[x] for x in range(3)])
                    q = [q[x] + eo[x] for x in range(3)]
                    w = FK.apply(M, [q[x] - O[x] for x in range(3)])
                    out.append([w[x] + off[x] for x in range(3)])
        return out

    def dans(e, bone, P, w, m=0.6):
        M, off, O = P[bone]
        R = FK.mat_rot(*e.get('rotation', [0, 0, 0]))
        eo = e.get('origin', O)
        q = mulT(M, [w[x] - off[x] for x in range(3)])
        q = [q[x] + O[x] for x in range(3)]
        q = mulT(R, [q[x] - eo[x] for x in range(3)])
        q = [q[x] + eo[x] for x in range(3)]
        f, t = e['from'], e['to']
        return all(min(f[x], t[x]) + m < q[x] < max(f[x], t[x]) - m for x in range(3))

    tot = img = 0
    coupables = {}
    for a in bb['animations']:
        t = tracks(a)
        L = a['length']
        n = 0
        for i in range(0, int(L * 30) + 1, pas):
            u = min(i / 30., L)
            img += 1
            P = rig.pose(lambda b, c, u=u: lp(t[b][c], u) if b in t and c in t[b]
                         else ([1., 1., 1.] if c == 'scale' else [0., 0., 0.]))
            touche = False
            for ea, ba in A:
                if any(dans(ec, bc, P, w) for w in pts(ea, ba, P) for ec, bc in B):
                    touche = True
                    break
            if touche:
                n += 1
        tot += n
        if n:
            coupables[a['name'][20:]] = n
    print('%-32s %5d / %5d images  (%.1f%%)' % (label, tot, img, 100 * tot / max(1, img)))
    for nm, n in sorted(coupables.items(), key=lambda kv: -kv[1])[:4]:
        print('      %-40s %d' % (nm, n))
    return tot, img


if __name__ == '__main__':
    analyse(sys.argv[1], sys.argv[2])
