# Site B, l'île du spinosaure (v2), en schematic WorldEdit

Île de **768 × 768 blocs**, 160 de haut, générée par `generer_ile.py`. Elle est pensée pour un
événement : il y a une vingtaine de lieux, dispersés et reliés par des pistes dans la jungle.

Fichiers dans `dist/` (format Sponge v2, Minecraft 1.20.1, biomes inclus) :

| Fichier | Contenu |
|---|---|
| `site_b_v2.schem` | l'île entière (4,1 Mo) |
| `site_b_v2_0_0.schem` … `site_b_v2_1_1.schem` | la même île en 4 tuiles de 384 × 384, à coller une par une si le serveur rame |

## Coller l'île

1. Installer **WorldEdit** pour Forge 1.20.1 (7.2.15). FastAsyncWorldEdit n'existe pas pour Forge : avec 94 millions de blocs, préférer **les 4 tuiles** et donner 6 à 8 Go de mémoire au jeu.
2. Copier les `.schem` dans `.minecraft/config/worldedit/schematics/`, ou `config/worldedit/schematics/` sur un serveur.
3. Monde **Superflat, préréglage « Le vide »**, ou un océan dégagé.
4. Coller avec **le coin nord-ouest en (X, 15, Z)**. La mer du schematic tombe alors à y = 63, comme la mer vanilla.
   - **Fichier complet** : `/tp @s X 15 Z`, puis `//schem load site_b_v2`, puis `//paste -a -b`.
   - **En tuiles** : la tuile `site_b_v2_i_j` se colle en `(X + 384·i, 15, Z + 384·j)`. Même commande pour chacune.
   - `-a` ignore l'air. `-b` applique les biomes : **toute la terre est en jungle, indispensable au spinosaure**.
5. Les coordonnées ci-dessous sont relatives à ce coin (X, Z).

Réglages conseillés pour l'événement :
- `/gamerule mobGriefing true` : il arrache les feuilles qui le bloquent ;
- `/gamerule doDaylightCycle` à votre goût, la nuit étant bien plus tendue ;
- `/setworldspawn` au ponton d'arrivée.

L'intérieur des bâtiments reste très sombre, mais des blocs de lumière invisibles (niveau 3) y empêchent l'apparition des monstres vanilla. Les grottes, elles, ne sont pas éclairées : des monstres vanilla peuvent y apparaître la nuit comme le jour.

Aperçus dans `apercus/` : `carte.png`, `grottes.png` (en orange les galeries sèches, en cyan les parties noyées), `ile_iso.jpg`, `temple.jpg`, `cenote.jpg`, `village.jpg`, `helicoptere.jpg`, `epave.jpg`, `fond_marin.jpg` (récif et lagon, sans l'eau), `cratere.jpg` (coupe), `jungle.jpg` (coupe dans la jungle : sous-bois, lianes, minerais dans la roche), `mine.jpg` (la mine vue de dessus), `gue.jpg`.

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

### Sous-sol : grottes, galeries et minerais

Sous l'île, un sous-sol **comme dans un monde classique** :
- **Cavernes vanilla :** galeries sinueuses entrelacées (« spaghetti ») et grandes cavernes (« fromage »), sous toutes les collines, soit 630 000 blocs creusés. Les parties basses sont noyées : ce sont des lacs souterrains.
- **Grottes à salles :** 72 salles avec des galeries principales où **le spinosaure passe**, et des boyaux de 3 blocs pour les joueurs. On y trouve :
  - des parois irrégulières (niches, surplombs) ;
  - des colonnes de stalactites qui rejoignent le sol et des éboulis ;
  - des salles envahies de végétation ;
  - des racines, des lianes des cavernes et des ossements.
- **Minerais** répartis par profondeur comme en 1.20 :
  - charbon (≈ 220 000 blocs), fer (≈ 100 000) et cuivre (≈ 110 000) ;
  - or, redstone et lapis en profondeur ;
  - diamant tout en bas ;
  - émeraude sous les hauteurs.

  Ceux qui affleurent dans les grottes se voient à la lampe.
- **Mine abandonnée de type vanilla** sous la crête ouest (147, 417) : 16 couloirs de 3 × 3 étayés (poteaux et poutres), rails, toiles d'araignée et quelques coffres. Elle croise les cavernes.
- **Entrées :** des porches rocheux en surplomb et deux gouffres ouverts dans la jungle. Les 11 entrées (x, z) sont : (169, 472), (98, 354), (644, 144), (543, 106), (144, 255), (559, 257), (645, 228), (503, 182), (180, 391), (422, 505), (426, 209). Leurs coordonnées exactes sont aussi dans `site_b_v2.json`.

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
  - arbres de voûte, figuiers étrangleurs creux, palmiers sur les berges, palétuviers dans le delta ;
  - jeunes arbres, buissons, bambous, troncs couchés moussus ;
  - sous-bois dense : herbes, fougères et plantes de 2 blocs couvrent environ 80 % du sol, avec de nombreux jeunes arbres et buissons. Sous les arbres, on ne voit plus à 50 blocs ;
  - **rideaux de lianes** : 120 000 blocs de lianes pendent des feuillages sur 3 à 14 blocs ;
  - **clairières** fleuries (herbes hautes, fougères géantes, orchidées, torchères, pétales roses, melons) : on y voit loin, et on y est vu ;
  - **mares** boueuses (40), avec nénuphars, grandes feuilles et cannes à sucre ;
  - **rochers moussus** (320), certains grands comme une cabane : de quoi se cacher ;
  - 38 **bambouseraies** ;
  - **versants et montagnes couverts** : mousse et herbe sur les pentes, buissons et jeunes arbres accrochés, parois tapissées de lianes par plaques (12 000 blocs). Seules les parois quasi verticales restent en roche nue.

Tout est en blocs vanilla 1.20.1 : **aucun mod à installer**.

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

`python3 generer_ile.py sortie/` (numpy requis, environ 3 min) produit les 5 `.schem`, `site_b_v2.json` (coordonnées des lieux, des entrées de grottes et des trous bleus), `blocs.npy` et `grottes.npy`. La graine est fixe : on obtient la même île à chaque fois. Pour remettre les panneaux, passer `PANNEAUX` à `True` dans `monde.py`.

| Module | Rôle |
|---|---|
| `relief.py` | forme de l'île, volcan, rivières, lac, lagon |
| `arbres.py` | les essences d'arbres |
| `campus.py` | les bâtiments du campus |
| `mobilier.py` | meubles et façades |
| `lieux.py` | les autres lieux (temple maya, cénote, maisons, hélicoptère…) |
| `grottes.py` | grottes, gouffres, lacs souterrains, antre et nids |
| `details.py` | falaises et récif en volume |
| `flore.py` | clairières, mares, rochers, rideaux de lianes, lianes des falaises |
| `recits.py` | les journaux (plus utilisés : les coffres n'en contiennent plus) |
| `monde.py` | volume de blocs et écriture Sponge v2 |
| `rendu.py` | vues isométriques, plans d'étage et carte, pour vérifier sans lancer le jeu |
