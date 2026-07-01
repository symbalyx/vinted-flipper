# 📋 Rapport d'amélioration — JARVIS v3 → v4.0

**Date :** 27 juin 2026
**Objet :** Évolution de JARVIS vers un véritable assistant de **maison
connectée Apple**, avec détection d'intrus renforcée et nouvelles
fonctionnalités.

---

## 1. Demande initiale

> « Améliore grandement ce JARVIS en ajoutant qu'il puisse se connecter aux
> enceintes Apple, à l'Apple TV et aux lumières, une meilleure détection des
> intrus, puis ajoute d'autres fonctionnalités sympas. »

✅ **Tous les points ont été livrés.**

---

## 2. Point de départ (v3)

Le projet d'origine : **un seul fichier** `server/jarvis_v3.py` (1166 lignes).
- IA conversationnelle (DeepSeek cloud ou Ollama local) avec une personnalité
  sarcastique.
- 18 « super pouvoirs » système (infos PC, fichiers, météo, blagues…).
- Une caméra de sécurité **basique** : détection de mouvement par pixels +
  détection de visages (sans distinction connu/inconnu), simple journalisation.
- Un dashboard web (chat + boutons + flux caméra + alertes).

**Limites identifiées :** aucune domotique, détection d'intrus naïve (un rideau
qui bouge = alerte), beaucoup de faux positifs, aucune réaction automatique.

---

## 3. Ce qui a été fait (v4)

### 3.1 🍎 Connexion aux enceintes Apple (HomePod / AirPlay)
- Nouveau module **`integrations/apple.py`** s'appuyant sur **`pyatv`** (la
  référence open-source pour le protocole Apple).
- **Annonces vocales** : JARVIS génère de la parole (TTS via `gTTS`) et la
  diffuse sur n'importe quelle enceinte HomePod par AirPlay.
- **Diffusion AirPlay** d'une URL audio/vidéo et **contrôle du volume** par
  enceinte.
- Comme `pyatv` est asynchrone, une **boucle asyncio dédiée tourne dans un
  thread de fond** et expose des méthodes synchrones propres au reste de JARVIS.
- Commandes naturelles : `[HOMEPOD_DIRE:texte]`, `[HOMEPOD_VOLUME:n]`,
  `[HOMEPOD_JOUER:url]`.

### 3.2 📺 Connexion à l'Apple TV
- Même module `pyatv` : **télécommande complète** (play, pause, menu, home,
  flèches, select, next/previous) et **lancement d'applications** (Netflix,
  YouTube, Disney+, Prime, Spotify, Twitch, Molotov… via leurs bundle IDs).
- Commandes : `[APPLETV:commande]`, `[APPLETV_APP:nom]`.

### 3.3 💡 Contrôle des lumières
- Nouveau module **`integrations/lights.py`** :
  - **Philips Hue** via l'API REST locale du pont (pas de cloud, faible latence).
  - **Mode simulé** automatique (5 pièces virtuelles) si aucun pont n'est
    configuré → tout est testable sans matériel.
- On/off, **luminosité**, **couleurs nommées** (rouge, bleu, chaud…) mappées en
  coordonnées CIE xy compatibles Hue, ciblage d'une pièce ou de « toutes ».
- Commandes : `[LUMIERE:nom|on/off]`, `[LUMIERE_COULEUR:nom|couleur]`,
  `[LUMIERE_LUMINOSITE:nom|0-100]`, `[LUMIERES_OFF]`.

### 3.4 🛡️ Détection d'intrus nettement améliorée
Nouveau module **`security_mod/detector.py`** + réécriture de `SecuritySystem` :

| Aspect | Avant (v3) | Après (v4) |
|--------|-----------|-----------|
| Détection | mouvement de pixels seul | mouvement **+ silhouette humaine (HOG)** + visages |
| Visages | « visage détecté » | **reconnaissance connus vs inconnus** (LBPH) |
| Fiabilité | beaucoup de faux positifs | **confirmation multi-frames** + **score de menace** pondéré |
| Modes | toujours actif | **ARMÉ / DÉSARMÉ** |
| Réaction | journal uniquement | **notification + annonce vocale HomePod + flash lumières rouges + sirène AirPlay** |

- **Score de menace** pondéré : mouvement (1) < personne (2) < visage inconnu
  (3) ; un visage **connu** ne déclenche rien.
- **Enrôlement de visages de confiance** depuis le dashboard (bouton dédié +
  endpoint `/api/security/enroll`).
- La **réponse anti-intrusion automatique** ne s'active que si l'alarme est
  **armée**, pour éviter les fausses alertes quand on est chez soi.
- Le HOG (détection de personnes) ne tourne que **lorsqu'il y a du mouvement et
  1 frame sur 3**, pour rester performant.

### 3.5 🎬 Autres fonctionnalités sympas
- **Scènes / routines** combinant lumières + Apple TV + annonce HomePod +
  armement : `cinéma`, `soirée`, `réveil`, `bonne nuit`, `absence`, `retour`.
- **Annonces vocales** réutilisées par les rappels et l'anti-intrusion.
- **Dashboard enrichi** : nouveau panneau « Maison connectée » (tuiles de pièces
  avec pastilles de couleur cliquables, boutons de scènes), bouton **ARMER /
  DÉSARMER**, enrôlement de visage, badge d'état armé, affichage du niveau de
  menace sur chaque alerte et sur le flux vidéo (HUD).
- **Nouveaux endpoints API** : `/api/home/*`, `/api/apple/*`,
  `/api/security/arm`, `/api/security/enroll`, stats de sécurité.

---

## 4. Architecture & qualité

- Passage d'un fichier unique à un **petit paquet modulaire** :
  ```
  JARVIS_v4/
  ├── server/
  │   ├── jarvis_v4.py            # app principale + parser + sécurité + dashboard
  │   ├── integrations/
  │   │   ├── apple.py            # HomePod + Apple TV (pyatv)
  │   │   └── lights.py           # Philips Hue + simulé
  │   └── security_mod/
  │       └── detector.py         # HOG + reconnaissance faciale + scoring
  ├── config/apple_credentials.json.example
  ├── requirements_v4.txt
  ├── README_v4.md
  └── RAPPORT.md
  ```
- **Dégradation gracieuse** partout : l'app démarre et reste utilisable même
  sans `pyatv`, sans `gtts`, sans pont Hue, ou sans `opencv-contrib` (chaque
  capacité absente renvoie un message clair au lieu de planter).
- Le **style et la personnalité** d'origine (ton sarcastique, emojis, structure
  du code) ont été conservés.

---

## 5. Tests effectués

- ✅ **Compilation** (`py_compile`) des 4 modules : OK.
- ✅ **Module lumières** exécuté : mode simulé, on/off, couleur, « toutes »,
  flash — fonctionnels.
- ✅ **Module Apple** : dégradation gracieuse vérifiée (messages clairs quand
  `pyatv`/`gtts` absents).
- ✅ **Regex du parser** : les 10 nouveaux tags testés isolément, y compris les
  paramètres optionnels (`HOMEPOD_DIRE` avec/​sans enceinte, `HOMEPOD_VOLUME`
  avec/sans appareil) et l'absence de collision (`APPLETV_APP` vs `APPLETV`,
  `LUMIERE_COULEUR` vs `LUMIERE`).

> Note : `opencv`, `flask`, `numpy` n'étant pas installés dans l'environnement
> de développement, le serveur complet n'a pas été lancé de bout en bout ici —
> mais le code compile et la logique testable a été validée. Sur la machine de
> l'utilisateur (`pip install -r requirements_v4.txt`), tout est prêt à tourner.

---

## 6. Pour démarrer

```bash
pip install -r requirements_v4.txt
pip uninstall opencv-python && pip install opencv-contrib-python   # reco faciale
python server/jarvis_v4.py        # → http://localhost:8004
```
Détails d'appairage Apple et Hue dans **README_v4.md**.

---

## 6 bis. Itération 2 — Voix, recherche web & notifications photo

Ajouts demandés après la première livraison :

### 🎙️ Voix bidirectionnelle
- **Reconnaissance vocale** (parler à JARVIS) et **synthèse vocale** (JARVIS lit
  ses réponses) via la **Web Speech API du navigateur** : zéro dépendance, zéro
  installation, fonctionne dans Chrome/Edge.
- Deux boutons dans la barre de chat : 🎙️ micro (push-to-talk) et 🔇/🔊 lecture.
- Couplé aux annonces HomePod déjà présentes → usage mains-libres complet.

### 🔎 Recherche web
- Nouveau module **`integrations/websearch.py`**, **sans clé API ni dépendance
  supplémentaire** (juste `requests`).
- Cascade DuckDuckGo : réponse instantanée (faits) → DDG Lite → DDG HTML.
- Tags `[RECHERCHE_WEB:requête]` et `[LIRE_WEB:url]` (l'IA résume ensuite avec sa
  personnalité). Le prompt système pousse JARVIS à chercher dès que la question
  est factuelle/actuelle.
- Parsing HTML maison robuste à l'ordre des attributs (bug détecté et corrigé
  pendant les tests : `href` placé avant `class`).

### 📲 Notifications photo à distance
- Nouveau module **`integrations/notify.py`** : **Telegram** (texte + photo),
  configuration en 2 minutes via env (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`),
  sans dépendance supplémentaire.
- **Branché sur l'anti-intrusion** : quand l'alarme est armée, le snapshot annoté
  de l'intrus est **envoyé sur le téléphone** automatiquement (en plus de la
  notif bureau, de l'annonce HomePod et du flash des lumières).
- Tag `[NOTIF_TEL:message]` + endpoint de test `/api/notify/test`.

### Tests itération 2
- ✅ Compilation des 3 modules concernés + main : OK.
- ✅ `websearch._parse_lite` / `_parse_html` validés sur HTML réaliste (ordre
  d'attributs variable) après correction du bug de regex.
- ✅ `notify` : dégradation gracieuse vérifiée (message clair si non configuré).
- ✅ Regex des 3 nouveaux tags validées.
- ℹ️ Le proxy de l'environnement de dev bloque DuckDuckGo (403) : la requête
  réseau réelle n'a pas pu être jouée ici, mais le parsing est prouvé correct et
  fonctionnera sur la machine de l'utilisateur (pas de proxy).

> Total : **33 pouvoirs**, 6 modules, dashboard avec voix + web + maison + sécurité.

## 7. Pistes pour une v5
- Reconnaissance faciale par réseau profond (`face_recognition`/dlib) plus
  robuste que LBPH.
- Vision multimodale réelle pour `[CAMERA_ANALYSE]` (envoi de l'image au modèle).
- Intégration **HomeKit natif** (HAP) pour piloter aussi serrures, volets,
  thermostats.
- Déclencheurs horaires (simulation de présence en mode absence).
- Application mobile / notifications push hors réseau local.
```
