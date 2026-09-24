"""Le bord interne de chaque palmure de main reste-t-il cache dans le doigt du milieu ?"""
import sys, json
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import compare_gif as C, fk as FK
from boite import coins

def boite_monde(e, P, nm):
    M, off, O = P[nm]
    R = FK.mat_rot(*e.get('rotation', [0, 0, 0])); eo = e['origin']
    Mt = FK.mul(M, R)
    c = [(e['from'][k] + e['to'][k]) / 2 for k in range(3)]
    h = [abs(e['to'][k] - e['from'][k]) / 2 + e.get('inflate', 0) for k in range(3)]
    q = FK.apply(R, [c[k] - eo[k] for k in range(3)]); q = [q[k] + eo[k] for k in range(3)]
    w = FK.apply(M, [q[k] - O[k] for k in range(3)])
    return Mt, [w[k] + off[k] for k in range(3)], h

def dehors(p, b):
    Mt, c, h = b
    d = [p[k] - c[k] for k in range(3)]
    l = [sum(Mt[k][j] * d[k] for k in range(3)) for j in range(3)]
    return max(0.0, max(abs(l[j]) - h[j] for j in range(3)))

def main(path, cote='left', n=24):
    bb, rig, *_ , A = C.prepare(path)
    E = {e['name']: e for e in bb['elements']}
    par = {}
    for u, cl in rig.cubes.items():
        for cu in cl: par[rig.elems[cu]['name']] = rig.groups[u]['name']
    pires = []
    for nom, a in A.items():
        T = C.pistes(a); L = a['length'] or 1
        for f in range(n + 1):
            u = L * f / n
            P = rig.pose(lambda b, c: (C.lp(T[b][c], u) if b in T and c in T[b] else ([1., 1., 1.] if c == 'scale' else [0., 0., 0.])))
            for i in (0, 2):
                w = E['V82_palmure_main_%s_%d' % (cote, i)]
                caches = [boite_monde(E[x], P, par[x]) for x in
                          ('V67_doigt_%s_1_0' % cote, 'V67_doigt_%s_1_1' % cote, 'V67_main_%s' % cote,
                           'V67_doigt_%s_%d_0' % (cote, i), 'V67_doigt_%s_%d_1' % (cote, i))]
                Mw, ow, hw = boite_monde(w, P, par[w['name']])
                # bord interne = la face laterale la plus proche du doigt du milieu
                c1 = boite_monde(E['V67_doigt_%s_1_0' % cote], P, par['V67_doigt_%s_1_0' % cote])[1]
                lat = [sum(Mw[k][0] * (c1[k] - ow[k]) for k in range(3))]
                sx = 1 if lat[0] > 0 else -1
                pire = 0
                for tz in [j / 10 for j in range(11)]:
                    for sy in (-1, 1):
                        l = [sx * hw[0], sy * hw[1], (2 * tz - 1) * hw[2]]
                        p = [ow[k] + sum(Mw[k][j] * l[j] for j in range(3)) for k in range(3)]
                        pire = max(pire, min(dehors(p, b) for b in caches))
                pires.append((pire, nom, round(u, 2), i))
    pires.sort(reverse=True)
    print('repos / pire depassement du bord interne (unites) :')
    for p in pires[:8]: print('   %.3f  %-34s t=%-5s doigt %d' % p)
    print('images avec depassement > 0.05 :', sum(1 for p in pires if p[0] > 0.05), '/', len(pires))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'left')
