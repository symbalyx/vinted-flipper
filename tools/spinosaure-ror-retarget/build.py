import json, math, uuid, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retarget as R
import fk as FK

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BBPATH = os.path.join(W, 'modelzip', 'RIVIERE_70_ADAPTATION_ROR(1).bbmodel')

bb = json.load(open(BBPATH))
ror = json.load(open(os.path.join(W, 'ror_anims.json')))
R.GROUP_UUID = {g['name']: g['uuid'] for g in bb['groups']}


# (lissage des animations d origine retire : leur valeur est continue a la couture,
#  l a-coup de cheville de `course` est un geste en V, pas un raccord casse)


def boucle(loop):
    """Vrai seulement pour une VRAIE boucle.

    Piege corrige ici : `loop` est une chaine ('once', 'hold', 'loop'), et toute
    chaine non vide est vraie en Python. Un simple `if loop:` refermait donc la
    derniere cle sur la premiere y compris pour les animations jouees une seule
    fois, ce qui produisait un saut d une image en fin d animation (jusqu a 58.8
    degres mesures sur la main de se_couche_ror).
    """
    return loop == 'loop'


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
            if boucle(loop):
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
    if boucle(loop):
        out[-1] = (out[-1][0], list(out[0][1]))
    tracks['sail']['rotation'] = R.compress(out, R.TOL['rotation'])


def lerp_track(tr, t, length, loop):
    if not tr:
        return [0.0, 0.0, 0.0]
    if boucle(loop):
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
    if boucle(loop):
        # nombre ENTIER de cycles par boucle (y compris la composante lente freq/4),
        # sinon la vibration casse a chaque tour
        freq = max(4, int(round(freq * length / 4.0)) * 4) / length
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
    if boucle(loop):
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
    if boucle(loop):
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
    if boucle(loop):
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
        if boucle(loop):
            out[-1] = (out[-1][0], list(out[0][1]))
        tracks.setdefault(bone, {})['rotation'] = R.compress(out, R.TOL['rotation'])


RIG = None
FLOOR = None


def _geometrie_finale():
    """Copie du modele avec la geometrie que le livrable aura REELLEMENT.

    build.py tourne AVANT le pipeline (voile, bras grossis, griffes allongees,
    nageoires). Caler les animations sur le rig d avant, c est les caler sur des
    bras plus courts que ceux livres : mesure faite sur embuscade_jaillissement,
    la griffe gauche frolait le sol a -62.7 avant le pipeline et le traversait de
    3.8 unites apres. On applique donc ici les memes transformations, en memoire,
    pour que ground_clamp et le garde-fou de queue voient la bonne geometrie.
    """
    import copy, grossir_bras, bras_ror, corps, nageoires
    g = copy.deepcopy(bb)
    grossir_bras.grossir(g)
    bras_ror.add(g)
    corps.remodele(g)          # meme ordre que pipeline.sh : queue et pattes AVANT nageoires
    nageoires.ajoute(g)
    return g


def _ensure_rig():
    global RIG, FLOOR
    if RIG is None:
        RIG = FK.Rig(_geometrie_finale())
        rest = RIG.pose(lambda b, c: [1.0, 1.0, 1.0] if c == 'scale' else [0.0, 0.0, 0.0])
        FLOOR = RIG.lowest(rest)


def ground_clamp(tracks, length, loop, smooth=2, skip=('tail_04', 'tail_05', 'tail_06')):
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
        off.append(max(0.0, FLOOR - RIG.lowest(RIG.pose(get), skip=skip)))
    if smooth:
        sm = []
        for i in range(len(off)):
            a = max(0, i - smooth); b = min(len(off), i + smooth + 1)
            sm.append(max(off[i], sum(off[a:b]) / (b - a)))
        off = sm
    if boucle(loop):
        off[-1] = off[0]
    if max(off) < 0.2:
        return
    base = tracks.setdefault('root', {}).get('position')
    out = []
    for i in range(n + 1):
        t = min(i / R.FPS, length)
        b = lerp_track(base, t, length, loop) if base else [0.0, 0.0, 0.0]
        out.append((t, [b[0], b[1] + off[i], b[2]]))
    if boucle(loop):
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
            if boucle(loop):
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
        lo = min(lo, RIG.lowest(RIG.pose(get), only=tuple(TAILB + ['tail_06'])))
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
    if y < FLOOR + 1.0:
        queue_hors_sol(tracks, length, loop)


def queue_hors_sol(tracks, length, loop, pas=0.6, maxi=40):
    """Redresse la queue jusqu a ce qu elle ne traverse plus le sol.

    tail_layers ne sait que doser l INERTIE ; quand c est la pose de base qui plonge
    (mange_carcasse : le root descend de 5 pour mordre au sol, la queue suit), ramener
    l inertie a zero ne suffit pas. On ajoute donc un redressement progressif reparti
    le long de la queue, dose par increments jusqu au degagement. Mesure : positif en
    X fait DESCENDRE la pointe, on retranche donc.
    """
    _ensure_rig()
    n = int(round(length * R.FPS))
    base = {b: list(tracks.get(b, {}).get('rotation') or []) for b in TAILB + ['tail_06']}
    for k in range(1, maxi + 1):
        for idx, b in enumerate(TAILB + ['tail_06'], start=1):
            src = base[b]
            out = []
            for i in range(n + 1):
                t = min(i / R.FPS, length)
                v = lerp_track(src, t, length, loop) if src else [0.0, 0.0, 0.0]
                out.append((t, [v[0] - pas * k * (0.35 + 0.14 * idx), v[1], v[2]]))
            if boucle(loop):
                out[-1] = (out[-1][0], list(out[0][1]))
            tracks.setdefault(b, {})['rotation'] = R.compress(out, R.TOL['rotation'])
        if tail_min_y(tracks, length, loop) >= FLOOR + 1.0:
            print('      queue redressee de %.1f deg a la pointe' % (pas * k * (0.35 + 0.14 * 6)))
            return
    print('      queue : degagement incomplet apres %d paliers' % maxi)


def pose_au_sol(tracks, length, loop, marge=0.15):
    """Descend le root pour que le pied touche REELLEMENT le sol.

    ground_clamp ne sait que remonter : il empeche de traverser mais laisse flotter.
    Le repliement d accroupissement etant calibre sur la pose de repos, il ne rend pas
    exactement la meme hauteur sur une jambe deja flechie par le cycle de marche
    (1.5 unite de flottement mesuree sur marche_feutree). On mesure donc le jeu reel
    et on le retranche, d un decalage CONSTANT qui preserve le mouvement vertical.
    """
    _ensure_rig()
    n = int(round(length * R.FPS))
    jeu = 1e9
    for i in range(n + 1):
        t = min(i / R.FPS, length)

        def get(bone, chan, t=t):
            tr = tracks.get(bone, {}).get(chan)
            neutral = [1.0, 1.0, 1.0] if chan == 'scale' else [0.0, 0.0, 0.0]
            return lerp_track(tr, t, length, loop) if tr else neutral
        jeu = min(jeu, RIG.lowest(RIG.pose(get), only=('foot_left', 'foot_right')) - FLOOR)
    if jeu <= marge:
        return
    base = tracks.setdefault('root', {}).get('position')
    out = []
    for i in range(n + 1):
        t = min(i / R.FPS, length)
        b = lerp_track(base, t, length, loop) if base else [0.0, 0.0, 0.0]
        out.append((t, [b[0], b[1] - jeu, b[2]]))
    if boucle(loop):
        out[-1] = (out[-1][0], list(out[0][1]))
    tracks['root']['position'] = R.compress(out, R.TOL['position'])
    print('      pose au sol : -%.1f (le pied flottait)' % jeu)


def pieds_plantes(tracks, length, loop, seuil=0.6):
    """Empeche le pied POSE de glisser lateralement.

    Un roulis ou un lacet du bassin pivote tout le corps autour de lui, et les pieds
    posés balaient le sol : 11 unites de glissement lateral par cycle mesurees sur les
    virages, 10.4 sur la boiterie. On deplace donc le bassin en X pour ramener chaque
    pied posé a sa position moyenne d appui : le corps se balance AU-DESSUS du pied qui
    porte, comme il le doit. Correction lissee et rendue periodique.
    """
    _ensure_rig()
    n = int(round(length * R.FPS))
    ts = [min(i / R.FPS, length) for i in range(n + 1)]

    def pose(t):
        def g(bone, chan):
            tr = tracks.get(bone, {}).get(chan)
            neutral = [1.0, 1.0, 1.0] if chan == 'scale' else [0.0, 0.0, 0.0]
            return lerp_track(tr, t, length, loop) if tr else neutral
        return RIG.pose(g)
    donnees = []
    for t in ts:
        P = pose(t)
        donnees.append({s: (RIG.lowest(P, only=(s,)) - FLOOR, P[s][1][0]) for s in ('foot_left', 'foot_right')})
    moy = {}
    for s in ('foot_left', 'foot_right'):
        xs = [d[s][1] for d in donnees if d[s][0] < seuil]
        moy[s] = sum(xs) / len(xs) if xs else None
    c = []
    for d in donnees:
        ecarts = [d[s][1] - moy[s] for s in d if d[s][0] < seuil and moy[s] is not None]
        c.append(-sum(ecarts) / len(ecarts) if ecarts else None)
    if all(x is None for x in c):
        return
    # trous (phases de vol) : interpolation lineaire, cyclique pour une boucle
    idx = [i for i, x in enumerate(c) if x is not None]
    for i in range(len(c)):
        if c[i] is None:
            a = max([j for j in idx if j < i], default=idx[-1] - len(c))
            b = min([j for j in idx if j > i], default=idx[0] + len(c))
            ca, cb = c[a % len(c)], c[b % len(c)]
            f = (i - a) / (b - a) if b != a else 0
            c[i] = ca + (cb - ca) * f
    if boucle(loop):
        c[-1] = c[0]
    lisse = []
    for i in range(len(c)):
        fen = [c[(i + k) % (len(c) - 1)] if boucle(loop) else c[min(max(i + k, 0), len(c) - 1)] for k in range(-1, 2)]
        lisse.append(sum(fen) / len(fen))
    if boucle(loop):
        lisse[-1] = lisse[0]
    base = tracks.setdefault('root', {}).get('position')
    out = []
    for i, t in enumerate(ts):
        v = lerp_track(base, t, length, loop) if base else [0.0, 0.0, 0.0]
        out.append((t, [v[0] + lisse[i], v[1], v[2]]))
    tracks['root']['position'] = R.compress(out, R.TOL['position'])
    print('      pieds plantes : bassin deplace de %.1f a %+.1f en X' % (min(lisse), max(lisse)))


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
    # le clip ROR ecrase la poche gulaire au decollage : meme attenuee, elle tombait a
    # 36 % de sa taille pendant 3 images, soit une gorge qui disparait. Bornee a 60 %.
    sc = tracks.get('throat', {}).get('scale')
    if sc:
        tracks['throat']['scale'] = [(t, [max(0.6, min(1.6, x)) for x in v]) for t, v in sc]

add('attaque_saut_sol_ror', 1.75, 'once', [Layer('mace_ground', 0.0)], post_slam, clamp=True)

# --- 3. course ROR pure
def post_run(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.28, lag=0.09, cap=5.0)
    throat_vibe(tracks, length, loop, freq=6.0, amp=0.09, rot=2.0)

# course_ror : ajoutee plus bas, apres COURSE, pour lui greffer des jambes saines


# --- 4. ruee griffes : deux foulees, coup de griffes gauche puis droit, gorge qui vibre
def post_rush(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.34, lag=0.10, cap=6.0)
    throat_vibe(tracks, length, loop, freq=6.0, amp=0.20, rot=4.5)

# ruee_griffes_ror : ajoutee plus bas, meme raison


# --- 5/6/7. coups de griffes
def post_slash(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.30, lag=0.10, cap=6.0)
    throat_vibe(tracks, length, loop, freq=5.5, amp=0.08, rot=2.0,
                env=lambda t: max(0.0, min(1.0, (t - 0.2) / 0.3)) * max(0.0, min(1.0, (length - 0.4 - t) / 0.4)))

add('coup_griffes_gauche_ror', 2.0, 'once', [Layer('slash_left', 0.0)], post_slash, clamp=True)
add('coup_griffes_droit_ror', 2.0, 'once', [Layer('slash_right', 0.0)], post_slash, clamp=True)
# combo_griffes_ror retiree (V81) : deux coups du MEME bras, couverts par coup_griffes_gauche_ror
# joue deux fois et par coup_griffes_double

# --- 8..13. le reste du bestiaire ROR, garde a notre sauce
def post_calm(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.26, lag=0.12, cap=4.5)

def post_breath(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.26, lag=0.12, cap=4.5)
    throat_vibe(tracks, length, loop, freq=1.1, amp=0.10, rot=1.6)

# se_couche_ror, se_releve_ror, assis_ror : reconstruites plus bas (voir 'postures ROR')
# renifle_piste_ror retiree (V81) : flair AERIEN malgre son nom (crane 103 -> 113),
# couvert par renifle_air (air) et renifle_piste_sol (museau a terre)
# mange_ror retiree (V81) : simple hochement de tete, entierement couvert par mange_carcasse
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


def periodique(fn, length, fondu):
    """Rend une boucle reellement periodique.

    Sur les `fondu` dernieres secondes, la fonction se fond dans sa propre continuation
    depuis le debut, f(t - length). Le poids suit une courbe en S (pente nulle aux deux
    bouts) : valeur ET vitesse se raccordent a la couture. Sans cela, tout oscillateur
    dont la periode ne divise pas la duree de la boucle laissait un saut que bake_fn
    cachait en forcant la derniere cle egale a la premiere : 57 degres en une demi-image
    sur la patte de virage_serre_droite, 15 sur la queue d affut_eau.
    """
    def g(bone, chan, t):
        w = ease(t, length - fondu, length)
        a = fn(bone, chan, t)
        if w <= 0.0 or a is None:
            return a
        b = fn(bone, chan, t - length)
        if b is None:
            return a
        return [a[k] * (1 - w) + b[k] * w for k in range(3)]
    return g


def bake_fn(fn, length, loop, bones=None):
    """Cuit une fonction (os, canal, t) -> valeur, puis compresse."""
    if boucle(loop):
        fn = periodique(fn, length, min(0.45, length / 4.0))
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
            if boucle(loop):
                raw[-1] = (raw[-1][0], list(raw[0][1]))
            chans[chan] = R.compress(raw, R.TOL[chan])
        if chans:
            tracks[bone] = chans
    return tracks


def add_maison(name, length, loop, fn, post=None, clamp=True, bones=None, sol=False,
               clamp_skip=('tail_04', 'tail_05', 'tail_06'), plante=False):
    tracks = bake_fn(fn, length, loop, bones)
    if post:
        post(tracks, length, loop)
    if clamp:
        ground_clamp(tracks, length, loop, skip=clamp_skip)
    if sol:
        # apres ground_clamp : c est lui qui peut laisser le pied en l air
        pose_au_sol(tracks, length, loop)
    if plante:
        # une seule passe : une seconde a ete essayee, elle degrade la boiterie (5.1 -> 6.5)
        pieds_plantes(tracks, length, loop)
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

# ---------------------------------------------------------------- jambes des courses ROR
# Mesure qui a fait tomber le portage d origine : sur course_ror, le pied posé AVANCAIT
# de 4.4 unites par image (moonwalk) et reculait en l air, et le genou ne pliait plus
# (tibia a -1 degre en vol, contre -35 sur la course du modele). Cause : la patte ROR
# est digitigrade a 4 segments, Leg5 et Leg6 plient en sens OPPOSES ; additionnes sur
# notre tibia unique, ils s annulent. Aucune inversion de signe ne rattrape ca (essaye :
# inverser la cuisse remet le sens mais le genou reste raide).
# Donc : tout le haut du corps reste ROR, les jambes sont celles de notre course,
# etirees au cycle ROR et calees en phase sur son rebond vertical.
JAMBES_OS = ('thigh_left', 'shin_left', 'foot_left', 'thigh_right', 'shin_right', 'foot_right')


def greffe_jambes(tracks, length, loop, source=COURSE, cycles=1, n=120):
    ry = tracks.get('root', {}).get('position')
    r = [lerp_track(ry, length * i / n, length, loop)[1] if ry else 0.0 for i in range(n)]

    def c(phase):
        return source.at('root', 'position', (phase % 1.0) * source.length)[1]

    def norm(v):
        m = sum(v) / len(v); e = (sum((x - m) ** 2 for x in v) / len(v)) ** 0.5 or 1.0
        return [(x - m) / e for x in v]
    rn = norm(r)
    best = None
    for k in range(200):
        o = k / 200.0
        sn = norm([c(i / n * cycles + o) for i in range(n)])
        err = sum((a - b) ** 2 for a, b in zip(rn, sn))
        if best is None or err < best[0]:
            best = (err, o)
    o = best[1]
    N = int(round(length * R.FPS))
    for b in JAMBES_OS:
        out = []
        for i in range(N + 1):
            t = min(i / R.FPS, length)
            ph = (t / length * cycles + o) % 1.0
            out.append((t, list(source.at(b, 'rotation', ph * source.length))))
        if boucle(loop):
            out[-1] = (out[-1][0], list(out[0][1]))
        tracks.setdefault(b, {})['rotation'] = R.compress(out, R.TOL['rotation'])
        tracks[b].pop('position', None)
    # la hauteur du bassin suit les appuis : on prend celle de la meme source, sinon le
    # rebond ROR (cale sur SES appuis) fait decoller nos pieds (7 images d appui sur 75)
    base = tracks.setdefault('root', {}).get('position')
    out = []
    for i in range(N + 1):
        t = min(i / R.FPS, length)
        ph = (t / length * cycles + o) % 1.0
        v = lerp_track(base, t, length, loop) if base else [0.0, 0.0, 0.0]
        out.append((t, [v[0], source.at('root', 'position', ph * source.length)[1], v[2]]))
    if boucle(loop):
        out[-1] = (out[-1][0], list(out[0][1]))
    tracks['root']['position'] = R.compress(out, R.TOL['position'])
    print('      jambes et hauteur de bassin greffees depuis course, %d cycle(s), phase %.2f' % (cycles, o))


def post_run_greffe(tracks, length, loop):
    greffe_jambes(tracks, length, loop, cycles=1)
    post_run(tracks, length, loop)


def post_rush_greffe(tracks, length, loop):
    greffe_jambes(tracks, length, loop, cycles=2)
    post_rush(tracks, length, loop)


# course_ror retiree (V81) : cinquieme course, avec depuis V80 les jambes memes de `course`

# ---------------------------------------------------------------- postures ROR
# Rendu de controle, qui a fait tomber le portage d origine : se_couche_ror se terminait
# DEBOUT, assis_ror etait debout, se_releve_ror commencait debout. Meme cause que la
# course : les deux segments de patte ROR plient en sens opposes et s annulent sur notre
# tibia, les pattes restaient raides et s enfoncaient de 35 unites ; le calage au sol
# avait alors releve tout le corps, ce qui annulait le geste. On avait verifie le sol,
# pas ce que faisait l animal.
# Le bas du corps (bassin, tronc, pattes, queue) vient donc des animations du MODELE qui
# font deja ce geste correctement ; le haut du corps (poitrail, cou, tete, gueule, gorge,
# bras, voile) reste celui de ROR.
# les bras aussi : couche, les bras ROR descendent vers le sol, et avec nos griffes
# allongees ils le traversaient ; le calage relevait alors l animal de 20 unites, pose
# sur le bout des griffes. Le modele avait deja resolu ou poser les bras couche.
BAS = ('root', 'body', 'thigh_left', 'shin_left', 'foot_left', 'thigh_right', 'shin_right',
       'foot_right', 'tail_01', 'tail_02', 'tail_03', 'tail_04', 'tail_05', 'tail_06',
       'upper_arm_left', 'forearm_left', 'hand_left', 'finger_left_0', 'finger_left_1',
       'finger_left_2', 'upper_arm_right', 'forearm_right', 'hand_right', 'finger_right_0',
       'finger_right_1', 'finger_right_2')
ENDORT = Maison('endormissement')
REVEIL = Maison('reveil')
DORT = Maison('dort')


def posture(source, duree_src, couches, longueur, boucle_src=False):
    def fn(bone, chan, t):
        if bone in BAS:
            u = t / longueur * duree_src
            return list(source.at(bone, chan, u, loop=boucle_src))
        v = evaluate(couches, bone, chan, t)
        if v is None:
            return [1.0, 1.0, 1.0] if chan == 'scale' else [0.0, 0.0, 0.0]
        return v
    return fn


add_maison('se_couche_ror', 1.5, 'once',
           posture(ENDORT, ENDORT.length, [Layer('down', 0.0)], 1.5), post_calm)
add_maison('se_releve_ror', 2.0, 'once',
           posture(REVEIL, REVEIL.length, [Layer('raise', 0.0)], 2.0), post_calm)
add_maison('assis_ror', 4.0, 'loop',
           posture(DORT, DORT.length, [Layer('sit', 0.0, loop_src=True)], 4.0, boucle_src=True),
           post_breath)
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
    post_rush_greffe, clamp=True)

# ---------------------------------------------------------------- 1 et 2. virages serres
# Convention verifiee sur le modele : rotation Y positive = le museau part vers la
# DROITE de l animal ; rotation Z negative = il se penche sur sa GAUCHE.
JAMBES = ('thigh_left', 'shin_left', 'foot_left', 'thigh_right', 'shin_right', 'foot_right')
MOY = {b: COURSE.moyenne(b) for b in JAMBES}


# deux foulees de course pile (2 x 0.8 s) : sur 1.25 s la boucle coupait la course a
# 1.56 foulee, et la patte sautait de 57 degres au raccord
VIRAGE_L = 2 * COURSE.length


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
            osc = math.sin(2 * math.pi * t / VIRAGE_L)
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


add_maison('virage_serre_gauche', VIRAGE_L, 'loop', virage(-1), post_virage, plante=True)
add_maison('virage_serre_droite', VIRAGE_L, 'loop', virage(+1), post_virage, plante=True)

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
                v[0] -= 3.5 * w
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


# sol=True : le bassin etait sureleve de 2.5, les pieds ne touchaient jamais le fond
add_maison('marche_eau_peu_profonde', 2.4, 'loop', marche_eau, post_eau, sol=True)

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
# Version precedente : un roulis pilote par une sinusoide arbitraire, qui montait a
# +22 degres, ne revenait jamais (moyenne +6.3) et culminait pendant que la patte
# DROITE portait - il se jetait donc sur la jambe blessee. D ou le penchement permanent.
#
# Ici tout est pilote par l appui REEL de la patte droite (mesure au FK sur le cycle de
# marche), et on reproduit la signature d une boiterie de membre posterieur :
#   - hanche qui MONTE du cote blesse pendant son appui (le "hip hike")
#   - buste qui s incline du cote SAIN pour decharger, et qui revient
#   - tete et cou qui se relevent a l appui douloureux
#   - appui droit ecourte, jambe posee avec precaution, jambe gauche qui compense
# moyennes d appui sur le cycle : on les retranche du roulis pour que la boiterie se
# lise dans la FORME de la courbe et non dans une inclinaison permanente. La jambe
# saine portant plus longtemps, sans ce recentrage l animal reste couche sur le cote.
_N_BOI = 72
_MAPD = sum(1.0 - en_lair('right', 2.4 * i / _N_BOI) for i in range(_N_BOI)) / _N_BOI
_MAPG = sum(1.0 - en_lair('left', 2.4 * i / _N_BOI) for i in range(_N_BOI)) / _N_BOI


def boite(bone, chan, t):
    k = 2.4 / MARCHE.length
    v = list(MARCHE.at(bone, chan, t / k))
    air_d = en_lair('right', t)            # 1 quand la patte blessee est en l air
    appui_d = 1.0 - air_d                  # 1 quand elle porte
    appui_g = 1.0 - en_lair('left', t)
    charge = appui_d - appui_g             # -1 (appui sain) .. +1 (appui blesse)
    if chan == 'rotation':
        if bone.endswith('right') and bone.startswith(('thigh', 'shin', 'foot')):
            m = MOY_M[bone]
            v = [m[i] + (v[i] - m[i]) * 0.74 for i in range(3)]   # foulee ecourtee
            if bone.startswith('thigh'):
                v[0] += 6.0 * appui_d
            if bone.startswith('shin'):
                v[0] += -8.0 * air_d                               # genou flechi en vol
            if bone.startswith('foot'):
                v[0] += 4.5 * air_d
        elif bone.endswith('left') and bone.startswith(('thigh', 'shin', 'foot')):
            m = MOY_M[bone]
            v = [m[i] + (v[i] - m[i]) * 1.14 for i in range(3)]   # la saine compense
        elif bone == 'root':
            # Mesure du repere : pied gauche a X=+21, droit a X=-21, et un roulis Z
            # NEGATIF porte la tete vers le +X, donc vers la GAUCHE. Le corps doit
            # passer au-dessus du pied qui porte ; la boiterie, c est de s y engager
            # franchement du cote sain et a peine du cote blesse.
            v[2] += 2.6 * (appui_d - _MAPD) - 6.0 * (appui_g - _MAPG)
            v[0] += 2.0 * appui_d
        elif bone == 'body':
            v[2] += 1.2 * (appui_d - _MAPD) - 2.8 * (appui_g - _MAPG)
            v[0] += 1.5 * appui_d
        elif bone == 'neck':
            v[0] += 7.5 * appui_d - 2.5 * appui_g - 3.0
            v[2] += -0.45 * (3.8 * (appui_d - _MAPD) - 8.8 * (appui_g - _MAPG))   # tete d aplomb
        elif bone == 'head':
            v[0] += 4.5 * appui_d - 1.5 * appui_g
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[1] += 1.4 * i * 0.35 * charge     # la queue contrebalance
            v[0] -= 0.5 * i * appui_d
    elif chan == 'position' and bone == 'root':
        v[1] += 2.6 * appui_d - 1.0 * appui_g                      # hanche qui monte du cote blesse
    return v


def post_boite(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.24, lag=0.13, cap=4.5)
    throat_vibe(tracks, length, loop, freq=1.4, amp=0.10, rot=1.8)


add_maison('marche_boiteuse', 2.4, 'loop', boite, post_boite, sol=True, plante=True)


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



# ================================================================== traque et horreur
# Principe commun, et c est l inverse de ce que j avais fait sur secoue_eau : ce qui
# fait peur n est pas le mouvement, c est sa RETENUE. Une tenue longue et parfaitement
# immobile suivie d une transition breve se lit comme une intention ; une oscillation
# continue se lit comme un tic. Toutes les bascules rapides ici durent au moins
# 3 images a 30 fps, et aucune frequence ne depasse 4.5 Hz (limite de Nyquist utile).


def marches(t, keys, duree=0.10):
    """Suite de PALIERS : chaque (temps, valeur) est tenue immobile jusqu a ce que la
    bascule vers la suivante s amorce, `duree` seconde avant son temps."""
    if t <= keys[0][0]:
        return keys[0][1]
    for i in range(len(keys) - 1):
        t1, v1 = keys[i + 1]
        if t < t1:
            d = max(duree, 3.0 / R.FPS)
            return keys[i][1] + (v1 - keys[i][1]) * ease(t, t1 - d, t1)
    return keys[-1][1]


# Calibration mesuree sur le rig : replier la jambe de (a, -1.36a, 0.35a) degres
# remonte le pied de 0.46a unites. Pour s accroupir sans decoller du sol il faut donc
# replier ET descendre le root d autant, car ground_clamp ne sait que remonter.
def pli(c):
    a = c / 0.46
    return a, -1.36 * a, 0.35 * a


def accroupi(bone, chan, v, c, garde=1.0):
    """Applique un accroupissement de c unites a une valeur deja calculee."""
    a, b, f = pli(c)
    if chan == 'rotation':
        if bone.startswith('thigh'):
            v[0] += a
        elif bone.startswith('shin'):
            v[0] += b
        elif bone.startswith('foot'):
            v[0] += f
    elif chan == 'position' and bone == 'root':
        v[1] -= c * garde
    return v


# ---------------------------------------------------------------- 1. traque au sol
# Foulee courte et basse, centre de gravite abaisse, queue tendue a l horizontale
# (le balancier lateral de la marche est coupe : un predateur en approche ne se
# signale pas), tete ramenee a l horizontale malgre le cou baisse -> regard verrouille.
def traque(bone, chan, t):
    L = 3.6
    v = list(MARCHE.at(bone, chan, t * MARCHE.length / L))
    if chan == 'rotation':
        if bone.startswith(('thigh', 'shin', 'foot')):
            m = MOY_M.get(bone, [0.0, 0.0, 0.0])
            v = [m[i] + (v[i] - m[i]) * 0.62 for i in range(3)]
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[0] -= 1.1 + 0.32 * i
            v[1] = v[1] * 0.40 + (1.4 + 0.5 * i) * _osc(t, 1 / L, -0.30 * i)
        elif bone == 'neck':
            v[0] += -16.0
            v[1] += 3.4 * _osc(t, 1 / 7.2)
        elif bone == 'head':
            v[0] += 12.0
            v[1] += 2.6 * _osc(t, 1 / 7.2, 0.9)
        elif bone.startswith('upper_arm'):
            v[0] += 14.0
        elif bone.startswith('forearm'):
            v[0] += 18.0
    return accroupi(bone, chan, v, 9.0)


def post_traque(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.18, lag=0.16, cap=3.5)
    throat_vibe(tracks, length, loop, freq=0.55, amp=0.07, rot=1.2)


add_maison('traque_lente', 3.6, 'loop', traque, post_traque, sol=True)


# ---------------------------------------------------------------- 2. traque a la surface
# Le corps derive, la TETE ne bouge pas. C est le contraste qui inquiete : une masse
# qui avance sans que le regard ne devie. Seuls le dessus du crane et la voile percent.
def traque_eau(bone, chan, t):
    L = 5.0
    v = list(REPOS.at(bone, chan, t * 0.30))
    lent = _osc(t, 1 / L)
    if chan == 'rotation':
        if bone == 'root':
            v[1] += 2.6 * lent
            v[0] += 4.0
        elif bone == 'body':
            v[1] += 1.8 * _osc(t, 1 / L, -0.7)
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[1] += (4.0 + 2.1 * i) * _osc(t, 1 / L, -0.42 * i)
            v[0] -= 0.5 * i
        elif bone == 'neck':
            v[0] += -5.0 - 2.2 * lent          # contre le lacet du corps : le cap tient
            v[1] += -2.4 * lent
        elif bone == 'head':
            v[0] += 7.0
            v[1] += -1.4 * lent + 1.2 * _osc(t, 1 / 12.0)
        elif bone.startswith('thigh'):
            v[0] += 12.0
        elif bone.startswith('shin'):
            v[0] += -18.0
        elif bone.startswith('foot'):
            v[0] += 7.0
        elif bone.startswith('upper_arm'):
            v[0] += 12.0
    elif chan == 'position' and bone == 'root':
        v[1] += -38.0 + 0.7 * _osc(t, 1 / (L / 2.0))
    return v


def post_traque_eau(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.22, lag=0.18, cap=3.5)
    throat_vibe(tracks, length, loop, freq=0.5, amp=0.09, rot=1.4)


add_maison('traque_eau_affleurante', 5.0, 'loop', traque_eau, post_traque_eau, clamp=False)


# ---------------------------------------------------------------- 3. immobilisation
# Le pied reste EN L AIR, pris au milieu du pas : c est la posture de l animal qui
# vient de reperer sa proie. Tremblement de tension a 3.5 Hz et 0.6 degre seulement,
# assez pour que la pose ne soit pas morte, trop peu pour se lire comme un tic.
_i_fige = max(range(len(_H['foot_left'])), key=lambda i: _H['foot_left'][i])
_PH_FIGE = _i_fige / len(_H['foot_left']) * MARCHE.length


def fige(bone, chan, t):
    v = list(MARCHE.at(bone, chan, _PH_FIGE))
    souffle = _osc(t, 1 / 4.2)
    if chan == 'rotation':
        if bone.startswith(('shin_left', 'foot_left')):
            v[0] += 0.6 * _osc(t, 3.5)
        elif bone == 'neck':
            v[0] += -13.0 + 0.7 * souffle
        elif bone == 'head':
            v[0] += 10.0
            v[1] += 0.8 * _osc(t, 1 / 8.4)
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[0] -= 0.9 + 0.30 * i
            v[1] = v[1] * 0.30 + 0.9 * _osc(t, 1 / 8.4, -0.25 * i)
        elif bone.startswith('upper_arm'):
            v[0] += 15.0
        elif bone.startswith('forearm'):
            v[0] += 19.0
    elif chan == 'position' and bone == 'root':
        v[1] += 0.5 * souffle
    return accroupi(bone, chan, v, 12.0)


def post_fige(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.12, lag=0.20, cap=2.0)
    throat_vibe(tracks, length, loop, freq=0.48, amp=0.06, rot=1.0)


add_maison('fige_en_traque', 4.2, 'loop', fige, post_fige, sol=True)


# ---------------------------------------------------------------- 4. embuscade
# Sortie de traque : ramasse, detente, extension en l air, reception encaissee.
T_RAM, T_DET, T_AIR, T_REC = 0.38, 0.72, 1.10, 1.62


def embuscade(bone, chan, t):
    v = list(MARCHE.at(bone, chan, _PH_FIGE))
    ram = ease(t, 0.0, T_RAM) * (1 - ease(t, T_RAM, T_DET))
    det = ease(t, T_RAM, T_DET) * (1 - ease(t, T_AIR, T_REC))
    rec = ease(t, T_AIR, T_REC)
    c = 11.0 + 7.0 * ram - 11.0 * det + 5.0 * rec
    if chan == 'rotation':
        if bone == 'neck':
            v[0] += -14.0 - 9.0 * ram + 30.0 * det - 6.0 * rec
        elif bone == 'head':
            v[0] += 11.0 + 5.0 * ram - 16.0 * det + 4.0 * rec
        elif bone == 'jaw':
            v[0] += -42.0 * bosse(t, T_RAM, T_AIR + 0.25) - 10.0 * rec
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            # positif = la pointe DESCEND (mesure faite sur le rig) : on leve donc
            # la queue au ramasse et on la tend en l air, sinon elle traverse le sol
            v[0] -= 1.2 * i * ram + 0.8 * i * det
            v[1] *= 0.3
        elif bone.startswith('upper_arm'):
            v[0] += 12.0 + 6.0 * ram - 34.0 * det
        elif bone.startswith('forearm'):
            v[0] += 15.0 - 26.0 * det
    return accroupi(bone, chan, v, c)


def post_embuscade(tracks, length, loop):
    add_root_curve(
        tracks, length,
        keys_pos=[(0.0, [0, 0, 0]), (T_RAM, [0, -2, 5]), (T_DET, [0, 9, -12]),
                  (T_AIR, [0, 16, -30]), (1.34, [0, 2, -42]), (T_REC, [0, -3, -46])],
        keys_rot=[(0.0, [0, 0, 0]), (T_RAM, [-5, 0, 0]), (T_DET, [10, 0, 0]),
                  (T_AIR, [7, 0, 0]), (T_REC, [-4, 0, 0])])
    sail_rework(tracks, length, loop, gain=0.38, lag=0.08, cap=9.0)
    throat_vibe(tracks, length, loop, freq=4.0, amp=0.20, rot=4.5,
                env=lambda t: bosse(t, T_RAM, T_REC))


add_maison('embuscade_jaillissement', 1.62, 'once', embuscade, post_embuscade)


# ---------------------------------------------------------------- 5. tete inclinee
# L inclinaison n est pas le sujet : la TENUE l est. 2.2 s de fixite absolue apres
# une bascule de 3 images. C est ce silence de mouvement qui met mal a l aise.
def tete_inclinee(bone, chan, t):
    v = list(REPOS.at(bone, chan, t * 0.22))
    roul = marches(t, [(0.0, 0.0), (1.00, 38.0), (3.45, -31.0), (5.20, 0.0), (5.5, 0.0)])
    lacet = marches(t, [(0.0, 0.0), (1.00, -9.0), (3.45, 7.0), (5.20, 0.0), (5.5, 0.0)])
    if chan == 'rotation':
        if bone == 'head':
            v[2] += roul
            v[1] += lacet
            v[0] += 9.0
        elif bone == 'neck':
            v[2] += roul * 0.22
            v[1] += lacet * 0.35
            v[0] += -12.0
        elif bone == 'jaw':
            v[0] += -8.0
        elif bone == 'chest':
            v[2] += roul * 0.06
        elif bone.startswith('tail_'):
            v[1] *= 0.25
    return v


def post_inclinee(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.14, lag=0.20, cap=2.5)
    throat_vibe(tracks, length, loop, freq=0.42, amp=0.08, rot=1.2)


add_maison('tete_inclinee_fixe', 5.5, 'once', tete_inclinee, post_inclinee)


# ---------------------------------------------------------------- 6. spasmes du cou
# Quatre repositionnements SECS separes par des tenues immobiles. Pas d oscillation :
# une sinusoide rapide donne la crise d epilepsie qu on a deja corrigee ailleurs,
# alors qu un escalier donne le mouvement reptilien anormal recherche.
SPASME_Y = [(0.0, 0.0), (0.62, 34.0), (1.34, -27.0), (2.10, 13.0), (2.92, 0.0), (3.4, 0.0)]
SPASME_Z = [(0.0, 0.0), (0.62, 17.0), (1.34, -23.0), (2.10, 29.0), (2.92, 0.0), (3.4, 0.0)]
SPASME_X = [(0.0, 0.0), (0.62, -6.0), (1.34, 9.0), (2.10, -11.0), (2.92, 0.0), (3.4, 0.0)]


def spasmes(bone, chan, t):
    v = list(REPOS.at(bone, chan, t * 0.25))
    y = marches(t, SPASME_Y, 0.10)
    z = marches(t, SPASME_Z, 0.10)
    x = marches(t, SPASME_X, 0.10)
    if chan == 'rotation':
        if bone == 'head':
            v[0] += 6.0 + x
            v[1] += y
            v[2] += z
        elif bone == 'neck':
            v[0] += -10.0 + x * 0.4
            v[1] += y * 0.32
            v[2] += z * 0.25
        elif bone == 'chest':
            v[1] += y * 0.10
        elif bone == 'jaw':
            v[0] += -5.0 - 9.0 * bosse(t, 2.00, 2.40)
        elif bone.startswith('tail_'):
            v[1] *= 0.2
    return v


def post_spasmes(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.20, lag=0.10, cap=4.0)
    throat_vibe(tracks, length, loop, freq=0.5, amp=0.09, rot=1.4)


add_maison('spasmes_cou', 3.4, 'once', spasmes, post_spasmes)


# ---------------------------------------------------------------- 7. emergence lente
# Il sort de l eau sans un bruit et sans rugir. La tete perce en premier et reste a
# l horizontale pendant toute la montee : rien ne detourne le regard.
def emergence(bone, chan, t):
    v = list(REPOS.at(bone, chan, t * 0.20))
    mont = ease(t, 0.60, 6.10)
    cou = ease(t, 0.35, 1.60) * (1 - ease(t, 3.40, 5.60))
    debout = ease(t, 4.60, 6.20)
    if chan == 'rotation':
        if bone == 'neck':
            v[0] += 27.0 * cou - 7.0 * debout - 4.0
        elif bone == 'head':
            v[0] += -23.0 * cou + 9.0 * debout + 3.0
            v[1] += 1.6 * _osc(t, 1 / 9.0)
        elif bone == 'jaw':
            v[0] += -11.0 * ease(t, 4.50, 5.60)
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[1] += (3.0 + 1.6 * i) * (1 - mont) * _osc(t, 0.30, -0.4 * i)
            v[0] -= 0.7 * i * (1 - debout)
        elif bone.startswith('thigh'):
            v[0] += 14.0 * (1 - debout)
        elif bone.startswith('shin'):
            v[0] += -19.0 * (1 - debout)
        elif bone.startswith('foot'):
            v[0] += 8.0 * (1 - debout)
        elif bone.startswith('upper_arm'):
            v[0] += 14.0 * (1 - debout) + 4.0 * debout
    elif chan == 'position' and bone == 'root':
        v[1] += -70.0 * (1 - mont) - 3.0 * debout
    return v


def post_emergence(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.24, lag=0.20, cap=4.0)
    throat_vibe(tracks, length, loop, freq=0.45, amp=0.14, rot=2.0,
                env=lambda t: ease(t, 2.6, 4.4))


add_maison('emergence_lente', 6.5, 'once', emergence, post_emergence, clamp=False)


# ---------------------------------------------------------------- 8. respiration lourde
# Boucle d ambiance : rien ne se passe, et c est le propos. Flancs qui travaillent,
# gueule entrouverte, tete basse. A jouer en fond quand le joueur est traque.
def respiration(bone, chan, t):
    L = 5.0
    v = list(REPOS.at(bone, chan, t * 0.28))
    b = _osc(t, 2.0 / L)                       # deux cycles par boucle
    ins = max(0.0, b)
    if chan == 'rotation':
        if bone == 'neck':
            v[0] += -11.0 + 2.6 * b
        elif bone == 'head':
            v[0] += 8.0 - 1.9 * b
        elif bone == 'jaw':
            v[0] += -6.0 - 5.0 * ins
        elif bone == 'chest':
            v[0] += 1.4 * b
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[1] += 1.2 * _osc(t, 1.0 / L, -0.3 * i)
        elif bone.startswith('upper_arm'):
            v[0] += 9.0
    elif chan == 'scale' and bone == 'chest':
        v = [v[0] * (1 + 0.040 * ins), v[1] * (1 + 0.028 * ins), v[2] * (1 + 0.048 * ins)]
    elif chan == 'position' and bone == 'root':
        v[1] += 0.9 * b
    return accroupi(bone, chan, v, 4.0)


def post_respiration(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.16, lag=0.18, cap=2.5)
    throat_vibe(tracks, length, loop, freq=0.4, amp=0.26, rot=3.2)


add_maison('respiration_lourde', 5.0, 'loop', respiration, post_respiration)


# ---------------------------------------------------------------- 9. avance menacante
# Contrairement a la traque, ici il veut etre vu : gueule entrouverte, epaules hautes,
# queue qui fouette lentement, grondement dans la gorge a 4 Hz.
def menace(bone, chan, t):
    L = 3.2
    v = list(MARCHE.at(bone, chan, t * MARCHE.length / L))
    if chan == 'rotation':
        if bone.startswith(('thigh', 'shin', 'foot')):
            m = MOY_M.get(bone, [0.0, 0.0, 0.0])
            v = [m[i] + (v[i] - m[i]) * 0.78 for i in range(3)]
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[0] -= 0.8 + 0.28 * i
            v[1] = v[1] * 0.5 + (5.0 + 2.4 * i) * _osc(t, 1 / L, -0.34 * i)
        elif bone == 'neck':
            v[0] += -19.0
            v[1] += 4.2 * _osc(t, 1 / (L * 2))
        elif bone == 'head':
            v[0] += 17.0
            v[1] += 3.0 * _osc(t, 1 / (L * 2), 0.8)
        elif bone == 'jaw':
            v[0] += -15.0 - 4.0 * _osc(t, 1 / L)
        elif bone.startswith('upper_arm'):
            v[0] += 18.0
            v[1] += 7.0 if bone.endswith('left') else -7.0
        elif bone.startswith('forearm'):
            v[0] += 26.0
    return accroupi(bone, chan, v, 6.0)


def post_menace(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.24, lag=0.13, cap=5.0)
    throat_vibe(tracks, length, loop, freq=4.0, amp=0.17, rot=3.8)


add_maison('avance_menacante', 3.2, 'loop', menace, post_menace, sol=True)



# ---------------------------------------------------------------- 10. marche feutree
# Ce qui rend un pas silencieux, c est la VITESSE D ARRIVEE du pied en appui : dans
# marche elle vaut -30 unites par seconde, en course -128.
#
# J ai d abord ecrit un reprofilage du temps (ralentir l horloge au moment du contact,
# rattraper pendant le vol). Mesure : il FAIT EMPIRER l impact, -11.0 contre -7.6 sans
# lui. La duree totale etant conservee, ralentir l approche accelere tout le reste, et
# a 30 images par seconde la descente ne dure de toute facon que quelques images : il
# n y a pas la resolution temporelle pour etaler un poser. Mecanisme supprime.
#
# Ce qui marche, et qui survit a 30 images par seconde : un cycle long (4.4 s), un
# degagement franc mais maitrise (8.7 unites contre 5.3 en marche), le corps plus bas
# que toutes les autres marches (hanche -13.4) et la queue tenue immobile.

FEUTRE_L = 4.4


def feutree(bone, chan, t):
    u = t / FEUTRE_L
    v = list(MARCHE.at(bone, chan, u * MARCHE.length))
    if chan == 'rotation':
        if bone.startswith(('thigh', 'shin', 'foot')):
            side = 'left' if bone.endswith('left') else 'right'
            w = en_lair(side, u * ETIRE * MARCHE.length)      # 1 quand la patte est en vol
            m = MOY_M.get(bone, [0.0, 0.0, 0.0])
            v = [m[i] + (v[i] - m[i]) * (0.66 + 0.18 * w) for i in range(3)]
            if bone.startswith('thigh'):
                v[0] -= 2.2 * w                                # patte degagee plus haut
            if bone.startswith('shin'):
                v[0] -= 3.5 * w
            if bone.startswith('foot'):
                v[0] += 3.0 * w                                # et reposee a plat
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[0] += -0.9 + 0.22 * i                            # base degagee, pointe basse
            v[1] = v[1] * 0.22 + 1.0 * _osc(t, 1 / FEUTRE_L, -0.28 * i)
        elif bone == 'neck':
            v[0] += -17.0
            v[1] += 2.6 * _osc(t, 1 / (FEUTRE_L * 2))
        elif bone == 'head':
            v[0] += 13.0
            v[1] += 1.8 * _osc(t, 1 / (FEUTRE_L * 2), 0.9)
        elif bone.startswith('upper_arm'):
            v[0] += 16.0
        elif bone.startswith('forearm'):
            v[0] += 20.0
    return accroupi(bone, chan, v, 12.0)


def post_feutree(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.14, lag=0.18, cap=2.5)
    throat_vibe(tracks, length, loop, freq=0.5, amp=0.06, rot=1.0)


add_maison('marche_feutree', FEUTRE_L, 'loop', feutree, post_feutree, sol=True)



# ================================================================== ecoute et flair
# Mesure des deux animations d origine : elles n animent QUE le cou et la tete, tous
# les autres os restent a zero.
#   ecoute_joueur : lacet de tete 15.6 deg, rien d autre, machoire et gorge mortes.
#   renifle_air   : le crane DESCEND de 76 a 67 et la tete se met a l horizontale,
#                   soit l inverse d un flairage d air, puis tenue 3.5 s sans rien.
# Les deux sont reecrites ici, memes noms et memes durees.

def ecoute(bone, chan, t):
    # Ce qui se lit comme "il ecoute" : l animal se FIGE, puis reoriente la tete par
    # paliers secs pour croiser les directions, en inclinant le crane (le cocking).
    # Le corps s immobilise : on ralentit la respiration de fond au lieu de la couper,
    # sinon la pose parait morte.
    fige = ease(t, 0.55, 0.95) * (1 - ease(t, 4.55, 5.20))
    v = list(REPOS.at(bone, chan, t * (0.42 - 0.34 * fige)))
    lacet = marches(t, [(0.0, 0.0), (1.10, 29.0), (2.45, -23.0), (3.70, 9.0),
                        (4.90, 0.0), (5.30, 0.0)], 0.16)
    roul = marches(t, [(0.0, 0.0), (1.10, 15.0), (2.45, -12.0), (3.70, 7.0),
                       (4.90, 0.0), (5.30, 0.0)], 0.16)
    if chan == 'rotation':
        if bone == 'head':
            v[1] += lacet
            v[2] += roul
            v[0] += 7.0 * fige                    # museau releve, il tend l oreille
        elif bone == 'neck':
            v[1] += lacet * 0.38
            v[2] += roul * 0.25
            v[0] += 5.0 * fige
        elif bone == 'chest':
            v[1] += lacet * 0.12
        elif bone == 'body':
            v[1] += lacet * 0.07
        elif bone == 'jaw':
            v[0] += -3.0 * fige                   # gueule juste entrouverte
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[1] = v[1] * (1 - 0.75 * fige) + 0.8 * i * 0.3 * fige * _osc(t, 1 / 9.0, -0.3 * i)
            v[0] -= 0.35 * i * fige
        elif bone.startswith(('thigh', 'shin')):
            v[0] += (2.5 if bone.startswith('thigh') else -3.5) * fige
    elif chan == 'position' and bone == 'root':
        v[1] += -1.2 * fige
    return v


def post_ecoute(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.16, lag=0.18, cap=3.0)
    # souffle suspendu pendant les tenues, puis reprise
    throat_vibe(tracks, length, loop, freq=0.55, amp=0.10, rot=1.6,
                env=lambda t: 1.0 - 0.75 * ease(t, 0.7, 1.1) * (1 - ease(t, 3.9, 4.4)))


add_maison('ecoute_joueur', 5.30, 'once', ecoute, post_ecoute)


F_HAUT, F_FIN = 1.05, 3.65


def renifle(bone, chan, t):
    # Flairer l AIR, c est lever le museau au-dessus de l horizontale et faire travailler
    # les narines. L original faisait descendre le crane de 9 unites : on inverse.
    haut = ease(t, 0.25, F_HAUT) * (1 - ease(t, F_FIN, 4.75))
    # bouffees de flair : 2.5 Hz (12 images par cycle a 30 fps), par salves
    salve = (ease(t, F_HAUT, 1.35) * (1 - ease(t, 2.05, 2.30))
             + ease(t, 2.55, 2.80) * (1 - ease(t, 3.40, F_FIN)))
    bouffee = max(0.0, math.sin(2 * math.pi * 2.5 * t)) * salve
    vent = _osc(t, 0.25) * haut                    # balayage lent pour prendre le vent
    if chan == 'rotation':
        if bone == 'neck':
            v = list(REPOS.at(bone, chan, t * 0.3))
            v[0] += 32.0 * haut
            v[1] += 11.0 * vent
        elif bone == 'head':
            v = list(REPOS.at(bone, chan, t * 0.3))
            v[0] += 14.0 * haut + 2.5 * bouffee
            v[1] += 6.0 * vent
            v[2] += 3.0 * vent
        elif bone == 'jaw':
            v = list(REPOS.at(bone, chan, t * 0.3))
            v[0] += -5.5 * bouffee - 2.0 * haut
        elif bone == 'chest':
            v = list(REPOS.at(bone, chan, t * 0.3))
            v[0] += 3.0 * haut
        elif bone == 'body':
            v = list(REPOS.at(bone, chan, t * 0.3))
            v[0] += 2.5 * haut
        elif bone.startswith('tail_'):
            v = list(REPOS.at(bone, chan, t * 0.3))
            i = int(bone[-2:])
            v[0] += 0.45 * i * haut                # contrepoids : la queue descend
            v[1] += 0.7 * i * 0.3 * vent
        elif bone.startswith('thigh'):
            v = list(REPOS.at(bone, chan, t * 0.3))
            v[0] += 4.0 * haut                     # appui reporte en arriere
        elif bone.startswith('shin'):
            v = list(REPOS.at(bone, chan, t * 0.3))
            v[0] += -5.0 * haut
        else:
            v = list(REPOS.at(bone, chan, t * 0.3))
    else:
        v = list(REPOS.at(bone, chan, t * 0.3))
        if chan == 'position' and bone == 'root':
            v[1] += 1.5 * haut
    return v


def post_renifle(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.18, lag=0.16, cap=3.5)
    # la gorge travaille a chaque bouffee
    throat_vibe(tracks, length, loop, freq=2.5, amp=0.20, rot=3.0,
                env=lambda t: (ease(t, F_HAUT, 1.35) * (1 - ease(t, 2.05, 2.30))
                               + ease(t, 2.55, 2.80) * (1 - ease(t, 3.40, F_FIN))))


add_maison('renifle_air', 5.00, 'once', renifle, post_renifle)



# ---------------------------------------------------------------- flairage de piste au sol
# renifle_piste_ror (le clip ROR) monte le crane a 104 : c est du flair AERIEN malgre son
# nom, et renifle_air en fait autant. Il manquait donc le seul qui compte pour pister :
# museau a terre.
#
# Cale par mesure, pas par estimation : cou -50 / tete -28 / tronc -13 amene la pointe
# du museau a 1.3 unite du sol (104.1 au repos) sans que rien ne traverse et sans
# decoller les pieds. Un premier essai a -58/-32/-15 enfoncait le museau de 5.9 sous
# le sol ; le laisser dans le calage sol n arrangeait rien, le calage ne sachant que
# remonter, il souleva l animal de 9.6 et le posa sur le nez, pattes en l air.
PISTE_L = 7.0
P_BAS, P_PAUSE, P_REPRISE, P_TROUVE, P_FIN = 1.05, 2.45, 3.05, 4.95, 6.25


def piste(bone, chan, t):
    v = list(REPOS.at(bone, chan, t * 0.28))
    # museau au sol, sauf pendant la pause d evaluation et le redressement final
    bas = (ease(t, 0.25, P_BAS)
           * (1 - 0.72 * bosse(t, P_PAUSE, P_REPRISE))
           * (1 - 0.55 * bosse(t, P_TROUVE, 5.45))
           * (1 - ease(t, P_FIN, 6.95)))
    alerte = ease(t, P_FIN, 6.95)                      # il releve la tete vers la piste
    # balayage : le museau traverse la trace de gauche a droite
    cast = _osc(t, 0.45) * bas
    # bouffees courtes a 3 Hz (10 images par cycle a 30 fps), par salves
    salve = (ease(t, P_BAS, 1.25) * (1 - ease(t, P_PAUSE - 0.2, P_PAUSE))
             + ease(t, P_REPRISE, 3.25) * (1 - ease(t, 4.55, P_TROUVE))
             + ease(t, 5.45, 5.65) * (1 - ease(t, 6.05, P_FIN)))
    bouffee = max(0.0, math.sin(2 * math.pi * 3.0 * t)) * salve
    if chan == 'rotation':
        if bone == 'neck':
            v[0] += -50.0 * bas + 16.0 * alerte
            v[1] += 14.0 * cast
        elif bone == 'head':
            v[0] += -28.0 * bas + 9.0 * alerte - 1.8 * bouffee
            v[1] += 9.0 * cast
            v[2] += 5.0 * cast
        elif bone == 'jaw':
            v[0] += -4.5 * bouffee - 2.5 * bas
        elif bone == 'body':
            v[0] += -13.0 * bas + 3.0 * alerte
            v[1] += 3.5 * cast
        elif bone == 'chest':
            v[0] += -5.0 * bas
            v[1] += 2.5 * cast
        elif bone == 'root':
            v[0] += -4.0 * bas
            v[1] += 2.0 * cast
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[0] -= 1.5 * i * bas                      # queue relevee en contrepoids
            v[1] += 0.9 * i * 0.35 * cast
        elif bone.startswith('upper_arm'):
            v[0] += 13.0 * bas                         # bras replies contre le poitrail
        elif bone.startswith('forearm'):
            v[0] += 17.0 * bas
        elif bone.startswith(('thigh', 'shin', 'foot')):
            # pas de repliement : il decollerait les pieds, et le calage sol, ne
            # pouvant que remonter l animal, le laisserait pose sur le museau
            pass
    return v


def post_piste(tracks, length, loop):
    # il avance le long de la trace pendant les deux phases de suivi
    add_root_curve(
        tracks, length,
        keys_pos=[(0.0, [0, 0, 0]), (P_BAS, [0, 0, -3]), (P_PAUSE, [0, 0, -17]),
                  (P_REPRISE, [0, 0, -19]), (4.55, [0, 0, -38]), (P_TROUVE, [0, 0, -41]),
                  (P_FIN, [0, 0, -44]), (PISTE_L, [0, 0, -45])])
    sail_rework(tracks, length, loop, gain=0.20, lag=0.15, cap=4.0)
    throat_vibe(tracks, length, loop, freq=3.0, amp=0.18, rot=2.8,
                env=lambda t: (ease(t, P_BAS, 1.25) * (1 - ease(t, P_PAUSE - 0.2, P_PAUSE))
                               + ease(t, P_REPRISE, 3.25) * (1 - ease(t, 4.55, P_TROUVE))
                               + ease(t, 5.45, 5.65) * (1 - ease(t, 6.05, P_FIN))))


# le museau touche le sol par construction : il est donc exclu du calage, sinon
# celui-ci souleve tout l animal et lui fait porter son poids sur le nez
add_maison('renifle_piste_sol', PISTE_L, 'once', piste, post_piste, sol=True,
           clamp_skip=('tail_04', 'tail_05', 'tail_06', 'head', 'jaw', 'tongue'))



# ================================================================== etats moteur
# Les seuls etats que Minecraft declenche TOUT SEUL, sans code du mod : coup recu, saut
# d un bloc, chute, mort. Jusqu ici : aucune animation pour les trois premiers, et une
# mort terrestre (le root descend a -24, l animal s effondre au sol) jouee aussi sous
# l eau. Le saut n affiche que la POSE : c est le moteur qui deplace l entite, une
# translation du root ici se cumulerait avec la sienne.
_HC = hauteur_pieds(COURSE)
_PH_VOL = (max(range(len(_HC['foot_left'])), key=lambda i: _HC['foot_left'][i])
           / len(_HC['foot_left']) * COURSE.length)


def patte_repliee(bone):
    """Patte en plein vol de course (pied au plus haut), la meme pour les deux cotes."""
    return list(COURSE.at(bone.replace('right', 'left'), 'rotation', _PH_VOL))


def _choc(t, a=0.0, monte=0.07, tient=0.12, fin=0.55):
    # front de 2 images : un coup recu est un evenement sec, pas une oscillation
    return ease(t, a, a + monte) * (1 - ease(t, a + tient, fin))


def degats_sur(base_fn, jambes=True):
    def fn(bone, chan, t):
        v = list(base_fn(bone, chan, t))
        c = _choc(t)
        if chan == 'rotation':
            if bone == 'root':
                v[0] += 4.0 * c
            elif bone == 'body':
                v[0] += 5.0 * c
            elif bone == 'chest':
                v[0] += 4.0 * c
            elif bone == 'neck':
                v[0] += 16.0 * c; v[1] += 9.0 * c
            elif bone == 'head':
                v[0] += 12.0 * c; v[1] += 6.0 * c; v[2] += 8.0 * c
            elif bone == 'jaw':
                v[0] += -30.0 * c                           # cri de douleur
            elif bone.startswith('upper_arm'):
                v[0] += 18.0 * c                            # les bras se replient
            elif bone.startswith('forearm'):
                v[0] += 22.0 * c
            elif bone.startswith('tail_'):
                i = int(bone[-2:])
                v[0] -= 1.2 * i * c
                v[1] += (1.5 + 0.9 * i) * c * math.sin(2 * math.pi * 3.0 * t)
        elif chan == 'position' and bone == 'root':
            v[2] += 4.0 * c                                 # repousse en arriere
            v[1] += -1.5 * c
        return accroupi(bone, chan, v, 3.0 * c) if jambes else v
    return fn


def post_degats(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.45, lag=0.07, cap=10.0)
    throat_vibe(tracks, length, loop, freq=4.0, amp=0.22, rot=5.0, env=lambda t: _choc(t))


add_maison('degats', 0.6, 'once', degats_sur(lambda b, c, t: REPOS.at(b, c, t * 0.3)), post_degats)
add_maison('degats_eau', 0.6, 'once',
           degats_sur(lambda b, c, t: NAGE.at(b, c, t), jambes=False), post_degats, clamp=False)


S_RAM, S_POUSSE, S_VOL, S_RECEP, S_FIN = 0.18, 0.28, 0.62, 0.78, 0.9


def saut(bone, chan, t):
    v = list(REPOS.at(bone, chan, t * 0.3))
    ram = ease(t, 0.0, S_RAM) * (1 - ease(t, S_RAM, S_POUSSE))
    # repli des pattes etale sur 0.16 s : sur 0.10 s il montait a 26 degres par image
    vol = ease(t, S_RAM, S_POUSSE + 0.06) * (1 - ease(t, S_VOL - 0.10, S_VOL + 0.04))
    rec = ease(t, S_VOL, S_VOL + 0.06) * (1 - ease(t, S_RECEP, S_FIN))
    if chan == 'rotation':
        if bone.startswith(('thigh', 'shin', 'foot')):
            r = patte_repliee(bone)
            v = [v[k] * (1 - vol) + r[k] * vol for k in range(3)]
        elif bone == 'root':
            v[0] += -5.0 * ram + 7.0 * vol - 6.0 * rec      # nez haut au depart, bas a la reception
        elif bone == 'neck':
            v[0] += -6.0 * ram + 8.0 * vol + 5.0 * rec      # le cou compense a la reception
        elif bone == 'head':
            v[0] += 3.0 * rec
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[0] -= (0.9 * vol + 0.6 * rec) * i             # queue en balancier
        elif bone.startswith('upper_arm'):
            v[0] += 14.0 * vol
        elif bone.startswith('forearm'):
            v[0] += 18.0 * vol
    elif chan == 'position' and bone == 'root':
        v[1] += -2.0 * ram + 3.0 * vol - 3.0 * rec
    return accroupi(bone, chan, v, 9.0 * ram + 11.0 * rec)


def post_saut(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.40, lag=0.08, cap=9.0)


# calage au sol actif : a la reception les pattes, encore a demi repliees, passaient
# 4.2 sous le sol. Il ne remonte que ce qui traverse, le vol n est pas touche.
add_maison('saut', S_FIN, 'once', saut, post_saut)


def chute(bone, chan, t):
    L = 0.8
    v = list(REPOS.at(bone, chan, t * 0.3))
    ag = math.sin(2 * math.pi * t / L)                    # 1.25 Hz : il bat des membres
    if chan == 'rotation':
        if bone.startswith(('thigh', 'shin', 'foot')):
            r = patte_repliee(bone)
            v = [v[k] * 0.4 + r[k] * 0.6 for k in range(3)]  # pattes en avant pour amortir
            if bone.startswith('thigh'):
                v[0] += 3.0 * ag * (1 if bone.endswith('left') else -1)
        elif bone == 'neck':
            v[0] += 10.0 + 2.0 * ag
        elif bone == 'head':
            v[0] += 6.0
        elif bone == 'jaw':
            v[0] += -9.0 - 3.0 * max(0.0, ag)
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[0] -= 1.4 * i
            v[1] += (1.5 + 1.0 * i) * math.sin(2 * math.pi * t / L - 0.35 * i)
        elif bone.startswith('upper_arm'):
            v[0] += 10.0
            v[2] += (9.0 + 4.0 * ag) * (1 if bone.endswith('left') else -1)   # bras ecartes
        elif bone.startswith('forearm'):
            v[0] += 12.0
    return v


def post_chute(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.30, lag=0.10, cap=6.0)
    throat_vibe(tracks, length, loop, freq=2.5, amp=0.12, rot=2.4)


add_maison('chute', 0.8, 'loop', chute, post_chute, clamp=False)


def mort_eau(bone, chan, t):
    nage = list(NAGE.at(bone, chan, t * 0.6))
    repos = [1.0, 1.0, 1.0] if chan == 'scale' else [0.0, 0.0, 0.0]
    mou = ease(t, 0.2, 1.6)                               # le tonus s en va
    v = [nage[k] * (1 - mou) + repos[k] * mou for k in range(3)]
    roule = ease(t, 0.3, 2.6)                             # bascule sur le flanc
    coule = ease(t, 0.8, 4.0)                             # et descend lentement
    spasme = _choc(t, a=0.32, monte=0.07, tient=0.10, fin=0.60)
    if chan == 'rotation':
        if bone == 'root':
            v[2] += 78.0 * roule
            v[0] += 6.0 * coule
        elif bone == 'neck':
            v[0] += -14.0 * mou + 9.0 * spasme
        elif bone == 'head':
            v[0] += -10.0 * mou + 6.0 * spasme
        elif bone == 'jaw':
            v[0] += -18.0 * mou                           # machoire relachee
        elif bone.startswith('tail_'):
            i = int(bone[-2:])
            v[1] += (1.2 + 0.7 * i) * math.sin(2 * math.pi * t / 3.0 - 0.3 * i) * (1 - 0.7 * coule)
        elif bone.startswith('upper_arm'):
            v[0] += 6.0 * mou
    elif chan == 'position' and bone == 'root':
        # la profondeur de nage est GARDEE (la melanger vers le repos ferait remonter le
        # corps a hauteur debout), puis il coule
        v = list(nage)
        v[1] += -48.0 * coule
    return v


def post_mort_eau(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.25, lag=0.20, cap=5.0)
    throat_vibe(tracks, length, loop, freq=0.6, amp=0.10, rot=1.5, env=lambda t: 1 - ease(t, 0.4, 1.8))


add_maison('mort_eau', 4.0, 'hold', mort_eau, post_mort_eau, clamp=False)



# ================================================================== regard fixe
# Pendant la marche, il tourne brusquement la tete et FIXE le joueur. La bascule dure
# 3 images, puis la tete est verrouillee en orientation absolue : les pattes continuent
# de marcher et le corps d oscille, mais ces oscillations sont retranchees de la tete,
# si bien que le regard ne bouge plus. Deux cotes : le code du mod joue celui ou se
# trouve le joueur. Duree = deux cycles de marche pile, pour s enchainer sur `marche`.
RF_L = 2 * MARCHE.length
RF_BASCULE, RF_LACHE, RF_FIN = 0.50, 2.85, 3.45
ANCETRES_TETE = ('root', 'body', 'chest', 'neck')
_MOY_RF = {b: MARCHE.moyenne(b) for b in ANCETRES_TETE + ('head',)}


def _fixe(t, a, lache, fin):
    return ease(t, a, a + 0.10) * (1 - ease(t, lache, fin))


def marche_regard(cote):
    def fn(bone, chan, t):
        v = list(MARCHE.at(bone, chan, t))
        f = _fixe(t, RF_BASCULE, RF_LACHE, RF_FIN)
        if chan != 'rotation' or f <= 0.0:
            return v
        if bone == 'neck':
            v[0] += 3.0 * f
            v[1] += 24.0 * cote * f
        elif bone == 'chest':
            v[1] += 6.0 * cote * f
        elif bone == 'head':
            m = _MOY_RF['head']
            # la tete ne suit plus la marche : on retire sa propre oscillation...
            v = [m[k] + (v[k] - m[k]) * (1 - f) for k in range(3)]
            # ...et celles de ses ancetres, pour que le regard reste fixe dans le monde
            for a in ANCETRES_TETE:
                va = MARCHE.at(a, 'rotation', t)
                ma = _MOY_RF[a]
                for k in range(3):
                    v[k] -= (va[k] - ma[k]) * f
            v[0] += -5.0 * f                       # il fixe, legerement vers le bas
            v[1] += 32.0 * cote * f
            v[2] += 7.0 * cote * f                 # crane a peine incline
        return v
    return fn


def _euler_zyx(R):
    """Inverse de fk.mat_rot (R = Rz . Ry . Rx), en degres."""
    b = math.asin(max(-1.0, min(1.0, -R[2][0])))
    a = math.atan2(R[2][1], R[2][2])
    g = math.atan2(R[1][0], R[0][0])
    return [math.degrees(a), math.degrees(b), math.degrees(g)]


def verrouille_tete(tracks, length, loop, env, t_ref):
    """Verrouille la tete en orientation ABSOLUE pendant `env`.

    Premier essai : retrancher de la tete les oscillations d angle de ses ancetres.
    Mesure : 1.9 deg de derive residuelle (contre 3.7 sur la marche normale), parce
    que des angles d Euler ne s additionnent pas en 3D. Ici c est exact : a chaque
    image on calcule l orientation du parent dans le monde, et on en deduit la
    rotation locale qui garde la tete dans l orientation qu elle avait a t_ref.
    """
    _ensure_rig()
    G = {g['name']: g for g in bb['groups']}
    parent = None
    for u, enfants in RIG.children.items():
        if RIG.byname['head'] in enfants and u is not None:
            parent = RIG.groups[u]['name']
    repos = G['head'].get('rotation', [0, 0, 0])

    def pose(t):
        def g(bone, chan):
            tr = tracks.get(bone, {}).get(chan)
            neutral = [1.0, 1.0, 1.0] if chan == 'scale' else [0.0, 0.0, 0.0]
            return lerp_track(tr, t, length, loop) if tr else neutral
        return RIG.pose(g)
    cible = pose(t_ref)['head'][0]
    base = tracks['head']['rotation']
    n = int(round(length * R.FPS))
    out = []
    for i in range(n + 1):
        t = min(i / R.FPS, length)
        v = lerp_track(base, t, length, loop)
        w = env(t)
        if w > 0.0:
            Mp = pose(t)[parent][0]
            loc = FK.mul([[Mp[k][j] for k in range(3)] for j in range(3)], cible)   # Mp^T . cible
            e = _euler_zyx(loc)
            e = [e[k] - repos[k] for k in range(3)]
            # meme determination de l angle que la piste d origine (pas de saut de 360)
            e = [e[k] + 360.0 * round((v[k] - e[k]) / 360.0) for k in range(3)]
            v = [v[k] * (1 - w) + e[k] * w for k in range(3)]
        out.append((t, v))
    tracks['head']['rotation'] = R.compress(out, R.TOL['rotation'])
    print('      tete verrouillee en orientation absolue (parent : %s)' % parent)


def post_marche_regard(tracks, length, loop):
    verrouille_tete(tracks, length, loop, lambda t: _fixe(t, RF_BASCULE + 0.10, RF_LACHE, RF_FIN),
                    RF_BASCULE + 0.10)
    sail_rework(tracks, length, loop, gain=0.24, lag=0.12, cap=4.5)
    # souffle retenu pendant qu il fixe
    throat_vibe(tracks, length, loop, freq=1.3, amp=0.09, rot=1.8,
                env=lambda t: 1 - 0.85 * _fixe(t, RF_BASCULE, RF_LACHE, RF_FIN))


add_maison('marche_regard_fixe_droite', RF_L, 'once', marche_regard(+1), post_marche_regard)
add_maison('marche_regard_fixe_gauche', RF_L, 'once', marche_regard(-1), post_marche_regard)


# Le meme geste pendant le repas, sans toucher a mange_carcasse. Juste apres la premiere
# morsure (tete au sol, viande dans la gueule), il releve la tete d un coup vers le
# joueur et SE FIGE tout entier 2.2 s ; puis il redescend lentement et reprend son
# repas exactement la ou il l avait laisse.
MR_T1, MR_TIENT, MR_RETOUR = 1.00, 3.30, 4.10
MR_DECALAGE = MR_RETOUR - MR_T1
MR_L = 5.8 + MR_DECALAGE


def mange_regard(cote):
    def fn(bone, chan, t):
        if t < MR_T1:
            return mange(bone, chan, t)
        if t >= MR_RETOUR:
            return mange(bone, chan, t - MR_DECALAGE)
        v = list(mange(bone, chan, MR_T1))           # tout le corps fige
        f = _fixe(t, MR_T1, MR_TIENT, MR_RETOUR)
        if chan != 'rotation':
            return v
        if bone == 'neck':
            v[0] += 24.0 * f; v[1] += 20.0 * cote * f
        elif bone == 'head':
            v[0] += 20.0 * f; v[1] += 28.0 * cote * f; v[2] += 6.0 * cote * f
        elif bone == 'jaw':
            # a l instant fige la machoire de mange est deja fermee (0) : on l entrouvre
            v[0] += -7.0 * f                         # sur la viande
        elif bone == 'chest':
            v[1] += 5.0 * cote * f
        return v
    return fn


def post_mange_regard(tracks, length, loop):
    sail_rework(tracks, length, loop, gain=0.30, lag=0.11, cap=6.0)
    d = MR_DECALAGE
    throat_vibe(tracks, length, loop, freq=3.5, amp=0.24, rot=5.5,
                env=lambda t: max(ease(t, 1.85 + d, 2.20 + d) * (1 - ease(t, 2.55 + d, 2.85 + d)),
                                  ease(t, 4.55 + d, 4.90 + d) * (1 - ease(t, 5.25 + d, 5.55 + d))))


add_maison('mange_carcasse_regard_droite', MR_L, 'once', mange_regard(+1), post_mange_regard)
add_maison('mange_carcasse_regard_gauche', MR_L, 'once', mange_regard(-1), post_mange_regard)


# ================================================================== ecriture
par_nom = {a['name']: i for i, a in enumerate(bb['animations'])}
remplacees = []
for a in NEW:
    if a['name'] in par_nom:
        bb['animations'][par_nom[a['name']]] = a
        remplacees.append(a['name'].split('.')[-1])
    else:
        bb['animations'].append(a)
if remplacees:
    print('animations d origine remplacees :', ', '.join(remplacees))
bb['name'] = 'RIVIERE_70_ADAPTATION_ROR_UPDATED'
bb['credit'] = ('V41 - texture et yeux JP3 affines; animation grimpe reconstruite; squelette et '
                'autres animations preserves | V70u - 13 animations portees depuis Raxio ROR '
                '(spino_basic/more/mace, avec accord de l auteur) et retargetees sur le rig RIVIERE : '
                'attaque plongeante, ruee griffes, voile reajustee, vibration de la gorge '
                '| V76 - 9 animations de traque et d ambiance horrifique ecrites main '
                '(traque au sol et a la surface, immobilisation, embuscade, tete inclinee, '
                'spasmes du cou, emergence lente, respiration lourde, avance menacante) '
                '| V77 - marche feutree ; correction du saut de derniere image sur les '
                'animations non bouclees ; calage sol sur la geometrie reelle du livrable '
                '| V78 - boiterie reecrite, ecoute_joueur et renifle_air refaits '
                '| V79 - renifle_piste_sol, museau a terre '
                '| V80 - revision complete : z-fighting supprime, courses ROR sans moonwalk, '
                'postures ROR reellement couchees, boucles periodiques, pieds plantes, '
                'etats moteur (degats, degats_eau, saut, chute, mort_eau) '
                '| V81 - queue droite et epaisse, pattes plus massives, texture d apres la '
                'reference du joueur, regard fixe en marchant et en mangeant, 4 portages ROR '
                'redondants retires')
out = os.path.join(W, 'RIVIERE_70_ADAPTATION_ROR_UPDATED.bbmodel')
json.dump(bb, open(out, 'w'), separators=(',', ':'))
print('\nEcrit :', out, round(os.path.getsize(out) / 1e6, 1), 'Mo',
      '| total animations =', len(bb['animations']))
