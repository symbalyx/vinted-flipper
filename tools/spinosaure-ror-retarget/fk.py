"""Cinematique directe minimale sur un rig bbmodel bedrock (ordre ZYX, comme Blockbench)."""
import math


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


I3 = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


class Rig:
    def __init__(self, bb):
        self.groups = {g['uuid']: g for g in bb['groups']}
        self.elems = {e['uuid']: e for e in bb['elements']}
        self.children, self.byname, self.cubes = {}, {}, {}
        self._walk(bb['outliner'][0], None)
        self.root = bb['outliner'][0]['uuid']
        # une boite englobante par os, en coordonnees du modele
        # Coins EXACTS de chaque cube dans le repere de son os : rotation propre du cube
        # autour de son origine, et inflate. L ancienne version prenait la boite
        # englobante des from/to sans rotation : sur les tibias, dont les cubes sont
        # inclines, elle descendait 15 unites plus bas que la geometrie reelle, d ou de
        # fausses penetrations du sol (dort a -13.9 alors que le tibia est a +1.2) et des
        # calages au sol faits sur une forme qui n existe pas.
        import numpy as _np
        self._np = _np
        self.box = {}
        self._pts = {}
        for u, cl in self.cubes.items():
            pts = []
            for cu in cl:
                e = self.elems[cu]
                g = e.get('inflate', 0) or 0
                f = [e['from'][k] - g for k in range(3)]
                t = [e['to'][k] + g for k in range(3)]
                R = mat_rot(*e.get('rotation', [0, 0, 0]))
                eo = e.get('origin', [0, 0, 0])
                for i in (0, 1):
                    for j in (0, 1):
                        for k in (0, 1):
                            p = [f[0] if i == 0 else t[0], f[1] if j == 0 else t[1], f[2] if k == 0 else t[2]]
                            q = apply(R, [p[x] - eo[x] for x in range(3)])
                            pts.append([q[x] + eo[x] for x in range(3)])
            if pts:
                self.box[u] = pts
                self._pts[u] = _np.array(pts, dtype=float)

    def _walk(self, node, par):
        if isinstance(node, str):
            self.cubes.setdefault(par, []).append(node)
            return
        u = node['uuid']
        self.byname[self.groups[u]['name']] = u
        self.children.setdefault(par, []).append(u)
        for c in node.get('children', []):
            self._walk(c, u)

    def pose(self, get):
        """get(bone_name, chan) -> [x,y,z] ; retourne {name: (M, offset, origin)}."""
        out = {}
        stack = [(self.root, I3, [0.0, 0.0, 0.0], self.groups[self.root]['origin'])]
        while stack:
            u, pM, pOff, pO = stack.pop()
            g = self.groups[u]
            O = g['origin']
            rest = g.get('rotation', [0, 0, 0])
            ar = get(g['name'], 'rotation')
            ap = get(g['name'], 'position')
            sc = get(g['name'], 'scale')
            Rl = mat_rot(rest[0] + ar[0], rest[1] + ar[1], rest[2] + ar[2])
            Rl = [[Rl[i][j] * sc[j] for j in range(3)] for i in range(3)]
            M = mul(pM, Rl)
            w = apply(pM, [O[k] - pO[k] + ap[k] for k in range(3)])
            off = [pOff[k] + w[k] for k in range(3)]
            out[g['name']] = (M, off, O)
            for c in self.children.get(u, []):
                stack.append((c, M, off, O))
        return out

    def lowest(self, P, skip=(), only=None):
        lo = 1e9
        for u, arr in self._pts.items():
            nm = self.groups[u]['name']
            if nm not in P or nm in skip or (only is not None and nm not in only):
                continue
            M, off, O = P[nm]
            ligne = self._np.array(M[1], dtype=float)
            y = float((arr @ ligne).min() - ligne @ self._np.array(O, dtype=float)) + off[1]
            if y < lo:
                lo = y
        return lo
