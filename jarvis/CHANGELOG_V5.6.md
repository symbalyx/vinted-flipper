# Changelog JARVIS v5.6

## Durable Agency

- ajout des statuts `verifying`, `retry_wait` et `blocked` ;
- checkpoints persistants par étape ;
- heartbeat mission/étape ;
- bail SQLite multi-worker ;
- reprise automatique après crash et fin de tranche ;
- retries exponentiels courts et persistants ;
- cycles de réparation ;
- définition de fini configurable ;
- contrôle final avant `completed` ;
- mémoire inter-missions ;
- artefacts et événements enrichis ;
- reçus d’idempotence pour éviter les doubles effets externes ;
- limite interne de tours d’un sous-agent transformée en erreur retentable ;
- jusqu’à 60 tours par étape, configurable ;
- tranches de mission jusqu’à 7 jours.

## Prospection

- nouveau module `server/prospecting/` ;
- interface `/prospection` ;
- CRM SQLite ;
- source publique obligatoire ;
- déduplication ;
- scoring explicable ;
- brouillons honnêtes ;
- URL de démo conditionnelle ;
- liste de suppression ;
- limites quotidienne, domaine et intervalle ;
- double envoi empêché ;
- outils agentiques de prospection ;
- nouveaux rôles Agency spécialisés ;
- chaque envoi classé `CRITICAL`.

## Confidentialité

- résultats d’e-mails, brouillons, workflows et fichiers masqués dans les logs ;
- paramètres sensibles masqués dans l’audit d’approbation ;
- coordonnées masquées dans la mémoire inter-missions.

## Interface

- définition de fini et cycles de réparation dans `/agency` ;
- affichage des essais et cycles d’erreur ;
- lien Prospection dans le tableau de bord ;
- CRM mobile sans injection HTML dynamique.

## Durabilité renforcée

- Les pannes du planificateur ou de l’orchestrateur passent en `retry_wait` avec
  backoff persistant au lieu de terminer la mission.
- Un refus d’approbation place l’étape et la mission en `blocked`, sans faux
  succès ni abandon définitif.
- Les mémoires inter-missions masquent aussi les coordonnées et secrets présents
  dans l’objectif, les critères et le verdict.

## Campagnes de prospection

- Nouveau lanceur dans `/prospection` par secteur, région, volume et offre.
- Création automatique d’une mission Agency durable avec définition de fini.
- Recherche publique, déduplication, qualification, brouillons non envoyés,
  contrôle conformité et rapport chiffré.

## Sauvegardes SQLite

- Contrôle `PRAGMA quick_check` avant et après copie.
- Sauvegarde cohérente des bases Agency et Prospection avec l’API SQLite.
- Rétention configurable et statut exposé dans `/api/agency/status`.
