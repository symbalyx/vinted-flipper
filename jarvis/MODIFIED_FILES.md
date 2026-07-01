# Fichiers ajoutés ou modifiés — JARVIS v5.6

## Moteur durable

- `server/agency/models.py` — nouveaux états persistants et métadonnées d’essai.
- `server/agency/store.py` — migrations SQLite, heartbeats, baux, checkpoints,
  mémoire inter-missions, artefacts et reçus d’idempotence.
- `server/agency/orchestrator.py` — reprise automatique, retries, tranches de
  calcul, validation finale, cycles de réparation et blocage explicite.
- `server/agency/planner.py` — rôles et plan de prospection.
- `server/agency/api.py` — critères de fini, mémoire et reprise.
- `server/durability.py` — contrôle d’intégrité et sauvegardes SQLite cohérentes.
- `server/agent.py` — limites de tours retentables, checkpoints d’outils,
  idempotence et outils de prospection.
- `server/permissions.py` — niveaux de risque, contexte d’approbation et logs masqués.

## Prospection

- `server/prospecting/__init__.py`
- `server/prospecting/policy.py`
- `server/prospecting/store.py`
- `server/prospecting/service.py`
- `server/prospecting/api.py` — CRM et création de campagnes Agency durables.
- `web/prospection.html` — campagne, CRM, scoring, brouillons et exclusions.

## Intégration et interface

- `server/jarvis_v4.py` — branchement Agency durable, CRM, validation et mémoire.
- `web/agency.html` — définition de fini, cycles, essais et reprise.
- `web/index.html` — accès Prospection.
- `.env.example`, `Dockerfile`, `docker-compose.yml`, scripts de lancement,
  requirements et `pyproject.toml` — configuration v5.6.

## Tests ajoutés ou étendus

- `tests/test_agency_durability.py`
- `tests/test_durability_maintenance.py`
- `tests/test_agency_runtime.py`
- `tests/test_prospecting.py`
- `tests/test_prospecting_api.py`

## Documentation

- `DURABLE_AGENCY_GUIDE.md`
- `PROSPECTING_GUIDE.md`
- `CHANGELOG_V5.6.md`
- `README_v4.md`
- `AGENCY_GUIDE.md`
- `SECURITY.md`
- `SECURITY_AUDIT_RESULTS.md`
- `TEST_RESULTS.md`
