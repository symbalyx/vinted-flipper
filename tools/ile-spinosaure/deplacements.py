"""Se deplacer sur l'ile : tyroliennes, passerelles de corde, barques, wagonnets.

Tyroliennes (mods Ziplines: Rezipped! + Reconnectible Chains) : le mod de tyrolienne n'ajoute pas
de cable, il fait glisser le joueur (pioche en main, clic droit maintenu) le long des chaines
tendues entre deux barrieres par Reconnectible Chains. Ce qu'on lit dans ses jars (CI, job
recherche) et qui fixe la construction :
- une chaine relie deux « noeuds » (entite connectiblechains:chain_knot, accrochee a une barriere
  ou un muret : TileX/TileY/TileZ) ; le noeud de depart garde le lien : Chains[{DestX, DestY,
  DestZ, SourceItem}] ;
- portee maximale d'une chaine : 32 blocs par defaut (reglage du joueur, pas de la carte) : on
  tend des troncons de 28 blocs au plus, et le joueur passe d'un troncon au suivant (angle < 45°) ;
- le joueur pend 2,3 blocs sous le cable : les pylones sont des potences (poteau decale de 2 blocs,
  bras au-dessus de la ligne, barriere d'ancrage pendue sous le bras), jamais sous la ligne ;
- physique a l'elan : on prend de la vitesse en descendant, on en perd en montant. Chaque ligne
  descend du depart (station haute) a l'arrivee.
"""
import math

import numpy as np

AIR = 'minecraft:air'
EAU = 'minecraft:water[level=0]'
PORTEE = 28                  # longueur maximale d'un troncon (la chaine casse au-dela de 32)
PENDU = 2.3                  # le joueur pend a 2,3 blocs sous le cable
MOU = 0.10                   # fleche estimee d'un troncon : 10 % de sa longueur (prudent)
BOIS = 'minecraft:stripped_spruce_log[axis=%s]'
PLANCHE = 'minecraft:spruce_planks'
BARRIERE = 'minecraft:spruce_fence'


class Reseau:
    def __init__(self, m, r, li, rng):
        self.m, self.r, self.li, self.rng = m, r, li, rng
        self.lignes = []                                   # (nom, [ancres (x, y, z)])
        self.couloir = np.zeros(r.h.shape, bool)           # pas d'arbre planté dans le couloir des cables
        self.echantillons = []                             # points du cable (x, y, z) pour degager les feuillages

    # ------------------------------------------------------------------ outils
    def haut_solide(self, x, z):
        """Plus haut bloc non vegetal de la colonne (sol, batiments, rochers), d'apres une carte
        calculee une fois (les arbres ne sont pas encore plantes)."""
        m = self.m
        if not (0 <= x < m.W and 0 <= z < m.L):
            return m.H
        if getattr(self, '_sommets', None) is None:
            dur = np.zeros(len(m.palette) + 1, bool)
            for n, i in m.palette.items():
                base = n.split('[')[0].split(':')[-1]
                dur[i] = i != m.AIR and base not in ('grass', 'fern', 'tall_grass', 'large_fern', 'water', 'moss_carpet') and \
                    not any(t in base for t in ('leaves', 'vine', 'bamboo', 'flower', 'bush', 'sapling'))
            plein = dur[m.blocs]
            self._sommets = (m.H - 1 - np.argmax(plein[::-1], axis=0)).astype(np.int32)
        return int(self._sommets[z, x])

    def _s3(self):
        """Sommets solides, maximum sur 3 x 3 (le joueur a un peu de largeur, et le vent)."""
        if getattr(self, '_s3_', None) is None:
            self.haut_solide(0, 0)
            s = np.maximum(self._sommets, self.r.eau.astype(np.int32))       # la surface de l'eau compte aussi
            t = s.copy()
            t[1:] = np.maximum(t[1:], s[:-1]); t[:-1] = np.maximum(t[:-1], s[1:])
            u = t.copy()
            u[:, 1:] = np.maximum(u[:, 1:], t[:, :-1]); u[:, :-1] = np.maximum(u[:, :-1], t[:, 1:])
            self._s3_ = u
        return self._s3_

    def _pourquoi(self, raison, h):
        import os
        if os.environ.get('TYRO_DEBUG'):
            print('   refus h=%d : %s' % (h, raison))

    def _deficits(self, pts, hauteurs):
        """Pour chaque troncon : le plus grand manque de hauteur (obstacle + 1 - bas du joueur),
        fleche comprise. Les 2 premiers et les 4 derniers blocs de la ligne ne comptent pas : on y
        est sur une station (plancher, portique)."""
        S = self._s3()
        total = sum(math.dist(p, q) for p, q in zip(pts, pts[1:]))
        fait = 0.0
        out = []
        for (a, ha), (b, hb) in zip(zip(pts, hauteurs), zip(pts[1:], hauteurs[1:])):
            Lh = math.dist(a, b)
            L = math.dist((a[0], ha, a[1]), (b[0], hb, b[1]))
            t = np.linspace(0, 1, max(3, int(Lh) + 1))
            x = np.round(a[0] + (b[0] - a[0]) * t).astype(int)
            z = np.round(a[1] + (b[1] - a[1]) * t).astype(int)
            yc = ha + (hb - ha) * t - 4 * MOU * L * t * (1 - t)
            manque = (S[z, x] + 1 + 0.8) - (yc - PENDU - 0.3)
            d = fait + t * Lh
            manque[(d < 2) | (d > total - 4)] = -99
            out.append((float(manque.max()), t[int(np.argmax(manque))]))
            fait += Lh
        return out

    def _profil(self, pts, hauteurs):
        return -max(m for m, _ in self._deficits(pts, hauteurs)) + 0.8

    def diagnostic(self, a, b):
        """Pourquoi une ligne a -> b est impossible (tour la plus haute)."""
        ya, yb = self.haut_solide(*a) + 1, self.haut_solide(*b) + 1
        return 'sols %d -> %d, %.0f blocs' % (ya, yb, math.dist(a, b))

    # ------------------------------------------------------------------ une ligne
    def tyrolienne(self, a, b, nom, sol_depart=None, haut_min=8, haut_max=42):
        """Tyrolienne de a (x, z) vers b (x, z). La station de depart est une tour dont on cherche
        la hauteur minimale qui laisse passer le joueur partout ; l'arrivee est un portique au sol.
        Renvoie la liste des ancres, ou None si c'est impossible (trop plat, obstacle)."""
        ya = self.haut_solide(*a) + 1 if sol_depart is None else sol_depart
        yb = self.haut_solide(*b) + 1
        D = math.dist(a, b)
        n = max(1, math.ceil(D / (PORTEE - 2)))
        pts = [(int(round(a[0] + (b[0] - a[0]) * i / n)), int(round(a[1] + (b[1] - a[1]) * i / n))) for i in range(n + 1)]
        arrivee = yb + 5                     # quai d'arrivee sureleve de 2 : ancrage 3 au-dessus du plancher
        for h in range(haut_min, haut_max + 1, 2):
            depart = ya + h + 3                                  # plancher a ya + h, ancrage 3 au-dessus
            if depart - arrivee < max(6, D * 0.06):               # il faut descendre (au moins ~6 %)
                self._pourquoi('pente', h)
                continue
            if depart >= self.m.H - 4:
                break
            hauteurs = [depart + (arrivee - depart) * i / n for i in range(n + 1)]
            # relever les pylones interieurs la ou le relief l'exige, sans jamais faire remonter la ligne
            for _ in range(12):
                deficits = self._deficits(pts, hauteurs)
                if max(m for m, _ in deficits) <= 0:
                    break
                for i, (manque, t) in enumerate(deficits):
                    if manque <= 0:
                        continue
                    if 0 < i + 1 < n:                              # extremite aval interieure
                        hauteurs[i + 1] += manque / max(t, 0.3) * 0.6
                    if 0 < i < n:                                  # extremite amont interieure
                        hauteurs[i] += manque / max(1 - t, 0.3) * 0.6
                for i in range(n - 1, 0, -1):                     # jamais plus haut que le precedent
                    hauteurs[i] = min(hauteurs[i], hauteurs[i - 1])
            if any(math.dist((p[0], y0, p[1]), (q[0], y1, q[1])) > PORTEE
                   for p, q, y0, y1 in zip(pts, pts[1:], hauteurs, hauteurs[1:])):
                self._pourquoi('portee', h)
                continue
            # pylones : pas plus de 45 blocs au-dessus du sol
            # (au-dessus de l'eau, compte depuis la surface : le poteau plonge jusqu'au fond)
            if any(hy - max(self.haut_solide(*p), int(self.r.eau[p[1], p[0]])) > 45 for p, hy in zip(pts[1:-1], hauteurs[1:-1])):
                self._pourquoi('pylone>45', h)
                continue
            marge = self._profil(pts, hauteurs)
            self.derniere_marge = max(getattr(self, 'derniere_marge', -99.0), marge)
            if marge < 0.8:
                self._pourquoi('marge %.1f' % marge, h)
                continue
            return self._construire(pts, [int(round(y)) for y in hauteurs], ya, ya + h, yb, nom)
        return None

    def _construire(self, pts, hauteurs, sol_a, plancher, yb, nom):
        m = self.m
        d = np.array(pts[-1], float) - np.array(pts[0], float)
        d /= max(np.linalg.norm(d), 1e-6)
        nrm = np.array([-d[1], d[0]])
        axe_b = 'x' if abs(nrm[0]) >= abs(nrm[1]) else 'z'
        ancres = []
        # depart : tour de 5 x 5, plancher a `plancher`, echelle a l'arriere, portique sur l'avant
        ax, az = pts[0]
        self._tour(ax, az, sol_a, plancher, d)
        ancres.append((ax, hauteurs[0], az))
        # pylones a potence
        for (px, pz), hy in zip(pts[1:-1], hauteurs[1:-1]):
            cx, cz = int(round(px + 2 * nrm[0])), int(round(pz + 2 * nrm[1]))
            bas = min(int(self.r.h[pz, px]), int(self.r.h[cz, cx])) - 2
            for y in range(bas, hy + 2):
                m.pose(cx, y, cz, BOIS % 'y')
            for s in (0.0, 0.5, 1.0, 1.5, 2.0):                  # bras du poteau jusqu'au-dessus de la ligne
                qx, qz = int(round(px + s * nrm[0])), int(round(pz + s * nrm[1]))
                m.pose(qx, hy + 1, qz, BOIS % axe_b)
            # jambe de force sous le bras
            m.pose(int(round(px + 1.5 * nrm[0])), hy, int(round(pz + 1.5 * nrm[1])), 'minecraft:spruce_fence')
            m.pose(px, hy, pz, BARRIERE)                         # ancrage, pendu sous le bras
            ancres.append((px, hy, pz))
            self.li.ajoute('', cx, cz, 3)
        # arrivee : plancher au sol, portique (2 poteaux, traverse, barriere pendue au milieu)
        bx, bz = pts[-1]
        self._portique(bx, bz, yb + 3, d, arrivee=True)
        ancres.append((bx, hauteurs[-1], bz))
        # couloir sans arbres et echantillons du cable
        for (p, hp), (q, hq) in zip(zip(pts, hauteurs), zip(pts[1:], hauteurs[1:])):
            L = math.dist(p, q)
            for k in range(int(L) + 1):
                t = k / max(L, 1)
                x, z = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
                yc = hp + (hq - hp) * t - 4 * MOU * L * t * (1 - t)
                self.echantillons.append((x, yc, z))
                ix, iz = int(round(x)), int(round(z))
                self.couloir[max(0, iz - 4):iz + 5, max(0, ix - 4):ix + 5] = True
        self.lignes.append((nom, ancres))
        self.li.ajoute(nom + ' (depart)', ax, az, 6)
        self.li.ajoute(nom + ' (arrivee)', bx, bz, 5)
        return ancres

    def _tour(self, x, z, sol, plancher, d):
        """Tour de depart : 4 poteaux, plancher 5 x 5, garde-corps, echelle a l'arriere, portique a
        l'avant (le cote de la ligne), lanterne."""
        m = self.m
        for dx in (-2, 2):
            for dz in (-2, 2):
                for y in range(min(sol, int(self.r.h[z + dz, x + dx])) - 2, plancher + 1):
                    m.pose(x + dx, y, z + dz, BOIS % 'y')
        for y in range(sol + 3, plancher, 6):                    # entretoises
            for i in range(-2, 3):
                for (a, b) in ((i, -2), (i, 2), (-2, i), (2, i)):
                    if m.get(x + a, y, z + b) == m.AIR:
                        m.pose(x + a, y, z + b, BARRIERE)
        m.boite(x - 2, plancher, z - 2, x + 2, plancher, z + 2, PLANCHE)
        # echelle a l'arriere : sur un poteau central, du sol au plancher
        face = {(1, 0): 'east', (-1, 0): 'west', (0, 1): 'south', (0, -1): 'north'}      # l'echelle regarde vers l'avant
        cle = (int(np.sign(d[0])), 0) if abs(d[0]) >= abs(d[1]) else (0, int(np.sign(d[1])))
        dos = (-cle[0], -cle[1])
        # le mur de l'echelle : un poteau plein a l'arriere, echelle devant lui (cote tour)
        wx, wz = x + dos[0] * 3, z + dos[1] * 3
        lx, lz = x + dos[0] * 2, z + dos[1] * 2
        for y in range(sol, plancher + 1):
            m.pose(wx, y, wz, BOIS % 'y')
        for y in range(sol, plancher):
            m.pose(lx, y, lz, 'minecraft:ladder[facing=%s,waterlogged=false]' % face.get(cle, 'north'))
        m.pose(lx, plancher, lz, 'minecraft:ladder[facing=%s,waterlogged=false]' % face.get(cle, 'north'))   # tremie
        # garde-corps sauf a l'avant (3 blocs ouverts) et au-dessus de l'echelle
        for i in range(-2, 3):
            for (a, b) in ((i, -3), (i, 3), (-3, i), (3, i)):
                if (a, b) == (dos[0] * 3, dos[1] * 3):
                    continue
                if (a * cle[0] + b * cle[1]) == 3 and abs(a * cle[1] - b * cle[0]) <= 1:
                    continue
                m.pose(x + a, plancher + 1, z + b, BARRIERE)
        for dz in range(-3, 4):
            for dx in range(-3, 4):
                if m.get(x + dx, plancher, z + dz) == m.AIR:
                    m.pose(x + dx, plancher, z + dz, PLANCHE)
        # portique a l'avant : barriere d'ancrage 3 au-dessus du plancher, au bord
        self._portique(x, z, plancher + 1, d, arrivee=False)
        m.pose(x - cle[1] * 3, plancher + 2, z + cle[0] * 3, 'minecraft:lantern[hanging=false,waterlogged=false]')

    def _portique(self, x, z, y_pied, d, arrivee):
        """Deux poteaux de part et d'autre de la ligne, traverse, barriere pendue au milieu en
        (x, y_pied + 2, z) : l'ancrage de la chaine."""
        m = self.m
        n = (-d[1], d[0])
        axe = 'x' if abs(n[0]) >= abs(n[1]) else 'z'
        for s in (-2, 2):
            px, pz = int(round(x + n[0] * s)), int(round(z + n[1] * s))
            for y in range(int(self.r.h[pz, px]) - 1 if arrivee else y_pied, y_pied + 4):
                m.pose(px, y, pz, BOIS % 'y')
        for s in (-2, -1, 0, 1, 2):
            m.pose(int(round(x + n[0] * s)), y_pied + 3, int(round(z + n[1] * s)), BOIS % axe)
        m.pose(x, y_pied + 2, z, BARRIERE)
        if arrivee:
            # plancher d'arrivee 5 x 5 sur le sol (ou sur pilotis au-dessus de l'eau)
            for dz in range(-2, 3):
                for dx in range(-2, 3):
                    for y in range(int(self.r.h[z + dz, x + dx]), y_pied - 1):
                        m.pose(x + dx, y, z + dz, BOIS % 'y' if (dx in (-2, 2) and dz in (-2, 2)) else AIR)
                    m.pose(x + dx, y_pied - 1, z + dz, PLANCHE)
            # marches pour descendre du quai, dans le sens de la marche (on sort vers l'avant)
            fx, fz = (int(np.sign(d[0])), 0) if abs(d[0]) >= abs(d[1]) else (0, int(np.sign(d[1])))
            face = {(1, 0): 'west', (-1, 0): 'east', (0, 1): 'north', (0, -1): 'south'}[(fx, fz)]
            for k in range(1, 5):
                sx, sz = x + fx * (2 + k), z + fz * (2 + k)
                ys = y_pied - 1 - k
                if ys < int(self.r.h[sz, sx]):
                    break
                for l in (-1, 0, 1):
                    m.pose(sx + fz * l, ys, sz + fx * l,
                           'minecraft:spruce_stairs[facing=%s,half=bottom,shape=straight,waterlogged=false]' % face)

    # ------------------------------------------------------------------ apres la foret
    def degager(self):
        """Retire feuillages, lianes et mousse dans un tube autour du cable (et sous lui, la ou
        pend le joueur). Les troncs n'y sont pas : le couloir a ete interdit a la plantation."""
        m = self.m
        vege = np.zeros(len(m.palette) + 1, bool)
        for nom, i in m.palette.items():
            vege[i] = any(t in nom for t in ('leaves', 'vine', 'spanish_moss', 'cocoa', 'propagule'))
        n = 0
        vus = set()
        for (x, y, z) in self.echantillons:
            ix, iz = int(round(x)), int(round(z))
            for dz in range(-2, 3):
                for dx in range(-2, 3):
                    if dx * dx + dz * dz > 5 or (ix + dx, iz + dz) in vus:
                        continue
                    for yy in range(int(math.floor(y - PENDU - 2.5)), int(math.ceil(y + 1.5))):
                        if 0 <= yy < m.H and vege[m.blocs[yy, iz + dz, ix + dx]]:
                            m.blocs[yy, iz + dz, ix + dx] = m.AIR
                            n += 1
            vus.add((ix, iz))
            if len(vus) > 20000:
                vus.clear()
        return n

    def noeuds(self):
        """Entites « noeud de chaine » sur chaque ancrage ; chaque noeud tient la chaine vers le
        suivant. UUID stables."""
        import nbt
        from monde_java import ORIGINE, DECALAGE_Y
        k = 0
        for nom, ancres in self.lignes:
            for i, (x, y, z) in enumerate(ancres):
                k += 1
                c = {'id': nbt.String('connectiblechains:chain_knot'),
                     'TileX': nbt.Int(x), 'TileY': nbt.Int(y), 'TileZ': nbt.Int(z),
                     'AttachedFace': nbt.Int(1),
                     'SourceItem': nbt.String('minecraft:chain'),
                     'UUID': nbt.IntArray([0x5A1B0000 + k, 0x20260925, 0x0C4A1, k])}
                if i + 1 < len(ancres):
                    X, Y, Z = ancres[i + 1]
                    c['Chains'] = nbt.List('compound', [nbt.Compound({
                        'DestX': nbt.Int(X + ORIGINE), 'DestY': nbt.Int(Y + DECALAGE_Y), 'DestZ': nbt.Int(Z + ORIGINE),
                        'SourceItem': nbt.String('minecraft:chain')})])
                # TileX/Y/Z en coordonnees du monde : l'export ne convertit que Pos
                c['TileX'] = nbt.Int(x + ORIGINE); c['TileY'] = nbt.Int(y + DECALAGE_Y); c['TileZ'] = nbt.Int(z + ORIGINE)
                self.m.mobiles.append((x + 0.5, y + 0.5, z + 0.5, c))
        return k


# =============================================================================================
def passerelle_ravin(m, r, pr, emprise, milieu):
    """Passerelle de corde au-dessus d'un ravin : planches et chaines (garde-corps), qui
    s'affaisse au milieu. Traversee perpendiculaire au ravin, en son milieu."""
    zs, xs = np.nonzero(emprise)
    c = np.cov(np.stack([xs, zs]).astype(float))
    w, v = np.linalg.eigh(c)
    axe = v[:, np.argmax(w)]                       # direction du ravin
    nrm = np.array([-axe[1], axe[0]])
    mx, mz = milieu
    # bords : on part du milieu et on sort de l'emprise des deux cotes
    bords = []
    for s in (1, -1):
        for t in range(1, 30):
            x, z = int(round(mx + nrm[0] * t * s)), int(round(mz + nrm[1] * t * s))
            if not emprise[z, x]:
                bords.append((int(round(mx + nrm[0] * (t + 2) * s)), int(round(mz + nrm[1] * (t + 2) * s))))
                break
    if len(bords) < 2:
        return None
    (ax, az), (bx, bz) = bords
    y = min(int(r.h[az, ax]), int(r.h[bz, bx])) + 1
    L = math.dist((ax, az), (bx, bz))
    n = int(L) + 1
    for i in range(n + 1):
        t = i / n
        x, z = ax + (bx - ax) * t, az + (bz - az) * t
        yy = int(round(y - 2.5 * math.sin(math.pi * t)))
        for s in (-1, 0, 1):
            qx, qz = int(round(x + axe[0] * s)), int(round(z + axe[1] * s))
            if m.get(qx, yy, qz) == m.AIR or t < 0.08 or t > 0.92:
                m.pose(qx, yy, qz, 'minecraft:spruce_slab[type=bottom,waterlogged=false]' if 0.08 < t < 0.92 else PLANCHE)
        for s in (-2, 2):
            qx, qz = int(round(x + axe[0] * s)), int(round(z + axe[1] * s))
            m.pose(qx, yy + 1, qz, 'minecraft:chain[axis=y,waterlogged=false]' if i % 3 else BARRIERE)
    for (px, pz) in ((ax, az), (bx, bz)):
        for s in (-2, 2):
            qx, qz = int(round(px + axe[0] * s)), int(round(pz + axe[1] * s))
            for yy in range(int(r.h[qz, qx]) - 2, y + 3):
                m.pose(qx, yy, qz, BOIS % 'y')
    return (ax, az), (bx, bz)


def barques(m, r, li, noms=('Ponton', 'Village', 'Bungalow', 'Station du delta')):
    """Des barques amarrees : sur l'eau libre la plus proche de chaque ponton / village."""
    import nbt
    faites = []
    for nom, x, z, _ in li.poi:
        if not nom.startswith(noms):
            continue
        if any(math.hypot(x - a, z - b) < 25 for a, b in faites):
            continue
        best = None
        for rr in range(4, 30):
            for k in range(24):
                a = k * math.pi / 12
                px, pz = int(round(x + math.cos(a) * rr)), int(round(z + math.sin(a) * rr))
                if not (2 <= px < m.W - 2 and 2 <= pz < m.L - 2):
                    continue
                e = int(r.eau[pz, px])
                if e >= r.SEA - 1 and e - r.h[pz, px] >= 2 and m.get(px, e + 1, pz) == m.AIR and \
                        m.get(px, e, pz) == m.P(EAU) and m.get(px + 1, e, pz) == m.P(EAU) and m.get(px, e, pz + 1) == m.P(EAU):
                    best = (px, e, pz)
                    break
            if best:
                break
        if not best:
            continue
        px, e, pz = best
        m.mobiles.append((px + 0.5, e + 0.95, pz + 0.5, {
            'id': nbt.String('minecraft:boat'), 'Type': nbt.String('jungle'),
            'Rotation': nbt.List('float', [nbt.Float(float(li.rng.uniform(0, 360))), nbt.Float(0)])}))
        faites.append((x, z))
    return len(faites)


def wagonnets(m, pr, rng, n_ile=6, n_profond=4):
    """Wagonnets sur les rails des mines (quelques-uns avec un coffre)."""
    import nbt
    rails = [i for nom, i in m.palette.items() if nom.startswith('minecraft:rail[')]
    poses = 0
    for tableau, dy, n in ((m.blocs, 0, n_ile), (pr.b, -79, n_profond)):
        ys, zs, xs = np.nonzero(np.isin(tableau, rails))
        if not len(ys):
            continue
        for k in rng.choice(len(ys), min(n, len(ys)), replace=False):
            coffre = rng.random() < 0.35
            c = {'id': nbt.String('minecraft:chest_minecart' if coffre else 'minecraft:minecart')}
            if coffre:
                c['Items'] = nbt.List('compound', [
                    nbt.Compound({'Slot': nbt.Byte(0), 'id': nbt.String('minecraft:torch'), 'Count': nbt.Byte(12)}),
                    nbt.Compound({'Slot': nbt.Byte(4), 'id': nbt.String('minecraft:rail'), 'Count': nbt.Byte(16)}),
                    nbt.Compound({'Slot': nbt.Byte(9), 'id': nbt.String('minecraft:raw_iron'), 'Count': nbt.Byte(int(rng.integers(3, 9)))}),
                ])
            m.mobiles.append((int(xs[k]) + 0.5, int(ys[k]) + dy + 0.0625, int(zs[k]) + 0.5, c))
            poses += 1
    return poses
