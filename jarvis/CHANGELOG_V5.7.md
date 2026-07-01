# CHANGELOG v5.7

## Incrément 2 — baux d'étape, reaper, classification, backoff, réconciliation, CSRF, SSRF
Base : incrément 1 (213 tests) → **236 tests** (`compileall` OK, `pytest` 236 passed).
Aucun test historique cassé. Simulation de crash exécutée avec succès (voir §Validation).

### Migrations SQLite (additives, données v5.6/v5.7-i1 préservées)
- `mission_steps` : `worker_id`, `lease_token`, `lease_acquired_at`,
  `lease_expires_at`, `attempt_started_at`, `error_type` + index
  `idx_steps_lease(status,lease_expires_at)`.
- `mission_action_receipts` : `operation_id`, `lease_owner`, `provider_reference`,
  `request_fingerprint`, `response_fingerprint`, `reconciliation_status`.
- Nouvelle table `schema_version` (version = **57**), migrations versionnées.

### 1-3. Baux d'étape + heartbeat + reaper (`server/agency/store.py`, `orchestrator.py`)
- `claim_step(step_id, worker_id, lease_seconds)` : acquisition **atomique**
  (UPDATE conditionnel sur le statut) + pose d'un **lease_token aléatoire**. Deux
  workers ne peuvent jamais acquérir la même étape.
- `renew_step_lease(step_id, worker_id, lease_token, s)` : renouvellement réservé
  au bon worker+token sur une étape encore active.
- `record_step_result(step_id, worker_id, lease_token, …)` : un ancien worker dont
  le bail a expiré (étape reprise) **ne peut plus écrire** de résultat périmé.
- `reap_expired_steps(delay, event_cb)` : reprend les étapes LEASED/RUNNING dont le
  bail est expiré → `retry_wait`, `TRANSIENT_WORKER_LOST`, checkpoint conservé,
  bail invalidé, événement journalisé. **Idempotent** (compteur d'essais non doublé).
- Reaper + réconciliation câblés dans le superviseur (`_reaper_tick`), cadence
  `AGENCY_REAPER_INTERVAL_SECONDS`. Heartbeat renouvelle le bail d'étape.

### 4. Classification des erreurs (`server/agency/errors.py`)
- `TRANSIENT_*` (réseau, timeout, rate-limit, service indisponible, worker perdu),
  `PERMANENT_*` (validation, permission, config, non supporté), `HUMAN_REQUIRED`,
  `CANCELLED_BY_USER`. `classify_error(exc, text)`. Les temporaires se retentent ;
  les permanentes bloquent/échouent ; un refus d'approbation → HUMAN_REQUIRED
  (jamais retenté pour contourner l'utilisateur).

### 5. Backoff + jitter (`server/agency/backoff.py`)
- `next_delay = clamp(base·2^(n-1), base, max) ± jitter`, `Retry-After` respecté,
  persistable (`next_run_at`). Variables `AGENCY_RETRY_*`.

### 6. Réconciliation des reçus `in_flight`
- `reconcile_stuck_receipts(max_in_flight_seconds)` : un reçu `in_flight` trop
  ancien passe en `RECONCILIATION_REQUIRED` — **jamais** de réexécution automatique
  (anti double-effet). Un in_flight bloque tout rejeu aveugle (fail-closed).

### 7. CSRF (`server/jarvis_v4.py`)
- `before_request` : sur méthode mutative, `Origin` (sinon `Referer`) est vérifié
  **quand présent** → origine étrangère **refusée (403)** ; les clients sans Origin
  (scripts, `X-JARVIS-Token`) passent (politique distincte). `/logout` **POST-only**.

### 8. SSRF (`server/integrations/websearch.py`, `server/osint.py`)
- `validate_url_for_fetch` : http/https seulement, refus des identifiants intégrés,
  résolution DNS + **toutes** les IP doivent être publiques (privé/loopback/
  link-local/réservé/multicast/unspecified/`::1`/169.254.169.254 bloqués).
- `read_page` : redirections suivies **manuellement** et **revalidées** à chaque
  saut (bloque une URL publique redirigeant vers localhost), bornées, taille et
  timeout limités. `osint.resolve_domain` ne renvoie que des IP publiques.

### Validation (résultats réels)
```
python -m compileall server tests   → OK (exit 0)
pytest -q                            → 236 passed
```
Simulation de crash (scriptée, exécutée) : worker A acquiert l'étape, écrit un
checkpoint et un reçu `in_flight`, « meurt » ; le bail expire ; le reaper reprend
l'étape (checkpoint conservé, `TRANSIENT_WORKER_LOST`) ; worker B termine ;
l'écriture de A est refusée ; **aucun e-mail renvoyé** (reçu in_flight bloquant).

### Tests ajoutés
- `tests/test_agency_step_leases.py` (12) — baux, reaper idempotent, classification,
  backoff, réconciliation, version de schéma.
- `tests/test_csrf_ssrf.py` (11) — Origin CSRF, logout POST-only, SSRF (localhost,
  métadonnées, privé, IPv6, schéma, credentials, DNS→privé, redirection→localhost).

### Fichiers modifiés (incrément 2)
`server/agency/store.py`, `server/agency/orchestrator.py`,
`server/agency/errors.py` (nouveau), `server/agency/backoff.py` (nouveau),
`server/jarvis_v4.py`, `server/integrations/websearch.py`, `server/osint.py`,
`.env.example`, `tests/test_agency_step_leases.py` (nouveau),
`tests/test_csrf_ssrf.py` (nouveau), `CHANGELOG_V5.7.md`, `DURABLE_LEASES_GUIDE.md` (nouveau).

### Restant pour les incréments suivants
Routage de TOUTES les écritures de résultat via `record_step_result` (aujourd'hui
le bail est appliqué au claim/heartbeat/reaper et `record_step_result` est
disponible+testé ; le write terminal de l'orchestrateur passe encore par
`update_step`). Puis : SSE/MJPEG bornés, scopes appareils imposés, liveness des
missions bloquées, vérif indépendante artefacts/reçus, migrations versionnées
étendues, sauvegarde/restauration testée.

---

# CHANGELOG v5.7 — Durabilité & sécurité (incrément 1)

Base : v5.6 (207 tests). Après cet incrément : **213 tests** (`compileall` OK,
`pytest` 213 passed). Aucun test historique cassé. Travail par étapes testables,
sans réécriture ni suppression des fonctions existantes.

## Méthode
- ZIP v5.6 extrait, lu, compilé, testé : **baseline 207 passed** (confirmé).
- 4 audits en **lecture seule** via sous-agents (moteur durable, sécurité) —
  rapports avec fichiers:lignes. Corrections appliquées ci-dessous.

## Corrections livrées (priorités 2 et 3)

### Priorité 2 — Aucune double exécution (idempotence en deux phases) ✅
Fichiers : `server/agency/store.py`, `server/agent.py`, migration additive.
- **Faille** (audit) : le reçu d'idempotence était écrit APRÈS l'effet externe.
  Un crash entre l'envoi (e-mail / workflow n8n / fichier) et l'écriture du reçu
  provoquait un **second envoi** au redémarrage.
- **Correctif** : reçu en **deux phases**. Avant toute action à effet externe
  (SENSIBLE/CRITIQUE), on écrit un reçu `in_flight` de façon atomique
  (`begin_action_receipt`). Après succès → `finalize_action_receipt('succeeded')`.
  Au rejeu : `succeeded` réutilise le résultat ; `in_flight` (effet incertain)
  **bloque la ré-exécution** et exige une vérification humaine (fail-closed).
- Migration SQLite additive (`status`, `updated_at`) : les reçus v5.6 existants
  sont réputés `succeeded`. Aucune donnée perdue.
- Tests : `tests/test_v57_security_durability.py` (reçu in_flight bloque le rejeu,
  finalisation puis réutilisation, blocage bout-en-bout dans ToolRegistry).

### Priorité 3 — Sécurité ✅
Fichiers : `server/guardian/service.py`, `server/agent.py`.
- **CRITIQUE — injection de faits par le `meta` client (Gardien).** `/api/guardian/analyze`
  laissait le navigateur poser `human_validated_intrusion` / `owner_approved_alert`
  / `manual_trigger` / `door_zone_breached`, forçant l'état **ALERT** et
  autorisant la **sirène**. Correctif : `_build_facts(..., trusted=False)` par
  défaut ; les faits critiques ne sont pris en compte que par le chemin serveur
  (`trigger_siren`, `trusted=True`). Le client ne peut plus rien déclencher.
- **Sirène : cooldown réellement appliqué** (il était défini mais jamais vérifié).
- **Secrets dans les logs** : `mot_de_passe`/`gen_password` ajoutés à la liste de
  masquage — un mot de passe généré n'est plus persisté dans `events.jsonl`, la
  timeline ni le flux SSE.
- Tests : injection meta bloquée, sirène autorisée seulement côté serveur,
  cooldown appliqué.

### Priorité 6 (partiel) — Limites Agency configurables ✅
Fichier : `server/agency/orchestrator.py`.
- `AGENCY_MAX_CONCURRENT_AGENTS`, `AGENCY_DEFAULT_MAX_ATTEMPTS`,
  `AGENCY_LEASE_SECONDS`, `AGENCY_HEARTBEAT_SECONDS` lus depuis l'environnement
  (bornés, défauts = comportement v5.6). Le heartbeat utilise l'intervalle configuré.

## Ce qui reste à faire (issu des audits, non encore implémenté) — honnête
Ces points sont réels et priorisés pour les incréments suivants ; ils ne sont
**pas** encore faits :
1. **Lease par ÉTAPE** (`worker_id`/`lease_expires` sur `mission_steps`) + reaper :
   aujourd'hui seule la mission a un bail ; une étape mid-run n'est pas annulée
   si le bail mission est perdu (fenêtre de double exécution multi-worker).
2. **Classification erreur transitoire vs permanente** : toute exception est
   traitée comme transitoire → une étape réellement impossible peut boucler en
   retry (≤6 h) longtemps. Ajouter `error_type` + route vers `BLOCKED`/`FAILED`,
   et **jitter** sur le backoff.
3. **États explicites manquants** : `WAITING_EXTERNAL_SERVICE`, `REPAIRING`,
   `LEASED`, `RETRY_SCHEDULED` (spec §4) — actuellement repliés sur d'autres états.
4. **Vérificateur indépendant renforcé** : la vérification s'appuie sur le texte
   du producteur ; croiser avec les **reçus/artefacts** durables et ne pas
   auto-compléter quand `completion_criteria` est vide.
5. **Liveness des états bloquants** : `BLOCKED`/`WAITING_APPROVAL` sans deadline
   ni escalade → ajouter un âge max + notification.
6. **CSRF** : ajouter un contrôle `Origin`/`Referer` + en-tête requis sur les
   routes mutatives ; passer `/logout` en POST.
7. **SSRF (DNS rebinding)** : épingler l'IP résolue dans `websearch.read_page`
   et filtrer les IP privées côté `osint.resolve_domain`.
8. **Bornage SSE/MJPEG** (connexions concurrentes), **scopes appareils Gardien**
   appliqués au niveau des routes, **brute-force login** durci.

## Fichiers modifiés dans cet incrément
- `server/agency/store.py` (reçus 2 phases + migration)
- `server/agent.py` (idempotence 2 phases, masquage secrets)
- `server/guardian/service.py` (faits trusted, cooldown sirène)
- `server/agency/orchestrator.py` (limites configurables)
- `tests/test_v57_security_durability.py` (nouveaux tests)
- `CHANGELOG_V5.7.md` (ce fichier)
