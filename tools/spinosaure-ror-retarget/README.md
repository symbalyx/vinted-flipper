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

## V71 : profil de voile et bras palmes

### Voile reprofilee (voile.py)

La voile est deja construite comme la reference visee : 12 dalles etagees plus un
liseré de 1 unite au sommet. L'ecart etait le profil — l'ancien etait a deux bosses
et restait haut a l'arriere. Profil retenu : **dome asymetrique**, sommet avance,
longue descente vers la queue (38 -> 67.3 -> 34).

Piege evite : **changer la hauteur d'une dalle sans re-mapper son UV etire la
texture**. L'aspect changerait alors qu'aucun pixel n'aurait bouge. `voile.py`
re-mappe donc chaque flanc a la densite propre de la dalle (7.450 px/unite),
en gardant le bas fixe puisque la voile est alignee par le bas. La bande de
camouflage peinte s'arrete a v=1272, ce qui plafonne les dalles a ~83 unites ;
le script le verifie par assertion.

Seules les faces east/west portent la texture haute. north, south, up et down
pointent toutes sur un petit patch generique deja partage par les 12 dalles quelles
que soient leurs hauteurs (40 a 64) : le modele ne leur demande aucune coherence de
densite, on n'y touche pas.

### Bras palmes (bras_ror.py)

Ce qui valait la peine d'etre repris de ROR n'etait pas sa geometrie mais deux idees
anatomiques que le rig RIVIERE n'avait pas : la **palmure interdigitale**
(plans 19x0x15 chez ROR) et la **membrane d'avant-bras** (plan 0x25x46). Plus des
griffes nettement plus imposantes (15 u chez ROR contre 6.5 u ici).

Trois choix qui font la difference entre un portage et un copier-coller :

1. **Volumes pleins, pas des plans.** Le modele RIVIERE n'utilise aucun element a
   epaisseur nulle (0 sur 374) et aucun inflate ; 313 de ses cubes ont leur propre
   rotation. C'est un modele sculpte en volumes. Les plans de ROR y seraient
   stylistiquement etrangers, et en jeu ils scintillent et disparaissent en
   incidence rasante.
2. **Aucun pixel de texture ajoute.** Les cubes de main et de doigts du modele
   partagent deja tous un meme rectangle UV, les griffes un autre. La nouvelle
   geometrie pointe sur ces memes patchs : elle herite de la peau existante.
3. **La palmure est rattachee a la main, pas a un doigt.** Un cube rigide entre deux
   doigts se dechire des qu'ils divergent. Mesure avant correction : 26.5 deg
   d'ecart dans attaque_saut_sol_ror, soit 2.77 u de decollement pour une palmure
   large de 2.6 u.

`finger_converge()` dans build.py borne l'ecart ENTRE doigts voisins a 12 deg
(le mouvement commun des doigts est integralement conserve, seul leur ecartement
relatif est resserre). Resultat mesure : ecart 12.0 deg, jeu 0.63 u au bout de la
palmure, pour une prise de 1.61 u dans chaque doigt. Les animations d'origine ne
sont pas concernees : leur divergence etait deja sous le seuil.

### Bilan V71

| | avant | apres |
|---|---|---|
| elements | 374 | 384 (10 ajoutes, 0 supprime, 42 modifies) |
| animations | 63 | 63 |
| cles | 200 526 | 61 429 |
| poids | 45 Mo | 21.5 Mo |
| texture | | identique a l octet pres |
| ecart sur les 50 animations d origine | | 0.077 unite |

## V72 : pagaie, saut amplifie, 5 animations maison

### La palmure etait invisible

Premiere version : une feuille de 0.7 d'epaisseur logee dans l'interstice entre
deux doigts. Or cet interstice fait 1.23 u pour des doigts epais de 2.5 : la
feuille etait noyee dedans. Retour a la source : chez ROR le plan de palmure fait
**19 u de large pour une main de 6** — c'est une pagaie qui deborde des doigts,
pas un bouche-trou. Corrige en deux feuilles pleine largeur (15.6 u pour une main
de 9.7), une par rangee de phalanges, debordant de 2.5 u de chaque cote.

### Le saut ne se lisait pas

Mesure : les pieds ne decollaient que de 28 u, contre 46 pour `bond_joueur`. Arc
du root repris : creuse a -6 pour l'elan, apex a +55, plongee a -22. Les pieds
montent maintenant a 81 u.

### 5 animations ecrites a la main

Pas portees du jar : composees a partir des animations existantes du modele
(`course`, `marche`, `repos`), donc sans suffixe `_ror`.

| animation | duree | construction |
|---|---|---|
| `virage_serre_gauche` / `_droite` | 1.25 s | `course` avec foulee interieure raccourcie (0.70) et exterieure allongee (1.18), roulis dans le virage, queue en contrepoids exterieur |
| `marche_eau_peu_profonde` | 2.4 s | `marche` ralentie ; le releve de patte n'est majore que pendant la phase aerienne, mesuree par FK, donc l'appui reste intact |
| `peche_gueule_eau` | 5.4 s | ecrite de zero : guet, frappe a vide, secousse, second guet, prise, deglutition (gorge qui se vide) |
| `ralentissement_course_arret` | 3.4 s | une seule phase de foulee partagee entre `course` et `marche`, cadence decroissante de 1.25 a 0 Hz : les appuis restent coherents pendant le fondu |

### Deux pieges rencontres

**Le signe de la queue.** Mesure directe : un offset X positif fait tomber le bout
de la queue de -42 a -80, un offset negatif le monte a -9.6. C'est donc le X
**negatif** qui releve la queue. Le raisonnement inverse (a partir de `course`,
dont la queue haute vient des segments profonds et non de `tail_01`) menait au
mauvais signe et enfoncait la queue dans le sol.

**Boite englobante contre geometrie reelle.** La pêche affichait 26 u de
penetration tete/torse en boites englobantes. Le test reel cube par cube (points
echantillonnes transformes dans le repere de chaque cube du torse) donne **zero**
penetration, comme pour les animations d'origine : la tete est allongee, sa boite
alignee aux axes deborde sans que la geometrie se touche. Le correctif applique
(moins d'enroulement du cou, pas en avant de 21 u) reste anatomiquement meilleur,
mais il ne corrigeait pas un vrai defaut.
