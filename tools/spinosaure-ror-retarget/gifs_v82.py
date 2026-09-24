import sys, os
S = '/tmp/claude-0/-home-user-vinted-flipper/8f65afb8-a44d-5883-ae6a-8bf69a8dd306/scratchpad/'
sys.path.insert(0, S); sys.path.insert(0, 'tools')
import compare_gif as C, gif
from gros_plan import gros_plan, cadre_os, pose
from PIL import Image, ImageDraw
D = S + 'gifs82'
os.makedirs(D, exist_ok=True)
V81, V82 = 'RIVIERE_81_SPINO.bbmodel', 'RIVIERE_82_SPINO.bbmodel'
quoi = sys.argv[1:] or ['tout']
def veut(k): return 'tout' in quoi or k in quoi
MAIN = ('hand_left', 'finger_left_0', 'finger_left_1', 'finger_left_2')

if veut('palmes'):
    cas = [('pose_reference', 0, 90, 5), ('pose_reference', 0, 30, -30), ('nage_sous_eau', 0.5, 200, 60), ('pose_reference', 0, 150, 20)]
    gros_plan(V81, cas, MAIN, '/tmp/_p81.png', surligne_prefixes=('V74_nageoire_main',))
    gros_plan(V82, cas, MAIN, '/tmp/_p82.png', surligne_prefixes=('V82_palmure',))
    gros_plan(V82, cas, MAIN, '/tmp/_p82t.png')
    ims = [Image.open(p) for p in ('/tmp/_p81.png', '/tmp/_p82.png', '/tmp/_p82t.png')]
    tit = ['V81 : palmure (en rouge) inclinee a l envers, coupe les doigts comme une lame',
           'V82 : une palmure par doigt externe, dans le plan du doigt (en rouge)',
           'V82 : rendu texture final']
    o = Image.new('RGB', (ims[0].width, sum(i.height + 24 for i in ims)), (40, 40, 46)); d = ImageDraw.Draw(o); y = 0
    for im, t in zip(ims, tit):
        d.text((8, y + 5), t, fill=(235, 235, 235), font=C.FP); o.paste(im, (0, y + 24)); y += im.height + 24
    o.save(D + '/01_palmes_avant_apres.png'); print('ecrit', D + '/01_palmes_avant_apres.png')

if veut('palmes_anim'):
    A = C.prepare(V82); taille = (420, 360); frames = []
    for nom, az, el in (('nage_sous_eau', 200, 50), ('attaque_saut_eau_ror', 100, -15), ('grimpe', 20, 10)):
        a = A[4][nom]; L = a['length']
        sc = cadre_os(A[1], pose(A, nom, L * 0.4), MAIN, taille, az, el, marge=0.75)[0]
        for i in range(36):
            u = L * i / 36
            P = pose(A, nom, u)
            sf, cxf, cyf = cadre_os(A[1], P, MAIN, taille, az, el, marge=0.75)   # la camera suit la main
            cx = taille[0] / 2 - (taille[0] / 2 - cxf) / sf * sc
            cy = taille[1] / 2 + (cyf - taille[1] / 2) / sf * sc
            im = gif.rendu_z(A[1], A[2], A[3], P, taille, sc, cx, cy, az, el, (30, 32, 40), set())
            ImageDraw.Draw(im).text((8, 6), '%s  t=%.2f' % (nom, u), fill=(235, 235, 235), font=C.FP)
            frames.append(im.convert('P', palette=Image.ADAPTIVE, colors=200))
    frames[0].save(D + '/02_palmes_en_mouvement.gif', save_all=True, append_images=frames[1:], duration=80, loop=0, disposal=2)
    print('ecrit', D + '/02_palmes_en_mouvement.gif')

if veut('grimpe'):
    C.fabrique(D + '/03_grimpe_avant_apres.gif', V81, V82, 'grimpe', 'grimpe V81', 'grimpe V82',
               'marche sur place, bras dans le vide', 'cabre, prises alternees, main fixe au mur',
               n=56, az=62, el=10, duree=60, boucle=True, L=2.8 * 2)
if veut('grimpe_face'):
    C.solo(D + '/04_grimpe_trois_quarts.gif', V82, 'grimpe', 'grimpe V82',
           'traction gauche / genou droit, puis l inverse', n=56, az=25, el=14, duree=50)
