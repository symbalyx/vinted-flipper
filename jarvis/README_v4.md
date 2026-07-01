# JARVIS v5.6 — Durable Agency, prospection et voix locale

JARVIS v5.6 réunit dans une application locale :

- chat IA Ollama ou DeepSeek avec function calling ;
- contrôle PC, maison connectée, Gardien vidéo et notifications ;
- localisation prudente de photos autorisées ;
- missions persistantes avec plusieurs sous-agents ;
- reprise automatique après crash, retries, heartbeat et checkpoints SQLite ;
- contrôle final de la « définition de fini » avant de déclarer une mission terminée ;
- mémoire inter-missions durable et reçus d’idempotence pour les actions externes ;
- vérification et sauvegardes SQLite cohérentes de la mémoire Agency et du CRM ;
- CRM de prospection avec sources publiques, qualification, brouillons et liste d’exclusion ;
- création sécurisée de workflows n8n ;
- envoi d’e-mails avec approbation humaine obligatoire ;
- reconnaissance vocale locale avec `faster-whisper`.

## Interfaces

- `/app` : chat et centre de contrôle ;
- `/agency` : missions durables et sous-agents ;
- `/prospection` : CRM, scoring et brouillons ;
- `/gardien` : caméra et sonnette ;
- `/os` : HUD JARVIS OS ;
- `/os#photo` : Photo → globe.

## Agency durable

Une mission suit le cycle :

```text
cadrage
→ plan
→ sous-agents parallèles
→ audit
→ vérification
→ contrôle de définition de fini
→ réparation si nécessaire
→ rapport final validé
```

La mission et chaque étape possèdent dans SQLite :

- état ;
- compteur d’essais ;
- backoff et prochaine date de reprise ;
- heartbeat ;
- checkpoint ;
- dépendances ;
- résultat et preuves ;
- cycles de réparation ;
- historique des événements.

`max_minutes` représente désormais une **tranche de calcul**. Lorsque
`continue_until_done=true`, la mission passe brièvement à `paused`, puis le
superviseur démarre une nouvelle tranche. Elle ne passe pas à `completed` tant
que le validateur final ne confirme pas les critères fournis.

Les statuts importants sont :

- `running` : travail actif ;
- `retry_wait` : nouvel essai programmé ;
- `waiting_approval` : action externe bloquée jusqu’à validation ;
- `paused` : fin d’une tranche, reprise automatique ;
- `blocked` : informations ou validation humaine nécessaires ;
- `completed` : définition de fini validée ;
- `cancelled` : annulation explicite par l’utilisateur.

### Reprise après redémarrage

Au redémarrage, JARVIS reprend automatiquement les missions `interrupted`,
`retry_wait` et `paused`. Un bail SQLite empêche deux workers ou deux processus
WSGI d’exécuter la même mission simultanément.

Une action externe réussie crée un reçu d’idempotence lié à :

```text
mission + étape + outil + paramètres exacts
```

Si la même étape est rejouée après un crash, JARVIS réutilise le résultat au lieu
de renvoyer le même e-mail, rouvrir la même application ou recréer le même
workflow.

### Mémoire dans le temps

Les missions terminées produisent une mémoire inter-missions locale. Elle
conserve surtout les décisions, méthodes, audits, vérifications et leçons. Les
coordonnées e-mail et téléphoniques sont masquées avant cette synthèse ; les
fiches détaillées restent uniquement dans le CRM de prospection.

## Prospection

Le module `/prospection` permet :

- de lancer une campagne durable par secteur, région et nombre de prospects ;
- d’enregistrer une entreprise avec son URL source publique ;
- de dédupliquer les prospects ;
- de calculer un score et d’expliquer ce score ;
- de conserver région, site, e-mail professionnel public et constats ;
- de préparer un brouillon personnalisé ;
- d’ajouter une URL de démonstration uniquement lorsqu’elle existe réellement ;
- de bloquer définitivement un contact ou un domaine ;
- de suivre les contacts et les réponses ;
- de limiter la fréquence d’envoi.

Le système ne possède aucun champ d’adresse privée et ne doit pas collecter de
données derrière une connexion. Il ne réalise aucun envoi de masse automatique.
Chaque envoi de brouillon est une action `CRITICAL` et demande une approbation
individuelle dans JARVIS.

Une mission de prospection peut être formulée ainsi :

> Trouve 20 artisans de Bordeaux à partir de sources professionnelles publiques,
> déduplique-les, ajoute l’URL de preuve, note leur besoin probable, prépare cinq
> brouillons honnêtes, n’envoie rien et fournis un rapport de conformité.

## n8n

Configure `N8N_URL` et `N8N_API_KEY`. JARVIS utilise la Public API n8n et crée
les workflows inactifs. L’activation demande une nouvelle approbation. Les
nœuds `Execute Command`, `Code`, SSH et accès fichiers locaux sont refusés par
défaut.

## E-mail

Configure les variables `SMTP_*`. Les outils de prévisualisation n’envoient
rien. `email_envoyer` et `prospection_envoyer_brouillon` sont classés
`CRITICAL`.

## Voix locale

Installe :

```bash
pip install -r requirements-voice.txt
```

Réglage CPU recommandé :

```dotenv
VOICE_STT_MODEL=base
VOICE_STT_DEVICE=cpu
VOICE_STT_COMPUTE_TYPE=int8
VOICE_BEAM_SIZE=1
VOICE_VAD_FILTER=1
```

Le navigateur utilise annulation d’écho, réduction de bruit, contrôle du gain,
détection de fin de parole et interruption de la synthèse quand l’utilisateur
reparle. Utilise `POST /api/voice/warmup` après le démarrage pour réduire la
latence de la première transcription.

## Installation rapide

```bash
python -m venv .venv
# Windows : .\.venv\Scripts\Activate.ps1
# Linux/macOS : source .venv/bin/activate
pip install -r requirements_v4.txt
pip install -r requirements-optional.txt
pip install -r requirements-voice.txt
```

Copie `.env.example` vers `.env`, configure les valeurs, puis lance
`scripts/run_windows.ps1` ou `scripts/run_linux.sh`.

## Limites honnêtes

- JARVIS ne peut pas continuer lorsque l’ordinateur et le serveur sont éteints ;
  il reprend dès le redémarrage.
- Une approbation humaine, un mot de passe manquant, une API indisponible ou une
  information impossible à obtenir peut placer la mission en attente ou en
  backoff, jamais en faux succès.
- « Continuer jusqu’à la fin » ne signifie pas contourner les permissions,
  envoyer du spam ou consommer des ressources sans limite.
- Pour une haute disponibilité réelle, utilise un service Windows/systemd,
  sauvegarde les volumes `data/`, puis envisage Redis/RQ ou Celery.

Voir `DURABLE_AGENCY_GUIDE.md`, `PROSPECTING_GUIDE.md`, `AGENCY_GUIDE.md`,
`VOICE_GUIDE.md`, `SECURITY.md` et `CHANGELOG_V5.6.md`.
