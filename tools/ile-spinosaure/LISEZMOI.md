# Site B, l'île du spinosaure (v2) : monde Minecraft Forge 1.20.1

Île de **768 × 768 blocs**, générée par `generer_ile.py`. Elle est pensée pour un événement :
une vingtaine de lieux, dispersés et reliés par des pistes dans la jungle, et un sous-sol complet
jusqu'à la bedrock.

## Fichiers (dans `dist/`)

| Fichier | Contenu |
|---|---|
| **`site_b_monde.zip`** | **le monde prêt à jouer** (dossier de sauvegarde « Site B », 12 Mo) : l'île de y = −64 à 174, et l'océan tout autour |
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

On apparaît au ponton d'arrivée, en créatif, commandes activées. `/gamemode survival` pour jouer.

Sur un serveur : copier le dossier `Site B` à la racine du serveur et mettre `level-name=Site B`
dans `server.properties`.

**Coordonnées.** Dans le monde, l'île est centrée sur l'origine : un point noté (x, z) plus bas,
relatif au coin nord-ouest de l'île, se trouve en **(x − 384, z − 384)** dans le jeu. La mer est
à y = 63, comme en vanilla.

Autour de l'île, le monde est un superflat océanique au même niveau (fond de sable, 31 blocs
d'eau) : la mer continue jusqu'à l'horizon.

## Ou coller le schematic (ancienne méthode)

WorldEdit 7.2.15 : copier les `.schem` dans `config/worldedit/schematics/`, puis sur un monde
océan ou vide, `/tp @s X 15 Z`, `//schem load site_b_v2`, `//paste -a -b` (coin nord-ouest en
(X, 15, Z) ; tuile `site_b_v2_i_j` en (X + 384·i, 15, Z + 384·j)). Le sous-sol profond n'est que
dans le monde.

Réglages conseillés pour l'événement :
- `/gamerule mobGriefing true` : il arrache les feuilles qui le bloquent ;
- `/gamerule doDaylightCycle` à votre goût, la nuit étant bien plus tendue ;
- `/setworldspawn` au ponton d'arrivée.

L'intérieur des bâtiments reste très sombre, mais des blocs de lumière invisibles (niveau 3) y empêchent l'apparition des monstres vanilla. Les grottes, elles, ne sont pas éclairées : des monstres vanilla peuvent y apparaître la nuit comme le jour.

Aperçus dans `apercus/` : `carte.png`, `grottes.png` (en orange les galeries sèches, en cyan les parties noyées), `ile_iso.jpg`, `temple.jpg`, `cenote.jpg`, `village.jpg`, `helicoptere.jpg`, `epave.jpg`, `fond_marin.jpg` (récif et lagon, sans l'eau), `cratere.jpg` (coupe), `jungle.jpg` (coupe dans la jungle : sous-bois, lianes, minerais dans la roche), `mine.jpg` (la mine vue de dessus), `gue.jpg`, `coupe_profond.jpg` (coupe de la crête jusqu'à la bedrock : puits de mine à échelles, mine profonde, lave), `ravin.jpg` (coupe d'un ravin), `tyrolienne.jpg` (la ligne relais radio → serres, câble dessiné en blanc), `lagon.jpg` (le lagon du mosasaure et les deux tyroliennes qui le survolent), `lagon_coupe.jpg` (coupe : haut-fond, tombant, algues, fosse et épave, eau retirée), `lagon_epave.jpg` (l'épave au fond de la fosse), `mine_profonde.jpg` (plan de la mine profonde à y = −30).

## Les lieux

| Lieu | x, z | Ce qu'on y trouve |
|---|---|---|
| **Ponton d'arrivée** (départ) | 533, 603 | Ponton, bateau de pêche couché sur le flanc et à demi rempli d'eau, abri avec le coffre de départ (carte vierge, boussole, arbalète, barque). La route mène au campus. |
| **Campus Site B** | 455–600, 345–480 | Voir plus bas |
| Checkpoint | 519, 511 | Barrière cassée, guérite, sacs de sable, projecteur |
| Piste d'atterrissage | 546–626, 522 | Piste, hangar, manche à air |
| Avion cargo | 588, 562 | Écrasé en bord de plage, caisses éparpillées |
| Relais radio | 617, 450 | Local technique, mât haubané de 40 blocs |
| Village de pêcheurs | 655, 402 | Six maisons sur pilotis, toutes différentes : charpente apparente, volets, véranda couverte sur le ponton, toit à débord, cheminée, intérieur meublé. L'une a perdu sa porte et porte des griffures, une autre a le toit crevé. Ponton, séchoirs, barques. |
| Serres | 406, 476 | Trois serres voûtées, carreaux brisés, plantes |
| Lac central et îlot aux carcasses | 342, 434 | Îlot couvert d'os, accessible seulement à la nage. C'est là que tout le monde le cherchera : ce n'est que l'endroit où il mange. |
| Affût | 268, 434 | Poste de chasse sur pilotis au bord du lac |
| Enclos des herbivores | 358, 321 | Clôture électrique arrachée, carcasses, tour d'observation |
| Campement abandonné | 408, 238 | Tentes, feu, traces de sang |
| Cimetière | 434, 257 | Tombes avec noms |
| Volière | 440, 159 | Dôme géodésique éventré, passerelle effondrée, nids |
| Phare | 345, 131 | Tour de 36 blocs à colimaçon, galerie, maison du gardien |
| Volcan : cascade et pont suspendu | 511, 227 | Chute de 80 blocs depuis le lac de cratère, gorge, pont cassé |
| Grotte de la cascade | 544, 196 | Galerie sous le volcan : l'antre, os rangés |
| Observatoire du volcan | 600, 170 | Sur la lèvre du cratère : sismographe, parabole |
| Hélicoptère abattu | 262, 196 | Transport militaire couché sur le flanc : cockpit vitré, poutre de queue et dérive, pales brisées (une plantée dans le sol), porte cargo ouverte vers le ciel, soute en désordre, fumée qui monte encore du moteur, sillon d'arbres arrachés |
| **Temple maya en ruine** | 227, 269 | Pyramide de 8 terrasses (talud-tablero, angles rentrants), escalier central raide gardé par deux têtes de serpent, sanctuaire au sommet avec voûte en encorbellement et crête ajourée, 50 blocs de haut. Place à stèles. Galerie basse vers la chambre du trésor. |
| **Cénote** | 186, 273 | Puits naturel noyé à côté du temple : 12 blocs de chute jusqu'à l'eau, lianes le long des parois, un nid sur la corniche |
| Tour de guet | 140, 357 | Sur la crête ouest, 26 blocs |
| Mine abandonnée | 202, 450 | Galerie boisée de 50 blocs, rails, minerai, salle du fond |
| Bunker | 265, 523 | Abri à demi enterré : couchettes, armurerie, vivres |
| Bungalows | 239, 568 | Trois cabanes sur pilotis au bord du lagon, toit de bambou, escalier jusqu'au sol |
| Épave | 83, 608 | Caboteur rouillé de 30 blocs échoué sur le récif : étrave montée sur le corail, gîte de 25°, flanc tribord éventré, cales noyées, poupe brisée et affaissée, timonerie, cheminée, mât plié, coraux sur la coque |
| Station du delta | 336, 642 | Passerelle dans la mangrove, labo de terrain |

Des jeeps abandonnées jalonnent les pistes. Il n'y a **aucun panneau** : la carte se découvre en explorant.

### Nids et antre

Sept nids : une cuvette de vase, une couronne de racines tressées, des œufs (œufs de renifleur) et des restes de repas. Ils sont volontairement **là où on ne les attend pas** : pas au bord des rivières.

| Nid | x, z |
|---|---|
| **Antre** : salle sèche au bout d'un tunnel noyé, sans autre issue. On n'y entre qu'**en plongeant dans le trou bleu du lagon** (150, 640), par une galerie ouverte à 12 blocs sous la surface. | 197, 485 |
| Sous le dôme éventré de la volière, parmi les nids d'oiseaux | 444, 154 |
| Perché sur le flanc du volcan, en plein découvert | 553, 248 |
| Grotte sous la crête ouest | 180, 365 |
| Grotte sous le flanc nord du volcan | 530, 101 |
| Corniche du cénote, en bas du puits | 186, 273 |

L'antre est entouré d'une gaine de roche : aucune autre galerie n'y débouche. Contrôlé par un remplissage 3D depuis le nid : la seule issue est le trou bleu.

### Sous-sol : grottes, galeries, mines et minerais

Sous l'île, un sous-sol **comme dans un monde classique**, jusqu'à la bedrock. Coordonnées (x, z)
relatives au coin de l'île, y du monde.

**Sous les collines (y ≈ 57 à 160)**
- **Cavernes vanilla :** galeries sinueuses entrelacées (« spaghetti ») et grandes cavernes (« fromage »), plus larges qu'avant, sous toutes les collines. Les parties au niveau de la nappe (y ≈ 57 à 61) sont noyées : lacs souterrains.
- **Grottes à salles :** 72 salles avec des galeries principales où **le spinosaure passe**, et des boyaux de 3 blocs pour les joueurs : parois irrégulières, colonnes de stalactites, éboulis, salles envahies de végétation (avec de la mousse luisante), racines, lianes des cavernes, ossements, amanites et champignons luisants.
- **Deux mines abandonnées de type vanilla**, sur quatre générations de couloirs :
  - sous la crête ouest (147, 417) : 47 couloirs de 3 × 3 étayés, rails, toiles, coffres. **Un puits de 3 × 3 à échelles** (paliers tous les 16 blocs) descend de là jusqu'à la mine profonde, 100 blocs plus bas ;
  - sous le plateau de l'est (632, 216) : 69 couloirs.
- **Entrées :** porches rocheux en surplomb et deux gouffres ouverts dans la jungle. Les 11 entrées (x, z) : (169, 472), (98, 354), (644, 144), (543, 106), (144, 255), (559, 257), (645, 228), (503, 182), (180, 391), (422, 505), (426, 209). Elles sont aussi dans `site_b_v2.json`.

**Le sous-sol profond (y = −64 à 14), sous toute l'île**
- Ardoise des abîmes sous y = 0, transition mêlée jusqu'à 8, pierre au-dessus ; poches de tuf, granite, diorite et andésite ; bedrock irrégulière au fond.
- **Cavernes** au bruit 3D : grandes salles à piliers, longues galeries, boyaux étroits. Environ 15 % du volume, soit 7 millions de blocs.
- **Lacs de lave** sous y = −55, comme en vanilla : ils éclairent le fond.
- **Minerais d'ardoise :** diamant (≈ 15 700 blocs, surtout vers y = −58), redstone, or, lapis, fer, cuivre, charbon.
- Deux **géodes d'améthyste**, des régions de **gouttes** (stalactites et stalagmites de dripstone, biome *dripstone caves*), et une **région de sculk** (biome *deep dark*).
- **La mine profonde** à y = −30, sous la crête : salle de terre centrale, 60 couloirs, rails, toiles et toiles pendantes, **œufs d'araignée** (BOP), **4 générateurs d'araignées venimeuses** enrobés de toiles, et des coffres un peu mieux garnis (diamants, pomme dorée, étiquette).

**Les liaisons, pour descendre**
- **5 descentes en colimaçon**, praticables à pied, depuis des grottes sèches de l'île jusqu'aux cavernes profondes : départs en (470, 203), (569, 131), (419, 433), (173, 350) et (197, 483).
- **2 ravins** ouverts dans la jungle, jusqu'à y ≈ −28 : un à-pic de plus de 100 blocs, centrés en (646, 235) et (138, 429). On y tombe, on n'y descend pas.
- Le **puits de mine à échelles** (147, 417).
- Aucune de ces liaisons ne touche l'eau : chaque tracé est refusé s'il passe à moins de 2 blocs d'une grotte noyée.

### Se déplacer : tyroliennes, passerelles, barques, wagonnets

**Huit tyroliennes**, toujours en descente (on prend de l'élan en descendant, on en perd en montant) :

| Ligne | Longueur | Départ → arrivée (y) |
|---|---|---|
| **Rive nord → rive sud du lagon** (au-dessus du lagon du mosasaure) | 127 blocs, 5 tronçons | 102 → 69 |
| **Serres → rive sud du lagon** (au-dessus du lagon) | 137 blocs, 6 tronçons | 102 → 70 |
| Relais radio → Serres (au-dessus du campus) | 185 blocs, 7 tronçons | 113 → 76 |
| Tour de guet → Affût (depuis la crête) | 152 blocs, 6 tronçons | 142 → 76 |
| Phare → Volière | 99 blocs, 4 tronçons | 108 → 88 |
| Hélicoptère abattu → Temple maya | 43 blocs | 100 → 75 |
| Temple maya → Cénote | 42 blocs | 92 → 75 |
| Relais radio → Village de pêcheurs | 33 blocs | 88 → 69 |

Au-dessus du lagon, les pylônes plongent jusqu'au fond (et jusqu'au fond de la fosse quand ils tombent dessus).

- **S'en servir :** monter à l'échelle de la tour de départ, se placer sous la barrière du portique, **pioche en main, clic droit maintenu** vers la chaîne. On regarde dans le sens de la marche. Relâcher le clic ou sauter pour lâcher ; accroupi pour se laisser tomber sans sauter.
- **Construction :** tour de départ, pylônes à potence (poteau décalé de 2 blocs et bras au-dessus de la ligne, pour que le joueur, qui pend 2,3 blocs sous le câble, ne heurte rien) et portique d'arrivée avec plancher. Les tronçons font au plus 28 blocs : Reconnectible Chains casse une chaîne au-delà de 32 blocs, réglage par défaut. Le joueur passe d'un tronçon au suivant sans lâcher.
- **Dégagement :** le relief, les bâtiments et les feuillages sont vérifiés sous toute la ligne, flèche de la chaîne comprise. On ne plante aucun arbre dans le couloir des câbles, et les feuillages qui y débordent sont retirés.
- Tyroliennes refusées faute de pente ou à cause d'un relief qui les barrait : observatoire du volcan → campement ou → cimetière (la lèvre du cratère coupe la ligne).

**Passerelles de corde** au-dessus des deux ravins : planches, garde-corps de chaînes, et elles s'affaissent au milieu.

**Barques** amarrées au ponton, au village de pêcheurs, aux bungalows et à la station du delta. **Wagonnets** sur les rails des mines, dont quelques-uns avec un coffre, jusque dans la mine profonde.

**Parkour (ParCool!)** : les rochers, les ruines du temple, les falaises en gradins et les pylônes deviennent des parcours.

### Le lagon du mosasaure

Un grand lagon tropical au sud de l'île, entre le delta et le ponton d'arrivée : on le voit en arrivant. Centre (428, 580), soit **(44, 196) dans le jeu**.
- **En surface :** 120 × 108 blocs d'eau turquoise (biome océan chaud), plages de sable blanc (BOP), palmiers et jungle tout autour. Un chenal de 12 blocs de large et 10 de fond le relie à l'océan, au sud.
- **Le piège :** une ceinture de haut-fond de sable blanc où l'on a pied (1 à 4 blocs), puis le **tombant**, une paroi de roche nue.
- **La cuvette :** **40 blocs de fond** (y = 23 à 63), assez de place pour une grande bête marine. On y trouve :
  - des **forêts de grandes algues** de 35 à 40 blocs de haut ;
  - **11 rochers énormes** (jusqu'à 22 blocs de large) ;
  - **3 aiguilles rocheuses** qui percent la surface, dont une percée d'une arche au ras de l'eau.
- **La fosse :** au milieu, un entonnoir irrégulier de 44 × 32 blocs qui descend dans l'ardoise des abîmes jusqu'à **y = −30** : **93 blocs d'eau** en tout. Des algues géantes montent du fond jusque sous la surface (plus de 80 blocs).
- **L'épave :** un caboteur rouillé de 44 blocs, couché sur le flanc et cassé en deux, **au fond de la fosse** (vers (52, 202) dans le jeu). Dans la cale, un coffre : or, cœur de la mer, diamants. Autour, des os.
- **Étanche :** toute cavité du sous-sol à moins de 3 blocs de l'eau du lagon a été murée (4 100 blocs), avant et après la pose de l'épave. Mesuré : 0 bloc d'eau au contact de l'air dans toute la zone du lagon.
- **Le mosasaure n'est pas fourni.** Le lagon est prêt pour une créature marine d'un autre mod : c'est de l'océan chaud, profond, relié à la mer.

### Rives, plages et gués

On ne traverse plus les rivières sur des ponts : **les ponts se sont effondrés**. Les pistes passent à **gué**, dans un bloc d'eau sur un haut-fond de gravier, entre les pilotis restants : lentement, à découvert, dans son territoire.

Une rive de rivière ou du lac sur deux environ est une **plage** au ras de l'eau, avec un haut-fond où l'on a pied.

Trois lieux ne se rejoignent **que par la plage** :
- le village de pêcheurs, depuis le ponton ;
- la station du delta, depuis les bungalows ;
- la volière, depuis le phare.

### Le campus

- **Centre d'accueil** :
  - atrium sous une charpente à deux pans, avec une verrière de faîtage et un pan effondré sous un arbre tombé ;
  - squelette de spinosaure et grand escalier ;
  - mezzanine d'exposition, café et boutique ;
  - façade vitrée éventrée : il peut entrer dans l'atrium.
- **Galerie d'observation sous-marine**, sous le parvis : une vitre sur le bassin de l'enclos.
- **Aile des laboratoires**, sur deux niveaux :
  - génétique, couveuse (un nid éclos), chambre froide, salle des cuves (une brisée), sécurité ;
  - salle de contrôle face à l'enclos, bureaux et bureau du directeur, serveurs, réunion, infirmerie ;
  - sur le toit : héliport, climatisation, panneaux solaires, antennes.
- **Sous-sol noyé** : passerelles, groupe de secours à cinq leviers, **tunnel de drainage** ouvert sur le bassin. C'est sa route pour entrer dans le bâtiment.
- **Loge du personnel** : cantine, cuisine, laverie, salle de détente, douze chambres, dont une barricadée, et toit en cuivre.
- **Belvédère** : tour ronde à colimaçon.
- **Centrale électrique** : cheminée et cuves.
- **Enclos S-01** : bassin, île intérieure, brèche vers la rivière, grue et cage.
- **Extérieur** : parvis avec fontaine, parking, portail, clôture de périmètre trouée.

Les couloirs font 2 blocs de large : il n'y entre pas. Mais il voit à travers les vitres.

### Objectifs possibles pour l'événement

Il n'y a plus ni journaux ni panneaux. Le décor raconte l'histoire, et on peut bâtir l'événement dessus :
- relancer le groupe de secours au sous-sol des labos (cinq leviers) ;
- joindre le relais radio ;
- trouver les nids ;
- tenir jusqu'à l'évacuation au ponton sud.

## Le terrain

- Volcan au nord-est : lac de cratère perché, cascade, gorge.
- Crête rocheuse à l'ouest, avec falaises en gradins.
- Rivière principale : de la cascade au lac central, puis en delta à mangrove au sud, avec un affluent et un bras vers l'est.
- Lagon et récif de corail au sud-ouest, plages de sable.
- **Plages en pente douce tout autour de l'île** : le fond remonte jusqu'à la ligne d'eau et la terre repart de là. On sort de l'eau à pied partout, lagon compris ; seules les falaises du volcan et de la crête font exception, volontairement.
- **Falaises au bord de l'eau** (cratère, gorges, trous bleus, crevasses, pointes rocheuses) : elles ne tombent plus en mur droit. Un bruit 3D les ronge et les fait déborder : niches, surplombs sous la lèvre, bancs horizontaux, éperons, et un talus d'éboulis au pied qui remonte sous l'eau. Près de 89 000 blocs retravaillés. Le rideau de la cascade n'est pas touché.
- **Barrière de corail en volume** : dômes, tables en champignon, tours et arches de corail, par colonies de couleur, avec des gorgones, des éventails sur les flancs et des concombres de mer. D'autres pâtés isolés parsèment le lagon.
- **Fond marin travaillé** : plage immergée puis tombant, bancs et rides de sable, gravier, argile et vase au large, pitons rocheux, **crevasses** étroites et sinueuses jusqu'à 18 blocs plus bas, forêts de kelp. **Sept trous bleus**, des puits à parois verticales jusqu'à 4 blocs du fond du monde, dont un dans le lagon : x, z = (150, 640), (712, 405), (708, 588), (79, 162), (32, 486), (287, 66), (495, 725).
- **Toutes les eaux libres sont au niveau de la mer** et forment un seul réseau : c'est son territoire.
- **Jungle à étages**, pas une forêt :
  - fromagers géants à contreforts et couronne en parasol ;
  - arbres de voûte (un sur trois est un **acajou** BOP), figuiers étrangleurs creux, **palmiers** BOP sur les berges, palétuviers dans le delta ;
  - **saules pleureurs** BOP le long des rivières et du lac : des rideaux de lianes jusqu'au sol ;
  - **mousse espagnole** BOP qui pend des feuillages (13 500 blocs) ;
  - jeunes arbres, buissons, bambous, troncs couchés moussus ;
  - sous-bois dense : herbes, fougères, buissons, pousses et trèfle BOP, hautes herbes BOP et plantes de 2 blocs couvrent environ 80 % du sol, avec de nombreux jeunes arbres et buissons. Sous les arbres, on ne voit plus à 50 blocs. De rares **fleurs luisantes** brillent dans le noir ;
  - fleurs de jungle : hibiscus, cosmos orange, violettes, fleurs sauvages (BOP) ;
  - au bord de l'eau : **massettes** et **roseaux** (BOP), cannes à sucre, nénuphars fleuris et **nénuphars géants** ;
  - sur les plages : oyats et herbes des dunes ; **sable noir** sur les plages du volcan ;
  - **rideaux de lianes** : 120 000 blocs de lianes pendent des feuillages sur 3 à 14 blocs ;
  - **clairières** fleuries (herbes hautes, fougères géantes, orchidées, torchères, pétales roses, melons) : on y voit loin, et on y est vu ;
  - **mares** boueuses (40), avec nénuphars, grandes feuilles et cannes à sucre ;
  - **rochers moussus** (320), certains grands comme une cabane : de quoi se cacher ;
  - 38 **bambouseraies** ;
  - **versants et montagnes couverts** : mousse et herbe sur les pentes, buissons et jeunes arbres accrochés, parois tapissées de lianes par plaques (12 000 blocs). Seules les parois quasi verticales restent en roche nue.

Blocs vanilla 1.20.1 et **Biomes O' Plenty** (à installer, voir plus haut).

**Mesuré à l'échelle du spinosaure** (boîte de 3,4 × 5) :
- 97 % des colonnes de forêt gardent **au moins 6 blocs libres sous les feuillages** ;
- les rivières font **9 blocs de fond** en médiane, et 94 % font au moins 4 blocs ;
- les troncs de la voûte sont espacés d'au moins 8 blocs.

## Vérifié, et pas vérifié

- Chaque état de bloc (650) est contrôlé contre les données Minecraft 1.20 de minecraft-data : 0 erreur.
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

`python3 generer_ile.py sortie/` (numpy requis, environ 3 min) produit le monde (`sortie/Site B/`, à zipper dans `dist/site_b_monde.zip`), les 5 `.schem`, `site_b_v2.json` (coordonnées des lieux, des entrées de grottes et des trous bleus), `verif_monde.txt` (blocs témoins pour la CI), `blocs.npy`, `profond.npy` et `grottes.npy`. `python3 verif_monde.py sortie/` relit ensuite les régions. La graine est fixe : on obtient la même île à chaque fois. Pour remettre les panneaux, passer `PANNEAUX` à `True` dans `monde.py`.

| Module | Rôle |
|---|---|
| `relief.py` | forme de l'île, volcan, rivières, lac, lagon |
| `arbres.py` | les essences d'arbres |
| `campus.py` | les bâtiments du campus |
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
