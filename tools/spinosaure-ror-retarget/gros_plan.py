"""Gros plan sur une zone du modele (os donnes), avec le rendu texture + profondeur."""
import sys, json
sys.path.insert(0, 'tools')
import compare_gif as C, gif, fk as FK
from boite import coins
from PIL import Image, ImageDraw

def pose(A, nom, u):
    T = C.pistes(A[4][nom])
    return A[1].pose(lambda b, c: (C.lp(T[b][c], u) if b in T and c in T.get(b, {})
                                   else ([1., 1., 1.] if c == 'scale' else [0., 0., 0.])))

def cadre_os(rig, P, os_, taille, az, el, marge=0.8):
    V = gif.mat_vue(az, el); xs = []; ys = []
    for u, cl in rig.cubes.items():
        nm = rig.groups[u]['name']
        if nm not in os_ or nm not in P: continue
        M, off, O = P[nm]
        for cu in cl:
            e = rig.elems[cu]; R = FK.mat_rot(*e.get('rotation', [0, 0, 0])); eo = e.get('origin', O)
            for p in coins(e['from'], e['to']):
                q = FK.apply(R, [p[x] - eo[x] for x in range(3)]); q = [q[x] + eo[x] for x in range(3)]
                w = FK.apply(M, [q[x] - O[x] for x in range(3)]); v = gif.applique(V, [w[x] + off[x] for x in range(3)])
                xs.append(v[0]); ys.append(v[1])
    sc = min(taille[0] * marge / (max(xs) - min(xs)), taille[1] * marge / (max(ys) - min(ys)))
    return sc, taille[0] / 2 - (min(xs) + max(xs)) / 2 * sc, taille[1] / 2 + (min(ys) + max(ys)) / 2 * sc

def gros_plan(modele, cas, os_, sortie, taille=(360, 300), surligne_prefixes=()):
    A = C.prepare(modele)
    surl = set()
    for e in A[0]['elements']:
        if e['name'].startswith(surligne_prefixes) and surligne_prefixes:
            for f in e['faces']: surl.add((e['uuid'], f))
    ims = []
    for nom, u, az, el in cas:
        P = pose(A, nom, u)
        sc, cx, cy = cadre_os(A[1], P, os_, taille, az, el)
        img = gif.rendu_z(A[1], A[2], A[3], P, taille, sc, cx, cy, az, el, (30, 32, 40), surl)
        ImageDraw.Draw(img).text((6, 4), '%s t=%.2f az=%d' % (nom, u, az), fill=(240, 240, 240))
        ims.append(img)
    o = Image.new('RGB', (taille[0] * len(ims) + 4 * (len(ims) - 1), taille[1]), (70, 70, 80))
    for i, im in enumerate(ims): o.paste(im, (i * (taille[0] + 4), 0))
    o.save(sortie); print('ecrit', sortie)

if __name__ == '__main__':
    MAIN = ('hand_left', 'finger_left_0', 'finger_left_1', 'finger_left_2', 'forearm_left')
    m = sys.argv[1]
    gros_plan(m, [('pose_reference', 0, 90, 5), ('pose_reference', 0, 150, 20), ('pose_reference', 0, 30, -30), ('pose_reference', 0, 200, 60)],
              MAIN, '/tmp/main_repos.png')
    gros_plan(m, [('pose_reference', 0, 90, 5), ('pose_reference', 0, 150, 20), ('pose_reference', 0, 30, -30), ('pose_reference', 0, 200, 60)],
              MAIN, '/tmp/main_repos_rouge.png', surligne_prefixes=('V74_nageoire_main',))
