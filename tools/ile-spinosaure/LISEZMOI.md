# Site B, l'île du spinosaure (v2), en schematic WorldEdit

Île de **768 × 768 blocs**, 160 de haut, générée par `generer_ile.py`. Elle est pensée pour un
événement : il y a une vingtaine de lieux, dispersés et reliés par des pistes dans la jungle.

Fichiers dans `dist/` (format Sponge v2, Minecraft 1.20.1, biomes inclus) :

| Fichier | Contenu |
|---|---|
| `site_b_v2.schem` | l'île entière (2,6 Mo) |
| `site_b_v2_0_0.schem` … `site_b_v2_1_1.schem` | la même île en 4 tuiles de 384 × 384, à coller une par une si le serveur rame |

## Coller l'île

1. Installer **WorldEdit** pour Forge 1.20.1. **FastAsyncWorldEdit** est fortement conseillé : il y a 94 millions de blocs.
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

L'intérieur des bâtiments reste très sombre, mais des blocs de lumière invisibles (niveau 3) y empêchent l'apparition des monstres vanilla.

## Les lieux

| Lieu | x, z | Ce qu'on y trouve |
|---|---|---|
| **Ponton d'arrivée** (départ) | 533, 603 | Ponton, bateau échoué, abri avec le coffre de départ (carte vierge, boussole, arbalète, barque). La route mène au campus. |
| **Campus Site B** | 455–600, 345–480 | Voir plus bas |
| Checkpoint | 519, 511 | Barrière cassée, guérite, sacs de sable, projecteur |
| Piste d'atterrissage | 546–626, 522 | Piste, hangar, manche à air |
| Avion cargo | 588, 562 | Écrasé en bord de plage, caisses éparpillées |
| Relais radio | 617, 450 | Local technique, mât haubané de 40 blocs |
| Village de pêcheurs | 650, 399 | Six maisons sur pilotis, ponton, séchoirs, barques |
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
| Hélicoptère abattu | 262, 196 | Carcasse couchée, sillon dans la jungle |
| Temple en ruine | 227, 269 | Pyramide à degrés, fresque en os, chambre basse au trésor |
| Tour de guet | 140, 357 | Sur la crête ouest, 26 blocs |
| Mine abandonnée | 202, 450 | Galerie boisée de 50 blocs, rails, minerai, salle du fond |
| Bunker | 265, 523 | Abri à demi enterré : couchettes, armurerie, vivres |
| Bungalows | 239, 568 | Trois cabanes sur pilotis au bord du lagon |
| Épave | 83, 608 | Bateau échoué sur le récif corallien |
| Station du delta | 336, 642 | Passerelle dans la mangrove, labo de terrain |

Aux carrefours, des **poteaux indicateurs** montrent la direction des lieux. Des jeeps abandonnées jalonnent les pistes.

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

### L'histoire

Huit **journaux écrits** sont cachés dans les coffres :
- le rapport du directeur ;
- le carnet d'un pêcheur ;
- la station delta ;
- le gardien du phare ;
- la mine ;
- le temple ;
- les ordres du bunker ;
- la dernière page, dans la grotte.

Des panneaux complètent le récit. Ensemble, ils suggèrent des objectifs pour l'événement :
- relancer le groupe de secours au sous-sol des labos ;
- joindre le relais radio ;
- trouver l'antre ;
- tenir jusqu'à l'évacuation au ponton sud.

## Le terrain

- Volcan au nord-est : lac de cratère perché, cascade, gorge.
- Crête rocheuse à l'ouest, avec falaises en gradins.
- Rivière principale : de la cascade au lac central, puis en delta à mangrove au sud, avec un affluent et un bras vers l'est.
- Lagon et récif de corail au sud-ouest, plages de sable.
- **Toutes les eaux libres sont au niveau de la mer** et forment un seul réseau : c'est son territoire.
- **Jungle à étages** :
  - fromagers géants à contreforts et couronne en parasol ;
  - arbres de voûte, figuiers étrangleurs creux, palmiers sur les berges, palétuviers dans le delta ;
  - jeunes arbres, buissons, bambous, troncs couchés moussus ;
  - sous-bois de fougères.

**Mesuré à l'échelle du spinosaure** (boîte de 3,4 × 5) :
- 97 % des colonnes de forêt gardent **au moins 6 blocs libres sous les feuillages** ;
- les rivières font **9 blocs de fond** en médiane, et 94 % font au moins 4 blocs ;
- les troncs de la voûte sont espacés d'au moins 8 blocs.

## Vérifié, et pas vérifié

- Chaque état de bloc (plus de 500) est contrôlé contre les données Minecraft 1.20 de minecraft-data : 0 erreur.
- Les fichiers ont été relus avec nbtlib :
  - dimensions et nombre de blocs exacts ;
  - palette, biomes, coffres et panneaux ;
  - pages des journaux.
- Vitres, barreaux, barrières et murets reçoivent leurs connexions à la génération : WorldEdit ne les recalcule pas au collage.
- **Pas testé dans un vrai Minecraft**. À vérifier au premier collage : l'orientation des portes, lits et escaliers, et le rendu de la cascade. La cascade est faite d'eau source et se met à couler dès qu'un bloc voisin change.

## Régénérer ou modifier

`python3 generer_ile.py sortie/` (numpy requis) produit les 5 `.schem`, `site_b_v2.json` (coordonnées des lieux) et `blocs.npy`. La graine est fixe : on obtient la même île à chaque fois.

| Module | Rôle |
|---|---|
| `relief.py` | forme de l'île, volcan, rivières, lac, lagon |
| `arbres.py` | les essences d'arbres |
| `campus.py` | les bâtiments du campus |
| `mobilier.py` | meubles et façades |
| `lieux.py` | les autres lieux |
| `recits.py` | les journaux |
| `monde.py` | volume de blocs et écriture Sponge v2 |
| `rendu.py` | vues isométriques, plans d'étage et carte, pour vérifier sans lancer le jeu |
