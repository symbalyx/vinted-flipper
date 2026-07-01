# CHANGELOG_GUARDIAN — JARVIS v5.4

## v5.4 — Photo jointe au chat et OSINT autorisé

- ajout d'un bouton de pièce jointe dans le chat principal ;
- commande naturelle « trouve où cette photo a été prise » ;
- traitement direct par le module spécialisé, sans envoyer l'image au LLM de chat ;
- attestation explicite de propriété ou d'autorisation ;
- finalités bornées : média personnel, bien contrôlé, lieu public, commerce ;
- refus serveur des recherches de personne, domicile, identité, réseaux sociaux,
  plaque, suivi en temps réel et demandes de « doxxing » ;
- nouveau module `server/guardian/legal_osint.py` ;
- réponse conversationnelle avec lien OpenStreetMap ;
- aucune image persistée dans l'historique ou le journal ;
- sept tests supplémentaires, pour un total de 166 tests.

## Objectif de cette révision

Reprendre l’intégration Gardien interrompue, corriger les failles de sécurité
encore présentes et rendre utilisable la fonction **Photo → globe** sans
présenter une estimation IA comme une localisation certaine.

Priorités appliquées : **sécurité → absence de faux déclenchement → intégration
au backend existant → fonctionnement local → interface mobile**.

## Audit de reprise

L’archive v5.2 contenait déjà une architecture Gardien modulaire, une machine
d’état, un gestionnaire d’approbations, SQLite, l’appairage et des tests. Les
principaux défauts restant dans la version reprise étaient :

- rendu dynamique du tableau de bord par chaînes HTML interprétées, donc risque
  XSS avec les réponses IA, titres, alertes ou métadonnées ;
- jeton d’API conservé durablement dans le stockage du navigateur ;
- ancien parser de balises LLM encore capable d’atteindre des chemins d’actions
  sensibles ;
- ancienne interface HTML embarquée dans `jarvis_v4.py`, dupliquée et difficile
  à sécuriser ;
- géolocalisation photo backend non reliée à l’interface ;
- absence de distinction nette, côté utilisateur, entre GPS EXIF et estimation
  visuelle ;
- désarmement API sans confirmation explicite et taille HTTP globale non bornée.

## Changements de sécurité

### Interface principale

- Réécriture du script de `web/index.html` avec création explicite de nœuds DOM
  et `textContent` pour toute donnée non fiable.
- Suppression des ressources Google Fonts et autres dépendances visuelles
  distantes.
- Jeton `X-JARVIS-Token` conservé uniquement en mémoire vive ; les anciennes
  clés de stockage sont purgées.
- Ajout de délais d’expiration réseau avec `AbortController`.
- Conservation de la palette de commandes, des conversations, de la maison,
  de la sécurité, du système, de la timeline, des approbations et du SSE.

### Backend

- Suppression de l’ancien `DASHBOARD_HTML` intégré au fichier Python ; `/`
  redirige vers `/app`.
- Limite globale de requête via `MAX_CONTENT_LENGTH` et réponse JSON `413`.
- Désarmement refusé sans `confirm=true`.
- CSP resserrée, sans domaine de police tiers, avec `object-src 'none'`.
- `JARVIS_LEGACY_TAGS=0` neutralise toutes les anciennes balises.
- Même en mode compatibilité, seules quelques opérations strictement
  `READ_ONLY` sont acceptables ; les balises critiques restent inertes.
- Le prompt système impose le function calling validé et les approbations côté
  application pour les actions sensibles ou critiques.
- Aucune valeur de clé cloud de démonstration n’est embarquée par défaut.
- Mise à jour du fournisseur OpenAI Realtime vers `/v1/realtime/client_secrets`,
  modèle configurable avec `gpt-realtime-2` par défaut, TTL borné et secret
  éphémère validé avant retour au navigateur.

## Photo → globe

### Backend

Nouveau module `server/guardian/geolocation.py` :

1. validation base64/data URL ;
2. formats autorisés : JPEG, PNG, WebP ;
3. limites d’octets et de pixels ;
4. lecture GPS EXIF avant tout appel vision ;
5. validation stricte du JSON vision ;
6. cinq candidats maximum ;
7. confiance minimale configurable ;
8. précision visuelle minimale forcée à 100 mètres ;
9. rate-limit dédié ;
10. aucune persistance de l’image.

Un GPS EXIF est affiché comme une coordonnée contenue dans le fichier, pas comme
une preuve infalsifiable. Sans EXIF, le résultat porte toujours
`exact=false` et `source=vision_estimate`. Si les indices sont insuffisants ou
le JSON invalide, le résultat est `unknown`.

Route ajoutée : `POST /api/guardian/geolocate`.

### Interface

Le module **Photo → globe** est accessible dans `web/os.html` et directement par
`/os#photo`. Il affiche :

- l’aperçu local de l’image ;
- la source EXIF ou estimation visuelle ;
- la confiance ;
- la précision estimée ;
- les indices et incertitudes ;
- les candidats cliquables sur le globe hors ligne.

## Tests ajoutés

- `tests/test_frontend_security.py`
- `tests/test_legacy_tags_disabled.py`
- `tests/test_photo_geolocation.py`
- `tests/test_openai_realtime_provider.py`

Ils couvrent notamment : XSS, absence de persistance du jeton, absence de
ressources tierces, CSP, limite de requête, confirmation de désarmement,
neutralisation des balises critiques, validation d’image, JSON vision invalide,
prudence de précision, coordonnées EXIF et références GPS encodées en octets.

Le résultat exact de la livraison est dans `TEST_RESULTS.md`.

## Limites restantes

- Une photo ordinaire sans GPS ni repère unique ne peut pas être localisée
  précisément de manière fiable. JARVIS fournit alors une estimation ou refuse.
- Les métadonnées EXIF peuvent être supprimées ou falsifiées.
- La CSP utilise encore des scripts/styles inline historiques ; leur extraction
  dans des fichiers statiques séparés reste une amélioration recommandée.
- `server/jarvis_v4.py` demeure partiellement monolithique malgré la suppression
  de l’ancienne UI et l’utilisation des modules Gardien.
- OpenAI Realtime n’a pas été vérifié avec une vraie clé dans cette livraison ;
  Gemini Live reste explicitement incomplet.
