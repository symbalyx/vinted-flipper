"""Controle des raccords de boucle : VALEUR et VITESSE.

L ancien controle verifiait seulement que la derniere cle egale la premiere, ce que
la cuisson garantissait de force : un saut de 57 degres concentre sur la derniere
demi-image passait donc pour une boucle parfaite. Ici on mesure :
  - le saut du DERNIER intervalle, compare au plus grand pas du reste de la piste ;
  - la rupture de vitesse entre la fin et le debut.
"""
import json, sys

bb = json.load(open(sys.argv[1]))
seuil_r, seuil_p = 2.5, 1.0


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


pb, n_boucles = [], 0
for a in bb['animations']:
    if a.get('loop') != 'loop':
        continue
    n_boucles += 1
    L = a['length']; dt = 1 / 30.
    for an in a['animators'].values():
        par = {}
        for k in an['keyframes']:
            par.setdefault(k['channel'], []).append(
                (k['time'], [float(k['data_points'][0].get(q, 0) or 0) for q in 'xyz']))
        for ch, p in par.items():
            if ch == 'scale' or len(p) < 3:
                continue
            p.sort()
            ts = [i * dt for i in range(int(L / dt) + 1) if i * dt < L - 1e-6] + [L]
            v = [lp(p, t) for t in ts]
            pas = lambda i: max(abs(v[i + 1][k] - v[i][k]) for k in range(3))
            final = pas(len(v) - 2)
            reste = max(pas(i) for i in range(len(v) - 2)) if len(v) > 3 else 0
            # vitesse par seconde, pour ne pas etre trompe par un dernier intervalle court
            h_fin = ts[-1] - ts[-2]
            vf = [(v[-1][k] - v[-2][k]) / h_fin for k in range(3)]
            vd = [(v[1][k] - v[0][k]) / (ts[1] - ts[0]) for k in range(3)]
            rupt = max(abs(vf[k] - vd[k]) for k in range(3)) * dt
            s = seuil_r if ch == 'rotation' else seuil_p
            if (final > s and final > 2 * reste) or (rupt > 2 * s and rupt > 2 * reste):
                pb.append((round(max(final, rupt), 1), a['name'].split('.')[-1], an['name'], ch,
                           round(final, 1), round(rupt, 1), round(reste, 1)))
pb.sort(reverse=True)
print('%d boucles controlees, %d pistes avec un raccord casse' % (n_boucles, len(pb)))
for x in pb[:25]:
    print('   %-26s %-16s %-8s saut final %5.1f  rupture vitesse %5.1f  (pas max ailleurs %4.1f)' % x[1:])
sys.exit(1 if pb else 0)
