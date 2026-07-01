# CHANGELOG — Intégration du Mode Gardien (JARVIS v5.2)

Ce document tient lieu d'**audit**, de **journal des changements**, de **liste
des fichiers modifiés**, de **choix d'architecture** et de **limitations**.
Priorité tenue : **sécurité → zéro faux déclenchement → intégration backend**.

---

## 1. Audit (état initial)

### Architecture actuelle
- **Monolithe** `server/jarvis_v4.py` (~2 500 lignes) : app Flask, `AIEngine`,
  `JarvisPowers`, `SecuritySystem` (OpenCV), routes, **2 UI HTML embarquées**
  (`DASHBOARD_HTML`, `LOGIN_HTML`) en plus de `web/index.html`.
- Modules propres : `agent.py` (function-calling), `emergency.py`,
  `security_mod/detector.py` (HOG + LBPH + comportement), `vision.py` (Ollama),
  `pc_control.py`, `integrations/*`, `memory.py`, `event_log.py`, `learning.py`.
- Persistance = **JSON épars** (`memory/*.json`, `events.jsonl`).

### Fonctions réellement opérationnelles (vérifiées, tests passants)
- Auth (mot de passe + jeton, rate-limit, comparaison à temps constant).
- Durcissements existants : `run_cmd` liste blanche, anti-traversée fichiers,
  SSRF websearch, échappement TwiML. **48 tests historiques passent.**
- Agent function-calling (multi-tours, fallback gracieux).
- Détection : mouvement + HOG + LBPH + analyse comportementale.

### Code dupliqué
- **Trois interfaces** : `DASHBOARD_HTML` (dans le .py), `LOGIN_HTML`,
  `web/index.html`. → on ne conserve qu'`web/index.html` ; `/` redirige `/app`.

### Bugs logiques (corrigés)
- **Reset du suivi de présence** : `behavior.update(persons, …)` recevait `[]`
  sur les frames où la détection lourde n'était pas exécutée (`frame_count % 3`),
  remettant `person_since` à zéro → rôdage jamais détecté. **Corrigé** (sentinelle
  `None` = « pas de détection cette frame »).

### Vulnérabilités (dans `gardien(2).html` d'origine)
- **Script tiers opaque** chargé depuis `claude.ai` (exécution arbitraire).
- **Clé d'API** saisie dans l'UI et stockée en `localStorage` ; appels directs
  navigateur → fournisseur, clé exposée.
- **XSS** : `addLine(...innerHTML...)` injecte la réponse du modèle en HTML.
- **Un seul appel LLM** décidait présence + menace + sirène ; escalade/sirène
  déclenchées par un `OUI:` du modèle ; bluff « police/chien/voisins prévenus ».
- Pas de CSP, pas de timeout, pas de limite de taille/fréquence, sirènes
  superposables, flash clignotant systématique.
- `emergency.py` : annonce « les secours et le propriétaire sont prévenus »
  **avant** tout envoi réel ; `[APPEL_POLICE:…]` posait `allow_call=True` sur un
  simple tag du LLM.

### Dépendances inutiles/contradictoires
- `requirements_v4.txt` installait **`opencv-python` ET `opencv-contrib-python`**
  (conflit de symboles). **Corrigé** : contrib seul + split core/optionnel/realtime.

### Annoncé mais incomplet
- « Vision réelle » et « temps réel » : dépendent d'Ollama/clé, non branchés au
  Gardien. Désormais structurés en fournisseurs (local par défaut).

---

## 2. Ce qui a été livré

### Nouveau module `server/guardian/` (séparation des responsabilités)
| Fichier | Rôle |
|---|---|
| `config.py` | Config typée via env (`GUARDIAN_*`), vue publique sans secret |
| `schemas.py` | **Validation stricte** de la perception (Pydantic + fallback pur) |
| `zones.py` | Zones configurables (porche/porte/chemin/ignore/privé/**masque public**) |
| `tracking.py` | **Suivi persistant** (id, bbox, first/last seen, dwell, trajectoire, aire lissée, zone, confiance, confirmations) ; `None` ≠ `[]` |
| `state_machine.py` | **FSM déterministe** IDLE→OBSERVING→ENGAGING→WARNING→ALERT→COOLDOWN |
| `policy.py` | Politique d'action + **politique de parole sûre** (claims interdits) |
| `store.py` | **SQLite** (events, decisions, devices, approvals, notifications, settings) WAL, rétention, export, wipe |
| `service.py` | Orchestration perception→suivi→politique→action ; rate-limit, taille image |
| `pairing.py` | Appairage téléphone/tablette (code temporaire, token révocable, scopes limités) |
| `api.py` | Blueprint Flask `/gardien` + `/api/guardian/*` |
| `providers/base.py` | Interfaces Vision/Speech/Realtime + parole **template** locale |
| `providers/ollama.py` | Vision + parole **100 % locales** (temp 0 pour la vision) |
| `providers/openai_realtime.py` | Vision OpenAI + **mint de jeton éphémère** (clé côté serveur) |
| `providers/gemini_live.py` | Vision Gemini + Live (**squelette explicite, non finalisé**) |

### Nouveaux modules serveur
- `server/permissions.py` — gestionnaire central READ_ONLY/REVERSIBLE/SENSITIVE/
  CRITICAL + **approbations** (jeton aléatoire, action+params exacts, expiration,
  usage unique, audit). Outil inconnu ⇒ **SENSITIVE** (fail-closed).
- `server/emergency_approval.py` — appel = demande serveur → confirmation →
  jeton usage unique → cooldown → journal. Cible par défaut = **propriétaire**.
- `server/wsgi.py` — entrée production (Gunicorn/Waitress), arrêt gracieux.

### Fichiers modifiés
- `server/jarvis_v4.py` :
  - `/` → **redirige `/app`** (fin du `DASHBOARD_HTML` géant servi).
  - **En-têtes de sécurité** globaux (`Content-Security-Policy`,
    `Permissions-Policy` caméra/micro, `X-Frame-Options`, `nosniff`…).
  - **Tags sensibles désactivés par défaut** (`[CMD]`,`[TUER]`,`[APPEL_POLICE]`,
    `[PC_POWER]`,`[ECRIRE_FICHIER]`,…) → `JARVIS_LEGACY_TAGS=1` pour réactiver.
  - Câblage du blueprint Gardien + services (store, providers, permissions,
    urgence, appairage).
  - Correctif du reset de suivi dans `_capture_loop` (sentinelle `None`).
- `server/security_mod/detector.py` :
  - `safe_person_id()` (anti-traversée) ; **FaceBank** : `person_id` sûr ≠ nom
    affiché ≠ dossier ; enrôlement multi-images ; **état « incertain »** ;
    `delete_identity`, `list_identities` ; `_person_dir` confiné.
  - `BehaviorAnalyzer.update()` gère `persons=None` (frame sans détection).
- `web/index.html` : onglet **Gardien** (lien `/gardien`).
- `web/gardien.html` : **réécriture complète et sécurisée** (voir §3).
- `requirements_v4.txt` : opencv unique + split ; ajout `pydantic`.

### Documentation & déploiement
`SECURITY.md`, `.env.example`, `INSTALL_LINUX.md`, `INSTALL_WINDOWS.md`,
`PAIRING_GUIDE.md`, `pyproject.toml`, `requirements-optional.txt`,
`requirements-realtime.txt`, `scripts/run_linux.sh`, `scripts/run_windows.ps1`,
`scripts/healthcheck.sh`.

---

## 3. `web/gardien.html` — corrections de sécurité
- ❌ Script `claude.ai` supprimé ; ❌ champ clé API supprimé ; **aucune clé** dans
  HTML/JS/localStorage/sessionStorage.
- Le navigateur ne parle qu'à **l'API JARVIS authentifiée** (cookie de session).
- **Anti-XSS** : journal construit via `textContent` + nœuds DOM ; toute réponse
  (phrase, état, métadonnée) traitée comme **non fiable**.
- `Content-Security-Policy` (meta + en-tête serveur), `Permissions-Policy`.
- `AbortController` (timeout), **limite de taille d'image**, **rate-limit client**,
  état **hors ligne** + **reconnexion** avec backoff borné.
- **Arrêt réel** caméra/micro/audio + **bouton de coupure immédiate**.
- Sirène : **un seul `AudioContext`**, nœuds fermés, anti-superposition,
  **durée max + cooldown**, bouton d'arrêt toujours visible, **flash off par
  défaut**, respect de `prefers-reduced-motion`. La sirène ne part **jamais**
  d'une phrase du LLM.

---

## 4. Choix d'architecture (brefs)
1. **Perception ≠ décision ≠ parole.** La vision ne renvoie qu'un JSON décrit ;
   la FSM+politique décident (déterministe) ; le LLM ne produit que la phrase,
   ensuite **nettoyée**. → pas de faux déclenchement piloté par le modèle.
2. **Fail-closed partout.** JSON invalide ⇒ `UNKNOWN` ⇒ aucune action. Outil
   inconnu ⇒ SENSITIVE. Sirène ⇒ autorisation explicite (manuel/approbation/
   critère critique). ALERT ⇒ fait critique déterministe, jamais « 5 images ».
3. **Local-first.** `GUARDIAN_CLOUD_VISION=0` par défaut : aucune image ne sort.
   Cloud = opt-in, clés strictement serveur, jeton éphémère pour le temps réel.
4. **Intégration, pas remplacement.** On réutilise `event_log`, `notifier`
   (Telegram), `emergency`, l'auth et le design existants. Refactor **progressif**
   (blueprint + services) au lieu d'une réécriture risquée du monolithe.
5. **Pure-python testable.** Le cœur Gardien (schemas/FSM/policy/permissions)
   n'a aucune dépendance lourde → testé rapidement et de façon déterministe.

---

## 4bis. Réutilisation open-source (design + détecteur)
- **Design de l'interface** : le langage visuel (palette cyan/zinc, rayons,
  ombres, typographies HUD) est adapté d'**OpenJarvis** (Stanford, Apache-2.0)
  et réinterprété en **CSS natif** dans `web/index.html` et `web/gardien.html`
  — aucun code React/Tauri, aucune police/CDN externe (CSP intacte).
- **Détecteur enfichable** (`server/security_mod/detectors.py`) : HOG par défaut
  (install minimale) + backend **ONNX/YOLOv8** optionnel (`GUARDIAN_DETECTOR=onnx`,
  `GUARDIAN_ONNX_MODEL`), à dégradation gracieuse — schéma inspiré du projet
  **thevickypedia/Jarvis** (MIT). Le décodage YOLO est testé indépendamment d'un
  modèle réel ; le chemin runtime ONNX reste optionnel (non testé en CI).
- Attribution : voir `CREDITS.md` et `NOTICE`.

## 4ter. Interface interactive (lot #1 : palette + cloche + SSE)
- **Gating des permissions dans l'agent** : `ToolRegistry` accepte désormais un
  `permission_manager`. Un outil SENSIBLE/CRITIQUE appelé sans jeton **crée une
  demande d'approbation** au lieu de s'exécuter (fail-closed) ; le comportement
  historique est conservé quand aucun gestionnaire n'est fourni (tests intacts).
- **Endpoints** : `GET /api/approvals`, `POST /api/approvals/confirm`,
  `POST /api/approvals/reject`. La confirmation exécute l'action EXACTE approuvée
  (jeton usage unique) via le registre d'outils.
- **UI (`web/index.html`)** : **cloche d'approbation** (badge + panneau,
  Confirmer/Refuser), **palette de commandes** (Ctrl/⌘+K, navigation clavier),
  **flux temps réel SSE** (`/api/stream`) qui rafraîchit la cloche et la timeline.
  Tout en vanilla JS, `textContent` (anti-XSS), sans dépendance ni CDN.

## 4quater. JARVIS OS — cœur animé + interfaces multiples + Docker
- **`web/os.html`** (route `/os`) : shell « Iron Man » avec un **cœur JARVIS
  animé original** (anneaux SVG rotatifs + réacteur + onde canvas) qui **s'anime
  quand JARVIS parle** (état lié à la synthèse vocale + évènements SSE).
- **Fenêtres de modules** déplaçables ouvrables à la demande (pas une seule
  interface) : Chat, Recherche Web, **Globe 3D** (canvas filaire original),
  Gardien, Système, Timeline, Approbations. Toutes branchées sur l'API réelle,
  `textContent` anti-XSS, CSP stricte, **aucun CDN**.
- **Micro** (dictée) et **bus SSE** : le cœur réagit aux évènements Gardien.
- **Docker** (auto-hébergement) : `Dockerfile` + `docker-compose.yml` +
  `.dockerignore`, Gunicorn, healthcheck, volumes de persistance (aucune donnée
  perso dans l'image). En conteneur headless : `opencv-python-headless`.
- ⚠️ Le projet `jarvis-OS` (AGPL-3.0) a servi d'**inspiration seulement** :
  aucune ligne copiée (voir `CREDITS.md`).

## 4quinquies. Carte géo auto-hébergée + OSINT d'infrastructure
- **Carte / Globe (module OS)** : globe **orthographique** avec les **pays réels**
  (GeoJSON Natural Earth, domaine public, simplifié et **vendu localement** dans
  `web/assets/world.geojson`). **Aucune tuile ni CDN externe** (offline, CSP
  intacte). Rotation auto + glisser, points géolocalisés OSINT.
- **OSINT d'INFRASTRUCTURE** (`server/osint.py`, endpoint `/api/osint/lookup`) :
  IP / domaine / hachage uniquement. Classification (privé/public/réservé),
  reverse DNS, résolution, WHOIS (port 43, sans clé), géoloc IP **optionnelle**
  (`OSINT_GEO_URL`, désactivée par défaut). Rate-limit + journalisation.
  ⚠️ **Jamais de ciblage de personnes** (pas de visage/nom/réseaux sociaux) —
  refus par conception. Une IP privée ne déclenche aucun appel externe.
- Route statique `/assets/<fichier>` (auto-hébergement du fond de carte).

## 5. Résultats de tests (réels)
Voir `TEST_RESULTS.md` (sortie exacte de `python -m compileall` et `pytest -q`).
**111 tests passent** (48 historiques + 63 nouveaux). Aucun test historique cassé.

---

## 6. Limitations restantes (honnêtes)
- **Refactor du monolithe (Étape 13)** : fait *partiellement* (blueprint, services,
  redirection, headers, tags gatés). L'app-factory complète et la découpe totale
  de `jarvis_v4.py` restent à faire — non entreprises pour ne pas casser l'existant.
- **OpenAI Realtime (Étape 8)** : le mint de jeton éphémère est implémenté mais
  **non testé avec une vraie clé** ; le WebRTC côté navigateur (VAD, barge-in,
  sélection micro/HP) n'est **pas** encore câblé dans `gardien.html` (audio OFF
  par défaut). Marqué comme tel.
- **Gemini Live** : **squelette** ; `mint_ephemeral_session` lève une erreur
  claire au lieu d'exposer une clé.
- **Suivi persistant serveur** : `tracking.py`/`zones.py` sont complets et testés
  comme composants ; leur branchement dans la boucle caméra OpenCV
  (`SecuritySystem`) reste à finaliser (le service Gardien navigateur, lui, agrège
  la présence temporellement). Détecteur ONNX : interface prévue, non fournie.
- **Appairage** : endpoints + gestion de tokens révocables livrés ; l'acceptation
  d'un **device-token non authentifié par session** dans `before_request` n'est
  pas activée (le `/gardien` utilise la session). Voir `PAIRING_GUIDE.md`.
- **SQLite (Étape 14)** : appliqué au **Gardien** ; la migration des JSON
  historiques (conversations/events globaux) n'est pas faite.
