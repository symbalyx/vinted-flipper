"""Verification FK du bbmodel : hauteur des pieds/corps, amplitudes, ecart tete-torse."""
import json, math, sys

bb = json.load(open(sys.argv[1]))
groups = {g['uuid']: g for g in bb['groups']}
elems = {e['uuid']: e for e in bb['elements']}
parent, children, byname, cubes_of = {}, {}, {}, {}


def walk(node, par=None):
    if isinstance(node, str):
        cubes_of.setdefault(par, []).append(node)
        return
    u = node['uuid']
    parent[u] = par
    byname[groups[u]['name']] = u
    children.setdefault(par, []).append(u)
    for c in node.get('children', []):
        walk(c, u)


walk(bb['outliner'][0])
ROOT = bb['outliner'][0]['uuid']


def mul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def apply(M, v):
    return [sum(M[i][k] * v[k] for k in range(3)) for i in range(3)]


def mat_rot(rx, ry, rz):
    cx, sx = math.cos(math.radians(rx)), math.sin(math.radians(rx))
    cy, sy = math.cos(math.radians(ry)), math.sin(math.radians(ry))
    cz, sz = math.cos(math.radians(rz)), math.sin(math.radians(rz))
    return mul(mul([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]], [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]),
               [[1, 0, 0], [0, cx, -sx], [0, sx, cx]])


def prep(anim):
    tr = {}
    for uid, a in anim['animators'].items():
        d = {}
        for k in a['keyframes']:
            d.setdefault(k['channel'], []).append(
                (k['time'], [float(k['data_points'][0].get(q, 0) or 0) for q in 'xyz']))
        for c in d:
            d[c].sort()
        tr[uid] = d
    return tr


def samp(d, chan, t, neutral):
    pts = d.get(chan)
    if not pts:
        return neutral
    if t <= pts[0][0]:
        return pts[0][1]
    if t >= pts[-1][0]:
        return pts[-1][1]
    lo, hi = 0, len(pts) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if pts[mid][0] <= t:
            lo = mid
        else:
            hi = mid
    a, b = pts[lo], pts[hi]
    f = (t - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0.0
    return [a[1][k] + (b[1][k] - a[1][k]) * f for k in range(3)]


I3 = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def pose(tr, t):
    out = {}
    stack = [(ROOT, I3, [0.0, 0.0, 0.0], groups[ROOT]['origin'])]
    while stack:
        u, pM, pOff, pO = stack.pop()
        g = groups[u]
        O = g['origin']
        rest = g.get('rotation', [0, 0, 0])
        d = tr.get(u, {})
        ar = samp(d, 'rotation', t, [0, 0, 0])
        ap = samp(d, 'position', t, [0, 0, 0])
        sc = samp(d, 'scale', t, [1, 1, 1])
        Rl = mat_rot(rest[0] + ar[0], rest[1] + ar[1], rest[2] + ar[2])
        Rl = [[Rl[i][j] * sc[j] for j in range(3)] for i in range(3)]
        M = mul(pM, Rl)
        lo = [O[k] - pO[k] + ap[k] for k in range(3)]
        w = apply(pM, lo)
        off = [pOff[k] + w[k] for k in range(3)]
        out[u] = (M, off, O)
        for c in children.get(u, []):
            stack.append((c, M, off, O))
    return out


CHECK = ['foot_left', 'foot_right', 'head', 'jaw', 'tail_06', 'hand_left', 'sail', 'throat']
PTS = {}
for nm in CHECK:
    u = byname[nm]
    ps = []
    for cu in cubes_of.get(u, []):
        e = elems[cu]
        f, to = e['from'], e['to']
        for i in (0, 1):
            for j in (0, 1):
                for k in (0, 1):
                    ps.append([f[0] if i == 0 else to[0],
                               f[1] if j == 0 else to[1],
                               f[2] if k == 0 else to[2]])
    PTS[nm] = (u, ps[:24])


def wp(nm, P):
    u, ps = PTS[nm]
    M, off, O = P[u]
    return [[apply(M, [p[x] - O[x] for x in range(3)])[k] + off[k] for k in range(3)] for p in ps]


T = sys.argv[2:]
print('%-40s %8s %8s %8s %8s %9s %8s' % ('animation', 'pied_lo', 'pied_hi', 'corps_lo',
                                          'tete_hi', 'd_tete_tx', 'maxrot'))
for anim in bb['animations']:
    nm = anim['name'].replace('animation.spinosaure.', '')
    if T and not any(x in nm for x in T):
        continue
    tr = prep(anim)
    L = anim['length']
    n = max(2, min(60, int(L * 12)))
    mx = max((abs(float(k['data_points'][0].get(q, 0) or 0))
              for a in anim['animators'].values() for k in a['keyframes']
              if k['channel'] == 'rotation' for q in 'xyz'), default=0.0)
    flo, fhi, blo, hy, dmin = 1e9, -1e9, 1e9, -1e9, 1e9
    for i in range(n + 1):
        t = L * i / n
        P = pose(tr, t)
        fp = wp('foot_left', P) + wp('foot_right', P)
        flo = min(flo, min(p[1] for p in fp))
        fhi = max(fhi, max(p[1] for p in fp))
        allp = fp + wp('head', P) + wp('jaw', P) + wp('tail_06', P) + wp('hand_left', P) + wp('sail', P)
        blo = min(blo, min(p[1] for p in allp))
        hp = wp('head', P)
        hy = max(hy, max(p[1] for p in hp))
        hc = [sum(p[k] for p in hp) / len(hp) for k in range(3)]
        M, off, O = P[byname['chest']]
        dmin = min(dmin, math.dist(hc, off))
    print('%-40s %8.1f %8.1f %8.1f %8.1f %9.1f %8.1f' % (nm, flo, fhi, blo, hy, dmin, mx))
