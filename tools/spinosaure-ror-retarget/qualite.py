"""Audit de qualite sur TOUTES les animations du livrable.

Ne verifie pas ce qui est joli (impossible sans ouvrir Blockbench) mais ce qui est
mesurable et qui casse en jeu : penetration du sol, boucles non refermees, vitesses
angulaires au-dela de ce que 30 images par seconde peuvent rendre, valeurs hors
domaine, cles malformees.
"""
import json, sys, math
sys.path.insert(0, 'tools')
import fk as FK

bb = json.load(open(sys.argv[1]))
rig = FK.Rig(bb)
FLOOR = rig.lowest(rig.pose(lambda b, c: [1., 1., 1.] if c == 'scale' else [0., 0., 0.]))
# animations qui se deroulent dans l eau : le sol ne s applique pas
AQUA = ('affut_eau', 'traque_eau_affleurante', 'nage_', 'plonge', 'plongeon', 'remonte_',
        'emergence_lente', 'entree_eau', 'capture_joueur_sous_eau', 'transport_joueur_sous_eau',
        'saut_attaque_hors_eau', 'bond_hors_eau_ror', 'attaque_saut_eau_ror', 'dash_morsure_bateau',
        'rugit_en_nageant_ror', 'frappe_queue_eau', 'sortie_eau_terre_redressement',
        'creuse_enfouissement', 'creuse_et_ressort_quatre_pattes', 'sort_terre_quatre_pattes',
        'mort', 'grimpe', 'plongeon_hauteur', 'bond_joueur', 'degats_eau', 'mort_eau')
# animations dont la secousse rapide est VOULUE
SECOUSSE = ('secoue_eau', 'secoue_proie', 'spasmes_cou', 'tete_inclinee_fixe',
            'hurle_intimidation_ondes', 'creuse_enfouissement')


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


pb = []
for a in sorted(bb['animations'], key=lambda x: x['name']):
    nm = a['name'].split('.')[-1]
    T, L = tracks(a), a['length']
    aqua = any(nm.startswith(x) or x in nm for x in AQUA)
    sec = nm in SECOUSSE

    # --- 1. cles malformees, valeurs non finies, echelles absurdes
    for b, d in T.items():
        for c, p in d.items():
            ts = [x[0] for x in p]
            if ts != sorted(ts):
                pb.append((nm, 'cles non triees sur %s/%s' % (b, c)))
            if ts[0] < -1e-6 or ts[-1] > L + 1e-6:
                pb.append((nm, 'cle hors de la duree sur %s/%s (%.3f..%.3f > %.3f)' % (b, c, ts[0], ts[-1], L)))
            for _, v in p:
                if any(not math.isfinite(x) for x in v):
                    pb.append((nm, 'valeur non finie sur %s/%s' % (b, c)))
                    break
            if c == 'scale' and b != 'paupiere_sommeil' and any(x < 0.4 or x > 2.5 for _, v in p for x in v):
                pb.append((nm, 'echelle hors domaine sur %s' % b))

    # --- 2. boucle non refermee
    if a.get('loop') == 'loop':
        for b, d in T.items():
            for c, p in d.items():
                e = math.dist(lp(p, 0.0), lp(p, L))
                if e > 0.5:
                    pb.append((nm, 'boucle non refermee sur %s/%s (ecart %.2f)' % (b, c, e)))

    # --- 3. vitesse angulaire : au-dela de ~25 deg/image le mouvement saute
    vmax, ou = 0.0, ''
    for b, d in T.items():
        p = d.get('rotation')
        if not p:
            continue
        prev = lp(p, 0.0)
        for i in range(1, int(L * 30) + 1):
            cur = lp(p, min(i / 30., L))
            v = math.dist(prev, cur)
            if v > vmax:
                vmax, ou = v, b
            prev = cur
    if vmax > 25.0 and not sec:
        pb.append((nm, 'saut de %.0f deg en une image sur %s' % (vmax, ou)))

    # --- 4. penetration du sol
    if not aqua:
        pen = 0.0
        for i in range(0, int(L * 30) + 1, 2):
            u = min(i / 30., L)
            P = rig.pose(lambda b, c: (lp(T[b][c], u) if b in T and c in T.get(b, {})
                                       else ([1., 1., 1.] if c == 'scale' else [0., 0., 0.])))
            pen = max(pen, FLOOR - rig.lowest(P))
        if pen > 2.0:
            pb.append((nm, 'traverse le sol de %.1f unites' % pen))

print('%d animations auditees, sol a %.1f' % (len(bb['animations']), FLOOR))
if pb:
    print('\n%d anomalie(s) :' % len(pb))
    for nm, m in pb:
        print('  %-34s %s' % (nm, m))
else:
    print('\naucune anomalie')
