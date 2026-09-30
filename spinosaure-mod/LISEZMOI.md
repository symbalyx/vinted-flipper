# Spinosaure — mod d'horreur Forge 1.20.1 + GeckoLib

Un spinosaure amphibie qui **traque** : il observe de loin, te file sans bruit, se fige sous
ton regard puis avance sur toi, et frappe à l'ouverture avant de s'effacer. Il se bat contre
les créatures qui l'attaquent, mange ses proies, dort la nuit. Ce n'est pas un boss : il n'a
pas de barre de vie et ne cherche pas le combat loyal.

## Ce qu'il fait

La tension monte avec le temps qu'il passe à te traquer :

| Phase | Durée de traque | Comportement |
|---|---|---|
| 1. Observation | 0 à 12 s | Il se poste à environ 28 blocs, de préférence dans l'eau, immobile, en respirant lourdement. Parfois sa tête se penche, ou son cou tressaille. |
| 2. Filature | 12 à 36 s | Il te suit **dans ton dos**, hors de ton champ de vision, à 16 blocs, à pas feutrés (`marche_observation`), sans bruit de pas. |
| 3. L'ouverture | au-delà | Il se rapproche à 8 blocs et attend que tu sois **isolé, dos tourné, à moins de 18 blocs**. Alors il jaillit en hurlant (`hurle_en_courant`), puis se rue griffes en avant. |

(Les phases duraient 30 s et 1 min 30, et il s'effaçait dès qu'on le regardait à moins de
24 blocs : en jeu on le regarde tout le temps, il semblait ne rien faire. Les essais en jeu
« dos tourné » et « groupe » échouaient d'ailleurs, sans que la CI ne le signale.)

| Situation | Réaction |
|---|---|
| Tu le regardes de près (moins de 12 blocs) | Au début de la traque, il **disparaît** (plonge ou s'enfuit hors de vue). La traque mûre (phase 3), il **frappe**. |
| Tu le regardes de loin | Il se **fige** et soutient ton regard 3 s. Au début de la traque il s'efface ; ensuite il **avance sur toi** (`avance_menacante`, lentement les 20 derniers blocs) et frappe. Un tronc qui coupe la vue une seconde ne l'arrête pas. |
| Frappe éclair | Au plus 2 attaques ou 6 s, puis il s'efface avant qu'on riposte. La traque reprend plus tard. |
| Tu le blesses de loin | Il se dérobe, et reviendra plus décidé. |
| Tu le blesses au contact (moins de 10 blocs) | Il riposte, **toujours**, même s'il était en train de s'effacer ou de se retirer. |
| Groupe de joueurs | Il reste à distance et observe. Il frappe celui qui s'isole : la tension monte sur tous ceux qu'il surveille, donc celui qui s'écarte est déjà « mûr ». Au bout de 4 min de traque, il ose même dans un groupe. |
| Proie affaiblie (moins de 35 % de vie) et isolée | Il frappe plus tôt, dès la phase 2. |
| Joueur dans l'eau | C'est son domaine. Il approche par en dessous, le **saisit** et l'entraîne au fond. Ses alliés le libèrent en lui infligeant 20 dégâts, la victime en lui en infligeant 12. |
| Tireur perché, inatteignable | Il passe à une autre proie, ou plonge pour rompre la ligne de tir. |
| Blessé à moins de 30 % en infériorité | Il se replie dans l'eau profonde et s'y soigne, puis revient en embuscade sur celui qui lui en veut le plus. |
| Acculé, sans eau, presque mort | Il se bat jusqu'au bout. |
| Plus personne en vue | Il va à la dernière position connue et renifle la piste. La rancune prolonge sa mémoire. |
| Joueur en créatif | Il l'observe et le suit, mais ne l'attaque jamais, et tes coups ne comptent pas. **Le combat se teste en survie.** |
| Une créature l'attaque ou le vise | Loup, golem, monstre, créature d'un autre mod : il se bat, sans jeu d'horreur, jusqu'au bout. Il la garde en mémoire une minute. |
| Un autre mod lui désigne une cible | (commande, mod de combats de créatures : `setTarget`) il la chasse et la tue. |
| Il vient de tuer | Il mange la proie (`mange_carcasse`), et relève la tête vers toi si tu es là (`..._regard_droite/gauche`). Trop près (14 blocs), ou un coup : il la laisse. Une grosse proie (20 PV et plus) : rugissement de victoire. |
| La nuit, au calme | Il s'endort 2 à 4 min (`endormissement`, `dort`). Endormi, il ne voit rien et n'entend qu'à moitié : on peut passer, accroupi ou au pas. Un sprint le réveille (`reveil`). |
| Le jour, après 2 min de calme | Il se couche un moment (`se_couche_ror`, `assis_ror`), puis se relève. |
| À chaque point d'errance | Il s'arrête quelques secondes : boit au bord de l'eau, pêche dans l'eau, lève le nez, rugit (rarement), appelle un congénère s'il y en a un. |

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
| Terrain | 48 points lus toutes les 2 s, **en descendant depuis 10 blocs au-dessus de lui, feuilles et troncs ignorés** : eau et profondeur, dénivelé, et danger selon le classement de pathfinding de Minecraft (lave, feu, cactus, neige poudreuse). Les cartes de hauteur tombaient sur la canopée de la jungle (et sur le plafond de barrières des essais en jeu) : aucun point n'était praticable. |
| Errance | Il patrouille les berges de son territoire, sauvegardé dans la partie. Il évite falaises et lave, et ne repasse pas par ses derniers points. |
| Repli | Il choisit l'eau profonde qui l'éloigne des joueurs, jamais une eau qu'il faudrait atteindre en leur passant au travers. |
| Déblocage | Mesuré en distance gagnée vers le but, pas en distance parcourue. Dans l'ordre : sauter (et arracher les feuilles), reculer, contourner par un côté puis par l'autre la fois suivante, abandonner. S'il abandonne, le cerveau raye la destination pour une minute, ou déclare la cible inatteignable. |

## Installer

**Le jar** : il est construit automatiquement par GitHub à chaque modification et déposé dans
`dist/` à la racine du dépôt (`dist/spinosaure-0.4.0.jar`).

**Le construire soi-même** (JDK 17 requis, rien d'autre : Gradle se télécharge seul) :

```
cd spinosaure-mod
gradlew.bat build        (Windows)
./gradlew build          (Mac / Linux)
```
Le jar sort dans `build/libs/`.

**Tester en survie** (`/gamemode survival`) : comme les mobs vanilla, il n'attaque pas un joueur
en créatif. En créatif il l'observe seulement : il le fixe, le suit à distance à pas feutrés
et se fige quand on le regarde.

**Jouer** : Minecraft 1.20.1 + Forge 47.x, et **GeckoLib 4.4.x pour Forge 1.20.1** dans le
dossier `mods` à côté du jar (le mod en dépend, il n'est pas inclus dedans).
Œuf d'apparition dans l'onglet créatif « Œufs d'apparition », ou `/summon spinosaure:spinosaure`.
Apparition naturelle rare dans **tous les biomes de jungle**, de jour comme de nuit, sauf en paisible.

**Nombre limité par zone** : `config/spinosaure-common.toml`, créé au premier lancement :

| Réglage | Défaut | Effet |
|---|---|---|
| `naturelle` | `true` | `false` : il n'apparaît plus tout seul (pour un événement où on le place avec `/summon`) |
| `max_par_zone` | `1` | pas de nouvelle apparition s'il y en a déjà autant dans la zone |
| `rayon_zone` | `160` | rayon de la zone, en blocs |

L'œuf et `/summon` ne sont jamais limités.

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

- **Le cerveau et le pilote** (`cerveau/`, sans aucune dépendance à Minecraft) : 67 tests
  JUnit, tous verts (`./gradlew test`). `AnimationsTest` vérifie que chacune des 87 animations
  est jouée (80) ou écartée avec sa raison (7, dans `Animations.ECARTEES`), et que tout nom
  demandé est bien enregistré : `tete_inclinee_fixe` était demandée mais jamais enregistrée,
  GeckoLib l'ignorait sans rien dire.
- **Essais en jeu** (GameTest, serveur sans écran) : seul, sous une canopée, dos tourné,
  regard soutenu, dans l'eau, groupe, créature qui l'attaque, cible désignée. Ils sont
  désormais bloquants en CI (ils étaient en « continue-on-error » et deux échouaient). Les tests du pilote simulent le modèle cinématique de
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

- Animations écartées : l'enfouissement (le modèle descend de 10 blocs sous ses pieds, il
  faudrait creuser le terrain), la capture et le transport sous l'eau (le joueur tenu
  flotterait hors de la gueule), la dérive à la verticale, la pose de référence.
- Le pathfinding vanilla gère mal les mobs larges. La boîte de collision fait 3,4 × 5 blocs
  (la largeur du corps) alors que le modèle mesure 13,4 blocs de long : la queue et le museau
  traversent les murs. Il peut aussi peiner en forêt dense (il arrache les feuilles qui le
  bloquent si `mobGriefing` est actif).
- Saisie : empêcher un joueur de descendre se fait côté serveur. Sur une connexion lente, le
  client peut afficher un bref décalage.
- La texture fait 4096², soit environ 64 Mo de mémoire vidéo. À réduire en 2048 si besoin :
  l'audit de l'atlas indique qu'il n'y aurait probablement aucune perte.
