# Portage des animations ROR vers le rig RIVIERE (spinosaure)

Outillage isolé, sans rapport avec le reste du dépôt : il vit sur cette branche
uniquement. Il extrait les animations du spinosaure de **Raxio ROR** (avec accord
de l'auteur) et les retargete sur le rig bedrock `RIVIERE_70_ADAPTATION_ROR`.

## Pourquoi ce n'est pas une simple copie

Les animations ROR ne sont pas en JSON : elles sont compilées en bytecode dans
`net/mcreator/raxioresagain/client/model/animations/spino_*.class`
(`net.minecraft.client.animation.AnimationDefinition`). Il faut décompiler, puis
convertir d'espace.

## Conventions d'espace (établies empiriquement, pas devinées)

Entre l'espace modèle Java (Y vers le bas) et l'espace bedrock du bbmodel :

| canal    | conversion                  |
|----------|-----------------------------|
| rotation | `(x, y, z) -> (-x, +y, -z)` |
| position | inchangée                   |
| échelle  | inchangée                   |

Vérifiée par trois recoupements indépendants sur des mouvements de sens connu :

1. **mâchoire** — ROR ouvre à `+48/+57`, le rig RIVIERE ouvre à `-40/-44` → X s'inverse.
2. **cou** — somme de la chaîne ROR en rugissement `-18`, RIVIERE `+25` → X s'inverse.
3. **bras** — l'armé du bras gauche est `z=-83` chez ROR, `z=+31` chez RIVIERE (Z s'inverse),
   tandis que Y garde le même signe et un ordre de grandeur comparable (`-12` vs `-8`).

Le miroir `diag(1,-1,1)` prédit exactement ce triplet de signes.

## Correspondance des squelettes

ROR a 52 os, RIVIERE 36. Les chaînes sont repliées par composition des deltas
(les deux moteurs appliquent l'animation en écart par rapport à la pose de repos) :

- cou : `Neck+Neck2+Neck3` → `neck`, `Neck4+Head` → `head`
- jambe : `Leg4` → `thigh`, `Leg5+Leg6` → `shin`, `Foot4` → `foot`
- tronc : `Body+RotZ` → `body`, `Body2` → `chest`, `fin` → `sail`
- les os de gigotement (`shaker*`, `leg_shaker*`) sont repliés à poids réduit

Les gains par os compensent les différences de proportions et de pose de repos ;
ils sont calés sur les amplitudes déjà employées par les animations maison.

## Couches ajoutées « à notre sauce »

- `sail_rework` : la voile traîne sur le mouvement du tronc (inertie), amplitude
  volontairement sobre — c'est une structure osseuse, pas un drapeau.
- `throat_vibe` : flottement de la poche gulaire (6 Hz, soit 5 images par cycle
  à 30 fps, donc pas de repliement de spectre).
- `tail_follow` / `tail_six` : inertie de queue, dosée par dichotomie sous
  contrainte FK pour que la queue ne traverse jamais le sol.
- `tongue_follow` : la langue suit la mâchoire avec un temps de retard.
- `ground_clamp` : remonte le root (jamais vers le bas) pour qu'aucune pièce ne
  passe sous le plancher du modèle — indispensable, les jambes ROR n'ont pas les
  mêmes proportions et enfonçaient les pieds de 35 unités dans le sol.

## Chaîne de commandes

```bash
unzip -q ror.jar -d jar
java -jar cfr.jar jar/net/mcreator/raxioresagain/client/model/animations/spino_*.class --outputdir dec
python3 tools/parse_anim.py dec/net/mcreator/.../spino_*.java     # -> ror_anims.json
python3 tools/build.py                                            # -> *_UPDATED.bbmodel
python3 tools/validate.py <bbmodel> [filtres]                     # contrôle FK
python3 tools/render.py  <bbmodel> <anim> <t1,t2,...> out.png     # aperçu de profil
```

`validate.py` compare chaque animation au plancher du modèle (`-62.76`) et aux
animations maison prises comme référence de normalité.

## Recuit des animations (recook.py)

Le bbmodel pesait 45 Mo dont **34 Mo de JSON d'animation** : 200 313 clés, parce que
tout est cuit image par image à 30-60 fps. La texture (4096x4096) ne pèse que 10.8 Mo
et la géométrie 0.4 Mo — c'est bien l'animation qui fait ramer Blockbench, via le
nombre d'objets clés à gérer dans la timeline.

Les pistes sont **100 % linéaires** (vérifié : 192 279 clés, zéro interpolation
bézier ou catmull-rom, zéro expression Molang). Supprimer les points colinéaires est
donc exact, et l'écart maximal d'une approximation linéaire par sous-ensemble se
produit **exactement aux temps des clés supprimées** : on peut mesurer l'erreur
réelle au lieu de l'estimer.

### Tolérance par bras de levier

Une tolérance angulaire uniforme est un mauvais réglage : 0.02 deg sur le `root`
(bras de levier 168 u) déplace la queue de 0.06 u, alors que la même tolérance sur
un doigt (20 u) ne déplace rien. `tol_per_bone()` dérive donc la tolérance de chaque
os de son bras de levier, pour un budget d'écart cumulé sur toute la chaîne.

Mesures sur les 63 animations (écart max en unités du modèle, qui fait 260 u de long) :

| réglage            | clés   | Mo   | gain | écart max |
|--------------------|--------|------|------|-----------|
| adaptatif 0.05 u   | 73 319 | 13.4 | 62 % | 0.036 u   |
| **adaptatif 0.15 u** | **60 869** | **11.2** | **69 %** | **0.077 u** |
| adaptatif 0.40 u   | 47 611 |  8.8 | 75 % | 0.212 u   |
| uniforme 0.02 deg  | 59 805 | 11.0 | 69 % | 0.183 u   |
| uniforme 0.06 deg  | 45 331 |  8.4 | 77 % | 0.441 u   |
| uniforme 0.30 deg  | 26 726 |  5.0 | 86 % | 2.276 u   |

L'adaptatif domine : à taille égale, deux fois moins d'erreur. Réglage retenu :
**adaptatif 0.15 u**, soit 0.077 u d'écart maximal — 0.03 % de la longueur du modèle.

### Garanties

`recook.py` ne **réécrit jamais une valeur** : il ne fait que supprimer des clés
existantes. `verify_recook.py` le prouve sur le fichier produit :

1. géométrie, squelette, texture strictement identiques
2. métadonnées d'animation et liste d'animateurs préservées
3. chaque clé restante est un objet identique à l'original (sous-ensemble strict)
4. bornes temporelles de chaque piste préservées
5. boucles toujours refermées

Contrôle visuel complémentaire par différence de pixels sur des rendus de profil :
`course` (l'animation maison la plus dense) rend **0 pixel de différence** ;
`endormissement` (pire cas mesuré) 136 pixels sur 660 000, soit 0.02 %, uniquement
des bascules de rastérisation d'un pixel sur des traits à bord dur.

```bash
python3 tools/recook.py <bbmodel> scan            # tableau comparatif des reglages
python3 tools/recook.py <bbmodel> F <sortie>      # applique l adaptatif 0.15 u
python3 tools/verify_recook.py <avant> <apres>    # prouve que rien d autre n a bouge
```
