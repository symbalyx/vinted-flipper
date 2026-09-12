"""Retarget des animations ROR (Java AnimationDefinition) vers le rig bedrock RIVIERE 70.

Conventions verifiees empiriquement (machoire / cou / bras, cf. notes.md) :
  rotation : (x, y, z)_bb = (-x, +y, -z)_ror   (miroir diag(1,-1,1) entre les deux espaces)
  position : identique (KeyframeAnimations.posVec inverse deja Y cote Java)
  echelle  : identique
"""
import json, math, uuid

FPS = 30.0
NS = uuid.UUID('6f0b2b5e-1c3f-4a7d-9e21-9a0c7c1d3b55')   # namespace deterministe

# ---------------------------------------------------------------- echantillonnage

def catmull(t, p0, p1, p2, p3):
    return p1 + 0.5 * t * (p2 - p0 + t * (2.0*p0 - 5.0*p1 + 4.0*p2 - p3 + t * (3.0*(p1 - p2) + p3 - p0)))

def sample(keys, t):
    """Reproduit AnimationChannel.Interpolations (LINEAR / CATMULLROM) de Minecraft."""
    if not keys:
        return None
    if t <= keys[0]['t']:
        return list(keys[0]['v'])
    if t >= keys[-1]['t']:
        return list(keys[-1]['v'])
    i = 0
    while i < len(keys) - 1 and keys[i+1]['t'] < t:
        i += 1
    a, b = keys[i], keys[i+1]
    span = b['t'] - a['t']
    d = 0.0 if span <= 1e-9 else (t - a['t']) / span
    if b['i'] == 'catmullrom':
        p0 = keys[max(0, i-1)]['v']
        p3 = keys[min(len(keys)-1, i+2)]['v']
        return [catmull(d, p0[k], a['v'][k], b['v'][k], p3[k]) for k in range(3)]
    return [a['v'][k] + (b['v'][k] - a['v'][k]) * d for k in range(3)]


class Src:
    """Une animation ROR echantillonnable, avec decalage temporel et fenetre optionnels."""
    def __init__(self, anims, name, offset=0.0, scale=1.0, t0=None, t1=None, loop_src=False):
        self.a = anims[name]
        self.offset, self.scale, self.loop = offset, scale, loop_src
        self.t0 = 0.0 if t0 is None else t0
        self.t1 = self.a['length'] if t1 is None else t1

    def at(self, bone, chan, t):
        ks = self.a['bones'].get(bone, {}).get(chan)
        if not ks:
            return None
        u = (t - self.offset) / self.scale + self.t0
        if self.loop:
            span = self.t1 - self.t0
            if span > 1e-9:
                u = self.t0 + ((u - self.t0) % span)
        elif u < self.t0 - 1e-9 or u > self.t1 + 1e-9:
            return None
        return sample(ks, u)


# ---------------------------------------------------------------- carte des os

# bb_bone : [(os_ror, poids), ...]
BONE_MAP = {
    'root':            [('All2', 1.0), ('All', 1.0), ('all_swim', 1.0)],
    'body':            [('Body', 1.0), ('RotZ', 1.0), ('torso', 0.35)],
    'chest':           [('Body2', 1.0), ('torso2', 0.35)],
    'sail':            [('fin', 1.0)],
    'neck':            [('Neck', 1.0), ('Neck2', 1.0), ('Neck3', 1.0),
                        ('shaker4', 0.25), ('shaker3', 0.25), ('shaker2', 0.25)],
    'head':            [('Neck4', 1.0), ('Head', 1.0), ('shaker', 0.25), ('bone', 0.30)],
    'jaw':             [('jaw', 1.0)],
    'throat':          [('throat', 1.0)],
    'upper_arm_left':  [('Arm3', 1.0)],
    'forearm_left':    [('Arm4', 1.0)],
    'hand_left':       [('hand', 1.0)],
    'finger_left_0':   [('finger', 1.0)],
    'finger_left_1':   [('finger2', 1.0)],
    'finger_left_2':   [('finger3', 1.0)],
    'upper_arm_right': [('Arm2', 1.0)],
    'forearm_right':   [('Arm5', 1.0)],
    'hand_right':      [('hand2', 1.0)],
    'finger_right_0':  [('finger4', 1.0)],
    'finger_right_1':  [('finger6', 1.0)],
    'finger_right_2':  [('finger5', 1.0)],
    'thigh_left':      [('Leg4', 1.0), ('leg_shaker', 0.30)],
    'shin_left':       [('Leg5', 1.0), ('Leg6', 1.0)],
    'foot_left':       [('Foot4', 1.0), ('Foot5', 0.15), ('Foot6', 0.15)],
    'thigh_right':     [('Leg2', 1.0), ('leg_shaker2', 0.30)],
    'shin_right':      [('Leg3', 1.0), ('Leg7', 1.0)],
    'foot_right':      [('Foot2', 1.0), ('Foot3', 0.15), ('Foot7', 0.15)],
    'tail_01':         [('Tail', 1.0)],
    'tail_02':         [('Tail2', 1.0)],
    'tail_03':         [('Tail3', 1.0)],
    'tail_04':         [('Tail4', 1.0)],
    'tail_05':         [('Tail5', 1.0)],
    'tail_06':         [],          # prolongement retarde de tail_05
}

# gains de rotation : compensent les differences de proportions et de pose de repos
GAIN = {
    'root': 1.00, 'body': 0.85, 'chest': 0.85, 'sail': 0.45,
    'neck': 0.80, 'head': 0.80, 'jaw': 0.85, 'throat': 0.50,
    'upper_arm_left': 0.62, 'forearm_left': 0.50, 'hand_left': 0.40,
    'upper_arm_right': 0.62, 'forearm_right': 0.50, 'hand_right': 0.40,
    'finger_left_0': 0.55, 'finger_left_1': 0.55, 'finger_left_2': 0.55,
    'finger_right_0': 0.55, 'finger_right_1': 0.55, 'finger_right_2': 0.55,
    'thigh_left': 0.80, 'shin_left': 0.70, 'foot_left': 0.50,
    'thigh_right': 0.80, 'shin_right': 0.70, 'foot_right': 0.50,
    'tail_01': 0.90, 'tail_02': 0.90, 'tail_03': 0.90,
    'tail_04': 0.90, 'tail_05': 0.90, 'tail_06': 0.65,
}

# Les doigts ROR sont empiles sur Y, les notres etales sur X : seul le repli (X) a
# un sens ici, l'ecartement lateral est fortement attenue. Bornes calees sur le style
# maison (doigts <= 20 deg, main <= 41 deg).
AXIS = {b: (1.0, 0.15, 0.15) for b in
        ('finger_left_0', 'finger_left_1', 'finger_left_2',
         'finger_right_0', 'finger_right_1', 'finger_right_2')}
LIMIT = {b: 20.0 for b in AXIS}   # plage maison (grimpe monte a 20)

# L'echelle de la gorge ROR s'applique a un plan plat ; notre gorge est un volume,
# on amortit donc le gonflement pour qu'elle ne traverse pas le cou.
SCALE_GAIN = {'throat': 0.55}

CORE = list(BONE_MAP.keys())            # 32 os, exactement la couverture maison


def eval_bone(srcs, bb_bone, chan, t):
    """Somme ponderee des sources ROR pour un os bb, dans l'espace bedrock."""
    total = [0.0, 0.0, 0.0] if chan != 'scale' else [1.0, 1.0, 1.0]
    got = False
    g = GAIN.get(bb_bone, 1.0)
    for src, smul in srcs:
        for ror_bone, w in BONE_MAP[bb_bone]:
            v = src.at(ror_bone, chan, t)
            if v is None:
                continue
            got = True
            ww = w * smul
            if chan == 'rotation':
                total[0] += -v[0] * ww * g
                total[1] += v[1] * ww * g
                total[2] += -v[2] * ww * g
            elif chan == 'position':
                for k in range(3):
                    total[k] += v[k] * ww
            else:  # scale
                for k in range(3):
                    total[k] *= 1.0 + (v[k] - 1.0) * ww
    return total if got else None


# ---------------------------------------------------------------- compression

def compress(track, tol):
    """Supprime les points alignes (erreur < tol) en gardant les extremites."""
    if len(track) <= 2:
        return track
    keep = [0, len(track) - 1]
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
            d = 0.0 if t1 - t0 < 1e-9 else (t - t0) / (t1 - t0)
            for k in range(len(v)):
                e = abs(v[k] - (v0[k] + (v1[k] - v0[k]) * d))
                if e > worst:
                    worst, wi = e, i
        if worst > tol and wi > 0:
            keep.append(wi)
            stack.append((i0, wi))
            stack.append((wi, i1))
    keep = sorted(set(keep))
    return [track[i] for i in keep]


TOL = {'rotation': 0.06, 'position': 0.015, 'scale': 0.003}


def fmt(v):
    r = round(v, 6)
    return str(r if abs(r) > 1e-9 else 0.0)


def make_anim(name, length, loop, tracks, snapping=30):
    """tracks : {bb_bone: {chan: [(t, [x,y,z]), ...]}} -> animation bbmodel."""
    animators = {}
    for bone, chans in tracks.items():
        uid = GROUP_UUID[bone]
        kfs = []
        for chan in ('rotation', 'position', 'scale'):
            if chan not in chans:
                continue
            for t, v in chans[chan]:
                kfs.append({
                    'uuid': str(uuid.uuid5(NS, f'{name}|{bone}|{chan}|{t:.5f}')),
                    'channel': chan,
                    'time': round(t, 6),
                    'data_points': [{'x': fmt(v[0]), 'y': fmt(v[1]), 'z': fmt(v[2])}],
                    'interpolation': 'linear',
                })
        kfs.sort(key=lambda k: (k['time'], k['channel']))
        animators[uid] = {'name': bone, 'type': 'bone', 'keyframes': kfs}
    return {
        'uuid': str(uuid.uuid5(NS, 'anim|' + name)),
        'name': name,
        'loop': loop,
        'length': round(length, 6),
        'snapping': snapping,
        'override': False,
        'animators': animators,
    }
