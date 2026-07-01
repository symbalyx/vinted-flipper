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
