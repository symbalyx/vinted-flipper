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
        self.box = {}
        for u, cl in self.cubes.items():
            pts = []
            for cu in cl:
                e = self.elems[cu]
                pts.append(e['from'])
                pts.append(e['to'])
            if pts:
                lo = [min(p[k] for p in pts) for k in range(3)]
                hi = [max(p[k] for p in pts) for k in range(3)]
                self.box[u] = [[lo[0] if i else hi[0], lo[1] if j else hi[1], lo[2] if k else hi[2]]
                               for i in (0, 1) for j in (0, 1) for k in (0, 1)]

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
        for u, corners in self.box.items():
            nm = self.groups[u]['name']
            if nm not in P or nm in skip or (only is not None and nm not in only):
                continue
            M, off, O = P[nm]
            for p in corners:
                y = sum(M[1][k] * (p[k] - O[k]) for k in range(3)) + off[1]
                if y < lo:
                    lo = y
        return lo
