# Spinosaure — mod Forge 1.20.1 + GeckoLib

Un spinosaure amphibie dont l'IA est pensée pour le **multijoueur** : il choisit sa cible,
change de tactique selon le nombre de joueurs et ne se laisse pas exploiter par les
astuces classiques (pilier, bouclier, encerclement).

## Ce qu'il fait

| Situation | Réaction |
|---|---|
| Plusieurs joueurs | Il choisit sa cible par score : menace récente, vie et armure du joueur, **isolement**, terrain (un joueur dans l'eau est vulnérable), rancune. Une hystérésis l'empêche de changer de cible à chaque tick. |
| La cible est entourée d'alliés | Il l'attaque **par le côté opposé** à ses alliés, qui doivent la contourner pour l'aider. |
| Un groupe de 3 arrive | Il rugit une fois par rencontre, avant le contact : Lenteur II et Faiblesse pendant 3 s pour tous dans un rayon de 16 blocs. |
| Joueurs dans son dos | Balayage de queue sur 360° avec recul. |
| Bouclier levé | Griffes qui désactivent le bouclier. Si elles sont en recharge, il passe sur le flanc. |
| Tireur sur un pilier, inatteignable | S'il y a une autre cible accessible, il va sur elle. S'il n'y a que le tireur, il **plonge** pour rompre la ligne de tir, ou s'éloigne hors de portée. |
| Cible bloquée (aucun progrès en 5 s) | Il la déclare inatteignable 15 s et en prend une autre. |
| Joueur dans l'eau | Il le **saisit** et l'entraîne au fond. Ses alliés le libèrent en infligeant 20 dégâts au spinosaure. La victime se libère en en infligeant 12. Le maintien dure 6 s au maximum. |
| Proie seule et distraite | **Traque** à pas feutrés. Si on le regarde, il **se fige**. Au bout de 4,5 s de regard, il attaque. |
| Près de l'eau | Affût submergé, puis jaillissement. |
| Moins de 30 % de vie et en infériorité | **Repli** vers l'eau profonde. Il se soigne au fond (+2 PV/s), puis revient en embuscade sur celui qui lui en veut le plus. |
| Pas d'eau et moins de 15 % de vie | Acculé, il se bat jusqu'au bout. |
| Plus personne en vue | Il va à la dernière position connue et renifle la piste. La **rancune** prolonge sa mémoire. |
| Perception | Vue en cône de 220° avec ligne de vue. Ouïe : 24 blocs pour un sprint, 12 pour une marche, 4 accroupi. Les joueurs invisibles ne sont qu'entendus. |

Toutes les attaques sont **télégraphiées**. Le coup porte à l'instant où on le voit porter dans
l'animation (fermeture de la mâchoire, bras au plus rapide), instant mesuré sur le fichier
d'animation. À plusieurs, un joueur attentif peut donc esquiver.

Une barre de vie de boss apparaît pour tous les joueurs proches pendant le combat.

## Déplacements

Le cerveau décide où aller et à quelle allure. Le **pilote** (`cerveau/Pilote.java`) décide
comment un animal de 13 blocs y va :

| Comportement | Détail |
|---|---|
| Rayon de braquage | 0,7 bloc au pas, 3 blocs en course, 5,3 en charge. Le déplacement vanilla le faisait pivoter de 90° par tick. |
| Inertie | Il met 1,6 s pour passer de l'arrêt à la course, et freine progressivement. S'il s'arrête en pleine course, il joue `ralentissement_course_arret`. |
| Freinage avant les virages | Il lit les nœuds du chemin à venir et ralentit pour ne pas déborder de plus de 1,5 bloc. Il ralentit aussi quand le point visé est dans son cercle de braquage, au lieu d'orbiter autour. |
| Pivot sur place | Si la destination est derrière lui à l'arrêt, il tourne sur place (`tourne_sur_place`, 90°/s). |
| Virages rapides | Il penche dans le virage (`virage_serre_gauche`/`droite`). |
| Chemins en diagonale | La grille vanilla produit des escaliers. Il vise la moyenne des nœuds des 4 prochains blocs, avec une correction de cap amortie. Cap mesuré sur une diagonale : 0,67°/tick, contre 4,5 en visant le nœud suivant. |
| Endurance | 12 s de course ou 5 s de charge l'essoufflent : il marche le temps de récupérer. Un joueur qui court longtemps peut le semer. |
| Charge engagée | Elle part vers le point où le joueur sera (interception), prolongé de 6 blocs, sans correction ensuite. Elle ne touche que sur l'axe du corps, jusqu'au museau, et renverse ce qui se trouve sur la ligne. Un pas de côté l'évite. Lancé, il dépasse de plus de 9 blocs avant de revenir : c'est la fenêtre de contre-attaque. |
| Interception | Il vise où le joueur sera, pas où il est : un fuyard en ligne droite se fait couper la route. |
| Terrain | 48 points lus dans les cartes de hauteur toutes les 2 s : eau et profondeur, dénivelé, et danger selon le classement de pathfinding de Minecraft (lave, feu, cactus, neige poudreuse). |
| Errance | Il patrouille les berges de son territoire, sauvegardé dans la partie. Il évite falaises et lave, et ne repasse pas par ses derniers points. |
| Repli | Il choisit l'eau profonde qui l'éloigne des joueurs, jamais une eau qu'il faudrait atteindre en leur passant au travers. |
| Déblocage | Mesuré en distance gagnée vers le but, pas en distance parcourue. Dans l'ordre : sauter (et arracher les feuilles), reculer, contourner par un côté puis par l'autre la fois suivante, abandonner. S'il abandonne, le cerveau raye la destination pour une minute, ou déclare la cible inatteignable. |

## Installer

1. JDK 17, puis dans ce dossier : `./gradlew runClient`.
2. **Exporter le modèle depuis Blockbench**, avec `RIVIERE_82_SPINO.bbmodel` ouvert :
   - Fichier → Exporter → *Export Bedrock Geometry* →
     `src/main/resources/assets/spinosaure/geo/spinosaure.geo.json`
   - Onglet Animer → Animation → *Export Animations* (toutes cochées) →
     `src/main/resources/assets/spinosaure/animations/spinosaure.animation.json`

   La texture est déjà en place, extraite du `.bbmodel`. Je n'ai pas écrit de
   convertisseur : l'export de Blockbench est la référence de GeckoLib, et une conversion
   maison risquait des inversions d'axes invisibles tant qu'on ne lance pas le jeu.
3. Œuf d'apparition dans l'onglet créatif « Œufs d'apparition ». Apparition naturelle
   rare dans les rivières et les marais.

## Régler

Tous les seuils sont dans `cerveau/Reglages.java` (portées, seuils de repli, hystérésis,
libération d'une saisie…). Les vitesses sont dans `Decision.Allure`, les dégâts et recharges
dans `Attaque`.

## Déboguer en jeu

```
/tag @e[type=spinosaure:spinosaure,limit=1,sort=nearest] add debug
```
Sa tactique et la raison de sa décision s'affichent au-dessus de sa tête, par exemple
`ENGAGEMENT : attaque par le cote oppose a ses allies`.

## Ce qui est vérifié, ce qui ne l'est pas

- **Le cerveau et le pilote** (`cerveau/`, sans aucune dépendance à Minecraft) : 36 tests
  JUnit, tous verts (`./gradlew test`). Les tests du pilote simulent le modèle cinématique de
  Minecraft : pivot, accélération, anti-orbite, freinage avant virage, dépassement après une
  charge ratée, essoufflement, stabilité du cap sur un chemin en escalier. S'y ajoutent
  l'échelle de déblocage, l'interception, le choix de l'eau de repli, l'errance sur les
  berges et l'abandon d'une destination bloquée. Ils couvrent le choix de cible, l'hystérésis, le tireur perché,
  l'encerclement, le bouclier, l'approche par le flanc, le repli, la traque, la saisie avec
  libération, la mémoire et le blocage.
- **La partie Minecraft** (`entite/`, `client/`) : **pas compilée contre le vrai Forge**, car
  les dépôts Forge et Mojang étaient inaccessibles depuis mon environnement. Je l'ai compilée
  contre des bouchons des API, ce qui valide la cohérence interne mais pas les signatures
  exactes. Points à surveiller à la première compilation :
  - la version `geckolib_version=4.4.9` dans `gradle.properties` : prendre la dernière 4.4.x
    pour 1.20.1 si elle diffère ;
  - `GeoEntityRenderer.withScale` ;
  - `Player.disableShield(boolean)` ;
  - `IForgeEntity.shouldRiderSit` ;
  - `WalkNodeEvaluator.getBlockPathTypeStatic`, utilisée pour classer le terrain dangereux.

## Limites connues

- Il ne réagit qu'aux **joueurs**. Un loup apprivoisé ou un golem qui l'attaque ne devient
  pas une cible.
- Le pathfinding vanilla gère mal les mobs larges. La boîte de collision fait 3,4 × 5 blocs
  (la largeur du corps) alors que le modèle mesure 13,4 blocs de long : la queue et le museau
  traversent les murs. Il peut aussi peiner en forêt dense (il arrache les feuilles qui le
  bloquent si `mobGriefing` est actif).
- Saisie : empêcher un joueur de descendre se fait côté serveur. Sur une connexion lente, le
  client peut afficher un bref décalage.
- La texture fait 4096², soit environ 64 Mo de mémoire vidéo. À réduire en 2048 si besoin :
  l'audit de l'atlas indique qu'il n'y aurait probablement aucune perte.
