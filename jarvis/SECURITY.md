# SECURITY.md — JARVIS v5.2

## Modèle de menace (résumé)
JARVIS tourne sur ton réseau local et pilote des actions physiques (lumières,
sirène, PC, appels). Les surfaces sensibles : le navigateur (XSS, clés), l'API
(auth, CSRF, SSRF), le LLM (sorties non fiables), et les actions physiques
(faux déclenchements).

## Principes
1. **Aucune clé d'API dans le navigateur.** OpenAI/Gemini/DeepSeek/Telegram/
   Twilio : uniquement en variables d'environnement **côté serveur**. Le client
   n'obtient au plus qu'un **jeton de session éphémère** (temps réel).
2. **Toute sortie de modèle est non fiable.** Vision validée par schéma strict ;
   phrases nettoyées ; jamais d'`innerHTML` sur du contenu modèle (→ `textContent`).
3. **Fail-closed.** JSON invalide ⇒ aucune action. Outil inconnu ⇒ SENSITIVE.
   Sirène/urgence ⇒ autorisation explicite. ALERT ⇒ fait critique déterministe.
4. **Séparation des privilèges.** Un appareil Gardien (téléphone/tablette) a des
   *scopes* limités (`guardian:*`) — **jamais** de contrôle PC ni urgence complète.

## Contrôles en place
- **Auth** : mot de passe (rate-limit anti-bruteforce, comparaison à temps
  constant) + jeton d'API distinct ; cookies `HttpOnly`, `SameSite=Lax`,
  `Secure` si HTTPS.
- **En-têtes** (pages HTML) : `Content-Security-Policy` (pas de script tiers),
  `Permissions-Policy` (caméra/micro = same-origin), `X-Frame-Options: DENY`,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy`.
- **Permissions des outils** : `permissions.py` — 4 niveaux + approbations à
  usage unique (jeton aléatoire, action+params exacts, expiration, audit).
- **Fallback par tags** : les actions **sensibles/critiques** (`[CMD]`, `[TUER]`,
  `[APPEL_POLICE]`, `[PC_POWER]`, écriture fichier…) sont **désactivées par
  défaut** (`JARVIS_LEGACY_TAGS=0`).
- **Urgence** : aucun appel sans demande serveur + confirmation + jeton unique +
  cooldown + journal. Cible par défaut = **propriétaire**, pas les secours.
  Aucune phrase « secours prévenus » n'est prononcée avant confirmation réelle.
- **FaceBank** : noms sanitisés (`safe_person_id`), dossiers confinés
  (anti-traversée), enrôlement multi-images, état « incertain ». La reconnaissance
  faciale **n'est jamais** la seule condition d'alerte.
- **Confidentialité** : `GUARDIAN_CLOUD_VISION=0` (aucune image ne quitte le LAN),
  audio OFF par défaut, rétention configurable + purge, export/wipe. Aucune donnée
  personnelle ni image réelle dans Git (`.gitignore`).

## Bonnes pratiques de déploiement
- Serveur WSGI (**Gunicorn**/**Waitress**), **pas** `app.run()` en prod.
- HTTPS via reverse-proxy (nginx/Caddy) ou certificats.
- `JARVIS_AUTH=1`, mot de passe fort, ne pas exposer sur Internet sans proxy.
- Sauvegarder `.env` hors du dépôt.

## Signaler une vulnérabilité
Ouvre une issue privée / contacte le mainteneur. Ne publie pas de PoC exploitant
une instance tierce sans consentement.
