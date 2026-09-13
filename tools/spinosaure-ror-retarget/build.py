import json, math, uuid, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retarget as R
import fk as FK

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BBPATH = os.path.join(W, 'modelzip', 'RIVIERE_70_ADAPTATION_ROR(1).bbmodel')

bb = json.load(open(BBPATH))
ror = json.load(open(os.path.join(W, 'ror_anims.json')))
R.GROUP_UUID = {g['name']: g['uuid'] for g in bb['groups']}


class Layer:
    """Une source ROR posee sur la timeline de l'animation cible."""
    def __init__(self, name, offset=0.0, scale=1.0, mul=1.0, only=None,
                 mode='add', window=None, fade=0.12, loop_src=False):
        self.src = R.Src(ror, name, offset=offset, scale=scale, loop_src=loop_src)
        self.mul, self.only, self.mode, self.fade = mul, only, mode, fade
        self.window = window or (offset, offset + ror[name]['length'] * scale)

    def weight(self, t):
        a, b = self.window
        if t < a - 1e-9 or t > b + 1e-9:
            return 0.0
        f = min(self.fade, (b - a) / 2.0)
        if f <= 1e-9:
            return 1.0
        return max(0.0, min(1.0, min(t - a, b - t) / f))


def evaluate(layers, bone, chan, t):
    g = R.GAIN.get(bone, 1.0)
    ax = R.AXIS.get(bone, (1.0, 1.0, 1.0))
    sg = R.SCALE_GAIN.get(bone, 1.0)
    acc = [0.0, 0.0, 0.0] if chan != 'scale' else [1.0, 1.0, 1.0]
    got = False
    # 1) couches additives
    for L in layers:
        if L.mode != 'add':
            continue
        for rb, w in R.BONE_MAP[bone]:
            if L.only is not None and rb not in L.only:
                continue
            v = L.src.at(rb, chan, t)
            if v is None:
                continue
            got = True
            ww = w * L.mul
            if chan == 'rotation':
                acc[0] += -v[0] * ww * g * ax[0]
                acc[1] += v[1] * ww * g * ax[1]
                acc[2] += -v[2] * ww * g * ax[2]
            elif chan == 'position':
                for k in range(3):
                    acc[k] += v[k] * ww
            else:
                for k in range(3):
                    acc[k] *= 1.0 + (v[k] - 1.0) * ww * sg
    # 2) couches de remplacement (avec fondu)
    for L in layers:
        if L.mode != 'replace':
            continue
        bw = L.weight(t)
        if bw <= 0:
            continue
        rep = [0.0, 0.0, 0.0] if chan != 'scale' else [1.0, 1.0, 1.0]
        hit = False
        for rb, w in R.BONE_MAP[bone]:
            if L.only is not None and rb not in L.only:
                continue
            v = L.src.at(rb, chan, t)
            if v is None:
                continue
            hit = True
            ww = w * L.mul
            if chan == 'rotation':
                rep[0] += -v[0] * ww * g * ax[0]
                rep[1] += v[1] * ww * g * ax[1]
                rep[2] += -v[2] * ww * g * ax[2]
            elif chan == 'position':
                for k in range(3):
                    rep[k] += v[k] * ww
            else:
                for k in range(3):
                    rep[k] *= 1.0 + (v[k] - 1.0) * ww * sg
        if hit:
            got = True
            acc = [acc[k] * (1 - bw) + rep[k] * bw for k in range(3)]
    if got and chan == 'rotation' and bone in R.LIMIT:
        lim = R.LIMIT[bone]
        acc = [max(-lim, min(lim, x)) for x in acc]
    return acc if got else None


def bake(layers, length, loop, bones=None, extra=None):
    """Echantillonne a 30 fps puis compresse. extra(bone, chan, t, base) -> override."""
    n = int(round(length * R.FPS))
    times = [i / R.FPS for i in range(n + 1)]
    times[-1] = length
    tracks = {}
    for bone in (bones or R.CORE):
        chans = {}
        for chan in ('rotation', 'position', 'scale'):
            raw = []
            any_val = False
            for t in times:
                v = evaluate(layers, bone, chan, t)
                if v is not None:
                    any_val = True
                if extra:
                    v = extra(bone, chan, t, v)
                if v is None:
                    v = [0.0, 0.0, 0.0] if chan != 'scale' else [1.0, 1.0, 1.0]
                    raw.append((t, v))
                else:
                    any_val = True
                    raw.append((t, list(v)))
            if not any_val:
                if chan != 'rotation':
                    continue
                raw = [(times[0], [0.0, 0.0, 0.0]), (times[-1], [0.0, 0.0, 0.0])]
            neutral = [0.0, 0.0, 0.0] if chan != 'scale' else [1.0, 1.0, 1.0]
            if all(max(abs(v[k] - neutral[k]) for k in range(3)) < 1e-6 for _, v in raw):
                if chan != 'rotation':
                    continue
                raw = [raw[0], raw[-1]]
            if loop:
                raw[-1] = (raw[-1][0], list(raw[0][1]))
            chans[chan] = R.compress(raw, R.TOL[chan])
        if chans:
            tracks[bone] = chans
    return tracks


# ------------------------------------------------------------------ couches maison

def sail_rework(tracks, length, loop, gain=0.55, lag=0.10, cap=13.0):
    """La voile traine sur le mouvement du tronc (inertie) puis se remet en place."""
    n = int(round(length * R.FPS))

    def chain(t):
        out = [0.0, 0.0, 0.0]
        for bone, w in (('body', 1.0), ('chest', 0.7), ('root', 0.5)):
            tr = tracks.get(bone, {}).get('rotation')
            if not tr:
                continue
            v = lerp_track(tr, t, length, loop)
            for k in range(3):
                out[k] += v[k] * w
        return out

    base = tracks.setdefault('sail', {}).get('rotation')
    out = []
    for i in range(n + 1):
        t = min(i / R.FPS, length)
        now, past = chain(t), chain(t - lag)
        v = lerp_track(base, t, length, loop) if base else [0.0, 0.0, 0.0]
        w = [v[k] + max(-cap, min(cap, (past[k] - now[k]) * gain * 3.0)) for k in range(3)]
        # la voile ne roule pas en x autant qu'elle ne balance en y/z
        w[0] *= 0.8
        out.append((t, w))
    if loop:
        out[-1] = (out[-1][0], list(out[0][1]))
    tracks['sail']['rotation'] = R.compress(out, R.TOL['rotation'])


def lerp_track(tr, t, length, loop):
    if not tr:
        return [0.0, 0.0, 0.0]
    if loop:
        t = t % length if length > 1e-9 else 0.0
    if t <= tr[0][0]:
        return list(tr[0][1])
    if t >= tr[-1][0]:
        return list(tr[-1][1])
    for i in range(len(tr) - 1):
        if tr[i + 1][0] >= t:
            a, b = tr[i], tr[i + 1]
            d = (t - a[0]) / (b[0] - a[0])
            return [a[1][k] + (b[1][k] - a[1][k]) * d for k in range(3)]
    return list(tr[-1][1])


def throat_vibe(tracks, length, loop, freq=6.0, amp=0.16, rot=3.5, env=None):
    """Flottement de la gorge : la poche gulaire vibre (grondement / halETement)."""
    n = int(round(length * R.FPS))
    ch = tracks.setdefault('throat', {})
    b_s = ch.get('scale')
    b_r = ch.get('rotation')
    b_p = ch.get('position')
    sc, rt, ps = [], [], []
    for i in range(n + 1):
        t = min(i / R.FPS, length)
        e = 1.0 if env is None else env(t)
        s = math.sin(2 * math.pi * freq * t)
        s2 = math.sin(2 * math.pi * freq * t + 0.6)
        slow = math.sin(2 * math.pi * (freq / 4.0) * t)
        bs = lerp_track(b_s, t, length, loop) if b_s else [1.0, 1.0, 1.0]
        br = lerp_track(b_r, t, length, loop) if b_r else [0.0, 0.0, 0.0]
        bp = lerp_track(b_p, t, length, loop) if b_p else [0.0, 0.0, 0.0]
        sc.append((t, [bs[0] * (1 + 0.35 * amp * e * s2),
                       bs[1] * (1 + amp * e * s + 0.05 * e * slow),
                       bs[2] * (1 + 0.5 * amp * e * s2)]))
        rt.append((t, [br[0] + rot * e * math.sin(2 * math.pi * freq * t + 1.2), br[1], br[2]]))
        ps.append((t, [bp[0], bp[1] - 0.55 * e * s, bp[2] + 0.35 * e * s2]))
    if loop:
        for arr in (sc, rt, ps):
            arr[-1] = (arr[-1][0], list(arr[0][1]))
    ch['scale'] = R.compress(sc, R.TOL['scale'])
    ch['rotation'] = R.compress(rt, R.TOL['rotation'])
    ch['position'] = R.compress(ps, R.TOL['position'])


def tongue_follow(tracks, length, loop, gain=0.28, lag=0.066):
    """La langue suit la machoire avec un temps de retard."""
    jaw = tracks.get('jaw', {}).get('rotation')
    if not jaw:
        return
    n = int(round(length * R.FPS))
    out = []
    for i in range(n + 1):
        t = min(i / R.FPS, length)
        v = lerp_track(jaw, t - lag, length, loop)
        out.append((t, [v[0] * gain, v[1] * gain * 0.5, v[2] * gain * 0.5]))
    if loop:
        out[-1] = (out[-1][0], list(out[0][1]))
    tr = R.compress(out, R.TOL['rotation'])
    if any(max(abs(x) for x in v) > 0.5 for _, v in tr):
        tracks['tongue'] = {'rotation': tr}


def tail_six(tracks, length, loop, gain=0.72, lag=0.066):
    """tail_06 prolonge tail_05 avec un leger retard (fouet de la queue)."""
    t5 = tracks.get('tail_05', {}).get('rotation')
    if not t5:
        return
    n = int(round(length * R.FPS))
    out = []
    for i in range(n + 1):
        t = min(i / R.FPS, length)
        v = lerp_track(t5, t - lag, length, loop)
        out.append((t, [x * gain for x in v]))
    if loop:
        out[-1] = (out[-1][0], list(out[0][1]))
    tracks.setdefault('tail_06', {})['rotation'] = R.compress(out, R.TOL['rotation'])


def tail_follow(tracks, length, loop, amp=0.55, base_lag=0.055, cap=11.0, factor=1.0):
    """Contre-mouvement retarde le long de la queue (inertie), en plus des donnees source."""
    n = int(round(length * R.FPS))

    def chain(t):
        out = [0.0, 0.0, 0.0]
        for bone, w in (('root', 1.0), ('body', 0.85)):
            tr = tracks.get(bone, {}).get('rotation')
            if not tr:
                continue
            v = lerp_track(tr, t, length, loop)
            for k in range(3):
                out[k] += v[k] * w
        return out

    for idx, bone in enumerate(['tail_01', 'tail_02', 'tail_03', 'tail_04', 'tail_05'], start=1):
        base = tracks.get(bone, {}).get('rotation')
        lag = base_lag * idx
        k = amp * (0.34 - 0.035 * idx) * factor
        out = []
        for i in range(n + 1):
            t = min(i / R.FPS, length)
            now, past = chain(t), chain(t - lag)
            b = lerp_track(base, t, length, loop) if base else [0.0, 0.0, 0.0]
            out.append((t, [b[j] + max(-cap, min(cap, (past[j] - now[j]) * k * 2.2)) for j in range(3)]))
        if loop:
            out[-1] = (out[-1][0], list(out[0][1]))
        tracks.setdefault(bone, {})['rotation'] = R.compress(out, R.TOL['rotation'])


RIG = None
FLOOR = None


def _ensure_rig():
    global RIG, FLOOR
    if RIG is None:
        RIG = FK.Rig(bb)
        rest = RIG.pose(lambda b, c: [1.0, 1.0, 1.0] if c == 'scale' else [0.0, 0.0, 0.0])
        FLOOR = RIG.lowest(rest)


def ground_clamp(tracks, length, loop, smooth=2):
    """Remonte le root pour qu'aucune piece ne passe sous le sol (jamais vers le bas)."""
    _ensure_rig()
    n = int(round(length * R.FPS))
    off = []
    for i in range(n + 1):
        t = min(i / R.FPS, length)
        def get(bone, chan, t=t):
            tr = tracks.get(bone, {}).get(chan)
            neutral = [1.0, 1.0, 1.0] if chan == 'scale' else [0.0, 0.0, 0.0]
            return lerp_track(tr, t, length, loop) if tr else neutral
        off.append(max(0.0, FLOOR - RIG.lowest(RIG.pose(get), skip=('tail_04', 'tail_05', 'tail_06'))))
    if smooth:
        sm = []
        for i in range(len(off)):
            a = max(0, i - smooth); b = min(len(off), i + smooth + 1)
            sm.append(max(off[i], sum(off[a:b]) / (b - a)))
        off = sm
    if loop:
        off[-1] = off[0]
    if max(off) < 0.2:
        return
    base = tracks.setdefault('root', {}).get('position')
    out = []
    for i in range(n + 1):
        t = min(i / R.FPS, length)
        b = lerp_track(base, t, length, loop) if base else [0.0, 0.0, 0.0]
        out.append((t, [b[0], b[1] + off[i], b[2]]))
    if loop:
        out[-1] = (out[-1][0], list(out[0][1]))
    tracks['root']['position'] = R.compress(out, R.TOL['position'])
    print('      calage sol : +%.1f max' % max(off))


TAILB = ['tail_01', 'tail_02', 'tail_03', 'tail_04', 'tail_05']


def finger_converge(tracks, length, loop, dmax=12.0):
    """Borne l'ecart de rotation entre doigts voisins.

    La palmure est un cube rigide : si deux doigts divergent, elle se decolle de
    l'un des deux. On conserve integralement le mouvement COMMUN des doigts et on
    ne resserre que leur ecartement relatif.
    """
    n = int(round(length * R.FPS))
    for side in ('left', 'right'):
        names = ['finger_%s_%d' % (side, i) for i in range(3)]
        trs = [tracks.get(nm, {}).get('rotation') for nm in names]
        if not any(trs):
            continue
        out = [[], [], []]
        for i in range(n + 1):
            t = min(i / R.FPS, length)
            v = [lerp_track(tr, t, length, loop) if tr else [0.0, 0.0, 0.0] for tr in trs]
            mean = [sum(v[k][j] for k in range(3)) / 3.0 for j in range(3)]
            d = max(math.dist(v[a], v[b]) for a, b in ((0, 1), (1, 2), (0, 2)))
            s = 1.0 if d <= dmax else dmax / d
            for k in range(3):
                out[k].append((t, [mean[j] + (v[k][j] - mean[j]) * s for j in range(3)]))
        for k, nm in enumerate(names):
            if loop:
                out[k][-1] = (out[k][-1][0], list(out[k][0][1]))
            tracks.setdefault(nm, {})['rotation'] = R.compress(out[k], R.TOL['rotation'])


def tail_min_y(tracks, length, loop):
    global RIG, FLOOR
    _ensure_rig()
    n = int(round(length * R.FPS))
    lo = 1e9
    for i in range(n + 1):
        t = min(i / R.FPS, length)
        def get(bone, chan, t=t):
            tr = tracks.get(bone, {}).get(chan)
            neutral = [1.0, 1.0, 1.0] if chan == 'scale' else [0.0, 0.0, 0.0]
            return lerp_track(tr, t, length, loop) if tr else neutral
        lo = min(lo, RIG.lowest(RIG.pose(get), only=('tail_04', 'tail_05', 'tail_06')))
    return lo


def tail_layers(tracks, length, loop, guard=True):
    """Inertie de queue + prolongement de tail_06, dose pour que la queue reste au-dessus du sol."""
    _ensure_rig()
    base = {b: list(tracks.get(b, {}).get('rotation') or []) for b in TAILB}

    def apply_f(f):
        for b in TAILB:
            if base[b]:
                tracks.setdefault(b, {})['rotation'] = [(t, list(v)) for t, v in base[b]]
            else:
                tracks.get(b, {}).pop('rotation', None)
        tail_follow(tracks, length, loop, factor=f)
        tail_six(tracks, length, loop, gain=0.72 * (0.35 + 0.65 * f))

    apply_f(1.0)
    if not guard or tail_min_y(tracks, length, loop) >= FLOOR + 1.0:
        return
    lo, hi = 0.0, 1.0
    for _ in range(6):
        mid = (lo + hi) / 2
        apply_f(mid)
        if tail_min_y(tracks, length, loop) >= FLOOR + 1.0:
            lo = mid
        else:
            hi = mid
    apply_f(lo)
    y = tail_min_y(tracks, length, loop)
    print('      queue : inertie a %.0f%% (bas de queue y=%.1f, sol %.1f)' % (lo * 100, y, FLOOR))


def add_root_curve(tracks, length, keys_pos=None, keys_rot=None):
    """Ajoute une courbe de deplacement au root (liste de (t,[x,y,z]), interpolation douce)."""
    def smooth(keys, t):
        if t <= keys[0][0]:
            return list(keys[0][1])
        if t >= keys[-1][0]:
            return list(keys[-1][1])
        for i in range(len(keys) - 1):
            if keys[i + 1][0] >= t:
                a, b = keys[i], keys[i + 1]
                d = (t - a[0]) / (b[0] - a[0])
                d = d * d * (3 - 2 * d)
                return [a[1][k] + (b[1][k] - a[1][k]) * d for k in range(3)]
        return list(keys[-1][1])

    n = int(round(length * R.FPS))
    ch = tracks.setdefault('root', {})
    for chan, keys in (('position', keys_pos), ('rotation', keys_rot)):
        if not keys:
            continue
        base = ch.get(chan)
        out = []
        for i in range(n + 1):
            t = min(i / R.FPS, length)
            b = lerp_track(base, t, length, False) if base else [0.0, 0.0, 0.0]
            s = smooth(keys, t)
            out.append((t, [b[k] + s[k] for k in range(3)]))
        ch[chan] = R.compress(out, R.TOL[chan])


# ================================================================== animations

ARMS_L = {'Arm3', 'Arm4', 'hand', 'finger', 'finger2', 'finger3'}
ARMS_R = {'Arm2', 'Arm5', 'hand2', 'finger4', 'finger5', 'finger6'}
TORSO  = {'Body', 'RotZ', 'Body2', 'torso', 'torso2', 'Neck', 'Neck2', 'Neck3', 'Neck4',
          'Head', 'shaker', 'shaker2', 'shaker3', 'shaker4', 'bone', 'jaw',
          'Tail', 'Tail2', 'Tail3', 'Tail4', 'Tail5'}

NEW = []


def add(name, length, loop, layers, post=None, snapping=30, clamp=False):
    tracks = bake(layers, length, loop)
    if post:
        post(tracks, length, loop)
    if clamp:
        ground_clamp(tracks, length, loop)
    tail_layers(tracks, length, loop, guard=clamp)
    finger_converge(tracks, length, loop)
    NEW.append(R.make_anim('animation.spinosaure.' + name, length, loop, tracks, snapping))
    nk = sum(len(v['keyframes']) for v in NEW[-1]['animators'].values())
    print('  %-34s len=%-7s loop=%-5s os=%-3d keyframes=%d' %
          (name, round(length, 3), loop, len(NEW[-1]['animators']), nk))


# --- 1. attaque plongeante dans l'eau : mace (elan) enchaine sur mace_air (impact)
def post_dive(tracks, length, loop):
    add_root_curve(
        tracks, length,
        keys_pos=[(0.0, [0, 0, 0]), (0.30, [0, -6, 3]), (0.55, [0, 8, -4]),
                  (0.85, [0, 34, -14]), (1.20, [0, 52, -26]), (1.45, [0, 55, -36]),
                  (1.667, [0, 44, -46]), (1.79, [0, -16, -62]), (1.95, [0, -22, -66]),
                  (2.20, [0, -13, -58]), (2.45, [0, -5, -30]), (2.667, [0, 0, 0])],
        keys_rot=[(0.0, [0, 0, 0]), (0.30, [-4, 0, 0]), (0.55, [8, 0, 0]),
                  (0.85, [20, 0, 0]), (1.20, [27, 0, 0]), (1.667, [14, 0, 0]),
                  (1.79, [-22, 0, 0]), (1.95, [-13, 0, 0]), (2.25, [-4, 0, 0]),
                  (2.667, [0, 0, 0])])
    sail_rework(tracks, length, loop, gain=0.32, lag=0.11, cap=7.0)
    # la gorge gonflee vibre pendant la tenue, puis s'ecrase a l'impact (donnees ROR)
    throat_vibe(tracks, length, loop, freq=5.0, amp=0.10, rot=2.5,
                env=lambda t: max(0.0, min(1.0, (t - 0.55) / 0.35)) * max(0.0, min(1.0, (1.70 - t) / 0.15)))


print('Construction des animations :')
add('attaque_saut_eau_ror', 2.6667, 'once',
    [Layer('mace', 0.0), Layer('mace_air', 1.6667)], post_dive)

# --- 2. variante au sol (mace_ground : le root est deja anime cote ROR)
def post_slam(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.32, lag=0.11, cap=7.0)
    throat_vibe(tracks, length, loop, freq=5.5, amp=0.09, rot=2.2,
                env=lambda t: max(0.0, min(1.0, (0.9 - t) / 0.3)))

add('attaque_saut_sol_ror', 1.75, 'once', [Layer('mace_ground', 0.0)], post_slam, clamp=True)

# --- 3. course ROR pure
def post_run(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.28, lag=0.09, cap=5.0)
    throat_vibe(tracks, length, loop, freq=6.0, amp=0.09, rot=2.0)

add('course_ror', 1.25, 'loop', [Layer('run', 0.0, loop_src=True)], post_run, clamp=True)

# --- 4. ruee griffes : deux foulees, coup de griffes gauche puis droit, gorge qui vibre
def post_rush(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.34, lag=0.10, cap=6.0)
    throat_vibe(tracks, length, loop, freq=6.0, amp=0.20, rot=4.5)

add('ruee_griffes_ror', 2.5, 'loop',
    [Layer('run', 0.0, scale=1.0, loop_src=True),
     # bras gauche : slash_left compresse sur la premiere foulee (remplace la course)
     Layer('slash_left', 0.05, scale=0.62, only=ARMS_L, mode='replace',
           window=(0.05, 1.29), fade=0.14),
     # bras droit : slash_right sur la seconde foulee
     Layer('slash_right', 1.30, scale=0.62, only=ARMS_R, mode='replace',
           window=(1.30, 2.54), fade=0.14),
     # torse et cou accompagnent le geste, en appui leger
     Layer('slash_left', 0.05, scale=0.62, mul=0.30, only=TORSO),
     Layer('slash_right', 1.30, scale=0.62, mul=0.30, only=TORSO)],
    post_rush, clamp=True)

# --- 5/6/7. coups de griffes
def post_slash(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.30, lag=0.10, cap=6.0)
    throat_vibe(tracks, length, loop, freq=5.5, amp=0.08, rot=2.0,
                env=lambda t: max(0.0, min(1.0, (t - 0.2) / 0.3)) * max(0.0, min(1.0, (length - 0.4 - t) / 0.4)))

add('coup_griffes_gauche_ror', 2.0, 'once', [Layer('slash_left', 0.0)], post_slash, clamp=True)
add('coup_griffes_droit_ror', 2.0, 'once', [Layer('slash_right', 0.0)], post_slash, clamp=True)
add('combo_griffes_ror', 4.0, 'once',
    [Layer('slash_left', 0.0), Layer('slash_left2', 2.0)], post_slash)

# --- 8..13. le reste du bestiaire ROR, garde a notre sauce
def post_calm(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.26, lag=0.12, cap=4.5)

def post_breath(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.26, lag=0.12, cap=4.5)
    throat_vibe(tracks, length, loop, freq=1.1, amp=0.10, rot=1.6)

add('se_couche_ror', 1.5, 'once', [Layer('down', 0.0)], post_calm, clamp=True)
add('se_releve_ror', 2.0, 'once', [Layer('raise', 0.0)], post_calm, clamp=True)
add('assis_ror', 4.0, 'loop', [Layer('sit', 0.0, loop_src=True)], post_breath, clamp=True)
add('renifle_piste_ror', 10.25, 'once', [Layer('scent', 0.0)], post_calm, clamp=True)
add('mange_ror', 2.0, 'once', [Layer('eat', 0.0)], post_calm, clamp=True)
add('nage_rapide_ror', 0.7519, 'loop', [Layer('swim2', 0.0, loop_src=True)], post_calm)


# ================================================================== animations maison
# Ecrites a la main a partir des animations existantes du modele (course, marche,
# repos), pas portees du jar : elles ne portent donc pas le suffixe _ror.

class Maison:
    """Lecture d'une animation deja presente dans le bbmodel, comme source."""

    def __init__(self, name):
        a = [x for x in bb['animations'] if x['name'].endswith(name)][0]
        self.length = a['length']
        self.t = {}
        for uid, an in a['animators'].items():
            d = {}
            for kf in an['keyframes']:
                d.setdefault(kf['channel'], []).append(
                    (kf['time'], [float(kf['data_points'][0].get(q, 0) or 0) for q in 'xyz']))
            for c in d:
                d[c].sort()
            self.t[an['name']] = d

    def at(self, bone, chan, t, loop=True):
        d = self.t.get(bone)
        if not d or chan not in d:
            return [1.0, 1.0, 1.0] if chan == 'scale' else [0.0, 0.0, 0.0]
        u = (t % self.length) if loop else max(0.0, min(self.length, t))
        return lerp_track(d[chan], u, self.length, False)

    def moyenne(self, bone, chan='rotation', n=60):
        v = [self.at(bone, chan, self.length * i / n) for i in range(n)]
        return [sum(x[k] for x in v) / n for k in range(3)]


def bake_fn(fn, length, loop, bones=None):
    """Cuit une fonction (os, canal, t) -> valeur, puis compresse."""
    n = int(round(length * R.FPS))
    tracks = {}
    for bone in (bones or R.CORE):
        chans = {}
        for chan in ('rotation', 'position', 'scale'):
            neutral = [1.0, 1.0, 1.0] if chan == 'scale' else [0.0, 0.0, 0.0]
            raw = []
            for i in range(n + 1):
                t = min(i / R.FPS, length)
                v = fn(bone, chan, t)
                raw.append((t, list(v if v is not None else neutral)))
            if all(max(abs(v[k] - neutral[k]) for k in range(3)) < 1e-6 for _, v in raw):
                if chan != 'rotation':
                    continue
                raw = [raw[0], raw[-1]]
            if loop:
                raw[-1] = (raw[-1][0], list(raw[0][1]))
            chans[chan] = R.compress(raw, R.TOL[chan])
        if chans:
            tracks[bone] = chans
    return tracks


def add_maison(name, length, loop, fn, post=None, clamp=True, bones=None):
    tracks = bake_fn(fn, length, loop, bones)
    if post:
        post(tracks, length, loop)
    if clamp:
        ground_clamp(tracks, length, loop)
    tail_layers(tracks, length, loop, guard=clamp)
    finger_converge(tracks, length, loop)
    NEW.append(R.make_anim('animation.spinosaure.' + name, length, loop, tracks, 30))
    nk = sum(len(v['keyframes']) for v in NEW[-1]['animators'].values())
    print('  %-34s len=%-7s loop=%-5s os=%-3d keyframes=%d' %
          (name, round(length, 3), loop, len(NEW[-1]['animators']), nk))


def ease(t, a, b):
    """Rampe lissee de 0 a 1 entre a et b."""
    if t <= a:
        return 0.0
    if t >= b:
        return 1.0
    d = (t - a) / (b - a)
    return d * d * (3 - 2 * d)


def bosse(t, a, b):
    """Cloche valant 1 au milieu de [a, b] et 0 aux bords."""
    if t <= a or t >= b:
        return 0.0
    return math.sin(math.pi * (t - a) / (b - a)) ** 2


print()
print('Animations maison :')

COURSE = Maison('course')
MARCHE = Maison('marche')
REPOS = Maison('repos')

# ---------------------------------------------------------------- 1 et 2. virages serres
# Convention verifiee sur le modele : rotation Y positive = le museau part vers la
# DROITE de l animal ; rotation Z negative = il se penche sur sa GAUCHE.
JAMBES = ('thigh_left', 'shin_left', 'foot_left', 'thigh_right', 'shin_right', 'foot_right')
MOY = {b: COURSE.moyenne(b) for b in JAMBES}


def virage(s):
    """s = -1 pour un virage a gauche, +1 pour un virage a droite."""
    def fn(bone, chan, t):
        v = list(COURSE.at(bone, chan, t))
        if chan == 'rotation':
            if bone in JAMBES:
                # la patte interieure raccourcit sa foulee, l exterieure l allonge
                interieur = bone.endswith('left') if s < 0 else bone.endswith('right')
                k = 0.70 if interieur else 1.18
                m = MOY[bone]
                v = [m[i] + (v[i] - m[i]) * k for i in range(3)]
            osc = math.sin(2 * math.pi * t / 1.25)
            if bone == 'root':
                v[1] += s * 7.0
                v[2] += s * -13.0 + osc * 1.5        # roulis dans le virage
            elif bone == 'body':
                v[1] += s * 8.0
                v[2] += s * -5.0
            elif bone == 'chest':
                v[1] += s * 6.0
            elif bone == 'neck':
                v[1] += s * 17.0
                v[0] += 3.0
            elif bone == 'head':
                v[1] += s * 11.0
                v[2] += s * -6.0
            elif bone.startswith('tail_'):
                # la queue part a l exterieur du virage, en contrepoids, de plus en
                # plus loin vers le bout
                i = int(bone[-2:])
                v[1] += -s * (3.0 + 2.6 * i)
                v[2] += -s * 1.2 * i
            elif bone.startswith('upper_arm'):
                v[1] += s * 6.0
        if chan == 'position' and bone == 'root':
            v[1] += -2.0                              # il s abaisse dans l appui
        return v
    return fn


def post_virage(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.34, lag=0.10, cap=6.0)
    throat_vibe(tracks, length, loop, freq=6.0, amp=0.14, rot=3.2)


add_maison('virage_serre_gauche', 1.25, 'loop', virage(-1), post_virage)
add_maison('virage_serre_droite', 1.25, 'loop', virage(+1), post_virage)

# ---------------------------------------------------------------- 3. marche en eau peu profonde
# On part de la marche maison, ralentie, et on ne majore le releve de patte QUE
# pendant la phase aerienne : la phase d appui reste intacte, donc le pied ne
# traverse pas le sol et ne flotte pas.
_rig_m = FK.Rig(bb)
_rest_m = _rig_m.pose(lambda b, c: [1.0, 1.0, 1.0] if c == 'scale' else [0.0, 0.0, 0.0])
_sol_m = _rig_m.lowest(_rest_m)


def hauteur_pieds(src, n=90):
    """Hauteur de chaque pied au fil du cycle, pour savoir quand il est en l air."""
    out = {'foot_left': [], 'foot_right': []}
    for i in range(n):
        t = src.length * i / n
        P = _rig_m.pose(lambda b, c: src.at(b, c, t))
        for s in out:
            u = _rig_m.byname[s]
            M, off, O = P[s]
            out[s].append(min(sum(M[1][k] * (p[k] - O[k]) for k in range(3)) + off[1]
                              for p in _rig_m.box[u]) - _sol_m)
    return out


_H = hauteur_pieds(MARCHE)
ETIRE = 2.4 / MARCHE.length


def en_lair(side, t):
    n = len(_H['foot_' + side])
    u = (t / ETIRE) % MARCHE.length
    h = _H['foot_' + side][int(u / MARCHE.length * n) % n]
    return max(0.0, min(1.0, h / 5.0))


def marche_eau(bone, chan, t):
    v = list(MARCHE.at(bone, chan, t / ETIRE))
    if chan == 'rotation':
        if bone.startswith(('thigh', 'shin', 'foot')):
            side = 'left' if bone.endswith('left') else 'right'
            w = en_lair(side, t)
            m = MOY_M.get(bone, [0, 0, 0])
            k = 1.0 + 0.80 * w                   # patte relevee plus haut hors de l eau
            v = [m[i] + (v[i] - m[i]) * k for i in range(3)]
            if bone.startswith('thigh'):
                v[0] -= 14.0 * w
            if bone.startswith('shin'):
                v[0] -= 20.0 * w
            if bone.startswith('foot'):
                v[0] += 16.0 * w
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[0] -= 1.4 + 0.48 * i               # queue relevee hors de l eau
        elif bone == 'neck':
            v[0] -= 4.0
            v[1] += 5.0 * math.sin(2 * math.pi * t / 4.8)
        elif bone == 'head':
            v[0] -= 3.0
            v[1] += 3.0 * math.sin(2 * math.pi * t / 4.8 + 0.8)
        elif bone == 'body':
            v[0] -= 2.0
    if chan == 'position' and bone == 'root':
        v[1] += 2.5 + 0.8 * math.sin(2 * math.pi * t / 2.4)
    return v


MOY_M = {b: MARCHE.moyenne(b) for b in JAMBES}


def post_eau(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.26, lag=0.12, cap=4.5)
    throat_vibe(tracks, length, loop, freq=1.3, amp=0.09, rot=1.8)


add_maison('marche_eau_peu_profonde', 2.4, 'loop', marche_eau, post_eau)

# ---------------------------------------------------------------- 5. ralentissement
# Une seule phase de foulee partagee entre course et marche : les appuis restent
# coherents pendant le fondu. La cadence decroit jusqu a l arret.
def cadence(t):
    if t < 0.45:
        return 1.25
    if t < 1.75:
        return 1.25 + (0.556 - 1.25) * ease(t, 0.45, 1.75)
    if t < 2.75:
        return 0.556 * (1 - ease(t, 1.75, 2.75))
    return 0.0


_PH = [0.0]
_TAB = []
_dt = 1.0 / R.FPS
_p = 0.0
for _i in range(int(3.4 * R.FPS) + 2):
    _TAB.append(_p)
    _p += _dt * cadence(_i * _dt)


def phase(t):
    i = min(len(_TAB) - 1, int(t * R.FPS))
    return _TAB[i]


def ralentir(bone, chan, t):
    wc = 1 - ease(t, 0.70, 1.75)
    wm = ease(t, 0.70, 1.75) * (1 - ease(t, 2.45, 3.05))
    wr = ease(t, 2.45, 3.05)
    tot = wc + wm + wr or 1.0
    ph = phase(t)
    c = COURSE.at(bone, chan, ph * COURSE.length)
    m = MARCHE.at(bone, chan, ph * MARCHE.length)
    r = REPOS.at(bone, chan, t * 0.5)
    v = [(c[k] * wc + m[k] * wm + r[k] * wr) / tot for k in range(3)]
    frein = bosse(t, 0.45, 2.20)
    if chan == 'rotation':
        if bone == 'root':
            v[0] += 9.0 * frein
        elif bone == 'body':
            v[0] += 7.0 * frein
        elif bone == 'neck':
            v[0] += 8.0 * frein
        elif bone == 'head':
            v[0] += 5.0 * frein
        elif bone.startswith('tail_'):
            v[0] -= (1.0 + 0.40 * int(bone[-2:])) * frein
        elif bone.startswith(('thigh', 'shin')):
            v[0] += -4.0 * frein
    elif chan == 'position' and bone == 'root':
        v[1] += -3.5 * frein
        v[2] += -5.0 * frein          # il glisse encore vers l avant en freinant
    return v


def post_ralentir(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.32, lag=0.11, cap=7.0)
    throat_vibe(tracks, length, loop, freq=5.5, amp=0.15, rot=3.5,
                env=lambda t: 1 - ease(t, 1.8, 3.0))


add_maison('ralentissement_course_arret', 3.4, 'once', ralentir, post_ralentir)


# ---------------------------------------------------------------- bond hors de l eau
# ROR n'a pas de bond hors de l eau : son clip mace/mace_air est un PLONGEON dans
# l eau (son entity.spino.dive_attack -> spino_hit_water). On reprend donc ses poses
# mais avec un arc de root qui part immerge et jaillit, comme le saut maison.
def post_bond(tracks, length, loop):
    add_root_curve(
        tracks, length,
        keys_pos=[(0.0, [0, -72, 0]), (0.30, [0, -88, 6]), (0.62, [0, -64, -4]),
                  (0.95, [0, -12, -16]), (1.25, [0, 34, -28]), (1.50, [0, 56, -38]),
                  (1.667, [0, 48, -46]), (1.85, [0, -26, -64]), (2.10, [0, -62, -68]),
                  (2.40, [0, -74, -46]), (2.667, [0, -72, 0])],
        keys_rot=[(0.0, [0, 0, 0]), (0.30, [-10, 0, 0]), (0.62, [12, 0, 0]),
                  (0.95, [28, 0, 0]), (1.25, [34, 0, 0]), (1.667, [16, 0, 0]),
                  (1.85, [-26, 0, 0]), (2.10, [-16, 0, 0]), (2.667, [0, 0, 0])])
    sail_rework(tracks, length, loop, gain=0.32, lag=0.11, cap=7.0)
    throat_vibe(tracks, length, loop, freq=5.0, amp=0.10, rot=2.5,
                env=lambda t: max(0.0, min(1.0, (t - 0.55) / 0.35)) * max(0.0, min(1.0, (1.70 - t) / 0.15)))


_L_BOND = [Layer('mace', 0.0), Layer('mace_air', 1.6667)]
_L_ROAR_NAGE = [Layer('roar_swim', 0.0)]


# deux clips aquatiques de ROR que le modele n a pas : la derive immobile en eau
# et le rugissement en nageant
def post_nage(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.22, lag=0.15, cap=4.0)
    throat_vibe(tracks, length, loop, freq=0.9, amp=0.12, rot=2.0)


add('nage_derive_ror', 3.0, 'loop', [Layer('swim_idle', 0.0, loop_src=True)], post_nage)


# ---------------------------------------------------------------- comportements immersifs
def _osc(t, f, ph=0.0):
    return math.sin(2 * math.pi * f * t + ph)


# 1. secouer l eau : onde de torsion qui remonte le corps, comme un chien mouille
# Version precedente : 7 Hz balayes vers 5, soit 4.3 images par cycle a 30 fps donc
# repliement de spectre, et des phases arbitraires sur Y et Z en meme temps -> ca
# tremblotait au lieu de s ebrouer. Ici une seule frequence a 4 Hz (7.5 images par
# cycle), un retard de phase croissant du tronc vers les extremites, et du Y presque
# pur : l onde se lit.
SEC_AMP = {'root': 4.0, 'body': 8.0, 'chest': 11.0, 'neck': 17.0, 'head': 23.0}
SEC_RET = {'root': -0.010, 'body': 0.0, 'chest': 0.015, 'neck': 0.035, 'head': 0.055}


def secoue_eau(bone, chan, t):
    v = list(REPOS.at(bone, chan, t * 0.35))
    env = ease(t, 0.15, 0.50) * (1 - ease(t, 1.75, 2.30))
    f = 4.0
    if chan == 'rotation':
        if bone in SEC_AMP:
            w = math.sin(2 * math.pi * f * (t - SEC_RET[bone]))
            v[1] += SEC_AMP[bone] * env * w
            if bone in ('root', 'body', 'chest'):
                v[2] += 0.35 * SEC_AMP[bone] * env * w
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[1] += (7.0 + 2.3 * i) * env * math.sin(2 * math.pi * f * (t - 0.020 - 0.018 * i))
        elif bone == 'jaw':
            v[0] += -7.0 * env
        elif bone.startswith('upper_arm'):
            v[1] += 8.0 * env * math.sin(2 * math.pi * f * (t - 0.030))
            v[0] += -6.0 * env
        elif bone.startswith(('thigh', 'shin')):
            v[2] += 3.5 * env * math.sin(2 * math.pi * f * (t - 0.005))
    elif chan == 'position' and bone == 'root':
        v[1] += 1.5 * env * abs(math.sin(2 * math.pi * f * t))
    return v


def post_secoue(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.40, lag=0.07, cap=11.0)
    throat_vibe(tracks, length, loop, freq=4.0, amp=0.16, rot=4.0,
                env=lambda t: ease(t, 0.15, 0.50) * (1 - ease(t, 1.75, 2.30)))


add_maison('secoue_eau', 2.4, 'once', secoue_eau, post_secoue)


# 2. affut : immerge, immobile, seuls la tete et la voile depassent
def affut(bone, chan, t):
    v = list(REPOS.at(bone, chan, t * 0.42))
    souffle = _osc(t, 1 / 6.0)
    guet = _osc(t, 1 / 3.0)
    if chan == 'rotation':
        if bone == 'root':
            v[0] += 5.0 + 1.2 * souffle
        elif bone == 'body':
            v[0] += 4.0
        elif bone == 'neck':
            # cou abaisse : il scrute la surface devant lui, pas le ciel
            v[0] += -11.0 + 1.2 * souffle
            v[1] += 7.0 * guet
        elif bone == 'head':
            v[0] += -7.0
            v[1] += 5.0 * guet + 1.6 * _osc(t, 1 / 1.7)
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[1] += (2.0 + 0.9 * i) * _osc(t, 1 / 4.0, -0.3 * i)
            v[0] -= 0.8 * i
        elif bone.startswith(('thigh', 'shin')):
            v[0] += 6.0 if bone.startswith('thigh') else -9.0
    elif chan == 'position' and bone == 'root':
        v[1] += -34.0 + 1.1 * souffle
    return v


def post_affut(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.20, lag=0.16, cap=3.0)
    throat_vibe(tracks, length, loop, freq=0.85, amp=0.13, rot=2.2)


add_maison('affut_eau', 6.0, 'loop', affut, post_affut, clamp=False)


# 3. secouer la proie : gueule fermee, secousses laterales violentes, puis avalee
def secoue_proie(bone, chan, t):
    v = list(REPOS.at(bone, chan, t * 0.4))
    env = bosse(t, 0.20, 1.95)
    f = 5.5
    leve = ease(t, 1.95, 2.35) * (1 - ease(t, 2.55, 2.8))
    if chan == 'rotation':
        if bone == 'root':
            v[2] += 6 * env * _osc(t, f, 0.2)
        elif bone == 'body':
            v[1] += -8 * env * _osc(t, f)
            v[0] += -6 * env
        elif bone == 'chest':
            v[1] += -6 * env * _osc(t, f, 0.15)
        elif bone == 'neck':
            v[1] += 24 * env * _osc(t, f, 0.35)
            v[0] += -14 * env + 22 * leve
        elif bone == 'head':
            v[1] += 29 * env * _osc(t, f, 0.55)
            v[2] += 16 * env * _osc(t, f, 1.1)
            v[0] += -9 * env + 18 * leve
        elif bone == 'jaw':
            v[0] += -3.0 - 2.0 * env - 20.0 * bosse(t, 2.35, 2.75)
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[1] += -(5 + 2.0 * i) * env * _osc(t, f, 0.3 + 0.18 * i)
        elif bone.startswith(('thigh', 'shin')):
            v[0] += (7 if bone.startswith('thigh') else -8) * env
    elif chan == 'position' and bone == 'root':
        v[2] += -3.0 * env
    return v


def post_proie(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.38, lag=0.08, cap=9.0)
    throat_vibe(tracks, length, loop, freq=5.0, amp=0.24, rot=5.5,
                env=lambda t: ease(t, 2.30, 2.55) * (1 - ease(t, 2.75, 3.0)))


add_maison('secoue_proie', 3.0, 'once', secoue_proie, post_proie)


# 6. coup de queue sur l eau
def frappe_queue(bone, chan, t):
    v = list(REPOS.at(bone, chan, t * 0.4))
    arme = ease(t, 0.10, 0.70) * (1 - ease(t, 0.70, 0.88))
    frappe = ease(t, 0.72, 0.92) * (1 - ease(t, 1.05, 1.75))
    if chan == 'rotation':
        if bone.startswith('tail_'):
            i = int(bone[-2:])
            v[0] += -(3.0 + 2.8 * i) * arme + (2.6 + 2.4 * i) * frappe
            v[1] += (2.0 + 1.8 * i) * arme - (1.6 + 1.4 * i) * frappe
        elif bone == 'root':
            v[0] += 4.0 * arme - 3.0 * frappe
            v[2] += -3.0 * arme + 2.5 * frappe
        elif bone == 'body':
            v[0] += 5.0 * arme - 4.0 * frappe
        elif bone == 'neck':
            v[0] += -6.0 * arme + 5.0 * frappe
        elif bone == 'head':
            v[1] += 9.0 * arme
        elif bone.startswith(('thigh', 'shin')):
            v[0] += (5.0 if bone.startswith('thigh') else -6.0) * (arme + frappe) * 0.5
    elif chan == 'position' and bone == 'root':
        v[1] += -2.0 * frappe
    return v


def post_frappe(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.36, lag=0.09, cap=8.0)


add_maison('frappe_queue_eau', 1.9, 'once', frappe_queue, post_frappe)


# 7. marche en boitant : l appui droit est ecourte et le corps s affaisse dessus
def boite(bone, chan, t):
    k = 2.4 / MARCHE.length
    v = list(MARCHE.at(bone, chan, t / k))
    ph = (t / 2.4) % 1.0
    douleur = max(0.0, math.sin(2 * math.pi * ph))     # phase d appui du cote droit
    if chan == 'rotation':
        if bone.endswith('right') and bone.startswith(('thigh', 'shin', 'foot')):
            m = MOY_M[bone]
            v = [m[i] + (v[i] - m[i]) * 0.38 for i in range(3)]
            if bone.startswith('shin'):
                v[0] += -17.0 * douleur
            if bone.startswith('thigh'):
                v[0] += 9.0 * douleur
        elif bone.endswith('left') and bone.startswith(('thigh', 'shin')):
            m = MOY_M[bone]
            v = [m[i] + (v[i] - m[i]) * 1.20 for i in range(3)]
        elif bone == 'root':
            v[2] += 12.0 * douleur
            v[0] += 5.0 * douleur
        elif bone == 'body':
            v[2] += 8.0 * douleur
            v[0] += 3.0 * douleur
        elif bone == 'neck':
            v[0] += 13.0 * douleur - 4.0
            v[2] += -6.0 * douleur
        elif bone == 'head':
            v[0] += 9.0 * douleur
        elif bone.startswith('tail_'):
            v[0] -= 0.8 * int(bone[-2:]) * douleur
    elif chan == 'position' and bone == 'root':
        v[1] += -7.5 * douleur
    return v


def post_boite(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.28, lag=0.12, cap=5.0)
    throat_vibe(tracks, length, loop, freq=1.6, amp=0.11, rot=2.0)


add_maison('marche_boiteuse', 2.4, 'loop', boite, post_boite)


# ---------------------------------------------------------------- corrections aquatiques
# Le clip roar_swim de ROR n'anime que machoire, tete, cou et gorge, et mace_air se termine
# en pose de repos : portes tels quels, le spino rugit debout et retombe debout. On glisse
# donc dessous la posture de nage du modele.
NAGE = Maison('nage_surface')


def _melange(base, sup, chan, w):
    if chan == 'scale':
        return [base[k] * (1 - w) + sup[k] * w for k in range(3)]
    return [base[k] * (1 - w) + sup[k] * w for k in range(3)]


def rugit_nage(bone, chan, t):
    nage = list(NAGE.at(bone, chan, t))
    cri = evaluate(_L_ROAR_NAGE, bone, chan, t)
    if cri is None:
        return nage
    if chan == 'scale':
        return [nage[k] * cri[k] for k in range(3)]
    return [nage[k] + cri[k] for k in range(3)]


add_maison('rugit_en_nageant_ror', 3.0, 'once', rugit_nage, post_nage, clamp=False)


def bond_hors_eau(bone, chan, t):
    v = evaluate(_L_BOND, bone, chan, t)
    if v is None:
        v = [1.0, 1.0, 1.0] if chan == 'scale' else [0.0, 0.0, 0.0]
    nage = NAGE.at(bone, chan, t)
    # il part en nageant et retombe en nageant : la pose de repos n a rien a faire la
    w = max(1 - ease(t, 0.0, 0.45), ease(t, 1.95, 2.55))
    return _melange(v, nage, chan, w)


add_maison('bond_hors_eau_ror', 2.6667, 'once', bond_hors_eau, post_bond, clamp=False)


# ---------------------------------------------------------------- peche : une seule frappe
T_GUET, T_FRAPPE, T_PRISE, T_AVALE = 1.30, 1.55, 1.95, 2.45


def peche(bone, chan, t):
    v = list(REPOS.at(bone, chan, t * 0.5))
    if chan == 'scale':
        return v
    guet = 1 - ease(t, T_GUET, T_FRAPPE)
    plonge = bosse(t, T_GUET, T_PRISE)
    releve = ease(t, T_PRISE, T_AVALE) * (1 - ease(t, 3.05, 3.55))
    avale = ease(t, T_AVALE, 2.80) * (1 - ease(t, 3.15, 3.55))
    balayage = math.sin(2 * math.pi * t / 2.1)
    if chan == 'rotation':
        if bone == 'root':
            v[0] += -7.0 * plonge + 3.0 * releve
        elif bone == 'body':
            v[0] += -13.0 * plonge + 4.0 * releve
            v[2] += 3.0 * balayage * guet
        elif bone == 'chest':
            v[0] += -7.0 * plonge
        elif bone == 'neck':
            v[0] += -14.0 * guet - 26.0 * plonge + 24.0 * releve
            v[1] += 13.0 * balayage * guet
        elif bone == 'head':
            v[0] += -10.0 * guet - 13.0 * plonge + 19.0 * releve + 24.0 * avale
            v[1] += 8.0 * balayage * guet
        elif bone == 'jaw':
            ouvre = ease(t, T_GUET, T_FRAPPE) * (1 - ease(t, T_FRAPPE, T_FRAPPE + 0.10))
            v[0] += -34.0 * ouvre - 8.0 * guet - 12.0 * bosse(t, T_AVALE, 3.15)
        elif bone.startswith('thigh'):
            v[0] += 5.0 * plonge
        elif bone.startswith('shin'):
            v[0] += -6.0 * plonge
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[0] -= (1.6 + 0.55 * i) * plonge - (0.5 + 0.22 * i) * releve
            v[1] += -6.0 * balayage * guet * (0.4 + 0.12 * i)
        elif bone.startswith('upper_arm'):
            v[0] += -8.0 * plonge
    elif chan == 'position' and bone == 'root':
        v[1] += -4.5 * plonge
        v[2] += -21.0 * plonge
    return v


def post_peche(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.30, lag=0.11, cap=6.0)
    throat_vibe(tracks, length, loop, freq=4.5, amp=0.22, rot=5.0,
                env=lambda t: ease(t, T_AVALE, 2.85) * (1 - ease(t, 3.25, 3.60))) 


add_maison('peche_gueule_eau', 3.6, 'once', peche, post_peche)


# ---------------------------------------------------------------- manger une carcasse
# Deux bouchees au sol : saisie, arrachement lateral, redressement, deglutition.
def mange(bone, chan, t):
    v = list(REPOS.at(bone, chan, t * 0.35))
    if chan == 'scale':
        return v
    bas = 0.0
    arrache = 0.0
    haut = 0.0
    for d in (0.0, 2.70):
        bas = max(bas, ease(t, 0.30 + d, 0.85 + d) * (1 - ease(t, 1.55 + d, 1.95 + d)))
        arrache = max(arrache, bosse(t, 1.05 + d, 1.75 + d))
        haut = max(haut, ease(t, 1.80 + d, 2.15 + d) * (1 - ease(t, 2.50 + d, 2.80 + d)))
    sec = math.sin(2 * math.pi * 4.0 * t)
    if chan == 'rotation':
        if bone == 'root':
            v[0] += -6.0 * bas + 5.0 * haut
        elif bone == 'body':
            v[0] += -11.0 * bas + 7.0 * haut + 3.0 * arrache
        elif bone == 'chest':
            v[0] += -6.0 * bas + 4.0 * haut
        elif bone == 'neck':
            v[0] += -30.0 * bas + 26.0 * haut
            v[1] += 11.0 * arrache * sec
        elif bone == 'head':
            v[0] += -18.0 * bas + 22.0 * haut
            v[1] += 15.0 * arrache * sec
            v[2] += 9.0 * arrache * sec
        elif bone == 'jaw':
            ouvre = 0.0
            for d in (0.0, 2.70):
                ouvre = max(ouvre, ease(t, 0.35 + d, 0.80 + d) * (1 - ease(t, 0.85 + d, 1.00 + d)))
                ouvre = max(ouvre, 0.55 * bosse(t, 2.15 + d, 2.55 + d))
            v[0] += -38.0 * ouvre - 4.0 * arrache
        elif bone.startswith('thigh'):
            v[0] += 7.0 * bas
        elif bone.startswith('shin'):
            v[0] += -8.0 * bas
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[0] -= (1.4 + 0.5 * i) * bas
            v[1] += -4.0 * arrache * sec * (0.3 + 0.1 * i)
        elif bone.startswith('upper_arm'):
            v[0] += -10.0 * bas
    elif chan == 'position' and bone == 'root':
        v[1] += -5.0 * bas
        v[2] += -7.0 * bas + 4.0 * arrache


    return v


def post_mange(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.30, lag=0.11, cap=6.0)
    throat_vibe(tracks, length, loop, freq=3.5, amp=0.24, rot=5.5,
                env=lambda t: max(ease(t, 1.85, 2.20) * (1 - ease(t, 2.55, 2.85)),
                                  ease(t, 4.55, 4.90) * (1 - ease(t, 5.25, 5.55))))


add_maison('mange_carcasse', 5.8, 'once', mange, post_mange)


# ================================================================== ecriture
existing = {a['name'] for a in bb['animations']}
for a in NEW:
    assert a['name'] not in existing, a['name']
bb['animations'].extend(NEW)
bb['name'] = 'RIVIERE_70_ADAPTATION_ROR_UPDATED'
bb['credit'] = ('V41 - texture et yeux JP3 affines; animation grimpe reconstruite; squelette et '
                'autres animations preserves | V70u - 13 animations portees depuis Raxio ROR '
                '(spino_basic/more/mace, avec accord de l auteur) et retargetees sur le rig RIVIERE : '
                'attaque plongeante, ruee griffes, voile reajustee, vibration de la gorge')
out = os.path.join(W, 'RIVIERE_70_ADAPTATION_ROR_UPDATED.bbmodel')
json.dump(bb, open(out, 'w'), separators=(',', ':'))
print('\nEcrit :', out, round(os.path.getsize(out) / 1e6, 1), 'Mo',
      '| total animations =', len(bb['animations']))
