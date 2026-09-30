# Site B, l'île du spinosaure (v3) : monde Minecraft Forge 1.20.1

Île de **640 × 640 blocs**, générée par `generer_ile.py`. Elle est pensée pour un événement :
une **base militaire** au centre-est, cœur de l'opération, reliée par des routes aux lieux qui la
servent (ponton, piste, relais radio, checkpoint, village), et des lieux isolés dans la jungle
reliés par des sentiers. Un sous-sol complet jusqu'à la bedrock.

## Fichiers (dans `dist/`)

| Fichier | Contenu |
|---|---|
| **`site_b_monde.zip`** | **le monde prêt à jouer** (dossier de sauvegarde « Site B », 7 Mo) : l'île de y = −64 à 174, et l'océan tout autour |
| `site_b_v2.schem`, `site_b_v2_0_0.schem` … `site_b_v2_1_1.schem` | l'ancienne voie WorldEdit : l'île de y = 15 à 174, sans le sous-sol profond |

## Installer le monde (solo, CurseForge)

Mods requis (Forge 1.20.1, **chaque joueur les installe**) :

| Mod | Version testée | Pourquoi |
|---|---|---|
| Biomes O' Plenty | 19.0.0.96 | la flore de l'île (palmiers, acajous, saules, mousse espagnole…) |
| TerraBlender | 3.0.1.10 | requis par Biomes O' Plenty |
| GlitchCore | 0.0.1.1 | requis par Biomes O' Plenty |
| GeckoLib | 4.8.4 | requis par le mod spinosaure |
| spinosaure | 0.4.0 (`dist/spinosaure-0.4.0.jar`) | la créature |
| Ziplines: Rezipped! | 1.3.0 (forge 1.20.1) | les tyroliennes : on glisse le long des chaînes, pioche en main |
| Reconnectible Chains | 2.2.5 (forge 1.20.1) | les chaînes tendues entre les pylônes (les câbles des tyroliennes) |
| Cloth Config API | 11.1.136 | requis par Reconnectible Chains |
| ParCool! | 1.20.1-4.0.0.5 | parkour : roulade, escalade, saut de mur, course sur les murs, franchissement |

**Forge 1.20.1-47.4.23 minimum** (exigé par ParCool). Dans CurseForge : *Profile Options* → *Modloader* → choisir 47.4.23 ou plus.

Plus simple pour les joueurs : une fois ton profil prêt, **CurseForge → ⋯ → Export Profile** produit un zip
que chacun importe (*Create Custom Profile → Import*) : mêmes mods, mêmes versions, sans erreur.

**Sans Reconnectible Chains, les câbles des tyroliennes disparaissent** (les pylônes restent). **Sans Biomes O' Plenty, les blocs de la flore disparaissent** : palmiers sans palmes, acajous
sans feuilles, plages du volcan sans sable.

1. Installer les mods dans l'instance (onglet *Mods* de CurseForge, ou copier les jars dans `mods/`).
2. Dézipper `site_b_monde.zip` dans le dossier `saves/` de l'instance : on obtient `saves/Site B/`.
3. Lancer le jeu. *Solo* : le monde « Site B » apparaît dans la liste.

On apparaît au ponton d'arrivée, **en survie**, commandes activées. Attention : en créatif, le spinosaure observe le joueur sans jamais l'attaquer, et les coups portés en créatif ne comptent pas. C'est voulu (mode organisateur).

Sur un serveur : copier le dossier `Site B` à la racine du serveur et mettre `level-name=Site B`
dans `server.properties`.

**Coordonnées.** Dans le monde, l'île est centrée sur l'origine (x et z de −320 à 319). Les
coordonnées données plus bas sont **celles du jeu** (touche F3). La mer est à y = 63, comme en vanilla.

Autour de l'île, le monde est un superflat océanique au même niveau (fond de sable, 31 blocs
d'eau) : la mer continue jusqu'à l'horizon.

## Ou coller le schematic (ancienne méthode)

WorldEdit 7.2.15 : copier les `.schem` dans `config/worldedit/schematics/`, puis sur un monde
océan ou vide, `/tp @s X 15 Z`, `//schem load site_b_v2`, `//paste -a -b` (coin nord-ouest en
(X, 15, Z) ; tuile `site_b_v2_i_j` en (X + 320·i, 15, Z + 320·j)). Le sous-sol profond n'est que
dans le monde.

Réglages conseillés pour l'événement :
- `/gamerule mobGriefing true` : il arrache les feuilles qui le bloquent ;
- `/gamerule doDaylightCycle` à votre goût, la nuit étant bien plus tendue ;
- `/setworldspawn` au ponton d'arrivée.

L'intérieur des bâtiments reste très sombre, mais des blocs de lumière invisibles (niveau 3) y empêchent l'apparition des monstres vanilla. Les grottes, elles, ne sont pas éclairées : des monstres vanilla peuvent y apparaître la nuit comme le jour.

Aperçus dans `apercus/` :
- à jour (v3) : `carte.png` (la carte avec les lieux), `base_militaire.jpg`, `base_interieurs.jpg` (QG, baraquement et cantine sans toit), `souterrain_plan.jpg` (plan des souterrains : la boucle, l'axe central, les salles, les puits aux coins), `souterrain_entrees.jpg` (l'effondrement et la rampe du hangar), `lagon_coupe.jpg` (coupe du lagon sans l'eau : parois, fond à y = −20, rochers, algues, épave), `lagon_epave.jpg` (l'épave sur le fond, entre les rochers) ;
- des versions précédentes, encore représentatifs du style mais plus de l'emplacement : `ile_iso.jpg`, `temple.jpg`, `cenote.jpg`, `village.jpg`, `helicoptere.jpg`, `epave.jpg`, `fond_marin.jpg`, `cratere.jpg`, `jungle.jpg`, `mine.jpg`, `gue.jpg`, `coupe_profond.jpg`, `ravin.jpg`, `tyrolienne.jpg`, `lagon.jpg`, `mine_profonde.jpg`, `grottes.png`.

## La logique de l'île

Une base militaire (« Kilo ») a été installée pour une opération sur l'île, et tout le reste en découle :
- **par la mer**, le ravitaillement arrive au **ponton** au sud ; une route monte à la base en passant par le **checkpoint** ;
- **par les airs**, la **piste d'atterrissage** à l'est, où un avion cargo s'est écrasé en bout de piste ;
- **les liaisons** : le **relais radio** sur la colline au nord-est de la base, et le **village de pêcheurs** sur la côte est ;
- **en avant-poste**, le **bunker** à l'ouest de la base et le **poste de recherche** sur la rive du lac, face à l'îlot aux carcasses ;
- **loin de tout**, les lieux isolés où l'on n'arrive que par des sentiers : campement, hélicoptère abattu, temple, cénote, phare, tour de guet, mine, bungalows, delta.

Les **routes** (4 à 5 blocs de large, en terre battue, boue tassée et terre grossière) partent des portes de la base : vers le ponton par le checkpoint, la piste, le relais, le bunker, le poste de recherche, la crête ouest et le campement, puis le volcan. Des **sentiers** étroits (2 à 3 blocs) desservent le reste : phare, hélicoptère, temple, tour de guet, mine, bungalows, delta, tour du lac, rives du lagon, village et cimetière.

## Les lieux

Coordonnées du jeu (x, z).

| Lieu | x, z | Ce qu'on y trouve |
|---|---|---|
| **Ponton d'arrivée** (départ) | 124, 202 | Ponton, bateau de pêche couché sur le flanc, abri avec le coffre de départ. La route monte à la base par le checkpoint. |
| **Base militaire** | 72 à 176, −20 à 64 | Voir plus bas |
| Checkpoint | 128, 131 | Barrière cassée, guérite, sacs de sable, projecteur |
| Piste d'atterrissage | 226, 90 | Piste, hangar, manche à air |
| Avion cargo | 202, 106 | Écrasé en bout de piste, caisses éparpillées |
| Relais radio | 186, −30 | Local technique, mât haubané, sur la colline au-dessus de la base |
| Village de pêcheurs | 233, 12 | Maisons sur pilotis, ponton, séchoirs, barques ; cimetière à côté (215, 17) |
| Bunker | 46, 40 | Abri à demi enterré : couchettes, armurerie, vivres |
| Poste de recherche (lac) | 20, 38 | Cabane de terrain sur la rive est du lac |
| Lac central et îlot aux carcasses | −35, 41 | Îlot couvert d'os, accessible seulement à la nage. C'est là que tout le monde le cherchera : ce n'est que l'endroit où il mange. |
| Affût | −97, 41 | Poste de chasse sur pilotis au bord du lac |
| **Lagon du mosasaure** | 20, 132 | Voir plus bas |
| Campement abandonné | 15, −118 | Tentes, feu, traces de sang |
| Volcan : cascade et pont suspendu | 113, −132 | Chute depuis le lac de cratère, gorge, pont cassé |
| Grotte de la cascade | 148, −158 | Galerie sous le volcan |
| Observatoire du volcan | 179, −156 | Sur la lèvre du cratère : sismographe, parabole |
| Hélicoptère abattu | −102, −157 | Transport militaire couché sur le flanc, fumée qui monte encore du moteur, sillon d'arbres arrachés |
| **Temple maya en ruine** | −135, −118 | Pyramide à terrasses, escalier gardé par deux têtes de serpent, sanctuaire au sommet, chambre du trésor |
| **Cénote** | −176, −114 | Puits naturel noyé à côté du temple |
| Phare | −32, −238 | Tour à colimaçon, galerie, maison du gardien |
| Tour de guet | −203, −23 | Sur la crête ouest |
| Mine abandonnée | −112, 55 | Galerie boisée, rails, minerai, salle du fond |
| Bungalows | −118, 145 | Trois cabanes sur pilotis au bord du récif |
| Épave | −113, 199 | Caboteur rouillé échoué sur le récif |
| Station du delta | −40, 215 | Passerelle dans la mangrove, labo de terrain |

Des jeeps abandonnées jalonnent les routes et les pistes. Il n'y a **aucun panneau** : la carte se découvre en explorant.

**Retirés en v3** : le campus-musée (centre d'accueil, squelette, labos), l'enclos au bassin, l'enclos des herbivores, les serres et la volière.

### La base militaire « Kilo »

104 × 84 blocs sur une dalle de gravier et de béton :
- **enceinte** grillagée, quatre **portes** gardées par des guérites, quatre **miradors** (longue-vue et arbalète en haut), **projecteurs** ;
- **QG** sur deux niveaux : salle des opérations (table de cartes), radio, armurerie (arbalètes, flèches, plastrons, TNT) ; à l'étage, bureau du commandant et dortoir des officiers ;
- deux **baraquements**, une **cantine** (vivres), un **hangar** (atelier, rails, wagonnet), un **héliport** ;
- **parc de véhicules** (jeeps), dépôt de **carburant**, **château d'eau**, **mât radio**, **conteneurs** de matériel.

Il est passé par là : un pan du grillage arraché au nord-est, des conteneurs renversés, du sang jusqu'au hangar, la base vide.

Intérieurs :
- **QG** : au rez, la table des opérations, un poste radio (baies, bureau à trois écrans) et une carte d'état-major sur le mur ouest ; à l'étage, des casiers, une table de réunion sur un tapis, une bibliothèque, le bureau du commandant et le dortoir des officiers ;
- **baraquements** : des cantines au pied des lits et une table de jeu au milieu ;
- **cantine** : comptoir de service avec plateaux, évier, fourneaux, réserve de tonneaux ;
- **hangar** : étagères, pneus, fûts, palan suspendu, établi, taches d'huile ;
- partout, des veilleuses invisibles (lumière 3) : aucun monstre vanilla n'apparaît dedans.

### Les souterrains de la base (poursuites)

Sous la base, un réseau de **longs couloirs à la taille du spinosaure** (5 de large, 6 de haut ; sa boîte fait 3,4 × 5), pensé pour une scène de poursuite :

| Couloir | Longueur | Sous |
|---|---|---|
| **A** (nord) | 81 blocs en ligne droite | l'allée nord de la base |
| **C** (sud) | 81 blocs en ligne droite | l'héliport et le parc de véhicules |
| **W** et **E** | 43 blocs | ferment la boucle |
| **B** (centre) | 42 blocs | coupe la boucle en deux |

Environ 300 blocs de couloirs en **boucle** : on peut courir sans fin, et se faire couper la route par le couloir central. Sol d'andésite avec une ligne jaune, plinthes sombres, câbles le long du plafond, grilles d'aération, éclairage de secours rouge, bandes jaunes et noires aux croisements. Quelques plafonniers marchent encore (15 %).

**Ses entrées** (à sa taille) :
- la **rampe du hangar**, 5 de large, qui descend vers un tunnel rejoignant le couloir E ;
- l'**effondrement** : le toit du couloir A s'est écroulé au bout de la traînée de sang, un talus d'éboulis descend de la surface. C'est par là qu'il est entré.

**Les entrées des joueurs** : l'escalier du QG (2 de large) et **quatre puits à échelle** aux coins de la boucle, qui débouchent dans de petits abris en béton en surface.

**Les salles** : leur porte fait 1 ou 2 blocs, il n'y entre pas. Ce sont des **refuges** :
- **poste de commandement** sous le QG : table des opérations, consoles, baies de serveurs, carte murale ;
- **armurerie** : arbalètes, flèches (dont spectrales), armures, bouclier, TNT, fusées ;
- **dortoir de secours** : lits superposés, vivres, barricade arrachée, du sang ;
- **infirmerie** : lits, paillasse, alambic, pommes dorées, du sang ;
- **archives** : rayonnages, lutrin, table de cartographie ;
- **réserve** : tonneaux, vivres, une pioche en fer.

Exception : la **salle des générateurs** (groupes électrogènes, cuves en cuivre), ouverte en grand. Il y entre, et on peut s'y cacher entre les machines. La traînée de sang y mène, depuis l'effondrement.

Coordonnées du jeu : rampe du hangar (142 à 149, 12 à 16) ; effondrement (143 à 151, −5 à 3) ; escalier du QG (134, −10) ; puits (82, 6), (166, 6), (82, 44), (166, 44).

Le réseau est au-dessus de la nappe (on y marche à y = 68 dans le jeu, la mer est à 63) et sous la zone protégée de la base : aucune grotte n'y débouche, aucune eau n'y entre.

### Nids et antre

| Nid | x, z |
|---|---|
| **Antre** : salle sèche au bout d'un tunnel noyé, sans autre issue. On n'y entre qu'**en plongeant dans le trou bleu du lagon de récif**, par une galerie ouverte sous la surface. | −181, 110 |
| Perché sur le flanc du volcan, en plein découvert | 136, −104 |
| Grotte sous le flanc nord du volcan | 196, −183 |

### Sous-sol : grottes, galeries, mines et minerais

**Sous les collines (y ≈ 57 à 160)**
- **Grottes à salles**, plus grandes qu'avant : 44 salles et des galeries principales de 8 à 11 blocs de large où **le spinosaure passe**, plus des boyaux de 3 blocs pour les joueurs. Peu de concrétions : quelques stalactites et stalagmites par salle, pas de forêt de pointes.
- **Cavernes vanilla** (galeries sinueuses et grandes cavernes) sous les collines.
- **Deux mines abandonnées** : sous la crête ouest (−197, 28), 27 couloirs, avec **un puits à échelles** jusqu'à la mine profonde ; sous le volcan (140, −208), 62 couloirs.
- **Entrées** (9) : (116, −176), (239, −180), (−205, 35), (−226, −67), (206, −101), (160, −247), (−182, −155), (−181, 118), (53, −120).

**Le sous-sol profond (y = −64 à 14), sous toute l'île**
- **Cavernes** plus larges et plus régulières : grandes salles et galeries (5 millions de blocs), sans les boyaux « nouilles ».
- **3 longs tunnels** de 220 à 340 blocs, 6 à 9 blocs de diamètre, qui traversent l'île entre y = −48 et −4.
- **Grande mine profonde** à y = −30, sous la crête : 172 couloirs, 36 coffres, rails, toiles, 4 générateurs d'araignées venimeuses.
- **Lave** réduite aux lacs du fond (y = −59 et −58) par poches, bordés de tuf : 25 000 blocs (contre 473 000 avant).
- **Gouttes** (dripstone) rares : 1 700 blocs (contre 72 000). Une région de sculk.
- Minerais d'ardoise : diamant, redstone, or, lapis, fer, cuivre, charbon.

**Les liaisons, pour descendre**
- 2 **descentes en colimaçon** depuis des grottes sèches : (70, −147) et (211, −139).
- 2 **ravins** jusqu'au sous-sol profond, avec une passerelle de corde au-dessus : (253, −163) et (−223, 26).
- Le **puits de mine à échelles** (−197, 28).

### Se déplacer : routes, tyroliennes, passerelles, barques, wagonnets

**Huit tyroliennes**, toujours en descente :

| Ligne | Longueur | Départ → arrivée (y) |
|---|---|---|
| **Base militaire → rive sud du lagon** (au-dessus du lagon) | 168 blocs, 7 tronçons | 91 → 79 |
| **Rive nord → rive sud du lagon** (au-dessus du lagon) | 122 blocs, 5 tronçons | 85 → 76 |
| Relais radio → Base militaire | 67 blocs, 3 tronçons | 101 → 81 |
| Tour de guet → Affût (depuis la crête) | 127 blocs, 5 tronçons | 141 → 83 |
| Relais radio → Village de pêcheurs | 44 blocs | 89 → 70 |
| Hélicoptère abattu → Temple maya | 43 blocs | 97 → 81 |
| Temple maya → Cénote | 53 blocs | 119 → 81 |
| Phare → Campement abandonné | 67 blocs | 91 → 84 |

- **S'en servir :** monter à l'échelle de la tour de départ, se placer sous la barrière du portique, **pioche en main, clic droit maintenu** vers la chaîne. Relâcher ou sauter pour lâcher.
- **Construction :** tour de départ, pylônes à potence (le joueur pend 2,3 blocs sous le câble), tronçons de 28 blocs au plus (Reconnectible Chains casse une chaîne au-delà de 32), **plate-forme d'arrivée surélevée de 2 blocs avec un escalier** : on arrive au-dessus du sol, pas dedans. Au-dessus du lagon, les pylônes plongent jusqu'au fond.
- **Dégagement** vérifié sous toute la ligne (relief, bâtiments, feuillages, eau). Refusée faute de dégagement : observatoire → campement (la lèvre du cratère coupe la ligne).

**Passerelles de corde** au-dessus des deux ravins. **Barques** au ponton, au village, aux bungalows et au delta. **Wagonnets** sur les rails des mines. **Parkour (ParCool!)** : rochers, ruines, falaises en gradins, pylônes.

### Le lagon du mosasaure

Un lagon fermé au milieu du sud de l'île, entre le lac et le ponton, relié à l'océan par un chenal vers le delta. Centre **(20, 132)**.
- **En surface :** environ 92 × 84 blocs d'eau turquoise (biome océan chaud), une fine bande de sable blanc (1 à 4 blocs) au bord, jungle tout autour.
- **Profond partout :** passé la bande de sable, le fond tombe d'un coup. Le **fond est à y = −20 au centre** (83 blocs d'eau) et remonte doucement vers les bords (y ≈ −10), sans cuvette ni haut-fond au milieu : tout le lagon laisse la place à une grande bête marine.
- **Rochers énormes** (8) posés sur le fond, et **3 aiguilles** qui montent du fond jusqu'au-dessus de la surface.
- **Algues** : peu, par massifs, seulement dans le tiers extérieur (89 pieds de kelp de 10 à 22 blocs) : l'eau reste claire, on voit le fond et l'épave.
- **L'épave :** un caboteur rouillé de 44 blocs, **posé sur le fond à y = −20**, vers (26, 136). Dans la cale, un coffre : or, cœur de la mer, diamants.
- **Étanche :** toute cavité à moins de 3 blocs de l'eau du lagon est murée (2 366 blocs). Mesuré : 0 bloc d'eau au contact de l'air sous le niveau de la mer, 0 au contact de la lave.
- **Le mosasaure n'est pas fourni** : le lagon est prêt pour une créature marine d'un autre mod.

### Rives, plages et gués

On ne traverse plus les rivières sur des ponts : **les ponts se sont effondrés**. Les pistes passent à **gué**, dans un bloc d'eau sur un haut-fond de gravier, entre les pilotis restants : lentement, à découvert, dans son territoire.

Une rive de rivière ou du lac sur deux environ est une **plage** au ras de l'eau, avec un haut-fond où l'on a pied.


### Objectifs possibles pour l'événement

Il n'y a ni journaux ni panneaux. Le décor raconte l'histoire, et on peut bâtir l'événement dessus :
- rejoindre la base et s'armer au QG ;
- joindre le relais radio ;
- trouver les nids ;
- tenir jusqu'à l'évacuation, par la piste ou par le ponton.

## Le terrain

- Volcan au nord-est : lac de cratère perché, cascade, gorge.
- Crête rocheuse à l'ouest, avec falaises en gradins.
- Rivière principale : de la cascade au lac central, puis en delta à mangrove au sud, avec un affluent et un bras vers l'est.
- Lagon de récif et barrière de corail au sud-ouest, lagon du mosasaure au sud, plages de sable.
- **Plages en pente douce tout autour de l'île** : le fond remonte jusqu'à la ligne d'eau et la terre repart de là. On sort de l'eau à pied partout, lagon compris ; seules les falaises du volcan et de la crête font exception, volontairement.
- **Falaises au bord de l'eau** (cratère, gorges, trous bleus, crevasses, pointes rocheuses) : elles ne tombent plus en mur droit. Un bruit 3D les ronge et les fait déborder : niches, surplombs sous la lèvre, bancs horizontaux, éperons, et un talus d'éboulis au pied qui remonte sous l'eau. Près de 89 000 blocs retravaillés. Le rideau de la cascade n'est pas touché.
- **Barrière de corail en volume** : dômes, tables en champignon, tours et arches de corail, par colonies de couleur, avec des gorgones, des éventails sur les flancs et des concombres de mer. D'autres pâtés isolés parsèment le lagon.
- **Fond marin travaillé** : plage immergée puis tombant, bancs et rides de sable, gravier, argile et vase au large, pitons rocheux, **crevasses** étroites et sinueuses jusqu'à 18 blocs plus bas, forêts de kelp. **Sept trous bleus**, des puits à parois verticales jusqu'à 4 blocs du fond du monde, dont un dans le lagon de récif (l'accès à l'antre). Coordonnées du jeu : (−195, 213), (13, 274), (270, 170), (−96, 247), (293, 58), (135, 276), (22, −291).
- **Toutes les eaux libres sont au niveau de la mer** et forment un seul réseau : c'est son territoire.
- **Jungle à étages**, pas une forêt :
  - fromagers géants à contreforts et couronne en parasol ;
  - arbres de voûte (un sur trois est un **acajou** BOP), figuiers étrangleurs creux, **palmiers** BOP sur les berges, palétuviers dans le delta ;
  - **saules pleureurs** BOP le long des rivières et du lac : des rideaux de lianes jusqu'au sol ;
  - **mousse espagnole** BOP qui pend des feuillages (9 200 blocs) ;
  - beaucoup de **petits arbres** : 690 jeunes arbres, 1 000 buissons et des arbrisseaux de 3 à 5 blocs (jungle, acajou, chêne, azalée), bambous, troncs couchés moussus ;
  - sous-bois dense : herbes, fougères, buissons, pousses et trèfle BOP, hautes herbes BOP et plantes de 2 blocs couvrent environ 80 % du sol, avec de nombreux jeunes arbres et buissons. Sous les arbres, on ne voit plus à 50 blocs. De rares **fleurs luisantes** brillent dans le noir ;
  - fleurs de jungle : hibiscus, cosmos orange, violettes, fleurs sauvages (BOP) ;
  - au bord de l'eau : **massettes** et **roseaux** (BOP), cannes à sucre, nénuphars fleuris et **nénuphars géants** ;
  - sur les plages : oyats et herbes des dunes ; **sable noir** sur les plages du volcan ;
  - **rideaux de lianes** : 82 000 blocs de lianes pendent des feuillages sur 3 à 14 blocs ;
  - **clairières** fleuries (herbes hautes, fougères géantes, orchidées, torchères, pétales roses, melons) : on y voit loin, et on y est vu ;
  - **mares** boueuses (38), avec nénuphars, grandes feuilles et cannes à sucre ;
  - **rochers moussus** (320), certains grands comme une cabane : de quoi se cacher ;
  - 23 **bambouseraies** ;
  - **versants et montagnes couverts** : mousse et herbe sur les pentes, buissons et jeunes arbres accrochés, parois tapissées de lianes par plaques (12 000 blocs). Seules les parois quasi verticales restent en roche nue.

Blocs vanilla 1.20.1 et **Biomes O' Plenty** (à installer, voir plus haut).

**Mesuré à l'échelle du spinosaure** (boîte de 3,4 × 5) :
- 97 % des colonnes de forêt gardent **au moins 6 blocs libres sous les feuillages** ;
- les rivières font **9 blocs de fond** en médiane, et 94 % font au moins 4 blocs ;
- les troncs de la voûte sont espacés d'au moins 8 blocs.

(Ces trois mesures datent de l'île de 768 ; elles n'ont pas été refaites sur la v3.)

## Vérifié, et pas vérifié

- **Souterrains** (v3.1) : 0 bloc d'eau ou de lave dans leur volume ; hauteur libre d'au moins 5 blocs au cœur de chaque couloir (sa boîte fait 5), 9 à 10 au-dessus de la rampe et du talus d'éboulis ; le talus n'est fait que de blocs naturels (sur un bloc « ouvrage », son pas tombe à 0,6 bloc).
- Chaque état de bloc (672 en v3.1) est contrôlé contre les données Minecraft 1.20 de minecraft-data, et ceux de Biomes O' Plenty contre le jar : 0 erreur.
- **Eau** (v3) : sous le niveau de la mer, 0 bloc d'eau au contact de l'air et 0 au contact de la lave, dans le sous-sol profond comme au-dessus, jonction y = 14 / 15 comprise. Seule la cascade (eau source au-dessus du sol, voulue) touche de l'air.
- Les fichiers portent le champ `BiomePaletteMax` exigé par WorldEdit 7.2.15 : sans lui, `//schem load` échouait avec « Unknown error ».
- **Côtes** : sur tout le tour de l'île, la terre au bord de la mer est au niveau de l'eau (0 bloc à escalader pour sortir de l'eau). Mesuré sur la carte des hauteurs.
- **Grottes** : 5 blocs de roche au moins entre le plafond et la surface (7 pour les cavernes), hors entrées. Toute cavité sous le niveau de la nappe est pleine d'eau, à surface plane. 10 cellules d'air couvertes touchent de l'eau sur toute l'île : au pire, quelques blocs d'eau couleront au premier bloc voisin modifié.
- **Clôtures** : aucune barrière, aucun muret ni aucune grille ne flotte à moins de 5 blocs du sol. 308 poteaux ont été prolongés jusqu'au sol après les retouches du terrain.
- **Carcasses** : squelettes en blocs d'os (colonne, cage thoracique, crâne, pattes, queue), sans barres de l'End.
- Les fichiers ont été relus avec nbtlib :
  - dimensions et nombre de blocs exacts ;
  - palette, biomes et coffres.
- Vitres, barreaux, barrières et murets reçoivent leurs connexions à la génération : WorldEdit ne les recalcule pas au collage.
- **Aucun arbre flottant.** Un détecteur suit chaque bloc d'arbre jusqu'au sol, en connexité par faces, arêtes et coins : 0 bloc de tronc ou de feuillage isolé sur 750 000. Les 825 lianes qui ne rejoignent pas un tronc sont accrochées à un mur, une falaise ou un plafond de grotte : chacune a été contrôlée. Seule exception : deux lianes des cavernes dans une grotte.
- Troncs, branches, racines et palmes sont tracés d'un seul tenant, reliés par les faces : pas de marches en diagonale.
- Aucune liane sans appui : chaque liane est accrochée à un bloc plein ou à la liane du dessus, et celles qui pendraient dans le vide sont retirées à la génération. Les propagules pendent sous des feuilles de palétuvier.
- **Chargé dans un vrai Minecraft** (WorldEdit 7.2.15, Forge 1.20.1) après la correction de `BiomePaletteMax`. **Pas encore vérifié en jeu** : l'orientation des portes, lits et escaliers, le rendu de la cascade (eau source, elle se met à couler dès qu'un bloc voisin change), le temple, les maisons et les grottes, et les performances au collage.

## Régénérer ou modifier

`python3 generer_ile.py sortie/` (numpy requis, environ 2 min) produit le monde (`sortie/Site B/`, à zipper dans `dist/site_b_monde.zip`), les 5 `.schem`, `site_b_v2.json` (coordonnées des lieux, des entrées de grottes et des trous bleus), `verif_monde.txt` (blocs témoins pour la CI), `blocs.npy`, `profond.npy` et `grottes.npy`. `python3 verif_monde.py sortie/` relit ensuite les régions. La graine est fixe : on obtient la même île à chaque fois. Pour remettre les panneaux, passer `PANNEAUX` à `True` dans `monde.py`.

| Module | Rôle |
|---|---|
| `relief.py` | forme de l'île, volcan, rivières, lac, lagon |
| `arbres.py` | les essences d'arbres |
| `base_militaire.py` | la base militaire « Kilo » : enceinte, miradors, QG, baraquements, hangar, héliport, dépôts, intérieurs |
| `souterrain_kilo.py` | les souterrains de la base : boucle de couloirs, salles refuges, rampe, effondrement, puits |
| `mobilier.py` | meubles et façades |
| `lieux.py` | les autres lieux (temple maya, cénote, maisons, hélicoptère…) |
| `grottes.py` | grottes, gouffres, lacs souterrains, cavernes, mines, antre et nids |
| `profond.py` | sous-sol profond (y −64 à 14), mine profonde, descentes, ravins, puits de mine |
| `details.py` | falaises et récif en volume |
| `flore.py` | clairières, mares, rochers, rideaux de lianes, mousse espagnole, lianes des falaises |
| `recits.py` | les journaux (plus utilisés : les coffres n'en contiennent plus) |
| `monde.py` | volume de blocs et écriture Sponge v2 |
| `lagon.py` | le lagon du mosasaure : cuvette, plages, chenal, fosse, scellement, épave, rochers, algues |
| `deplacements.py` | tyroliennes (tours, pylônes à potence, portiques, nœuds de chaîne), passerelles des ravins, barques, wagonnets |
| `monde_java.py` | export en monde Minecraft 1.20.1 (régions Anvil, level.dat), blocs témoins |
| `verif_monde.py` | relecture indépendante des régions avec nbtlib, comparée bloc à bloc au modèle |
| `bop_blocs.json` | les blocs de Biomes O' Plenty utilisés et leurs propriétés (inventaire du jar par la CI) |
| `rendu.py` | vues isométriques, plans d'étage et carte, pour vérifier sans lancer le jeu |
