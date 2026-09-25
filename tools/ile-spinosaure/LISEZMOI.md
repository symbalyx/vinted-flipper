# Site B — l'île du spinosaure (schematic WorldEdit)

Île de 384 × 384 blocs, 128 de haut, générée par `generer_ile.py`. Fichier : `dist/site_b.schem`
(format Sponge v2, Minecraft 1.20.1, biomes inclus).

## Ce qu'il y a dessus

- **Jungle géante, pensée pour sa taille.**
  - Troncs 2×2 ou 3×3 hauts de 20 à 34 blocs, avec contreforts, espacés de 10 à 12 blocs.
  - Canopée qui plonge le sol dans la pénombre. Mesuré : 99 % du sous-bois garde au moins 6 blocs de hauteur libre.
  - Lianes lumineuses (baies lumineuses) et fougères au sol : rien ne le bloque.
- **Montagne au nord-est** : lac de cratère et falaise ouest de 50 blocs, d'où tombe une **cascade**. **Grotte** derrière la chute.
- **Rivière** de la cascade jusqu'à l'embouchure au sud-ouest : 16 à 24 blocs de large, 7 de fond. C'est son territoire : il s'y submerge.
- **Site B, le complexe de recherche** :
  - rez-de-chaussée : hall, poste de sécurité, laboratoire avec cuves (une brisée), paillasses. **Couloirs de 2 blocs : il ne peut pas y entrer.**
  - étage : salle de contrôle vitrée au-dessus de l'enclos, bureaux, couveuse ; héliport sur le toit.
  - **sous-sol inondé** : eau noire, passerelles de 2 blocs, piliers ; salle du générateur au sec.
  - **enclos S-01** : bassin de 12 blocs de fond, murs de 12 m, **brèche** ouverte sur la rivière.
  - **tunnel de drainage noyé** entre l'enclos et le sous-sol, grille arrachée. C'est sa route pour entrer dans le bâtiment : l'embuscade.
  - hangar à bateaux et ponton sur la rivière ; clôture de périmètre trouée.
- **Ponton d'arrivée** au sud avec cabane et coffre de départ. Un chemin mène au laboratoire.
- **Tour de guet** (24 m) à l'ouest, **hélicoptère abattu** au nord-ouest, **campement abandonné** au nord, **pont suspendu cassé** sur la rivière.
- Des panneaux racontent ce qui s'est passé (« Il ne mange pas quand on le regarde. », « Rapport 17 : il suit les équipes sans jamais se montrer. »…).

## Coller l'île

1. Installer **WorldEdit** pour Forge 1.20.1. **FastAsyncWorldEdit** est bien plus rapide pour 19 millions de blocs.
2. Copier `site_b.schem` dans `.minecraft/config/worldedit/schematics/`.
3. Créer un monde **Superflat, préréglage « Le vide »**, ou se placer au-dessus d'un océan dégagé.
4. Se placer au **coin nord-ouest** voulu, **à y = 15**, pour que la mer du schematic tombe à y = 63 comme la mer vanilla :
   `/tp @s 0 15 0`
5. `//schem load site_b` puis `//paste -a -b`. `-a` ignore l'air ; `-b` applique les biomes : **toute l'île est en jungle, indispensable pour le spinosaure**.
6. L'île s'étend de +0 à +384 en x et en z. Le ponton d'arrivée est au sud, vers x = 176, z = 345.

Conseillé : `/gamerule mobGriefing true` (il arrache les feuilles qui le bloquent), et jouer de nuit.

## Régénérer ou modifier

`python3 generer_ile.py site_b.schem` (numpy requis), puis `python3 apercu.py site_b.schem` et
`python3 iso.py site_b.schem` pour les aperçus. La graine est fixe : même île à chaque fois.
