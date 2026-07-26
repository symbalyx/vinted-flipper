# Site RHESO

Site vitrine du système RHESO. Aucun build à exécuter pour servir la page :
`site/` se déploie tel quel.

```
site/
  index.html      la page entière (styles + script + polices + logo embarqués)
  fondateurs.webp photo du héros
  equipe.webp     photo de la section « Qui sommes-nous ? »
  favicon.svg     logo RHESO, rouge brique sur crème
  _headers        CSP et en-têtes de sécurité (Cloudflare Pages)
  robots.txt      indexation autorisée, collecte pour entraînement refusée
```

## Déploiement Cloudflare Pages

1. Nouveau projet Pages → *Direct Upload*, ou connexion au dépôt.
2. Build command : **aucune**. Output directory : **`site`**.
3. `_headers` applique la CSP. La page fonctionne sous `default-src 'self'`
   sans `connect-src` : elle ne fait aucun appel réseau.

La page s’ouvre aussi en local (`file://`), à la nuance près que les deux
photos ne s’affichent que si les `.webp` sont dans le même dossier.

## Ce que la page publie — et ce qu’elle ne publie pas

C’est la règle la plus importante de ce dépôt.

**Publié** — ce qui rend la vitrine crédible :

- les cinq curseurs : nom, sous-titre, question, point de vigilance ;
- les vingt-cinq réglages : code, libellé, définition en une ligne ;
- la mécanique de la console : crans, mix, lecture des combinaisons ;
- **une seule fiche complète**, `H3 « J’écoute vraiment »`, en démonstration.

**Non publié** — le cœur du savoir-faire :

- « ce que je fais », « ce que je dis », l’intention et la frontière avec le
  niveau voisin, pour les vingt-quatre autres réglages ;
- les règles d’interaction prescriptives entre curseurs. La console nomme la
  combinaison visible (« Intensité maximale et jeu fermé »), elle ne donne pas
  la conduite à tenir.

Tout ce qui part dans `index.html` est lisible par n’importe qui : « voir le
code source » suffit, aucune obfuscation n’y change rien. **La seule protection
réelle est de ne pas expédier le contenu.** C’est le parti pris de
`06-data.js` : les champs `do`, `say`, `int` et `bd` n’existent que sur la
fiche marquée `full:true`.

Si vous ajoutez un contenu de fiche, vous le rendez public. Le drapeau
`full:true` ne doit rester que sur `H3`.

`robots.txt` refuse les collecteurs d’entraînement connus (GPTBot, ClaudeBot,
CCBot, Google-Extended, PerplexityBot…) et `_headers` ajoute
`X-Robots-Tag: noarchive, noai, noimageai`. Ces directives sont respectées par
les acteurs qui choisissent de les respecter : elles complètent la règle
ci-dessus, elles ne la remplacent pas.

## Modifier le site

`index.html` est assemblé à partir de `dev/` :

```
dev/
  build.py            assemble tout dans site/ ; trace aussi les motifs
  00-head.html        <head> + métadonnées
  01-tokens.css       palette, échelle typographique, espacements
  02-base.css         base, typographie, boutons, marque
  03-layout.css       en-tête, héros et toutes les sections
  04-console.css      la console
  05-body.html        le contenu de la page
  06-data.js          les données publiées  ← lire la note ci-dessus
  07-app.js           la console et le reste de l’interface
  logo.svg            logo vectorisé depuis la plaquette
  face-*.css          Montserrat et JetBrains Mono, embarquées en woff2
```

```sh
cd dev && python3 build.py     # réécrit site/index.html et site/favicon.svg
```

Éditez les fichiers de `dev/`, jamais `site/index.html` directement — il est
régénéré à chaque exécution.

## Charte

Relevée sur la présentation RHESO : crème `#FBF5DF`, vert profond `#234A33`,
rouge brique `#8E1710`, or `#C29A0C`. Typographie **Montserrat** (titres et
texte) et **JetBrains Mono** (codes, surtitres, valeurs) — celles du site
précédent, conservées.

Les cinq couleurs de curseur viennent du référentiel : R vert, H or, E orange,
S turquoise, O rose. Chacune existe en trois variantes, et les confondre est
la principale source de problèmes de contraste :

| variante | usage |
|---|---|
| `--x`   | traits et surfaces décoratives |
| `--x-t` | texte sur crème, **et** fond des surfaces pleines portant du texte blanc |
| `--x-l` | texte et traits sur le vert profond |

L’or brut ne supporte pas le texte blanc : toute surface pleine qui porte du
blanc utilise `--x-t`, jamais `--x`.

## Parti pris

- **Aucune animation de décor.** Pas de banderole défilante, pas d’apparition
  au scroll, pas de VU-mètre. Les transitions ne servent qu’aux états
  interactifs et à l’aiguille des boutons rotatifs.
- **Asymétrie.** Les blocs commencent rarement colonne 1 et finissent rarement
  colonne 12 ; les listes s’indentent progressivement ; les colonnes n’ont pas
  la même largeur ni la même hauteur de départ. Seul le pupitre de la console
  est symétrique : c’est un instrument.
- **La console se manipule vraiment.** Glisser le bouton, toucher un cran, ou
  les flèches du clavier — les trois marchent, au doigt comme à la souris.
  Chaque curseur est un `role="slider"` unique pour les lecteurs d’écran ; les
  diodes sont des raccourcis à la souris (`aria-hidden`).

## Qualité

Vérifié sur la page assemblée, à chaque build :

- **contraste** : tout le texte rendu atteint WCAG AA, dans les deux états de
  la fiche (démo et verrouillée) ;
- **largeurs** : aucun débordement horizontal de 320 à 1920 px ;
- **cibles tactiles** : ≥ 44 px pour les commandes, ≥ 30 px pour les diodes ;
- **console** : glisser, appui simple, diodes, clavier (`↑` `↓` `Début` `Fin`
  `1`–`5`), rappels de situation, partage par URL `#reglage=R4H3E3S3O2`.

`prefers-reduced-motion` est respecté.
