# Spinosaure — mod d'horreur Forge 1.20.1 + GeckoLib

Un spinosaure amphibie qui **traque** : il observe de loin, te file sans bruit, disparaît
quand tu le regardes de trop près, et ne frappe qu'à l'ouverture, avant de s'effacer. Ce
n'est pas un boss : il n'a pas de barre de vie et ne cherche pas le combat loyal.

## Ce qu'il fait

La tension monte avec le temps qu'il passe à te traquer :

| Phase | Durée de traque | Comportement |
|---|---|---|
| 1. Observation | 0 à 30 s | Il se poste à environ 28 blocs, de préférence dans l'eau, immobile, en respirant lourdement. Parfois sa tête se penche (`tete_inclinee_fixe`). |
| 2. Filature | 30 s à 1 min 30 | Il te suit **dans ton dos**, hors de ton champ de vision, à 16 blocs, à pas feutrés, sans bruit de pas. |
| 3. L'ouverture | au-delà | Il se rapproche à 10 blocs et attend que tu sois **isolé, dos tourné, à moins de 14 blocs**. Alors il jaillit : c'est son seul rugissement. |

| Situation | Réaction |
|---|---|
| Tu le regardes de près (moins de 24 blocs) | Il **disparaît** : il plonge dans l'eau la plus proche, ou s'enfuit hors de vue. |
| Tu le regardes de loin | Il se **fige** et soutient ton regard, puis s'efface au bout de 4,5 s. |
| Frappe éclair | Au plus 2 attaques ou 6 s, puis il s'efface avant qu'on riposte. La traque reprend plus tard. |
| Tu le blesses de loin | Il se dérobe, et reviendra plus décidé. |
| Tu le blesses au contact | Il riposte, frappe éclair comprise. |
| Groupe de joueurs | Il reste à distance et observe. Il frappe celui qui s'isole : la tension monte sur tous ceux qu'il surveille, donc celui qui s'écarte est déjà « mûr ». Au bout de 4 min de traque, il ose même dans un groupe. |
| Proie affaiblie (moins de 35 % de vie) et isolée | Il frappe plus tôt, dès la phase 2. |
| Joueur dans l'eau | C'est son domaine. Il approche par en dessous, le **saisit** et l'entraîne au fond. Ses alliés le libèrent en lui infligeant 20 dégâts, la victime en lui en infligeant 12. |
| Tireur perché, inatteignable | Il passe à une autre proie, ou plonge pour rompre la ligne de tir. |
| Blessé à moins de 30 % en infériorité | Il se replie dans l'eau profonde et s'y soigne, puis revient en embuscade sur celui qui lui en veut le plus. |
| Acculé, sans eau, presque mort | Il se bat jusqu'au bout. |
| Plus personne en vue | Il va à la dernière position connue et renifle la piste. La rancune prolonge sa mémoire. |
| Joueur en créatif | Il l'observe et le suit, mais ne l'attaque jamais. **Le combat se teste en survie.** |

| Hors de la jungle | Il n'y va pas. Si tu sors en plaine, il te regarde depuis la lisière et ne te suit pas. L'eau reste son domaine partout. Il n'apparaît qu'en jungle. |
| Joueur armé (TaCZ) | Il te file et t'observe de plus loin, de préférence à couvert : derrière un tronc, hors de ta ligne de vue, calculé par lancer de rayon. Un canon braqué sur lui à moins de 40 blocs : il disparaît. Jamais de charge de face contre un fusil braqué. |
| Tu nages | Il sent les remous à 40 blocs, même dans son dos, et se glisse dans l'eau vers toi. Accroupi, tu coules sans bruit. |
| Coups de feu | Il les entend à 96 blocs et va voir d'où ils viennent. Si le tireur le voit, il est « sous le feu » : il se met à couvert (eau, tronc, relief). |
| Rechargement | Arme vide : c'est son ouverture. Il frappe même si tu le regardes. |
| Le « directeur » (*Alien Isolation*) | Sans contact depuis 1 min, il reçoit ta zone approximative (à 16 blocs près) et s'en approche. Après 3 min de pression continue sans frapper, il se retire 80 s « en coulisses », puis revient. |

**Sons**
- Silence pendant l'observation, la filature, l'affût et la fuite.
- De temps en temps, une respiration grave : elle vient de sa position réelle, donc tu l'entends dans ton dos.
- Un rugissement quand il jaillit.
- Sa tête et son cou suivent ce qu'il regarde.

**Attaques**
- Elles sont télégraphiées : le coup porte quand on le voit porter.
- Au contact : balayage de queue si on l'encercle, griffes qui brisent les boucliers, morsure, et il tourne autour de sa proie entre deux coups.
- En surgissant : charge ou bond.

## Déplacements

Le cerveau décide où aller et à quelle allure. Le **pilote** (`cerveau/Pilote.java`) décide
comment un animal de 13 blocs y va :

| Comportement | Détail |
|---|---|
| Rayon de braquage | 1 bloc au pas, 3 blocs en course, 5,3 en charge. Le déplacement vanilla le faisait pivoter de 90° par tick. |
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

**Le jar** : il est construit automatiquement par GitHub à chaque modification (onglet
*Actions* du dépôt, workflow « Spinosaure - construire le jar », artefact `spinosaure-jar`).

**Le construire soi-même** (JDK 17 requis, rien d'autre : Gradle se télécharge seul) :

```
cd spinosaure-mod
gradlew.bat build        (Windows)
./gradlew build          (Mac / Linux)
```
Le jar sort dans `build/libs/spinosaure-0.2.0.jar`.

**Tester en survie** (`/gamemode survival`) : comme les mobs vanilla, il n'attaque pas un joueur
en créatif. En créatif il l'observe seulement : il le fixe, le suit à distance à pas feutrés
et se fige quand on le regarde.

**Jouer** : Minecraft 1.20.1 + Forge 47.x, et **GeckoLib 4.4.x pour Forge 1.20.1** dans le
dossier `mods` à côté du jar (le mod en dépend, il n'est pas inclus dedans).
Œuf d'apparition dans l'onglet créatif « Œufs d'apparition ». Apparition naturelle rare dans
les rivières et les marais.

**Modèle et animations** : `geo/spinosaure.geo.json` et `animations/spinosaure.animation.json`
sont générés depuis le `.bbmodel` par `tools/spinosaure-ror-retarget/export_geckolib.py`, qui
reproduit l'export bedrock de Blockbench (contrôle aller-retour : 384 cubes, écart 0,0001).
Si le modèle apparaissait en miroir ou déformé en jeu, remplacer ces deux fichiers par un
export Blockbench (*Export Bedrock Geometry* et *Export Animations*).

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
- **La partie Minecraft** (`entite/`, `client/`) : compilée par GitHub Actions contre le vrai
  Forge 1.20.1 et GeckoLib. **TaCZ** est détecté sans dépendance de compilation : objets et
  balles de l'espace de noms `tacz`, munitions lues dans la donnée `GunCurrentAmmoCount`.
  À vérifier en jeu si une version de TaCZ nomme ces éléments autrement. Anciens points de
  vigilance, résolus par la compilation :
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
