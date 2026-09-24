import sys, json, os
sys.path.insert(0, 'tools')
import compare_gif as C, zdetect
D = '/tmp/claude-0/-home-user-vinted-flipper/8f65afb8-a44d-5883-ae6a-8bf69a8dd306/scratchpad/gifs80'
os.makedirs(D, exist_ok=True)
ORIG = 'modelzip/RIVIERE_70_ADAPTATION_ROR(1).bbmodel'
V77, V79, V80 = 'RIVIERE_77_SPINO.bbmodel', 'RIVIERE_79_SPINO.bbmodel', '../V80_rendu.bbmodel'
quoi = sys.argv[1:] or ['tout']
def veut(k): return 'tout' in quoi or k in quoi

if veut('course'):
    C.fabrique(D + '/01_course_ror.gif', V79, V80, 'course_ror', 'V79', 'V80',
               'moonwalk : le pied pose avance', 'pied pose qui recule, genou qui plie',
               n=38, az=90, el=5, duree=66, reperes=True, boucle=True)
if veut('couche'):
    C.fabrique(D + '/02_se_couche_ror.gif', V79, V80, 'se_couche_ror', 'V79', 'V80',
               'finit DEBOUT', 'se couche vraiment', n=40, az=90, el=6, duree=70, reperes=True)
if veut('assis'):
    C.fabrique(D + '/03_assis_ror.gif', V79, V80, 'assis_ror', 'V79', 'V80',
               'debout', 'couche, tete haute (port ROR)', n=40, az=70, el=10, duree=80, reperes=True, boucle=True)
if veut('virage'):
    C.fabrique(D + '/04_virage.gif', V79, V80, 'virage_serre_droite', 'V79', 'V80',
               'patte : saut de 57 deg au raccord', 'boucle periodique, pieds plantes',
               n=48, az=20, el=12, duree=66, reperes=True, boucle=True, L=3.2)
if veut('zfight'):
    zf = zdetect.paires(json.load(open(V79)))
    surl = set()
    from boite import FACES
    def aire(e, f):
        u, v = FACES[f][2]
        return abs(e['to'][u] - e['from'][u]) * abs(e['to'][v] - e['from'][v])
    # seule la plus petite des deux faces est peinte : c est elle qui correspond a la
    # zone reellement en conflit (le liseré du bord de voile, pas toute la voile)
    for ar, a, fa, b, fb, meme in zf:
        surl.add((a['uuid'], fa) if aire(a, fa) <= aire(b, fb) else (b['uuid'], fb))
    C.tourne(D + '/05_scintillement.gif', V79, V80, 'V79 : en rouge, ce qui scintillait', 'V80',
             '83 paires de faces coplanaires', '0 paire', n=44, el=14, duree=80, surl_g=surl)
if veut('degats'):
    C.fabrique(D + '/06_degats.gif', V80, V80, 'degats', 'degats', 'degats_eau',
               'coup recu au sol', 'coup recu en nageant', anim_d='degats_eau',
               n=30, az=55, el=10, duree=60, boucle=True, L=1.2)
if veut('saut'):
    C.solo(D + '/07_saut.gif', V80, 'saut', 'saut  (nouveau)', 'ramasse, vol pattes repliees, reception',
           n=36, az=78, el=8, duree=60)
if veut('chute'):
    C.solo(D + '/08_chute.gif', V80, 'chute', 'chute  (nouveau)', 'pattes en avant, bras ecartes, en boucle',
           n=32, az=40, el=12, duree=60)
if veut('mort'):
    C.fabrique(D + '/09_mort_eau.gif', V80, V80, 'mort', 'mort (terrestre)', 'mort_eau  (nouveau)',
               'ce que le jeu jouait sous l eau', 'bascule sur le flanc et coule', anim_d='mort_eau',
               n=46, az=60, el=12, duree=90)
if veut('boiterie'):
    C.fabrique(D + '/10_boiterie.gif', V77, V80, 'marche_boiteuse', 'V77', 'V80',
               'roulis jusqu a +22 deg, jamais de retour', 'roulis +/-5, pied pose immobile',
               n=44, az=7, el=8, duree=66, reperes=True, boucle=True)
if veut('flair'):
    C.fabrique(D + '/11_renifle_air.gif', ORIG, V80, 'renifle_air', 'ORIGINE', 'V80',
               'le crane descend', 'museau au ciel', n=42, az=90, el=6, duree=70)
if veut('geo'):
    C.tourne(D + '/12_geometrie.gif', ORIG, V80, 'MODELE 70 (origine)', 'MODELE 80',
             'voile, bras, griffes d origine', 'voile profil C, bras, nageoires, griffes x1.40',
             n=44, el=13, duree=78)
