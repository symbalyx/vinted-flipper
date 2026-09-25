"""Texture d apres la reference du joueur (capture 1), sans perdre le travail de l auteur.

  peau    : recoloration par RANG de luminance vers la rampe de la reference. Le grain,
            les ombres et les details peints par l auteur sont gardes, seule la palette
            change. Seuls les pixels BRUNS sont touches : un oeil peint, un detail rouge,
            un blanc restent tels quels.
  voile   : reseau de losanges ocre sur brun fonce, peint en coordonnees du monde (la
            bande de la voile dans l atlas en est une image lineaire exacte), en blocs
            carres sur le modele, qui se fond dans la peau vers la base.
  gueule  : langue, palais, plancher vers le rose de la reference.
  arcades : arcades sourcilieres vers le rouge de la reference.
  intact  : dents, griffes, paupieres.
"""
import json, sys, os, base64, io, math
import numpy as np
from PIL import Image

ICI = os.path.dirname(os.path.abspath(__file__))
PAL = json.load(open(os.path.join(ICI, 'palette_reference.json')))
INTACT = ('V70_dent', 'V46_griffe_pied', 'V70_ROR_griffe', 'V70_paupiere')
BOUCHE = ('V70_langue', 'V70_palais', 'V70_plancher')
ROUGE = ('V70_arcade',)
PRIO = {'peau': 1, 'bord': 2, 'rouge': 3, 'bouche': 4, 'voile': 5, 'intact': 6}

# reglages de la rampe de peau : on laisse tomber les ombres les plus noires et le
# reflet speculaire de la capture, qui viennent de l eclairage, pas de la peau
PEAU_BAS, PEAU_HAUT, PEAU_GAIN = 0.07, 0.97, 1.14
BLOC = 1.6                     # taille d un pixel de voile, en unites du modele
LOS_L, LOS_H = 30.0, 26.0      # losange : 4 a 5 par rangee comme la reference (15.6 en donnait 9)
TRAIT = 0.10                   # demi-epaisseur du reseau sombre (fraction de periode)
JAUNE_GAIN = 1.16             # la rampe vient d une capture eclairee : on remonte l albedo
JAUNE_BLEU = 0.70             # moins de bleu = or plus sature
FONDU = 15.0                   # bas de voile ou le reseau se fond dans la peau
# V83 : retour du joueur, « le quadrillage de la voile est moche » : la voile garde sa
# texture d'avant V81 (pixels d'origine, ni reseau de losanges ni lisere repeint).
VOILE_ANCIENNE = True


def hexa(c):
    return np.array(c, dtype=float) / 255.0


def rampe(couleurs, q):
    """Interpolation lineaire dans une rampe (liste de RGB 0..255), q dans [0, 1]."""
    r = np.array(couleurs, dtype=float) / 255.0
    x = np.clip(q, 0, 1) * (len(r) - 1)
    i = np.clip(np.floor(x).astype(int), 0, len(r) - 2)
    f = (x - i)[..., None]
    return r[i] * (1 - f) + r[i + 1] * f


def classe(nom, face):
    if nom.startswith(INTACT):
        return 'intact'
    if nom.startswith(BOUCHE):
        return 'bouche'
    if nom.startswith(ROUGE):
        return 'rouge'
    if nom.startswith('V69_voile') and face in ('east', 'west'):
        return 'voile'
    if nom.startswith(('V69_voile', 'V69_bord_voile')):
        return 'bord'
    return 'peau'


def rect(uv, W, H):
    x0, x1 = sorted((uv[0], uv[2])); y0, y1 = sorted((uv[1], uv[3]))
    return (max(0, int(math.floor(x0))), max(0, int(math.floor(y0))),
            min(W, int(math.ceil(x1))), min(H, int(math.ceil(y1))))


def rang(v):
    o = np.argsort(v, kind='stable')
    q = np.empty(len(v)); q[o] = np.arange(len(v)) / max(1, len(v) - 1)
    return q


def hachage(a, b):
    """Bruit deterministe dans [0, 1) par bloc."""
    x = np.sin(a * 12.9898 + b * 78.233) * 43758.5453
    return x - np.floor(x)


def peint(bb, log=print):
    src = bb['textures'][0]['source']
    im = Image.open(io.BytesIO(base64.b64decode(src.split(',', 1)[1]))).convert('RGBA')
    A = np.asarray(im).astype(float) / 255.0
    H, W = A.shape[:2]
    rgb = A[..., :3].copy()
    carte = np.zeros((H, W), dtype=np.int8)
    for e in bb['elements']:
        for fn, fd in e['faces'].items():
            if not fd.get('uv'):
                continue
            x0, y0, x1, y1 = rect(fd['uv'], W, H)
            p = PRIO[classe(e['name'], fn)]
            zone = carte[y0:y1, x0:x1]
            np.maximum(zone, p, out=zone)

    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    mx = rgb.max(-1); mn = rgb.min(-1); sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    teinte = np.zeros_like(mx)
    d = np.maximum(mx - mn, 1e-6)
    r_, g_, b_ = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    teinte = np.where(mx == r_, ((g_ - b_) / d) % 6, np.where(mx == g_, (b_ - r_) / d + 2, (r_ - g_) / d + 4)) / 6.0
    brun = ((teinte > 0.01) & (teinte < 0.14) & (sat < 0.85)) | (sat < 0.18)

    # --- peau
    m = (carte == PRIO['peau']) & brun
    q = rang(lum[m])
    rgb[m] = np.clip(rampe(PAL['peau'], PEAU_BAS + q * (PEAU_HAUT - PEAU_BAS)) * PEAU_GAIN, 0, 1)
    log('peau    : %d pixels recolores, %d gardes (non bruns : yeux, details)' %
        (m.sum(), ((carte == PRIO['peau']) & ~brun).sum()))
    # --- gueule
    m = carte == PRIO['bouche']
    rgb[m] = rampe(PAL['rouge_tete'][6:] + PAL['bouche'][2:], rang(lum[m]))
    log('gueule  : %d pixels vers le rose' % m.sum())
    # --- arcades
    m = carte == PRIO['rouge']
    rgb[m] = rampe(PAL['rouge_tete'][4:], rang(lum[m]))
    log('arcades : %d pixels vers le rouge' % m.sum())
    if VOILE_ANCIENNE:
        log('voile   : texture d origine conservee (%d pixels de voile et de lisere)'
            % ((carte == PRIO['voile']) | (carte == PRIO['bord'])).sum())
    else:
        # --- liseré et dessus de la voile
        m = carte == PRIO['bord']
        sombre = PAL['voile_sombre'][3:12]
        rgb[m] = rampe(sombre, 0.25 + 0.5 * rang(lum[m]))
        log('lisere  : %d pixels brun sombre' % m.sum())
        # --- cotes de la voile : reseau de losanges en coordonnees du monde
        plaques = [e for e in bb['elements'] if e['name'].startswith('V69_voile_')]
        zmin = min(e['from'][2] for e in plaques); zmax = max(e['to'][2] for e in plaques)
        ybas = min(e['from'][1] for e in plaques)
        zc = (zmin + zmax) / 2
        n_v = 0
        for e in plaques:
            uv = e['faces']['west']['uv']
            u0, u1 = sorted((uv[0], uv[2])); v0, v1 = sorted((uv[1], uv[3]))
            x0, y0, x1, y1 = rect(uv, W, H)
            uu, vv = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
            z = e['from'][2] + (uu - u0) / (u1 - u0) * (e['to'][2] - e['from'][2])
            y = e['to'][1] - (vv - v0) / (v1 - v0) * (e['to'][1] - e['from'][1])
            zb = (np.floor((z - zmin) / BLOC) + 0.5) * BLOC + zmin
            yb = (np.floor((y - ybas) / BLOC) + 0.5) * BLOC + ybas
            P = (zb - zc) / LOS_L + (yb - ybas) / LOS_H
            Q = (zb - zc) / LOS_L - (yb - ybas) / LOS_H
            fp, fq = P - np.floor(P), Q - np.floor(Q)
            dl = np.minimum(np.minimum(fp, 1 - fp), np.minimum(fq, 1 - fq))
            dc = np.maximum(abs(fp - 0.5), abs(fq - 0.5)) * 2
            h = hachage(zb, yb)
            jaune = np.clip(rampe(PAL['voile_jaune'][1:], np.clip(1 - 0.75 * dc + 0.18 * (h - 0.5), 0, 1)) * JAUNE_GAIN, 0, 1)
            jaune[..., 2] *= JAUNE_BLEU                # or plus sature : la rampe tirait sur le kaki
            trait = rampe(sombre, 0.2 + 0.5 * h)
            c = np.where((dl < TRAIT)[..., None], trait, jaune)
            # bord superieur de chaque plaque : liseré sombre, comme sur la reference
            c = np.where(((e['to'][1] - yb) < BLOC)[..., None], trait, c)
            # base : le reseau se defait dans la peau
            f = np.clip((yb - ybas) / FONDU, 0, 1)
            peau = rampe(PAL['peau'], PEAU_BAS + hachage(zb * 1.7, yb * 2.3) * (PEAU_HAUT - PEAU_BAS))
            c = np.where((hachage(zb * 3.1, yb * 0.7) > f * f)[..., None], peau, c)
            grain = 1 + 0.04 * (hachage(uu, vv) - 0.5)[..., None]
            rgb[y0:y1, x0:x1] = np.clip(c * grain, 0, 1)
            n_v += (x1 - x0) * (y1 - y0)
        log('voile   : %d pixels, reseau de losanges %.1f x %.1f u, pixels de %.1f u' % (n_v, LOS_L, LOS_H, BLOC))

    A[..., :3] = rgb
    out = Image.fromarray((A * 255 + 0.5).astype(np.uint8), 'RGBA')
    buf = io.BytesIO(); out.save(buf, 'PNG', optimize=True)
    bb['textures'][0]['source'] = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
    return out


if __name__ == '__main__':
    bb = json.load(open(sys.argv[1]))
    out = peint(bb)
    json.dump(bb, open(sys.argv[2], 'w'), separators=(',', ':'))
    if len(sys.argv) > 3:
        out.save(sys.argv[3])
    print('ecrit', sys.argv[2])
