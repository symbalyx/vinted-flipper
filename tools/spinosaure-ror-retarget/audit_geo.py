"""Audit geometrique profond, en pose de repos.

Ce que les audits precedents ne regardaient pas :
  1. z-fighting : faces coplanaires, meme orientation, qui se recouvrent -> scintillement
  2. symetrie gauche/droite : pieces qui n ont pas leur jumelle miroir
  3. densite de texels : faces floues (trop peu de pixels par unite) ou etirees
  4. place reellement utile dans l atlas de 4096
"""
import json, sys, math, collections
sys.path.insert(0, 'tools')
import fk as FK
from boite import coins, FACES

bb = json.load(open(sys.argv[1]))
rig = FK.Rig(bb)
P = rig.pose(lambda b, c: [1., 1., 1.] if c == 'scale' else [0., 0., 0.])
RES = bb.get('resolution', {'width': 4096, 'height': 4096})



faces = []          # (element, face, normal, pts_monde)
cubes = []
for u, cl in rig.cubes.items():
    nm = rig.groups[u]['name']
    if nm not in P:
        continue
    M, off, O = P[nm]
    for cu in cl:
        e = rig.elems[cu]
        R = FK.mat_rot(*e.get('rotation', [0, 0, 0]))
        eo = e.get('origin', O)
        W = []
        for p in coins(e['from'], e['to']):
            q = FK.apply(R, [p[x] - eo[x] for x in range(3)])
            q = [q[x] + eo[x] for x in range(3)]
            w = FK.apply(M, [q[x] - O[x] for x in range(3)])
            W.append([w[x] + off[x] for x in range(3)])
        cubes.append((e, nm, W))
        for fn, (idx, nl, _) in FACES.items():
            fd = e.get('faces', {}).get(fn)
            if not fd or fd.get('texture') is None:
                continue
            n = FK.apply(M, FK.apply(R, list(nl)))
            faces.append((e, fn, n, [W[i] for i in idx], fd, nm))

# ------------------------------------------------------------------ 1. z-fighting
# detection commune a zfight.py (tient compte du champ inflate) : une copie locale de
# ce code, qui l ignorait, annoncait encore 83 paires sur un modele deja corrige
import zdetect
zf = zdetect.paires(bb)
print('1. Z-FIGHTING (faces coplanaires de meme orientation qui se recouvrent)')
print('   %d paires, surface cumulee %.1f u2' % (len(zf), sum(z[0] for z in zf)))
print('   dont %d dans un meme os (scintillent TOUJOURS) et %d entre os (selon la pose)'
      % (sum(1 for z in zf if z[5]), sum(1 for z in zf if not z[5])))
for z in zf[:14]:
    print('     %6.2f u2  %-28s %-5s  <->  %-28s %-5s %s' % (z[0], z[1]['name'], z[2], z[3]['name'], z[4],
                                                           '' if z[5] else '(os differents)'))
json.dump([[z[0], z[1]['name'], z[2], z[3]['name'], z[4], z[5]] for z in zf], open('/tmp/zfight.json', 'w'))

# ------------------------------------------------------------------ 2. symetrie
print('\n2. SYMETRIE GAUCHE / DROITE')
def centre(W):
    return [sum(p[k] for p in W) / 8 for k in range(3)]
def dims(e):
    return sorted(round(abs(e['to'][k] - e['from'][k]), 2) for k in range(3))
lat = [(e, nm, W, centre(W)) for e, nm, W in cubes]
seuls = []
ecarts = []
for e, nm, W, c in lat:
    if abs(c[0]) < 0.8:          # piece mediane
        continue
    cible = [-c[0], c[1], c[2]]
    best = None
    for e2, nm2, W2, c2 in lat:
        if e2 is e:
            continue
        dd = math.dist(cible, c2)
        if best is None or dd < best[0]:
            best = (dd, e2, dims(e2))
    if best is None or best[0] > 3.0:
        seuls.append((e['name'], round(best[0], 1) if best else None))
    else:
        dim_ecart = max(abs(a - b) for a, b in zip(dims(e), best[2]))
        if best[0] > 0.35 or dim_ecart > 0.35:
            ecarts.append((round(best[0], 2), round(dim_ecart, 2), e['name'], best[1]['name']))
print('   pieces laterales sans jumelle miroir a moins de 3 u : %d' % len(seuls))
for s in seuls[:10]:
    print('     ', s)
ecarts.sort(reverse=True)
print('   paires miroir decalees ou de tailles differentes (> 0.35 u) : %d' % len(ecarts))
for e in ecarts[:10]:
    print('      decalage %5.2f  ecart taille %5.2f  %-30s <-> %s' % e)

# ------------------------------------------------------------------ 3. densite de texels
print('\n3. DENSITE DE TEXELS (pixels d atlas par unite de modele)')
dens = []
for e, fn, n, pts, fd, bone in faces:
    uv = fd.get('uv')
    if not uv:
        continue
    ax = FACES[fn][2]
    f, t = e['from'], e['to']
    lu = abs(t[ax[0]] - f[ax[0]]); lv = abs(t[ax[1]] - f[ax[1]])
    pu = abs(uv[2] - uv[0]); pv = abs(uv[3] - uv[1])
    rot = fd.get('rotation', 0) % 180
    if rot == 90:
        pu, pv = pv, pu
    if lu < 0.05 or lv < 0.05:
        continue
    du, dv = pu / lu, pv / lv
    dens.append((min(du, dv), max(du, dv) / max(1e-6, min(du, dv)), e['name'], fn, du, dv, lu * lv))
tri = sorted(d[0] for d in dens)
med = tri[len(tri) // 2]
print('   %d faces mesurees, densite mediane %.2f px/u' % (len(dens), med))
flou = [d for d in dens if d[0] < 0.35 * med]
etire = [d for d in dens if d[1] > 3.0]
print('   faces a moins de 35%% de la mediane (floues a cote des autres) : %d' % len(flou))
for d in sorted(flou)[:8]:
    print('      %5.2f px/u  %-30s %-5s  (%.1f u2)' % (d[0], d[2], d[3], d[6]))
print('   faces etirees (rapport u/v > 3, texture deformee) : %d' % len(etire))
for d in sorted(etire, key=lambda x: -x[1])[:8]:
    print('      x%-5.1f  %-30s %-5s  u=%.2f v=%.2f px/u' % (d[1], d[2], d[3], d[4], d[5]))

# ------------------------------------------------------------------ 4. atlas
print('\n4. ATLAS')
rects = set()
for e, fn, n, pts, fd, bone in faces:
    uv = fd.get('uv')
    if uv:
        rects.add((min(uv[0], uv[2]), min(uv[1], uv[3]), max(uv[0], uv[2]), max(uv[1], uv[3])))
G = 512
occ = bytearray(G * G)
for x0, y0, x1, y1 in rects:
    for gx in range(int(x0 / RES['width'] * G), min(G, int(math.ceil(x1 / RES['width'] * G)))):
        for gy in range(int(y0 / RES['height'] * G), min(G, int(math.ceil(y1 / RES['height'] * G)))):
            occ[gy * G + gx] = 1
utile = sum(occ) / (G * G)
print('   %d rectangles UV distincts, %.1f%% de l atlas utilise' % (len(rects), 100 * utile))
cote = math.sqrt(utile) * RES['width']
print('   surface utile equivalente a un carre de %.0f px de cote' % cote)
for s in (1024, 2048):
    print('   un atlas de %d suffirait %s, sans perdre un seul texel' % (s, 'probablement' if cote * 1.25 < s else 'NON'))
