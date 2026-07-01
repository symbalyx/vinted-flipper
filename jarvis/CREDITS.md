# Crédits & attributions

Ce projet réutilise des idées et/ou du code de projets open-source. Merci à
leurs auteurs. Les licences respectives sont reproduites ci-dessous par renvoi.

## OpenJarvis — Stanford Scaling Intelligence (Apache-2.0)
- Dépôt : https://github.com/open-jarvis/OpenJarvis
- Licence : Apache License 2.0
- Réutilisation ici : **langage visuel de l'interface** (système de tokens de
  design — palette cyan/zinc, rayons, ombres, hiérarchie typographique) adapté
  à notre interface vanilla/Flask dans `web/index.html` et `web/gardien.html`.
  Aucun code React/Tauri n'est copié ; seuls les *tokens de design* et principes
  visuels ont été réinterprétés en CSS natif (sans dépendance ni CDN externe).
- Conformément à Apache-2.0, voir le fichier `NOTICE`.

## Jarvis — Vignesh Rao / thevickypedia (MIT)
- Dépôt : https://github.com/thevickypedia/Jarvis
- Licence : MIT (Copyright (c) 2020 Vignesh Rao)
- Réutilisation ici : **schéma de conception** du détecteur enfichable avec
  garde d'import et dégradation gracieuse (inspiration pour
  `server/security_mod/detectors.py` : backend ONNX optionnel + fallback HOG,
  à la manière de leur intégration `face_recognition` import-guardée).
  Aucune ligne copiée telle quelle ; il s'agit d'une réimplémentation propre.

## jarvis-OS (AGPL-3.0) — INSPIRATION UNIQUEMENT, aucun code copié
- Dépôt : projet « jarvis-OS » fourni par le propriétaire (licence **AGPL-3.0**).
- ⚠️ L'AGPL-3.0 est un copyleft fort : copier son code imposerait l'AGPL à tout
  le projet (incompatible avec nos bases MIT/Apache). Nous n'avons donc **repris
  aucune ligne** de son code (ni `wakeup_setup/demo.html`, ni `WakeSequence.tsx`).
- Le **cœur JARVIS animé** (`web/os.html`) et le shell multi-fenêtres sont une
  **création originale** (SVG/CSS/canvas), inspirée de l'esthétique HUD Iron Man,
  écrite sans dépendance ni CDN.

## Natural Earth — fond de carte (domaine public)
- Source : Natural Earth (`ne_110m_admin_0_countries`, échelle 1:110m).
- Statut : **domaine public** (aucune restriction). Simplifié (coordonnées
  arrondies) et vendu localement dans `web/assets/world.geojson` pour la carte du
  JARVIS OS — **aucune tuile ni CDN externe** (100% auto-hébergé).

---
Le reste du projet JARVIS (v4/v5) provient de l'archive fournie par le
propriétaire du dépôt. Le mode Gardien et les durcissements de sécurité sont
ajoutés dans ce dépôt.
