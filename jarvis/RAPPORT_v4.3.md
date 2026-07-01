# 📋 Rapport détaillé — JARVIS itération 3 (UI + voix passive + Veesion + urgence + apprentissage)

**Date :** 27 juin 2026 · **Périmètre :** refonte UI (skill UI/UX Pro Max), mot
de réveil & double clap, sécurité inspirée Veesion, appel d'urgence,
auto-amélioration long terme. **Notation : volontairement sévère.**

---

## 1. Demande & taux de couverture

| # | Demande | État | Note |
|---|---------|------|------|
| 1 | Améliorer l'UI du dashboard via le skill UI/UX Pro Max | ✅ Fait (refonte complète) | A |
| 2 | Réveil par « Ok Jarvis » / « Jarvis réveille-toi » / « Jarvis papa est là » | ✅ Fait | A− |
| 3 | Réveil par **double clap** | ✅ Fait (Web Audio) | B+ |
| 4 | Sécurité inspirée de **Veesion** (comportement) | ✅ Fait (approximation honnête) | B |
| 5 | **Appeler la police** en extrême urgence et à la demande | ⚠️ Fait avec garde-fous (contact d'urgence, pas le 17 direct) | B− |
| 6 | S'**améliorer sur le long terme** | ✅ Fait (profil + auto-tuning) | B+ |
| 7 | Rapport détaillé, sévère, comparatif | ✅ Ce document | — |

**Couverture fonctionnelle : 7/7 abordés**, mais plusieurs reposent sur des
**approximations** ou du **navigateur** (voir critique).

---

## 2. Ce qui a été livré, concrètement

### 2.1 UI (skill UI/UX Pro Max réellement utilisé)
J'ai exécuté `search.py --design-system` du skill et **appliqué ses
recommandations** :
- **Dark OLED + glassmorphism + glow**, dégradé profond (pas de `#000` pur),
  blobs d'ambiance animés.
- **Inter** (UI) + **JetBrains Mono** (données, chiffres tabulaires).
- **Icônes SVG** (suppression des emojis-icônes, exigence forte du skill),
  `focus-visible`, transitions 150–300ms, `prefers-reduced-motion`.
- **Responsive** 1→2 colonnes, squelettes de chargement, toasts, modale,
  `aria-label`/`aria-live`.
- Vérifié : le template **Jinja se rend** (37,9 Ko) sans collision de braces.

### 2.2 Veille vocale
- **Mot de réveil** : écoute continue (`SpeechRecognition`), phrases « ok jarvis »,
  « hey jarvis », « jarvis réveille-toi », « jarvis papa est là »… Si une commande
  suit le mot de réveil, elle est exécutée directement.
- **Double clap** : analyse d'amplitude temps réel (`AnalyserNode`), 2 pics < 700 ms.
- Carillon + orbe vert au réveil.

### 2.3 Sécurité « façon Veesion »
- Nouveau `BehaviorAnalyzer` : **rôdage**, **approche rapide**, **mouvements
  erratiques**, **présence nocturne** → bonus de score de menace.
- Nouveau palier **« extrême »** ; en extrême + armé → **escalade d'urgence auto**.
- Testé : rôdage nocturne + approche rapide = +5, qui combiné à personne+visage
  inconnu atteint « extrême ».

### 2.4 Urgence
- `EmergencyDispatcher` : escalade **annonce vocale → Telegram (+photo) → SMS →
  appel vocal** (Twilio via REST, sans SDK).
- **Garde-fous** : cooldown anti-rappel (120 s, **vérifié en test**),
  auto-appel **désactivé par défaut**, cible un **contact de confiance**.
- Tags `[APPEL_POLICE:raison]` + endpoint `/api/emergency/police`.

### 2.5 Apprentissage long terme
- `LearningEngine` (`memory/profile.json`) : compte commandes/scènes/pièces,
  enceinte favorite, **faits** (`[RETIENS:...]`), **réinjectés dans le prompt**.
- **Auto-tuning** de la détection : retour « fausse alerte » → la sensibilité
  baisse seule (testé : seuil 25 → 30 après 2 retours).

---

## 3. Tests réellement exécutés

| Test | Résultat |
|------|----------|
| `py_compile` de tous les modules | ✅ |
| Import complet du module (cv2 4.13 + flask installés) | ✅ |
| Parser sur `[SCENE] [LUMIERE] [LUMIERE_COULEUR] [RETIENS] [APPEL_POLICE] [RECHERCHE_WEB]` | ✅ |
| Endpoints `/`, `/api/home/scenes`, `/api/learning/profile`, `/api/status`, `/api/security/feedback`, `/api/security/arm`, `/api/emergency/police` | ✅ 200 |
| `BehaviorAnalyzer` (rôdage/nuit/approche) | ✅ scores corrects |
| Auto-tuning sensibilité après fausses alertes | ✅ 25→30 |
| Cooldown anti-rappel d'urgence | ✅ déclenché |
| Rendu Jinja du dashboard | ✅ |

**Non testé (limites environnement) :** caméra réelle (HOG/visages sur flux),
appairage HomePod/Apple TV, appel Twilio réel, recherche DuckDuckGo (proxy du bac
à sable = 403), reconnaissance/synthèse vocale navigateur (pas de navigateur ici).

---

## 4. NOTATION SÉVÈRE

### Notes par axe

| Axe | Note /20 | Justification sans complaisance |
|-----|:-------:|--------------------------------|
| **UI / design** | 16 | Design system bien appliqué, accessible, responsive. Mais une seule passe, pas de tests sur device réel ni audit Lighthouse ; densité d'info encore élevée. |
| **Veille vocale** | 13 | Fonctionne, mais **dépend du navigateur** (Chrome/Edge), `webkitSpeechRecognition` part dans le cloud Google (vie privée), pas de wake-word **on-device** ni serveur (Whisper/openWakeWord). Le double clap est heuristique (faux positifs probables). |
| **Sécurité Veesion** | 11 | Honnête mais **loin du vrai Veesion** (réseaux spatio-temporels sur gestes). Ici : heuristiques HOG + dwell + variance. Pas de modèle d'action, pas d'évaluation chiffrée (précision/rappel). |
| **Appel police** | 10 | Marche **uniquement si Twilio configuré**, et vise un contact perso — pas un vrai lien PSAP/secours. Risque légal réel d'appels abusifs. Garde-fous présents mais minimalistes (pas de double confirmation vocale, pas de code PIN). |
| **Apprentissage** | 12 | Vrai persistant et utile, mais **rudimentaire** : compteurs + ajustement linéaire. Pas de véritable modèle, pas de désapprentissage fin, pas de bornes statistiques. |
| **Qualité code / archi** | 14 | Modulaire, dégradation gracieuse, testé. Mais `jarvis_v4.py` ~1800 lignes (le HTML/JS géant devrait être un fichier statique), pas de tests automatisés versionnés, pas de typage. |
| **Sécurité applicative** | 7 | **Point noir** : dashboard sur `0.0.0.0:8004` **sans auth**, CORS `*`, exécution de commandes shell, contrôle de la maison et **déclencheur d'urgence accessibles à quiconque est sur le réseau**. Inacceptable en l'état pour de la prod. |
| **Vie privée** | 9 | Micro toujours ouvert en veille → STT cloud Google ; snapshots et profil stockés en clair. |

### 🎯 Note globale : **11,5 / 20**

> **Verdict :** démo riche et cohérente, bien au-dessus de la v3, qui *coche
> toutes les cases demandées*. Mais notée sévèrement, c'est un **prototype** :
> deux angles morts sérieux — **aucune authentification** et une fonction
> **« appel d'urgence » juridiquement sensible** — l'empêchent d'être « sérieux »
> au sens production. Le « Veesion » et l'« apprentissage » sont des
> approximations honnêtes, pas l'état de l'art.

---

## 5. Comparatif des versions

| Critère | v3 (origine) | v4 itér.1 (maison Apple) | v4 itér.2 (voix+web) | **v4 itér.3 (cette livraison)** |
|--------|:---:|:---:|:---:|:---:|
| Fichiers | 1 | 6 | 8 | **11** |
| Pouvoirs (tags) | 18 | 30 | 33 | **36** |
| HomePod / Apple TV | ❌ | ✅ | ✅ | ✅ |
| Lumières + scènes | ❌ | ✅ | ✅ | ✅ |
| Détection intrus | mouvement px | + personnes + visages | idem | **+ comportement (Veesion-like) + palier extrême** |
| Voix | ❌ | annonce HomePod | + STT/TTS navigateur | **+ veille « Ok Jarvis » + double clap** |
| Recherche web | ❌ | ❌ | ✅ | ✅ |
| Notif photo distante | ❌ | ❌ | ✅ Telegram | ✅ |
| Appel d'urgence | ❌ | ❌ | ❌ | **✅ (Twilio + garde-fous)** |
| Apprentissage | ❌ | ❌ | ❌ | **✅ profil + auto-tuning** |
| UI | Courier, 2 col fixes | idem | + boutons voix | **refonte design system, responsive, SVG, a11y** |
| Auth / sécurité appli | ❌ | ❌ | ❌ | ❌ *(toujours le trou)* |
| Note sévère /20 | ~6 | ~9 | ~10,5 | **11,5** |

**Progression nette** sur les fonctionnalités et l'UX ; **stagnation** sur la
sécurité applicative, qui devient le facteur limitant n°1.

---

## 6. Dette & priorités pour passer de 11,5 à 16+

1. **Authentification + HTTPS** sur le dashboard (token/login), retirer CORS `*`,
   protéger spécialement `/api/emergency/*` et `[CMD]`. ← *bloquant*
2. **Wake-word on-device** (openWakeWord/Porcupine) + STT local (Whisper) pour la
   vie privée et la fiabilité hors Chrome.
3. **Vrai modèle comportemental** (action recognition) + jeu de test annoté avec
   précision/rappel mesurés.
4. **Sortir le HTML/JS** dans des fichiers statiques (maintenabilité, tests).
5. **Tests automatisés** versionnés (pytest) + CI.
6. Urgence : double confirmation (code PIN/vocal), journal d'audit, et clarifier
   le cadre légal selon le pays.

---

## 6 bis. Itération 4 — Auth, question « connu/inconnu », coupure & appel hôte

Ajouts demandés après le rapport sévère :

- **🔐 Authentification + HTTPS** (le point noir n°1 est comblé) : page de login,
  cookie de session signé, **jeton d'API**, CORS wildcard supprimé, HTTPS via
  certs ou `adhoc`. → l'axe « sécurité applicative » passe de **7 à 14/20**.
- **👤 Question interactive** : à chaque personne suspecte, JARVIS demande
  « tu connais cette personne ? » sur le **dashboard** (bandeau + photo) **et
  Telegram** (boutons, réponses lues par long-polling). *Connu* → enrôle le
  visage ; *Inconnu* → escalade + prévient l'hôte.
- **😴 Couper JARVIS** : veille (chat suspendu, réveil par « Ok Jarvis ») +
  **extinction** complète (caméra + serveur).
- **📞 Appeler l'hôte** : bouton + `[APPEL_HOTE]`, et auto si inconnu confirmé.

**Tests itération 4 (exécutés) :** flux d'auth complet (302/401/login/token),
veille+réveil via chat, question d'identité (pending → identify inconnu → escalade
→ vidée), call-owner dégradé proprement, rendu des 2 templates Jinja. ✅

### Note révisée

| Axe | Avant | Après itér.4 |
|-----|:----:|:----:|
| Sécurité applicative | 7 | **14** |
| Sécurité Veesion (+ question identité humaine) | 11 | **13** |
| Contrôle (couper/éteindre) | — | **15** |
| **Note globale /20** | 11,5 | **≈ 13,5** |

> Reste à faire pour viser 16+ : wake-word on-device, vrai modèle comportemental
> chiffré, double confirmation PIN sur l'urgence, sortir le HTML en statique,
> tests pytest versionnés. Le trou critique (accès libre) est néanmoins **corrigé**.

## 7. Démarrage

```bash
pip install -r requirements_v4.txt
pip uninstall opencv-python && pip install opencv-contrib-python   # reco faciale
python server/jarvis_v4.py      # → http://localhost:8004 (Chrome/Edge pour la voix)
```
Config Apple / Hue / Telegram / Twilio : voir **README_v4.md**.
