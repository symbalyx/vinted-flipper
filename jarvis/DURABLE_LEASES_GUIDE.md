# Guide — Baux d'étape, reaper et réconciliation (v5.7)

## Pourquoi
Une mission peut durer des heures/jours avec plusieurs workers. Si un worker
meurt (crash, coupure), son étape ne doit ni rester bloquée, ni être exécutée
deux fois. Ce guide décrit les mécanismes.

## Baux d'étape (`mission_steps`)
Colonnes : `worker_id`, `lease_token` (aléatoire), `lease_acquired_at`,
`lease_expires_at`, `heartbeat_at`, `attempt_started_at`, `error_type`.

- **Acquisition** — `claim_step(step_id, worker_id, lease_seconds)` : un `UPDATE`
  conditionnel fait passer l'étape `pending/ready/retry_wait → running` et pose un
  `lease_token`. SQLite garantit qu'**un seul** worker gagne (`rowcount == 1`).
- **Renouvellement** — `renew_step_lease(step_id, worker_id, lease_token, s)` :
  accepté uniquement pour le bon worker+token et une étape encore active. Le
  heartbeat du worker le rappelle toutes les `AGENCY_STEP_HEARTBEAT_SECONDS`.
- **Écriture de résultat** — `record_step_result(step_id, worker_id, lease_token,…)`
  refuse un worker dont le bail a été repris : **pas d'écrasement périmé**.

## Reaper (récupération des workers morts)
`reap_expired_steps(next_run_delay, event_cb)`, appelé par le superviseur toutes
les `AGENCY_REAPER_INTERVAL_SECONDS` :
1. sélectionne les étapes `running/leased` avec `lease_expires_at < now` ;
2. journalise l'abandon (`step_abandoned`) ;
3. conserve le `checkpoint` ;
4. classe l'interruption `TRANSIENT_WORKER_LOST` ;
5. remet l'étape en `retry_wait` avec un `next_run_at` (backoff) ;
6. invalide l'ancien bail.
Il est **idempotent** : `lease_expires_at` est remis à 0, un second passage ne
retraite pas l'étape (compteur d'essais non doublé).

## Classification des erreurs
`server/agency/errors.py` distingue temporaire / permanent / humain requis.
Temporaire → retry planifié. Permanent → blocage/échec expliqué. Refus
d'approbation → `HUMAN_REQUIRED`, jamais retenté automatiquement.

## Backoff + jitter
`server/agency/backoff.py` : `clamp(base·2^(n-1), base, max) ± jitter`, respecte
`Retry-After`, borné, persistant (`next_run_at`). Réglable via `AGENCY_RETRY_*`.

## Réconciliation des reçus `in_flight`
Une action à effet externe pose un reçu `in_flight` **avant** l'effet
(cf. incrément 1). Après un crash entre l'effet et la confirmation :
- le reçu reste `in_flight` → **tout rejeu aveugle est bloqué** ;
- `reconcile_stuck_receipts()` marque les reçus trop anciens
  `RECONCILIATION_REQUIRED` (jamais de réexécution automatique).

### Stratégies par action (état cible)
| Action | Stratégie de réconciliation |
|---|---|
| E-mail | `Message-ID`/clé d'idempotence ; en cas de doute → `UNKNOWN_EXTERNAL_STATE`, décision humaine, **pas de renvoi** |
| n8n | rechercher un workflow au tag d'opération avant de recréer |
| Fichier | écriture temp + remplacement atomique + empreinte ; vérifier si le contenu final existe |
| App | ne pas relancer si le process attendu tourne déjà |

> État actuel : le blocage anti-double-effet et le marquage
> `RECONCILIATION_REQUIRED` sont **implémentés et testés**. Les stratégies
> spécifiques par fournisseur (Message-ID e-mail, tag n8n) sont **prévues** et
> documentées ci-dessus ; leur implémentation complète est un incrément suivant.

## Variables d'environnement
Voir `.env.example` (`AGENCY_STEP_LEASE_SECONDS`, `AGENCY_STEP_HEARTBEAT_SECONDS`,
`AGENCY_REAPER_INTERVAL_SECONDS`, `AGENCY_RETRY_BASE_SECONDS`,
`AGENCY_RETRY_MAX_SECONDS`, `AGENCY_RETRY_JITTER_RATIO`).
