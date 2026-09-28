# Site B, l'île du spinosaure (v2), en schematic WorldEdit

Île de **768 × 768 blocs**, 160 de haut, générée par `generer_ile.py`. Elle est pensée pour un
événement : il y a une vingtaine de lieux, dispersés et reliés par des pistes dans la jungle.

Fichiers dans `dist/` (format Sponge v2, Minecraft 1.20.1, biomes inclus) :

| Fichier | Contenu |
|---|---|
| `site_b_v2.schem` | l'île entière (2,9 Mo) |
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

Aperçus dans `apercus/` : `carte.png`, `grottes.png` (en orange les galeries sèches, en cyan les parties noyées), `ile_iso.jpg`, `temple.jpg`, `village.jpg`, `helicoptere.jpg`, `fond_marin.jpg`.

## Les lieux

| Lieu | x, z | Ce qu'on y trouve |
|---|---|---|
| **Ponton d'arrivée** (départ) | 533, 603 | Ponton, bateau échoué, abri avec le coffre de départ (carte vierge, boussole, arbalète, barque). La route mène au campus. |
| **Campus Site B** | 455–600, 345–480 | Voir plus bas |
| Checkpoint | 519, 511 | Barrière cassée, guérite, sacs de sable, projecteur |
| Piste d'atterrissage | 546–626, 522 | Piste, hangar, manche à air |
| Avion cargo | 588, 562 | Écrasé en bord de plage, caisses éparpillées |
| Relais radio | 617, 450 | Local technique, mât haubané de 40 blocs |
| Village de pêcheurs | 655, 402 | Six maisons sur pilotis, toutes différentes : charpente apparente, volets, véranda couverte sur le ponton, toit à débord, cheminée, intérieur meublé. L'une a perdu sa porte et porte des griffures, une autre a le toit crevé. Ponton, séchoirs, barques. |
| Serres | 406, 476 | Trois serres voûtées, carreaux brisés, plantes |
| Lac central et **Repaire** | 342, 434 | Îlot couvert d'os et de carcasses, accessible seulement à la nage |
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
| Épave | 83, 608 | Bateau échoué sur le récif corallien |
| Station du delta | 336, 642 | Passerelle dans la mangrove, labo de terrain |

Des jeeps abandonnées jalonnent les pistes. Il n'y a **aucun panneau** : la carte se découvre en explorant.

### Nids

Six nids de spinosaure : une cuvette de vase, une couronne de racines tressées, des œufs (œufs de renifleur) et des restes de repas. Autant d'objectifs ou de points de rendez-vous.

| Nid | x, z |
|---|---|
| Corniche du cénote | 186, 273 (en bas du puits) |
| Grotte sous le volcan (ouest) | 551, 257 |
| Grotte sous le volcan | 608, 240 |
| Grotte sous le volcan (est) | 681, 223 |
| Berge du delta | 301, 633 |
| Berge du bras est | 644, 359 |

### Grottes

Une dizaine de réseaux de galeries sous les collines, le volcan et la crête ouest, avec 75 salles :
- des galeries principales de 6 à 9 blocs de diamètre : **le spinosaure y passe** ;
- des boyaux de 3 blocs, où seuls les joueurs passent ;
- des lacs souterrains au fond des parties basses ;
- des stalactites et stalagmites, de la mousse, des racines et lianes des cavernes, du lichen luisant rare, des toiles dans les boyaux, des ossements.

13 entrées (x, z) :
(521, 126), (136, 261), (691, 197), (618, 112), (164, 395), (103, 335), (609, 249), (182, 523), (458, 199), (422, 441), (410, 523), (462, 280), (684, 280). Deux d'entre elles sont des **gouffres** verticaux ouverts dans la jungle : on tombe dedans si on ne regarde pas où l'on marche.

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
- **Fond marin travaillé** : plage immergée puis tombant, bancs et rides de sable, gravier, argile et vase au large, pitons rocheux, **crevasses** étroites et sinueuses jusqu'à 18 blocs plus bas, forêts de kelp. **Sept trous bleus**, des puits à parois verticales jusqu'à 4 blocs du fond du monde, dont un dans le lagon : x, z = (150, 640), (712, 405), (708, 588), (79, 162), (32, 486), (287, 66), (495, 725).
- **Toutes les eaux libres sont au niveau de la mer** et forment un seul réseau : c'est son territoire.
- **Jungle à étages** :
  - fromagers géants à contreforts et couronne en parasol ;
  - arbres de voûte, figuiers étrangleurs creux, palmiers sur les berges, palétuviers dans le delta ;
  - jeunes arbres, buissons, bambous, troncs couchés moussus ;
  - sous-bois dense : herbes, fougères et plantes de 2 blocs couvrent environ 80 % du sol, avec de nombreux jeunes arbres et buissons. Sous les arbres, on ne voit plus à 50 blocs.

**Mesuré à l'échelle du spinosaure** (boîte de 3,4 × 5) :
- 97 % des colonnes de forêt gardent **au moins 6 blocs libres sous les feuillages** ;
- les rivières font **9 blocs de fond** en médiane, et 94 % font au moins 4 blocs ;
- les troncs de la voûte sont espacés d'au moins 8 blocs.

## Vérifié, et pas vérifié

- Chaque état de bloc (565) est contrôlé contre les données Minecraft 1.20 de minecraft-data : 0 erreur.
- Les fichiers portent le champ `BiomePaletteMax` exigé par WorldEdit 7.2.15 : sans lui, `//schem load` échouait avec « Unknown error ».
- **Côtes** : sur tout le tour de l'île, la terre au bord de la mer est au niveau de l'eau (0 bloc à escalader pour sortir de l'eau). Mesuré sur la carte des hauteurs.
- **Grottes** : 5 blocs de roche au moins entre le plafond et la surface, hors entrées. Toute cavité sous le niveau de la nappe est pleine d'eau, à surface plane, et rien ne coule. Une seule cellule d'air couverte touche de l'eau sur toute l'île : une niche de berge.
- Les fichiers ont été relus avec nbtlib :
  - dimensions et nombre de blocs exacts ;
  - palette, biomes et coffres.
- Vitres, barreaux, barrières et murets reçoivent leurs connexions à la génération : WorldEdit ne les recalcule pas au collage.
- **Aucun arbre flottant.** Un détecteur suit chaque bloc d'arbre jusqu'au sol, en connexité par faces, arêtes et coins : 0 bloc de tronc ou de feuillage isolé sur 760 000. Les 432 lianes qui ne rejoignent pas un tronc sont accrochées à un mur ou à un plafond de grotte : chacune a été contrôlée.
- Troncs, branches, racines et palmes sont tracés d'un seul tenant, reliés par les faces : pas de marches en diagonale.
- Aucune liane sans appui : chaque liane est accrochée à un bloc plein ou à la liane du dessus, et celles qui pendraient dans le vide sont retirées à la génération. Les propagules pendent sous des feuilles de palétuvier.
- **Chargé dans un vrai Minecraft** (WorldEdit 7.2.15, Forge 1.20.1) après la correction de `BiomePaletteMax`. **Pas encore vérifié en jeu** : l'orientation des portes, lits et escaliers, le rendu de la cascade (eau source, elle se met à couler dès qu'un bloc voisin change), le temple, les maisons et les grottes, et les performances au collage.

## Régénérer ou modifier

`python3 generer_ile.py sortie/` (numpy requis, environ 80 s) produit les 5 `.schem`, `site_b_v2.json` (coordonnées des lieux, des entrées de grottes et des trous bleus), `blocs.npy` et `grottes.npy`. La graine est fixe : on obtient la même île à chaque fois. Pour remettre les panneaux, passer `PANNEAUX` à `True` dans `monde.py`.

| Module | Rôle |
|---|---|
| `relief.py` | forme de l'île, volcan, rivières, lac, lagon |
| `arbres.py` | les essences d'arbres |
| `campus.py` | les bâtiments du campus |
| `mobilier.py` | meubles et façades |
| `lieux.py` | les autres lieux (temple maya, cénote, maisons, hélicoptère…) |
| `grottes.py` | grottes, gouffres, lacs souterrains et nids |
| `recits.py` | les journaux (plus utilisés : les coffres n'en contiennent plus) |
| `monde.py` | volume de blocs et écriture Sponge v2 |
| `rendu.py` | vues isométriques, plans d'étage et carte, pour vérifier sans lancer le jeu |
