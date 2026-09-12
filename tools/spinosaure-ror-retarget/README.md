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
