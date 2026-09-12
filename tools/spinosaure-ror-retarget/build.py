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
    tongue_follow(tracks, length, loop)
    finger_converge(tracks, length, loop)
    NEW.append(R.make_anim('animation.spinosaure.' + name, length, loop, tracks, snapping))
    nk = sum(len(v['keyframes']) for v in NEW[-1]['animators'].values())
    print('  %-34s len=%-7s loop=%-5s os=%-3d keyframes=%d' %
          (name, round(length, 3), loop, len(NEW[-1]['animators']), nk))


# --- 1. attaque plongeante dans l'eau : mace (elan) enchaine sur mace_air (impact)
def post_dive(tracks, length, loop):
    add_root_curve(
        tracks, length,
        keys_pos=[(0.0, [0, 0, 0]), (0.35, [0, 3, 2]), (0.80, [0, 15, -6]),
                  (1.20, [0, 26, -16]), (1.667, [0, 21, -26]), (1.79, [0, -14, -40]),
                  (1.95, [0, -18, -43]), (2.20, [0, -11, -37]), (2.45, [0, -5, -22]),
                  (2.667, [0, 0, 0])],
        keys_rot=[(0.0, [0, 0, 0]), (0.35, [5, 0, 0]), (0.80, [14, 0, 0]),
                  (1.20, [19, 0, 0]), (1.667, [11, 0, 0]), (1.79, [-16, 0, 0]),
                  (1.95, [-10, 0, 0]), (2.25, [-3, 0, 0]), (2.667, [0, 0, 0])])
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
