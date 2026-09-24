"""Planche d'images d'une animation : n instants x plusieurs angles."""
import sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import compare_gif as C, gif
from PIL import Image

def planche(modele, nom, sortie, n=8, angles=((90, 8), (30, 12)), cote=(260, 240), reperes=True):
    A = C.prepare(modele); a = A[4][nom]
    lignes = []
    for az, el in angles:
        sc, cx, cy = gif.cadre(A[1], C.poses_de(a, A[1], 16), cote, az, el)
        ims = [C.bande(cote, a, A[1], A[2], A[3], nom.split('_')[0], 't=%.2f' % (a['length'] * i / n),
                       a['length'] * i / n, sc, cx, cy, az, el, (20, 21, 27), reperes,
                       C.sol_de(A[1]) if reperes else None) for i in range(n)]
        lignes.append(ims)
    o = Image.new('RGB', (cote[0] * n, cote[1] * len(lignes)), (60, 60, 70))
    for j, l in enumerate(lignes):
        for i, im in enumerate(l): o.paste(im, (i * cote[0], j * cote[1]))
    o.save(sortie); print('ecrit', sortie)

if __name__ == '__main__':
    planche(sys.argv[1], sys.argv[2], sys.argv[3])
