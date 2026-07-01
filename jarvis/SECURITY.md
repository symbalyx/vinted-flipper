# SECURITY.md — JARVIS v5.6

## Modèle de menace

JARVIS reçoit du contenu non fiable provenant du navigateur, des caméras, des
transcriptions, des fournisseurs IA et d’appareils du réseau local. Il peut aussi
piloter des actions sensibles : fichiers, applications, PC, caméra, sirène,
notifications et appels. Une sortie de modèle n’est donc jamais une autorisation.

## Garanties principales

1. **Clés côté serveur uniquement.** Aucune clé OpenAI, Gemini, DeepSeek,
   Telegram ou Twilio n’est servie au navigateur. Le jeton JARVIS saisi dans le
   tableau de bord reste uniquement en mémoire vive et disparaît au rechargement.
2. **Rendu non interprété.** Les réponses IA, transcriptions, noms, événements et
   métadonnées sont insérés avec `textContent` et des nœuds DOM explicites.
3. **Fail-closed.** JSON vision invalide, fournisseur indisponible, approbation
   expirée ou action inconnue : aucune action physique ou sensible.
4. **Séparation perception/décision/parole.** Le modèle de vision décrit ; la
   machine d’état et la politique déterministe décident ; le modèle de langage
   ne peut pas déclencher directement sirène, désarmement ou appel.
5. **Approbations applicatives.** Les actions SENSITIVE et CRITICAL utilisent un
   identifiant aléatoire, les paramètres exacts, une expiration, une validation
   utilisateur, un usage unique et un journal d’audit.

## Protections HTTP et navigateur

- authentification par session et/ou `X-JARVIS-Token` ;
- cookies `HttpOnly`, `SameSite=Lax`, `Secure` sous HTTPS ;
- rate-limit de connexion et des routes Gardien ;
- limite globale `JARVIS_MAX_REQUEST_BYTES` ;
- Content-Security-Policy, `object-src 'none'`, `frame-ancestors 'none'` ;
- Permissions-Policy limitée à la caméra et au microphone de même origine ;
- `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, Referrer-Policy ;
- timeouts réseau côté client ;
- aucune police, script ou bibliothèque distante dans les interfaces servies.

## Anciennes balises LLM

`JARVIS_LEGACY_TAGS=0` désactive toutes les balises historiques telles que
`[CMD:...]`, `[TUER:...]`, `[APPEL_POLICE:...]`, `[PC_POWER:...]` ou écriture de
fichier. Le mode compatibilité ne réactive pas les actions sensibles ou
critiques. Les outils modernes passent par le function calling validé et le
gestionnaire de permissions.

## Gardien et actions physiques

- une succession d’images positives ne suffit jamais à déclencher la sirène ;
- une personne immobile n’est pas automatiquement classée dangereuse ;
- un résultat `UNKNOWN` reste en observation et ne produit aucune action ;
- l’escalade automatique est désactivée par défaut ;
- le désarmement API exige `confirm=true` ;
- un appel nécessite demande, affichage de la cible, confirmation, jeton unique,
  cooldown et journalisation ;
- la reconnaissance faciale n’est jamais le seul motif d’alerte ou d’annulation.

## Photo → globe et confidentialité

- l’image est validée puis traitée en mémoire, sans sauvegarde par le module ;
- `GUARDIAN_CLOUD_VISION=0` garantit l’utilisation du fournisseur local configuré ;
- JPEG/PNG/WebP uniquement, taille et nombre de pixels bornés ;
- GPS EXIF prioritaire, mais présenté comme métadonnée potentiellement modifiable ;
- toute inférence visuelle est marquée **estimation non exacte** avec confiance,
  précision et incertitudes ;
- aucune identification d’une personne ni recherche ciblée d’une résidence privée
  n’est demandée au fournisseur vision.


## Agency, n8n et e-mail

- une tranche de mission est bornée à 7 jours, 40 étapes et 8 sous-agents ; en mode durable, le superviseur enchaîne les tranches jusqu’au contrôle final ;
- les sous-agents n'ont pas de shell libre et utilisent uniquement le registre d'outils ;
- les écritures de fichiers restent confinées à `JARVIS_FILES_ROOT` ;
- les workflows n8n sont validés, créés inactifs et leurs identifiants sont filtrés ;
- `Execute Command`, Code/Function, SSH, FTP et accès fichiers locaux n8n sont refusés par défaut ;
- l'envoi SMTP, l'activation n8n et les actions critiques exigent une approbation liée aux paramètres exacts ;
- un refus d'approbation fait échouer l'étape au lieu d'être compté comme une réussite ;
- après redémarrage, une approbation volatile perdue est redemandée ;
- corps d'e-mail, workflow JSON, contenu de fichiers et presse-papier sont masqués dans les journaux.

## Voix locale

- les clips sont bornés en taille et en durée côté navigateur ;
- la capture demande annulation d'écho, réduction de bruit et gain automatique ;
- le fichier temporaire de transcription est supprimé après traitement ;
- `faster-whisper` est chargé côté serveur et aucune clé cloud n'est envoyée au navigateur ;
- la synthèse en cours est interrompue dès que l'utilisateur reprend la parole ;
- une transcription reste une entrée non fiable et ne contourne jamais les permissions d'outil.

## Déploiement recommandé

- conserver `JARVIS_AUTH=1` et choisir un mot de passe long ;
- ne jamais commiter `.env` ;
- utiliser Waitress sur Windows ou Gunicorn sur Linux ;
- placer JARVIS derrière HTTPS/reverse proxy avant tout accès hors machine ;
- ne pas exposer directement le port Flask sur Internet ;
- garder audio, cloud vision et escalade automatique désactivés tant qu’ils ne
  sont pas explicitement nécessaires et testés.

## Limites connues

La CSP conserve encore du code inline historique. Le backend principal reste
volumineux. Les intégrations cloud dépendent de fournisseurs externes et doivent
être testées avec les comptes réels avant usage de production.

## OSINT autorisé et anti-doxxing

La route de géolocalisation exige une attestation explicite et une finalité
parmi une liste fermée. Le serveur refuse les types de cible personnels et
analyse aussi le texte de la demande afin de bloquer les intentions de
pistage, d'identification ou de recherche d'adresse privée. Ces contrôles
s'appliquent à `/api/guardian/geolocate` et aux photos jointes à `/api/chat`.

## Durable Agency v5.6

- Les missions actives utilisent un bail SQLite renouvelé par heartbeat. Un
  second worker ne doit pas exécuter la même mission en parallèle.
- Les étapes persistantes utilisent des retries et checkpoints. Une erreur ne
  doit jamais être convertie en succès pour « faire avancer » le plan.
- Les actions externes réussies créent un reçu d’idempotence lié à la mission,
  l’étape, l’outil et les paramètres exacts.
- Une limite de tours d’un sous-agent est une erreur retentable, pas un livrable.
- Une mission n’est `completed` qu’après le contrôle de définition de fini.
- Les bases Agency et Prospection peuvent être vérifiées et copiées avec des
  sauvegardes SQLite cohérentes et une rétention bornée.
- Les actions sensibles et critiques restent soumises aux approbations, même en
  mode `continue_until_done`.

## Prospection

- L’URL de source professionnelle publique est obligatoire.
- Aucune adresse privée n’est stockée par le schéma du CRM.
- Aucun envoi de masse automatique n’est exposé.
- Chaque envoi de brouillon est `CRITICAL` et approuvé individuellement.
- Les contacts et domaines supprimés sont refusés avant l’envoi.
- Les limites quotidienne, par domaine et d’intervalle restent actives même
  après approbation.
- Le contenu des brouillons, e-mails et workflows est masqué dans les logs.
