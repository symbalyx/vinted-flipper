"""Detecte les animations qui font la meme chose, par mesure et non par nom.

Chaque animation est reduite a une signature : la pose de 12 os cles echantillonnee
a 16 instants sur sa duree normalisee. Deux animations sont dites equivalentes si
l'ecart moyen de pose reste sous un seuil en degres. Les boucles sont comparees a
toutes leurs phases, une course decalee d'une demi-foulee restant la meme course.
"""
import json, sys, math

OS = ('root', 'body', 'chest', 'neck', 'head', 'jaw', 'thigh_left', 'shin_left',
      'foot_left', 'tail_01', 'tail_03', 'tail_05')
N = 16


def tracks(a):
    t = {}
    for uid, an in a['animators'].items():
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


def signature(a):
    T = tracks(a)
    L = a['length']
    sig = []
    for i in range(N):
        u = L * i / N
        for b in OS:
            d = T.get(b, {})
            r = lp(d['rotation'], u) if 'rotation' in d else [0, 0, 0]
            p = lp(d['position'], u) if 'position' in d else [0, 0, 0]
            sig += r + list(p)   # 1 unite de translation pese comme 1 degre
    return sig, a.get('loop') == 'loop'


def ecart(s1, s2, boucle):
    n = len(OS) * 6
    best = 1e9
    phases = range(N) if boucle else (0,)
    for d in phases:
        tot = 0.0
        for i in range(N):
            j = (i + d) % N
            for k in range(n):
                tot += abs(s1[i * n + k] - s2[j * n + k])
        best = min(best, tot / (N * n))
    return best


if __name__ == '__main__':
    bb = json.load(open(sys.argv[1]))
    seuil = float(sys.argv[2]) if len(sys.argv) > 2 else 2.5
    sigs = {}
    for a in bb['animations']:
        sigs[a['name']] = signature(a)
    noms = list(sigs)
    paires = []
    for i in range(len(noms)):
        for j in range(i + 1, len(noms)):
            s1, b1 = sigs[noms[i]]
            s2, b2 = sigs[noms[j]]
            if b1 != b2:
                continue
            e = ecart(s1, s2, b1)
            if e < seuil:
                paires.append((e, noms[i], noms[j]))
    paires.sort()
    print('Paires sous %.2f d ecart moyen de pose (deg ou unites) :' % seuil)
    for e, a, b in paires:
        marque = ''
        if a.endswith('_ror') != b.endswith('_ror'):
            marque = '   <- une portee ROR double une maison'
        print('  %5.2f  %-34s %-34s%s' % (e, a[20:], b[20:], marque))
    if not paires:
        print('  aucune')
