"""Detection du z-fighting : faces coplanaires, de meme orientation, qui se recouvrent.

Deux faces dans le meme plan et tournees du meme cote se disputent chaque pixel au
tampon de profondeur : en jeu elles scintillent. Les faces coplanaires OPPOSEES (deux
cubes qui se touchent) sont internes et invisibles, elles ne comptent pas.
"""
import math, collections, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fk as FK
from boite import coins, FACES


def faces_monde(bb, rig=None):
    rig = rig or FK.Rig(bb)
    P = rig.pose(lambda b, c: [1., 1., 1.] if c == 'scale' else [0., 0., 0.])
    out = []
    for u, cl in rig.cubes.items():
        nm = rig.groups[u]['name']
        if nm not in P:
            continue
        M, off, O = P[nm]
        for cu in cl:
            e = rig.elems[cu]
            R = FK.mat_rot(*e.get('rotation', [0, 0, 0]))
            eo = e.get('origin', O)
            g = e.get('inflate', 0) or 0
            f = [e['from'][k] - g for k in range(3)]
            t = [e['to'][k] + g for k in range(3)]
            W = []
            for p in coins(f, t):
                q = FK.apply(R, [p[x] - eo[x] for x in range(3)])
                q = [q[x] + eo[x] for x in range(3)]
                w = FK.apply(M, [q[x] - O[x] for x in range(3)])
                W.append([w[x] + off[x] for x in range(3)])
            for fn, (idx, nl, _) in FACES.items():
                fd = e.get('faces', {}).get(fn)
                if not fd or fd.get('texture') is None:
                    continue
                n = FK.apply(M, FK.apply(R, list(nl)))
                ln = math.sqrt(sum(x * x for x in n))
                out.append((e, fn, [x / ln for x in n], [W[i] for i in idx], nm))
    return out


def _aire_signee(pts):
    return sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts))) / 2


def _decoupe(sujet, clip):
    def dedans(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= -1e-9

    def inter(p, q, a, b):
        x1, y1 = p; x2, y2 = q; x3, y3 = a; x4, y4 = b
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-12:
            return q
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    out = sujet
    for i in range(len(clip)):
        a, b = clip[i], clip[(i + 1) % len(clip)]
        inp, out = out, []
        if not inp:
            break
        for j in range(len(inp)):
            p, q = inp[j], inp[(j + 1) % len(inp)]
            if dedans(q, a, b):
                if not dedans(p, a, b):
                    out.append(inter(p, q, a, b))
                out.append(q)
            elif dedans(p, a, b):
                out.append(inter(p, q, a, b))
    return out


def _base(n):
    a = [1, 0, 0] if abs(n[0]) < 0.9 else [0, 1, 0]
    u = [n[1] * a[2] - n[2] * a[1], n[2] * a[0] - n[0] * a[2], n[0] * a[1] - n[1] * a[0]]
    lu = math.sqrt(sum(x * x for x in u)); u = [x / lu for x in u]
    v = [n[1] * u[2] - n[2] * u[1], n[2] * u[0] - n[0] * u[2], n[0] * u[1] - n[1] * u[0]]
    return u, v


def paires(bb, tol=0.02, aire_min=0.05):
    F = faces_monde(bb)
    seau = collections.defaultdict(list)
    for i, (e, fn, n, pts, bone) in enumerate(F):
        d = sum(n[k] * pts[0][k] for k in range(3))
        seau[(round(n[0], 2), round(n[1], 2), round(n[2], 2), round(d, 1))].append((i, d))
    res = []
    for lst in seau.values():
        for a in range(len(lst)):
            for b in range(a + 1, len(lst)):
                i, d1 = lst[a]; j, d2 = lst[b]
                if abs(d1 - d2) > tol or F[i][0] is F[j][0]:
                    continue
                u, v = _base(F[i][2])
                A = [(sum(p[k] * u[k] for k in range(3)), sum(p[k] * v[k] for k in range(3))) for p in F[i][3]]
                B = [(sum(p[k] * u[k] for k in range(3)), sum(p[k] * v[k] for k in range(3))) for p in F[j][3]]
                if _aire_signee(A) < 0: A = A[::-1]
                if _aire_signee(B) < 0: B = B[::-1]
                I = _decoupe(A, B)
                if len(I) >= 3:
                    ar = abs(_aire_signee(I))
                    if ar > aire_min:
                        res.append((ar, F[i][0], F[i][1], F[j][0], F[j][1], F[i][4] == F[j][4]))
    res.sort(key=lambda r: -r[0])
    return res
