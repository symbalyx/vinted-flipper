"""Recuit des animations : supprime les cles colineaires, puis MESURE l'ecart visuel reel.

Les pistes sont 100% lineaires : l'ecart maximal entre la courbe d'origine et la
courbe recuite se produit exactement aux temps des cles supprimees. On evalue donc
la cinematique directe a l'union des temps de cles d'origine, ce qui donne l'erreur
exacte en espace monde (et non une estimation).
"""
import json, sys, math
sys.path.insert(0, 'tools')
import fk as FK


def compress(track, tol):
    """Douglas-Peucker sur une piste (t, [x,y,z]) ; conserve toujours les extremites."""
    if len(track) <= 2:
        return list(range(len(track)))
    keep = {0, len(track) - 1}
    stack = [(0, len(track) - 1)]
    while stack:
        i0, i1 = stack.pop()
        if i1 - i0 < 2:
            continue
        t0, v0 = track[i0]
        t1, v1 = track[i1]
        worst, wi = -1.0, -1
        for i in range(i0 + 1, i1):
            t, v = track[i]
            d = 0.0 if t1 - t0 < 1e-12 else (t - t0) / (t1 - t0)
            for k in range(3):
                e = abs(v[k] - (v0[k] + (v1[k] - v0[k]) * d))
                if e > worst:
                    worst, wi = e, i
        if worst > tol and wi > 0:
            keep.add(wi)
            stack.append((i0, wi))
            stack.append((wi, i1))
    return sorted(keep)


def levers(rig):
    """Bras de levier de chaque os : distance max du pivot a sa geometrie descendante.

    Une erreur de theta degres sur cet os deplace sa geometrie d au plus
    L * theta * pi/180 unites. On en deduit une tolerance par os au lieu d une
    tolerance uniforme : les petits os (doigts, machoire) tolerent bien plus
    d angle pour le meme ecart visuel que le root.
    """
    rest = rig.pose(lambda b, c: [1.0, 1.0, 1.0] if c == 'scale' else [0.0, 0.0, 0.0])
    pts = {}
    for u, corners in rig.box.items():
        nm = rig.groups[u]['name']
        M, off, O = rest[nm]
        pts[nm] = [[sum(M[r][c] * (p[c] - O[c]) for c in range(3)) + off[r] for r in range(3)]
                   for p in corners]
    kids = {}
    for par, cl in rig.children.items():
        if par is None:
            continue
        kids[rig.groups[par]['name']] = [rig.groups[c]['name'] for c in cl]

    def descend(nm, acc):
        acc.extend(pts.get(nm, []))
        for c in kids.get(nm, []):
            descend(c, acc)
        return acc

    out, depth = {}, {}
    for u in rig.groups:
        nm = rig.groups[u]['name']
        M, off, O = rest[nm]
        piv = off
        far = descend(nm, [])
        out[nm] = max((math.dist(piv, q) for q in far), default=1.0) or 1.0

    def deep(nm, d=1):
        depth[nm] = d
        for c in kids.get(nm, []):
            deep(c, d + 1)
    deep(rig.groups[rig.root]['name'])
    return out, max(depth.values())


def tol_per_bone(rig, target):
    """Tolerances par os garantissant un ecart cumule <= target sur toute la chaine."""
    L, D = levers(rig)
    budget = target / D
    out = {}
    for nm, l in L.items():
        out[nm] = {
            'rotation': min(3.0, max(0.004, math.degrees(budget / l))),
            'position': max(0.002, budget),
            'scale': min(0.05, max(0.0005, budget / l)),
        }
    return out


def channels(animator):
    per = {}
    for idx, kf in enumerate(animator['keyframes']):
        per.setdefault(kf['channel'], []).append(idx)
    for c in per:
        per[c].sort(key=lambda i: animator['keyframes'][i]['time'])
    return per


def recook_anim(anim, tol, perbone=None):
    """Retourne un nouvel objet animation, en ne conservant que des cles d'origine."""
    out = {k: v for k, v in anim.items() if k != 'animators'}
    out['animators'] = {}
    dropped = kept = 0
    for uid, an in anim['animators'].items():
        btol = perbone.get(an['name'], tol) if perbone else tol
        new_kfs = []
        for chan, idxs in channels(an).items():
            track = [(an['keyframes'][i]['time'],
                      [float(an['keyframes'][i]['data_points'][0].get(q, 0) or 0) for q in 'xyz'])
                     for i in idxs]
            sel = compress(track, btol[chan])
            for s in sel:
                new_kfs.append(an['keyframes'][idxs[s]])
            kept += len(sel)
            dropped += len(idxs) - len(sel)
        new_kfs.sort(key=lambda k: (k['time'], k['channel']))
        out['animators'][uid] = {k: v for k, v in an.items() if k != 'keyframes'}
        out['animators'][uid]['keyframes'] = new_kfs
    return out, kept, dropped


# ------------------------------------------------------------- mesure de l'ecart

def tracks_of(anim):
    t = {}
    for uid, an in anim['animators'].items():
        d = {}
        for kf in an['keyframes']:
            d.setdefault(kf['channel'], []).append(
                (kf['time'], [float(kf['data_points'][0].get(q, 0) or 0) for q in 'xyz']))
        for c in d:
            d[c].sort()
        t[an['name']] = d
    return t


def lerp(pts, t):
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


def getter(T):
    def g(bone, chan):
        d = T.get(bone)
        if d and chan in d:
            return lerp(d[chan], g.t)
        return [1.0, 1.0, 1.0] if chan == 'scale' else [0.0, 0.0, 0.0]
    return g


def max_world_error(rig, a_old, a_new):
    """Ecart maximal, en unites du modele, sur les coins de boite de chaque os."""
    To, Tn = tracks_of(a_old), tracks_of(a_new)
    times = sorted({kf['time'] for an in a_old['animators'].values() for kf in an['keyframes']})
    go, gn = getter(To), getter(Tn)
    worst = 0.0
    for t in times:
        go.t = gn.t = t
        Po, Pn = rig.pose(go), rig.pose(gn)
        for u, corners in rig.box.items():
            nm = rig.groups[u]['name']
            if nm not in Po or nm not in Pn:
                continue
            Mo, oo, O = Po[nm]
            Mn, on, _ = Pn[nm]
            for p in corners:
                q = [p[0] - O[0], p[1] - O[1], p[2] - O[2]]
                d2 = 0.0
                for r in range(3):
                    a = sum(Mo[r][c] * q[c] for c in range(3)) + oo[r]
                    b = sum(Mn[r][c] * q[c] for c in range(3)) + on[r]
                    d2 += (a - b) ** 2
                if d2 > worst:
                    worst = d2
    return math.sqrt(worst)


if __name__ == '__main__':
    src = sys.argv[1]
    bb = json.load(open(src))
    rig = FK.Rig(bb)
    mode = sys.argv[2] if len(sys.argv) > 2 else 'scan'
    PRESETS = {
        'A': {'rotation': 0.02, 'position': 0.005, 'scale': 0.001},
        'B': {'rotation': 0.06, 'position': 0.015, 'scale': 0.003},
        'C': {'rotation': 0.15, 'position': 0.040, 'scale': 0.008},
        'D': {'rotation': 0.30, 'position': 0.080, 'scale': 0.015},
        'E': 'adaptatif 0.05u', 'F': 'adaptatif 0.15u', 'G': 'adaptatif 0.40u',
    }
    ONLY = set(sys.argv[3]) if len(sys.argv) > 3 else None
    base = len(json.dumps(bb['animations'])) / 1e6
    if mode == 'scan':
        print('modele : %d animations, %.1f Mo de JSON d animation' % (len(bb['animations']), base))
        print('%-7s %10s %10s %9s %14s' % ('preset', 'cles', 'Mo', 'gain', 'ecart max (u)'))
        ADAPT = {'E': 0.05, 'F': 0.15, 'G': 0.40}
        for name, tol in PRESETS.items():
            if ONLY and name not in ONLY:
                continue
            pb = tol_per_bone(rig, ADAPT[name]) if name in ADAPT else None
            if pb:
                tol = {'rotation': 0.02, 'position': 0.005, 'scale': 0.001}
            news, kept, dropped, err = [], 0, 0, 0.0
            for a in bb['animations']:
                na, k, d = recook_anim(a, tol, pb)
                news.append(na)
                kept += k
                dropped += d
                err = max(err, max_world_error(rig, a, na))
            mb = len(json.dumps(news)) / 1e6
            print('%-7s %10d %10.1f %8.0f%% %14.4f' % (name, kept, mb, 100 * (1 - mb / base), err))
    else:
        ADAPT = {'E': 0.05, 'F': 0.15, 'G': 0.40}
        pb = tol_per_bone(rig, ADAPT[mode]) if mode in ADAPT else None
        tol = PRESETS[mode] if mode not in ADAPT else {'rotation': 0.02, 'position': 0.005, 'scale': 0.001}
        news, kept, err, worst_anim = [], 0, 0.0, None
        for a in bb['animations']:
            na, k, d = recook_anim(a, tol, pb)
            e = max_world_error(rig, a, na)
            if e > err:
                err, worst_anim = e, a['name']
            news.append(na)
            kept += k
        bb['animations'] = news
        out = sys.argv[3]
        json.dump(bb, open(out, 'w'), separators=(',', ':'))
        print('preset %s : %d cles conservees, ecart max %.4f u (pire : %s)' % (mode, kept, err, worst_anim))
        print('ecrit', out)
