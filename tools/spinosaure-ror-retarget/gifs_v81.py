import sys, os
sys.path.insert(0, 'tools')
import compare_gif as C, gif
from PIL import Image, ImageDraw
D = '/tmp/claude-0/-home-user-vinted-flipper/8f65afb8-a44d-5883-ae6a-8bf69a8dd306/scratchpad/gifs81'
IMG = '/tmp/claude-0/-home-user-vinted-flipper/8f65afb8-a44d-5883-ae6a-8bf69a8dd306/images/'
os.makedirs(D, exist_ok=True)
V80, V81 = 'RIVIERE_80_SPINO.bbmodel', 'RIVIERE_81_SPINO.bbmodel'
quoi = sys.argv[1:] or ['tout']
def veut(k): return 'tout' in quoi or k in quoi

def pose(A, nom, u):
    T = C.pistes(A[4][nom])
    return A[1].pose(lambda b, c: (C.lp(T[b][c], u) if b in T and c in T.get(b, {})
                                   else ([1., 1., 1.] if c == 'scale' else [0., 0., 0.])))

def vue(chemin, nom, u, taille, az, el, fond, titre=''):
    A = C.prepare(chemin)
    sc, cx, cy = gif.cadre(A[1], [pose(A, nom, u)], taille, az, el)
    return C.bande(taille, A[4][nom], A[1], A[2], A[3], titre, '', u, sc, cx, cy, az, el, fond)

def planche(gauche, droite, sortie, tg, td):
    w = gauche.width + droite.width + 6; h = max(gauche.height, droite.height) + 26
    o = Image.new('RGB', (w, h), (40, 40, 46)); d = ImageDraw.Draw(o)
    o.paste(gauche, (0, 26)); o.paste(droite, (gauche.width + 6, 26))
    d.text((8, 6), tg, fill=(235, 235, 235), font=C.FP); d.text((gauche.width + 14, 6), td, fill=(235, 235, 235), font=C.FP)
    o.save(sortie); print('ecrit', sortie)

if veut('ref1'):
    ref = Image.open(IMG + '1.png').convert('RGB').resize((700, 410))
    planche(ref, vue(V81, 'hurle_long', 1.2, (700, 410), -62, 10, (236, 236, 236)),
            D + '/A_reference_texture.png', 'TA REFERENCE (texture)', 'V81, meme angle')
if veut('ref2'):
    ref = Image.open(IMG + '2.png').convert('RGB').resize((545, 366))
    planche(ref, vue(V81, 'repos', 0.0, (720, 366), 90, 4, (214, 208, 170)),
            D + '/B_reference_silhouette.png', 'TA REFERENCE (silhouette)', 'V81, profil (notre tete gardee)')
if veut('tourne'):
    C.tourne(D + '/01_avant_apres.gif', V80, V81, 'V80', 'V81',
             'ancienne texture, queue qui plonge', 'texture de ta reference, queue droite',
             n=44, el=12, duree=80)
if veut('regard'):
    C.fabrique(D + '/02_marche_regard_fixe.gif', V81, V81, 'marche_regard_fixe_droite',
               'marche_regard_fixe_droite', 'marche_regard_fixe_gauche',
               'bascule en 3 images, tete verrouillee', 'le corps marche, le regard ne bouge plus',
               anim_d='marche_regard_fixe_gauche', n=54, az=8, el=14, duree=66)
if veut('mange'):
    C.fabrique(D + '/03_mange_regard.gif', V81, V81, 'mange_carcasse', 'mange_carcasse (inchangee)',
               'mange_carcasse_regard_droite', 'repas normal', 'il releve la tete, te fixe, se fige',
               anim_d='mange_carcasse_regard_droite', n=66, az=35, el=12, duree=80)
