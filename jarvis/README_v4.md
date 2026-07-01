# JARVIS v5.2 « MÉGA » 🤖

> **Nouveautés v5.2** : 🖥️ **App web unifiée** (`/app`) — une seule interface
> façon ChatGPT avec barre latérale et onglets **Chat · Maison · Sécurité ·
> Système · Timeline**. Le **chat passe par l'agent** : tu écris « allume le
> salon en bleu » ou « mode cinéma » et il **pilote vraiment la maison** (+ web,
> vision). 💬 **Conversations persistantes côté serveur** (multi-conversations,
> partagées entre appareils) via `/api/conversations`. Ouvre **http://localhost:8004/app**
> (même origine = contrôle live, session déjà authentifiée).

---

# JARVIS v5.1 « MÉGA » 🤖

> **Nouveautés v5.1** : 🖥️ **Contrôle PC avancé** (capture d'écran, touches média,
> alimentation lock/sleep/shutdown avec confirmation, kill process, presse-papier,
> luminosité, fenêtre active) — exposé en boutons, tags et outils d'agent.
> 👁️ **Vision réelle** de la caméra/écran via un modèle multimodal (Ollama llava).
> 🧪 **Suite de tests pytest** (44 tests, tous verts) + **CI GitHub Actions**.
>
> Tester : `pip install pytest && pytest -q` (depuis le dossier du projet).

---

# JARVIS v5.0 « MÉGA » 🤖

> **Nouveautés v5 (équipe d'agents)** : JARVIS devient un **vrai agent** —
> boucle multi-tours + **function-calling** (il voit le résultat de ses actions,
> enchaîne, résume), **mémoire long terme RAG**, **timeline** de tous les
> évènements, **bus temps réel SSE** (dashboard poussé), **moteur
> d'automatisations** (proactif : heure × présence × météo → scène) et
> **briefing matinal**. Plus un gros **durcissement sécurité** : injection
> `[CMD]` corrigée, anti-SSRF, fichiers confinés (`JARVIS_FILES_ROOT`), auth à
> temps constant + jeton API distinct + rate-limit, cookies sécurisés, bind
> **127.0.0.1** par défaut. Détails : `RAPPORT_v5_MEGA.md`.
>
> Variables : `JARVIS_AGENT=0` (désactiver l'agent), `JARVIS_HOST=0.0.0.0`
> (exposer au LAN), `JARVIS_FILES_ROOT`, `JARVIS_CITY`, `JARVIS_PROACTIVE=0`.

---

# JARVIS v4.0 — Maison connectée 🏠

JARVIS, ton assistant IA sarcastique, contrôle désormais **ta maison Apple** :
enceintes **HomePod**, **Apple TV**, **lumières** connectées, et une **détection
d'intrus** bien plus sérieuse que la v3.

> Nouveautés v4 : 🍎 HomePod (annonces vocales + AirPlay) · 📺 Apple TV
> (télécommande + lancement d'apps) · 💡 Lumières (Philips Hue ou mode simulé) ·
> 🛡️ Anti-intrusion (personnes + visages connus/inconnus + réponse automatique) ·
> 🎬 Scènes/routines · le tout en langage naturel.

---

## 🚀 Installation

```bash
# 1. Dépendances
pip install -r requirements_v4.txt
# Pour la reconnaissance de visages connus/inconnus :
pip uninstall opencv-python && pip install opencv-contrib-python

# 2. Backend IA (au choix)
export DEEPSEEK_API_KEY=sk-...        # cloud, quasi-gratuit
# ou : ollama serve + export JARVIS_BACKEND=ollama   (100% local)

# 3. Lancer
python server/jarvis_v4.py
# → http://localhost:8004
```

JARVIS démarre **même sans matériel Apple ni lumières** : les lumières passent
en *mode simulé* et les actions Apple renvoient un message clair tant que `pyatv`
n'est pas installé/appairé. Tu peux donc tester le dashboard tout de suite.

---

## 🍎 Connecter les HomePod & l'Apple TV

```bash
pip install pyatv gtts
atvremote scan                                          # trouve tes appareils
atvremote --id <ID> --protocol airplay pair             # HomePod
atvremote --id <ID> --protocol companion pair           # Apple TV
```

Copie `config/apple_credentials.json.example` → `config/apple_credentials.json`
et colle les credentials (la clé = le **nom exact** de l'appareil).

Variables utiles :
```bash
export JARVIS_HOMEPOD="Salon HomePod"   # enceinte par défaut
export JARVIS_APPLETV="Apple TV"        # Apple TV par défaut
export JARVIS_SIREN_URL="http://.../alarme.mp3"   # sirène diffusée si intrusion
```

## 💡 Connecter les lumières (Philips Hue)

```bash
# 1. IP du pont : https://discovery.meethue.com
# 2. Appuie sur le bouton du pont, puis :
curl -X POST http://<IP_PONT>/api -d '{"devicetype":"jarvis#home"}'
# 3. Récupère le "username" renvoyé :
export HUE_BRIDGE_IP=192.168.1.x
export HUE_USERNAME=xxxxxxxx
```
Sans pont configuré → **mode simulé** (5 lampes virtuelles : salon, chambre,
cuisine, bureau, entrée) pour tester scènes et anti-intrusion.

---

## 🔐 Sécurité d'accès — auth + HTTPS (NOUVEAU)

Le dashboard n'est plus ouvert à tous : **page de connexion** obligatoire.
```bash
export JARVIS_PASSWORD="ton-mot-de-passe"   # sinon généré et affiché au démarrage
export JARVIS_AUTH=0                          # (déconseillé) désactiver l'auth
# HTTPS :
export JARVIS_HTTPS=adhoc                     # certif auto-signé (pip install cryptography)
# ou en prod :
export JARVIS_SSL_CERT=/chemin/cert.pem  JARVIS_SSL_KEY=/chemin/key.pem
export JARVIS_CORS="https://mondomaine"       # origines cross-site autorisées (sinon aucune)
```
- Cookie de session signé + **jeton d'API** (`X-JARVIS-Token: <mot de passe>`) pour
  les scripts/curl. CORS wildcard supprimé. Bouton **déconnexion** dans l'entête.

## 👤 « Tu connais cette personne ? » — question interactive (NOUVEAU)

Dès qu'une personne **suspecte** est détectée (personne / visage inconnu /
rôdage…), JARVIS **demande systématiquement** si c'est un inconnu :
- **Sur le dashboard** : bandeau jaune avec photo du contexte + boutons
  **✅ Connu** (avec champ nom) / **🚨 Inconnu**.
- **Sur Telegram** : message photo avec 2 boutons ; les réponses reviennent à
  JARVIS (long-polling).

Réponse **Connu** → JARVIS **enrôle le visage** (devient « de confiance ») et se
détend (et apprend que ce n'était pas une menace). Réponse **Inconnu** → il
**escalade** (réponse anti-intrusion + alerte l'hôte / urgence si armé).

## 😴 Couper / réveiller / éteindre JARVIS (NOUVEAU)

- **Veille** : bouton ⏻ dans l'entête, ou dis « coupe-toi » / « stop » / « au
  dodo » (`[VEILLE]`). En veille, JARVIS ne répond plus… jusqu'à « **réveille-toi** »
  ou « **Ok Jarvis** » (la veille vocale le rallume).
- **Extinction complète** : bouton rouge ⏻ → arrête caméra + serveur
  (`/api/system/shutdown`).

## 📞 Appeler l'hôte de la maison (NOUVEAU)

Bouton **« Appeler l'hôte »** (barre caméra) ou commande à JARVIS
(`[APPEL_HOTE:message]`) → appel vocal au propriétaire via Twilio (repli Telegram/
voix si la téléphonie n'est pas configurée). Déclenché aussi automatiquement quand
un **inconnu est confirmé** alors que l'alarme n'est pas armée.

## 👂 Veille vocale — mot de réveil & double clap (NOUVEAU)

Active la **veille vocale** (bouton oreille dans le chat). JARVIS écoute en
continu et se réveille quand tu dis :
- « **Ok Jarvis** » / « Hey Jarvis »
- « **Jarvis réveille-toi** »
- « **Jarvis papa est là** »
- ou **2 applaudissements** rapides 👏👏

Au réveil : carillon + orbe qui passe au vert, puis il capte ta commande (si tu
enchaînes « Ok Jarvis, mode cinéma », il l'exécute directement). 100 % navigateur
(Web Speech + Web Audio), aucune installation. *Chrome/Edge requis pour la voix.*

## 🎨 Nouvelle interface (design system UI/UX Pro Max)

Refonte complète du dashboard avec le skill **UI/UX Pro Max** :
- Style **Dark OLED** + glassmorphism, dégradé profond, **glow** discret, blobs
  d'ambiance animés.
- Police **Inter** (UI) + **JetBrains Mono** (données/horloge, chiffres tabulaires).
- **Icônes SVG** (fini les emojis comme icônes de contrôle), états *hover/press/
  focus-visible*, transitions 150–300ms, `prefers-reduced-motion` respecté.
- **Responsive** (1 colonne mobile → 2 colonnes ≥920px), squelettes de chargement,
  toasts, modale de confirmation, contrastes WCAG.

## 🕵️ Détection comportementale — inspirée Veesion (NOUVEAU)

La menace ne vient plus seulement de *qui* est là, mais de *comment il se
comporte*. Nouveau `BehaviorAnalyzer` :
- **Rôdage / loitering** : personne présente trop longtemps.
- **Approche rapide** : silhouette qui grossit vite.
- **Mouvements erratiques** : forte variance de mouvement.
- **Présence nocturne** : personne aux heures sensibles.

Ces comportements augmentent le **score de menace** (bas → moyen → élevé →
**extrême**). En menace **extrême** + alarme armée, JARVIS déclenche
automatiquement le **protocole d'urgence**.

## 🆘 Protocole d'urgence / appel (NOUVEAU)

Bouton **Urgence** (avec confirmation) ou commande à JARVIS. Escalade graduée :
1. Annonce vocale dissuasive (HomePod)
2. Notification + **photo** sur ton téléphone (Telegram)
3. **SMS** au contact d'urgence (Twilio)
4. **Appel vocal** au contact d'urgence (Twilio, message parlé)

```bash
export TWILIO_ACCOUNT_SID=...   TWILIO_AUTH_TOKEN=...   TWILIO_FROM=+1...
export EMERGENCY_CONTACT=+33...      # prévenu en priorité
export EMERGENCY_NUMBER=+33...       # appelé en dernier recours
export EMERGENCY_AUTO_DIAL=1         # autorise l'appel auto (défaut: NON)
```
> ⚠️ **Légal** : un appel abusif aux secours est un délit. Par défaut JARVIS
> **n'appelle pas** automatiquement et vise un **contact de confiance**, pas le
> 17/112. À configurer en connaissance de cause.

## 🧠 Apprentissage long terme (NOUVEAU)

JARVIS s'améliore avec le temps (`memory/profile.json`) :
- Mémorise commandes/scènes/pièces les plus utilisées + ton enceinte favorite,
  et **réinjecte ce profil dans son prompt** → réponses personnalisées.
- `[RETIENS:fait]` pour lui apprendre une info durable.
- **Détection auto-adaptative** : marque une alerte « fausse » → il **baisse tout
  seul sa sensibilité** (moins de faux positifs au fil du temps). Panneau
  *Apprentissage* + endpoint `/api/security/feedback`.

## 🎙️ Voix bidirectionnelle

Dans le dashboard, deux boutons dans la barre de chat :
- **🎙️ Micro** : parle, JARVIS transcrit et exécute (reconnaissance vocale du
  navigateur — Chrome/Edge, **aucune installation**).
- **🔇 → 🔊 Lecture vocale** : active la lecture à voix haute des réponses
  (synthèse vocale française du navigateur).

Combiné aux annonces HomePod, tu peux donc parler à JARVIS *et* l'entendre te
répondre — mains libres.

## 🔎 Recherche web (NOUVEAU)

JARVIS cherche sur le web (via DuckDuckGo, **sans clé API**) dès qu'une question
porte sur l'actualité ou un fait qu'il ne connaît pas, puis **résume** avec sa
personnalité.
- *« cherche les dernières news sur l'IA »* → `[RECHERCHE_WEB:news IA]`
- *« résume-moi cette page : <url> »* → `[LIRE_WEB:url]`
- Bouton 🔎 RECHERCHE WEB dans les Super Pouvoirs.

## 📲 Notifications photo à distance (NOUVEAU)

Reçois la **photo de l'intrus sur ton téléphone**, où que tu sois, via Telegram.
```bash
# 1. @BotFather → /newbot → récupère le TOKEN
# 2. https://api.telegram.org/bot<TOKEN>/getUpdates → ton chat id
export TELEGRAM_BOT_TOKEN=123456:ABC...
export TELEGRAM_CHAT_ID=987654321
```
Quand l'alarme est **armée** et qu'un intrus est détecté, JARVIS envoie
automatiquement le snapshot annoté sur Telegram (en plus de la notif bureau, de
l'annonce HomePod et du flash des lumières). JARVIS peut aussi t'envoyer un
message à la demande : `[NOTIF_TEL:message]`. Teste avec `POST /api/notify/test`.

## 🗣️ Parler à JARVIS (langage naturel)

| Tu dis... | JARVIS fait... |
|-----------|----------------|
| « Allume le salon en bleu » | `[LUMIERE_COULEUR:salon\|bleu]` |
| « Éteins tout » | `[LUMIERES_OFF]` |
| « Mets le mode cinéma » | `[SCENE:cinéma]` |
| « Dis bonjour sur le HomePod » | `[HOMEPOD_DIRE:Bonjour]` |
| « Monte le HomePod à 60 » | `[HOMEPOD_VOLUME:60]` |
| « Mets Netflix sur la télé » | `[APPLETV_APP:netflix]` |
| « Pause la télé » | `[APPLETV:pause]` |
| « Arme l'alarme » | `[ARMER]` |
| « Je rentre » | `[SCENE:retour]` |

## 🎬 Scènes prêtes à l'emploi
`cinéma` · `soirée` · `réveil` · `bonne nuit` · `absence` · `retour`
(combinent lumières + Apple TV + annonce HomePod + armement). Modifiables dans
`CONFIG["scenes"]`.

---

## 🛡️ Détection d'intrus (v4)

| | v3 | **v4** |
|--|----|--------|
| Détection | mouvement de pixels | **mouvement + silhouette humaine (HOG) + visages** |
| Visages | « visage détecté » | **connus vs inconnus** (reco faciale) |
| Faux positifs | élevés | **confirmation multi-frames + score de menace** |
| Réaction | log only | **notif + annonce HomePod + flash lumières rouges + sirène** |
| Modes | toujours actif | **ARMÉ / DÉSARMÉ** (réponse auto seulement si armé) |

**Enregistrer un visage de confiance** : place-toi devant la caméra →
bouton *« 👤 Enregistrer visage »* → entre ton nom. Tout visage non reconnu
ensuite = **intrus** (menace élevée).

Config dans `CONFIG["security"]` : `person_detection`, `confirm_frames`,
`auto_response`, `default_armed`, `siren_url`, `alert_cooldown`.

---

## 🧰 Les autres pouvoirs (hérités v3, toujours là)
PC info, processus, disques, réseau, météo, fichiers, commandes système (liste
blanche), mot de passe, calcul, rappels, notifications, blagues, citations,
ouverture d'apps/URL, analyse caméra par l'IA. Voir le panneau *Super Pouvoirs*.

---

## 🔌 Endpoints API ajoutés
`/api/home/lights` · `/api/home/light` · `/api/home/scene` · `/api/home/scenes`
`/api/apple/devices` · `/api/apple/say` · `/api/apple/appletv/<cmd>`
`/api/security/arm` · `/api/security/enroll` · `/api/security/alerts` (+ stats)
`/api/web/search?q=` · `/api/web/read?url=` · `/api/notify/test`
`/api/emergency/police` · `/api/emergency/call-owner` · `/api/security/feedback`
`/api/security/pending` · `/api/security/identify` · `/api/learning/profile`
`/login` · `/logout` · `/api/system/standby` · `/api/system/shutdown`
`/api/stream` (SSE) · `/api/timeline` · `/api/automations` · `/api/proactive/briefing`
`/api/pc/screenshot` · `/api/pc/media/<action>` · `/api/pc/power` · `/api/pc/kill`
`/api/pc/brightness` · `/api/pc/lock` · `/api/pc/clipboard` · `/api/vision/analyze`
`/app` (app web unifiée) · `/api/conversations` (GET/POST) · `/api/conversations/<id>` (GET/DELETE)
