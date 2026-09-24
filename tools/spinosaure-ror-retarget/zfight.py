"""Supprime le z-fighting sans rien changer de visible.

Deux faces dans le meme plan et tournees du meme cote clignotent en jeu. On gonfle
(champ `inflate` de Blockbench, gere par Bedrock et GeckoLib) le cube le plus PETIT
de chaque paire : c est en general le detail pose sur la piece de base (bord de voile
sur la voile, menton sous la machoire), qui passe alors devant de facon stable.

Deux essais rates avant celui-ci, gardes en memoire ici :
  - un pas fixe de 0.03 repete : le plancher de la gueule a marche, passe apres passe,
    pile sur la face de la mandibule situee 0.12 plus bas (4 x 0.03) ;
  - un pas irregulier par passe : quand trois pieces se partagent un plan (mandibule,
    plancher, menton), gonfler "le plus petit de chaque paire" gonfle plancher ET
    menton du meme montant, qui restent donc coplanaires entre eux.
  - un rang global par groupe : les groupes sont grands (la voile et ses bords forment
    une chaine), le gonflement montait a 0.19 et ramenait le plancher sur la mandibule.
Solution : un NIVEAU par piece, egal a la longueur du plus long chemin qui descend
vers elle depuis une piece plus grosse avec laquelle elle se dispute un plan. Les
chaines sont courtes (2 ou 3), le gonflement reste petit. Puis, si un gonflement
cree une coincidence avec une piece etrangere, un pas impair de 0.007 la defait.
0.021 unite = 0.0013 bloc : assez pour le tampon de profondeur, invisible a l oeil.
"""
import json, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zdetect

PAS = 0.021


def vol(e):
    return abs((e['to'][0] - e['from'][0]) * (e['to'][1] - e['from'][1]) * (e['to'][2] - e['from'][2]))


def corrige(bb):
    P = zdetect.paires(bb)
    par_id, voisins = {}, collections.defaultdict(set)
    for ar, a, fa, b, fb, meme in P:
        par_id[id(a)] = a; par_id[id(b)] = b
        voisins[id(a)].add(id(b)); voisins[id(b)].add(id(a))
    vu, groupes = set(), []
    for k in par_id:
        if k in vu:
            continue
        pile, g = [k], []
        while pile:
            x = pile.pop()
            if x in vu:
                continue
            vu.add(x); g.append(x); pile.extend(voisins[x] - vu)
        groupes.append(g)
    # niveau = plus long chemin depuis une piece plus grosse (graphe oriente gros -> petit)
    def cle(k):
        return (-vol(par_id[k]), par_id[k]['name'])
    niveau = {}
    for k in sorted(par_id, key=cle):
        plus_gros = [v for v in voisins[k] if cle(v) < cle(k)]
        niveau[k] = 1 + max((niveau[v] for v in plus_gros), default=-1)
    for k, n in niveau.items():
        if n:
            e = par_id[k]
            e['inflate'] = round((e.get('inflate', 0) or 0) + PAS * n, 4)
    # coincidences nouvelles creees par un gonflement : pas impair sur la plus petite
    for _ in range(6):
        R = zdetect.paires(bb)
        if not R:
            break
        for ar, a, fa, b, fb, meme in R:
            e = a if vol(a) < vol(b) or (vol(a) == vol(b) and a['name'] > b['name']) else b
            e['inflate'] = round((e.get('inflate', 0) or 0) + 0.007, 4)
    return P, groupes, par_id


if __name__ == '__main__':
    bb = json.load(open(sys.argv[1]))
    P, groupes, par_id = corrige(bb)
    print('avant : %d paires, %.1f u2, en %d groupes de pieces' % (len(P), sum(x[0] for x in P), len(groupes)))
    reste = zdetect.paires(bb)
    print('apres : %d paires' % len(reste))
    for r in reste[:6]:
        print('   reste %.2f %s %s <-> %s %s' % (r[0], r[1]['name'], r[2], r[3]['name'], r[4]))
    gon = [e for e in bb['elements'] if e.get('inflate')]
    print('%d cubes gonfles, maximum %.3f unite' % (len(gon), max(e['inflate'] for e in gon) if gon else 0))
    json.dump(bb, open(sys.argv[2], 'w'), separators=(',', ':'))
    if reste:
        sys.exit(1)
