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

---
Le reste du projet JARVIS (v4/v5) provient de l'archive fournie par le
propriétaire du dépôt. Le mode Gardien et les durcissements de sécurité sont
ajoutés dans ce dépôt.
